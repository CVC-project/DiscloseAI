"""개인·공익재단·비상장 필터 + top50 target 매칭.

동작: RelationRaw 전체 스캔 → 필터 통과한 레코드만 RelationLocal에 마이그레이션.
ticker 기반 source_corp/target_corp로 변환.

상세 규칙은 modules/relation/transform/CLAUDE.md 참조.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from modules.relation.common.names import build_ticker_map, normalize_company_name
from modules.relation.storage.db import get_local_session
from modules.relation.storage.models import RelationLocal, RelationRaw

logger = logging.getLogger(__name__)

_TOP50_CSV = Path(__file__).parent.parent / "data" / "top50.csv"

PERSONAL_RELATIONS = {
    "본인",
    "친인척",
    "친족",
    "인척",
    "계열회사 임원",
    "최대주주의 특수관계인",
    "최대주주 본인",
}
FOUNDATION_KEYWORDS = ("재단", "공익", "장학회", "문화재단")
RRN_PATTERN = re.compile(r"\d{6}-\d{7}")  # 주민번호


def is_personal_shareholder(name: str, relate: str | None) -> bool:
    """주주명·관계 필드로 개인 여부 판단."""
    if not name:
        return False
    # relate가 개인 관계어이고 name에 법인 표기(주식회사/㈜ 등)가 없으면 개인
    if relate:
        for kw in PERSONAL_RELATIONS:
            if kw in relate:
                if not any(
                    sym in name
                    for sym in ("주식회사", "(주)", "㈜", "(유)", "Ltd", "Inc", "Corp")
                ):
                    # 이름에 재단·회사 식별자 없고, 2~4자 한글이면 개인 확정
                    if 2 <= len(name.replace(" ", "")) <= 5 and all(
                        "\uac00" <= c <= "\ud7a3" for c in name.replace(" ", "")
                    ):
                        return True
    # 주민번호 패턴
    if RRN_PATTERN.search(name):
        return True
    return False


def is_foundation(name: str) -> bool:
    """기업명에 공익재단 키워드 포함."""
    if not name:
        return False
    return any(kw in name for kw in FOUNDATION_KEYWORDS)


def match_to_top50(normalized_name: str, ticker_map: dict[str, str]) -> str | None:
    """정규화된 이름 → ticker (매칭 실패 시 None)."""
    return ticker_map.get(normalized_name)


def apply() -> dict:
    """RelationRaw 전체 스캔 → 필터·정규화·ticker 매칭 후 RelationLocal에 INSERT.

    - hyslrSttus / otrCprInvstmntSttus: 개인·재단·미매칭 제외
    - ftc: 이미 ticker로 저장됐으므로 그대로 복사 (relation_type=ftc_group)
    - dart_filing: ticker 형태, 그대로 복사 (relation_type=dart_filing)
    - manual: 대상 없음 (향후 별도 로딩)

    Returns:
        {'kept_ownership', 'kept_ftc', 'kept_filing',
         'dropped_personal', 'dropped_foundation', 'dropped_unmatched'}
    """
    ticker_map = build_ticker_map(_TOP50_CSV)
    # ticker → ticker 매핑 (ftc/dart_filing은 이미 ticker로 저장됨)
    valid_tickers = set(ticker_map.values())

    session = get_local_session()
    counters = {
        "kept_ownership": 0,
        "kept_ftc": 0,
        "kept_filing": 0,
        "dropped_personal": 0,
        "dropped_foundation": 0,
        "dropped_unmatched": 0,
    }

    try:
        # 기존 RelationLocal 전체 삭제 후 재생성 (idempotent)
        session.query(RelationLocal).delete()

        raws = session.query(RelationRaw).all()
        for r in raws:
            if r.source_type == "hyslrSttus":
                # source = 주주, target = 자기 기업명 (자기 ticker는 알 수 없으나
                # target_name을 정규화해서 top50 ticker 조회 가능)
                target_ticker = ticker_map.get(normalize_company_name(r.target_name))
                if not target_ticker:
                    counters["dropped_unmatched"] += 1
                    continue
                # source 판별: 개인/재단/top50이 아닌 법인 → drop
                if is_personal_shareholder(r.source_name, r.relate):
                    counters["dropped_personal"] += 1
                    continue
                if is_foundation(r.source_name):
                    counters["dropped_foundation"] += 1
                    continue
                source_ticker = ticker_map.get(normalize_company_name(r.source_name))
                if not source_ticker:
                    counters["dropped_unmatched"] += 1
                    continue
                session.add(
                    RelationLocal(
                        source_corp=source_ticker,
                        target_corp=target_ticker,
                        relation_type="ownership",  # kifrs.apply()에서 재분류
                        ratio=r.ratio,
                        detail=f"{r.source_name} {r.ratio}% ({r.relate or ''})".strip(),
                        source_type=r.source_type,
                        bsns_year=r.bsns_year,
                    )
                )
                counters["kept_ownership"] += 1

            elif r.source_type == "otrCprInvstmntSttus":
                # source = 자기 기업명, target = 피투자법인명
                source_ticker = ticker_map.get(normalize_company_name(r.source_name))
                if not source_ticker:
                    counters["dropped_unmatched"] += 1
                    continue
                if is_foundation(r.target_name):
                    counters["dropped_foundation"] += 1
                    continue
                target_ticker = ticker_map.get(normalize_company_name(r.target_name))
                if not target_ticker:
                    counters["dropped_unmatched"] += 1
                    continue
                # 자기 자신 출자 무시
                if source_ticker == target_ticker:
                    continue
                session.add(
                    RelationLocal(
                        source_corp=source_ticker,
                        target_corp=target_ticker,
                        relation_type="ownership",
                        ratio=r.ratio,
                        detail=f"{r.target_name} {r.ratio}%",
                        source_type=r.source_type,
                        bsns_year=r.bsns_year,
                    )
                )
                counters["kept_ownership"] += 1

            elif r.source_type == "ftc":
                # ftc 엣지는 이미 ticker. 그대로 복사
                if r.source_name in valid_tickers and r.target_name in valid_tickers:
                    session.add(
                        RelationLocal(
                            source_corp=r.source_name,
                            target_corp=r.target_name,
                            relation_type="ftc_group",
                            ratio=None,
                            detail=r.raw_response,
                            source_type="ftc",
                            bsns_year=r.bsns_year,
                            group_name=_extract_group_from_raw(r.raw_response),
                        )
                    )
                    counters["kept_ftc"] += 1
                else:
                    counters["dropped_unmatched"] += 1

            elif r.source_type == "dart_filing":
                if r.source_name in valid_tickers and r.target_name in valid_tickers:
                    session.add(
                        RelationLocal(
                            source_corp=r.source_name,
                            target_corp=r.target_name,
                            relation_type="dart_filing",
                            ratio=None,
                            detail=f"사업보고서 주석: {r.relate or ''}",
                            source_type="dart_filing",
                            bsns_year=r.bsns_year,
                        )
                    )
                    counters["kept_filing"] += 1

        session.commit()
    finally:
        session.close()

    logger.info(f"filters.apply 결과: {counters}")
    return counters


def _extract_group_from_raw(raw: str | None) -> str | None:
    """RelationRaw.raw_response JSON에서 group_name 추출."""
    import json

    if not raw:
        return None
    try:
        obj = json.loads(raw)
        return obj.get("group_name") if isinstance(obj, dict) else None
    except (ValueError, TypeError):
        return None
