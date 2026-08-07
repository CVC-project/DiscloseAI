"""impact_<ticker>.json 생성기 — 공시가 어느 표면에 영향을 주는지 라우팅.

설계 정본: ../v2/DISCLOSURE_TAB_PLAN.md §5 (공시 영향 라우팅)
- 수집은 하지 않는다. disclosure 모듈의 DB를 **read-only**로 읽어 분류·라우팅만 한다
  (integration/CLAUDE.md 경계: 타 모듈 파일 수정 금지, 읽기만 허용).
- 결산 스냅샷(사업보고서 rcept_no·접수일) 이후 공시 = "스냅샷 이후 변화".

Usage:
    python integration/dossier/build_disclosure_impact.py 009150
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DATA = HERE / "data"
DISCLOSURE_DB = ROOT / "modules" / "disclosure" / "data" / "disclosure.db"
REPORTS_DB = ROOT / "shared" / "data" / "reports.db"

# ---- 영향 차원 (4종) — dossier 표면과 1:1 ----
DIMS = {
    "cash": {"label": "재무구조", "surface": "현금 은하수 · EQS 재무분석", "color_key": "cyan"},
    "gov": {"label": "지배구조", "surface": "관계 지도(지배구조)", "color_key": "gold"},
    "vc": {"label": "밸류체인", "surface": "관계 지도(밸류체인)", "color_key": "mint"},
    "biz": {"label": "산업·기업", "surface": "사업·기업 탭", "color_key": "steel"},
}

# ---- 1차 라우팅: disclosure_type(collector._detect_type의 14종) → 차원 ----
TYPE_ROUTE: dict[str, list[str]] = {
    "증자": ["cash", "gov"],
    "전환사채": ["cash"],
    "BW": ["cash"],
    "채권발행": ["cash"],
    "자기주식": ["cash"],
    "최대주주변동": ["gov"],
    "임원변동": ["gov"],
    "내부자거래": ["gov"],
    "M&A/분할": ["vc", "gov"],
    "영업양도": ["vc", "gov"],
    "계약": ["vc", "biz"],
    "CAPEX": ["vc", "cash"],
    "실적": ["cash", "biz"],
    "정기보고서": ["cash", "biz"],
}

# ---- 2차 라우팅: '기타'(전체의 절반 이상)를 제목 키워드로 구제 ----
# (정규식, 차원들, 한 줄 설명) — 위에서부터 먼저 맞는 것 하나만 적용
TITLE_RULES: list[tuple[str, list[str], str]] = [
    (r"사업보고서|반기보고서|분기보고서", ["cash", "biz"], "결산 숫자가 갱신되는 공시예요 — 은하수의 기준 스냅샷이 바뀌어요."),
    (r"배당", ["cash"], "번 돈의 일부가 주주에게 나가요 — 저수지에서 물이 빠지는 자리예요."),
    (r"기업가치제고|밸류업", ["cash", "biz"], "주주환원·자본 활용 계획이라 재무 존의 방향을 예고해요."),
    (r"특수관계인|계열회사|기업집단|상품ㆍ용역거래|상품·용역거래", ["vc", "gov"], "그룹 안 거래·출자 관계라 밸류체인과 지배구조를 함께 건드려요."),
    (r"대량보유|소유주식|의결권|주주명부|주주총회|사외이사|이사의|감사", ["gov"], "누가 회사를 통제하는지에 관한 공시예요."),
    (r"합병|분할|영업양수|영업양도|주식교환", ["vc", "gov"], "사업의 경계가 바뀌어요 — 밸류체인과 지배구조가 함께 움직여요."),
    (r"공급계약|수주|납품", ["vc", "biz"], "매출이 어디서 오는지가 바뀌는 자리예요."),
    (r"투자판단|풍문|조회공시", ["biz"], "시장의 관심사에 회사가 답한 공시예요."),
    (r"기업설명회|IR", ["biz"], "회사가 사업을 직접 설명하는 자리예요."),
    (r"단일판매|공급계약체결", ["vc", "biz"], "매출이 어디서 오는지가 바뀌는 자리예요."),
    (r"지배구조보고서", ["gov"], "이사회·주주권 같은 통제 장치를 회사가 스스로 점검한 보고서예요."),
    (r"지급수단별|하도급|대금지급", ["vc"], "협력사에 언제 어떤 방식으로 돈을 주는지에 관한 공시예요 — 공급망의 현금 흐름이에요."),
    (r"지속가능경영|ESG|환경", ["biz"], "사업을 둘러싼 환경·사회 측면을 회사가 설명한 보고서예요."),
]

# ---- 유형별 "이 공시가 바꾸는 것" 1문장 (collector._CPA_TEMPLATES 취지의 경어체 축약) ----
TYPE_MEANING: dict[str, str] = {
    "증자": "새 주식을 찍어 돈을 모아요 — 현금은 늘지만 내 지분의 몫은 옅어져요.",
    "전환사채": "지금은 빚이지만 나중에 주식으로 바뀔 수 있어요 — 미래의 지분 희석을 예약한 셈이에요.",
    "BW": "빚과 함께 '주식을 살 권리'를 얹어 파는 방식이에요 — 나중에 주식 수가 늘 수 있어요.",
    "채권발행": "외부에서 돈을 빌려와요 — 재무 존의 화살표가 안쪽으로 향하는 자리예요.",
    "자기주식": "회사가 자기 주식을 사거나 없애요 — 주주에게 돌려주는 현금이에요.",
    "최대주주변동": "회사를 지배하는 사람의 지분이 움직였어요.",
    "임원변동": "회사를 운영하는 사람이 바뀌었어요.",
    "내부자거래": "임원·주요주주가 자기 회사 주식을 사고팔았어요.",
    "M&A/분할": "회사의 사업 경계가 바뀌어요 — 무엇을 하는 회사인지가 달라져요.",
    "영업양도": "사업의 일부를 넘기거나 받아요 — 매출의 구성이 바뀌어요.",
    "계약": "매출이 어디서 오는지가 바뀌는 자리예요.",
    "CAPEX": "설비에 큰돈을 넣어요 — 투자 지류가 굵어지는 자리예요.",
    "실적": "그동안의 장사 결과가 숫자로 공개돼요 — 은하수의 강폭이 갱신돼요.",
    "정기보고서": "결산 숫자가 갱신되는 공시예요 — 은하수의 기준 스냅샷이 바뀌어요.",
}

DART_URL = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo={}"


def snapshot_date(ticker: str) -> dict[str, Any]:
    """은하수 기준 스냅샷 = 최신 사업보고서의 접수일(rcept_no 앞 8자리)."""
    out = {"rcept_no": None, "date": None, "fiscal_year": None}
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
        if row:
            rc = row[0]
            out["rcept_no"], out["fiscal_year"] = rc, row[1]
            if len(rc) >= 8 and rc[:8].isdigit():
                out["date"] = f"{rc[0:4]}-{rc[4:6]}-{rc[6:8]}"
    finally:
        con.close()
    return out


def route(dtype: str, title: str) -> tuple[list[str], str, str]:
    """(차원들, 근거, 뜻) — 1차 유형 라우팅, 실패 시 2차 제목 룰."""
    t = (title or "").replace(" ", "")
    if dtype in TYPE_ROUTE:
        return TYPE_ROUTE[dtype], "type", TYPE_MEANING.get(dtype, "")
    for pat, dims, meaning in TITLE_RULES:
        if re.search(pat, t):
            return dims, "title", meaning
    return [], "none", ""


def build(ticker: str) -> dict[str, Any]:
    if not DISCLOSURE_DB.exists():
        raise SystemExit(f"[FATAL] disclosure.db 없음: {DISCLOSURE_DB}")
    snap = snapshot_date(ticker)

    con = sqlite3.connect(f"file:{DISCLOSURE_DB}?mode=ro", uri=True)
    try:
        cur = con.cursor()
        cur.execute(
            "select disclosure_id, corp_name, disclosure_date, disclosure_type, title, "
            "       summary, high_impact, dilution_ratio "
            "from disclosure_local where stock_code=? order by disclosure_date desc, disclosure_id desc",
            (ticker,),
        )
        rows = cur.fetchall()
    finally:
        con.close()

    items: list[dict[str, Any]] = []
    counts = {k: 0 for k in DIMS}
    unrouted = 0
    corp_name = ""
    for did, cname, ddate, dtype, title, summary, hi, dil in rows:
        corp_name = corp_name or (cname or "")
        dims, basis, meaning = route(dtype or "", title or "")
        if not dims:
            unrouted += 1
        after = bool(snap["date"] and ddate and str(ddate) >= snap["date"])
        for d in dims:
            counts[d] += 1
        items.append(
            {
                "id": did,
                "date": str(ddate) if ddate else None,
                "type": dtype,
                "title": (title or "").strip(),
                "dims": dims,
                "basis": basis,
                "means": meaning,
                "after_snapshot": after,
                "high_impact": bool(hi),
                "dilution_ratio": dil,
                "summary": (summary or "").strip() or None,
                "dart_url": DART_URL.format(did),
            }
        )

    after_items = [i for i in items if i["after_snapshot"]]
    after_counts = {k: 0 for k in DIMS}
    for i in after_items:
        for d in i["dims"]:
            after_counts[d] += 1

    badge_parts = [
        f"{DIMS[k]['label']} {after_counts[k]}" for k in ("cash", "gov", "vc", "biz") if after_counts[k]
    ]
    badge = (
        f"결산 이후 공시 {len(after_items)}건" + (" — " + " · ".join(badge_parts) if badge_parts else "")
        if after_items
        else f"최근 공시 {len(items)}건"
    )

    return {
        "schema_version": 1,
        "corp": {"ticker": ticker, "name": corp_name},
        "snapshot": snap,
        "dims": DIMS,
        "badge": badge,
        "counts": {"total": len(items), "after_snapshot": len(after_items),
                   "by_dim": counts, "after_by_dim": after_counts, "unrouted": unrouted},
        "items": items,
        "meta": {
            "generated_by": "build_disclosure_impact.py",
            "source": "modules/disclosure/data/disclosure.db (read-only)",
            "note": "수집 범위는 disclosure 모듈 소관 — 여기서는 분류·라우팅만 한다",
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    doc = build(args.ticker)
    path = Path(args.out) if args.out else DATA / f"impact_{args.ticker}.json"
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    c = doc["counts"]
    print(
        f"[OK] {path.name}  총 {c['total']}건 / 결산({doc['snapshot']['date']}) 이후 {c['after_snapshot']}건  "
        f"미분류 {c['unrouted']}건  차원별 {c['by_dim']}"
    )


if __name__ == "__main__":
    main()
