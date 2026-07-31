"""universe/sectors.py — KSIC 섹터 매핑 (U0, U-D7).

2단계:
  1. fetch_induty_codes(): DART 기업개황 company.json의 induty_code(KSIC 3자리) 전
     상장사 수집 → CompanyRegistry.ksic_code. dart_get()의 rate limit(0.2초)·
     raw_cache 캐싱을 그대로 통과 — 별도 재구현 없음.
  2. apply_sector_mapping(): ksic_sector_map.csv(이 파일과 같은 폴더, relation
     소유 데이터)로 ksic_code → sector_id 적용. 미매핑 0을 U0 게이트로 강제.

색 배정은 이 파일의 책임이 아니다(§0.5 경계) — sector_id 목록만 공급하고
SECTOR_DEF/SECTOR_PALETTE 동시 확장은 U2(integration)가 수행한다.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from modules.relation.ingest._http import DART_STATUS_OK, dart_get
from modules.relation.storage.db import get_local_session
from modules.relation.storage.models import CompanyRegistry

logger = logging.getLogger(__name__)

_MAP_CSV = Path(__file__).parent / "data" / "ksic_sector_map.csv"
# 회사 단위 예외(2026-07-31 신설). KSIC 코드 하나에 성격이 다른 회사가 섞여 있어
# 코드→섹터 1:1로는 못 가르는 소수를 교정한다. 코드 매핑은 **다수결**로 두고, 소수만
# 여기서 뒤집는다 — 실측 근거:
#   · 64992(지주회사) 74사 중 9사가 **금융지주**(KB금융·신한지주·하나금융지주 등).
#     코드는 holding으로 옮기되 이 9사는 fin에 남긴다 — 은행·보험·증권을 거느린
#     금융지주는 투자자가 금융으로 읽는다(리더 판정 2026-07-31). 옮기는 대상은
#     SK스퀘어·SK·LX홀딩스 같은 **비금융 지주회사**다.
#   · 649(기타 금융업) 20사는 창투·스팩 12 vs 지주 8. 코드는 fin으로 두고 지주 8사만 뒤집는다.
#   · 64999(그 외 기타 금융업) 3사는 핀테크·스팩과 지주가 혼재 — HS효성만 뒤집는다.
_OVERRIDE_CSV = Path(__file__).parent / "data" / "sector_overrides.csv"


def fetch_induty_codes(limit: int | None = None) -> dict:
    """전 상장사 company.json 조회 → CompanyRegistry.ksic_code 갱신.

    이미 ksic_code가 있는 행은 건너뛴다(재실행 시 미완료분만 이어서 처리 —
    다음 세션 이어달리기·중단 후 재개에 안전).

    Args:
        limit: 테스트용 처리 상한(None이면 전량).

    Returns: {'processed': int, 'ok': int, 'no_data': int, 'errors': [...]}
    """
    session = get_local_session()
    try:
        q = session.query(CompanyRegistry).filter(CompanyRegistry.ksic_code.is_(None))
        targets = q.limit(limit).all() if limit else q.all()
        total = len(targets)
        logger.info(f"induty_code 수집 대상: {total}건")

        ok = 0
        no_data = 0
        errors: list[str] = []
        for i, reg in enumerate(targets, start=1):
            try:
                data = dart_get("company.json", {"corp_code": reg.corp_code})
                if data.get("status") != DART_STATUS_OK:
                    no_data += 1
                    continue
                induty = (data.get("induty_code") or "").strip()
                if induty:
                    reg.ksic_code = induty
                    ok += 1
                else:
                    no_data += 1
            except Exception as e:  # noqa: BLE001
                errors.append(f"{reg.corp_code}({reg.name_current}): {e}")
                logger.error(f"induty_code 실패 {reg.corp_code}: {e}")

            if i % 100 == 0:
                session.commit()  # 체크포인트 — 중단 시 진행분 보존
                logger.info(f"진행: {i}/{total} (ok={ok}, no_data={no_data}, err={len(errors)})")

        session.commit()
    finally:
        session.close()

    result = {"processed": total, "ok": ok, "no_data": no_data, "errors": errors}
    logger.info(f"induty_code 수집 완료: {ok}/{total} 성공, no_data={no_data}, errors={len(errors)}")
    return result


def load_ksic_sector_map() -> dict[str, str]:
    """ksic_sector_map.csv → {ksic_code: sector_id}. 파일 없으면 빈 dict."""
    if not _MAP_CSV.exists():
        return {}
    with open(_MAP_CSV, encoding="utf-8") as f:
        return {row["ksic_code"]: row["sector_id"] for row in csv.DictReader(f)}


def load_sector_overrides() -> dict[str, str]:
    """sector_overrides.csv → {ticker: sector_id}. 파일 없으면 빈 dict."""
    if not _OVERRIDE_CSV.exists():
        return {}
    with open(_OVERRIDE_CSV, encoding="utf-8") as f:
        return {row["ticker"]: row["sector_id"] for row in csv.DictReader(f)}


def ksic_distribution() -> list[tuple[str, int]]:
    """현재 ksic_code 분포(빈도 내림차순) — 매핑 CSV 설계용 리포트."""
    session = get_local_session()
    try:
        rows = (
            session.query(CompanyRegistry.ksic_code)
            .filter(CompanyRegistry.ksic_code.isnot(None))
            .all()
        )
    finally:
        session.close()
    from collections import Counter

    counts = Counter(r[0] for r in rows)
    return sorted(counts.items(), key=lambda kv: -kv[1])


def apply_sector_mapping() -> dict:
    """ksic_sector_map.csv 적용 → CompanyRegistry.sector_id 갱신.

    Returns: {'mapped': int, 'unmapped_codes': {code: count}, 'unmapped_total': int}
    """
    mapping = load_ksic_sector_map()
    overrides = load_sector_overrides()
    session = get_local_session()
    mapped = 0
    overridden = 0
    unmapped: dict[str, int] = {}
    try:
        rows = session.query(CompanyRegistry).filter(CompanyRegistry.ksic_code.isnot(None)).all()
        for reg in rows:
            sector_id = mapping.get(reg.ksic_code)
            if sector_id:
                reg.sector_id = sector_id
                mapped += 1
            else:
                unmapped[reg.ksic_code] = unmapped.get(reg.ksic_code, 0) + 1
        # 회사 단위 예외는 **코드 매핑 뒤에** 적용한다(뒤집는 게 목적이므로 순서가 계약).
        # ksic_code가 없어 위 루프에서 빠진 회사도 교정되도록 별도 조회한다.
        for ticker, sector_id in overrides.items():
            reg = (
                session.query(CompanyRegistry)
                .filter(CompanyRegistry.ticker == ticker)
                .one_or_none()
            )
            if reg is None:
                logger.warning(f"sector_overrides: 미등재 티커 {ticker} — 건너뜀")
                continue
            reg.sector_id = sector_id
            overridden += 1
        session.commit()
    finally:
        session.close()

    result = {
        "mapped": mapped,
        "overridden": overridden,
        "unmapped_codes": unmapped,
        "unmapped_total": sum(unmapped.values()),
    }
    logger.info(
        f"섹터 매핑 적용: {mapped}건 매핑, 예외 {overridden}건, "
        f"미매핑 {result['unmapped_total']}건"
    )
    return result


if __name__ == "__main__":
    import argparse
    import json

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true", help="induty_code 수집 실행")
    parser.add_argument("--limit", type=int, default=None, help="--fetch 테스트 상한")
    parser.add_argument("--distribution", action="store_true", help="ksic_code 분포 출력")
    parser.add_argument("--apply", action="store_true", help="ksic_sector_map.csv 적용")
    args = parser.parse_args()

    if args.fetch:
        print(json.dumps(fetch_induty_codes(limit=args.limit), ensure_ascii=False, indent=2))
    if args.distribution:
        for code, count in ksic_distribution():
            print(f"{code}\t{count}")
    if args.apply:
        print(json.dumps(apply_sector_mapping(), ensure_ascii=False, indent=2))
