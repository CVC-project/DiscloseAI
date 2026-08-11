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


def load_cf_gapfill(ticker: str, fiscal_years: list[int]) -> dict[int, dict[str, float]]:
    """firm JSON에 빈 현금흐름 3계정을 fs_account(정형계정, read-only)에서 보충.

    ⚠️ '미공시'가 아니다 — 현금흐름표는 매년 공시된다. firm JSON 쪽 수집 갭일 뿐이므로
    reports.db에 있으면 채우고, 그래도 없으면 화면엔 '데이터 준비 중'으로 표기한다(FN-021).
    fs_account 커버리지는 클러스터 부여 55사 — 그 밖은 빈 dict.
    """
    out: dict[int, dict[str, float]] = {}
    if not REPORTS_DB.exists() or not fiscal_years:
        return out
    con = sqlite3.connect(f"file:{REPORTS_DB}?mode=ro", uri=True)
    try:
        cur = con.cursor()
        q = ",".join("?" * len(fiscal_years))
        cur.execute(
            f"select fiscal_year, account_nm, amount from fs_account "
            f"where ticker=? and sj_div='CF' and fiscal_year in ({q})",
            (ticker, *fiscal_years),
        )
        for fy, nm, amt in cur.fetchall():
            nm = (nm or "").replace(" ", "")
            if amt is None or "현금흐름" not in nm or "창출" in nm:
                continue
            key = None
            if "영업활동" in nm:
                key = "ocf"
            elif "투자활동" in nm:
                key = "icf"
            elif "재무활동" in nm:
                key = "fin"
            if key:
                out.setdefault(int(fy), {})[key] = float(amt)
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
    # 근소값 경계: 세 계정 중 하나라도 |값| < 매출 1%면 부호가 쉽게 뒤집힌다 (전 시장 실측 21%)
    i_last = cf["indices"][-1]
    rev = series["revenue"][i_last]
    edge = bool(rev) and min(
        abs(series[k][i_last]) for k in ("ocf", "icf", "fin")
    ) < abs(rev) * 0.01
    return {"code": last["code"], "name": name, "desc": desc, "path": path, "edge": edge}


def valley_index(vals: list[float | None]) -> int | None:
    pairs = [(i, v) for i, v in enumerate(vals) if v is not None]
    if len(pairs) < 3:
        return None
    return min(pairs, key=lambda x: x[1])[0]


# ---------- 델타 카드 (GALAXY_LITE_PLAN §6 — 직관 서술, 비유 최소화) ----------

# 카드 -> 표준 골든 딥다이브 착지 행 (dives의 row 값. focus=dive:<key>로 바로 고정)
_ROW_BY_SERIES = {"cogs": "is-cogs", "op": "is-opincome", "ni": "is-netincome",
                  "ocf": "cf-op", "icf": "cf-inv", "fin": "cf-fin"}


def _std_dive_focus(std_doc: dict[str, Any], row: str | None, zone: str) -> str:
    """골든 dives에서 row 일치 키를 찾아 'dive:<key>'로. 없으면 존 스크롤 폴백."""
    if row:
        for k, v in (std_doc.get("dives") or {}).items():
            if isinstance(v, dict) and v.get("row") == row:
                return f"dive:{k}"
    return f"zone{zone}"


