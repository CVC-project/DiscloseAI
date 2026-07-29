"""신선도 필터 단위 테스트 (2026-07-29 리더 결정 — 원천별 규칙·경계값)."""

from datetime import date
from types import SimpleNamespace

from modules.relation.valuechain.freshness import keep_edge

TODAY = date(2026, 7, 29)


def _edge(kind, as_of=None, valid_until=None, edge_type="customer",
          src="AAAAAAAA", dst="BBBBBBBB"):
    return SimpleNamespace(source_kind=kind, as_of=as_of, valid_until=valid_until,
                           edge_type=edge_type, src_corp=src, dst_corp=dst)


# ── rp_note: 보고 주체의 최신 주석 연도만 ──────────────────────────────

def test_rp_note_latest_year_kept_stale_dropped():
    latest = {"AAAAAAAA": 2025}
    assert keep_edge(_edge("rp_note", 2025), latest, TODAY)
    assert not keep_edge(_edge("rp_note", 2024), latest, TODAY)


def test_rp_note_self_is_dst_for_supply_direction():
    # supply 방향은 dst가 자사 — dst 기준 최신 연도로 판정해야 한다
    latest = {"BBBBBBBB": 2024}
    assert keep_edge(_edge("rp_note", 2024, edge_type="supply"), latest, TODAY)
    assert not keep_edge(_edge("rp_note", 2023, edge_type="supply"), latest, TODAY)


def test_rp_note_company_whose_latest_is_2024_not_penalized():
    # 최신 보고서가 2024인 회사(2025 미제출/미파싱)는 2024가 유효 — 전역 연도 컷이 아님
    latest = {"AAAAAAAA": 2024}
    assert keep_edge(_edge("rp_note", 2024), latest, TODAY)


# ── supply_contract: 종료일 우선, 없으면 2년 컷 ────────────────────────

def test_contract_end_date_governs_over_year():
    # 2020년 계약이라도 종료일이 미래면 유효
    assert keep_edge(_edge("supply_contract", 2020, valid_until="2027-12-31"), {}, TODAY)
    # 2025년 계약이라도 종료일이 지났으면 무효
    assert not keep_edge(_edge("supply_contract", 2025, valid_until="2026-01-31"), {}, TODAY)


def test_contract_end_boundary_today():
    assert keep_edge(_edge("supply_contract", 2024, valid_until="2026-07-29"), {}, TODAY)
    assert not keep_edge(_edge("supply_contract", 2024, valid_until="2026-07-28"), {}, TODAY)


def test_contract_without_end_uses_two_year_cut():
    assert keep_edge(_edge("supply_contract", 2025), {}, TODAY)
    assert keep_edge(_edge("supply_contract", 2026), {}, TODAY)
    assert not keep_edge(_edge("supply_contract", 2024), {}, TODAY)


# ── biz_prose(T2): 2년 컷 ─────────────────────────────────────────────

def test_t2_two_year_cut():
    assert keep_edge(_edge("biz_prose", 2025), {}, TODAY)
    assert not keep_edge(_edge("biz_prose", 2023), {}, TODAY)


def test_unknown_kind_passes():
    assert keep_edge(_edge("io_table", 2020), {}, TODAY)
