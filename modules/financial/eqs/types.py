"""EQS 입력/출력 데이터 컨테이너.

DART/재무제표를 그대로 들고 오기에는 컬럼 이름이 모듈마다 달라서, EQS 계산용
정규화된 dataclass를 둔다. ``shared.models.FinancialData`` ORM 객체와
1:1로 변환되도록 필드명을 맞췄다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class FirmYear:
    """단일 연도 재무 스냅샷.

    Modified Jones / Beneish / Piotroski 모두 t-1, t 두 시점이 필요하다.
    누락 항목은 None으로 두고, 각 모듈에서 필요한 컬럼이 None이면 점수 산정을
    건너뛴다 (None 반환).
    """

    year: int
    quarter: Optional[int] = None  # 연간 결산이면 None

    # 손익계산서
    revenue: Optional[float] = None
    cogs: Optional[float] = None  # 매출원가
    sga: Optional[float] = None  # 판관비
    depreciation: Optional[float] = None
    operating_income: Optional[float] = None
    net_income: Optional[float] = None
    nonrecurring_income: Optional[float] = None  # 일회성 손익 (M4용)

    # 재무상태표
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    total_equity: Optional[float] = None
    current_assets: Optional[float] = None
    current_liabilities: Optional[float] = None
    long_term_debt: Optional[float] = None
    ppe: Optional[float] = None  # 유형자산 (Property/Plant/Equipment)
    accounts_receivable: Optional[float] = None
    contract_assets: Optional[float] = None  # 계약자산(미청구공사) — 건설·조선 M2용
    shares_outstanding: Optional[float] = None

    # 현금흐름표
    operating_cashflow: Optional[float] = None
    investing_cashflow: Optional[float] = None
    financing_cashflow: Optional[float] = None


@dataclass
class FirmPanel:
    """한 기업의 다년도 패널. 시간 오름차순으로 정렬된다."""

    corp_code: str
    corp_name: Optional[str] = None
    industry_code: Optional[str] = None  # KRX 업종코드 (예: "064" = 은행)
    years: List[FirmYear] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.years = sorted(self.years, key=lambda y: (y.year, y.quarter or 0))

    def latest(self) -> Optional[FirmYear]:
        return self.years[-1] if self.years else None

    def prior(self) -> Optional[FirmYear]:
        return self.years[-2] if len(self.years) >= 2 else None


@dataclass
class ModuleScore:
    """단일 EQS 모듈 결과."""

    name: str  # "M1" ~ "M5"
    score: Optional[float]  # 0~100, None이면 산출 불가/제외
    raw: Optional[float] = None  # 원시 통계량 (DA, M-score, F-score 등)
    note: str = ""  # 사람이 읽을 한 줄 요약


@dataclass
class EQSResult:
    """EQS 종합 결과."""

    corp_code: str
    corp_name: Optional[str]
    industry_code: Optional[str]
    modules: List[ModuleScore]
    total: Optional[float]  # 0~100
    grade: Optional[str]  # A/B/C/D/F
    excluded: List[str] = field(default_factory=list)  # 업종 예외로 제외된 모듈
