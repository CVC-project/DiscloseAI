"""K-IFRS 1024호 경계값 테스트."""

from __future__ import annotations

import pytest

from modules.relation.transform.kifrs import classify_ownership


@pytest.mark.parametrize(
    "ratio,expected",
    [
        # 경계값 (필수)
        (50.01, "subsidiary"),
        (50.0, "associate"),  # > 50% 이면 subsidiary, 50% 정확히는 associate
        (49.99, "associate"),
        (20.0, "associate"),  # ≥ 20% 이면 associate
        (19.99, "investment"),
        (5.0, "investment"),  # ≥ 5% 이면 investment
        (4.99, None),  # < 5% 이면 엣지 제외
        (0.0, None),
        (None, None),
        # 실전 케이스 (DART 수집 결과)
        (31.2, "associate"),  # 삼성전자→삼성바이오로직스
        (23.7, "associate"),  # 삼성전자→삼성전기
        (19.58, "investment"),  # 삼성전자→삼성SDI
        (8.51, "investment"),  # 삼성생명→삼성전자
        (5.01, "investment"),  # 삼성물산→삼성전자
        (1.63, None),  # 이재용 개인 지분 — classify는 None 반환 (filter에서 제외됨)
        (100.0, "subsidiary"),  # 100% 자회사
        (51.0, "subsidiary"),
    ],
)
def test_classify_ownership_boundaries(ratio, expected):
    assert classify_ownership(ratio) == expected
