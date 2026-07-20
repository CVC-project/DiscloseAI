"""DART 산업코드(KSIC) 기반 EQS 업종 메타데이터."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CompanyIndustry:
    code: Optional[str]
    name: Optional[str]


def normalize_industry_code(value: Optional[str]) -> Optional[str]:
    code = "".join(ch for ch in (value or "") if ch.isdigit())
    return code or None


def is_financial(value: Optional[str]) -> bool:
    return (normalize_industry_code(value) or "")[:2] in {"64", "65", "66"}
