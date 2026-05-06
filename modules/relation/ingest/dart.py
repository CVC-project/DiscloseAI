"""DART OpenAPI 수집.

2개 엔드포인트 호출:
- hyslrSttus.json       (최대주주 및 특수관계인 현황 — 들어오는 지분)
- otrCprInvstmntSttus.json (타법인 출자현황 — 나가는 지분)

상세 파라미터·응답 필드는 modules/relation/ingest/CLAUDE.md 참조.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import zipfile
from pathlib import Path

from lxml import etree

from modules.relation.ingest._http import (
    DART_STATUS_NO_DATA,
    DART_STATUS_OK,
    DART_STATUS_ORIGIN_MISSING,
    dart_get,
    dart_get_binary,
)
from modules.relation.storage.db import get_local_session
from modules.relation.storage.models import CompanyNode, RelationRaw

logger = logging.getLogger(__name__)

ENDPOINT_SHAREHOLDERS = "hyslrSttus.json"
ENDPOINT_INVESTMENTS = "otrCprInvstmntSttus.json"

_TOP50_CSV = Path(__file__).parent.parent / "data" / "top50.csv"


# ============================================================
# 2a.1 — corp_code 매핑 (one-off)
# ============================================================


def map_corp_codes() -> dict:
    """DART corpCode.xml 전체 다운 → top50.csv의 corp_code 컬럼 갱신.

    동작:
      1. DART `corpCode.xml` 호출 → ZIP 바이너리
      2. ZIP 내부 CORPCODE.xml 파싱 → {stock_code: corp_code} 맵
      3. top50.csv 읽어 ticker별 corp_code 채움
      4. top50.csv 저장 (corp_code 컬럼 갱신)
      5. storage/CompanyNode에도 UPSERT

    Returns: {'matched': int, 'unmatched_tickers': [...], 'total': int}
    """
    logger.info("DART corpCode.xml 전체 다운로드 중...")
    zip_bytes = dart_get_binary("corpCode.xml", {})

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        xml_bytes = zf.read("CORPCODE.xml")

    root = etree.fromstring(xml_bytes)

    # stock_code(6자리) → corp_code(8자리) 매핑 (상장사만)
    stock_to_corp: dict[str, tuple[str, str]] = {}  # ticker → (corp_code, corp_name)
    for item in root.findall(".//list"):
        stock_code = (item.findtext("stock_code") or "").strip()
        corp_code = (item.findtext("corp_code") or "").strip()
        corp_name = (item.findtext("corp_name") or "").strip()
        if stock_code and corp_code:
            stock_to_corp[stock_code] = (corp_code, corp_name)

    logger.info(f"DART 전체 기업 수: {len(stock_to_corp):,} (상장사)")

    # top50.csv 읽기
    rows: list[dict] = []
    with open(_TOP50_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    matched = 0
    unmatched: list[str] = []
    for row in rows:
        ticker = row.get("ticker", "").strip()
        if not ticker:
            continue
        mapping = stock_to_corp.get(ticker)
        if mapping:
            row["corp_code"] = mapping[0]
            matched += 1
        else:
            unmatched.append(f"{ticker} ({row.get('corp_name')})")

    # top50.csv 저장
    with open(_TOP50_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # CompanyNode UPSERT
    session = get_local_session()
    try:
        for row in rows:
            corp_code = row.get("corp_code", "").strip()
            ticker = row.get("ticker", "").strip()
            if not corp_code or not ticker:
                continue
            existing = session.query(CompanyNode).filter_by(corp_code=corp_code).first()
            market_cap = float(row.get("market_cap", 0) or 0)
            sector = row.get("sector") or None
            group_name = row.get("group_name") or None
            corp_name = row.get("corp_name")
            if existing:
                existing.corp_name = corp_name
                existing.ticker = ticker
                existing.market_cap = market_cap
                existing.sector = sector
                existing.group_name = group_name
                existing.is_target = True
            else:
                session.add(
                    CompanyNode(
                        corp_code=corp_code,
                        corp_name=corp_name,
                        ticker=ticker,
                        market_cap=market_cap,
                        sector=sector,
                        group_name=group_name,
                        is_target=True,
                    )
                )
        session.commit()
    finally:
        session.close()

    result = {"matched": matched, "unmatched_tickers": unmatched, "total": len(rows)}
    logger.info(f"corp_code 매핑: {matched}/{len(rows)}개 완료")
    if unmatched:
        logger.warning(f"매칭 실패 ({len(unmatched)}): {unmatched}")
    return result


# ============================================================
# 2a.2 — fetch_shareholders (hyslrSttus)
# ============================================================


def fetch_shareholders(
    corp_code: str, bsns_year: int, reprt_code: str = "11011"
) -> list[dict]:
    """hyslrSttus → 최대주주 및 특수관계인 현황.

    Returns: [{nm, relate, stock_knd, ratio, ...}, ...]
    - status='013' 데이터 없음 → 빈 리스트
    - status='900' 원본 공시 없음 → 빈 리스트
    - status='800' 인증 실패 → DartError raise (재시도 안 함)
    """
    data = dart_get(
        ENDPOINT_SHAREHOLDERS,
        {"corp_code": corp_code, "bsns_year": str(bsns_year), "reprt_code": reprt_code},
    )
    status = data.get("status")
    if status in (DART_STATUS_NO_DATA, DART_STATUS_ORIGIN_MISSING):
        return []
    if status != DART_STATUS_OK:
        logger.warning(
            f"hyslrSttus status={status} message={data.get('message')} corp={corp_code}"
        )
        return []
    return data.get("list", []) or []


# ============================================================
# 2a.3 — fetch_investments (otrCprInvstmntSttus)
# ============================================================


def fetch_investments(
    corp_code: str, bsns_year: int, reprt_code: str = "11011"
) -> list[dict]:
    """otrCprInvstmntSttus → 타법인 출자현황.

    Returns: [{inv_prm, ratio, invstmnt_purps, ...}, ...]
    """
    data = dart_get(
        ENDPOINT_INVESTMENTS,
        {"corp_code": corp_code, "bsns_year": str(bsns_year), "reprt_code": reprt_code},
    )
    status = data.get("status")
    if status in (DART_STATUS_NO_DATA, DART_STATUS_ORIGIN_MISSING):
        return []
    if status != DART_STATUS_OK:
        logger.warning(f"otrCprInvstmntSttus status={status} corp={corp_code}")
        return []
    return data.get("list", []) or []


# ============================================================
# 2a.4 — collect
# ============================================================


def _parse_ratio(raw: str | None) -> float | None:
    """'12.34' / '12.34%' / '1,234.56' 등 → float."""
    if not raw:
        return None
    s = str(raw).strip().replace(",", "").replace("%", "")
    if not s or s in ("-",):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _load_top50() -> list[dict]:
    with open(_TOP50_CSV, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def collect(corp: str | None = None, bsns_year: int = 2024) -> dict:
    """DART 2개 엔드포인트 호출 → RelationRaw INSERT.

    Idempotent: 동일 (corp, bsns_year, source_type) 기존 레코드 삭제 후 재생성.

    Args:
        corp: None이면 top50 전체, 'ticker' 주면 해당 1개만 수집
        bsns_year: 사업연도

    Returns: {'shareholders_rows': int, 'investments_rows': int, 'errors': [...]}
    """
    top50 = _load_top50()
    if corp:
        top50 = [r for r in top50 if r.get("ticker") == corp]
        if not top50:
            raise ValueError(f"corp (ticker) '{corp}' not found in top50.csv")

    session = get_local_session()
    sh_rows = 0
    inv_rows = 0
    errors: list[str] = []

    try:
        # Idempotency: 기존 DART ingest 레코드 삭제 후 재생성
        # (삼성전자 단건 수집도 전체 bsns_year 범위의 hyslrSttus·otrCprInvstmntSttus 초기화)
        corp_names = [r.get("corp_name") for r in top50]
        session.query(RelationRaw).filter(
            RelationRaw.source_type.in_(["hyslrSttus", "otrCprInvstmntSttus"]),
            RelationRaw.bsns_year == bsns_year,
            (
                RelationRaw.source_name.in_(corp_names)
                | RelationRaw.target_name.in_(corp_names)
            ),
        ).delete(synchronize_session=False)
        for row in top50:
            ticker = row.get("ticker", "").strip()
            corp_code = row.get("corp_code", "").strip()
            corp_name = row.get("corp_name", "").strip()
            if not corp_code:
                errors.append(f"{ticker}: corp_code 없음 (map-corp-codes 먼저 실행)")
                continue

            # --- hyslrSttus (들어오는 지분) ---
            try:
                shareholders = fetch_shareholders(corp_code, bsns_year)
                for item in shareholders:
                    ratio = _parse_ratio(item.get("trmend_posesn_stock_qota_rt"))
                    rec = RelationRaw(
                        source_name=(item.get("nm") or "").strip(),
                        target_name=corp_name,
                        relate=(item.get("relate") or "").strip() or None,
                        ratio=ratio,
                        stock_knd=(item.get("stock_knd") or "").strip() or None,
                        source_type="hyslrSttus",
                        bsns_year=bsns_year,
                        raw_response=json.dumps(item, ensure_ascii=False),
                    )
                    session.add(rec)
                    sh_rows += 1
                logger.info(f"[hyslrSttus] {ticker} {corp_name}: {len(shareholders)}건")
            except Exception as e:  # noqa: BLE001
                errors.append(f"{ticker} hyslrSttus: {e}")
                logger.error(f"{ticker} hyslrSttus 실패: {e}")

            # --- otrCprInvstmntSttus (나가는 지분) ---
            try:
                investments = fetch_investments(corp_code, bsns_year)
                for item in investments:
                    ratio = _parse_ratio(item.get("trmend_blce_qota_rt"))
                    rec = RelationRaw(
                        source_name=corp_name,
                        target_name=(item.get("inv_prm") or "").strip(),
                        relate=None,
                        ratio=ratio,
                        stock_knd=None,
                        source_type="otrCprInvstmntSttus",
                        bsns_year=bsns_year,
                        raw_response=json.dumps(item, ensure_ascii=False),
                    )
                    session.add(rec)
                    inv_rows += 1
                logger.info(
                    f"[otrCprInvstmntSttus] {ticker} {corp_name}: {len(investments)}건"
                )
            except Exception as e:  # noqa: BLE001
                errors.append(f"{ticker} otrCprInvstmntSttus: {e}")
                logger.error(f"{ticker} otrCprInvstmntSttus 실패: {e}")

        session.commit()
    finally:
        session.close()

    result = {
        "shareholders_rows": sh_rows,
        "investments_rows": inv_rows,
        "errors": errors,
    }
    logger.info(
        f"DART 수집 완료: 최대주주 {sh_rows}건 + 타법인출자 {inv_rows}건. errors={len(errors)}"
    )
    return result
