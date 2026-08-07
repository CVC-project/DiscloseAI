"""galaxy_lite_<ticker>.json 생성기 — 표준(골든) 대비 델타 은하수.

설계 정본: GALAXY_LITE_PLAN.md
- 수치는 전부 코드가 산출한다 (LLM은 §7 '주목할 점' 카드만, 별도 주입).
- 입력: firm_<t>.json(13계정×5년) + galaxy_<표준>.json(series, 조원) + reports.db(read-only)
- 출력: data/galaxy_lite_<t>.json

Usage:
    python integration/dossier/build_galaxy_lite.py 009150
    python integration/dossier/build_galaxy_lite.py 009150 --std 005930
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DATA = HERE / "data"
REPORTS_DB = ROOT / "shared" / "data" / "reports.db"
CORPS_CSV = ROOT / "modules" / "report" / "data" / "corps.csv"
COMPANIES_INDEX = ROOT / "integration" / "data" / "companies_index.json"

# firm JSON 13계정 -> lite series 키
FIRM_KEYS = {
    "revenue": "revenue",
    "cogs": "cogs",
    "operating_income": "op",
    "net_income": "ni",
    "operating_cashflow": "ocf",
    "investing_cashflow": "icf",
    "financing_cashflow": "fin",
    "total_assets": "assets",
    "total_liabilities": "debt",
    "total_equity": "equity",
    "current_assets": "ca",
    "current_liabilities": "cl",
    "long_term_debt": "ltd",
}

# (OCF, ICF, FIN) 부호 -> 8상 (GALAXY_LITE_PLAN §4)
PATTERNS = {
    "+--": ("자가발전형", "벌어서 투자하고 빚도 갚아요"),
    "+-+": ("확장투자형", "벌면서도 외부 자금을 더 당겨 투자해요"),
    "++-": ("정리형", "벌고 자산도 팔아 빚을 갚아요"),
    "+++": ("비축형", "벌고 팔고 빌리고 — 현금을 쌓는 국면이에요"),
    "--+": ("외부수혈형", "영업에선 못 벌고 조달로 버티며 투자해요"),
    "-++": ("버티기형", "영업 적자를 자산 매각과 조달로 메워요"),
    "-+-": ("구조조정형", "자산을 팔아 빚을 갚는 국면이에요"),
    "---": ("소진형", "벌지 못하는데 투자와 상환이 겹쳐 현금이 빠르게 줄어요"),
}

# 주목할 점 카드용 주석 후보 시그니처 (GALAXY_LITE_PLAN §7)
NOTE_SIGNATURES = [
    "재고자산",
    "매출채권",
    "차입금",
    "사채",
    "충당부채",
    "우발",
    "특수관계자",
    "영업부문",
    "중단영업",
    "유형자산",
    "무형자산",
    "리스",
]

ZONES = {
    "A": "저수지(기초현금)",
    "B": "손익 강",
    "C": "현금 전환",
    "D": "저수지(기말현금)",
    "E": "자본",
}


# ---------- 유틸 ----------


def _sign(v: float | None) -> str:
    if v is None:
        return "?"
    return "+" if v >= 0 else "-"


def _pct(num: float | None, den: float | None) -> float | None:
    if num is None or den in (None, 0):
        return None
    return num / den * 100.0


def _fmt_won(v: float | None) -> str:
    """원 단위 숫자 -> '11.3조' / '9,133억' 표시 문자열."""
    if v is None:
        return "—"
    a = abs(v)
    sign = "-" if v < 0 else ""
    if a >= 1e12:
        return f"{sign}{a / 1e12:.1f}조"
    if a >= 1e8:
        return f"{sign}{a / 1e8:,.0f}억"
    return f"{sign}{a:,.0f}원"


def _fmt_jo(v: float | None) -> str:
    """조원 단위 숫자(골든 series) -> 표시 문자열."""
    if v is None:
        return "—"
    return f"{v:,.1f}조"


def _pp(v: float | None, digits: int = 1) -> str:
    if v is None:
        return "—"
    return f"{v:.{digits}f}%"


# 숫자 읽기의 받침 유무 (영·일·삼·육·칠·팔은 받침 있음 / 이·사·오·구는 없음)
_DIGIT_JONG = {"0": True, "1": True, "2": False, "3": True, "4": False,
               "5": False, "6": True, "7": True, "8": True, "9": False}
_DIGIT_RIEUL = {"1", "7", "8"}  # ㄹ 받침 — '으로'가 아니라 '로'


def _tail(word: str) -> tuple[bool, bool]:
    """(받침 있음, ㄹ받침) — 조사 선택용. 괄호·기호는 벗겨내고 마지막 글자로 판정."""
    w = word.strip().rstrip("])}·.,%")
    if not w:
        return False, False
    ch = w[-1]
    if ch.isdigit():
        return _DIGIT_JONG[ch], ch in _DIGIT_RIEUL
    if "가" <= ch <= "힣":
        code = (ord(ch) - 0xAC00) % 28
        return code != 0, code == 8  # 8 = ㄹ
    # 한글·숫자가 아니면(영문 등) 받침 없음으로 처리
    return False, False


def J(word: str, kind: str) -> str:
    """word + 알맞은 조사. kind: 은는/이가/을를/으로/과와."""
    has, rieul = _tail(word)
    pair = {
        "은는": ("은", "는"),
        "이가": ("이", "가"),
        "을를": ("을", "를"),
        "과와": ("과", "와"),
    }
    if kind == "으로":
        return word + ("로" if (not has or rieul) else "으로")
    a, b = pair[kind]
    return word + (a if has else b)


def JB(word: str, kind: str) -> str:
    """숫자를 [브래킷 칩]으로 감싸고 조사는 칩 **밖**에 붙인다 (STYLE_GUIDE A7)."""
    has, rieul = _tail(word)
    if kind == "으로":
        josa = "로" if (not has or rieul) else "으로"
    else:
        pair = {"은는": ("은", "는"), "이가": ("이", "가"), "을를": ("을", "를"), "과와": ("과", "와")}
        a, b = pair[kind]
        josa = a if has else b
    return f"[{word}]{josa}"


# ---------- 입력 로드 ----------


def load_firm(ticker: str) -> dict[str, Any]:
    p = DATA / f"firm_{ticker}.json"
    if not p.exists():
        raise SystemExit(f"[FATAL] firm JSON 없음: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def load_std(std_ticker: str) -> dict[str, Any]:
    p = DATA / f"galaxy_{std_ticker}.json"
    if not p.exists():
        raise SystemExit(f"[FATAL] 표준 골든 JSON 없음: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def load_corps() -> dict[str, dict[str, str]]:
    rows = {}
    with CORPS_CSV.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows[row["ticker"]] = row
    return rows


def resolve_standard(ticker: str, corps: dict[str, dict[str, str]]) -> tuple[str, str, bool]:
    """(표준 티커, 클러스터, 인접여부) — 같은 cluster의 tier<=1 대표를 찾는다."""
    me = corps.get(ticker)
    if not me or not me.get("cluster"):
        raise SystemExit(f"[FATAL] corps.csv에 {ticker}의 cluster가 없어요 — 표준 매핑 불가")
    cluster = me["cluster"]
    cands = [
        (t, r)
        for t, r in corps.items()
        if r.get("cluster") == cluster and (r.get("tier") or "").strip() in ("0", "1") and t != ticker
    ]
    # tier 0(T0) 우선
    cands.sort(key=lambda x: (x[1].get("tier") or "9"))
    for t, _ in cands:
        if (DATA / f"galaxy_{t}.json").exists():
            return t, cluster, False
    raise SystemExit(f"[FATAL] 클러스터 '{cluster}'에 골든 표준이 없어요 — 신규 골든 빌드가 선행돼야 해요")


def load_sector(ticker: str) -> str:
    try:
        idx = json.loads(COMPANIES_INDEX.read_text(encoding="utf-8"))
    except Exception:
        return ""
    items = idx if isinstance(idx, list) else idx.get("companies", idx.get("items", []))
    for c in items:
        if c.get("t") == ticker:
            return c.get("s", "")
    return ""


def load_report_meta(ticker: str) -> dict[str, Any]:
    """최신 사업보고서 rcept_no·연도 + 주목할 점 주석 후보 목록 (read-only)."""
    out: dict[str, Any] = {"rcept_no": None, "fiscal_year": None, "note_candidates": []}
    if not REPORTS_DB.exists():
        return out
    con = sqlite3.connect(f"file:{REPORTS_DB}?mode=ro", uri=True)
    try:
        cur = con.cursor()
        cur.execute(
            "select rcept_no, fiscal_year from report_raw where ticker=? "
            "order by fiscal_year desc, rcept_no desc limit 1",
            (ticker,),
        )
        row = cur.fetchone()
        if not row:
            return out
        out["rcept_no"], out["fiscal_year"] = row[0], row[1]
        cur.execute(
            "select note_no, title, char_len from report_section where rcept_no=? order by char_len desc",
            (row[0],),
        )
        for note_no, title, char_len in cur.fetchall():
            t = title or ""
            if any(sig in t for sig in NOTE_SIGNATURES):
                out["note_candidates"].append(
                    {"note_no": note_no, "title": t, "char_len": char_len}
                )
    finally:
        con.close()
    return out


# ---------- 계열 산출 ----------


def build_series(firm: dict[str, Any]) -> tuple[list[str], dict[str, list[float | None]]]:
    years_raw = sorted(firm.get("years", []), key=lambda y: y["year"])
    labels = [f"FY{str(y['year'])[2:]}" for y in years_raw]
    series: dict[str, list[float | None]] = {k: [] for k in FIRM_KEYS.values()}
    for y in years_raw:
        for src, dst in FIRM_KEYS.items():
            v = y.get(src)
            series[dst].append(float(v) if v is not None else None)
    return labels, series


def std_series(std: dict[str, Any]) -> dict[str, list[float | None]]:
    """골든 series(조원) 중 lite와 비교 가능한 키만."""
    s = std.get("series", {})
    keep = ["revenue", "cogs", "op", "ni", "ocf", "icf", "fin", "assets", "debt", "equity"]
    return {k: s.get(k, []) for k in keep if k in s}


def normalize(series: dict[str, list[float | None]], base_key: str = "revenue") -> dict[str, list[float | None]]:
    """매출=100 정규화 — 규모가 달라도 '모양'을 비교하기 위한 축."""
    base = series.get(base_key, [])
    out: dict[str, list[float | None]] = {}
    for k, vals in series.items():
        row: list[float | None] = []
        for i, v in enumerate(vals):
            b = base[i] if i < len(base) else None
            row.append(None if (v is None or not b) else v / b * 100.0)
        out[k] = row
    return out


def cf_availability(series: dict[str, list[float | None]], labels: list[str]) -> dict[str, Any]:
    """현금흐름 3계정이 모두 있는 연도 인덱스 (GALAXY_LITE_PLAN §2.1 결측 규칙)."""
    idx = [
        i
        for i in range(len(labels))
        if all(series[k][i] is not None for k in ("ocf", "icf", "fin"))
    ]
    return {
        "indices": idx,
        "from": labels[idx[0]] if idx else None,
        "full": len(idx) == len(labels),
        "count": len(idx),
    }


def detect_pattern(series: dict[str, list[float | None]], labels: list[str], cf: dict[str, Any]) -> dict[str, Any]:
    path = []
    for i in cf["indices"]:
        code = _sign(series["ocf"][i]) + _sign(series["icf"][i]) + _sign(series["fin"][i])
        name = PATTERNS.get(code, ("분류불가", ""))[0]
        path.append({"year": labels[i], "code": code, "name": name})
    if not path:
        return {"code": None, "name": None, "desc": None, "path": []}
    last = path[-1]
    name, desc = PATTERNS.get(last["code"], ("분류불가", ""))
    return {"code": last["code"], "name": name, "desc": desc, "path": path}


def valley_index(vals: list[float | None]) -> int | None:
    pairs = [(i, v) for i, v in enumerate(vals) if v is not None]
    if len(pairs) < 3:
        return None
    return min(pairs, key=lambda x: x[1])[0]


# ---------- 델타 카드 (GALAXY_LITE_PLAN §6) ----------


def build_cards(
    ctx: dict[str, Any],
) -> list[dict[str, Any]]:
    """5~6장. 멘트 규격: ①표준에서는 A였어요 ②이 회사는 B예요 ③그래서 C를 뜻해요 (경어체)."""
    labels: list[str] = ctx["labels"]
    S: dict[str, list[float | None]] = ctx["series"]
    N: dict[str, list[float | None]] = ctx["norm"]
    SD: dict[str, list[float | None]] = ctx["std_series"]
    SN: dict[str, list[float | None]] = ctx["std_norm"]
    std_name: str = ctx["std_name"]
    name: str = ctx["name"]
    cf: dict[str, Any] = ctx["cf"]
    pattern: dict[str, Any] = ctx["pattern"]
    std_years: list[str] = ctx["std_years"]
    std_ticker: str = ctx["std_ticker"]

    cards: list[dict[str, Any]] = []
    li = len(labels) - 1  # 최신 연도 인덱스
    sli = len(std_years) - 1

    def card(cid, title, lines, zone, focus, nums):
        cards.append(
            {
                "id": cid,
                "kind": "delta",
                "title": title,
                "lines": lines,
                "anchor": {"zone": zone, "std_focus": focus, "std_ticker": std_ticker},
                "nums": nums,
            }
        )

    # 1) 항로 개형 — 매출 100원이 영업 존에서 얼마 남는가
    op_m = _pct(S["op"][li], S["revenue"][li])
    std_op_m = _pct(SD["op"][sli], SD["revenue"][sli])
    if op_m is not None and std_op_m is not None:
        gap = op_m - std_op_m
        verdict = (
            f"같은 100원을 팔아도 이 회사 강줄기는 영업 존을 지나며 [{abs(gap):.1f}%p] 더 가늘어져요"
            if gap < 0
            else f"같은 100원을 팔아도 이 회사 강줄기는 영업 존에서 [{gap:.1f}%p] 더 두껍게 남아요"
        )
        card(
            "d1",
            "항로 개형 — 100원이 영업 존을 지나면",
            [
                f"표준인 {J(std_name, '은는')} 매출 [{_fmt_jo(SD['revenue'][sli])}] 가운데 영업이익 "
                f"{JB(_fmt_jo(SD['op'][sli]), '을를')} 남겼어요. 100원을 팔면 [{std_op_m:.1f}원]이 남는 항로예요.",
                f"{J(name, '은는')} 매출 [{_fmt_won(S['revenue'][li])}]에 영업이익 "
                f"{JB(_fmt_won(S['op'][li]), '으로')}, 100원당 [{op_m:.1f}원]이 남아요.",
                f"{verdict} — 규모가 아니라 강폭의 문제라, 뒤에 나오는 투자·재무 존에서 쓸 수 있는 여력도 그만큼 달라져요.",
            ],
            "B",
            "zoneB",
            [{"k": "op_margin", "v": op_m}, {"k": "std_op_margin", "v": std_op_m}],
        )

    # 2) 골짜기 비교 — 사이클 동조 여부
    vi = valley_index(S["op"])
    svi = ctx["std_anchor"].get("valley_index")
    if vi is not None and svi is not None:
        same = labels[vi] == (std_years[svi] if svi < len(std_years) else None)
        peak = max(v for v in S["op"] if v is not None)
        drop = (1 - S["op"][vi] / peak) * 100 if peak else None
        std_label = ctx["std_anchor"].get("label") or "골짜기"
        if same:
            third = (
                f"두 회사가 같은 해에 함께 꺾였다는 건, 이 회사의 부진이 개별 사정이 아니라 "
                f"산업 사이클을 함께 탄 결과라는 뜻이에요. 표준의 골짜기 이야기를 읽어 두면 이 회사의 [{labels[vi]}]도 같은 문법으로 읽혀요."
            )
        else:
            third = (
                f"표준과 다른 해에 꺾였다는 건, 산업 전체보다 이 회사 고유의 사정이 더 크게 작용했다는 신호예요. "
                f"무엇이 그해를 눌렀는지는 아래 '주목할 점'에서 주석으로 확인해 보세요."
            )
        card(
            "d2",
            f"골짜기 비교 — {labels[vi]}에 무슨 일이",
            [
                f"표준인 {J(std_name, '은는')} [{std_years[svi]}]이 골짜기였어요. "
                f"'{std_label}'{'로' if not _tail(std_label)[0] or _tail(std_label)[1] else '으로'} 영업이익이 [{_fmt_jo(SD['op'][svi])}]까지 내려앉은 해예요.",
                f"{name}의 최저점은 [{labels[vi]}]이고, 영업이익은 [{_fmt_won(S['op'][vi])}]"
                + (
                    f"{'로' if not _tail(_fmt_won(S['op'][vi]))[0] else '으로'} 5년 최고치 대비 [{drop:.0f}%] 낮아요."
                    if drop
                    else "예요."
                ),
                third,
            ],
            "B",
            "zoneB",  # 골든의 data-zone 앵커명 (focus 딥링크가 이 값으로 스크롤한다)
            [{"k": "valley", "v": labels[vi]}, {"k": "std_valley", "v": std_years[svi]}],
        )

    # 3) 항로 전환 — 8상 경로
    if pattern["path"]:
        first, last = pattern["path"][0], pattern["path"][-1]
        std_path_code = (
            _sign(SD["ocf"][sli]) + _sign(SD["icf"][sli]) + _sign(SD["fin"][sli])
            if all(SD.get(k) for k in ("ocf", "icf", "fin"))
            else None
        )
        std_pname = PATTERNS.get(std_path_code, ("—", ""))[0] if std_path_code else "—"
        changed = first["code"] != last["code"]
        line2 = (
            f"{J(name, '은는')} [{first['year']}] {first['name']}에서 [{last['year']}] "
            f"{J(last['name'], '으로')} 항로를 바꿨어요."
            if changed
            else f"{name}도 [{first['year']}]부터 [{last['year']}]까지 줄곧 {last['name']}이에요."
        )
        fin_v = S["fin"][li]
        if fin_v is not None and fin_v > 0:
            third = (
                f"재무 존의 화살표가 바깥이 아니라 안으로 향한다는 건, 번 돈만으로는 투자를 다 대지 못해 "
                f"외부에서 {JB(_fmt_won(fin_v), '을를')} 더 당겨왔다는 뜻이에요. 표준은 같은 해 그 반대 방향이었어요."
            )
        else:
            third = (
                "재무 존의 화살표가 바깥으로 향하면 번 돈으로 빚을 갚고 주주에게 돌려주는 국면이에요. "
                "표준과 같은 방향이라면, 현금을 다루는 방식이 업계 성숙 기업의 문법을 따르고 있다는 신호예요."
            )
        card(
            "d3",
            f"항로 전환 — 지금은 {pattern['name']}",
            [
                f"표준인 {J(std_name, '은는')} 최근 연도가 {std_pname}이에요. 벌어들인 현금으로 투자와 상환을 모두 감당하는 항로예요.",
                line2 + f" ({pattern['desc']})",
                third,
            ],
            "D",
            "zoneD",
            [{"k": "pattern", "v": pattern["code"]}, {"k": "std_pattern", "v": std_path_code}],
        )

    # 4) 저수지 궤적 — 순현금 누적
    if cf["indices"]:
        net = [
            (S["ocf"][i] or 0) + (S["icf"][i] or 0) + (S["fin"][i] or 0) for i in cf["indices"]
        ]
        cum = sum(net)
        yrs = [labels[i] for i in cf["indices"]]
        std_net = [
            (SD["ocf"][i] or 0) + (SD["icf"][i] or 0) + (SD["fin"][i] or 0)
            for i in range(len(std_years))
        ]
        std_cum = sum(std_net)
        span = f"{len(yrs)}개년" if len(yrs) < len(labels) else "5년"
        card(
            "d4",
            "저수지 궤적 — 현금은 쌓였을까 말랐을까",
            [
                f"표준인 {J(std_name, '은는')} 5년간 영업·투자·재무를 모두 합친 현금이 [{_fmt_jo(std_cum)}] "
                + ("늘었어요." if std_cum >= 0 else "줄었어요."),
                f"{J(name, '은는')} 현금흐름이 확인되는 [{yrs[0]}]부터 [{yrs[-1]}]까지 {span} 합계로 [{_fmt_won(cum)}] "
                + ("늘었어요." if cum >= 0 else "줄었어요."),
                "영업에서 번 돈(들어오는 물)과 투자·재무로 나간 돈(빠지는 물)의 차이가 저수지 수위를 정해요. "
                + (
                    "수위가 오르는 항해예요 — 다음 투자를 자기 힘으로 시작할 수 있다는 뜻이에요."
                    if cum >= 0
                    else "수위가 내려가는 항해예요 — 이 상태가 이어지면 어디선가 물을 더 끌어와야 해요."
                ),
            ],
            "D",
            "zoneD",
            [{"k": "cum_net", "v": cum}, {"k": "std_cum_net", "v": std_cum}],
        )

    # 5) 가장 다른 대목 — 정규화 편차 최대
    # 흐름(flow) 계정만 비교한다 — 잔액(assets·debt·equity) 대비는 EQS 탭의 영역(§1 차별선)
    diffs = []
    for k in ("cogs", "op", "ni", "ocf", "icf", "fin"):
        a = N.get(k, [None] * len(labels))[li] if k in N else None
        b = SN.get(k, [None] * len(std_years))[sli] if k in SN else None
        if a is not None and b is not None:
            diffs.append((abs(a - b), k, a, b))
    if diffs:
        diffs.sort(reverse=True)
        gapv, gk, a, b = diffs[0]
        KO = {
            "cogs": "매출원가",
            "op": "영업이익",
            "ni": "순이익",
            "ocf": "영업활동 현금",
            "icf": "투자활동 현금",
            "fin": "재무활동 현금",
        }
        ko = KO.get(gk, gk)
        card(
            "d5",
            f"가장 다른 대목 — {ko}",
            [
                f"매출을 100으로 맞춰 놓고 보면, 표준인 {std_name}의 {J(ko, '은는')} [{b:.1f}]이에요.",
                f"{J(name, '은는')} 같은 자리에서 [{a:.1f}]{'로' if not _tail(f'{a:.1f}')[0] else '으로'}, "
                f"표준과 [{gapv:.1f}]만큼 벌어져요. 5년 항로에서 두 회사가 가장 크게 갈라지는 지점이에요.",
                "규모를 지우고 모양만 남겼을 때 남는 차이라서, 이 대목이 이 회사를 표준과 다르게 만드는 구조적 특징이에요. 위 지도에서 강조된 마디가 바로 여기예요.",
            ],
            "C",
            "zoneC",
            [{"k": gk, "v": a}, {"k": "std_" + gk, "v": b}, {"k": "gap", "v": gapv}],
        )

    return cards


# ---------- 조립 ----------


def build(ticker: str, std_ticker: str | None = None) -> dict[str, Any]:
    corps = load_corps()
    if std_ticker:
        cluster = corps.get(ticker, {}).get("cluster", "")
        adjacent = False
    else:
        std_ticker, cluster, adjacent = resolve_standard(ticker, corps)

    firm = load_firm(ticker)
    std = load_std(std_ticker)
    rmeta = load_report_meta(ticker)

    labels, series = build_series(firm)
    cf = cf_availability(series, labels)
    pattern = detect_pattern(series, labels, cf)
    norm = normalize(series)
    sd = std_series(std)
    snorm = normalize(sd)

    name = firm["corp"]["name"]
    fy = labels[-1].replace("FY", "20") if labels else ""

    ctx = {
        "labels": labels,
        "series": series,
        "norm": norm,
        "std_series": sd,
        "std_norm": snorm,
        "std_years": std.get("years", []),
        "std_name": std["corp"]["name"],
        "std_ticker": std_ticker,
        "std_anchor": std.get("anchor", {}),
        "name": name,
        "cf": cf,
        "pattern": pattern,
    }
    cards = build_cards(ctx)

    intro = [
        f"이 화면은 {name}만 따로 읽는 곳이 아니라, 먼저 배운 표준 항로 위에 {name}을 겹쳐 보는 곳이에요.",
        f"같은 업종의 표준은 {std['corp']['name']}이에요. 표준을 아직 안 보셨다면 먼저 그 은하수를 한 번 훑고 오시면 이 차이들이 훨씬 잘 읽혀요.",
    ]

    out = {
        "schema_version": 1,
        "kind": "lite",
        "corp": {
            "ticker": ticker,
            "name": name,
            "fiscal_year": fy,
            "fiscal_label": f"FY{fy} · 연결 기준",
            "sector": load_sector(ticker),
            "cluster": cluster,
            "rcept_no": rmeta["rcept_no"],
            "report_fiscal_year": rmeta["fiscal_year"],
            "cash_flow_from": cf["from"],
        },
        "std_ref": {
            "ticker": std_ticker,
            "name": std["corp"]["name"],
            "cluster": cluster,
            "adjacent": adjacent,
            "fiscal_label": std["corp"].get("fiscal_label", ""),
        },
        "years": labels,
        "series": series,
        "norm": norm,
        "std_years": std.get("years", []),
        "std_series": sd,
        "std_norm": snorm,
        "cf_available": cf,
        "pattern": pattern,
        "strings": {
            "header": f"{name} · FY{fy} · 연결 기준",
            "hero": f"표준({std['corp']['name']})과 무엇이 어떻게 다를까요?",
            "intro_lines": intro,
        },
        "cards": cards,
        "notes": [],  # LLM '주목할 점' 카드 — inject_lite_notes.py가 채운다
        "note_candidates": rmeta["note_candidates"][:8],
        "meta": {
            "generated_by": "build_galaxy_lite.py",
            "validated": False,
            "std_source": f"galaxy_{std_ticker}.json",
            "firm_source": f"firm_{ticker}.json",
        },
    }
    return out


def selfcheck(doc: dict[str, Any], ticker: str) -> list[str]:
    """빌더 자체 assert — 모든 수치가 입력에서 재도출되는지 (GALAXY_LITE_PLAN §10-1)."""
    errs = []
    firm = load_firm(ticker)
    years_raw = sorted(firm.get("years", []), key=lambda y: y["year"])
    for i, y in enumerate(years_raw):
        for src, dst in FIRM_KEYS.items():
            want = y.get(src)
            got = doc["series"][dst][i]
            if (want is None) != (got is None):
                errs.append(f"series.{dst}[{i}] 결측 불일치")
            elif want is not None and abs(float(want) - got) > 1:
                errs.append(f"series.{dst}[{i}] 값 불일치 {want} != {got}")
    if doc["pattern"]["path"]:
        for step in doc["pattern"]["path"]:
            if step["code"] not in PATTERNS:
                errs.append(f"pattern code 미정의: {step['code']}")
    if not doc["cards"]:
        errs.append("델타 카드가 0장")
    for c in doc["cards"]:
        if len(c["lines"]) != 3:
            errs.append(f"{c['id']}: 3문장 규격 위반 ({len(c['lines'])}줄)")
        for ln in c["lines"]:
            if ln.rstrip().endswith("다.") and "요." not in ln[-4:]:
                errs.append(f"{c['id']}: 격식체 의심 — {ln[-30:]}")
    return errs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("--std", default=None, help="표준 티커 강제 지정 (기본: cluster에서 자동)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    doc = build(args.ticker, args.std)
    errs = selfcheck(doc, args.ticker)
    if errs:
        print("[CHECK] FAIL")
        for e in errs:
            print("  -", e)
        raise SystemExit(1)

    path = Path(args.out) if args.out else DATA / f"galaxy_lite_{args.ticker}.json"
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[OK] {path.name}  표준={doc['std_ref']['name']}({doc['std_ref']['ticker']})  "
          f"카드={len(doc['cards'])}  패턴={doc['pattern']['name']}  "
          f"현금흐름={doc['cf_available']['count']}개년  주석후보={len(doc['note_candidates'])}")


if __name__ == "__main__":
    main()
