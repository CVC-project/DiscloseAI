"""개인·공익재단·비상장 필터 + top50 target 매칭 + 기업명 정규화.

상세 규칙은 modules/relation/transform/CLAUDE.md 참조.
"""

from __future__ import annotations

import re

PERSONAL_RELATIONS = {"본인", "친인척", "친족", "인척"}
FOUNDATION_KEYWORDS = ("재단", "공익", "장학회")
RRN_PATTERN = re.compile(r"\d{6}-\d{7}")  # 주민번호 패턴

NAME_ALIASES = {
    # DART 표기 → 정규화된 KRX 이름 (예외 수동 매핑)
    "현대자동차": "현대차",
}


def is_personal_shareholder(name: str, relate: str | None) -> bool:
    """주주명·관계 필드로 개인 여부 판단."""
    raise NotImplementedError("Phase 2d에서 구현")


def is_foundation(name: str) -> bool:
    """기업명에 공익재단 키워드 포함 여부."""
    raise NotImplementedError("Phase 2d에서 구현")


def normalize_company_name(name: str) -> str:
    """(주)·주식회사·공백·Ltd. 제거 + 별칭 매핑."""
    raise NotImplementedError("Phase 2d에서 구현")


def match_to_top50(normalized_name: str) -> str | None:
    """정규화된 기업명 → top50 ticker (매칭 실패 시 None)."""
    raise NotImplementedError("Phase 2d에서 구현")


def apply() -> None:
    """RelationLocal 전체 스캔 → 개인·재단·top50 비포함 target 엣지 삭제."""
    raise NotImplementedError("Phase 2d에서 구현")
