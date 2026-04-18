"""재무제표 → 한국어 한 줄 요약."""

from __future__ import annotations

from typing import List, Optional

from ..eqs.types import FirmYear


def _pct(num: Optional[float], den: Optional[float]) -> Optional[float]:
    if num is None or not den:
        return None
    return num / den * 100


def translate_income(y: FirmYear) -> str:
    """손익계산서: 영업이익률을 '100원 팔면 N원이 남는다'로 표현."""
    op_margin = _pct(y.operating_income, y.revenue)
    net_margin = _pct(y.net_income, y.revenue)
    if op_margin is None:
        return "매출/영업이익 데이터가 부족해 손익을 풀어 설명할 수 없습니다."
    op_text = f"100원 팔면 영업으로 {op_margin:.0f}원이 남습니다"
    if net_margin is not None:
        op_text += f" (세금·이자 등 빼고 최종 {net_margin:.0f}원)"
    return op_text + "."


def translate_balance(y: FirmYear) -> str:
    """재무상태표: 부채비율 + 자본구조."""
    if not y.total_assets:
        return "자산총계 정보가 없어 재무상태를 풀어 설명할 수 없습니다."
    debt_ratio = _pct(y.total_liabilities, y.total_assets)
    equity_ratio = _pct(y.total_equity, y.total_assets)
    if debt_ratio is None:
        return "부채 정보가 없어 재무상태를 풀어 설명할 수 없습니다."
    parts = [f"빚이 전체 자산의 {debt_ratio:.0f}%입니다"]
    if equity_ratio is not None:
        parts.append(f"자본은 {equity_ratio:.0f}%")
    return ", ".join(parts) + "."


def translate_cashflow(y: FirmYear) -> str:
    """현금흐름표: OCF/ICF/FCF 부호 패턴으로 4가지 전형 분류."""
    ocf, icf, fcf = y.operating_cashflow, y.investing_cashflow, y.financing_cashflow
    if ocf is None or icf is None or fcf is None:
        return "현금흐름 3대 항목 중 일부가 없어 흐름을 설명할 수 없습니다."
    s_ocf = _sign(ocf)
    s_icf = _sign(icf)
    s_fcf = _sign(fcf)
    pattern = (s_ocf, s_icf, s_fcf)
    label = _CF_PATTERNS.get(pattern, "혼합형 — 추가 검토 필요")
    return f"벌어서 투자하고 — {label}."


def translate_all(y: FirmYear) -> List[str]:
    """세 재무제표 한 줄 요약을 리스트로."""
    return [translate_income(y), translate_balance(y), translate_cashflow(y)]


def _sign(x: float) -> str:
    if x > 0:
        return "+"
    if x < 0:
        return "-"
    return "0"


# OCF/ICF/FCF 부호 패턴 → 전형 진단 (회계학 교과서 분류).
_CF_PATTERNS = {
    ("+", "-", "-"): "여유 있는 구조 (영업 흑자로 투자도 하고 빚도 갚는다)",
    ("+", "-", "+"): "성장 투자 단계 (영업 흑자 + 외부자금 끌어 투자 확대)",
    ("+", "+", "-"): "사업 축소 (자산 매각 + 차입 상환)",
    ("+", "+", "+"): "현금 비축 (영업·매각·차입 모두 +, 다음 대형 투자 직전 가능)",
    ("-", "-", "+"): "위태로운 신생/적자 기업 (영업 적자, 외부자금에 의존)",
    ("-", "+", "+"): "구조조정 진행 (자산 팔고 빚 내서 적자 메움 — 위험 신호)",
    ("-", "+", "-"): "청산 단계 (자산 매각으로 빚 갚는 중)",
    ("-", "-", "-"): "전방위 위기 (현금 모두 유출)",
}
