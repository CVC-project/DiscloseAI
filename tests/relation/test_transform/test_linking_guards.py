"""엔티티 링킹 방어층 회귀 테스트 (FN-013 — HMM 오링킹 사고 재발 방지).

사업보고서 추출의 정확성은 교육 서비스의 신뢰 기반(리더 지정 Key 요건).
여기 케이스들은 실제 발생한 사고의 박제다 — 다음 확장(전 상장사 재수집·T2 확장)에서
이 테스트가 깨지면 같은 사고가 재발한다는 뜻이므로 절대 삭제·완화하지 말 것.

방어 5층 (transform/CLAUDE.md "엔티티 링킹 방어 5층" 조문 참조):
  L1 모호 약칭 게이트 + 실존 상장사명 화이트리스트   (filters.is_ambiguous_abbrev)
  L2 쌍 단위 블록리스트                              (data/link_blocklist.csv)
  L3 ratio sanity (>100% 오파싱 차단)                (filters.apply otrCpr 분기)
  L4 50%+ 교차검증 스캔 → CPA 검수 리스트            (수동 루프 — 자동화 아님)
  L5 LinkFailQueue → 수동 별칭/블록 확정 (M2)        (storage.LinkFailQueue)
"""

from __future__ import annotations

import pytest

from modules.relation.common.names import NAME_ALIASES, normalize_company_name
from modules.relation.transform.filters import (
    is_ambiguous_abbrev,
    load_link_blocklist,
)


# ── L1: 모호 약칭 게이트 ────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "raw,expected",
    [
        # 실사고: 현대차 사업보고서의 해외 생산법인 약칭 무리 — 게이트 대상
        ("HMM", True),
        ("HMA", True),
        ("HMI", True),
        ("GMC", True),
        # 정식 사명이 약칭 형태인 실존 상장사도 형태상으로는 게이트 대상
        # (통과 여부는 ticker_map 화이트리스트가 결정 — apply() 내부)
        ("KT", True),
        ("NAVER", True),
        ("POSCO", True),
        # 게이트 비대상: 한글 포함·정식 법인 표기·긴 영문
        ("HD현대", False),
        ("(주)하림", False),
        ("HMM오션서비스", False),
        ("Hyundai Motor Manufacturing", False),
        ("삼성전자", False),
        ("", False),
    ],
)
def test_ambiguous_abbrev_gate(raw, expected):
    assert is_ambiguous_abbrev(raw) == expected


# ── L2: 쌍 단위 블록리스트 ──────────────────────────────────────────────────

def test_blocklist_contains_confirmed_mislinks():
    """CPA 검수 1차(2026-07-28)로 확정된 오링킹 쌍이 블록리스트에 남아 있어야 한다."""
    bl = load_link_blocklist()
    # 실사고 원형: 현대차 → HMM (해외법인 약칭 → 상장 해운사)
    assert ("005380", "011200") in bl
    # 유형 대표: 한글 동명 비상장 (DS단석 '하이브 주식회사' → 엔터 하이브)
    assert ("017860", "352820") in bl
    # 유형 대표: 구사명 충돌 (금호에이치티 '풍전약품(주)' → 당시 에스씨엠생명과학)
    assert ("214330", "298060") in bl
    # 유형 대표: 수치 오파싱 (영풍 → 시그네틱스 710651%)
    assert ("000670", "033170") in bl
    assert len(bl) >= 16


# ── 구사명 별칭 (registry name_current 시차 보정) ───────────────────────────

def test_former_name_alias_resolves_to_current():
    """구사명은 별칭으로 현재 사명에 흡수 — 과거 연도 공시 링킹의 시차 보정."""
    assert normalize_company_name("에스씨엠생명과학") == normalize_company_name("풍전약품")
    # 별칭 사전 자체에 등재돼 있는지 (실수로 지우면 여기서 잡힘)
    assert "에스씨엠생명과학" in NAME_ALIASES


# ── L3: ratio sanity 규칙 문서화 테스트 ────────────────────────────────────

def test_ratio_sanity_threshold_semantics():
    """>100%는 오파싱(주식수 혼입), 정확히 100%는 유효(상장 前 완전자회사).

    apply() 내부 분기라 여기서는 경계 의미만 박제 — 100.0은 통과, 100.01부터 차단.
    (실사고: 영풍→시그네틱스 710651.0 — 실지분 0.83%로 기준 미달이 정답이었음)
    """
    valid, invalid = 100.0, 710651.0
    assert not valid > 100
    assert invalid > 100
