"""fs_parse.py — 사업보고서 원문 XML의 **재무제표 본표**를 규칙 파싱 → fs_account_xml.

배경: [FS_PARSE_PLAN.md](FS_PARSE_PLAN.md) (D안) · [integration/DECISIONS.md](../../integration/DECISIONS.md) FN-025.
`fs_enrich.py`가 DART API 재호출이라 55사에 머문 반면, 원문 XML은 이미 2,590사·27GB가 로컬에 있다.

**LLM 미사용(D7)** — 정규식·우선순위 규칙만. 파생·합산 금지, 0 채움 금지.
기존 `fs_account`(DART API 산출 = 정답지)는 **읽지도 쓰지도 않는다** — 별도 테이블에 적재한다.

## 설계 요지 (실측 근거는 FS_PARSE_PLAN §7)

- 본표 셀은 **XBRL 태깅**되어 있어 `ACODE`가 DART API의 `account_id`와 같다 → 1순위는 표준계정ID.
  단 **FY2023 보고서는 ACODE가 없다**(실측 0/54) → 계정명 매칭이 필수 폴백.
- 원문 형식 2종: 신형식(FY2023~, `<TITLE>2-1. 연결 재무상태표</TITLE>` + `<TE>`)과
  구형식(FY2021·22, `<TABLE-GROUP ACLASS="{XBRL}BS">` + `<TD><P>`).
- 한 보고서에 **당기·전기·전전기 3열**. 당기 열 연도 == 보고서 사업연도(실측 161/161).
  **전전기 열은 재작성값일 수 있으므로** 소비 시 `col_kind` 오름차순(당기 우선)으로 접는다.
- 단위 3종(원·천원·백만원) → 표마다 읽어 원 단위로 스케일링.
- 음수는 **괄호**가 정본(`ANEGATED` 속성은 신뢰 불가 — 괄호인데 `N`인 셀 실측).

## FN-025 재발 방지

계정명 별칭을 **first-wins로 훑지 않는다**. 규칙마다 순위(rank)를 매기고 **전 후보를 모은 뒤
정렬해서 최상위 1건**만 채택한다(`pick_account`). `이자수익`·`수수료수익`·`보험수익`은
revenue 별칭에서 **제외** — 금융업 top line은 `영업수익`(ifrs-full_Revenue)이 담당한다.

실행: `python -m modules.report.fs_parse --tickers 005930,035720`
      `python -m modules.report.fs_parse --pilot`  (fs_account 보유 55사)
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Iterable, NamedTuple

from .db import get_local_session, init_local_db
from .models import FsAccountXml, ReportRaw

if hasattr(sys.stdout, "reconfigure"):  # cp949 콘솔 크래시 방지
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_HERE = os.path.dirname(__file__)
RAW_DIR = os.path.join(_HERE, "data", "raw_cache")

# ── 계정 우선순위 규칙 (FN-025: 순위 정렬 후 최상위 1건) ────────────────────────
# 각 항목: (rank, kind, values). kind='code'는 ACODE/account_id 정확 일치,
# 'name'은 정규화된 계정명 정확 일치. rank가 작을수록 우선.
CODE, NAME = "code", "name"

ACCOUNT_RULES: dict[str, list[tuple[int, str, frozenset[str]]]] = {
    "revenue": [
        (1, CODE, frozenset({"ifrs-full_Revenue"})),
        (2, CODE, frozenset({"dart_Revenue", "ifrs_Revenue"})),
        # ⚠️ 이자수익·수수료수익·보험수익은 넣지 않는다 (FN-025).
        (3, NAME, frozenset({"매출액", "수익(매출액)", "영업수익", "매출",
                             "영업수익(매출액)", "매출액(영업수익)", "매출및지분법손익",
                             "매출수익", "영업수익합계", "매출액합계", "수익"})),
    ],
    "cogs": [
        (1, CODE, frozenset({"ifrs-full_CostOfSales"})),
        (2, NAME, frozenset({"매출원가", "매출원가(영업비용)", "매출원가합계"})),
    ],
    "operating_income": [
        (1, CODE, frozenset({"dart_OperatingIncomeLoss"})),
        (2, CODE, frozenset({"ifrs-full_ProfitLossFromOperatingActivities"})),
        (3, NAME, frozenset({"영업이익", "영업이익(손실)", "영업손익",
                             "영업손실", "영업이익(영업손실)", "영업손실(영업이익)"})),
    ],
    "net_income": [
        (1, CODE, frozenset({"ifrs-full_ProfitLoss"})),
        (2, NAME, frozenset({"당기순이익", "당기순이익(손실)", "당기순손익",
                             "당기순손실", "연결당기순이익", "당기순이익(당기순손실)"})),
    ],
    "total_assets": [
        (1, CODE, frozenset({"ifrs-full_Assets"})),
        (2, NAME, frozenset({"자산총계", "자산합계", "자산계", "자산"})),
    ],
    "total_liabilities": [
        (1, CODE, frozenset({"ifrs-full_Liabilities"})),
        (2, NAME, frozenset({"부채총계", "부채합계", "부채계", "부채"})),
    ],
    "total_equity": [
        (1, CODE, frozenset({"ifrs-full_Equity"})),
        (2, NAME, frozenset({"자본총계", "자본합계", "자본계", "자본"})),
    ],
    "current_assets": [
        (1, CODE, frozenset({"ifrs-full_CurrentAssets"})),
        (2, NAME, frozenset({"유동자산", "유동자산합계", "유동자산계"})),
    ],
    "current_liabilities": [
        (1, CODE, frozenset({"ifrs-full_CurrentLiabilities"})),
        (2, NAME, frozenset({"유동부채", "유동부채합계", "유동부채계"})),
    ],
    "long_term_debt": [  # = 비유동부채 (financial/collector.py와 동일 규약)
        (1, CODE, frozenset({"ifrs-full_NoncurrentLiabilities"})),
        (2, NAME, frozenset({"비유동부채", "비유동부채합계", "비유동부채계"})),
    ],
    "operating_cashflow": [
        (1, CODE, frozenset({"ifrs-full_CashFlowsFromUsedInOperatingActivities"})),
        # ⚠️ '영업에서창출된현금'(CashFlowsFromUsedInOperations)은 소계라 제외.
        (2, NAME, frozenset({"영업활동현금흐름", "영업활동으로인한현금흐름",
                             "영업활동으로인한순현금흐름", "영업활동순현금흐름",
                             "영업활동으로부터의현금흐름", "영업활동으로인한현금흐름액",
                             "영업활동으로인한자금수지", "영업활동으로인한순현금흐름액"})),
    ],
    "investing_cashflow": [
        (1, CODE, frozenset({"ifrs-full_CashFlowsFromUsedInInvestingActivities"})),
        (2, NAME, frozenset({"투자활동현금흐름", "투자활동으로인한현금흐름",
                             "투자활동으로인한순현금흐름", "투자활동순현금흐름",
                             "투자활동으로부터의현금흐름", "투자활동으로인한현금흐름액",
                             "투자활동으로인한자금수지", "투자활동으로인한순현금흐름액"})),
    ],
    "financing_cashflow": [
        (1, CODE, frozenset({"ifrs-full_CashFlowsFromUsedInFinancingActivities"})),
        (2, NAME, frozenset({"재무활동현금흐름", "재무활동으로인한현금흐름",
                             "재무활동으로인한순현금흐름", "재무활동순현금흐름",
                             "재무활동으로부터의현금흐름", "재무활동으로인한현금흐름액",
                             "재무활동으로인한자금수지", "재무활동으로인한순현금흐름액"})),
    ],
}

# 계정이 실릴 수 있는 재무제표(우선순위 순). 자본총계를 SCE에서 줍지 않기 위한 방어이기도 하다.
SJ_PREF: dict[str, tuple[str, ...]] = {
    "revenue": ("IS", "CIS"),
    "cogs": ("IS", "CIS"),
    "operating_income": ("IS", "CIS"),
    "net_income": ("IS", "CIS"),
    "total_assets": ("BS",),
    "total_liabilities": ("BS",),
    "total_equity": ("BS",),
    "current_assets": ("BS",),
    "current_liabilities": ("BS",),
    "long_term_debt": ("BS",),
    "operating_cashflow": ("CF",),
    "investing_cashflow": ("CF",),
    "financing_cashflow": ("CF",),
}

ACCOUNT_KEYS = tuple(ACCOUNT_RULES)

# ── 부정 이름 가드 (FN-025 "조건 없는 별칭 금지"의 읽기 측 판본) ────────────────
# 표준계정ID가 맞아도 **이 문자열이 계정명에 있으면 그 키가 아니다**.
# 실측 근거: 두산 000150 FY2021 원문은 `투자활동으로 인한 현금유입액` 행에
# `ifrs-full_CashFlowsFromUsedInInvestingActivities`를 붙였고(원문 XBRL 오태깅),
# 진짜 순현금흐름 행은 `-표준계정코드 미사용-`이다. 코드만 믿으면 유입액(+2.47조)을
# 순현금흐름(-0.32조) 자리에 넣는다 — DART API 정답지도 같은 함정에 빠져 있다.
NAME_EXCLUDE: dict[str, tuple[str, ...]] = {
    "operating_cashflow": ("유입", "유출"),
    "investing_cashflow": ("유입", "유출"),
    "financing_cashflow": ("유입", "유출"),
    "revenue": ("이자수익", "수수료수익", "보험수익", "금융수익", "기타수익"),
}

# 부호 규약 — 원문의 괄호는 '차감 표시'지 음수 값이 아니다. 매출원가를 괄호로 싣는
# 회사와 양수로 싣는 회사가 갈리는데(실측 24건), DART API 정본은 항상 양수다.
# ⚠️ 파생·합산이 아니라 **표기 정규화**다. 값 자체는 원문 그대로.
SIGN_ABS = frozenset({"cogs"})

# ── 원문 마크업 상수 (실측 근거: FS_PARSE_PLAN §7.2) ───────────────────────────
# 신형식: <TITLE>2-1. 연결 재무상태표</TITLE> / <TITLE>4-2. 포괄손익계산서</TITLE>
_FS_TITLE_RE = re.compile(
    r"<TITLE[^>]*>\s*\d+\s*[-.]\s*\d+\s*\.?\s*"
    r"((?:연결\s*)?(?:재무상태표|대차대조표|포괄손익계산서|손익계산서|현금흐름표|자본변동표))"
    # 병기 괄호 허용 — KB금융 등은 `2-1. 연결 재무상태표(대차대조표)`로 쓴다.
    r"\s*(?:\([^<)]{0,20}\))?\s*</TITLE>",
    re.I,
)
_ANY_TITLE_RE = re.compile(r"<TITLE[^>]*>", re.I)
# 구형식 변종 2 (금융지주·보험·증권 실측 9사) — TABLE-GROUP 앵커도, 본표 TITLE도 없다.
# `<TITLE>2. 연결재무제표</TITLE>` 절 안에 캡션 표 + 데이터 표가 연달아 놓인다.
_FS_SECT_RE = re.compile(
    r"<TITLE[^>]*>\s*\d+\s*\.\s*((?:연결)?\s*재무제표)\s*</TITLE>", re.I
)
# 구형식: <TABLE-GROUP ACLASS="{XBRL}IS2">
_TG_RE = re.compile(r'<TABLE-GROUP[^>]*ACLASS="\{XBRL\}([A-Za-z0-9_]+)"[^>]*>', re.I)
_ANY_TG_RE = re.compile(r"<TABLE-GROUP\b", re.I)

_CAP_EL_RE = re.compile(r"<(TD|TE|TH|P)\b[^>]*>(.*?)</\1>", re.I | re.S)
_CAP_NAME_RE = re.compile(
    r"(?:연결|별도|개별)?(?:재무상태표|대차대조표|포괄손익계산서|손익계산서|현금흐름표|자본변동표)"
)
_TR_RE = re.compile(r"<TR\b[^>]*>(.*?)</TR>", re.I | re.S)
_CELL_RE = re.compile(r"<(TE|TD|TH)\b([^>]*)>(.*?)</\1>", re.I | re.S)
_ATTR_RE = re.compile(r'([A-Za-z_][A-Za-z0-9_-]*)\s*=\s*"([^"]*)"')
_UNIT_RE = re.compile(r"단위\s*[:：]\s*([가-힣]*원)")
_TAG_RE = re.compile(r"<[^>]+>")

_STMT_MAP = (
    ("재무상태표", "BS"),
    ("대차대조표", "BS"),
    ("포괄손익계산서", "CIS"),
    ("손익계산서", "IS"),
    ("현금흐름표", "CF"),
    ("자본변동표", "SCE"),
)
_UNIT_SCALE = {
    "원": 1.0,
    "천원": 1e3,
    "백만원": 1e6,
    "십억원": 1e9,
    "억원": 1e8,
    "조원": 1e12,
}
# 본표 계정명에 병기되는 주석 참조: '(주6,32)' '(주석30)' '(주 9, 26, 32)' '<주13>'
_NOTE_REF_RE = re.compile(r"[\(（<\[]주석?[\d,.\-~\s]*[\)）>\]]")
# 들여쓰기 불릿 — 두산 000150은 하위 항목을 `-당기순이익(손실)`로 쓴다.
_LEAD_BULLET_RE = re.compile(r"^[\-−–ㆍ·‧∙•*]+")
# 계정명 선행 번호: 'Ⅰ.', 'I.', '1.', '(1)', '가.', '①'
_LEAD_NUM_RE = re.compile(
    r"^[\(\[]?[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩIVXivx0-9가나다라마바사아자차카타파하①②③④⑤⑥⑦⑧⑨⑩]{1,4}[\)\].,·]\s*"
)


class Row(NamedTuple):
    """본표 한 셀(계정×열). `pick_account`가 fs_account 행과 동일하게 다룬다."""

    fs_div: str  # CFS | OFS
    sj_div: str  # BS | IS | CIS | CF | SCE
    account_id: str
    account_nm: str
    amount: float
    col_kind: int  # 0=당기 1=전기 2=전전기
    unit_scale: float
    order: int  # 원문 등장 순서 (동순위 tie-break)


# ── 공용 유틸 ────────────────────────────────────────────────────────────────


def norm_name(s: str | None) -> str:
    """계정명 정규화 — 태그·공백·주석참조 제거 + 선행 번호 제거.

    괄호 자체는 유지한다(`수익(매출액)`·`영업이익(손실)`은 계정 식별자의 일부).
    **주석 참조만** 걷어낸다 — `매출액(주6,32)`·`매출원가(주석 30)`처럼 본표에 주석
    번호를 병기하는 회사가 많고(FY2023 보고서는 ACODE도 없어) 이걸 안 떼면 그 해가
    통째로 미발견이 된다(실측: 대체 열로 밀려 재작성값 불일치 16건).
    """
    if not s:
        return ""
    s = _TAG_RE.sub("", s)
    s = s.replace("&nbsp;", " ").replace("　", " ").replace("\xa0", " ")
    s = re.sub(r"\s+", "", s)
    s = _NOTE_REF_RE.sub("", s)
    prev = None
    while prev != s:  # 'Ⅰ.1.' 같은 이중 접두 + 들여쓰기 불릿(`-당기순이익(손실)` 실측)
        prev = s
        s = _LEAD_NUM_RE.sub("", s)
        s = _LEAD_BULLET_RE.sub("", s)
    return s.strip(" .·")


def parse_amount(s: str | None) -> float | None:
    """금액 파싱. 괄호·△·▲·선행 '-'는 음수. 빈 칸·'-'는 **None(미발견)** — 0으로 채우지 않는다."""
    if s is None:
        return None
    t = _TAG_RE.sub("", s)
    t = t.replace("&nbsp;", " ").replace("　", " ").replace("\xa0", " ").strip()
    if t in ("", "-", "–", "—", "―", "N/A", "해당사항없음"):
        return None
    neg = False
    if t.startswith("(") and t.endswith(")"):
        neg, t = True, t[1:-1].strip()
    if t[:1] in ("△", "▲", "-", "−", "▵"):
        neg, t = True, t[1:].strip()
    t = t.replace(",", "").replace(" ", "")
    if not re.fullmatch(r"\d+(\.\d+)?", t):
        return None
    v = float(t)
    return -v if neg else v


def _rank_of(rules, account_id: str, name_norm: str) -> int | None:
    """규칙 목록에서 이 행이 받는 최상위 순위. 미해당이면 None."""
    best = None
    for rank, kind, values in rules:
        hit = (account_id in values) if kind == CODE else (name_norm in values)
        if hit and (best is None or rank < best):
            best = rank
    return best


def pick_account(rows: Iterable, key: str):
    """(rank, 재무제표 우선순위, 원문 순서) 오름차순 최상위 **1건**을 고른다.

    ⚠️ first-wins 금지(FN-025). 전 후보를 모아 정렬한 뒤 최상위를 택한다.
    `rows`는 `.sj_div/.account_id/.account_nm/.amount`를 갖는 무엇이든 된다 —
    `FsAccount`(정답지)와 `Row`(파싱값)에 **같은 선택기**를 써야 대조가 성립한다.
    """
    rules = ACCOUNT_RULES[key]
    pref = SJ_PREF[key]
    bans = NAME_EXCLUDE.get(key, ())
    best, best_score = None, None
    for i, r in enumerate(rows):
        sj = (getattr(r, "sj_div", "") or "").upper()
        if sj not in pref:
            continue
        if getattr(r, "amount", None) is None:
            continue
        nm = norm_name(getattr(r, "account_nm", ""))
        if any(b in nm for b in bans):
            continue
        rank = _rank_of(rules, getattr(r, "account_id", "") or "", nm)
        if rank is None:
            continue
        order = getattr(r, "order", i)
        score = (rank, pref.index(sj), order)
        if best_score is None or score < best_score:
            best, best_score = r, score
    return best, (best_score[0] if best_score else None)


# ── 본표 블록 추출 ───────────────────────────────────────────────────────────


def _sj_of(name: str) -> str | None:
    n = norm_name(name)
    for token, sj in _STMT_MAP:  # 포괄손익계산서를 손익계산서보다 먼저 본다
        if token in n:
            return sj
    return None


def _blocks(html: str) -> list[tuple[str, str, str]]:
    """(fs_div, sj_div, 블록 HTML) 목록. 신형식 우선, 없으면 구형식."""
    out: list[tuple[str, str, str]] = []
    ms = list(_FS_TITLE_RE.finditer(html))
    if ms:
        for m in ms:
            name = m.group(1)
            sj = _sj_of(name)
            if sj is None:
                continue
            nxt = _ANY_TITLE_RE.search(html, m.end())
            body = html[m.end(): nxt.start() if nxt else len(html)]
            out.append(("CFS" if "연결" in norm_name(name) else "OFS", sj, body))
        return out
    # 구형식 — 표 이름은 캡션 표 첫 셀에 있다.
    # ⚠️ 경계는 **닫는 태그**로 잡는다. 다음 <TABLE-GROUP> 시작까지로 두면 마지막 본표
    #    블록(CF_S)이 그 뒤 '5.재무제표 주석' 47만자를 통째로 삼킨다(삼성 2021 실측).
    for m in _TG_RE.finditer(html):
        close = html.find("</TABLE-GROUP>", m.end())
        nxt = _ANY_TG_RE.search(html, m.end())
        end = min(x for x in (close, nxt.start() if nxt else -1, len(html)) if x >= 0)
        body = html[m.end(): end]
        cap = ""
        cm = _CELL_RE.search(body)
        if cm:
            cap = cm.group(3)
        sj = _sj_of(cap)
        if sj is None:
            continue
        out.append(("CFS" if "연결" in norm_name(cap) else "OFS", sj, body))
    if out:
        return out
    # 구형식 변종 2 — 절 블록 안에서 **캡션 행**으로 표를 가른다.
    for m in _FS_SECT_RE.finditer(html):
        fs_div = "CFS" if "연결" in norm_name(m.group(1)) else "OFS"
        nxt = _ANY_TITLE_RE.search(html, m.end())
        sect = html[m.end(): nxt.start() if nxt else len(html)]
        # 캡션은 `<TD>연 결 재 무 상 태 표</TD>` 또는 `<P>연결포괄손익계산서</P>` —
        # 요소 종류가 회사마다 갈리므로 **텍스트가 표 이름 그 자체인 요소**를 경계로 삼는다.
        cuts: list[tuple[int, str]] = []
        for em in _CAP_EL_RE.finditer(sect):
            t = norm_name(em.group(2))
            if _CAP_NAME_RE.fullmatch(t):
                cuts.append((em.start(), _sj_of(t)))
        for i, (pos, sj) in enumerate(cuts):
            end = cuts[i + 1][0] if i + 1 < len(cuts) else len(sect)
            out.append((fs_div, sj, sect[pos:end]))
    return out
    return out


def _unit_scale(body: str) -> float:
    head = _TAG_RE.sub(" ", body[:6000]).replace("　", " ")
    m = _UNIT_RE.search(head)
    if not m:
        return 1.0
    return _UNIT_SCALE.get(m.group(1), 1.0)


def parse_report(html: str) -> tuple[list[Row], dict]:
    """원문 1건 → 본표 셀 목록. 열→사업연도 부여는 `select_core`가 한다."""
    rows: list[Row] = []
    stats: dict = {"blocks": 0, "cells": 0, "format": None}
    blocks = _blocks(html)
    stats["format"] = "new" if _FS_TITLE_RE.search(html) else ("old" if blocks else None)
    order = 0
    for fs_div, sj, body in blocks:
        stats["blocks"] += 1
        scale = _unit_scale(body)
        for tr in _TR_RE.findall(body):
            cells = _CELL_RE.findall(tr)
            if len(cells) < 2:
                continue
            name = norm_name(cells[0][2])
            if not name:
                continue
            for ci, (_tag, attrs, txt) in enumerate(cells[1:4]):
                amt = parse_amount(txt)
                if amt is None:
                    continue
                a = dict(_ATTR_RE.findall(attrs))
                rows.append(
                    Row(
                        fs_div=fs_div,
                        sj_div=sj,
                        account_id=a.get("ACODE", ""),
                        account_nm=name,
                        amount=amt * scale,
                        col_kind=ci,
                        unit_scale=scale,
                        order=order,
                    )
                )
                order += 1
                stats["cells"] += 1
    return rows, stats


def select_core(rows: list[Row], src_fy: int) -> list[dict]:
    """13계정 × (연결|별도) × 3열 → 각 조합에서 최상위 1건. 파생·합산 없음."""
    out: list[dict] = []
    for fs_div in ("CFS", "OFS"):
        for col in (0, 1, 2):
            sub = [r for r in rows if r.fs_div == fs_div and r.col_kind == col]
            if not sub:
                continue
            for key in ACCOUNT_KEYS:
                hit, rank = pick_account(sub, key)
                if hit is None:
                    continue  # 미발견 — 0으로 채우지 않는다
                out.append(
                    {
                        "fiscal_year": src_fy - col,
                        "src_fiscal_year": src_fy,
                        "col_kind": col,
                        "fs_div": fs_div,
                        "sj_div": hit.sj_div,
                        "account_key": key,
                        "match_rank": rank,
                        "account_id": hit.account_id,
                        "account_nm": hit.account_nm,
                        "amount": abs(hit.amount) if key in SIGN_ABS else hit.amount,
                        "unit_scale": hit.unit_scale,
                    }
                )
    return out


def parse_file(path: str, src_fy: int) -> tuple[list[dict], dict]:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        html = f.read()
    rows, stats = parse_report(html)
    return select_core(rows, src_fy), stats


# ── DB 적재 ─────────────────────────────────────────────────────────────────


def run(tickers: list[str] | None = None, min_fy: int = 2021, quiet: bool = False) -> dict:
    init_local_db()
    sess = get_local_session()
    q = sess.query(ReportRaw).filter(ReportRaw.fiscal_year >= min_fy)
    if tickers:
        q = q.filter(ReportRaw.ticker.in_(tickers))
    reports = q.order_by(ReportRaw.ticker, ReportRaw.fiscal_year).all()
    agg = {"보고서": 0, "파일없음": 0, "블록0": 0, "행": 0, "신형식": 0, "구형식": 0}
    done_t = set()
    for rep in reports:
        path = os.path.join(RAW_DIR, rep.ticker, f"{rep.rcept_no}.xml")
        if not os.path.exists(path):
            agg["파일없음"] += 1
            continue
        picked, stats = parse_file(path, rep.fiscal_year)
        agg["보고서"] += 1
        if stats["format"] == "new":
            agg["신형식"] += 1
        elif stats["format"] == "old":
            agg["구형식"] += 1
        if not picked:
            agg["블록0"] += 1
            continue
        sess.query(FsAccountXml).filter_by(rcept_no=rep.rcept_no).delete()
        for d in picked:
            sess.add(FsAccountXml(rcept_no=rep.rcept_no, ticker=rep.ticker, **d))
        agg["행"] += len(picked)
        if rep.ticker not in done_t:
            done_t.add(rep.ticker)
        sess.commit()
        if not quiet:
            print(f"[{rep.ticker}] FY{rep.fiscal_year} {stats['format']} "
                  f"블록{stats['blocks']} 셀{stats['cells']} → {len(picked)}행")
    sess.close()
    agg["기업"] = len(done_t)
    return agg


def main() -> None:
    ap = argparse.ArgumentParser(description="원문 XML 본표 → fs_account_xml")
    ap.add_argument("--tickers", help="쉼표 구분 종목코드")
    ap.add_argument("--pilot", action="store_true", help="fs_account 보유 55사만")
    ap.add_argument("--min-fy", type=int, default=2021)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    tickers = None
    if args.tickers:
        tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]
    elif args.pilot:
        from .models import FsAccount

        s = get_local_session()
        tickers = [r[0] for r in s.query(FsAccount.ticker).distinct().all()]
        s.close()
    agg = run(tickers, min_fy=args.min_fy, quiet=args.quiet)
    print("요약:", agg)


if __name__ == "__main__":
    main()
