"""Phase 2b — ingest/ftc.py 단위 테스트.

공정위 OpenAPI 응답 샘플(XML)로 fetch 동작, 전 상장사 매칭, 삼성 그룹 스타
토폴로지(★U1, U-D4 — 기존 클리크에서 전환) 검증.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree

from modules.relation.ingest import ftc

FIXTURES = Path(__file__).parent.parent / "fixtures"


# ============================================================
# fetch_available_months (publicYmList)
# ============================================================


def test_fetch_available_months_parses_xml(monkeypatch):
    sample = etree.fromstring((FIXTURES / "ftc_publicYmList_sample.xml").read_bytes())
    # ftc_get_all_pages는 내부에서 ftc_get를 여러 번 호출하는데
    # totalCount=3, numOfRows=1000이라 1페이지로 종료
    monkeypatch.setattr(
        "modules.relation.ingest.ftc.ftc_get_all_pages",
        lambda api_path, params, item_key: [
            {"othbcYm": "202505", "jobSeCode": "0001"},
            {"othbcYm": "202405", "jobSeCode": "0001"},
            {"othbcYm": "202305", "jobSeCode": "0001"},
        ],
    )
    months = ftc.fetch_available_months()
    assert len(months) == 3
    assert months[0]["othbcYm"] == "202505"
    assert sample is not None  # sample XML 정합성만 확인


def test_latest_yyyymm(monkeypatch):
    monkeypatch.setattr(
        "modules.relation.ingest.ftc.fetch_available_months",
        lambda: [
            {"othbcYm": "202305"},
            {"othbcYm": "202505"},
            {"othbcYm": "202405"},
        ],
    )
    assert ftc.latest_yyyymm() == "202505"


# ============================================================
# collect — 삼성 그룹 완전연결
# ============================================================


def test_collect_creates_samsung_ftc_edges(in_memory_session, monkeypatch):
    """삼성 8개 소속회사 샘플로 collect 실행 → 전 상장사 매칭된 기업 간
    ftc_group 엣지가 **스타 토폴로지**(허브=시총 최댓값, n-1개)로 생성되는지
    (★U1, U-D4 — 기존 클리크 C(8,2)=28개에서 전환).
    """
    from modules.relation.storage.models import CompanyNode, CompanyRegistry, RelationRaw

    # in_memory_session 치환
    monkeypatch.setattr(
        "modules.relation.ingest.ftc.get_local_session",
        lambda: in_memory_session,
    )

    # 삼성 계열 8개사 — CompanyRegistry(★U1, top50.csv 대체) + 레거시 CompanyNode 병존
    # 삼성전자를 시총 최댓값으로 설정 → 허브로 선정돼야 함(현실과 부합)
    samsung_nodes = [
        ("00126380", "삼성전자", "005930", 500_0000_0000_0000),
        ("00149655", "삼성물산", "028260", 30_0000_0000_0000),
        ("00126256", "삼성생명", "032830", 20_0000_0000_0000),
        ("00139214", "삼성화재", "000810", 15_0000_0000_0000),
        ("00126362", "삼성SDI", "006400", 25_0000_0000_0000),
        ("00877059", "삼성바이오로직스", "207940", 60_0000_0000_0000),
        ("00126371", "삼성전기", "009150", 10_0000_0000_0000),
        ("00126478", "삼성중공업", "010140", 8_0000_0000_0000),
    ]
    for corp_code, corp_name, ticker, cap in samsung_nodes:
        in_memory_session.add(
            CompanyNode(
                corp_code=corp_code, corp_name=corp_name, ticker=ticker,
                market_cap=0.0, is_target=True,
            )
        )
        in_memory_session.add(
            CompanyRegistry(
                corp_code=corp_code, ticker=ticker, name_current=corp_name,
                market="KOSPI", market_cap_krw=cap,
            )
        )
    in_memory_session.commit()

    # fetch_all_affiliates 치환 — 샘플 fixture와 동일한 8개 삼성 계열 반환
    samsung_affiliates = [
        {"unityGrupNm": "삼성", "entrprsNm": "삼성전자(주)"},
        {"unityGrupNm": "삼성", "entrprsNm": "삼성물산(주)"},
        {"unityGrupNm": "삼성", "entrprsNm": "삼성생명보험(주)"},
        {"unityGrupNm": "삼성", "entrprsNm": "삼성화재해상보험(주)"},
        {"unityGrupNm": "삼성", "entrprsNm": "삼성에스디아이(주)"},
        {"unityGrupNm": "삼성", "entrprsNm": "삼성바이오로직스(주)"},
        {"unityGrupNm": "삼성", "entrprsNm": "삼성전기(주)"},
        {"unityGrupNm": "삼성", "entrprsNm": "삼성중공업(주)"},
        # 레지스트리 외(비상장·팀 등) — 매칭 안 되고 노드 제외돼야 함
        {"unityGrupNm": "삼성", "entrprsNm": "삼성디스플레이(주)"},
        {"unityGrupNm": "삼성", "entrprsNm": "수원삼성축구단(주)"},
    ]
    monkeypatch.setattr(
        "modules.relation.ingest.ftc.fetch_all_affiliates",
        lambda yyyymm, presentn_year=None: samsung_affiliates,
    )

    result = ftc.collect(yyyymm="202505")

    # 삼성 8개사 매칭
    assert (
        result["registry_matched"] == 8
    ), f"8개사 매칭 기대, 실제 {result['registry_matched']}"
    assert result["groups_covered"] == 1
    # 스타 토폴로지: n-1 = 7개 엣지 (클리크 C(8,2)=28개가 아님)
    assert (
        result["ftc_group_edges"] == 7
    ), f"스타 n-1=7개 기대, 실제 {result['ftc_group_edges']}"

    # DB에도 7개 ftc 엣지 저장됨 — 전부 허브(삼성전자, 시총 최댓값)에서 출발
    edges = in_memory_session.query(RelationRaw).filter_by(source_type="ftc").all()
    assert len(edges) == 7
    for e in edges:
        assert len(e.source_name) == 6
        assert len(e.target_name) == 6
        assert e.source_name == "005930", "허브는 시총 최댓값(삼성전자)이어야 함"
        assert e.target_name != "005930"

    # CompanyNode.group_name이 '삼성'으로 업데이트됨 (레거시 병존)
    samsung_group_nodes = (
        in_memory_session.query(CompanyNode).filter_by(group_name="삼성").all()
    )
    assert len(samsung_group_nodes) == 8
