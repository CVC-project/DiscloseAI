"""엣지 신선도 필터 — export 전용 (★2026-07-29 리더 결정, PLAN.md §1 D13).

원칙: DB는 전 연도 스냅샷 보존(D7 — 타임머신 여지), **자르는 것은 export만**.

원천별 규칙:
  rp_note (특수관계자 주석 — 매년 반복 기재되는 지속 거래):
    보고 주체(자사)의 **최신 주석 연도** 엣지만 유효. 이전 연도에만 있고 최신 주석에서
    빠진 관계 = 종료된 거래로 본다. 보고 주체 복원: edge_type=customer면 src가 자사,
    supply면 dst가 자사 (related_party.apply의 방향 규칙 역산 — 외부 DB 불요).
  supply_contract (단일판매·공급계약 수시공시 — 일회성 계약):
    계약 종료일(valid_until)이 있으면 **오늘 기준 미경과**만 유효.
    없으면 **2년 컷**(as_of >= 올해-1).
  biz_prose (T2 서술 추출):
    2년 컷 — 최신 보고서 서술만 (구연도 서술은 하네스 C 연간 갱신 루프가 대체).
  io_table 등 기타: 통과 (해당 원천 정책 확정 시 추가).
"""

from __future__ import annotations

from datetime import date

from modules.relation.storage.models import ValueChainEdge

FRESH_WINDOW_YEARS = 1  # "2년 컷" = as_of >= 올해 - 1


def _rp_note_self(edge) -> str:
    """rp_note 보고 주체(자사) corp_code — related_party.apply 방향 규칙 역산."""
    return edge.src_corp if edge.edge_type == "customer" else edge.dst_corp


def keep_edge(edge, latest_rp_year_by_self: dict[str, int], today: date) -> bool:
    """엣지 1건 신선도 판정 (순수 함수 — 단위 테스트 대상)."""
    kind = edge.source_kind
    if kind == "rp_note":
        latest = latest_rp_year_by_self.get(_rp_note_self(edge))
        return edge.as_of is not None and edge.as_of == latest
    if kind == "supply_contract":
        if edge.valid_until:
            return edge.valid_until >= today.isoformat()  # ISO 문자열 비교 = 날짜 비교
        return edge.as_of is not None and edge.as_of >= today.year - FRESH_WINDOW_YEARS
    if kind == "biz_prose":
        return edge.as_of is not None and edge.as_of >= today.year - FRESH_WINDOW_YEARS
    return True  # 기타 원천 — 정책 미확정, 통과


def fresh_edges(session, today: date | None = None) -> tuple[list, dict]:
    """active 엣지 → 신선도 통과분. Returns (edges, counters)."""
    today = today or date.today()
    active = session.query(ValueChainEdge).filter_by(status="active").all()

    latest_rp: dict[str, int] = {}
    for e in active:
        if e.source_kind == "rp_note" and e.as_of is not None:
            self_corp = _rp_note_self(e)
            if e.as_of > latest_rp.get(self_corp, 0):
                latest_rp[self_corp] = e.as_of

    kept, counters = [], {"total_active": len(active), "kept": 0,
                          "dropped_rp_stale": 0, "dropped_contract_expired": 0,
                          "dropped_contract_old": 0, "dropped_t2_old": 0}
    for e in active:
        if keep_edge(e, latest_rp, today):
            kept.append(e)
            continue
        if e.source_kind == "rp_note":
            counters["dropped_rp_stale"] += 1
        elif e.source_kind == "supply_contract":
            counters["dropped_contract_expired" if e.valid_until
                     else "dropped_contract_old"] += 1
        else:
            counters["dropped_t2_old"] += 1
    counters["kept"] = len(kept)
    return kept, counters
