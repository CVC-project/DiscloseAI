"""transform/dedupe.py 단위 테스트."""

from __future__ import annotations

from modules.relation.storage.models import RelationLocal
from modules.relation.transform import dedupe


def test_bidirectional_ownership_dedup_keeps_higher_ratio(
    in_memory_session, monkeypatch
):
    """A→B 5% + B→A 19% 같은 양방향 중복 → 19%만 남음."""
    monkeypatch.setattr(
        "modules.relation.transform.dedupe.get_local_session",
        lambda: in_memory_session,
    )
    # 같은 쌍(005930, 028260) ownership 엣지 2개 (ratio 5, 19)
    in_memory_session.add(
        RelationLocal(
            source_corp="005930",
            target_corp="028260",
            relation_type="investment",
            ratio=5.0,
            source_type="otrCprInvstmntSttus",
            bsns_year=2024,
        )
    )
    in_memory_session.add(
        RelationLocal(
            source_corp="028260",
            target_corp="005930",
            relation_type="investment",
            ratio=19.0,
            source_type="hyslrSttus",
            bsns_year=2024,
        )
    )
    in_memory_session.commit()

    result = dedupe.apply()
    assert result["kept"] == 1
    assert result["removed"] == 1

    # higher ratio (19.0) 엣지만 남음
    remaining = in_memory_session.query(RelationLocal).all()
    assert len(remaining) == 1
    assert remaining[0].ratio == 19.0


def test_layer_coexistence_ftc_and_ownership(in_memory_session, monkeypatch):
    """같은 쌍(A,B)에 ftc_group + subsidiary는 둘 다 유지 (레이어 공존)."""
    monkeypatch.setattr(
        "modules.relation.transform.dedupe.get_local_session",
        lambda: in_memory_session,
    )
    in_memory_session.add(
        RelationLocal(
            source_corp="005930",
            target_corp="028260",
            relation_type="ftc_group",
            source_type="ftc",
            bsns_year=2024,
        )
    )
    in_memory_session.add(
        RelationLocal(
            source_corp="005930",
            target_corp="028260",
            relation_type="subsidiary",
            ratio=80.0,
            source_type="otrCprInvstmntSttus",
            bsns_year=2024,
        )
    )
    in_memory_session.commit()

    dedupe.apply()

    remaining = in_memory_session.query(RelationLocal).all()
    # 둘 다 유지 (relation_type 다르면 공존)
    types = {r.relation_type for r in remaining}
    assert types == {"ftc_group", "subsidiary"}
