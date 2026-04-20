"""Phase 2a — ingest/dart.py 단위 테스트.

실제 API 호출 없이 fixture + monkeypatch로 검증.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from modules.relation.ingest import dart

# ============================================================
# _parse_ratio
# ============================================================


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("12.34", 12.34),
        ("12.34%", 12.34),
        ("1,234.56", 1234.56),
        ("0.00", 0.0),
        ("", None),
        (None, None),
        ("-", None),
        ("abc", None),
    ],
)
def test_parse_ratio(raw, expected):
    assert dart._parse_ratio(raw) == expected


# ============================================================
# fetch_shareholders — 정상 응답
# ============================================================


def test_fetch_shareholders_returns_list(dart_hyslr_005930):
    """status=000 응답이면 list 필드 반환."""
    with patch("modules.relation.ingest.dart.dart_get", return_value=dart_hyslr_005930):
        result = dart.fetch_shareholders("00126380", 2024)
    assert isinstance(result, list)
    assert len(result) > 0
    # 응답 구조 확인
    first = result[0]
    assert "nm" in first
    assert "relate" in first


def test_fetch_shareholders_samsung_contains_known_people(dart_hyslr_005930):
    """삼성전자 fixture에 홍라희·이재용·삼성생명보험 포함되는지."""
    with patch("modules.relation.ingest.dart.dart_get", return_value=dart_hyslr_005930):
        items = dart.fetch_shareholders("00126380", 2024)
    names = {item.get("nm") for item in items}
    assert "홍라희" in names
    assert "이재용" in names
    # 삼성생명보험은 표기 변형 가능 (㈜ 포함)
    assert any("삼성생명" in (n or "") for n in names)


# ============================================================
# fetch_shareholders — 에러 케이스
# ============================================================


def test_fetch_shareholders_no_data_returns_empty():
    """status=013 (데이터 없음) 응답이면 빈 리스트."""
    no_data = {"status": "013", "message": "조회된 데이터가 없습니다."}
    with patch("modules.relation.ingest.dart.dart_get", return_value=no_data):
        result = dart.fetch_shareholders("99999999", 2024)
    assert result == []


def test_fetch_shareholders_origin_missing_returns_empty():
    """status=900 원본 공시 없음도 빈 리스트."""
    no_origin = {"status": "900", "message": "원본 데이터 없음"}
    with patch("modules.relation.ingest.dart.dart_get", return_value=no_origin):
        result = dart.fetch_shareholders("99999999", 2024)
    assert result == []


# ============================================================
# fetch_investments
# ============================================================


def test_fetch_investments_returns_list(dart_invst_005930):
    with patch("modules.relation.ingest.dart.dart_get", return_value=dart_invst_005930):
        result = dart.fetch_investments("00126380", 2024)
    assert isinstance(result, list)
    assert len(result) > 0
    # 피투자 법인명 필드 확인
    assert all("inv_prm" in item for item in result[:3])


# ============================================================
# collect — RelationRaw INSERT 개수
# ============================================================


def test_collect_for_samsung_inserts_relation_raw(
    in_memory_session, dart_hyslr_005930, dart_invst_005930, monkeypatch, tmp_path
):
    """collect(corp='005930') 실행 시 RelationRaw가 생성되는지 (개인·재단 포함, 필터는 transform)."""
    from modules.relation.storage.models import RelationRaw

    # storage.db.get_local_session을 in_memory_session으로 치환
    monkeypatch.setattr(
        "modules.relation.ingest.dart.get_local_session",
        lambda: in_memory_session,
    )

    # dart_get을 fixture 응답으로 치환
    def fake_dart_get(endpoint, params, use_cache=True):
        if endpoint == "hyslrSttus.json":
            return dart_hyslr_005930
        if endpoint == "otrCprInvstmntSttus.json":
            return dart_invst_005930
        raise ValueError(f"unknown endpoint {endpoint}")

    monkeypatch.setattr("modules.relation.ingest.dart.dart_get", fake_dart_get)

    result = dart.collect(corp="005930", bsns_year=2024)

    assert result["shareholders_rows"] > 0, "hyslrSttus row count > 0"
    assert result["investments_rows"] > 0, "otrCprInvstmntSttus row count > 0"
    assert result["errors"] == [], f"errors: {result['errors']}"

    # DB 실제 저장 확인
    total = in_memory_session.query(RelationRaw).count()
    assert total == result["shareholders_rows"] + result["investments_rows"]

    # 삼성전자가 target 또는 source인 엣지가 저장됨
    samsung_edges = (
        in_memory_session.query(RelationRaw)
        .filter(
            (RelationRaw.source_name.like("%삼성전자%"))
            | (RelationRaw.target_name.like("%삼성전자%"))
        )
        .count()
    )
    assert samsung_edges > 0, "삼성전자 관련 엣지 최소 1개 이상 저장되어야"
