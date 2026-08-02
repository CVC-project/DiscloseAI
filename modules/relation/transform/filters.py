"""개인·공익재단·비상장 필터 + 전 상장사 target 매칭 (★U1: top50 → Registry).

동작: RelationRaw 전체 스캔 → 필터 통과한 레코드만 RelationLocal에 upsert.
ticker 기반 source_corp/target_corp로 변환.

상세 규칙은 modules/relation/transform/CLAUDE.md 참조.
"""

from __future__ import annotations

import csv
import logging
import re
from pathlib import Path

from modules.relation.common.names import (
    build_ticker_map_from_registry,
    normalize_company_name,
)
from modules.relation.storage.db import get_local_session
from modules.relation.storage.models import LinkFailQueue, RelationLocal, RelationRaw
from modules.relation.transform import entity_kind

logger = logging.getLogger(__name__)

_MANUAL_OVERRIDES_CSV = Path(__file__).parent.parent / "data" / "manual_overrides.csv"

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
# 주주명 칸에 잘못 들어오는 주식 종류 어휘 (DART 응답 컬럼 밀림 — 445090 실측)
_STOCK_KIND_TOKENS = {"보통주", "우선주", "종류주", "전환우선주", "상환우선주", "기타주"}


def _stock_kind_rank(stock_knd: str | None) -> int:
    """의결권 우선순위 — 작을수록 우선. K-IFRS 지배력은 **의결권** 기준이다."""
    s = (stock_knd or "").strip()
    if not s:
        return 1          # 미상 — 보통주보다 뒤, 우선주보다 앞
    if "보통" in s:
        return 0
    if "우선" in s or "종류" in s:
        return 2
    return 1
RRN_PATTERN = re.compile(r"\d{6}-\d{7}")  # 주민번호


_CORP_MARKERS = ("주식회사", "(주)", "㈜", "(유)", "Ltd", "Inc", "Corp")


def _looks_like_korean_person_name(name: str) -> bool:
    """2~5자 순한글 이름이면서 법인 표기가 없음 → 개인명으로 간주."""
    stripped = name.replace(" ", "")
    if not (2 <= len(stripped) <= 5):
        return False
    if any(sym in name for sym in _CORP_MARKERS):
        return False
    return all("\uac00" <= c <= "\ud7a3" for c in stripped)


def is_personal_shareholder(name: str, relate: str | None) -> bool:
    """주주명·관계 필드로 개인 여부 판단.

    판별 경로:
      (A) relate가 PERSONAL_RELATIONS에 포함 + 이름이 개인명 형태
      (B) relate가 비어있어도 이름이 명확한 개인명 형태면 개인으로 간주
          (DART 일부 응답에서 relate 미기재 케이스 방어)
      (C) 주민번호 패턴 포함
    """
    if not name:
        return False
    # (C) 주민번호 패턴
    if RRN_PATTERN.search(name):
        return True
    # (A) 관계어 + 개인명 형태
    if relate:
        for kw in PERSONAL_RELATIONS:
            if kw in relate and _looks_like_korean_person_name(name):
                return True
    # (B) relate 비어있을 때 개인명 형태만으로 판별 (false positive 허용 — 법인명에 해당하는 2~5자 한글은 대부분 법인 표기 포함)
    elif _looks_like_korean_person_name(name):
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


# ★2026-07-28 (FN-013): 타법인출자(otrCpr) 대상명이 짧은 영문 약칭 단독이면 상장사
# 자동 링킹을 금지한다. 실제 사고: 현대차 사업보고서의 출자 대상 "HMM"(해외 생산법인
# HMMA/HMMC류 축약 표기)이 상장 해운사 HMM(011200)에 정확 일치로 오링킹 →
# "현대차가 HMM 99.99% 종속" 허위 엣지 4개년치 생성(리더 발견). 영문 2~5자 단독
# 표기는 동명 충돌 위험이 구조적으로 높아 자동 매칭 대신 LinkFailQueue로 보내
# 수동 확정(M2 루프)한다. 한글 포함·정식 법인 표기는 게이트 대상이 아님.
AMBIGUOUS_ABBREV_RE = re.compile(r"^[A-Za-z&.\- ]{2,5}$")


def is_ambiguous_abbrev(raw_name: str) -> bool:
    """원문 표기가 영문 약칭 단독(공백·기호 포함 5자 이하)인지 — 자동 링킹 금지 대상."""
    return bool(raw_name) and bool(AMBIGUOUS_ABBREV_RE.fullmatch(raw_name.strip()))


