"""양방향 지분 엣지 중복 제거.

A→B와 B→A 양쪽에서 같은 지분 사실이 수집될 수 있음 (DART 양방향 API 특성).
higher ratio를 채택하여 하나만 남김.

relation_type 레이어 공존은 유지 — 같은 (A, B) 쌍에 ftc_group + subsidiary가
함께 있는 경우는 삭제하지 않음 (교육용 대조 목적).

상세는 modules/relation/transform/CLAUDE.md 참조.
"""

from __future__ import annotations


def apply() -> None:
    """RelationLocal 스캔 → 양방향 지분 중복 쌍 식별 → higher ratio만 남기고 나머지 삭제."""
    raise NotImplementedError("Phase 2d에서 구현")
