"""universe/export.py — relation.db → 산출물 4종 (universe/PLAN.md §4, U-D9·U-D10).

산출: universe.json · ego/<ticker>.json(전 상장사) · sectors.json · companies_index.json.
relation은 데이터만 공급 — 색 배정·렌더링은 integration 소유(§0.5 경계).

작성자 단독 원칙(U-D10): ego 파일은 이 모듈이 RelationLocal(governance)과
ValueChainEdge(valuechain) 둘 다 읽어 레이어 통합 스키마로 합성한다.

식별자 주의: RelationLocal.source_corp/target_corp는 **ticker**(6자리),
ValueChainEdge.src_corp/dst_corp는 **corp_code**(8자리) — CompanyRegistry가
둘 다 갖고 있어 이 파일에서 상호 변환한다.
"""

from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from pathlib import Path

from modules.relation.storage.db import get_local_session
from modules.relation.storage.models import CompanyRegistry, ValueChainEdge
from modules.relation.storage.queries import latest_relation_local_edges
from modules.relation.valuechain.extract.related_party import GROUP_AGGREGATE_MARK

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent / "data"
_EGO_DIR = _DATA_DIR / "ego"

# dart_filing(사업보고서 주석) 엣지의 원문 구분값 정규화.
# RelationLocal.detail에 "사업보고서 주석: 지배기업"·"대규모기업집단(*1)"·"기  타"처럼
# 접두어·주석기호·공백 변형이 섞여 들어온다. 화면 라벨로 쓰려면 표준 카테고리로 접어야 한다.
# ⚠️ rl-string은 "이름:타입:detail" 3분할 계약이라 detail에 콜론이 남으면 파싱이 깨진다 -
# 접두어 제거로 대부분 사라지지만 방어적으로 콜론을 제거한다.
_FILING_CATEGORY_RULES = [
    (("최상위", "지배기업"), "최상위 지배기업"),
    (("지배기업",), "지배기업"),
    (("종속기업",), "종속기업"),
    (("관계기업",), "관계기업"),
    (("공동기업",), "관계기업"),
    (("영향력",), "유의적 영향력"),
    (("대규모기업집단",), "대규모기업집단"),
    (("계열회사",), "대규모기업집단"),
]


def _normalize_filing_category(raw: str | None) -> str:
    if not raw:
        return ""
    s = str(raw)
    if ":" in s:
        s = s.split(":", 1)[1]
    s = re.sub(r"\((?:주|\*)[^)]*\)|\(\*\)", " ", s)  # (주1)·(*1)·(*) 주석기호 제거
    s = re.sub(r"\s+", " ", s).strip().strip(",")
    s = s.replace(":", " ").strip()
    compact = s.replace(" ", "")
    for needles, label in _FILING_CATEGORY_RULES:
        if all(n in compact for n in needles):
            return label
    if "기타" in compact or "그밖" in compact:
        return "기타"
    return s


def _edge_detail(e) -> str:
    """엣지 1건의 화면용 detail. 지분율 > 계열 그룹명 > 주석 구분 순.

    FN-010: 과거엔 ratio·group_name만 보고 없으면 빈 문자열을 내보내 dart_filing의
    '지배기업/관계기업/대규모기업집단' 구분이 통째로 유실됐다(DB에는 있었음).

    ★2026-07-29: "그룹 합산" 마커는 **정규화 뒤에** 다시 붙인다 —
    _normalize_filing_category는 표준 카테고리로 접는 함수라 마커를 그냥 두면
    규칙 매칭 과정에서 사라진다(예: "대규모기업집단 (그룹 합산)" → "대규모기업집단").
    원문이 단일 회사가 아니라 그룹 전체를 가리킨다는 사실은 화면에 남아야 한다
    (리더 판정: "지배기업이 회사 단일로 지배하는 것은 아니다").
    ⚠️ 마커에 콜론을 쓰지 않는다 — rl-string "이름:타입:detail" 3분할 계약.
    """
    if e.ratio is not None:
        return f"{e.ratio}%"
    if e.group_name:
        return str(e.group_name).replace(":", " ")
    label = _normalize_filing_category(e.detail)
    if GROUP_AGGREGATE_MARK in (e.detail or ""):
        label = f"{label} ({GROUP_AGGREGATE_MARK})".strip()
    return label

