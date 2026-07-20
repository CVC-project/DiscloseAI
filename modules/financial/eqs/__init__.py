"""EQS (Earnings Quality Score) modules.

V3 uses an absolute cash-conversion scale for M1 and KSIC peer percentiles for
M2-M5 when ``compute_eqs(panel, calibration)`` receives a calibration table.
Without a calibration table, the legacy V2 compatibility path remains active.
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
