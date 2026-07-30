"""특수관계자 주석 T1 파서 (valuechain PLAN.md Phase V1, universe/PLAN.md U-D2).

shared/data/reports.db의 report_section(연결주석) 중 "특수관계자*" 계열 제목 노트의
마크다운 표(text_md)에서 매출/매입 거래금액을 추출해 ValueChainEdge(T1)로 적재한다.

표 구조 실측(2026-07-21, 삼성전자 5개년 샘플로 확인):
  - DART XBRL→마크다운 변환 산출물은 계층형 컬럼 헤더를 완전한 콜스팬 정보 없이
    평탄화한다 — "관계기업 및 공동기업"(2열) 같은 상위 그룹 헤더 행은 하위 리프 헤더
    (개별 상대회사명)보다 셀 수가 적어 위치로 정렬할 수 없다.
  - 실제 개별 상대회사명은 "이 표 블록 안에서 첫 칸이 빈 마지막 행"으로 식별한다 —
    헤더 행은 모두 첫 칸이 비고, 데이터 행(매출 등/매입 등…)은 첫 칸에 항목명이
    있어 이 규칙이 흔들리지 않는다(회사·연도별 표 편차와 무관하게 안정적).
  - "당기"/"전기" 두 기간이 같은 표 제목 아래 반복된다 — 전기는 스킵(중복 방지:
    전기 수치는 그 회사의 전년도 보고서 자체의 "당기" 블록에서 이미 잡힌다).
  - "기타 관계기업 및 공동기업" 등 "기타 "로 시작하는 컬럼은 특정 법인이 아닌
    집계 컬럼이므로 엣지를 만들지 않는다.
  - "특수관계자거래에 대한 공시, 합계" 등 제목에 "합계"가 붙은 표는 리프 헤더 자체가
    개별 법인명이 아니라 "관계기업 및 공동기업"·"대규모기업집단" 같은 카테고리명이다
    ("기타" 접두어가 없어 위 필터로 걸러지지 않음) — 표 제목으로 통째 스킵한다.
  - "비유동자산 매입/처분"처럼 "매입"을 포함하지만 상거래가 아닌 항목을 오분류하지
    않도록 라벨은 startswith로만 판정한다(포함 매치 금지).

파서는 1벌 구현, 소비자 2곳 원칙(U-D2) — 이 함수는 ValueChainEdge만 적재한다.
RelationLocal 소비(주석 전용 지배구조 엣지, U1 미포착분 보완)는 U3에서 이 parse_note()
출력을 재사용해 별도 어댑터를 얹는다(이중 파서 구현 금지).
"""

from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup

from modules.relation.storage.db import get_local_session
from modules.relation.storage.models import RelationLocal, ValueChainEdge
from modules.relation.transform import entity_kind
from modules.relation.valuechain.extract import reports_source
from modules.relation.valuechain.extract.linking import (
    blocked_pair,
    build_guard_context,
    link_counterparty,
)

logger = logging.getLogger(__name__)

# 실측 확인된 제목 변형 10종 (report_section.title, section_key="III.3.연결주석")
NOTE_TITLES = {
    "특수관계자",
    "특수관계자거래",
    "특수관계자 거래",
    "특수관계자와의 거래",
    "특수관계자 등과의 거래",
    "특수관계자등과의 거래",
    "특수관계자 - 연결",
    "특수관계자 및 대규모기업집단 소속회사와 거래",
    "특수관계자 공시 등",
    "연결실체와 특수관계자간의 거래",
}

_PERIOD_MARKER_RE = re.compile(r"^\|\s*(당기|전기)\s*\|\s*\(단위\s*[:：]\s*([^)]+)\)\s*\|?\s*$")
_TITLE_LINE_RE = re.compile(r"^\|\s*([^|]+?)\s*\|\s*$")
_UNIT_MULTIPLIERS = {"원": 1, "천원": 1_000, "백만원": 1_000_000, "억원": 100_000_000}

_EXCLUDE_LABEL_SUBSTR = ("채권", "채무", "잔액")

# 회사별 표기 편차 실측(2026-07-22, 109노트 전수) — "매출 등"/"매입 등"(삼성 계열)만으로는
# 13/109만 커버. "수익거래"/"비용거래"(현대차 계열 등)를 추가해 41/109로 확대.
# ★ 여전히 커버 못 하는 다수(하나금융지주 계열·LIG넥스원 등)는 **행=상대회사명**인
# 전치(transposed) 표 구조 — 이 함수가 가정하는 "행=거래유형·열=상대회사명"의 반대라
# 별도 파서가 필요(후속 과제, PROGRESS.md에 정직하게 기록). 억지 매칭 금지.
# ★ 2026-07-22 추가 실측(기아·현대모비스·한화시스템 investigate): "재화의 판매로 인한
# 수익, 특수관계자거래"/"재화의 매입, 특수관계자거래"(한화시스템 컬럼 헤더) 라벨도
# 동일 어휘군 — startswith 접두어에 추가(기아의 "특수관계자 기타매출"/"특수관계자
# 기타매입" 같은 비상거래 컬럼은 "특수관계자"로 시작해 이 접두어와 자연히 불일치,
# 오분류 위험 없음 확인).
_SALES_LABEL_PREFIXES = ("매출", "수익거래", "재화의 판매로 인한 수익")
_PURCHASE_LABEL_PREFIXES = ("매입", "비용거래", "재화의 매입")