_SECTOR_ID_TO_KO = {
    "semi": "반도체", "fin": "금융", "it": "플랫폼", "auto": "자동차",
    "pharma": "제약바이오", "energy": "에너지", "indust": "중공업·방산",
    "cons": "건설", "tele": "통신", "etc": "기타", "food": "식음료",
    "textile": "섬유·의류", "materials": "소재", "media": "미디어",
    "chem": "화학", "steel": "철강·금속", "elec_parts": "전기전자부품",
    "machinery": "기계·장비", "retail": "유통", "logistics": "운송·물류",
    "leisure": "레저·교육", "holding": "지주", "prof_svc": "전문서비스",
    "realestate": "부동산", "cosmetics": "화장품",
}


def _sector_ko(sector_id: str | None) -> str:
    return _SECTOR_ID_TO_KO.get(sector_id or "", "기타")


def _dot_layout(rank_in_sector: int) -> tuple[float, float]:
    """dot 배치 좌표 — 결정적 스파이럴(placeholder, U2에서 integration이 정교화 가능).

    rank_in_sector: 그 섹터 내 dot 순번(0-base). 골든비 각도로 균등 분산.
    """
    import math

    golden_angle = math.pi * (3 - math.sqrt(5))
    radius = 0.5 + 0.08 * math.sqrt(rank_in_sector)
    angle = rank_in_sector * golden_angle
    return round(radius * math.cos(angle), 3), round(radius * math.sin(angle), 3)


def _cap_bucket(market_cap_krw: float | None) -> int:
    """시총 → dot 크기 버킷 0~3 (조원 기준 대략 구간)."""
    if not market_cap_krw:
        return 0
    jo = market_cap_krw / 1_000_000_000_000
    if jo >= 5:
        return 3
    if jo >= 1:
        return 2
    if jo >= 0.2:
        return 1
    return 0


def _load_all(session):
    companies = session.query(CompanyRegistry).all()
    by_ticker = {c.ticker: c for c in companies if c.ticker}
    by_corp_code = {c.corp_code: c for c in companies}
    return companies, by_ticker, by_corp_code


