"""filters→kifrs→dedupe 전체 사이클 멱등성 (M4, U-D13) — 세션 주입으로 격리.

★U1에서 발견된 실제 버그의 회귀 테스트: RelationLocal UNIQUE 키에 relation_type을
포함시켰던 최초 설계는 kifrs.apply()의 사후 재분류(ownership→subsidiary 등) UPDATE가
제약 위반으로 즉시 깨졌다(재현 확인). source_type으로 키를 교체해 해결 — 이 테스트가
그 수정을 고정한다. 반드시 실제 relation.db가 아니라 in_memory_session만 사용 —
이 클래스 버그를 조사하며 monkeypatch 실패로 실 DB를 오염시킨 적이 있어(세션 주입
없이 이미 임포트된 이름을 재할당해도 호출부엔 반영 안 됨), 이후 전 모듈에 session
파라미터를 추가했다.
"""

from __future__ import annotations

from modules.relation.storage.models import CompanyRegistry, RelationLocal, RelationRaw
from modules.relation.transform import dedupe, filters, kifrs


def _seed(session):
    session.add(CompanyRegistry(corp_code="00126380", ticker="005930", name_current="삼성전자", market="KOSPI"))
    session.add(CompanyRegistry(corp_code="00164779", ticker="000660", name_current="SK하이닉스", market="KOSPI"))
    # 신규 확장분(과거 top50.csv엔 없었을 법한 코스닥 소형주) — Registry 매칭 검증용
    session.add(CompanyRegistry(corp_code="01516933", ticker="900001", name_current="테스트코스닥", market="KOSDAQ"))
    session.add(
        RelationRaw(
            source_name="삼성전자",
            target_name="SK하이닉스",
            ratio=60.0,
            source_type="otrCprInvstmntSttus",
            bsns_year=2024,
        )
    )
    session.add(
        RelationRaw(
            source_name="테스트코스닥",
            target_name="삼성전자",
            ratio=15.0,
            relate="",
            source_type="hyslrSttus",
            bsns_year=2024,
        )
    )
    session.commit()


def _run_full_cycle(session):
    f = filters.apply(session=session)
    k = kifrs.apply(session=session)
    d = dedupe.apply(session=session)
    return f, k, d


def test_full_cycle_idempotent_on_rerun(in_memory_session):
    """filters→kifrs→dedupe를 두 번 반복해도 RelationLocal 행 수·내용이 불변해야 한다 (M4)."""
    _seed(in_memory_session)

    f1, k1, d1 = _run_full_cycle(in_memory_session)
    rows1 = in_memory_session.query(RelationLocal).all()
    snapshot1 = sorted(
        (r.source_corp, r.target_corp, r.relation_type, r.source_type, r.ratio) for r in rows1
    )

    # 두 번째 사이클 — 같은 RelationRaw로 재실행 (재수집 시나리오)
    f2, k2, d2 = _run_full_cycle(in_memory_session)
    rows2 = in_memory_session.query(RelationLocal).all()
    snapshot2 = sorted(
        (r.source_corp, r.target_corp, r.relation_type, r.source_type, r.ratio) for r in rows2
    )

    assert len(rows1) == len(rows2), f"행 수 변함: {len(rows1)} -> {len(rows2)}"
    assert snapshot1 == snapshot2, "재실행 후 내용이 달라짐 (멱등성 위반)"
    # kifrs가 두 번째 실행에서도 정상 재분류(예외 없이 완주)했는지
    assert k2["classified"] >= 0


def test_registry_based_matching_beyond_top50(in_memory_session):
    """top50.csv엔 없을 코스닥 소형주(테스트코스닥)도 Registry 매칭으로 엣지 생성돼야 한다."""
    _seed(in_memory_session)
    filters.apply(session=in_memory_session)

    edge = (
        in_memory_session.query(RelationLocal)
        .filter_by(source_corp="900001", target_corp="005930")
        .one_or_none()
    )
    assert edge is not None, "Registry 기반 매칭 실패 — top50 범위 밖 기업 엣지 누락"


def test_manual_overrides_empty_file_is_noop():
    """실제 manual_overrides.csv(주석뿐, 데이터 0행)를 로드해도 에러 없이 빈 dict."""
    overrides = filters.load_manual_overrides()
    assert overrides == {}


def test_stale_relation_local_pruned_when_raw_source_disappears(in_memory_session):
    """★U1 실측 버그 회귀: RelationRaw에서 사라진 관계는 RelationLocal에서도 정리(prune)돼야 한다.

    재현 경위: FTC를 클리크→스타 토폴로지로 바꾼 뒤(ftc.py 수정), 예전 클리크 시절
    RelationLocal 행(예: B↔C 직접 엣지)이 새 스타 데이터(허브 A→B, A→C)와 함께
    영구히 남아있었다 — filters.apply()가 upsert만 하고 삭제는 하지 않았기 때문.
    """
    session = in_memory_session
    session.add(CompanyRegistry(corp_code="00000001", ticker="000001", name_current="A", market="KOSPI"))
    session.add(CompanyRegistry(corp_code="00000002", ticker="000002", name_current="B", market="KOSPI"))
    session.add(CompanyRegistry(corp_code="00000003", ticker="000003", name_current="C", market="KOSPI"))

    # 1차: "클리크" 시절 — B→C 직접 ftc 관계가 raw에 존재
    session.add(
        RelationRaw(source_name="000002", target_name="000003", source_type="ftc", bsns_year=2025)
    )
    session.commit()
    filters.apply(session=session)

    stale = (
        session.query(RelationLocal)
        .filter_by(source_corp="000002", target_corp="000003", source_type="ftc")
        .one_or_none()
    )
    assert stale is not None, "테스트 전제 붕괴 — 1차 실행에서 B→C가 생성되지 않음"

    # 2차: "스타" 시절 — B→C raw 레코드가 사라지고 A→B, A→C(허브 기준)로 교체됨
    session.query(RelationRaw).filter_by(source_type="ftc").delete()
    session.add(
        RelationRaw(source_name="000001", target_name="000002", source_type="ftc", bsns_year=2025)
    )
    session.add(
        RelationRaw(source_name="000001", target_name="000003", source_type="ftc", bsns_year=2025)
    )
    session.commit()
    filters.apply(session=session)

    # B→C(구 클리크 잔재)는 정리되고, 허브 기준 A→B/A→C만 남아야 함
    remaining = {
        (r.source_corp, r.target_corp)
        for r in session.query(RelationLocal).filter_by(source_type="ftc").all()
    }
    assert remaining == {("000001", "000002"), ("000001", "000003")}, (
        f"prune 실패 — 예전 관계가 남아있거나 새 관계가 누락됨: {remaining}"
    )
