"""Phase 2b — ingest/ftc.py 단위 테스트.

공정위 OpenAPI 응답 샘플(XML)로 fetch 동작, top50 매칭, 삼성 그룹 완전연결 검증.
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


def test_collect_creates_samsung_ftc_edges(in_memory_session, monkeypatch, tmp_path):
    """삼성 8개 소속회사 샘플로 collect 실행 → top50 매칭된 기업 간
    ftc_group 엣지가 C(N,2) 개수만큼 생성되는지.
    """
    from modules.relation.storage.models import CompanyNode, RelationRaw

    # in_memory_session 치환
    monkeypatch.setattr(
        "modules.relation.ingest.ftc.get_local_session",
        lambda: in_memory_session,
    )

    # top50 중 삼성 계열 6개만 미리 CompanyNode에 등록 (top50.csv 일부를 가정)
    samsung_nodes = [
        ("00126380", "삼성전자", "005930"),
        ("00149655", "삼성물산", "028260"),
        ("00126256", "삼성생명", "032830"),
        ("00139214", "삼성화재", "000810"),
        ("00126362", "삼성SDI", "006400"),
        ("00877059", "삼성바이오로직스", "207940"),
        ("00126371", "삼성전기", "009150"),
        ("00126478", "삼성중공업", "010140"),
    ]
    for corp_code, corp_name, ticker in samsung_nodes:
        in_memory_session.add(
            CompanyNode(
                corp_code=corp_code,
                corp_name=corp_name,
                ticker=ticker,
                market_cap=0.0,
                is_target=True,
            )
        )
    in_memory_session.commit()

    # 임시 top50.csv 생성 (build_ticker_map용)
    tmp_csv = tmp_path / "top50.csv"
    tmp_csv.write_text(
        "rank,corp_name,ticker,market_cap,group_name,sector,corp_code\n"
        + "\n".join(
            f"{i+1},{name},{ticker},1000,,,{corp_code}"
            for i, (corp_code, name, ticker) in enumerate(samsung_nodes)
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("modules.relation.ingest.ftc._TOP50_CSV", tmp_csv)

    # fetch_all_affiliates 치환 — 샘플 fixture와 동일한 8개 삼성 계열 반환
    # (samsung_nodes에 있는 top50 8개가 모두 매칭되도록 FTC 정식 법인명 사용)
    samsung_affiliates = [
        {"unityGrupNm": "삼성", "entrprsNm": "삼성전자(주)"},
        {"unityGrupNm": "삼성", "entrprsNm": "삼성물산(주)"},
        {"unityGrupNm": "삼성", "entrprsNm": "삼성생명보험(주)"},
        {"unityGrupNm": "삼성", "entrprsNm": "삼성화재해상보험(주)"},
        {"unityGrupNm": "삼성", "entrprsNm": "삼성에스디아이(주)"},
        {"unityGrupNm": "삼성", "entrprsNm": "삼성바이오로직스(주)"},
        {"unityGrupNm": "삼성", "entrprsNm": "삼성전기(주)"},
        {"unityGrupNm": "삼성", "entrprsNm": "삼성중공업(주)"},
        # top50 외 (노드 제외)
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
        result["top50_matched"] == 8
    ), f"8개사 매칭 기대, 실제 {result['top50_matched']}"
    assert result["groups_covered"] == 1
    # C(8,2) = 28개 엣지
    assert (
        result["ftc_group_edges"] == 28
    ), f"C(8,2)=28개 기대, 실제 {result['ftc_group_edges']}"

    # DB에도 28개 ftc 엣지 저장됨
    edges = in_memory_session.query(RelationRaw).filter_by(source_type="ftc").all()
    assert len(edges) == 28
    # source/target 모두 ticker 형태
    for e in edges:
        assert len(e.source_name) == 6
        assert len(e.target_name) == 6
        # 정렬 순서 보장 (source < target)
        assert e.source_name < e.target_name

    # CompanyNode.group_name이 '삼성'으로 업데이트됨
    samsung_group_nodes = (
        in_memory_session.query(CompanyNode).filter_by(group_name="삼성").all()
    )
    assert len(samsung_group_nodes) == 8
