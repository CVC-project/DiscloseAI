"""전체 상장사 company_master.json 조립 — integration-only (financial 코드 무수정).

원재료(financial 소유, read-only 조인):
  modules/financial/data/CORPCODE.xml                     DART 전체 corp_code 마스터 (corp_code/corp_name/stock_code)
  modules/financial/data/universe/krx_listed_tickers.json  현재 KRX 상장 티커 2,706개 (2026-07-16 KIND 수집)
  modules/financial/data/universe/company_ksic.json        corp_code -> KSIC 업종코드 2,731건
  modules/financial/data/universe/eqs_v3_scores_2021_2025.json        일반기업 EQS v3 (M1~M5) 2,683건
  modules/financial/data/universe/financial_feqs_scores_2021_2025.json  금융업 F-EQS (F1~F5) 118건

산출물: integration/dossier/data/company_master.json

⚠️ 정본 지위 관련 (2026-07-28):
  modules/relation/universe/PLAN.md U-D5는 "기업 마스터 = valuechain V0 CompanyRegistry
  단일 정본, 마스터 이중화 금지"를 이미 승인 결정으로 명시하고 있다. relation 쪽 U0
  (CompanyRegistry)는 이 스크립트 작성 시점 기준 아직 미착수(계획만 존재)라 직접 충돌은
  없지만, relation 담당자도 동일한 GPU 디스크 원본(krx_listed_tickers.json 등)을 쓰기로
  했으므로 핵심 데이터(ticker↔corp_code↔업종코드)는 정합적일 가능성이 높다.
  이 파일은 financial/EQS 전체 상장사 확장을 먼저 진행하기 위한 **잠정 마스터**다.
  relation의 CompanyRegistry가 실제로 나오면, 그쪽을 정본으로 승격하고 이 파일은
  거기서 read-only 파생하는 방식으로 전환 검토할 것 (마스터 이중화 해소).

알려진 갭 (이번 1단계 범위 밖, null로 남김):
  - market (KOSPI/KOSDAQ 구분) — 소스에 시장 구분 필드 없음
  - industry_name (KSIC 코드 -> 한글 업종명) — 매핑 테이블 미확보
  - is_etf — ETF는 대부분 DART corp_code 자체가 없어 이 마스터에 애초에 안 잡힘(별도 확인 필요)
  - listing_status — krx_listed_tickers 자체가 "현재 상장"만 담고 있어 전원 "listed"로 채움(폐지 종목 없음)

확인된 사실 (버그 아님, 검증 완료):
  - is_preferred_stock: krx_listed_tickers.json(2,706개) 자체가 이미 우선주 제외 목록이다
    (예: 005935 삼성전자우, 051915 LG화학우2우B 모두 미포함 확인). 그래서 이 필드는 현재
    소스 기준으로 전원 False가 나오는 게 정상이다 — corp_code 공유 그룹 검출 로직은
    향후 소스가 우선주 포함으로 바뀔 경우를 대비해 남겨둔다.
  - is_spac: CORPCODE.xml 전체엔 "기업인수목적" 포함사가 174개 있으나, 현재 2,706개
    목록엔 매칭되는 게 0개였다(검증 완료, 173건 전수 대조). 최근 신규 SPAC이 명명 관례를
    바꿨거나 이름에 공백·특수문자가 섞였을 가능성이 있어, 실제 SPAC이 0개라고 단정하진
    않는다 — 후속 검증 필요.

실행 (repo 루트에서)::
    python integration/dossier/build_company_master.py
"""

from __future__ import annotations

import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))

_CORPCODE_XML = os.path.join(_ROOT, "modules", "financial", "data", "CORPCODE.xml")
_UNIVERSE_DIR = os.path.join(_ROOT, "modules", "financial", "data", "universe")
_KRX_TICKERS = os.path.join(_UNIVERSE_DIR, "krx_listed_tickers.json")
_KRX_MARKET_INDUSTRY = os.path.join(_UNIVERSE_DIR, "krx_market_industry.json")
_KSIC_MAP = os.path.join(_UNIVERSE_DIR, "company_ksic.json")
_EQS_SCORES = os.path.join(_UNIVERSE_DIR, "eqs_v3_scores_2021_2025.json")
_FEQS_SCORES = os.path.join(_UNIVERSE_DIR, "financial_feqs_scores_2021_2025.json")

