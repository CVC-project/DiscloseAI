"""엔티티 링킹 공용 유틸 — 밸류체인 T1 파서 전용 (valuechain PLAN.md §2.2 LinkFailQueue).

특수관계자 주석·공급계약 공시 등에서 등장하는 상대방 표기를 CompanyRegistry/
CompanyAlias 기준 corp_code로 매칭한다. 실패분은 LinkFailQueue에 빈도 누적
(M2 수동 별칭 보정 루프의 입력) — relation.db는 상장 법인만 노드로 삼는 원칙
(relation/CLAUDE.md 핵심 원칙 #1)이므로, 매칭 실패는 "정말 비상장이라 정당히
제외"와 "표기 불일치로 놓침"이 섞여 있음을 전제로 한다(빈도순 수동 검수 대상).
"""

from __future__ import annotations

from modules.relation.common.names import normalize_company_name
from modules.relation.storage.models import CompanyAlias, CompanyRegistry, LinkFailQueue


def build_name_to_corp_map(session) -> dict[str, str]:
    """{정규화된 이름: corp_code} — CompanyRegistry.name_current 우선, CompanyAlias로 보충."""
    mapping: dict[str, str] = {}
    for name, corp_code in session.query(
        CompanyRegistry.name_current, CompanyRegistry.corp_code
    ).all():
        norm = normalize_company_name(name)
        if norm:
            mapping[norm] = corp_code
    for alias, corp_code in session.query(CompanyAlias.alias, CompanyAlias.corp_code).all():
        norm = normalize_company_name(alias)
        if norm and norm not in mapping:
            mapping[norm] = corp_code
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
