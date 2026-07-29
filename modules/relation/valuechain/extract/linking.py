"""엔티티 링킹 공용 유틸 — 밸류체인 T1 파서 전용 (valuechain PLAN.md §2.2 LinkFailQueue).

특수관계자 주석·공급계약 공시 등에서 등장하는 상대방 표기를 CompanyRegistry/
CompanyAlias 기준 corp_code로 매칭한다. 실패분은 LinkFailQueue에 빈도 누적
(M2 수동 별칭 보정 루프의 입력) — relation.db는 상장 법인만 노드로 삼는 원칙
(relation/CLAUDE.md 핵심 원칙 #1)이므로, 매칭 실패는 "정말 비상장이라 정당히
제외"와 "표기 불일치로 놓침"이 섞여 있음을 전제로 한다(빈도순 수동 검수 대상).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from modules.relation.common.names import add_phonetic_aliases, normalize_company_name
from modules.relation.storage.models import CompanyAlias, CompanyRegistry, LinkFailQueue


def build_name_to_corp_map(session) -> dict[str, str]:
    """{정규화된 이름: corp_code} — CompanyRegistry.name_current 우선, CompanyAlias로 보충.

    보강 순서(2026-07-29): 실제 사명 → CompanyAlias → 한글 음차 변형.
    음차는 마지막이라 실존 사명·수동 별칭을 절대 덮지 않는다(names.add_phonetic_aliases).
    """
    registry_rows = session.query(
        CompanyRegistry.name_current, CompanyRegistry.corp_code
    ).all()
    mapping: dict[str, str] = {}
    for name, corp_code in registry_rows:
        norm = normalize_company_name(name)
        if norm:
            mapping[norm] = corp_code
    for alias, corp_code in session.query(CompanyAlias.alias, CompanyAlias.corp_code).all():
        norm = normalize_company_name(alias)
        if norm and norm not in mapping:
            mapping[norm] = corp_code
    for name, corp_code in registry_rows:
        if name:
            add_phonetic_aliases(mapping, name, corp_code)
    return mapping


def resolve_corp(
    surface_form: str,
    name_to_corp: dict[str, str],
    session,
    sample_chunk_id: str | None = None,
) -> str | None:
    """표기 → corp_code. 실패 시 LinkFailQueue에 빈도 누적(upsert) 후 None 반환."""
    norm = normalize_company_name(surface_form)
    if not norm:
        return None
    corp_code = name_to_corp.get(norm)
    if corp_code:
        return corp_code

    existing = session.query(LinkFailQueue).filter_by(surface_form=surface_form).one_or_none()
    if existing:
        existing.freq += 1
    else:
        session.add(
            LinkFailQueue(surface_form=surface_form, freq=1, sample_chunk_id=sample_chunk_id)
        )
    return None


# ── 방어층 통과 링킹 (FN-013 방어 5층 — L1·L2·L5 공용 구현) ─────────────────
# 2026-07-29 U-확대: T2 추출기(llm_extract.py)에만 있던 GuardContext를 이관 —
# T1 주석 파서(related_party.apply/apply_governance)도 corp_code 없는 이름-only
# 링킹이라 같은 방어가 필요하다(transform/CLAUDE.md "다음 확장 때도 이 5층을
# 통과해야 한다"). L3(ratio)·L4(교차검증)는 지분율 원천 전용이라 비대상.


@dataclass
class GuardContext:
    """링킹 방어층 실행 컨텍스트 — 세션 스코프 1회 구축."""

    name_to_corp: dict[str, str]
    registry_official: set[str]            # L1 화이트리스트: 정식명 정확 존재
    blocklist: set[tuple[str, str]]        # L2: (source_ticker, target_ticker)
    ticker_by_corp: dict[str, str]
    counters: dict = field(default_factory=lambda: {
        "chunks": 0, "extracted": 0, "evidence_mismatch": 0, "verify_rejected": 0,
        "anonymous": 0, "not_active": 0, "l1_ambiguous_queued": 0,
        "l2_blocklisted": 0, "link_failed": 0, "self_ref": 0,
        "edges_kept": 0, "llm_error": 0,
    })


def build_guard_context(session) -> GuardContext:
    # transform.filters는 linking을 import하지 않으므로 순환 없음 (지연 import는
    # 모듈 로드 시점의 상호참조 가능성만 차단하는 방어).
    from modules.relation.transform.filters import load_link_blocklist

    official = set()
    ticker_by_corp = {}
    for r in session.query(CompanyRegistry).all():
        norm = normalize_company_name(r.name_current or "")
        if norm:
            official.add(norm)
        if r.ticker:
            ticker_by_corp[r.corp_code] = r.ticker
    return GuardContext(
        name_to_corp=build_name_to_corp_map(session),
        registry_official=official,
        blocklist=load_link_blocklist(),
        ticker_by_corp=ticker_by_corp,
    )


def _enqueue(session, surface: str, chunk_id: str | None) -> None:
    existing = session.query(LinkFailQueue).filter_by(surface_form=surface).one_or_none()
    if existing:
        existing.freq += 1
    else:
        session.add(LinkFailQueue(surface_form=surface, freq=1, sample_chunk_id=chunk_id))


def link_counterparty(session, ctx: GuardContext, surface: str,
                      chunk_id: str | None) -> str | None:
    """방어층 통과 링킹 — 실패·차단 시 None (사유는 ctx.counters에 집계)."""
    from modules.relation.transform.filters import is_ambiguous_abbrev

    norm = normalize_company_name(surface)
    # L1: 영문 2~5자 단독 약칭 — 정식명 정확 존재(화이트리스트) 아니면 큐로
    if is_ambiguous_abbrev(surface) and norm not in ctx.registry_official:
        ctx.counters["l1_ambiguous_queued"] += 1
        _enqueue(session, surface, chunk_id)
        return None
    corp = ctx.name_to_corp.get(norm)
    if not corp:
        ctx.counters["link_failed"] += 1
        _enqueue(session, surface, chunk_id)
        return None
    return corp


def blocked_pair(ctx: GuardContext, src_corp: str, dst_corp: str) -> bool:
    """L2 쌍 블록리스트 — ticker 기준(filters.apply와 동일 키), 양방향 검사."""
    s_t, d_t = ctx.ticker_by_corp.get(src_corp, ""), ctx.ticker_by_corp.get(dst_corp, "")
    return (s_t, d_t) in ctx.blocklist or (d_t, s_t) in ctx.blocklist
