"""⚡ 주목 포인트 자동 추출 (규칙 기반).

CPA 팀이 설계할 20~30개 규칙의 1차 골격. 각 규칙은:
- 패널을 받아서 감지/미감지 + (severity, 메시지)를 반환
- severity가 높은 순으로 정렬 → 상위 3개를 highlight로 채택

심각도(severity): 0~10
- 10: 분식·부도 위험 등 즉시 확인 필요
- 5~7: 추세 악화·이상 신호
- 1~4: 참고용

새 규칙은 ``_RULES`` 리스트에 함수만 추가하면 자동 반영된다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

from ..eqs.types import FirmPanel, FirmYear


@dataclass
class Highlight:
    severity: int  # 0~10
    title: str  # 짧은 라벨 ("부채 급증" 등)
    message: str  # 한 줄 설명


# ---------- 개별 규칙 ----------


def _rule_ocf_ni_gap(panel: FirmPanel) -> Optional[Highlight]:
    """OCF가 NI보다 현저히 작으면 발생액 누적 위험."""
    curr = panel.latest()
    if not curr or not curr.net_income or curr.operating_cashflow is None:
        return None
    if curr.net_income <= 0:
        return None
    ratio = curr.operating_cashflow / curr.net_income
    if ratio < 0.3:
        return Highlight(
            severity=8,
            title="이익 대비 현금 부족",
            message=f"순이익은 흑자지만 영업현금흐름은 그 {ratio*100:.0f}% 수준에 불과합니다.",
        )
    return None


def _rule_debt_jump(panel: FirmPanel) -> Optional[Highlight]:
    """전년 대비 부채 30%+ 급증."""
    curr, prev = panel.latest(), panel.prior()
    if not curr or not prev:
        return None
    if not curr.total_liabilities or not prev.total_liabilities:
        return None
    growth = (curr.total_liabilities - prev.total_liabilities) / prev.total_liabilities
    if growth >= 0.30:
        return Highlight(
            severity=7,
            title="부채 급증",
            message=f"부채총계가 1년 만에 {growth*100:.0f}% 늘었습니다.",
        )
    return None


def _rule_ar_outpaces_sales(panel: FirmPanel) -> Optional[Highlight]:
    """매출채권 증가율이 매출 증가율을 크게 앞지르면 매출 부풀리기 의심."""
    curr, prev = panel.latest(), panel.prior()
    if not curr or not prev:
        return None
    if not all(
        [
            curr.revenue,
            prev.revenue,
            curr.accounts_receivable,
            prev.accounts_receivable,
        ]
    ):
        return None
    rev_g = (curr.revenue - prev.revenue) / prev.revenue
    ar_g = (curr.accounts_receivable - prev.accounts_receivable) / prev.accounts_receivable
    gap = ar_g - rev_g
    if gap >= 0.15:
        return Highlight(
            severity=8,
            title="매출채권이 매출보다 빨리 증가",
            message=f"매출은 {rev_g*100:+.0f}% 증가했는데 매출채권은 {ar_g*100:+.0f}% 늘었습니다.",
        )
    return None


def _rule_high_leverage(panel: FirmPanel) -> Optional[Highlight]:
    """부채비율 70% 초과."""
    curr = panel.latest()
    if not curr or not curr.total_assets or curr.total_liabilities is None:
        return None
    ratio = curr.total_liabilities / curr.total_assets
    if ratio >= 0.70:
        return Highlight(
            severity=6,
            title="고부채 구조",
            message=f"전체 자산의 {ratio*100:.0f}%가 부채입니다.",
        )
    return None


def _rule_operating_loss(panel: FirmPanel) -> Optional[Highlight]:
    """영업적자."""
    curr = panel.latest()
    if not curr or curr.operating_income is None:
        return None
    if curr.operating_income < 0:
        return Highlight(
            severity=9,
            title="영업적자",
            message=f"본업에서 {abs(curr.operating_income):,.0f} 손실이 발생했습니다.",
        )
    return None


def _rule_margin_drop(panel: FirmPanel) -> Optional[Highlight]:
    """영업이익률이 5%p 이상 하락."""
    curr, prev = panel.latest(), panel.prior()
    if not curr or not prev:
        return None
    if not curr.revenue or not prev.revenue:
        return None
    if curr.operating_income is None or prev.operating_income is None:
        return None
    m_curr = curr.operating_income / curr.revenue
    m_prev = prev.operating_income / prev.revenue
    drop = m_prev - m_curr
    if drop >= 0.05:
        return Highlight(
            severity=6,
            title="영업이익률 급락",
            message=f"영업이익률이 {m_prev*100:.0f}% → {m_curr*100:.0f}%로 떨어졌습니다.",
        )
    return None


def _rule_negative_equity(panel: FirmPanel) -> Optional[Highlight]:
    """자본잠식."""
    curr = panel.latest()
    if not curr or curr.total_equity is None:
        return None
    if curr.total_equity < 0:
        return Highlight(
            severity=10,
            title="자본잠식",
            message="자본총계가 마이너스입니다 — 상장폐지 사유 점검이 필요합니다.",
        )
    return None


def _rule_strong_cash_generation(panel: FirmPanel) -> Optional[Highlight]:
    """OCF가 NI의 1.2배 이상 — 양질의 현금창출 (긍정 highlight)."""
    curr = panel.latest()
    if not curr or not curr.net_income or curr.operating_cashflow is None:
        return None
    if curr.net_income <= 0:
        return None
    ratio = curr.operating_cashflow / curr.net_income
    if ratio >= 1.2:
        return Highlight(
            severity=4,
            title="현금창출력 우수",
            message=f"영업현금흐름이 순이익의 {ratio*100:.0f}%로 이익을 충분히 뒷받침합니다.",
        )
    return None


_RULES: List[Callable[[FirmPanel], Optional[Highlight]]] = [
    _rule_negative_equity,
    _rule_operating_loss,
    _rule_ocf_ni_gap,
    _rule_ar_outpaces_sales,
    _rule_debt_jump,
    _rule_margin_drop,
    _rule_high_leverage,
    _rule_strong_cash_generation,
]


def extract_highlights(panel: FirmPanel, top_k: int = 3) -> List[Highlight]:
    """심각도 기준 상위 ``top_k``개 highlight 반환."""
    found: List[Highlight] = []
    for rule in _RULES:
        try:
            hit = rule(panel)
        except Exception:  # 규칙 1개 실패가 전체를 막지 않도록
            hit = None
        if hit is not None:
            found.append(hit)
    found.sort(key=lambda h: h.severity, reverse=True)
    return found[:top_k]
