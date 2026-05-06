"""재무제표 번역기 — 숫자를 한국어 한 줄로 풀어 설명.

세 가지 진입점:
- ``translate_income(year)`` — 손익계산서 ("100원 팔면 12원이 남습니다")
- ``translate_balance(year)`` — 재무상태표 ("빚이 전체 자산의 22%입니다")
- ``translate_cashflow(year)`` — 현금흐름표 ("벌어서 투자하고 — 여유 있는 구조")

그리고 ``extract_highlights(panel)`` — 규칙 기반 ⚡ 주목 포인트 3개 자동 추출.
"""

from .translate import (
    translate_income,
    translate_balance,
    translate_cashflow,
    translate_all,
)
from .highlights import extract_highlights, Highlight
from .ratios import Ratios, compute_ratios, LABELS as RATIO_LABELS

__all__ = [
    "translate_income",
    "translate_balance",
    "translate_cashflow",
    "translate_all",
    "extract_highlights",
    "Highlight",
    "Ratios",
    "compute_ratios",
    "RATIO_LABELS",
]