def build_cards(
    ctx: dict[str, Any],
) -> list[dict[str, Any]]:
    """5~6장. 멘트 규격: ①표준은 A였어요 ②이 회사는 B예요 ③그래서 C예요 (경어체, 직관 서술)."""
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
    std_doc: dict[str, Any] = ctx["std_doc"]

    cards: list[dict[str, Any]] = []
    li = len(labels) - 1
    sli = len(std_years) - 1

    def card(cid, title, lines, zone, row, nums):
        cards.append(
            {
                "id": cid,
                "kind": "delta",
                "title": title,
                "lines": lines,
                "anchor": {"zone": zone,
                           "std_focus": _std_dive_focus(std_doc, row, zone),
                           "std_ticker": std_ticker},
                "nums": nums,
            }
        )

    # 1) 이익률 격차 — 100원 팔면 몇 원 남나
    op_m = _pct(S["op"][li], S["revenue"][li])
    std_op_m = _pct(SD["op"][sli], SD["revenue"][sli])
    if op_m is not None and std_op_m is not None:
        gap = op_m - std_op_m
        if gap < 0:
            verdict = (
                f"같은 100원을 팔아도 남는 돈이 [{abs(gap):.1f}%p] 적은 거예요. "
                "남는 돈이 적으면 그만큼 투자·빚 상환·배당에 쓸 여력도 줄어요."
            )
        else:
            verdict = (
                f"같은 100원을 팔아도 남는 돈이 [{gap:.1f}%p] 많은 거예요. "
                "그만큼 투자·빚 상환·배당에 쓸 여력이 커요."
            )
        card(
            "d1",
            "100원 팔면 몇 원이 남나",
            [
                f"표준인 {J(std_name, '은는')} 매출 [{_fmt_jo(SD['revenue'][sli])}] 가운데 영업이익 "
                f"{JB(_fmt_jo(SD['op'][sli]), '을를')} 남겼어요 — 100원어치를 팔면 [{std_op_m:.1f}원]이 남는 구조예요.",
                f"{J(name, '은는')} 매출 [{_fmt_won(S['revenue'][li])}]에 영업이익 "
                f"{JB(_fmt_won(S['op'][li]), '으로')}, 100원당 [{op_m:.1f}원]이 남아요.",
                verdict,
            ],
            "B",
            "is-opincome",
            [{"k": "op_margin", "v": op_m}, {"k": "std_op_margin", "v": std_op_m}],
        )

    # 2) 최악의 해 — 산업 경기 동조 여부
    vi = valley_index(S["op"])
    svi = ctx["std_anchor"].get("valley_index")
    if vi is not None and svi is not None:
        same = labels[vi] == (std_years[svi] if svi < len(std_years) else None)
        peak = max(v for v in S["op"] if v is not None)
        drop = (1 - S["op"][vi] / peak) * 100 if peak else None
        std_label = ctx["std_anchor"].get("label") or "부진"
        if same:
            third = (
                "두 회사가 같은 해에 나빠졌다는 건, 이 회사만의 문제가 아니라 산업 경기가 함께 꺾였다는 "
                f"뜻이에요. 표준의 그 해 설명을 읽어 두면 이 회사의 [{labels[vi]}]도 같은 맥락으로 읽을 수 있어요."
            )
        else:
            third = (
                "표준과 다른 해에 나빠졌다는 건, 산업 경기보다 이 회사 고유의 사정이 컸다는 신호예요. "
                "무엇이 그 해를 눌렀는지는 아래 '눈여겨볼 곳'에서 주석으로 확인해 보세요."
            )
        jl = "로" if (not _tail(std_label)[0] or _tail(std_label)[1]) else "으로"
        card(
            "d2",
            f"가장 나빴던 해 — {labels[vi]}",
            [
                f"표준인 {J(std_name, '은는')} [{std_years[svi]}]이 5년 중 가장 나빴던 해예요 — "
                f"'{std_label}'{jl} 영업이익이 [{_fmt_jo(SD['op'][svi])}]까지 줄었어요.",
                f"{name}의 최저점도 [{labels[vi]}]이고, 영업이익 {JB(_fmt_won(S['op'][vi]), '으로')} "
                + (f"5년 최고치보다 [{drop:.0f}%] 적었어요." if drop else "내려앉았어요."),
                third,
            ],
            "B",
            "is-opincome",
            [{"k": "valley", "v": labels[vi]}, {"k": "std_valley", "v": std_years[svi]}],
        )

    # 3) 지금 국면 — 8상 전환
    if pattern["path"]:
        first, last = pattern["path"][0], pattern["path"][-1]
        std_code = (
            _sign(SD["ocf"][sli]) + _sign(SD["icf"][sli]) + _sign(SD["fin"][sli])
            if all(SD.get(k) for k in ("ocf", "icf", "fin"))
            else None
        )
        std_pname, std_pdesc = PATTERNS.get(std_code, ("—", "")) if std_code else ("—", "")
        changed = first["code"] != last["code"]
        line2 = (
            f"{J(name, '은는')} [{first['year']}] {first['name']}에서 [{last['year']}] "
            f"{J(last['name'], '으로')} 바뀌었어요 — {pattern['desc']}."
            if changed
            else f"{name}도 [{first['year']}]부터 [{last['year']}]까지 줄곧 {last['name']}이에요 — {pattern['desc']}."
        )
        fin_v = S["fin"][li]
        if fin_v is not None and fin_v > 0:
            third = (
                f"재무활동 현금이 (+)라는 건, 갚은 돈보다 새로 빌리거나 조달한 돈이 "
                f"{JB(_fmt_won(fin_v), '이가')} 더 많았다는 뜻이에요. 번 것만으로는 투자를 다 대지 "
                "못했다는 신호이고, 표준은 같은 해 반대로 빚을 갚고 주주에게 돌려줬어요."
            )
        else:
            third = (
                "재무활동 현금이 (−)면 번 돈으로 빚을 갚고 주주에게 돌려주는 국면이에요 — "
                "돈을 다루는 방식이 표준과 같은 방향이에요."
            )
        card(
            "d3",
            f"지금 국면 — {pattern['name']}",
            [
                f"표준인 {J(std_name, '은는')} 최근 연도가 {std_pname}이에요 — {std_pdesc}.",
                line2,
                third,
            ],
            "D",
            "cf-fin",
            [{"k": "pattern", "v": pattern["code"]}, {"k": "std_pattern", "v": std_code}],
        )

    # 4) 5년간 현금 증감
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
            "5년간 현금이 늘었나, 줄었나",
            [
                f"표준인 {J(std_name, '은는')} 5년 동안 영업·투자·재무를 모두 합친 현금이 [{_fmt_jo(std_cum)}] "
                + ("늘었어요." if std_cum >= 0 else "줄었어요."),
                f"{J(name, '은는')} "
                + ("" if cf["full"] else "현금흐름 데이터가 준비된 ")
                + f"[{yrs[0]}]부터 [{yrs[-1]}]까지 {span} 합계로 [{_fmt_won(cum)}] "
                + ("늘었어요." if cum >= 0 else "줄었어요."),
                "번 돈에서 투자·상환·배당으로 나간 돈을 뺀 값이에요. (+)가 이어지면 다음 투자를 자기 돈으로 "
                "시작할 수 있고, (−)가 이어지면 결국 외부에서 돈을 구해 와야 해요.",
            ],
            "D",
            "bs-cash",
            [{"k": "cum_net", "v": cum}, {"k": "std_cum_net", "v": std_cum}],
        )

    # 5) 가장 다른 항목 — 정규화 편차 최대 (흐름 계정만, 잔액 비교는 EQS 영역)
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
        updown = "높아요" if a > b else "낮아요"
        card(
            "d5",
            f"가장 다른 항목 — {ko}",
            [
                f"매출을 100으로 놓고 보면, 표준인 {std_name}의 {J(ko, '은는')} [{b:.1f}]이에요.",
                f"{J(name, '은는')} 같은 기준에서 [{a:.1f}]{'로' if not _tail(f'{a:.1f}')[0] else '으로'} "
                f"표준보다 [{gapv:.1f}]만큼 {updown}. 두 회사 숫자가 가장 크게 갈라지는 항목이에요.",
                "회사 크기를 지우고 구조만 남겨 비교했을 때 남는 차이라서, 이 항목이 이 회사의 구조적 "
                "특징이에요. 위 비교 차트에서 강조된 줄이 바로 여기예요.",
            ],
            "C",
            _ROW_BY_SERIES.get(gk),
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
    # 현금흐름 결측 연도를 fs_account에서 보충 (채운 값은 meta.cf_gapfill에 근거 기록)
    fys = [int(lbl.replace("FY", "20")) for lbl in labels]
    gap = load_cf_gapfill(ticker, fys)
    cf_gapfill: dict[str, dict[str, float]] = {}
    for i, lbl in enumerate(labels):
        for key in ("ocf", "icf", "fin"):
            if series[key][i] is None and gap.get(fys[i], {}).get(key) is not None:
                series[key][i] = gap[fys[i]][key]
                cf_gapfill.setdefault(lbl, {})[key] = gap[fys[i]][key]
    cf = cf_availability(series, labels)
    pattern = detect_pattern(series, labels, cf)
    norm = normalize(series)
    sd = std_series(std)
    snorm = normalize(sd)

    name = firm["corp"]["name"]
    fy = labels[-1].replace("FY", "20") if labels else ""

    # 델타 카드 서사 순서 + 연결 문구(bridge) — 위에서 아래로 하나의 이야기로 읽히게 (UX-042)
    # 수익성 격차 → 격차의 진원 → 경기 동조 → 현금 결산 → 최근 국면 전환
    CARD_ORDER: dict[str, tuple[int, str | None]] = {
        "d1": (1, None),
        "d5": (2, "그 격차가 어디서 생기는지, 숫자가 가장 크게 갈라지는 항목부터 볼게요."),
        "d2": (3, "구조가 이렇게 다른 두 회사가, 경기가 꺾일 때는 어떻게 움직였을까요?"),
        "d4": (4, "그렇게 벌고 쓴 5년의 결과, 통장에는 무엇이 남았을까요?"),
        "d3": (5, "그런데 가장 최근 연도에, 돈의 흐름이 방향을 바꿨어요."),
    }

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
        "std_doc": std,
    }
    cards = build_cards(ctx)
    for c in cards:
        o, b = CARD_ORDER.get(c["id"], (99, None))
        c["order"], c["bridge"] = o, b
    cards.sort(key=lambda c: c["order"])

    intro = [
        f"이 화면은 {J(name, '을를')} 처음부터 설명하는 곳이 아니라, 먼저 배운 표준({std['corp']['name']}) 위에 겹쳐 차이만 보는 곳이에요.",
        "표준 은하수를 아직 안 보셨다면 먼저 한 번 보고 오세요 — 여기 나오는 차이들이 훨씬 잘 읽혀요.",
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
            "cash_flow_from": None if cf["full"] else cf["from"],
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
        "pattern": {
            **pattern,
            # FY21~FY25 전 연도 경로 — 분류 불가 연도는 name=None (렌더러가 '현금흐름 미공시'로 표시)
            "path_full": [
                next((st for st in pattern["path"] if st["year"] == lbl),
                     {"year": lbl, "code": None, "name": None})
                for lbl in labels
            ],
            # 8상 전체 범례 (화면 '유형 안내' 소스 — SSOT는 이 파일의 PATTERNS)
            "legend": [
                {"code": code, "name": nm, "desc": desc}
                for code, (nm, desc) in PATTERNS.items()
            ],
        },
        "strings": {
            "header": f"{name} · FY{fy} · 연결 기준",
            "hero": f"표준({std['corp']['name']})과 무엇이 어떻게 다를까요?",
            "intro_lines": intro,
            "delta_intro": f"{name}의 5년을 표준 위에 겹치면, 이야기는 이렇게 이어져요.",
            "notes_intro": "여기서부터는 사업보고서 주석으로 내려가, 위 이야기의 이유를 따라가요.",
        },
        "cards": cards,
        "notes": [],  # LLM '주목할 점' 카드 — inject_lite_notes.py가 채운다
        "note_candidates": rmeta["note_candidates"][:8],
        "meta": {
            "generated_by": "build_galaxy_lite.py",
            "cf_gapfill": cf_gapfill,  # firm JSON 결측을 fs_account로 채운 연도·계정 (원 단위)
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
    gapfill = doc.get("meta", {}).get("cf_gapfill", {})
    for i, y in enumerate(years_raw):
        lbl = doc["years"][i]
        for src, dst in FIRM_KEYS.items():
            want = y.get(src)
            got = doc["series"][dst][i]
            if want is None and got is not None:
                gv = gapfill.get(lbl, {}).get(dst)
                if gv is None or abs(float(gv) - got) > 1:
                    errs.append(f"series.{dst}[{i}] firm 결측인데 근거(cf_gapfill) 없음")
            elif want is not None and got is None:
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