_LINK_BLOCKLIST_CSV = Path(__file__).parent.parent / "data" / "link_blocklist.csv"


def load_link_blocklist() -> set[tuple[str, str]]:
    """오링킹 확정 (source,target) 쌍 — otrCpr 링킹에서 차단 (FN-013 M2 수동 보정).

    한글 동명 비상장 자회사(예: DS단석의 '하이브 주식회사')는 약칭 게이트로 못 막는다 —
    CPA 검수로 확정된 쌍을 여기 등재하면 transform 재실행 시 prune이 기존 행도 정리한다.
    """
    if not _LINK_BLOCKLIST_CSV.exists():
        return set()
    pairs: set[tuple[str, str]] = set()
    with open(_LINK_BLOCKLIST_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(ln for ln in f if not ln.lstrip().startswith("#"))
        for row in reader:
            s, t = (row.get("source_ticker") or "").strip(), (row.get("target_ticker") or "").strip()
            if s and t:
                pairs.add((s, t))
    return pairs


def _enqueue_link_fail(session, surface_form: str, sample: str) -> None:
    """모호 표기를 LinkFailQueue에 적재(있으면 freq+1) — M2 수동 별칭 루프의 입력."""
    row = (
        session.query(LinkFailQueue)
        .filter(LinkFailQueue.surface_form == surface_form)
        .first()
    )
    if row:
        row.freq = (row.freq or 1) + 1
    else:
        session.add(
            LinkFailQueue(surface_form=surface_form, freq=1, sample_chunk_id=sample)
        )


def load_manual_overrides() -> dict[str, str]:
    """manual_overrides.csv → {ticker: group_name} (★U1 구현 — 이전엔 스캐폴드만 존재).

    CPA가 공정위·K-IFRS·주석 파싱을 거치고도 group_name이 비거나 보정이 필요한
    경우만 채우는 소수 파일(실전 0~2건 예상). `#`로 시작하는 줄은 주석으로 무시.
    """
    if not _MANUAL_OVERRIDES_CSV.exists():
        return {}
    overrides: dict[str, str] = {}
    with open(_MANUAL_OVERRIDES_CSV, encoding="utf-8") as f:
        lines = [ln for ln in f if not ln.lstrip().startswith("#")]
    for row in csv.DictReader(lines):
        ticker = (row.get("ticker") or "").strip()
        group_name = (row.get("group_name") or "").strip()
        if ticker and group_name:
            overrides[ticker] = group_name
    return overrides


# ★ 2026-07-29 소실 사고: dart_filing을 이 튜플에서 제외 — U3부터 dart_filing의
# 정본 생산자는 valuechain related_party.apply_governance()(RelationLocal 직접 적재)
# 인데, 이 prune 스코프에 남아 있어 "RelationRaw에 없다"는 이유로 transform 재실행
# 때마다 전량(115엣지·7개사) 오인 삭제됐다. prune은 생산자 소관 원칙: 이 함수는
# RelationRaw에서 복사하는 3종만 관리하고, dart_filing stale 정리는 apply_governance
# 전량 실행이 담당한다. (ingest/filing.py의 RelationRaw dart_filing 경로는 top50
# 시절 legacy — 아래 복사 분기는 하위호환으로만 유지, prune 소유권은 없음.)
_MANAGED_SOURCE_TYPES = ("hyslrSttus", "otrCprInvstmntSttus", "ftc")


def _upsert_relation_local(session, **fields) -> tuple:
    """UNIQUE(source_corp, target_corp, source_type, bsns_year) 키로 upsert (★U1 멱등, U-D13).

    relation_type이 아니라 source_type이 키다 — kifrs.apply()가 relation_type을
    사후 재분류(ownership→subsidiary 등)하므로 relation_type은 안정적 식별자가
    아니다(models.py RelationLocal 주석 참조, 재현 확인됨). 기존 행이 있으면 갱신,
    없으면 삽입 — 재실행 시 중복·유실 없음(D12).

    Returns: 이 행의 자연키 튜플(apply()가 prune 대상 판별에 사용).
    """
    stock_knd = fields.pop("_stock_knd", None)
    fields["_stock_knd"] = stock_knd            # 아래 비교용(모델 컬럼 아님 — 마지막에 제거)
    key = {
        "source_corp": fields["source_corp"],
        "target_corp": fields["target_corp"],
        "source_type": fields["source_type"],
        "bsns_year": fields.get("bsns_year"),
    }
    existing = session.query(RelationLocal).filter_by(**key).one_or_none()
    if existing:
        # ★2026-07-29 order-dependent 사고 수정: DART hyslrSttus는 **주식 종류마다
        # 별도 행**을 내려준다(보통주 34.0% + 우선주 0.71%). 무조건 덮어쓰면 응답
        # 순서에 따라 우선주 값이 이겨 지분율이 0.71%가 되고, 이어 kifrs가 5% 미만으로
        # 판정해 **엣지를 통째로 삭제**했다(실측: 계양전기←해성산업 34%, DL←㈜대림
        # 48.27%, JW중외제약←JW홀딩스 40.25% 등 최대주주 다수가 화면에서 사라짐).
        #
        # ★2차 수정(적대적 검증): 1차의 "higher ratio 채택"은 **우선주를 고르는**
        # 오류를 낳았다(428건 — 레이←㈜레이홀딩스 보통주 7.55% / 우선주 29.91% →
        # 29.91% associate). K-IFRS 지배력 판정의 기준은 **의결권**이므로 비율 크기가
        # 아니라 **주식 종류**가 우선이다: 보통주 > 종류주 > 미상. 같은 종류일 때만
        # higher ratio(= dedupe.py 양방향 중복 관례).
        incoming_ratio = fields.get("ratio")
        rank_in = _stock_kind_rank(fields.get("_stock_knd"))
        rank_ex = _stock_kind_rank(getattr(existing, "_stock_knd_cache", None))
        if rank_in != rank_ex:
            keep_existing = rank_in > rank_ex      # 숫자가 작을수록 우선(보통주=0)
        else:
            keep_existing = (
                incoming_ratio is None and existing.ratio is not None
            ) or (
                incoming_ratio is not None
                and existing.ratio is not None
                and incoming_ratio < existing.ratio
            )
        if not keep_existing:
            for k, v in fields.items():
                if k != "_stock_knd":
                    setattr(existing, k, v)
            existing._stock_knd_cache = stock_knd
        existing.status = "active"
    else:
        row = RelationLocal(**{k: v for k, v in fields.items() if k != "_stock_knd"},
                            status="active")
        row._stock_knd_cache = stock_knd
        session.add(row)
    return (key["source_corp"], key["target_corp"], key["source_type"], key["bsns_year"])


def apply(session=None) -> dict:
    """RelationRaw 전체 스캔 → 필터·정규화·ticker 매칭 후 RelationLocal에 upsert.

    - hyslrSttus / otrCprInvstmntSttus: 개인·재단·미매칭 제외
    - ftc: 이미 ticker로 저장됐으므로 그대로 복사 (relation_type=ftc_group) +
      manual_overrides.csv의 group_name 보정 적용
    - dart_filing: ticker 형태, 그대로 복사 (relation_type=dart_filing)

    ★U1: ticker_map을 top50.csv가 아니라 CompanyRegistry(전 상장사)에서 구축 —
    top50 자연 필터가 E2E 단절 지점이었음(universe/PLAN.md U-D1). 삭제 후 재삽입이
    아니라 UNIQUE 키 upsert(U-D13) — 재실행해도 중복 없음.

    ★U1 실측 버그 수정(2026-07-21): upsert만으로는 "예전엔 있었는데 지금 RelationRaw엔
    없는" 행이 영원히 남는다 — 재현: FTC를 클리크→스타로 바꾼 뒤에도 예전 클리크 시절
    RelationLocal 행(예: 006400↔009150 직접 엣지)이 새 스타 데이터와 함께 남아있었음
    (RelationRaw는 collect()가 지우고 다시 채우지만, RelationLocal은 upsert-only라
    원본에서 사라진 관계를 그대로 들고 있었던 것). 이번 실행에서 실제로 upsert된
    키 집합을 추적해, 이 함수가 관리하는 3개 source_type(hyslrSttus·
    otrCprInvstmntSttus·ftc) 중 RelationRaw에 더 이상 없는 행은 실행 끝에
    정리(prune)한다. ★dart_filing은 2026-07-29부터 prune 스코프 제외 —
    _MANAGED_SOURCE_TYPES 주석 참조(생산자 apply_governance 소관).

    session: 주입 시 그 세션 사용(테스트용 — 닫지 않음, 커밋은 호출). None이면 로컬 relation.db.

    Returns:
        {'kept_ownership', 'kept_ftc', 'kept_filing',
         'dropped_personal', 'dropped_foundation', 'dropped_unmatched', 'pruned_stale'}
    """
    owns_session = session is None
    if owns_session:
        session = get_local_session()
    ticker_map = build_ticker_map_from_registry(session)
    # ticker → ticker 매핑 (ftc/dart_filing은 이미 ticker로 저장됨)
    valid_tickers = set(ticker_map.values())
    manual_overrides = load_manual_overrides()
    link_blocklist = load_link_blocklist()

    counters = {
        "kept_ownership": 0,
        "kept_ftc": 0,
        "kept_filing": 0,
        "dropped_personal": 0,
        "dropped_foundation": 0,
        "dropped_unmatched": 0,
        "queued_ambiguous": 0,
        "dropped_blocklist": 0,
        "dropped_ratio_invalid": 0,
        "pruned_stale": 0,
        "unlisted_nodes": 0,       # ★U5: 비상장·개인 노드로 살린 상대 (과거엔 drop)
        "pruned_orphan_nodes": 0,
        "dropped_self_loop": 0,
        "dropped_stock_kind_row": 0,
        "kind_reconciled": 0,
    }
    touched_keys: set[tuple] = set()

    try:
        raws = session.query(RelationRaw).all()
        for r in raws:
            if r.source_type == "hyslrSttus":
                # ★DART 응답 컬럼 밀림 방어(실측 445090 에이직랜드): 주주명 칸에
                # 주식 종류가 들어온 원문 오류 — nm='보통주', stock_knd='최대주주'.
                # 이런 행을 노드로 만들면 '보통주'라는 주주가 생긴다.
                if (r.source_name or "").strip() in _STOCK_KIND_TOKENS:
                    counters["dropped_stock_kind_row"] += 1
                    continue
                # source = 주주, target = 자기 기업명 (자기 ticker는 알 수 없으나
                # target_name을 정규화해서 top50 ticker 조회 가능)
                target_ticker = ticker_map.get(normalize_company_name(r.target_name))
                if not target_ticker:
                    counters["dropped_unmatched"] += 1
                    continue
                # source 판별: 상장사면 그대로, 아니면 U5 비상장 노드로 적재
                # (개인·재단·비상장 전부 — 과거엔 여기서 drop돼 화면이 비었다)
                source_ticker = ticker_map.get(normalize_company_name(r.source_name))
                if not source_ticker:
                    source_ticker = entity_kind.upsert_unlisted_node(
                        session,
                        anchor_corp=target_ticker,
                        name_raw=r.source_name,
                        relate=r.relate,
                        provenance=f"hyslrSttus:{r.bsns_year}",
                        surname_fallback=True,   # 최대주주 현황 = 사람 명부
                    )
                    if not source_ticker:
                        counters["dropped_unmatched"] += 1
                        continue
                    counters["unlisted_nodes"] += 1
                # ★2026-07-29: 자사주·최대주주 본인 행은 A→A 자기 엣지가 된다
                # (실측 36건 — "KG스틸의 관계기업 = KG스틸 39.97%"가 화면에 떴다).
                # hyslrSttus에는 '자기주식'·본인 지분이 함께 기재되므로 여기서 막는다.
                if source_ticker == target_ticker:
                    counters["dropped_self_loop"] += 1
                    continue
                touched_keys.add(
                    _upsert_relation_local(
                        session,
                        source_corp=source_ticker,
                        target_corp=target_ticker,
                        relation_type="ownership",  # kifrs.apply()에서 재분류
                        ratio=r.ratio,
                        detail=f"{r.source_name} {r.ratio}% ({r.relate or ''})".strip(),
                        source_type=r.source_type,
                        bsns_year=r.bsns_year,
                        _stock_knd=r.stock_knd,
                    )
                )
                counters["kept_ownership"] += 1

            elif r.source_type == "otrCprInvstmntSttus":
                # source = 자기 기업명, target = 피투자법인명
                source_ticker = ticker_map.get(normalize_company_name(r.source_name))
                if not source_ticker:
                    counters["dropped_unmatched"] += 1
                    continue
                # FN-013: ratio sanity — 지분율에 주식수가 들어온 오파싱(영풍→시그네틱스 710651%) 차단
                if r.ratio is not None and r.ratio > 100:
                    counters["dropped_ratio_invalid"] += 1
                    continue
                # FN-013: 영문 약칭 단독 대상명 게이트. 단 NAVER·KT·SK·HMM처럼 **정식 사명
                # 자체가 약칭 형태인 실존 상장사**(ticker_map에 정확 존재)는 통과 —
                # 이 경우의 오링킹(현대차→HMM)은 쌍 단위 블록리스트가 최종 방어한다.
                # ★U5: 게이트에 걸려도 이제 버리지 않는다 — 상장사로 붙이지 않을 뿐
                # **공시에 적힌 그대로 비상장 노드**가 된다('HMA'는 'HMA'로 표시).
                # 사고(FN-013)는 그대로 차단하면서 정보는 살린다.
                target_ticker = None
                gated = is_ambiguous_abbrev(r.target_name) and not ticker_map.get(
                    normalize_company_name(r.target_name)
                )
                if gated:
                    _enqueue_link_fail(
                        session, r.target_name, f"otrCpr:{r.source_name}:{r.bsns_year}"
                    )
                    counters["queued_ambiguous"] += 1
                else:
                    target_ticker = ticker_map.get(normalize_company_name(r.target_name))
                if not target_ticker:
                    # 재단도 비상장 노드로 표시(공익재단 출자는 지배구조상 유의미)
                    target_ticker = entity_kind.upsert_unlisted_node(
                        session,
                        anchor_corp=source_ticker,
                        name_raw=r.target_name,
                        relate=None,
                        provenance=f"otrCprInvstmntSttus:{r.bsns_year}",
                        allow_person=False,   # 타법인출자 대상은 정의상 법인
                    )
                    if not target_ticker:
                        counters["dropped_unmatched"] += 1
                        continue
                    counters["unlisted_nodes"] += 1
                # FN-013 M2: CPA 검수로 확정된 오링킹 쌍 차단 (동명 비상장·구사명 충돌·수치 오류)
                if (source_ticker, target_ticker) in link_blocklist:
                    counters["dropped_blocklist"] += 1
                    continue
                # 자기 자신 출자 무시
                if source_ticker == target_ticker:
                    continue
                touched_keys.add(
                    _upsert_relation_local(
                        session,
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
                # ftc 엣지는 이미 ticker. 그대로 복사 (manual_overrides로 group_name 보정)
                if r.source_name in valid_tickers and r.target_name in valid_tickers:
                    group_name = manual_overrides.get(r.target_name) or _extract_group_from_raw(
                        r.raw_response
                    )
                    touched_keys.add(
                        _upsert_relation_local(
                            session,
                            source_corp=r.source_name,
                            target_corp=r.target_name,
                            relation_type="ftc_group",
                            ratio=None,
                            detail=r.raw_response,
                            source_type="ftc",
                            bsns_year=r.bsns_year,
                            group_name=group_name,
                        )
                    )
                    counters["kept_ftc"] += 1
                else:
                    counters["dropped_unmatched"] += 1

            elif r.source_type == "dart_filing":
                if r.source_name in valid_tickers and r.target_name in valid_tickers:
                    touched_keys.add(
                        _upsert_relation_local(
                            session,
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

        # ★U1 실측 버그 수정: RelationRaw에서 사라진(더 이상 어떤 raw 레코드도 만들지
        # 않는) 행을 prune — 이 함수가 관리하는 3개 source_type 전체를 스캔해 이번 실행
        # 에서 touched_keys에 없는 것만 삭제(dart_filing·manual 등 다른 생산자의
        # source_type은 건드리지 않음 — _MANAGED_SOURCE_TYPES 주석 참조).
        stale = (
            session.query(RelationLocal)
            .filter(RelationLocal.source_type.in_(_MANAGED_SOURCE_TYPES))
            .all()
        )
        for row in stale:
            key = (row.source_corp, row.target_corp, row.source_type, row.bsns_year)
            if key not in touched_keys:
                session.delete(row)
                counters["pruned_stale"] += 1

        # ★U5: 엣지가 사라진 비상장 노드 정리 (참조 무결성 기준 — entity_kind 주석 참조)
        # ⚠️ 순서: reconcile → prune. reconcile이 노드를 **병합·삭제**하므로 prune을
        #    먼저 돌리면 그 결과로 생긴 끊어진 참조를 못 잡는다(2026-07-30 실측 1건).
        session.flush()
        counters["kind_reconciled"] = entity_kind.reconcile_unlisted_kinds(session)
        session.flush()
        counters["pruned_orphan_nodes"] = entity_kind.prune_orphan_unlisted_nodes(session)

        session.commit()
    finally:
        if owns_session:
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