def export_universe_json(session, output_path: Path | None = None) -> dict:
    """universe.json — meta + sectors(집계+dots 좌표) + named(top-400 + 상호 rl)."""
    companies, by_ticker, _ = _load_all(session)
    named = [c for c in companies if c.universe_tier == "named400"]
    dots = [c for c in companies if c.universe_tier == "dot"]

    # 섹터별 집계 + dot 좌표
    dots_by_sector: dict[str, list] = defaultdict(list)
    for c in sorted(dots, key=lambda x: -(x.market_cap_krw or 0)):
        dots_by_sector[c.sector_id or "etc"].append(c)

    sector_agg: dict[str, dict] = {}
    for c in companies:
        sid = c.sector_id or "etc"
        agg = sector_agg.setdefault(sid, {"count": 0, "cap": 0.0})
        agg["count"] += 1
        agg["cap"] += (c.market_cap_krw or 0) / 1_000_000_000_000  # 조원

    sectors_out = []
    for sid, agg in sorted(sector_agg.items(), key=lambda kv: -kv[1]["cap"]):
        dot_list = dots_by_sector.get(sid, [])
        sectors_out.append(
            {
                "id": sid,
                "ko": _sector_ko(sid),
                "count": agg["count"],
                "cap": round(agg["cap"], 1),
                "dots": [
                    [*(_dot_layout(i)), _cap_bucket(c.market_cap_krw)]
                    for i, c in enumerate(dot_list)
                ],
            }
        )

    # named 상호 간 rl (governance만 — RelationLocal, ticker 기준)
    named_tickers = {c.ticker for c in named}
    rl_by_ticker: dict[str, list[tuple]] = defaultdict(list)
    edges = [
        e
        for e in latest_relation_local_edges(session)
        if e.source_corp in named_tickers and e.target_corp in named_tickers
    ]
    for e in edges:
        target = by_ticker.get(e.target_corp)
        if not target:
            continue
        detail = _edge_detail(e)
        ratio_sort = -(e.ratio if e.ratio is not None else -1)
        rl_by_ticker[e.source_corp].append(
            (ratio_sort, f"{target.name_current}:{e.relation_type}:{detail}".replace("\n", " "))
        )

    named_out = []
    max_cap = max((c.market_cap_krw or 0) for c in named) or 1
    for c in sorted(named, key=lambda x: x.universe_rank or 999999):
        rl_sorted = sorted(rl_by_ticker.get(c.ticker, []), key=lambda x: x[0])
        named_out.append(
            {
                "n": c.name_current,
                "t": c.ticker,
                "s": _sector_ko(c.sector_id),
                "mkt": c.market,  # KOSPI|KOSDAQ — U2 시장별 성운 분할용(integration LOD)
                "sz": round((c.market_cap_krw or 0) / max_cap, 4),
                "mc": f"{round((c.market_cap_krw or 0) / 1_000_000_000_000, 1)}조",
                "group": None,  # FTC 집단명은 ego 파일의 governance layer에서 확인 (U2 시각화 시 파생 가능)
                "rank": c.universe_rank,
                "rl": [item[1] for item in rl_sorted],
            }
        )

    max_cap_asof = max((c.cap_asof for c in companies if c.cap_asof), default=None)
    payload = {
        "meta": {"as_of": max_cap_asof, "named_count": len(named), "total": len(companies)},
        "sectors": sectors_out,
        "named": named_out,
    }
    path = output_path or (_DATA_DIR / "universe.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def export_sectors_json(session, output_path: Path | None = None) -> list[dict]:
    """sectors.json — SECTOR_DEF/PALETTE 정합화(V-2)용 섹터 목록 handoff (색 배정은 integration)."""
    companies, _, _ = _load_all(session)
    counts: dict[str, int] = defaultdict(int)
    for c in companies:
        counts[c.sector_id or "etc"] += 1
    payload = [
        {"id": sid, "ko": _sector_ko(sid), "count": n}
        for sid, n in sorted(counts.items(), key=lambda kv: -kv[1])
    ]
    path = output_path or (_DATA_DIR / "sectors.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def export_companies_index_json(session, output_path: Path | None = None) -> list[dict]:
    """companies_index.json — 전 상장사 검색 타이프어헤드 경량 인덱스."""
    companies, _, _ = _load_all(session)
    payload = [
        {
            "t": c.ticker,
            "n": c.name_current,
            "s": _sector_ko(c.sector_id),
            "tier": c.universe_tier,
            "mkt": c.market,  # KOSPI|KOSDAQ — U2 시장별 성운 분할 dots 배치용
            # capBucket: 시총 조원 규모(0~) — dot 크기용. named는 universe.json에서 상세 확보.
            "cb": _cap_bucket(c.market_cap_krw),
        }
        for c in companies
        if c.ticker
    ]
    path = output_path or (_DATA_DIR / "companies_index.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def _build_ego_payload(
    company: CompanyRegistry,
    gov_edges: list,
    vc_up: list[ValueChainEdge],
    vc_down: list[ValueChainEdge],
    by_ticker: dict[str, CompanyRegistry],
    by_corp_code: dict[str, CompanyRegistry],
) -> dict:
    governance = []
    for e in gov_edges:
        is_source = e.source_corp == company.ticker
        neighbor_ticker = e.target_corp if is_source else e.source_corp
        neighbor = by_ticker.get(neighbor_ticker)
        if not neighbor:
            continue
        detail = _edge_detail(e)
        governance.append(
            {
                "t": neighbor.ticker,
                "n": neighbor.name_current,
                "type": e.relation_type,
                "detail": detail,
                "dir": "out" if is_source else "in",
                "s": _sector_ko(neighbor.sector_id),
                "tier": neighbor.universe_tier or "dot",
            }
        )

    def _vc_side(edges: list[ValueChainEdge], other_attr: str) -> list[dict]:
        out = []
        for e in edges:
            other_code = getattr(e, other_attr)
            other = by_corp_code.get(other_code)
            if not other:
                continue
            out.append(
                {
                    "t": other.ticker,
                    "n": other.name_current,
                    "type": e.edge_type,
                    "tier_grade": e.tier,
                    "amount": e.amount,
                    "as_of": e.as_of,
                    "prov": e.provenance,
                }
            )
        return out

    return {
        "t": company.ticker,
        "n": company.name_current,
        "s": _sector_ko(company.sector_id),
        "tier": company.universe_tier or "dot",
        "layers": {
            "governance": governance,
            "valuechain": {
                "up": _vc_side(vc_up, "src_corp"),
                "down": _vc_side(vc_down, "dst_corp"),
            },
        },
    }


def export_ego_files(session, output_dir: Path | None = None) -> dict:
    """ego/<ticker>.json 전 상장사 생성 — governance(RelationLocal)+valuechain(ValueChainEdge) 통합.

    Returns: {'written': int, 'manifest_path': str}
    """
    companies, by_ticker, by_corp_code = _load_all(session)
    ego_dir = output_dir or _EGO_DIR
    ego_dir.mkdir(parents=True, exist_ok=True)

    gov_edges = latest_relation_local_edges(session)
    gov_by_ticker: dict[str, list] = defaultdict(list)
    for e in gov_edges:
        gov_by_ticker[e.source_corp].append(e)
        if e.target_corp != e.source_corp:
            gov_by_ticker[e.target_corp].append(e)

    # ★2026-07-29 신선도 필터(리더 결정, valuechain/freshness.py 정본) — 상세는 그 모듈 docstring
    from modules.relation.valuechain.freshness import fresh_edges
    vc_edges, _fresh_counters = fresh_edges(session)
    vc_up_by_corp: dict[str, list] = defaultdict(list)  # 이 회사가 dst(수요자) — 상류=공급처
    vc_down_by_corp: dict[str, list] = defaultdict(list)  # 이 회사가 src(공급자) — 하류=고객
    for e in vc_edges:
        vc_up_by_corp[e.dst_corp].append(e)
        vc_down_by_corp[e.src_corp].append(e)

    written = 0
    manifest = []
    for c in companies:
        if not c.ticker:
            continue
        payload = _build_ego_payload(
            c,
            gov_by_ticker.get(c.ticker, []),
            vc_up_by_corp.get(c.corp_code, []),
            vc_down_by_corp.get(c.corp_code, []),
            by_ticker,
            by_corp_code,
        )
        path = ego_dir / f"{c.ticker}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        written += 1
        manifest.append(c.ticker)

    manifest_path = ego_dir / "manifest.json"
    manifest_path.write_text(json.dumps(sorted(manifest)), encoding="utf-8")
    return {"written": written, "manifest_path": str(manifest_path)}


def export_all(session=None) -> dict:
    """4종 산출물 전부 생성. session 미지정 시 로컬 relation.db."""
    owns_session = session is None
    if owns_session:
        session = get_local_session()
    try:
        universe = export_universe_json(session)
        sectors = export_sectors_json(session)
        index = export_companies_index_json(session)
        ego = export_ego_files(session)
    finally:
        if owns_session:
            session.close()
    result = {
        "universe_named": universe["meta"]["named_count"],
        "universe_total": universe["meta"]["total"],
        "sectors": len(sectors),
        "companies_index": len(index),
        "ego_written": ego["written"],
    }
    logger.info(f"universe export 완료: {result}")
    return result


if __name__ == "__main__":
    import json as _json

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print(_json.dumps(export_all(), ensure_ascii=False, indent=2))
