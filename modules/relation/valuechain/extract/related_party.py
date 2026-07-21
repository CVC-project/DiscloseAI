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

from modules.relation.storage.db import get_local_session
from modules.relation.storage.models import ValueChainEdge
from modules.relation.valuechain.extract import reports_source
from modules.relation.valuechain.extract.linking import build_name_to_corp_map, resolve_corp

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
_SALES_LABEL_PREFIXES = ("매출", "수익거래")
_PURCHASE_LABEL_PREFIXES = ("매입", "비용거래")


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


def apply(session=None, sections: list[dict] | None = None) -> dict:
    """특수관계자 주석 전량 스캔 → ValueChainEdge(T1) upsert.

    session: 주입 시 그 세션 사용(테스트용 — 닫지 않음, 커밋은 호출). None이면 로컬 relation.db.
    sections: 주입 시 reports.db 대신 이 리스트 사용(테스트용 — 실 파일 접근 회피).
              None이면 reports_source.fetch_sections_by_title(NOTE_TITLES) 호출.

    Returns: {'notes_scanned', 'edges_kept', 'link_failed'}
    """
    owns_session = session is None
    if owns_session:
        session = get_local_session()

    if sections is None:
        sections = reports_source.fetch_sections_by_title(NOTE_TITLES)

    counters = {"notes_scanned": 0, "edges_kept": 0, "link_failed": 0}
    try:
        name_to_corp = build_name_to_corp_map(session)

        for row in sections:
            counters["notes_scanned"] += 1
            self_corp = row["corp_code8"]
            rcept_no = row["rcept_no"]
            as_of = row["fiscal_year"]

            for item in parse_note(row["text_md"]):
                corp_code = resolve_corp(
                    item["counterparty"], name_to_corp, session, sample_chunk_id=rcept_no
                )
                if not corp_code:
                    counters["link_failed"] += 1
                    continue
                if corp_code == self_corp:
                    continue  # 자기 자신 표기(연결실체 자기 참조) 무시

                if item["direction"] == "customer":
                    src_corp, dst_corp = self_corp, corp_code
                else:
                    src_corp, dst_corp = corp_code, self_corp

                _upsert_edge(
                    session,
                    src_corp=src_corp,
                    dst_corp=dst_corp,
                    edge_type=item["direction"],
                    tier="T1",
                    source_kind="rp_note",
                    rcept_no=rcept_no,
                    provenance=f"{row['title']} · {item['label']}",
                    amount=item["amount"],
                    as_of=as_of,
                )
                counters["edges_kept"] += 1
        session.commit()
    finally:
        if owns_session:
            session.close()

    logger.info(f"related_party.apply 결과: {counters}")
    return counters


if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print(json.dumps(apply(), ensure_ascii=False, indent=2))
