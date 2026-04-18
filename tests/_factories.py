"""테스트용 FirmYear/FirmPanel 빌더 — 보일러플레이트 줄이려고."""

from __future__ import annotations

from typing import List

from modules.financial.eqs.types import FirmPanel, FirmYear


def make_year(
    year: int,
    *,
    revenue: float = 1000.0,
    cogs: float = 700.0,
    sga: float = 100.0,
    depreciation: float = 50.0,
    op: float = 200.0,
    ni: float = 100.0,
    nonrec: float | None = None,
    ta: float = 5000.0,
    tl: float = 2000.0,
    te: float = 3000.0,
    ca: float = 2000.0,
    cl: float = 1000.0,
    ltd: float = 800.0,
    ppe: float = 1500.0,
    ar: float = 300.0,
    shares: float = 1000.0,
    ocf: float = 150.0,
    icf: float = -100.0,
    fcf: float = -30.0,
) -> FirmYear:
    return FirmYear(
        year=year,
        revenue=revenue,
        cogs=cogs,
        sga=sga,
        depreciation=depreciation,
        operating_income=op,
        net_income=ni,
        nonrecurring_income=nonrec,
        total_assets=ta,
        total_liabilities=tl,
        total_equity=te,
        current_assets=ca,
        current_liabilities=cl,
        long_term_debt=ltd,
        ppe=ppe,
        accounts_receivable=ar,
        shares_outstanding=shares,
        operating_cashflow=ocf,
        investing_cashflow=icf,
        financing_cashflow=fcf,
    )


def healthy_panel(corp_code: str = "005930", n_years: int = 5) -> FirmPanel:
    """건강한 우상향 기업.

    - 매출 +10%/yr, 이익 더 빠르게 +12%/yr → 마진 점진 개선
    - 자산 +8%/yr (이익보다 느림 → ROA·자산회전율 개선)
    - LTD 매년 5% 상환 → 부채비율 감소
    - CA/CL 비율 점진 개선
    - 신주 발행 없음, OCF가 NI보다 항상 큼
    """
    years: List[FirmYear] = []
    base_year = 2020
    for i in range(n_years):
        rev_g = (1.10) ** i
        ni_g = (1.12) ** i
        asset_g = (1.08) ** i
        years.append(
            make_year(
                base_year + i,
                revenue=1000 * rev_g,
                cogs=700 * rev_g * (1 - 0.005 * i),  # 마진 점진 개선
                sga=100 * rev_g,
                op=200 * ni_g,
                ni=100 * ni_g,
                ta=5000 * asset_g,
                tl=2000 * (0.97**i),  # 부채 매년 3% 감소
                te=3000 * asset_g + 500 * i,  # 자본 누적
                ca=2000 * asset_g * (1 + 0.02 * i),  # CA가 약간 더 빠르게
                cl=1000 * asset_g,
                ltd=800 * (0.95**i),  # 장기차입금 매년 5% 상환
                ppe=1500 * asset_g,
                ar=300 * rev_g,
                ocf=120 * ni_g,  # OCF > NI 유지
                shares=1000.0,
            )
        )
    return FirmPanel(corp_code=corp_code, corp_name="HealthyCo", industry_code="013", years=years)


def manipulator_panel(corp_code: str = "999999") -> FirmPanel:
    """분식 의심 패턴 — AR 급증, OCF는 NI를 못 따라감, 부채 급증."""
    y0 = make_year(2023, revenue=1000, ar=200, ni=80, ocf=70, tl=2000, ta=5000, cogs=700)
    y1 = make_year(
        2024,
        revenue=1500,  # 매출 +50%
        ar=600,  # 매출채권 +200% (매출 증가율보다 훨씬 큼)
        ni=200,  # 이익 +150%
        ocf=10,  # 현금은 거의 안 들어옴
        tl=3000,  # 부채 +50%
        ta=6500,
        cogs=1100,  # 마진 압박
    )
    return FirmPanel(corp_code=corp_code, corp_name="SuspectCo", industry_code="013", years=[y0, y1])