def _split_row(line: str) -> list[str]:
    """마크다운 표 한 행 → 셀 리스트 (앞뒤 파이프 제거, strip)."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _parse_amount(cell: str, multiplier: int) -> float | None:
    s = cell.strip().replace(",", "")
    if not s or s in ("-", "−", "―"):
        return None
    try:
        value = float(s)
    except ValueError:
        return None
    if value == 0:
        return None
    return value * multiplier


def _extract_period_blocks(text_md: str) -> list[tuple[str, str, int, list[str]]]:
    """text_md → [(title, period, multiplier, table_lines), ...].

    title은 직전에 나온 단일 셀 `| ... |` 행(당기/전기 마커가 아닌 것) — "합계" 표
    스킵 판단용. 마커 라인과 실제 표(|로 시작하는 행) 사이에는 회사마다 편차가 있다
    (실측: 빈 줄 한 줄만 있는 경우 vs 제목·기간·단위를 파이프 없이 그대로 반복하는
    평문 몇 줄이 끼는 경우 — sectioner가 원문 `<P>` 문단과 `<TABLE>`을 각각 렌더링해
    중복 생김). 그래서 "|"로 시작하지 않는 줄은 전부 건너뛰되, **다음 마커·제목 줄과
    만나면 그 자리에서 멈춘다**(표가 아예 없는 블록을 다음 마커까지 통째로 삼켜버리는
    사고 방지).
    """
    lines = text_md.splitlines()
    blocks: list[tuple[str, str, int, list[str]]] = []
    current_title = ""
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        m = _PERIOD_MARKER_RE.match(stripped)
        if not m:
            title_m = _TITLE_LINE_RE.match(stripped)
            if title_m:
                current_title = title_m.group(1).strip()
            i += 1
            continue
        period, unit_raw = m.group(1), m.group(2).strip()
        multiplier = _UNIT_MULTIPLIERS.get(unit_raw, 1)
        i += 1
        while i < len(lines):
            s = lines[i].strip()
            if s.startswith("|"):
                break
            if _PERIOD_MARKER_RE.match(s) or _TITLE_LINE_RE.match(s):
                break  # 표 없는 블록 — 다음 마커/제목에서 멈추고 그대로 넘김
            i += 1  # 평문 중복(제목·기간·단위 재진술) 또는 빈 줄 — 스킵
        table_lines: list[str] = []
        while i < len(lines) and lines[i].strip().startswith("|"):
            table_lines.append(lines[i])
            i += 1
        blocks.append((current_title, period, multiplier, table_lines))
    return blocks


def parse_note(text_md: str | None) -> list[dict]:
    """특수관계자 주석 텍스트 → [{counterparty, direction, amount, label}] (당기분만).

    direction: "customer"(당사의 매출처 — 상대가 고객) | "supply"(당사의 매입처 — 상대가 공급자)
    amount 단위: 원(KRW) — 표기 단위(백만원 등)를 곱해 정규화.
    """
    results: list[dict] = []
    if not text_md:
        return results

    for title, period, multiplier, table_lines in _extract_period_blocks(text_md):
        if period != "당기":
            continue
        if "합계" in title:
            continue  # 카테고리 집계 표 — 리프 헤더가 개별 법인명이 아님
        rows = [_split_row(ln) for ln in table_lines]
        header_rows = [r for r in rows if r and r[0] == ""]
        data_rows = [r for r in rows if r and r[0] != ""]
        if not header_rows:
            continue
        leaf_columns = header_rows[-1]  # 첫 칸이 빈 마지막 행 = 개별 상대회사명

        for row in data_rows:
            # rowspan 하위분류 행(예: "수익거래"/"매출거래" 2단 라벨)은 라벨 셀이
            # 1개 더 많아 값 위치가 한 칸씩 밀린다 — 잘못된 상대회사에 금액을 붙이는
            # 사고를 막기 위해 라벨 1개(=leaf_columns와 정확히 같은 셀 수)인 행만
            # 처리한다. 하위분류 세부금액은 스킵되지만(총계 행만 반영) 오귀속보다 안전.
            if len(row) != len(leaf_columns):
                continue
            label = row[0]
            if any(x in label for x in _EXCLUDE_LABEL_SUBSTR):
                continue
            if label.startswith(_SALES_LABEL_PREFIXES):
                direction = "customer"
            elif label.startswith(_PURCHASE_LABEL_PREFIXES):
                direction = "supply"
            else:
                continue

            for idx in range(1, min(len(row), len(leaf_columns))):
                counterparty = leaf_columns[idx].strip()
                if not counterparty or counterparty.startswith("기타"):
                    continue
                amount = _parse_amount(row[idx], multiplier)
                if amount is None:
                    continue
                results.append(
                    {
                        "counterparty": counterparty,
                        "direction": direction,
                        "amount": amount,
                        "label": label,
                    }
                )
    return results


# ★ 2026-07-22 전치(transposed)형 거래금액 표(하나금융지주 계열·LIG디펜스앤에어로
# 스페이스 등, 위 parse_note() 주석에서 후속 과제로 남겼던 것) — parse_note()가
# 가정하는 "행=거래유형·열=상대회사명"의 정반대로 "행=상대회사명(ROWSPAN
# 카테고리)·열=거래유형"이다. text_md 평탄화는 이 표의 ROWSPAN도 뭉개므로
# U3에서 구축한 text_html + rowspan 그리드 복원 경로(_html_table_grid,
# _find_header_row)를 그대로 재사용한다(U-D2 준용 — 표 파싱 인프라 1벌).
_UNIT_RE = re.compile(r"\(단위\s*[:：]\s*([^)]+)\)")


def _label_match(h: str, prefixes: tuple[str, ...]) -> bool:
    return h.startswith(prefixes) and not any(x in h for x in _EXCLUDE_LABEL_SUBSTR)


def parse_note_transposed(text_html: str | None) -> list[dict]:
    """전치형 거래금액 표(하나금융지주·LIG디펜스앤에어로스페이스·기아·한화시스템류) →
    parse_note()와 동일 스키마 [{counterparty, direction, amount, label}].

    "당기"/"(단위 : ...)" 소표를 순서대로 만나 상태를 갱신하고, 매출/매입 계열
    열 헤더(_SALES_LABEL_PREFIXES/_PURCHASE_LABEL_PREFIXES — "매출 등"·"매출"·
    "재화의 판매로 인한 수익..." 등 회사별 표기 편차 전부 포함)가 있는 본표를
    만나면 그 상태로 처리한다. 전기 표는 parse_note()와 동일하게 스킵(그 회사
    전년도 보고서의 당기 블록에서 이미 잡힘, 중복 방지).
    """
    results: list[dict] = []
    if not text_html:
        return results

    soup = BeautifulSoup(text_html, "html.parser")
    period = None
    multiplier = 1
    for table in soup.find_all("table"):
        text = table.get_text(" ", strip=True)
        ths_probe = table.find_all("th")
        # 제목/기간/단위 소표(회사마다 렌더링 편차 — 별도 표이거나 한 표 안에 같이
        # 있거나, ★2026-07-22 추가 실측(기아·한화시스템): "제목 행 + 당기·단위 행"
        # 2행짜리 한 표인 경우도 있음)는 전부 `<th>`가 없는 작은 표라는 공통점으로
        # 식별한다 — 본 데이터 표는 항상 `<thead><th>`를 쓰므로 구분에 안전하다.
        if not ths_probe:
            cell_texts = [c.get_text(strip=True) for c in table.find_all(["td", "te"])]
            if len(cell_texts) <= 4:
                if "당기" in cell_texts:
                    period = "당기"
                elif "전기" in cell_texts:
                    period = "전기"
                unit_m = _UNIT_RE.search(text)
                if unit_m:
                    multiplier = _UNIT_MULTIPLIERS.get(unit_m.group(1).strip(), 1)
                continue

        ths = [th.get_text(strip=True) for th in ths_probe]
        sales_ths = [h for h in ths if _label_match(h, _SALES_LABEL_PREFIXES)]
        purchase_ths = [h for h in ths if _label_match(h, _PURCHASE_LABEL_PREFIXES)]
        if not (sales_ths or purchase_ths):
            continue
        if period != "당기":
            continue  # 전기 표(또는 기간 마커를 못 만난 표) — 스킵

        grid = _html_table_grid(table)
        anchor_label = sales_ths[0] if sales_ths else purchase_ths[0]
        header_idx = _find_header_row(grid, {anchor_label})
        if header_idx is None:
            continue
        header_row = grid[header_idx]
        amount_cols = [
            (idx, "customer")
            for idx, h in enumerate(header_row)
            if _label_match(h, _SALES_LABEL_PREFIXES)
        ] + [
            (idx, "supply")
            for idx, h in enumerate(header_row)
            if _label_match(h, _PURCHASE_LABEL_PREFIXES)
        ]
        if not amount_cols:
            continue
        name_col = min(idx for idx, _ in amount_cols) - 1
        category_col = name_col - 1
        if name_col < 0:
            continue

        for row in grid[header_idx + 1 :]:
            if len(row) <= name_col:
                continue
            counterparty = row[name_col].strip()
            if (
                not counterparty
                or counterparty.startswith("기타")
                or counterparty.endswith("기타")  # ★기아 실측: "유의적인 영향력을 행사하는 기타" 등 집계 캐치올
                or "합계" in counterparty
            ):
                continue
            if category_col >= 0 and counterparty == row[category_col].strip():
                continue  # "전체 특수관계자" 같은 합계 행 — 개별 법인 아님
            for idx, direction in amount_cols:
                if idx >= len(row):
                    continue
                amount = _parse_amount(row[idx], multiplier)
                if amount is None:
                    continue
                results.append(
                    {
                        "counterparty": counterparty,
                        "direction": direction,
                        "amount": amount,
                        "label": header_row[idx],
                    }
                )
    return results


# ★ 2026-07-29 U-확대 실측: 전 상장사 1,550노트 중 거래금액 파서가 0건인 856노트를
# 분해한 결과 **464노트(54%)가 "라벨은 인식되는데 셀 수가 안 맞아" 스킵된 것**이었다
# (나머지: 라벨 어휘 미등록 32 · 더 깊은 구조 변형 357). 원인은 parse_note()의
# 한계로 이미 적혀 있던 그것 — markdown 평탄화가 계층 헤더의 COLSPAN을 뭉개
# 열 정렬 자체가 불가능해진다. 표 자체는 정상이고, 원본 text_html을 ROWSPAN/COLSPAN
# 복원(_html_table_grid)하면 **모든 행이 균일 폭으로 완벽 정렬**된다(포스코퓨처엠 21열·
# 현대차 계열 27열·삼성전자 16열 실측). 즉 새 표 변형이 아니라 **같은 표를 온전한
# 소스로 다시 읽는 것** — 거버넌스 파서 3종이 이미 쓰는 검증된 경로를 거래금액에 적용.
_GROUP_TOTAL_SKIP = True  # 그룹 합계 행(라벨 셀 전부 동일) 이중계상 방지

# K-IFRS 1024호 특수관계자 공시의 **구분(카테고리) 어휘** — 리프 헤더 칸에 이 말이
# 들어 있으면 개별 법인이 아니라 집계 컬럼이다. 실측 근거(2026-07-29): 카테고리
# 하위에 개별 분해가 없는 컬럼은 상위 카테고리명이 ROWSPAN으로 리프 행까지 내려온다
# (현대차 계열의 "그 밖의 특수관계자"·"대규모기업집단 계열회사"가 회사명 칸에 그대로).
# ⚠️ "캐리다운이면 집계"로 판정하면 안 된다 — 삼성전자 표의 삼성엔지니어링㈜·㈜에스원은
# 하위 분해가 없어 똑같이 캐리다운되지만 **실제 법인**이라 4건이 통째로 소실됐다
# (구현 중 실측·수정). 그래서 구조가 아니라 **어휘**로 판정한다. 법인격 표기(㈜·(주)·
# Ltd. 등)를 쓰는 실제 사명과 이 어휘군은 겹치지 않는다.
_CATEGORY_COLUMN_VOCAB = (
    "특수관계자", "관계기업", "공동기업", "종속기업", "지배기업", "기업집단",
    "계열회사", "경영진", "영향력", "공동지배", "합계",
)


def _is_category_column(name: str) -> bool:
    """리프 헤더 값이 개별 법인이 아니라 K-IFRS 구분(집계 컬럼)인가."""
    return any(v in name for v in _CATEGORY_COLUMN_VOCAB)


def _leaf_header_index(grid: list[list[str]]) -> int | None:
    """첫 칸이 빈 마지막 헤더 행 = 개별 상대회사명 행 (parse_note와 같은 규칙).

    데이터 행은 첫 칸에 항목명이 있고 헤더 행은 첫 칸이 비므로, "첫 칸이 빈 행이
    연속되다 처음 안 비는 행이 나오는 경계"의 직전이 리프 헤더다.
    """
    last_empty = None
    for i, row in enumerate(grid):
        if not row:
            continue
        if row[0].strip() == "":
            last_empty = i
        elif last_empty is not None:
            return last_empty
    return None


def parse_note_html_grid(text_html: str | None) -> list[dict]:
    """계층 헤더 거래금액 표 → parse_note()와 동일 스키마.

    markdown 경로가 COLSPAN 유실로 열 정렬에 실패하는 표를 원본 HTML 그리드로
    읽는다. 리프 헤더의 선행 빈 칸 개수 = 라벨 컬럼 수이며(현대차 계열은 2단
    라벨이라 2, 포스코·삼성은 1), 금액은 그 다음 칸부터 리프 회사명과 1:1 대응한다.

    이중계상 방지: 2단 라벨 표의 그룹 합계 행(라벨 셀이 전부 같은 값 — 현대차의
    "수익거래|수익거래|…")은 같은 그룹에 세부 행이 따로 있으면 스킵한다.
    억지 매칭 금지: 리프 헤더를 못 찾거나 라벨 컬럼이 0이면 조용히 건너뛴다.
    """
    results: list[dict] = []
    if not text_html:
        return results

    soup = BeautifulSoup(text_html, "html.parser")
    period: str | None = None
    multiplier = 1

    for table in soup.find_all("table"):
        if not table.find_all("th"):
            # 제목/기간/단위 소표 — parse_note_transposed와 동일한 식별 규칙
            cell_texts = [c.get_text(strip=True) for c in table.find_all(["td", "te"])]
            if len(cell_texts) <= 4:
                if "당기" in cell_texts:
                    period = "당기"
                elif "전기" in cell_texts:
                    period = "전기"
                unit_m = _UNIT_RE.search(table.get_text(" ", strip=True))
                if unit_m:
                    multiplier = _UNIT_MULTIPLIERS.get(unit_m.group(1).strip(), 1)
                continue
        if period != "당기":
            continue  # 전기 표(또는 기간 마커 미확인) — parse_note와 같은 중복 방지

        grid = _html_table_grid(table)
        if len(grid) < 2:
            continue
        header_idx = _leaf_header_index(grid)
        if header_idx is None:
            continue
        leaf = grid[header_idx]
        label_cols = 0
        for cell in leaf:
            if cell.strip() == "":
                label_cols += 1
            else:
                break
        if label_cols == 0 or label_cols >= len(leaf):
            continue


        # 1차 수집 — 그룹 합계 판정을 위해 행 단위로 모은 뒤 확정
        staged: list[tuple[str, str, list[str]]] = []  # (group, label, row)
        for row in grid[header_idx + 1 :]:
            if len(row) != len(leaf):
                continue  # 그리드 복원 후에도 폭이 다른 행 — 표 밖 잔재, 스킵
            label = row[label_cols - 1].strip()
            if not label:
                continue
            staged.append((row[0].strip(), label, row))

        sublabels_by_group: dict[str, set[str]] = {}
        for group, label, _row in staged:
            sublabels_by_group.setdefault(group, set()).add(label)

        for group, label, row in staged:
            if (
                _GROUP_TOTAL_SKIP
                and label_cols > 1
                and label == group
                and len(sublabels_by_group.get(group, set())) > 1
            ):
                continue  # 그룹 합계 행 — 세부 행이 따로 있으므로 이중계상
            if any(x in label for x in _EXCLUDE_LABEL_SUBSTR):
                continue
            if label.startswith(_SALES_LABEL_PREFIXES):
                direction = "customer"
            elif label.startswith(_PURCHASE_LABEL_PREFIXES):
                direction = "supply"
            else:
                continue

            for idx in range(label_cols, len(leaf)):
                counterparty = leaf[idx].strip()
                if (
                    not counterparty
                    or counterparty.startswith("기타")
                    or _is_category_column(counterparty)
                ):
                    continue  # 집계 컬럼 — 특정 법인 아님
                amount = _parse_amount(row[idx], multiplier)
                if amount is None:
                    continue
                results.append(
                    {
                        "counterparty": counterparty,
                        "direction": direction,
                        "amount": amount,
                        "label": label,
                    }
                )
    return results


# 2026-07-22 실측(109노트 표본 조사): "구분/특수관계자명" 2-컬럼 카테고리 나열형이
# 여러 회사에서 동일하게 확인됨(삼성바이오로직스·SK이노베이션·HD현대·HD현대중공업·
# HD한국조선해양 등) — U-D2 "파서 1벌, 소비자 2곳" 원칙에 따라 같은 노트에서 이
# 표를 추출해 RelationLocal(거버넌스 레이어, source_type=dart_filing)도 채운다.
# ★ 다른 두 변형(현대로템·LIG넥스원류의 와이드 1행형, KT&G류의 행=개별회사+상세
# 메타데이터형)은 구조가 크게 달라 이번엔 손대지 않는다 — 억지 매칭 금지, 후속 과제.
# ★ 2026-07-22 추가 실측: 구조는 동일하나 두 번째 컬럼 라벨이 "특수관계자명"이
# 아니라 "회사명"(SK하이닉스·SK텔레콤)인 회사가 있음 — 카카오는 "회사명(주1)"처럼
# 각주 마커가 라벨에 붙기도 함. 라벨 문자열만 다르고 표 구조(카테고리별 콤마 구분
# 나열)는 동일해 같은 정규식으로 흡수.
_CATEGORY_HEADER_RE = re.compile(
    r"^\|\s*구\s*분\s*\|\s*(?:특수관계자명|회사명)\s*(?:\([^)]*\))?\s*\|\s*$"
)
_FOOTNOTE_LABEL_RE = re.compile(r"^\(주\d*\)$")

# ★ 2026-07-30 열 밀림 수리에서 함께 발견 — 콤마 분할이 **두 가지로** 틀렸다.
# 전수 실측(1,550노트): parse_governance_categories 산출 3,882건 중 잡음 326건,
# 그 **261건이 `suffix_fragment`** — `Co., Ltd.`의 콤마를 쪼개 `Ltd.` 조각만 남은 것이고,
# 나머지는 `㈜에이피헬스케어(구.㈜...)(*1, 2)`처럼 **괄호 안 콤마**를 쪼개 사명이
# 두 동으로 갈린 것이다(에이프로젠바이오로직스 실측: `...(*1` + `2)`).
#
# 원칙 ②("괄호는 신원 정보다")의 분할판 — 괄호 안은 한 덩어리다. 그리고 법인격
# 접미어만 남는 조각은 앞 조각의 일부이므로 되붙인다.
_LIST_SEP_RE = re.compile(r"[,、·]")
_OPEN_BRACKETS = "([{（［｛"
_CLOSE_BRACKETS = ")]}）］｝"
# 되붙임 대상 — 이 토큰만으로 이루어진 조각은 독립 법인명이 될 수 없다.
_LEGAL_TAIL_TOKENS = frozenset({
    "ltd", "inc", "llc", "llp", "co", "corp", "gmbh", "sa", "sas", "sarl",
    "bv", "nv", "pte", "plc", "ag", "kk", "lp", "sro", "srl", "pty", "spa",
    "limited", "company", "corporation", "sdnbhd", "bhd", "ltda", "cv", "kg",
})
_ASCII_TAIL_MAX = 8  # 'SAdeCV'(6)·'SdnBhd'(6)·'GmbHCoKG'(8) 등 약어 길이 상한


def _is_legal_tail(piece: str) -> bool:
    """조각이 **법인격 접미어만**인가 — 그렇다면 앞 조각의 일부다.

    ⚠️ 토큰 열거로는 못 막는다(실측: `Kia Mexico, S.A. de C.V.`가 `S.A. de C.V.`를
    미등록 토큰이라 쪼갰다). 그래서 형태 규칙을 쓴다 —
      ① 알파벳만 남겼을 때 8자 이하(약어 길이) **그리고**
      ② 점(.)을 포함하거나 알려진 접미어 토큰 — 점이 없는 짧은 토큰까지 접미어로
         보면 `HMM`·`KT` 같은 **실존 단독 사명이 앞 조각에 흡수**된다.
    한글이 섞인 조각은 대상이 아니다('다라 주식회사'를 '가나'에 붙이면 안 됨).
    """
    p = piece.strip()
    if not p or re.search(r"[가-힣]", p):
        return False
    letters = re.sub(r"[^A-Za-z]", "", p)
    if not letters or len(letters) > _ASCII_TAIL_MAX:
        return False
    return "." in p or letters.lower() in _LEGAL_TAIL_TOKENS


def split_company_list(name: str | None) -> list[str]:
    """콤마·중점 나열 회사명 칸 → 개별 법인 조각 (분리 지점 없으면 빈 리스트).

    ⚠️ 두 가지 함정을 회귀 박제로 막는다:
      ① **괄호 안 콤마는 분리하지 않는다** — `㈜앱토크롬(구, ㈜에이피헬스케어)`·
         `...(*1, 2)`가 두 동으로 갈린다(표기 정규화 원칙 ② 분할판).
      ② **법인격 접미어만 남는 조각은 앞으로 되붙인다** — `Co., Ltd.`를 쪼개면
         `Ltd.` 조각이 노드 후보로 남는다(실측 261건).
    """
    if not name:
        return []
    depth = 0
    parts: list[str] = []
    buf: list[str] = []
    for ch in name:
        if ch in _OPEN_BRACKETS:
            depth += 1
        elif ch in _CLOSE_BRACKETS:
            depth = max(0, depth - 1)
        if depth == 0 and _LIST_SEP_RE.match(ch):
            parts.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    parts.append("".join(buf))
    if len(parts) < 2:
        return []

    merged: list[str] = []
    for raw in parts:
        piece = raw.strip()
        if not piece:
            continue
        if merged and _is_legal_tail(piece):
            merged[-1] = f"{merged[-1]}, {piece}"  # 'Co.' + 'Ltd.' → 'Co., Ltd.'
            continue
        merged.append(piece)
    return merged if len(merged) >= 2 else []


def parse_governance_categories(text_md: str | None) -> list[dict]:
    """특수관계자 "구분/특수관계자명" 카테고리 표 → [{category, counterparty}].

    지배기업/관계기업/공동기업/기타/대규모기업집단 등 카테고리별로 콤마 구분된
    회사명 나열을 개별 상대회사로 분해한다. sectioner가 원문 문단을 평문으로도
    중복 렌더링하므로(관련 없는 문장에 우연히 "구분...특수관계자명..." 텍스트가
    이어붙어 나타남) **파이프 표 형태로 정확히 일치하는 헤더 행만** 인식하고,
    첫 매칭 표만 처리한다(사업연도당 표는 논리적으로 1개뿐 — 뒤이은 평문/재렌더
    중복 스킵).

    한계(정직하게 기록): 외국법인명이 "Ltd.," 처럼 콤마를 포함한 법인 접미어를
    쓰는 경우 콤마 분리 시 잘못 쪼개질 수 있다 — 다만 그런 이름은 대부분
    CompanyRegistry(국내 상장사)에 없어 entity linking 단계에서 자연히 걸러지므로
    (링킹 실패로 소실될 뿐 잘못된 엣지가 생기지는 않음) 실질적 정확도 영향은 적다.
    """
    results: list[dict] = []
    if not text_md:
        return results

    lines = text_md.splitlines()
    for i, ln in enumerate(lines):
        if not _CATEGORY_HEADER_RE.match(ln.strip()):
            continue
        j = i + 1
        while j < len(lines) and lines[j].strip().startswith("|"):
            row = _split_row(lines[j])
            j += 1
            if len(row) < 2 or not row[0]:
                continue
            category = row[0].strip()
            if _FOOTNOTE_LABEL_RE.match(category):
                continue  # "(주1)" 각주 행 — 카테고리 아님
            # 괄호 안 콤마 보존 + 법인격 접미어 되붙임 (split_company_list)
            names = split_company_list(row[1]) or [row[1]]
            for name in names:
                name = name.strip()
                if name:
                    results.append({"category": category, "counterparty": name})
        break  # 첫 매칭 표만 — 평문/재렌더 중복 스킵
    return results


# ★ 2026-07-22 와이드 1행형(현대로템류) — DART taxonomy 표준 공시항목 제목
# "회사와 주요 거래 또는 채권ㆍ채무가 있는 특수관계자 현황에 대한 공시" 직후에
# 카테고리가 컬럼 헤더, 상대회사명이 그 아래 단일 데이터 행인 표가 온다.
# 한계(정직하게 기록): LIG디펜스앤에어로스페이스 등 일부 회사는 제목 문구는 같지만
# 표 형태가 전혀 달라(같은 셀 안에 회사명 여러 개가 구분자 없이 붙어 렌더링됨 —
# 원본 마크다운 변환 단계에서 이미 구분자가 유실된 것으로 보임, 텍스트만으로
# 복구 불가) 이 파서로 커버할 수 없다 — **억지 매칭 금지**: 기대한 정확한 표
# 형태(전체 특수관계자/특수관계자 보일러플레이트 2행 + 카테고리 헤더 행 + 데이터
# 행, 셀 수 일치)가 아니면 조용히 빈 결과를 반환한다.
_WIDE_ROW_TITLE_RE = re.compile(
    r"^\|\s*회사와\s*주요\s*거래\s*또는\s*채권.\s*채무가\s*있는\s*특수관계자\s*현황에\s*대한\s*공시\s*\|\s*$"
)
_WIDE_ROW_BOILERPLATE_LABELS = {"전체 특수관계자", "특수관계자"}


def parse_governance_wide_row(text_md: str | None) -> list[dict]:
    """와이드 1행형 거버넌스 표(현대로템류) → [{category, counterparty}].

    카테고리가 컬럼 헤더인 표를 찾아 바로 아래 단일 데이터 행과 위치로 짝짓는다.
    "전체 특수관계자"/"특수관계자" 보일러플레이트 행(모든 회사의 거래금액 표에도
    반복 등장하는 고정 상위 계층 라벨)은 카테고리 헤더로 오인하지 않도록 건너뛴다.
    """
    results: list[dict] = []
    if not text_md:
        return results

    lines = text_md.splitlines()
    for i, ln in enumerate(lines):
        if not _WIDE_ROW_TITLE_RE.match(ln.strip()):
            continue
        header_row: list[str] | None = None
        header_idx: int | None = None
        j = i + 1
        # 제목과 표 사이에 빈 줄·sectioner 평문 중복 렌더링이 끼어들 수 있음 — 첫
        # 파이프 행이 나올 때까지 건너뛴다(무관한 먼 표까지 건너뛰지 않도록 상한).
        lookahead_limit = min(len(lines), i + 1 + 10)
        while j < lookahead_limit and not lines[j].strip().startswith("|"):
            j += 1
        while j < len(lines) and lines[j].strip().startswith("|"):
            row = _split_row(lines[j])
            if (
                len(row) > 2
                and row[0] == ""
                and all(c.strip() for c in row[1:])
            ):
                header_row = row
                header_idx = j
                break
            if not (
                len(row) == 2
                and row[0] == ""
                and row[1].strip() in _WIDE_ROW_BOILERPLATE_LABELS
            ):
                break  # 예상 밖 행 — 안전하게 중단(억지 매칭 금지)
            j += 1
        if header_row is None or header_idx is None:
            break
        data_idx = header_idx + 1
        if data_idx >= len(lines) or not lines[data_idx].strip().startswith("|"):
            break
        data_row = _split_row(lines[data_idx])
        if len(data_row) != len(header_row):
            break  # 셀 수 불일치 — 안전하게 중단
        for category, value in zip(header_row[1:], data_row[1:]):
            category = category.strip()
            if not category:
                continue
            for name in value.split(","):
                name = name.strip()
                if name:
                    results.append({"category": category, "counterparty": name})
        break  # 첫 매칭 표만
    return results


# ★ 2026-07-22 행=개별회사형(KT&G류) — text_md(markdown 평탄화)에서는 카테고리
# 라벨의 rowspan 캐리포워드 정보가 유실돼 행마다 셀 개수가 11/9/8로 달라지고
# 위치 추론이 안전하지 않았다(investigate 기록). 원본 text_html(sectioner 변환
# 이전, ROWSPAN 속성 보존)을 직접 파싱하면 이 모호성이 해소된다 — rowspan을
# 반영한 완전한 셀 그리드를 복원하면 카테고리/회사명 컬럼 위치가 항상 고정된다.
def _html_table_grid(table) -> list[list[str]]:
    """<TABLE> → ROWSPAN/COLSPAN을 반영해 셀 위치를 완전히 채운 2차원 그리드.

    DART XML 표는 <TE>(데이터)·<TH>(헤더) 태그를 쓴다(html.parser가 소문자화).
    """
    grid: list[list[str]] = []
    carry: dict[int, list] = {}  # col_idx -> [remaining_rows, text]
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "te", "td"], recursive=False)
        row: list[str] = []
        col = 0

        def _consume_carry() -> bool:
            nonlocal col
            if col not in carry:
                return False
            entry = carry[col]
            row.append(entry[1])
            entry[0] -= 1
            if entry[0] <= 0:
                del carry[col]
            col += 1
            return True

        for cell in cells:
            while _consume_carry():
                pass
            text = cell.get_text(strip=True)
            colspan = int(cell.get("colspan", 1) or 1)
            rowspan = int(cell.get("rowspan", 1) or 1)
            for _ in range(colspan):
                row.append(text)
                if rowspan > 1:
                    carry[col] = [rowspan - 1, text]
                col += 1
        while _consume_carry():
            pass
        grid.append(row)
    return grid


def _find_header_row(grid: list[list[str]], required_labels: set[str]) -> int | None:
    """required_labels가 모두 셀 값으로(부분일치 아님) 존재하는 첫 행의 인덱스.

    ★ 2026-07-22 실측(두산): sectioner의 평문 중복 렌더링이 markdown뿐 아니라
    원본 text_html 안에도 <TABLE>의 첫 <TR>에 통째로 뭉친 단일 셀로 끼어드는
    경우가 있음(예: `<TD>1) 주요...구분당기말전기말...` 하나의 셀에 표 전체
    텍스트가 이어붙음) — grid[0]을 무조건 헤더로 가정하면 이 오염 행을 헤더로
    잘못 읽는다. 정확히 일치하는 셀 값만 인정해 이 오염 행(라벨이 부분 문자열로만
    존재)을 자연스럽게 걸러낸다.
    """
    for i, row in enumerate(grid):
        if required_labels <= set(row):
            return i
    return None


# ★ 2026-07-30 열 밀림 수리 — 회사명 칸 위치를 **헤더 어휘로** 찾는다.
# 기존 구현은 "소재지 컬럼 바로 왼쪽 = 회사명"이라는 **위치 가정**에 의존했다.
# KT&G(헤더 4칸이 공백 + 소재지가 5번째)에서는 맞지만, 아이센스 실측
# (rcept 20260318001657)의 표는 `회사명 | 소유지분율(당기말·전기말) | 소재지 |
# 결산월 | 업종` 순서라 회사명이 소재지 **왼쪽 3칸**이다 — 결과가 한 칸도 아니고
# 통째로 밀려 `{category:'5.51%', counterparty:'5.56%'}`가 나왔다(지분율 2칸).
# → 회사명 헤더가 **있으면 그 위치**를, 없으면(KT&G) 기존 소재지-상대 위치를 쓴다.
_NAME_HEADER_VOCAB = (
    "특수관계자명", "특수관계자의 명칭", "특수관계자의명칭",
    "회사명", "기업명", "법인명", "상호", "명칭",
)
_PERIOD_SUBHEADERS = {"당기말", "전기말", "당기", "전기", "당기초", "기초", "기말"}


def _collapse(cell: str) -> str:
    return re.sub(r"\s+", "", (cell or "").strip())


def _header_col_by_vocab(header_row: list[str], vocab: tuple[str, ...]) -> int | None:
    """헤더 행에서 vocab 중 하나를 값으로 가진 첫 컬럼 인덱스 (공백 무시)."""
    for idx, cell in enumerate(header_row):
        c = _collapse(cell)
        if c and any(v in c for v in vocab):
            return idx
    return None


def _category_col_by_vocab(header_row: list[str]) -> int | None:
    """'구분'류 카테고리 컬럼. ⚠️ '특수관계자명'을 카테고리로 오인하지 않도록
    '구분'만 본다(부분일치 '특수관계'를 쓰면 회사명 칸이 카테고리가 된다)."""
    for idx, cell in enumerate(header_row):
        if "구분" in _collapse(cell):
            return idx
    return None


# ★ 2026-07-30: 계층 나열 표는 하위 법인 앞에 들여쓰기 불릿을 찍는다(HL D&I 실측
# 13건 — `- HL Transportation, LLC.`·`- 신한벽지 주식회사`). 불릿은 표 레이아웃이지
# 사명이 아니다 — 원문 충실 원칙은 **문자**에 대한 것이고, 개행·연속공백을 접는 것과
# 같은 층의 정리다(upsert_unlisted_node의 공백 정규화 선례).
_LIST_MARKER_RE = re.compile(r"^[-−–—ㆍ·•*※]+\s+")


def _strip_list_marker(name: str) -> str:
    return _LIST_MARKER_RE.sub("", name or "").strip()


def _is_full_width_label(row: list[str]) -> str | None:
    """모든 칸이 같은 값인 행 = 표 안의 전폭 카테고리 머리행(아이센스 '관계기업:').

    COLSPAN 복원 결과 같은 문자열이 행 전체를 채운다 — 회사 데이터 행이 아니다.
    """
    values = {c.strip() for c in row if c.strip()}
    if len(values) == 1 and len(row) > 1:
        return values.pop().strip(" :：")
    return None


def parse_governance_html_rows(text_html: str | None) -> list[dict]:
    """행=개별회사형 거버넌스 표(KT&G·아이센스류) → [{category, counterparty}].

    IFRS 표준 공시항목 컬럼("소재지"·"소유지분율")이 모두 있는 표를 앵커로 찾아
    ROWSPAN/COLSPAN을 반영한 그리드로 복원한 뒤,
      · 회사명 컬럼 = 헤더 어휘(회사명·특수관계자명…)가 있으면 그 위치, 없으면
        소재지 바로 왼쪽(KT&G류 — 헤더가 공백인 표)
      · 카테고리 = '구분' 컬럼, 없으면 전폭 머리행(아이센스 '관계기업:')을 누적
    으로 읽는다. 카테고리 자체가 회사명 칸에 그대로 들어간 캐치올 행(KT&G "기타")·
    하위 기간 헤더 행(당기말/전기말)·전폭 머리행은 회사로 만들지 않는다.
    """
    results: list[dict] = []
    if not text_html:
        return results

    soup = BeautifulSoup(text_html, "html.parser")
    target_table = None
    for table in soup.find_all("table"):
        headers = {th.get_text(strip=True) for th in table.find_all("th")}
        if "소재지" in headers and "소유지분율" in headers:
            target_table = table
            break
    if target_table is None:
        return results

    grid = _html_table_grid(target_table)
    header_idx = _find_header_row(grid, {"소재지", "소유지분율"})
    if header_idx is None:
        return results
    header_row = grid[header_idx]

    name_col = _header_col_by_vocab(header_row, _NAME_HEADER_VOCAB)
    if name_col is None:
        # KT&G류 — 헤더 칸이 공백이라 어휘로 못 찾는다. 기존 위치 규칙 유지.
        name_col = header_row.index("소재지") - 1
    if name_col < 0:
        return results
    category_col = _category_col_by_vocab(header_row)
    if category_col is None and name_col - 1 >= 0:
        category_col = name_col - 1
    header_name_value = _collapse(header_row[name_col]) if name_col < len(header_row) else ""

    running_category = ""
    for row in grid[header_idx + 1 :]:
        if len(row) <= name_col:
            continue
        full = _is_full_width_label(row)
        if full is not None:
            running_category = full  # 전폭 머리행 — 이후 행의 카테고리
            continue
        counterparty = row[name_col].strip()
        if not counterparty:
            continue
        if _collapse(counterparty) == header_name_value:
            continue  # 헤더 rowspan 캐리다운(회사명) — 데이터 아님
        if _collapse(counterparty) in _PERIOD_SUBHEADERS:
            continue  # 하위 기간 헤더 행(당기말/전기말)
        counterparty = _strip_list_marker(counterparty)
        if not counterparty:
            continue
        category = (
            row[category_col].strip()
            if category_col is not None and category_col < len(row)
            else ""
        ) or running_category
        if not category or counterparty == category:
            continue
        results.append({"category": category, "counterparty": counterparty})
    return results


# ★ 2026-07-22 삼성전자형 — 별도 거버넌스 리스팅 표 자체가 없고, 거래금액 표의
# 컬럼 헤더(카테고리가 COLSPAN, 리프가 개별 회사명)에 카테고리 정보가 인코딩돼
# 있다. text_md 평탄화는 COLSPAN을 셀 반복으로 뭉개 위치가 흔들리므로, 마찬가지로
# text_html을 rowspan/colspan 그리드로 복원해 읽는다.
def parse_governance_transaction_header(text_html: str | None) -> list[dict]:
    """거래금액 표 컬럼 헤더에 인코딩된 카테고리(삼성전자류) → [{category, counterparty}].

    "전체 특수관계자"/"특수관계자" 보일러플레이트 헤더 행을 건너뛰고, 그 다음
    (카테고리 행, 개별회사명 행) 한 쌍을 위치로 짝짓는다. "기타 관계기업 및
    공동기업"처럼 "기타"로 시작하는 리프 컬럼은 특정 법인이 아닌 집계 컬럼이라
    제외(related_party.py 거래금액 파서의 기존 관례와 동일).
    """
    results: list[dict] = []
    if not text_html:
        return results

    soup = BeautifulSoup(text_html, "html.parser")
    target_table = None
    for table in soup.find_all("table"):
        ths = [th.get_text(strip=True) for th in table.find_all("th")]
        if "전체 특수관계자" in ths and "특수관계자" in ths:
            target_table = table
            break
    if target_table is None:
        return results

    grid = _html_table_grid(target_table)
    # ★ 2026-07-30 열 밀림 수리 (최대 산출원 — 실측 4,140건 중 3,261건이 잡음).
    # 기존 구현은 "보일러플레이트(전체 특수관계자/특수관계자) 행을 위에서부터
    # 건너뛴 첫 행 = 카테고리 행, 그 다음 = 회사명 행"으로 잡았다. 두 방향으로 깨진다:
    #   ① 합계 컬럼이 있으면(`전체 특수관계자  합계`) 그 행의 값이 2종이 되어
    #      "전부 같은 값"이라는 보일러플레이트 판정에 실패 → **한 층 위에서 멈춘다**
    #      (JW중외제약 2024: category='전체 특수관계자', counterparty='지배기업').
    #   ② 반대로 카테고리 층이 전부 보일러플레이트면 **한 층 아래로 지나쳐** 회사명
    #      행이 카테고리가 되고 데이터 행이 회사명이 된다(JW중외제약 2025 실측:
    #      category='JW홀딩스㈜', counterparty='(4,891,807)' — 리더가 본 그 화면).
    # → 위에서 세는 대신 **아래에서 잡는다**: 리프 헤더 행(첫 칸이 빈 마지막 행,
    #   parse_note_html_grid와 같은 규칙)이 회사명 행이고 그 직상단이 카테고리 행이다.
    #   층 수·합계 컬럼 유무와 무관하게 성립한다.
    # ★ 두 배치가 공존한다(실측). 마지막 헤더 층(첫 칸이 빈 마지막 행)이
    #   ① **회사명 층**인 표 — 삼성전자·JW중외제약. 그 아래는 금액 데이터 행.
    #   ② **카테고리 층**인 표 — 유한양행·롯데지주·SK리츠·하림. 회사명은 **그 아래
    #      데이터 행**에 오고(콤마 나열이 흔함), 첫 칸은 `특수관계자명`·`특수관계의
    #      성격에 대한 기술` 같은 라벨이다.
    # 라벨 어휘로 ②를 식별하려 하면 놓친다(라벨 표기가 회사마다 제각각 —
    # 실측 상장타깃 114엣지 소실). → **마지막 헤더 층의 값이 전부 K-IFRS 구분이면
    # 그 층은 카테고리 행**이라는 내용 기준으로 가른다. 회사명 층에는 반드시
    # 법인격 표기를 쓰는 실제 사명이 섞여 있으므로 "전부 구분"이 성립하지 않는다.
    # ⚠️ "마지막 헤더 층 = 회사명"도 틀린다: 회사명 층 **아래로 소항목 층이 더 쌓이는**
    # 표가 있다(JW생명과학 rcept 20260318001371 — 회사명은 3층인데 그 아래 '지급보증의
    # 구분'·'제공한 지급보증'이 더 있어 마지막 층은 6층. 제일약품은 '자산'·'토지와 건물').
    # 위치로는 어느 층인지 알 수 없으므로 **법인격 표기가 있는 마지막 헤더 층**을 고른다.
    hdr_idx = _leaf_header_index(grid)
    if hdr_idx is None:
        return results
    header_idxs = [i for i in range(hdr_idx + 1) if grid[i] and grid[i][0].strip() == ""]
    if not header_idxs:
        return results
    # ⚠️ **가장 얕은** 층을 고른다 — 소항목 층에도 법인격 표기가 나올 수 있다
    # (제일약품 실측: 회사명 층은 3층 '제일파마홀딩스(주)'인데 그 아래 담보 소항목
    # 층에 '비아트리스코리아㈜'·'신한은행'이 있어 가장 깊은 층을 고르면 담보제공처가
    # 상대회사가 된다). 특수관계자 계층은 카테고리 → 회사명 → 소항목 순이므로
    # 법인격 표기가 처음 나타나는 층이 회사명 층이다.
    name_idx = None
    for i in header_idxs:
        if any(entity_kind._CORP_MARKS.search(c) for c in grid[i][1:] if c.strip()):
            name_idx = i
            break
    if name_idx is not None and name_idx >= 1:
        category_row, name_row = grid[name_idx - 1], grid[name_idx]  # ① 회사명=헤더 층
    elif hdr_idx + 1 < len(grid):
        # ② 어느 헤더 층에도 사명이 없다 → 회사명은 **그 아래 데이터 행**에 있다
        #    (유한양행·롯데지주·SK리츠·하림·퍼시스·아시아나항공 — 콤마 나열이 흔함).
        # ⚠️ 카테고리 어휘로 "이 층이 카테고리인가"를 판정하려 했더니 표기 편차에
        #    걸려 통째로 0이 됐다(실측: '지배력이 있는 개인'·'기타(*1)'가 어휘 미등록).
        #    회사명 층이 없다는 사실 자체가 곧 "회사명은 아래에 있다"이므로 어휘를
        #    보지 않는다 — 숫자만인 칸은 아래 필터·잡음 게이트가 막는다.
        category_row, name_row = grid[hdr_idx], grid[hdr_idx + 1]
    else:
        return results
    if len(category_row) != len(name_row):
        return results

    for category, name in zip(category_row[1:], name_row[1:]):
        category = category.strip()
        name = name.strip()
        if not category or not name or name.startswith("기타"):
            continue
        # 개별 법인이 아니라 K-IFRS 구분/서술이면 회사가 아니다. 단 두 가지는 실제 사명:
        #   · 법인격 표기가 있는 것(entity_kind.is_noise의 category_label 판정과 같은 규칙)
        #   · **집계 꼬리를 뗀 나머지가 사명인 것** — `LX 하우시스 및 그 종속기업`은
        #     '종속기업'을 품어 구분처럼 보이지만 대표사가 실존 상장사다(실측: 이 조건을
        #     빼면 LX인터내셔널→LX하우시스·LX세미콘 2엣지가 소실).
        probe = strip_group_aggregate(name) or name
        if _is_category_column(probe) and not entity_kind._CORP_MARKS.search(probe):
            continue
        if _DASH_ONLY_RE.match(name) or _RATIO_ONLY_RE.match(name):
            continue  # 금액·지분율 칸 — 회사명 층이 아니다
        results.append({"category": category, "counterparty": name})
    return results


# ★ 2026-07-22 두산 캐리포워드형 — "구분/당기말/전기말/비고" 4컬럼, 카테고리가
# ROWSPAN으로 그룹 첫 행에만 붙고 이후 행은 라벨 없이 이어진다(KT&G와 같은
# ROWSPAN 캐리포워드 유형, 컬럼 구성만 다름). 스냅샷 원칙(latest_relation_local_
# edges와 동일 사상)에 따라 **당기말 컬럼만** 채택 — 전기말은 그 회사 전년도
# 보고서 자체의 당기말 블록에서 이미 잡히므로 중복(module docstring 상단 참조).
_DASH_ONLY_RE = re.compile(r"^[-−―–—\s]+$")
_RATIO_ONLY_RE = re.compile(r"^[\d,.\s%]+$")


def parse_governance_carryforward(text_html: str | None) -> list[dict]:
    """당기말/전기말형 거버넌스 표(두산·일신방직류) → [{category, counterparty}].

    ★ 2026-07-30 열 밀림 수리 — **두 가지 표가 같은 헤더를 쓴다.**
      · 두산류: `구분 | 당기말 | 전기말 | 비고` — 당기말 칸에 **회사명**이 들어간다.
      · 일신방직·현대코퍼레이션홀딩스·HL D&I류: `구분 | 특수관계자명 | … | 당기말 |
        전기말` — 당기말/전기말은 **지분율 컬럼의 하위 헤더**이고 회사명은 별도 칸이다.
    기존 구현은 전자만 가정해 후자에서 지분율을 회사명으로 읽었다(실측: `48.54%`·
    `23.99%`·`23.78`이 노드 후보로, 진짜 회사명 `㈜지오다노`·`현대코퍼레이션(주)`·
    `에이치엘홀딩스 주식회사`는 detail에만 남음). → 회사명 컬럼이 헤더에 **있으면
    그것을 쓰고**, 당기말은 신선도 판정(처분 여부)에만 쓴다.

    신선도(D13·후속14 오류1 "처분 부활"과 같은 사상): 당기말이 비었/대시인데
    전기말에 값이 있으면 **당기 중 이탈**이므로 스킵한다. 양쪽 다 대시인 행은
    지분율이 공시되지 않은 것일 뿐이므로(HL D&I의 계열 종속기업 나열) 유지한다.
    """
    results: list[dict] = []
    if not text_html:
        return results

    soup = BeautifulSoup(text_html, "html.parser")
    target_table = None
    for table in soup.find_all("table"):
        ths = {th.get_text(strip=True) for th in table.find_all("th")}
        if {"구분", "당기말", "전기말"} <= ths:
            target_table = table
            break
    if target_table is None:
        return results

    grid = _html_table_grid(target_table)
    header_idx = _find_header_row(grid, {"구분", "당기말"})
    if header_idx is None:
        return results
    header_row = grid[header_idx]
    category_col = header_row.index("구분")
    current_col = header_row.index("당기말")
    prev_col = header_row.index("전기말") if "전기말" in header_row else None

    # 회사명 전용 컬럼이 있으면 그쪽이 상대회사다(당기말은 지분율).
    name_col = _header_col_by_vocab(header_row, _NAME_HEADER_VOCAB)
    if name_col == category_col:
        name_col = None
    ratio_style = name_col is not None
    if name_col is None:
        name_col = current_col  # 두산류 — 당기말 칸이 회사명

    for row in grid[header_idx + 1 :]:
        needed = [c for c in (category_col, name_col, current_col) if c is not None]
        if len(row) <= max(needed):
            continue
        category = row[category_col].strip()
        counterparty = row[name_col].strip()
        if not category or not counterparty or counterparty == category:
            continue
        if _is_full_width_label(row) is not None:
            continue  # 전폭 머리행 — 회사 데이터 아님
        current = row[current_col].strip()
        prev = row[prev_col].strip() if prev_col is not None and prev_col < len(row) else ""
        if ratio_style:
            # 회사명은 별도 칸에서 읽었으므로 당기말은 신선도 판정에만 쓴다.
            if (not current or _DASH_ONLY_RE.match(current)) and _RATIO_ONLY_RE.match(
                prev or ""
            ) and any(ch.isdigit() for ch in prev):
                continue  # 당기 중 처분 — 끝난 관계를 현재처럼 노출하지 않는다
            if counterparty == current:
                continue  # COLSPAN 캐리(그룹 머리행)
        else:
            # 두산류 — 당기말 칸 자체가 회사명. 대시/숫자만이면 회사가 아니다.
            if _DASH_ONLY_RE.match(counterparty) or _RATIO_ONLY_RE.match(counterparty):
                continue
        counterparty = _strip_list_marker(counterparty)
        if not counterparty:
            continue
        results.append({"category": category, "counterparty": counterparty})
    return results


def _upsert_edge(session, **fields) -> None:
    """UNIQUE(src_corp, dst_corp, edge_type, as_of, rcept_no) upsert (D12 멱등)."""
    key = {
        "src_corp": fields["src_corp"],
        "dst_corp": fields["dst_corp"],
        "edge_type": fields["edge_type"],
        "as_of": fields["as_of"],
        "rcept_no": fields["rcept_no"],
    }
    existing = session.query(ValueChainEdge).filter_by(**key).one_or_none()
    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
        existing.status = "active"
    else:
        session.add(ValueChainEdge(**fields, status="active"))


def apply(
    session=None, sections: list[dict] | None = None, prune: bool | None = None
) -> dict:
    """특수관계자 주석 전량 스캔 → ValueChainEdge(T1) upsert.

    session: 주입 시 그 세션 사용(테스트용 — 닫지 않음, 커밋은 호출). None이면 로컬 relation.db.
    sections: 주입 시 reports.db 대신 이 리스트 사용(테스트용 — 실 파일 접근 회피).
              None이면 reports_source.fetch_rp_note_sections() 전량(U-확대 접두 규칙).
    prune: **이 함수가 만드는 rp_note VCE의 stale 정리는 생산자인 이 함수 소관**
      (transform/CLAUDE.md "prune은 생산자 소관"의 rp_note 판 — 2026-07-30 신설).
      없던 시절 과거 코드 세대가 만든 행이 그대로 남아 **이미 삭제된 비상장 노드
      uid를 가리키는 dangling 참조 112건**이 누적돼 있었다(전수 검증에서 발견,
      전부 rp_note·T1·과거연도). apply_governance와 동일 규율 — 전량 스캔일 때만
      이번 파스에 없는 rp_note 행을 정리하고, 부분 주입(테스트)은 미정리.

    링킹은 방어 5층 중 L1(약칭 게이트+화이트리스트)·L2(쌍 블록리스트)·L5(LinkFailQueue)
    적용 — corp_code 없는 이름-only 원천의 공통 요건(transform/CLAUDE.md, 2026-07-29
    전 상장사 확대 시 연결). L3·L4는 지분율 원천 전용이라 비대상.

    Returns: {'notes_scanned', 'notes_unparsed', 'edges_kept', 'link_failed',
              'l1_ambiguous_queued', 'l2_blocklisted', 'pruned_stale'}
    """
    owns_session = session is None
    if owns_session:
        session = get_local_session()

    if prune is None:
        prune = sections is None
    if sections is None:
        sections = reports_source.fetch_rp_note_sections()

    counters = {
        "notes_scanned": 0,
        "notes_unparsed": 0,
        "edges_kept": 0,
        "group_aggregate": 0,
        "unlisted_nodes": 0,
        "pruned_stale": 0,
    }
    touched_vce: set[tuple] = set()
    try:
        ctx = build_guard_context(session)

        for row in sections:
            counters["notes_scanned"] += 1
            self_corp = row["corp_code8"]
            rcept_no = row["rcept_no"]
            as_of = row["fiscal_year"]

            note_items = parse_note(row["text_md"])
            if not note_items:
                # 행=거래유형 구조가 아예 없는 노트(전치형, 하나금융지주·
                # LIG디펜스앤에어로스페이스류)에 한해서만 폴백 — 이미 잡힌
                # 노트를 이중으로 다시 읽지 않도록 방지(U3와 동일 관례).
                note_items = parse_note_transposed(row.get("text_html"))
            if not note_items:
                # ★2026-07-29 U-확대: markdown COLSPAN 유실로 열 정렬이 깨진
                # 계층 헤더 표(전체 미파싱의 54%) — 원본 HTML 그리드로 재독.
                # markdown 경로가 성공한 노트는 그 결과를 유지한다(G-C 검수를
                # 통과한 기존 동작 보존, 두 경로 불일치 84건은 후속 조사 과제).
                note_items = parse_note_html_grid(row.get("text_html"))
            if not note_items:
                # 미지원 표 구조 — 억지 매칭 금지, 스킵 집계만(유형 분류는
                # 별도 조사 스크립트 소관, 파서 분기 신설은 fixture 필수)
                counters["notes_unparsed"] += 1
                continue
            for item in note_items:
                corp_code = link_counterparty(
                    session, ctx, item["counterparty"], chunk_id=rcept_no
                )
                # 원문이 안 붙으면 그룹 집계 표현인지 보고 대표사로 재시도
                # (리더 판정 — 붙이되 provenance에 "그룹 합산" 명시)
                is_aggregate = False
                if not corp_code:
                    base = strip_group_aggregate(item["counterparty"])
                    if base:
                        corp_code = link_counterparty(
                            session, ctx, base, chunk_id=rcept_no
                        )
                        is_aggregate = bool(corp_code)
                if not corp_code:
                    # ★U5: 상장사로 못 붙으면 비상장 노드로 (앵커-로컬, 원문 그대로)
                    self_ticker = ctx.ticker_by_corp.get(self_corp)
                    if self_ticker:
                        corp_code = entity_kind.upsert_unlisted_node(
                            session,
                            anchor_corp=self_ticker,
                            name_raw=item["counterparty"],
                            relate=None,
                            provenance=f"rp_note:{rcept_no}",
                        )
                        if corp_code:
                            counters["unlisted_nodes"] += 1
                if not corp_code:
                    continue  # 잡음이거나 앵커 미상 — ctx.counters에 집계됨
                if corp_code == self_corp:
                    continue  # 자기 자신 표기(연결실체 자기 참조) 무시

                if item["direction"] == "customer":
                    src_corp, dst_corp = self_corp, corp_code
                else:
                    src_corp, dst_corp = corp_code, self_corp

                if blocked_pair(ctx, src_corp, dst_corp):
                    ctx.counters["l2_blocklisted"] += 1
                    continue

                provenance = f"{row['title']} · {item['label']}"
                if is_aggregate:
                    provenance += f" · {GROUP_AGGREGATE_MARK}"
                    counters["group_aggregate"] += 1
                _upsert_edge(
                    session,
                    src_corp=src_corp,
                    dst_corp=dst_corp,
                    edge_type=item["direction"],
                    tier="T1",
                    source_kind="rp_note",
                    rcept_no=rcept_no,
                    provenance=provenance,
                    amount=item["amount"],
                    as_of=as_of,
                )
                touched_vce.add(
                    (src_corp, dst_corp, item["direction"], as_of, rcept_no)
                )
                counters["edges_kept"] += 1

        if prune:
            # 생산자 소관 prune — 이번 전량 파스에 없는 rp_note 행은 stale이다.
            # (없던 시절 누적된 dangling uid 참조 112건이 이 정리로 사라진다)
            for e in session.query(ValueChainEdge).filter_by(source_kind="rp_note").all():
                key = (e.src_corp, e.dst_corp, e.edge_type, e.as_of, e.rcept_no)
                if key not in touched_vce:
                    session.delete(e)
                    counters["pruned_stale"] += 1
            session.flush()
            entity_kind.prune_orphan_unlisted_nodes(session)
        session.commit()
    finally:
        if owns_session:
            session.close()

    counters["link_failed"] = ctx.counters["link_failed"]
    counters["l1_ambiguous_queued"] = ctx.counters["l1_ambiguous_queued"]
    counters["l2_blocklisted"] = ctx.counters["l2_blocklisted"]
    logger.info(f"related_party.apply 결과: {counters}")
    return counters


# ★ 2026-07-29 실측: 거버넌스 표의 회사명 칸에 여러 법인이 콤마로 나열되는 경우가 있다
# ("한국수력원자력(주), 한국남동발전(주), …", "기아㈜, 현대제철㈜, 현대글로비스㈜ 등").
# parse_governance_categories()는 콤마 분리를 하지만 **HTML 기반 3종(html_rows·
# carryforward·transaction_header)과 wide_row는 안 해서** 통째로 링킹 실패했다 —
# 71표기 안에 상장사 116건이 묻혀 있었다.
#
# ⚠️ 거래금액 파서(apply)에는 적용하지 않는다 — 금액이 딸린 항목을 쪼개면 같은 금액이
# 여러 상대에 중복 귀속된다(과대계상). 거버넌스는 금액이 없어 분할이 안전하다.
# ⚠️ 외국 법인명의 "Co., Ltd." 콤마를 잘못 쪼갤 수 있으므로 **원문 링킹을 먼저 시도**하고
# 실패했을 때만 분할한다(기존 파서 폴백 관례와 동일 — 이미 잡힌 것을 흔들지 않는다).
def split_multi_counterparties(name: str) -> list[str]:
    """콤마 나열형 회사명 칸 → 개별 법인 후보. 분리 지점이 없으면 빈 리스트.

    ★ 2026-07-30: 자체 정규식 분할을 `split_company_list`로 교체 — 괄호 안 콤마를
    쪼개거나 `Co., Ltd.`를 조각내던 문제를 한 곳에서 해소한다(분할 규칙 1벌).
    """
    return [p for p in split_company_list(name) if len(p.strip(" ()")) >= 2]


# ★ 2026-07-29 리더(CPA) 판정: 그룹 집계 표현도 대표사 엣지로 붙이되 **"그룹 합산"을
# 명시**한다. 근거: "지배기업이 회사 단일로 지배하는 것은 아니다" — 관계 자체는 사실이고,
# 금액이 그룹 합산이라는 점을 표기로 밝히면 오해가 없다. 지배구조·밸류체인 양쪽 공통 적용.
#
# 원문 형태(LG화학 2025 주석 실측): 회사명 칸에 꼬리가 붙어 통째로 링킹 실패했다.
#   | 대규모기업집단 | 엘지디스플레이㈜와 종속기업 | 340,980 | …   ← 매출 3,409억
#   | 그 밖의 특수관계자 | ㈜엘지씨엔에스와 그 종속기업 | 43,632 | …
# 같은 표의 "㈜테크윈"·"한국전구체 주식회사"는 평이한 사명이라 정상 링킹된다 —
# 즉 `와 종속기업` 꼬리 하나가 유일한 차단 요인이었다.
_GROUP_AGGREGATE_RE = re.compile(
    r"\s*(?:(?:및|와|과)\s*(?:그\s*)?[^,]*?(?:종속|계열|자회사|공동기업|관계기업)[^,]*"
    r"|등(?:\s+[^,]*?(?:기업집단|계열회사|소속회사|소속)[^,]*)?)\s*$"
)
GROUP_AGGREGATE_MARK = "그룹 합산"


def strip_group_aggregate(name: str) -> str | None:
    """'X와 그 종속기업' → 'X'. 집계 꼬리가 없으면 None(변형 없음).

    꼬리는 **연결어(및·와·과·등) 뒤**에 올 때만 인정한다 — '현대종속기업개발' 같은
    정상 사명을 깎아내지 않기 위함(실측 확인).
    """
    if not name:
        return None
    base = _GROUP_AGGREGATE_RE.sub("", name).strip(" ,·")
    return base if base and base != name.strip() else None


def _upsert_relation_local_dart_filing(session, **fields) -> None:
    """UNIQUE(source_corp, target_corp, source_type, bsns_year) upsert — transform/filters.py
    의 동일 패턴 준용(U-D13 멱등 키). source_type은 항상 "dart_filing"."""
    key = {
        "source_corp": fields["source_corp"],
        "target_corp": fields["target_corp"],
        "source_type": "dart_filing",
        "bsns_year": fields.get("bsns_year"),
    }
    existing = session.query(RelationLocal).filter_by(**key).one_or_none()
    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
        existing.status = "active"
    else:
        session.add(RelationLocal(**fields, source_type="dart_filing", status="active"))


def apply_governance(
    session=None, sections: list[dict] | None = None, prune: bool | None = None
) -> dict:
    """특수관계자 주석의 거버넌스 카테고리 표(2-컬럼 나열형 + 와이드 1행형) →
    RelationLocal(dart_filing) upsert.

    U-D2 "파서 1벌, 소비자 2곳" — apply()와 같은 sections 입력을 받아 같은 노트에서
    다른 표(거래금액이 아니라 카테고리 리스팅)를 뽑아 거버넌스 레이어에 반영한다.
    U1(DART hyslrSttus/otrCprInvstmntSttus)가 이미 포착한 지분관계와 다른 source_type
    (dart_filing)이라 레이어 공존 원칙(같은 쌍이라도 source_type이 다르면 별도 행)에
    따라 중복 없이 공존한다 — U1 미포착분(지분 없는 "기타" 특수관계 등)을 보완.

    RelationLocal.source_corp/target_corp는 ticker(6자리)라 corp_code(8자리)를 변환
    해야 한다 — CompanyRegistry에서 corp_code→ticker 매핑을 구축.

    ★ prune (2026-07-29, 소실 사고 후 신설): dart_filing 행의 stale 정리는 **이
    함수(생산자)의 소관**이다 — filters.apply()의 prune 스코프에 dart_filing이
    들어 있던 시절, 이 함수가 적재한 행 전체(115엣지·7개사)가 RelationRaw에 없다는
    이유로 transform 재실행 때마다 오인 삭제됐다(발견 2026-07-29). 전량 스캔
    (sections=None)일 때만 이번 실행에서 안 만져진 dart_filing 행을 정리한다 —
    부분 주입 실행(테스트 등)은 스캔 밖 행을 지우면 안 되므로 기본 미정리
    (prune=True로 강제 가능, 테스트용).

    Returns: {'notes_scanned', 'notes_unparsed', 'edges_kept', 'link_failed',
              'l1_ambiguous_queued', 'l2_blocklisted', 'no_ticker', 'pruned_stale'}
    """
    owns_session = session is None
    if owns_session:
        session = get_local_session()

    if prune is None:
        prune = sections is None
    if sections is None:
        sections = reports_source.fetch_rp_note_sections()

    counters = {
        "notes_scanned": 0,
        "notes_unparsed": 0,
        "edges_kept": 0,
        "group_aggregate": 0,
        "unlisted_nodes": 0,
        "no_ticker": 0,
        "pruned_stale": 0,
        "pruned_orphan_nodes": 0,
        "kind_reconciled": 0,
    }
    touched_keys: set[tuple] = set()
    try:
        ctx = build_guard_context(session)
        ticker_by_corp_code = ctx.ticker_by_corp

        for row in sections:
            counters["notes_scanned"] += 1
            self_corp_code = row["corp_code8"]
            self_ticker = ticker_by_corp_code.get(self_corp_code)
            if not self_ticker:
                counters["no_ticker"] += 1
                continue
            rcept_no = row["rcept_no"]
            as_of = row["fiscal_year"]

            governance_items = (
                parse_governance_categories(row["text_md"])
                + parse_governance_wide_row(row["text_md"])
                + parse_governance_html_rows(row.get("text_html"))
                + parse_governance_carryforward(row.get("text_html"))
            )
            if not governance_items:
                # 별도 거버넌스 리스팅 표가 아예 없는 노트(삼성전자류)에 한해서만
                # 거래금액 표 컬럼 헤더에서 폴백 추출 — 이미 위에서 잡힌 노트에
                # 같은 표를 이중으로 다시 읽어 detail을 덮어쓰지 않도록 방지.
                governance_items = parse_governance_transaction_header(
                    row.get("text_html")
                )
            if not governance_items:
                counters["notes_unparsed"] += 1
                continue
            for item in governance_items:
                # ★2026-07-30 순서 변경 (후속14 잔여 2): 분할을 **비상장 노드 생성
                # 前으로** 당긴다. 이전에는 분할 조각 중 **상장사만** 회수하고 나머지는
                # 버렸고, 하나도 안 붙으면 칸 전체가 노드 1개가 됐다 — 한 칸에 최대
                # 114개사가 뭉쳐(한국전력공사 3,662자·OCI 127표지) **노드 하나가 계열
                # 전체를 대표하고 kind도 오분류**됐다(실측 뭉침 후보 1,565·콤마형 1,282).
                # 이제 조각별로 상장 링킹 → 그룹집계 대표사 → 비상장 노드를 각각 시도한다.
                # ⚠️ 거버넌스 전용 — 거래금액 경로(apply)에는 적용하지 않는다(원칙 ③:
                #    금액이 딸린 칸을 쪼개면 같은 금액이 여러 상대에 중복 귀속된다).
                # ⚠️ 원문 우선 불변 — 원문이 링킹되면 분할하지 않는다('가나, 다라 주식회사').
                surfaces: list[tuple[str, bool]] = []  # (corp_or_uid, is_aggregate)

                def _resolve(surface: str, allow_unlisted: bool) -> None:
                    got = link_counterparty(session, ctx, surface, chunk_id=rcept_no)
                    if got:
                        surfaces.append((got, False))
                        return
                    base = strip_group_aggregate(surface)
                    if base:
                        got = link_counterparty(session, ctx, base, chunk_id=rcept_no)
                        if got:
                            surfaces.append((got, True))
                            return
                    if not allow_unlisted:
                        return
                    # ★U5: 상장사로 못 붙으면 비상장 노드로 (앵커-로컬, 원문 그대로)
                    uid = entity_kind.upsert_unlisted_node(
                        session,
                        anchor_corp=self_ticker,
                        name_raw=surface,
                        relate=None,
                        provenance=f"dart_filing:{rcept_no}",
                    )
                    if uid:
                        surfaces.append((uid, False))
                        counters["unlisted_nodes"] += 1

                whole = item["counterparty"]
                pieces = split_multi_counterparties(whole)
                if pieces:
                    # 분리 지점이 있으면 원문 링킹을 먼저 시도(원문 우선), 실패 시 조각별
                    _resolve(whole, allow_unlisted=False)
                    if not surfaces:
                        for piece in pieces:
                            _resolve(piece, allow_unlisted=True)
                if not surfaces:
                    _resolve(whole, allow_unlisted=True)
                if not surfaces:
                    continue  # 잡음 — ctx.counters에 집계됨
                counters["group_aggregate"] += sum(1 for _, agg in surfaces if agg)

                seen_surfaces: set[str] = set()
                for corp, is_aggregate in surfaces:
                    if corp in seen_surfaces:
                        continue  # 순서 보존 중복 제거
                    seen_surfaces.add(corp)
                    if corp == self_corp_code:
                        continue
                    # 비상장 노드 uid는 그대로 target, 상장사는 corp_code→ticker 변환
                    if corp.startswith("x_"):
                        target_ticker = corp
                    else:
                        target_ticker = ticker_by_corp_code.get(corp)
                    if not target_ticker:
                        counters["no_ticker"] += 1
                        continue
                    if blocked_pair(ctx, self_corp_code, corp):
                        ctx.counters["l2_blocklisted"] += 1
                        continue

                    detail = f"사업보고서 주석: {item['category']}"
                    if is_aggregate:
                        # ⚠️ rl-string은 `이름:타입:detail` 3분할 계약(FN-010) —
                        # 마커에 콜론을 쓰지 않는다.
                        detail += f" ({GROUP_AGGREGATE_MARK})"
                    _upsert_relation_local_dart_filing(
                        session,
                        source_corp=self_ticker,
                        target_corp=target_ticker,
                        relation_type="dart_filing",
                        ratio=None,
                        detail=detail,
                        bsns_year=as_of,
                    )
                    touched_keys.add((self_ticker, target_ticker, "dart_filing", as_of))
                    counters["edges_kept"] += 1

        if prune:
            stale = (
                session.query(RelationLocal).filter_by(source_type="dart_filing").all()
            )
            for r in stale:
                key = (r.source_corp, r.target_corp, r.source_type, r.bsns_year)
                if key not in touched_keys:
                    session.delete(r)
                    counters["pruned_stale"] += 1

        # ★U5: 엣지가 사라진 비상장 노드 정리 (참조 무결성 기준)
        session.flush()
        counters["pruned_orphan_nodes"] = entity_kind.prune_orphan_unlisted_nodes(session)
        counters["kind_reconciled"] = entity_kind.reconcile_unlisted_kinds(session)

        session.commit()
    finally:
        if owns_session:
            session.close()

    counters["link_failed"] = ctx.counters["link_failed"]
    counters["l1_ambiguous_queued"] = ctx.counters["l1_ambiguous_queued"]
    counters["l2_blocklisted"] = ctx.counters["l2_blocklisted"]
    logger.info(f"related_party.apply_governance 결과: {counters}")
    return counters


if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print(json.dumps(apply(), ensure_ascii=False, indent=2))
    print(json.dumps(apply_governance(), ensure_ascii=False, indent=2))
