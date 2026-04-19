"""KOSPI 50 등 다수 기업 batch 수집 + EQS 일괄 계산.

이름 매칭의 함정:
- DART 정식명과 시장 통용명이 다른 경우 (현대차/현대자동차, KT&G/케이티앤지)
- 우선주는 별도 종목코드를 가지지만 corp_code는 본주와 같음
- ETF는 재무제표가 없어 제외 필요

해결: ``ALIASES``에 시장 통용명 → 종목코드를 명시. find_corp가 종목코드로
6자리 정확매칭하므로 안전.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

from .collector import CorpInfo, find_corp, fetch_panel
from .eqs import compute_eqs
from .eqs.types import EQSResult, FirmPanel

# 시장 통용명 → 종목코드(6자리) 또는 corp_code(8자리) 매핑.
# - 부분매칭 휴리스틱이 잘못 잡는 경우(현대차→현대차증권) 방지
# - 정식 corp_name이 다른 경우(NAVER→네이버) 보강
# - 우선주는 DART에 별도 등록되지 않으므로 본주 corp_code(8자리)로 직접 매핑
ALIASES = {
    "삼성전자우": "00126380",  # corp_code 직접 매핑 (본주와 동일 재무제표)
    "현대차": "005380",        # 정식명: 현대자동차
    "기아": "000270",
    "셀트리온": "068270",
    "LS ELECTRIC": "010120",
    "카카오": "035720",
    "LIG넥스원": "079550",
    "KT&G": "033780",
    "NAVER": "035420",         # 정식명: 네이버
    "삼성물산": "028260",       # find_corp 부분매칭이 다른 삼성물산을 잡음
    "미래에셋증권": "006800",
    "SK": "034730",            # SK(주) — 자회사가 너무 많아 부분매칭 위험
    "우리금융지주": "316140",
}

# 재무제표가 없는 종목 (ETF, REIT 등) — 분석 대상에서 제외
INSTRUMENT_BLACKLIST = {"KODEX 200"}

# 금융업 (KRX 업종코드 064~067) — fnlttSinglAcntAll endpoint가 옛 데이터 미제공.
# CLAUDE.local.md 규칙대로 M2·M3 자동 제외 + 별도 BIS 모듈 도입 시까지 EQS 보류.
# KOSPI 50 명단 기준 자동 분류용 — KRX 정식 분류 연동 전까지 하드코딩.
_FINANCIAL_INDUSTRIES = {
    "KB금융": "064",          # 은행지주
    "신한지주": "064",
    "하나금융지주": "064",
    "우리금융지주": "064",
    "메리츠금융지주": "064",
    "미래에셋증권": "066",     # 증권
    "삼성생명": "067",         # 보험
    "삼성화재": "067",
}

# 지주·투자회사 — 자회사 지분법이익이 주수익이라 M1(발생액 품질)의
# 단일기업 fallback이 '이상 발생액'으로 오인. industry.py excluded_modules에서
# M1 자동 제외. 내부 코드 "100".
_HOLDING_COMPANIES = {
    "SK스퀘어": "100",   # SK하이닉스 지분 보유
    "SK": "100",         # SK그룹 지주
    "HD현대": "100",     # HD그룹 지주
    "두산": "100",       # 두산그룹 지주
    "삼성물산": "100",    # 삼성그룹 사실상 지주 역할
}


def _industry_for(name: str) -> Optional[str]:
    """이름 기반 업종코드 추정. 금융 > 지주 > 일반 순. 미상이면 None."""
    if name in _FINANCIAL_INDUSTRIES:
        return _FINANCIAL_INDUSTRIES[name]
    if name in _HOLDING_COMPANIES:
        return _HOLDING_COMPANIES[name]
    return None

KOSPI_TOP_50 = [
    "삼성전자", "SK하이닉스", "삼성전자우", "현대차", "LG에너지솔루션",
    "한화에어로스페이스", "SK스퀘어", "삼성바이오로직스", "두산에너빌리티", "KB금융",
    "기아", "HD현대중공업", "삼성생명", "삼성물산", "신한지주",
    "셀트리온", "삼성전기", "삼성SDI", "한화오션", "HD현대일렉트릭",
    "미래에셋증권", "현대모비스", "고려아연", "하나금융지주", "NAVER",
    "POSCO홀딩스", "효성중공업", "HD한국조선해양", "한국전력", "LS ELECTRIC",
    "한미반도체", "SK", "우리금융지주", "한화시스템", "삼성중공업",
    "LG화학", "현대로템", "삼성화재", "두산", "카카오",
    "LIG넥스원", "SK이노베이션", "KODEX 200", "HMM", "SK텔레콤",
    "현대건설", "HD현대", "메리츠금융지주", "포스코퓨처엠", "KT&G",
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
        market_cap = fetch_market_cap(corp.stock_code) if fetch_market_caps and corp.stock_code else None

        try:
            panel = fetch_panel(
                corp.corp_code,
                year_range,
                corp_name=name,
                industry_code=industry,
                sleep_sec=sleep_sec,
            )
            eqs = compute_eqs(panel)
            out.append(FirmRecord(name, corp, panel=panel, eqs=eqs,
                                  market_cap=market_cap, industry_code=industry))
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
                print(f"[{i:2d}/{n}] {name} ({corp.stock_code}){tag}: {len(panel.years)}년 → EQS={tot} ({grade}){cap_str}")
        except Exception as e:  # noqa: BLE001 — 한 종목 실패가 전체를 막지 않도록
            out.append(FirmRecord(name, corp, market_cap=market_cap, industry_code=industry,
                                  error=f"{type(e).__name__}: {e}"))
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