_DOSSIER_DATA_DIR = os.path.join(_HERE, "data")
_OUT_PATH = os.path.join(_DOSSIER_DATA_DIR, "company_master.json")

_REIT_RE = re.compile(r"리츠")
_SPAC_RE = re.compile(r"기업인수목적")
_PREFERRED_RE = re.compile(r".+우(\(?B\)?|\d)?$")  # "삼성전자우", "LG우", "삼성전자우B" 등


def _load_json(path: str):
    with open(path, "r", encoding="utf-8") as fp:
        return json.load(fp)


def _load_corpcode(path: str) -> list[dict]:
    tree = ET.parse(path)
    root = tree.getroot()
    rows = []
    for node in root.findall("list"):
        stock_code = (node.findtext("stock_code") or "").strip()
        if not stock_code:
            continue
        rows.append(
            {
                "corp_code": (node.findtext("corp_code") or "").strip(),
                "corp_name": (node.findtext("corp_name") or "").strip(),
                "stock_code": stock_code,
                "modify_date": (node.findtext("modify_date") or "").strip(),
            }
        )
    return rows


def _detect_preferred_flags(rows: list[dict]) -> dict[str, bool]:
    """같은 corp_code를 공유하는 티커 그룹에서, 이름이 '...우'로 끝나는 쪽을 우선주로 표시.

    한국 시장 관행: 우선주는 본주와 corp_code가 같고 종목코드(stock_code)만 다르다.
    """
    by_corp: dict[str, list[dict]] = {}
    for r in rows:
        by_corp.setdefault(r["corp_code"], []).append(r)

    flags: dict[str, bool] = {}
    for corp_code, group in by_corp.items():
        if len(group) < 2:
            flags[group[0]["stock_code"]] = False
            continue
        for r in group:
            flags[r["stock_code"]] = bool(_PREFERRED_RE.match(r["corp_name"]))
    return flags


