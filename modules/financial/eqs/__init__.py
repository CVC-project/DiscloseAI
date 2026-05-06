"""EQS (Earnings Quality Score) — 5개 모듈로 이익의 '진짜 질'을 진단.

| 모듈 | 방법론 | 핵심 질문 |
|------|--------|----------|
| M1 | 수정 Jones    | 이익이 현금으로 뒷받침되는가? |
| M2 | Beneish/K-Beneish | 이익을 조작했을 확률은? |
| M3 | OCF/NI 추세  | 이익은 늘어나는데 현금은 어디? |
| M4 | AR(1) + 일회성 | 올해 이익이 내년에도 유지? |
| M5 | Piotroski F  | 기초 체력이 좋아지고 있나? |

상위 진입점: ``compute_eqs(panel)`` → ``EQSResult``.
"""

from .types import FirmYear, FirmPanel, EQSResult, ModuleScore
from .score import compute_eqs, grade_from_score

__all__ = [
    "FirmYear",
    "FirmPanel",
    "EQSResult",
    "ModuleScore",
    "compute_eqs",
    "grade_from_score",
]
