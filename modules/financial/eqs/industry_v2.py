"""EQS v2 업종 분류 + 임계값 테이블.

설계 문서 ``modules/financial/EQS_V2_DESIGN.md`` 5장의 업종별 임계값을 기계화.

3가지 분류축:
- ``m3_bucket``  → 부채비율 D/E 임계값 (4 thresholds: 우량·양호·주의·위험)
- ``m4_mean_bucket`` → 영업이익률 평균 임계값 (5 thresholds: 위험·손익·보통·우수·최우수)
- ``m4_vol_bucket``  → 영업이익률 변동폭 임계값 (4 thresholds: 안정·보통·들쭉·불안정)
- ``m2_excluded`` → 금융업은 매출채권 개념 부적합 → M2 점수 산출 제외

KOSPI 48개 universe는 ``UNIVERSE_BUCKETS``에 회사명→분류 직접 매핑.
universe 외 종목은 ``classify_by_industry_code`` fallback 진입 (제조업 일반).

승인 후 KSIC API 연동되면 ``UNIVERSE_BUCKETS``는 자동 분류로 대체.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


# ---------------------------------------------------------------------------
# 임계값 테이블 (EQS_V2_DESIGN.md §M3, §M4 표 그대로 옮김)
# ---------------------------------------------------------------------------

# M3 D/E 임계값 (소수): [우량=100점, 양호=80점, 주의=50점, 위험=0점]
M3_THRESHOLDS: Dict[str, Tuple[float, float, float, float]] = {
    "ict_software":       (0.30, 0.60, 1.20, 2.50),
    "manufacturing":      (0.50, 1.00, 2.00, 4.00),
    "chemicals":          (0.60, 1.20, 2.20, 4.50),
    "utility":            (0.80, 1.50, 2.80, 5.00),
    "retail":             (0.50, 1.00, 2.00, 4.00),
    "construction":       (1.00, 2.00, 3.50, 6.00),
    "transport":          (1.00, 2.00, 3.50, 6.00),
    "fin_holding":        (8.00, 12.00, 17.00, 25.00),
    "bank":               (8.00, 12.00, 17.00, 25.00),
    "securities":         (2.00, 4.00, 6.00, 10.00),
    "life_insurance":     (7.00, 11.00, 15.00, 22.00),
    "non_life_insurance": (4.00, 7.00, 11.00, 17.00),
}

# M4 영업이익률 평균 임계값 (소수): [위험=0, 손익=20, 보통=50, 우수=80, 최우수=100]
M4_MEAN_THRESHOLDS: Dict[str, Tuple[float, float, float, float, float]] = {
    "ict_software":       (-0.05, 0.0, 0.10, 0.20, 0.30),
    "biotech":            (-0.10, 0.0, 0.08, 0.20, 0.35),
    "manufacturing":      (-0.05, 0.0, 0.05, 0.10, 0.15),
    "chemicals":          (-0.03, 0.0, 0.04, 0.08, 0.12),
    "automotive":         (-0.03, 0.0, 0.04, 0.08, 0.12),
    "retail":             (-0.02, 0.0, 0.02, 0.04, 0.07),
    "construction":       (-0.03, 0.0, 0.03, 0.06, 0.10),
    "transport":          (-0.05, 0.0, 0.04, 0.10, 0.15),
    "utility":            (-0.03, 0.0, 0.02, 0.05, 0.08),
    "fin_holding":        (-0.05, 0.0, 0.25, 0.35, 0.45),
    "bank":               (-0.05, 0.0, 0.25, 0.35, 0.45),
    "securities":         (-0.10, 0.0, 0.10, 0.25, 0.40),
    "life_insurance":     (-0.05, 0.0, 0.05, 0.12, 0.20),
    "non_life_insurance": (-0.03, 0.0, 0.05, 0.10, 0.18),
}

# M4 영업이익률 변동폭 임계값 (소수, %p): [안정=100, 보통=70, 들쭉=50, 불안정=0]
M4_VOL_THRESHOLDS: Dict[str, Tuple[float, float, float, float]] = {
    "stable":       (0.02, 0.04, 0.07, 0.12),
    "general":      (0.03, 0.07, 0.10, 0.20),
    "cyclic":       (0.08, 0.15, 0.25, 0.50),
    "fin_stable":   (0.03, 0.05, 0.08, 0.15),
    "fin_volatile": (0.03, 0.07, 0.10, 0.20),
    "fin_cyclic":   (0.08, 0.15, 0.25, 0.50),
}


# ---------------------------------------------------------------------------
# 회사별 분류 (KOSPI 48 hardcoded — KSIC API 연동 전까지)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IndustryV2:
    """v2 업종 분류 결과."""

    m3_bucket: str
    m4_mean_bucket: str
    m4_vol_bucket: str
    m2_excluded: bool  # 금융업은 매출채권 개념 부적합 → M2 산출 제외
    fin_kind: Optional[str] = None  # "fin_holding"/"bank"/"securities"/"life"/"non_life"


# (m3, m4_mean, m4_vol, m2_excluded, fin_kind)
# m2_excluded=True인 회사는 금융업 — 종합점수에서 M2 제외, 4개 모듈 평균.
UNIVERSE_BUCKETS: Dict[str, IndustryV2] = {
    # 반도체·전자부품 (제조업 일반 + 사이클)
    "삼성전자":    IndustryV2("manufacturing", "manufacturing", "cyclic", False),
    "SK하이닉스":  IndustryV2("manufacturing", "manufacturing", "cyclic", False),
    "삼성전기":    IndustryV2("manufacturing", "manufacturing", "cyclic", False),
    "한미반도체":  IndustryV2("manufacturing", "manufacturing", "cyclic", False),
    # 2차전지·배터리 (제조업 일반 + 사이클)
    "LG에너지솔루션": IndustryV2("manufacturing", "manufacturing", "cyclic", False),
    "삼성SDI":     IndustryV2("manufacturing", "manufacturing", "cyclic", False),
    "포스코퓨처엠": IndustryV2("chemicals", "chemicals", "cyclic", False),
    # 자동차·부품
    "현대차":      IndustryV2("manufacturing", "automotive", "cyclic", False),
    "기아":        IndustryV2("manufacturing", "automotive", "cyclic", False),
    "현대모비스":  IndustryV2("manufacturing", "automotive", "cyclic", False),
    # 조선·중공업 (수주산업 — M2 계약자산 합산 대상)
    "HD현대중공업":   IndustryV2("manufacturing", "manufacturing", "cyclic", False),
    "HD한국조선해양": IndustryV2("manufacturing", "manufacturing", "cyclic", False),
    "한화오션":    IndustryV2("manufacturing", "manufacturing", "cyclic", False),
    "삼성중공업":  IndustryV2("manufacturing", "manufacturing", "cyclic", False),
    "두산에너빌리티": IndustryV2("manufacturing", "manufacturing", "cyclic", False),
    # 화학·정유·소재 (사이클)
    "LG화학":      IndustryV2("chemicals", "chemicals", "cyclic", False),
    "SK이노베이션": IndustryV2("chemicals", "chemicals", "cyclic", False),
    "고려아연":    IndustryV2("chemicals", "chemicals", "cyclic", False),
    "POSCO홀딩스": IndustryV2("chemicals", "chemicals", "cyclic", False),
    # 바이오·제약 (안정업종 변동폭)
    "삼성바이오로직스": IndustryV2("manufacturing", "biotech", "stable", False),
    "셀트리온":    IndustryV2("manufacturing", "biotech", "stable", False),
    # 정보통신·소프트웨어
    "NAVER":       IndustryV2("ict_software", "ict_software", "general", False),
    "카카오":      IndustryV2("ict_software", "ict_software", "general", False),
    "SK텔레콤":    IndustryV2("ict_software", "ict_software", "stable", False),  # 통신=안정
    # 중공업·방산·전기장비
    "한화에어로스페이스": IndustryV2("manufacturing", "manufacturing", "general", False),
    "효성중공업":  IndustryV2("manufacturing", "manufacturing", "cyclic", False),
    "HD현대일렉트릭": IndustryV2("manufacturing", "manufacturing", "general", False),
    "LS ELECTRIC": IndustryV2("manufacturing", "manufacturing", "general", False),
    "현대로템":    IndustryV2("manufacturing", "manufacturing", "cyclic", False),
    "한화시스템":  IndustryV2("manufacturing", "manufacturing", "general", False),
    "LIG넥스원":   IndustryV2("manufacturing", "manufacturing", "general", False),
    # 비금융 지주·복합기업 (제조업 일반 fallback)
    "SK스퀘어":    IndustryV2("manufacturing", "manufacturing", "general", False),
    "SK":          IndustryV2("manufacturing", "manufacturing", "general", False),
    "두산":        IndustryV2("manufacturing", "manufacturing", "general", False),
    "삼성물산":    IndustryV2("manufacturing", "manufacturing", "general", False),
    "HD현대":      IndustryV2("manufacturing", "manufacturing", "general", False),
    # 통신·유틸리티·운송·기타
    "한국전력":    IndustryV2("utility", "utility", "stable", False),
    "HMM":         IndustryV2("transport", "transport", "cyclic", False),
    "현대건설":    IndustryV2("construction", "construction", "general", False),
    "KT&G":        IndustryV2("retail", "retail", "stable", False),
    # 금융업 — M2 적용 제외
    "KB금융":      IndustryV2("fin_holding", "fin_holding", "fin_stable", True, "fin_holding"),
    "신한지주":    IndustryV2("fin_holding", "fin_holding", "fin_stable", True, "fin_holding"),
    "하나금융지주": IndustryV2("fin_holding", "fin_holding", "fin_stable", True, "fin_holding"),
    "우리금융지주": IndustryV2("fin_holding", "fin_holding", "fin_stable", True, "fin_holding"),
    "메리츠금융지주": IndustryV2("fin_holding", "fin_holding", "fin_stable", True, "fin_holding"),
    "미래에셋증권": IndustryV2("securities", "securities", "fin_cyclic", True, "securities"),
    "삼성생명":    IndustryV2("life_insurance", "life_insurance", "fin_stable", True, "life"),
    "삼성화재":    IndustryV2("non_life_insurance", "non_life_insurance", "fin_volatile", True, "non_life"),
}

# 수주산업 (M2에서 매출채권 + 계약자산 합산 사용)
RECEIVABLE_INCLUDES_CONTRACT: set[str] = {
    "HD현대중공업",
    "HD한국조선해양",
    "한화오션",
    "삼성중공업",
    "두산에너빌리티",
    "현대건설",
    "현대로템",
    "한화에어로스페이스",
    "효성중공업",
    "LS ELECTRIC",
    "HD현대일렉트릭",
    "한화시스템",
    "LIG넥스원",
}


_DEFAULT = IndustryV2("manufacturing", "manufacturing", "general", False)


def classify(corp_name: Optional[str]) -> IndustryV2:
    """회사명 → v2 업종 분류. 미상이면 제조업 일반 fallback."""
    if not corp_name:
        return _DEFAULT
    return UNIVERSE_BUCKETS.get(corp_name.strip(), _DEFAULT)


def includes_contract_assets(corp_name: Optional[str]) -> bool:
    """수주산업 — M2에서 매출채권 + 계약자산을 합산해 미수채권으로 사용."""
    if not corp_name:
        return False
    return corp_name.strip() in RECEIVABLE_INCLUDES_CONTRACT


def m3_thresholds(bucket: str) -> Tuple[float, float, float, float]:
    return M3_THRESHOLDS.get(bucket, M3_THRESHOLDS["manufacturing"])


def m4_mean_thresholds(bucket: str) -> Tuple[float, float, float, float, float]:
    return M4_MEAN_THRESHOLDS.get(bucket, M4_MEAN_THRESHOLDS["manufacturing"])


def m4_vol_thresholds(bucket: str) -> Tuple[float, float, float, float]:
    return M4_VOL_THRESHOLDS.get(bucket, M4_VOL_THRESHOLDS["general"])