def build() -> dict:
    krx = _load_json(_KRX_TICKERS)
    tickers: list[str] = krx["tickers"]

    corpcode_rows = _load_corpcode(_CORPCODE_XML)
    by_stock_code: dict[str, dict] = {}
    for row in corpcode_rows:
        # 동일 stock_code 중복 시 modify_date가 더 최신인 것 채택
        prev = by_stock_code.get(row["stock_code"])
        if prev is None or row["modify_date"] >= prev["modify_date"]:
            by_stock_code[row["stock_code"]] = row

    preferred_flags = _detect_preferred_flags(corpcode_rows)

    ksic_map: dict[str, str] = _load_json(_KSIC_MAP)

    market_industry_by_ticker: dict[str, dict] = {}
    if os.path.exists(_KRX_MARKET_INDUSTRY):
        for row in _load_json(_KRX_MARKET_INDUSTRY)["rows"]:
            market_industry_by_ticker[row["ticker"]] = row

    eqs_data = _load_json(_EQS_SCORES)
    eqs_by_corp: dict[str, dict] = {r["corp_code"]: r for r in eqs_data["results"]}

    feqs_data = _load_json(_FEQS_SCORES)
    feqs_by_corp: dict[str, dict] = {r["corp_code"]: r for r in feqs_data["results"]}

    dossier_tickers: set[str] = set()
    if os.path.isdir(_DOSSIER_DATA_DIR):
        for fname in os.listdir(_DOSSIER_DATA_DIR):
            if fname.startswith("firm_") and fname.endswith(".json"):
                dossier_tickers.add(fname[len("firm_") : -len(".json")])

    companies = []
    unmatched_tickers = []
    for ticker in tickers:
        info = by_stock_code.get(ticker)
        if info is None:
            unmatched_tickers.append(ticker)
            continue
        corp_code = info["corp_code"]
        corp_name = info["corp_name"]

        industry_code = ksic_map.get(corp_code)
        mi = market_industry_by_ticker.get(ticker)
        feqs_row = feqs_by_corp.get(corp_code)
        eqs_row = eqs_by_corp.get(corp_code)
        is_financial = feqs_row is not None

        eqs_block = None
        if is_financial:
            eqs_block = {
                "method": "feqs_v1_financial_peer_percentile_2021_2025",
                "total": feqs_row.get("total"),
                "grade": feqs_row.get("grade"),
            }
        elif eqs_row is not None:
            eqs_block = {
                "method": "eqs_v3_industry_percentile",
                "total": eqs_row.get("total"),
                "grade": eqs_row.get("grade"),
            }

        companies.append(
            {
                "ticker": ticker,
                "corp_code": corp_code,
                "company_name": corp_name,
                "market": mi["market"] if mi else None,
                "industry_code": industry_code,
                "industry_name": mi["industry_desc"] if mi else None,
                "is_financial": is_financial,
                "is_etf": None,
                "is_reit": bool(_REIT_RE.search(corp_name)),
                "is_spac": bool(_SPAC_RE.search(corp_name)),
                "is_preferred_stock": preferred_flags.get(ticker, False),
                "listing_status": "listed",
                "eqs": eqs_block,
                "has_dossier": ticker in dossier_tickers,
            }
        )

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "master_status": (
            "PROVISIONAL — financial/EQS 전체 상장사 확장용 잠정 마스터. "
            "modules/relation/universe/PLAN.md U-D5에 따라 향후 relation의 "
            "CompanyRegistry(valuechain V0)가 정본으로 승격되면 이 파일은 그쪽에서 "
            "read-only 파생하는 방식으로 전환 예정 (마스터 이중화 해소 목적). "
            "relation 담당자도 동일 GPU 디스크 원본을 사용하기로 합의됨(2026-07-28)."
        ),
        "source": {
            "krx_listed_tickers": "modules/financial/data/universe/krx_listed_tickers.json (fetched_at=%s)"
            % krx.get("fetched_at"),
            "corpcode_xml": "modules/financial/data/CORPCODE.xml",
            "ksic_map": "modules/financial/data/universe/company_ksic.json",
            "eqs_v3_scores": "modules/financial/data/universe/eqs_v3_scores_2021_2025.json (generated_at=%s)"
            % eqs_data.get("generated_at"),
            "financial_feqs_scores": "modules/financial/data/universe/financial_feqs_scores_2021_2025.json",
        },
        "known_gaps": [
            "industry_name은 KIND(kind.krx.co.kr)의 자유서술 업종설명이다 — DART KSIC 숫자코드"
            "(industry_code)와 공식 1:1 매핑표가 아니라 사람이 읽기 좋은 보조 라벨일 뿐이다.",
            "is_etf 미판정 (ETF는 대부분 DART corp_code 자체가 없어 이 마스터에 안 잡힐 가능성)",
            "listing_status는 krx_listed_tickers 스냅샷 기준 전원 'listed' (폐지 종목 없음)",
            "market 미확보 3건(057050 현대홈쇼핑, 060240 스타코링크, 467930 IBKS제23호스팩) "
            "— KIND·CORPCODE 간 사명 불일치 추정, 영향 미미해 보류",
        ],
        "ticker_count": len(tickers),
        "matched_count": len(companies),
        "unmatched_tickers": unmatched_tickers,
        "companies": companies,
    }


def main() -> int:
    result = build()
    os.makedirs(_DOSSIER_DATA_DIR, exist_ok=True)
    with open(_OUT_PATH, "w", encoding="utf-8") as fp:
        json.dump(result, fp, ensure_ascii=False, indent=2)

    print(f"[done] {_OUT_PATH}")
    print(f"  전체 티커: {result['ticker_count']}")
    print(f"  매칭 성공: {result['matched_count']}")
    print(f"  미매칭: {len(result['unmatched_tickers'])} {result['unmatched_tickers'][:10]}")
    is_financial_count = sum(1 for c in result["companies"] if c["is_financial"])
    is_preferred_count = sum(1 for c in result["companies"] if c["is_preferred_stock"])
    is_reit_count = sum(1 for c in result["companies"] if c["is_reit"])
    is_spac_count = sum(1 for c in result["companies"] if c["is_spac"])
    has_eqs_count = sum(1 for c in result["companies"] if c["eqs"] is not None)
    has_dossier_count = sum(1 for c in result["companies"] if c["has_dossier"])
    print(f"  is_financial: {is_financial_count}")
    print(f"  is_preferred_stock: {is_preferred_count}")
    print(f"  is_reit: {is_reit_count}")
    print(f"  is_spac: {is_spac_count}")
    print(f"  EQS/F-EQS 점수 보유: {has_eqs_count}")
    print(f"  현재 dossier(48개) 포함: {has_dossier_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
