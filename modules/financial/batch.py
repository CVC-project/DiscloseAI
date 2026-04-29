"""KOSPI 50 등 다수 기업 batch 수집 + EQS 일괄 계산.

이름 매칭의 함정:
- DART 정식명과 시장 통용명이 다른 경우 (현대차/현대자동차, KT&G/케이티앤지)
- 우선주는 별도 종목코드를 가지지만 corp_code는 본주와 같음 → 본주와 재무가
  동일하여 분석 중복이므로 universe에서 제외 (삼성전자우 등)
- ETF는 재무제표가 없어 제외 (KODEX 200 등)

해결: ``ALIASES``에 시장 통용명 → 종목코드를 명시. find_corp가 종목코드로
6자리 정확매칭하므로 안전.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

from .collector import CorpInfo, find_corp, fetch_panel, fetch_latest_report_url
from .eqs import compute_eqs
from .eqs.types import EQSResult, FirmPanel

# 시장 통용명 → 종목코드(6자리) 또는 corp_code(8자리) 매핑.
# - 부분매칭 휴리스틱이 잘못 잡는 경우(현대차→현대차증권) 방지
# - 정식 corp_name이 다른 경우(NAVER→네이버) 보강
ALIASES = {
    "현대차": "005380",  # 정식명: 현대자동차
    "기아": "000270",
    "셀트리온": "068270",
    "LS ELECTRIC": "010120",
    "카카오": "035720",
    "LIG넥스원": "079550",
    "KT&G": "033780",
    "NAVER": "035420",  # 정식명: 네이버
    "삼성물산": "028260",  # find_corp 부분매칭이 다른 삼성물산을 잡음
    "미래에셋증권": "006800",
    "SK": "034730",  # SK(주) — 자회사가 너무 많아 부분매칭 위험
    "우리금융지주": "316140",
}

# 재무제표가 없는 종목 (ETF, REIT 등) — 분석 대상에서 제외.
# 현재 universe(KOSPI_TOP_50)에는 ETF가 포함되어 있지 않지만, 입력 단계 안전망으로
# 빈 set 유지. 향후 ETF 의심 종목 추가 시 여기에 등록.
INSTRUMENT_BLACKLIST: set[str] = set()

# 금융업 (KRX 업종코드 064~067) — fnlttSinglAcntAll endpoint가 옛 데이터 미제공.
# CLAUDE.local.md 규칙대로 M2·M3 자동 제외 + 별도 BIS 모듈 도입 시까지 EQS 보류.
# KOSPI 50 명단 기준 자동 분류용 — KRX 정식 분류 연동 전까지 하드코딩.
_FINANCIAL_INDUSTRIES = {
    "KB금융": "064",  # 은행지주
    "신한지주": "064",
    "하나금융지주": "064",
    "우리금융지주": "064",
    "메리츠금융지주": "064",
    "미래에셋증권": "066",  # 증권
    "삼성생명": "067",  # 보험
    "삼성화재": "067",
}

# 지주·투자회사 — 자회사 지분법이익이 주수익이라 M1(발생액 품질)의
# 단일기업 fallback이 '이상 발생액'으로 오인. industry.py excluded_modules에서
# M1 자동 제외. 내부 코드 "100".
_HOLDING_COMPANIES = {
    "SK스퀘어": "100",  # SK하이닉스 지분 보유
    "SK": "100",  # SK그룹 지주
    "HD현대": "100",  # HD그룹 지주
    "두산": "100",  # 두산그룹 지주
    "삼성물산": "100",  # 삼성그룹 사실상 지주 역할
}


def _industry_for(name: str) -> Optional[str]:
    """이름 기반 업종코드 추정. 금융 > 지주 > 일반 순. 미상이면 None."""
    if name in _FINANCIAL_INDUSTRIES:
        return _FINANCIAL_INDUSTRIES[name]
    if name in _HOLDING_COMPANIES:
        return _HOLDING_COMPANIES[name]
    return None


KOSPI_TOP_50 = [
    "삼성전자",
    "SK하이닉스",
    "현대차",
    "LG에너지솔루션",
    "한화에어로스페이스",
    "SK스퀘어",
    "삼성바이오로직스",
    "두산에너빌리티",
    "KB금융",
    "기아",
    "HD현대중공업",
    "삼성생명",
    "삼성물산",
    "신한지주",
    "셀트리온",
    "삼성전기",
    "삼성SDI",
    "한화오션",
    "HD현대일렉트릭",
    "미래에셋증권",
    "현대모비스",
    "고려아연",
    "하나금융지주",
    "NAVER",
    "POSCO홀딩스",
    "효성중공업",
    "HD한국조선해양",
    "한국전력",
    "LS ELECTRIC",
    "한미반도체",
    "SK",
    "우리금융지주",
    "한화시스템",
    "삼성중공업",
    "LG화학",
    "현대로템",
    "삼성화재",
    "두산",
    "카카오",
    "LIG넥스원",
    "SK이노베이션",
    "HMM",
    "SK텔레콤",
    "현대건설",
    "HD현대",
    "메리츠금융지주",
    "포스코퓨처엠",
    "KT&G",
]


@dataclass
class FirmRecord:
    """수집·분석 결과 1행."""

    display_name: str  # 사용자 입력명
    corp: Optional[CorpInfo]
    panel: Optional[FirmPanel] = None
    eqs: Optional[EQSResult] = None
    market_cap: Optional[float] = None  # 시가총액 (원), yfinance에서
    industry_code: Optional[str] = None  # 064~067이면 금융업
    dart_url: Optional[str] = None  # DART 최신 사업보고서 URL
    error: Optional[str] = None


def resolve_corp(name: str) -> Optional[CorpInfo]:
    """입력명을 CorpInfo로 변환. ALIASES → 정확매칭 → 부분매칭 순.

    ALIASES 값:
    - 6자리 숫자: 종목코드 → find_corp이 종목코드로 매칭
    - 8자리 숫자: corp_code → DART 매핑에서 직접 lookup (우선주처럼 별도
      stock_code가 없는 경우)
    - 그 외: 정식 회사명 → find_corp 정확매칭
    """
    if name in INSTRUMENT_BLACKLIST:
        return None
    key = ALIASES.get(name, name)
    if key.isdigit() and len(key) == 8:
        # corp_code 직접 lookup
        from .collector import fetch_corp_codes

        for c in fetch_corp_codes():
            if c.corp_code == key:
                return c
        return None
    return find_corp(key)


def fetch_market_cap(stock_code: str) -> Optional[float]:
    """yfinance에서 시가총액(원). KOSPI는 .KS suffix.

    yfinance는 비공식 API라 종종 None/예외 발생 — 호출자에서 None 처리.
    """
    try:
        import yfinance as yf

        ticker = yf.Ticker(f"{stock_code}.KS")
        info = ticker.info
        return info.get("marketCap")
    except Exception:  # noqa: BLE001
        return None


def collect_batch(
    names: Iterable[str],
    year_range: Iterable[int],
    *,
    sleep_sec: float = 0.1,
    progress: bool = True,
    fetch_market_caps: bool = True,
) -> List[FirmRecord]:
    """이름 리스트 → 패널 + EQS 결과 + 시가총액. 실패는 record.error에 기록."""
    name_list = list(names)
    n = len(name_list)
    out: List[FirmRecord] = []
    for i, name in enumerate(name_list, 1):
        if name in INSTRUMENT_BLACKLIST:
            out.append(FirmRecord(name, None, error="ETF/REIT 등 재무제표 비대상"))
            if progress:
                print(f"[{i:2d}/{n}] {name}: 제외 (instrument blacklist)")
            continue
        corp = resolve_corp(name)
        if corp is None:
            out.append(FirmRecord(name, None, error="corp_code 매칭 실패"))
            if progress:
                print(f"[{i:2d}/{n}] {name}: 매칭 실패")
            continue

        industry = _industry_for(name)
        market_cap = (
            fetch_market_cap(corp.stock_code)
            if fetch_market_caps and corp.stock_code
            else None
        )
        dart_url = fetch_latest_report_url(corp.corp_code)

        try:
            panel = fetch_panel(
                corp.corp_code,
                year_range,
                corp_name=name,
                industry_code=industry,
                sleep_sec=sleep_sec,
            )
            eqs = compute_eqs(panel)
            out.append(
                FirmRecord(
                    name,
                    corp,
                    panel=panel,
                    eqs=eqs,
                    market_cap=market_cap,
                    industry_code=industry,
                    dart_url=dart_url,
                )
            )
            if progress:
                tot = eqs.total if eqs.total is not None else "—"
                grade = eqs.grade or "—"
                if industry and industry.startswith("100"):
                    tag = " [지주]"
                elif industry:
                    tag = " [금융]"
                else:
                    tag = ""
                cap_str = f" cap={market_cap/1e12:.1f}조" if market_cap else ""
                print(
                    f"[{i:2d}/{n}] {name} ({corp.stock_code}){tag}: {len(panel.years)}년 → EQS={tot} ({grade}){cap_str}"
                )
        except Exception as e:  # noqa: BLE001 — 한 종목 실패가 전체를 막지 않도록
            out.append(
                FirmRecord(
                    name,
                    corp,
                    market_cap=market_cap,
                    industry_code=industry,
                    dart_url=dart_url,
                    error=f"{type(e).__name__}: {e}",
                )
            )
            if progress:
                print(f"[{i:2d}/{n}] {name}: 에러 {e}")
    return out


def build_sector_stats(records: List[FirmRecord]) -> dict:
    """배치 결과 → 섹터별 평균 수익성 비율 + 캐시 저장.

    각 FirmRecord의 가장 최근 연도 비율을 뽑아 industry_groups에서 집계.
    저장 경로(JSON)를 반환. dashboard.py가 이 파일을 로드해 '업계 대비' 섹션 렌더링.
    """
    from .industry_groups import compute_sector_stats, save_sector_stats
    from .translator.ratios import compute_ratios

    company_ratios: dict = {}
    for r in records:
        if r.panel is None or r.error is not None:
            continue
        latest = r.panel.latest()
        if latest is None:
            continue
        company_ratios[r.display_name] = compute_ratios(latest).as_dict()

    stats = compute_sector_stats(company_ratios)
    return {
        "cache_path": save_sector_stats(stats),
        "sectors_computed": len(stats),
        "total_companies": sum(s.n_companies for s in stats.values()),
    }


_MODULE_LABELS = {
    "M1": "현금이익률",
    "M2": "매출 회수 건전성",
    "M3": "부채 건전성",
    "M4": "본업 안정성",
    "M5": "자본 성장성",
}


def _to_eok(v):
    """원 → 억원 변환. None이면 None."""
    if v is None:
        return None
    return round(v / 1e8)


def _history_block(panel: FirmPanel) -> Optional[dict]:
    """5년 시계열을 sparkline용 JSON 블록으로 직렬화 (억원 단위).

    panel.years는 (year, quarter) 오름차순 정렬됨. 연간 결산만 추출 후
    매출/영업이익/순이익/영업CF 4개 지표를 array로 반환. 누락 연도는 None
    으로 채워 array 길이를 일정하게 유지 (sparkline에서 점 누락 처리).
    """
    annual = [fy for fy in (panel.years or []) if fy.quarter is None]
    if not annual:
        return None
    return {
        "years": [fy.year for fy in annual],
        "revenue": [_to_eok(fy.revenue) for fy in annual],
        "operating_income": [_to_eok(fy.operating_income) for fy in annual],
        "net_income": [_to_eok(fy.net_income) for fy in annual],
        "operating_cashflow": [_to_eok(fy.operating_cashflow) for fy in annual],
    }


def _compute_industry_percentiles(records: List[FirmRecord]) -> dict:
    """동종업계(섹터) 내 firm 단위 백분위 산출 — 0(최하)~100(최상).

    그룹키: ``industry_groups.get_sector(name)`` (KOSPI 50 11개 섹터).
    표본 < 3인 섹터는 백분위 산출 부적절 → ``_industry_size``만 기록.

    metrics:
      - operating_margin (%) : 영업이익/매출 — 높을수록 좋음
      - debt_to_equity (%)   : 부채총계/자본총계 — 낮을수록 좋음 (반전)
      - ocf_to_revenue (%)   : 영업CF/매출 — 높을수록 좋음
      - eqs_total            : EQS 종합점수 — 높을수록 좋음
    """
    from .industry_groups import get_sector

    groups: dict = {}
    for r in records:
        if r.corp is None or r.panel is None or r.error is not None:
            continue
        sec = get_sector(r.display_name)
        if not sec:
            continue
        groups.setdefault(sec, []).append(r)

    def _operating_margin(r: FirmRecord) -> Optional[float]:
        l = r.panel.latest() if r.panel else None
        if l is None or not l.revenue or l.operating_income is None:
            return None
        return l.operating_income / l.revenue * 100

    def _debt_to_equity(r: FirmRecord) -> Optional[float]:
        l = r.panel.latest() if r.panel else None
        if (
            l is None
            or l.total_equity is None
            or l.total_equity <= 0
            or l.total_liabilities is None
        ):
            return None
        return l.total_liabilities / l.total_equity * 100

    def _ocf_to_revenue(r: FirmRecord) -> Optional[float]:
        l = r.panel.latest() if r.panel else None
        if l is None or not l.revenue or l.operating_cashflow is None:
            return None
        return l.operating_cashflow / l.revenue * 100

    def _eqs_total(r: FirmRecord) -> Optional[float]:
        return r.eqs.total if (r.eqs and r.eqs.total is not None) else None

    metrics = [
        ("operating_margin", _operating_margin, "high"),
        ("debt_to_equity", _debt_to_equity, "low"),
        ("ocf_to_revenue", _ocf_to_revenue, "high"),
        ("eqs_total", _eqs_total, "high"),
    ]

    out: dict = {}
    for sector, group in groups.items():
        size = len(group)
        # 모든 firm에 sector·size 기록
        for r in group:
            out[r.corp.corp_code] = {"_sector": sector, "_size": size}
        if size < 3:
            continue
        for metric_name, extractor, direction in metrics:
            valid = [(r, extractor(r)) for r in group]
            valid = [(r, v) for r, v in valid if v is not None]
            if len(valid) < 3:
                continue
            # direction='high' → 큰 값이 1등 (rank 0); 'low' → 작은 값이 1등
            valid_sorted = sorted(
                valid, key=lambda x: x[1], reverse=(direction == "high")
            )
            n = len(valid_sorted)
            for rank, (r, _) in enumerate(valid_sorted):
                # rank 0(최상위) → 100, rank n-1(최하위) → 0
                pct = round((n - 1 - rank) / (n - 1) * 100) if n > 1 else 50
                out[r.corp.corp_code][metric_name] = pct
    return out


def export_for_frontend(
    records: List[FirmRecord],
    output_dir: Optional[str] = None,
    *,
    output_name: str = "eqs_data.json",
) -> str:
    """relation/price 등 다른 모듈이 사용할 종목별 EQS 데이터 JSON 내보내기.

    행성 클릭 시 표시할 데이터:
    - name, stock_code, market_cap, grade, total(평균점수)
    - modules: M1~M5 각 점수 + 한글 라벨 + note(산출 방식)
    - dart_url: 최신 사업보고서 링크
    - latest_year: 최근 재무 데이터(매출, 영업이익, 순이익, 영업CF 등)
    """
    import json

    out_dir = output_dir or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "docs",
        "prototype",
    )
    os.makedirs(out_dir, exist_ok=True)

    percentiles = _compute_industry_percentiles(records)

    items = []
    for r in records:
        if r.eqs is None:
            continue
        # 모듈별 점수
        modules = {}
        for m in r.eqs.modules:
            modules[m.name] = {
                "label": _MODULE_LABELS.get(m.name, m.name),
                "score": m.score,
                "note": m.note or "",
            }
        # 최근 연도 재무 요약
        latest = r.panel.latest() if r.panel else None
        latest_year = None
        if latest:
            latest_year = {
                "year": latest.year,
                "revenue": _to_eok(latest.revenue),
                "operating_income": _to_eok(latest.operating_income),
                "net_income": _to_eok(latest.net_income),
                "operating_cashflow": _to_eok(latest.operating_cashflow),
                "investing_cashflow": _to_eok(latest.investing_cashflow),
                "financing_cashflow": _to_eok(latest.financing_cashflow),
                "total_assets": _to_eok(latest.total_assets),
                "total_equity": _to_eok(latest.total_equity),
            }

        items.append(
            {
                "name": r.display_name,
                "stock_code": r.corp.stock_code if r.corp else None,
                "corp_code": r.corp.corp_code if r.corp else None,
                "market_cap": r.market_cap,
                "grade": r.eqs.grade,
                "total": r.eqs.total,
                "modules": modules,
                "dart_url": r.dart_url,
                "latest_year": latest_year,
                "industry_code": r.industry_code,
                "history": _history_block(r.panel) if r.panel else None,
                "percentile": percentiles.get(
                    r.corp.corp_code if r.corp else "", None
                ),
            }
        )

    out_path = os.path.join(out_dir, output_name)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    return out_path


def build_per_firm_dashboards(records: List[FirmRecord]) -> dict:
    """각 기업별 단독 분석 HTML 생성 — 통합 대시보드 오버레이용.

    파일명: ``firm_<ticker>.html`` (ticker 없으면 corp_code 사용).
    자체완결형 — DATA를 인라인 임베드하므로 file:// 환경에서도 동작.
    """
    from .dashboard import build_dashboard
    from .translator import extract_highlights, translate_all

    written = 0
    skipped = 0
    for r in records:
        if r.corp is None or r.panel is None or r.eqs is None or r.error is not None:
            skipped += 1
            continue
        latest = r.panel.latest()
        if latest is None:
            skipped += 1
            continue
        ticker = r.corp.stock_code or r.corp.corp_code
        try:
            build_dashboard(
                r.panel,
                r.eqs,
                translate_all(latest),
                extract_highlights(r.panel),
                output_name=f"firm_{ticker}.html",
            )
            written += 1
        except Exception:  # noqa: BLE001 — 한 기업 실패가 전체를 막지 않도록
            skipped += 1
    return {"written": written, "skipped": skipped}


def persist_to_db(records: List[FirmRecord]) -> dict:
    """배치 결과를 modules/financial/data/financial.db (financial_local)에 upsert.

    각 기업의 최근 연도 1행만 저장 — extract_data.py가 'corp_code별 최신 1건'
    으로 읽기 때문에 latest year만 있으면 충분. 동일 corp_code의 기존 행은
    DELETE 후 INSERT (단순 upsert + 중복 정리).

    EQS 5모듈/총점/등급은 latest year 행에 함께 attach.
    재무수치는 **억원 단위**로 저장 (기존 financial_local 컨벤션 유지) —
    integration의 dashboard.html은 억→조(/10000) 변환을 가정한다.
    """
    from .db import get_local_session, init_local_db
    from .models import FinancialLocal

    init_local_db()  # 테이블 없으면 생성
    session = get_local_session()
    written = 0
    skipped = 0
    try:
        for r in records:
            if r.corp is None or r.panel is None or r.error is not None:
                skipped += 1
                continue
            latest = r.panel.latest()
            if latest is None:
                skipped += 1
                continue
            # 동일 corp_code 기존 행 삭제 (중복 정리 + upsert)
            session.query(FinancialLocal).filter(
                FinancialLocal.corp_code == r.corp.corp_code
            ).delete(synchronize_session=False)

            # EQS 모듈 점수 추출 (있는 경우)
            mod_scores = {}
            eqs_total = None
            eqs_grade = None
            if r.eqs is not None:
                eqs_total = r.eqs.total
                eqs_grade = r.eqs.grade
                for m in r.eqs.modules:
                    mod_scores[m.name] = m.score

            session.add(
                FinancialLocal(
                    corp_code=r.corp.corp_code,
                    corp_name=r.display_name,
                    year=latest.year,
                    quarter=latest.quarter,
                    revenue=_to_eok(latest.revenue),
                    operating_income=_to_eok(latest.operating_income),
                    net_income=_to_eok(latest.net_income),
                    total_assets=_to_eok(latest.total_assets),
                    total_liabilities=_to_eok(latest.total_liabilities),
                    total_equity=_to_eok(latest.total_equity),
                    operating_cashflow=_to_eok(latest.operating_cashflow),
                    investing_cashflow=_to_eok(latest.investing_cashflow),
                    financing_cashflow=_to_eok(latest.financing_cashflow),
                    eqs_m1=mod_scores.get("M1"),
                    eqs_m2=mod_scores.get("M2"),
                    eqs_m3=mod_scores.get("M3"),
                    eqs_m4=mod_scores.get("M4"),
                    eqs_m5=mod_scores.get("M5"),
                    eqs_total=eqs_total,
                    eqs_grade=eqs_grade,
                )
            )
            written += 1
        session.commit()
    finally:
        session.close()
    return {"written": written, "skipped": skipped}


def summarize(records: List[FirmRecord]) -> dict:
    """배치 결과 요약 통계."""
    ok = [r for r in records if r.eqs and r.eqs.total is not None]
    grade_dist = {g: 0 for g in ("A", "B", "C", "D", "F")}
    for r in ok:
        grade_dist[r.eqs.grade] = grade_dist.get(r.eqs.grade, 0) + 1
    # 모듈별 평균
    module_means: dict = {}
    for mod_name in ("M1", "M2", "M3", "M4", "M5"):
        scores = []
        for r in ok:
            for m in r.eqs.modules:
                if m.name == mod_name and m.score is not None:
                    scores.append(m.score)
        module_means[mod_name] = round(sum(scores) / len(scores), 1) if scores else None
    return {
        "total_count": len(records),
        "success_count": len(ok),
        "fail_count": len(records) - len(ok),
        "grade_distribution": grade_dist,
        "module_means": module_means,
        "avg_total": round(sum(r.eqs.total for r in ok) / len(ok), 1) if ok else None,
    }
