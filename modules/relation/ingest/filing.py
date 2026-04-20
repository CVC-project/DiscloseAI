"""DART 사업보고서 주석 HTML 파싱 — 공정위 미포함 기업 한정.

대상 선정: CompanyNode에서 group_name IS NULL인 기업 (실전 1~3개 예상).
파싱 목표: "특수관계자" 섹션의 기업명·관계 유형(지배/종속/관계/공동) 테이블.
결과: source_type="dart_filing" 엣지로 RelationRaw 저장.

best-effort 전략: 파싱 실패해도 예외 없이 다음 기업으로 진행.
상세는 modules/relation/ingest/CLAUDE.md 참조.
"""

from __future__ import annotations

import io
import json
import logging
import re
import zipfile
from pathlib import Path

from bs4 import BeautifulSoup

from modules.relation.common.names import build_ticker_map, normalize_company_name
from modules.relation.ingest._http import dart_get, dart_get_binary
from modules.relation.storage.db import get_local_session
from modules.relation.storage.models import CompanyNode, RelationRaw

_TOP50_CSV = Path(__file__).parent.parent / "data" / "top50.csv"

logger = logging.getLogger(__name__)

# relation_kind 정규화 매핑 (공정위·IFRS 용어 → 4단계 분류)
_RELATION_KIND_MAP = {
    "지배": "지배",
    "지배기업": "지배",
    "지배회사": "지배",
    "모회사": "지배",
    "종속": "종속",
    "종속기업": "종속",
    "자회사": "종속",
    "종속회사": "종속",
    "관계": "관계",
    "관계기업": "관계",
    "관계회사": "관계",
    "공동": "공동",
    "공동기업": "공동",
    "조인트벤처": "공동",
}


# ============================================================
# 2c.1 — identify_missing_groups
# ============================================================


def identify_missing_groups() -> list[dict]:
    """CompanyNode에서 group_name IS NULL인 기업 반환.

    Returns: [{'corp_code', 'corp_name', 'ticker'}, ...]
    """
    session = get_local_session()
    try:
        rows = session.query(CompanyNode).filter(CompanyNode.group_name.is_(None)).all()
        return [
            {"corp_code": r.corp_code, "corp_name": r.corp_name, "ticker": r.ticker}
            for r in rows
        ]
    finally:
        session.close()


# ============================================================
# 2c.2 — get_latest_rcept_no
# ============================================================


def get_latest_rcept_no(corp_code: str, bsns_year: int = 2024) -> str | None:
    """해당 사업연도의 최신 사업보고서 접수번호.

    DART list.json: pblntf_detail_ty='A001' (사업보고서), last_reprt_at='Y'.
    """
    data = dart_get(
        "list.json",
        {
            "corp_code": corp_code,
            "bgn_de": f"{bsns_year}0101",
            "end_de": f"{bsns_year + 1}0630",  # 사업보고서는 3월말 제출이라 다음해 초까지 범위
            "pblntf_detail_ty": "A001",
            "last_reprt_at": "Y",
            "page_count": 10,
        },
    )
    if data.get("status") != "000":
        return None
    items = data.get("list", []) or []
    if not items:
        return None
    # 최근 접수 순 (rcept_dt 내림차순)
    items.sort(key=lambda x: x.get("rcept_dt", ""), reverse=True)
    return items[0].get("rcept_no")


# ============================================================
# 2c.3 — download_filing + extract
# ============================================================


def download_filing(rcept_no: str) -> bytes:
    """DART document.json → ZIP 바이너리."""
    return dart_get_binary("document.xml", {"rcept_no": rcept_no})


def extract_related_party_html(zip_bytes: bytes) -> str | None:
    """ZIP 내부 XML에서 '특수관계자' 섹션 HTML 추출.

    전략:
      1. ZIP 내부 모든 xml/html 파일 스캔
      2. '특수관계자' 문자열을 포함한 파일에서 해당 섹션 전후를 반환
      3. 실패 시 None
    """
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            for name in zf.namelist():
                if not name.lower().endswith((".xml", ".html", ".htm")):
                    continue
                try:
                    content = zf.read(name).decode("utf-8", errors="replace")
                except Exception:  # noqa: BLE001
                    continue
                if "특수관계자" not in content:
                    continue
                # '특수관계자' 첫 출현 위치부터 다음 주요 섹션 경계까지 추출
                idx = content.find("특수관계자")
                # 약 30KB 범위 자르기 (관계자 섹션 크기)
                end = min(idx + 50000, len(content))
                return content[idx:end]
    except zipfile.BadZipFile:
        logger.warning("ZIP 손상 — 파싱 불가")
    return None


# ============================================================
# 2c.4 — parse_related_party_section
# ============================================================


def parse_related_party_section(html_fragment: str) -> list[dict]:
    """HTML에서 특수관계자 목록 [{'name', 'relation_kind'}, ...] 추출.

    best-effort: 회사별 포맷이 달라 부분적으로만 성공할 수 있음.
    """
    results: list[dict] = []
    soup = BeautifulSoup(html_fragment, "lxml")

    # 테이블 기반 파싱 — 특수관계자 목록 테이블 탐색
    for table in soup.find_all("table"):
        text = table.get_text(" ", strip=True)
        # 테이블에 관계 유형 키워드가 포함되어야
        if not any(
            kw in text
            for kw in ("지배기업", "종속기업", "관계기업", "공동기업", "특수관계")
        ):
            continue
        for tr in table.find_all("tr"):
            cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
            if len(cells) < 2:
                continue
            # 셀 중 하나가 관계 유형, 다른 하나가 기업명
            kind_cell = next((c for c in cells if _extract_relation_kind(c)), None)
            if not kind_cell:
                continue
            relation_kind = _extract_relation_kind(kind_cell)
            # 관계 유형이 아닌 나머지 셀에서 기업명 후보 추출
            for c in cells:
                if c == kind_cell:
                    continue
                name_candidate = _clean_name(c)
                if name_candidate and 2 <= len(name_candidate) <= 40:
                    results.append(
                        {"name": name_candidate, "relation_kind": relation_kind}
                    )

    # 중복 제거
    seen = set()
    unique: list[dict] = []
    for r in results:
        key = (r["name"], r["relation_kind"])
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def _extract_relation_kind(text: str) -> str | None:
    """셀 텍스트에서 관계 유형 키워드 추출."""
    for keyword, kind in _RELATION_KIND_MAP.items():
        if keyword in text:
            return kind
    return None


def _clean_name(text: str) -> str:
    """기업명 후보 정제 — 숫자·기호 제거, 너무 긴 문장 배제."""
    # 숫자로만 된 문자열은 제외
    if re.fullmatch(r"[\d\s,.\-]+", text):
        return ""
    # 너무 긴 서술문 제외
    if len(text) > 50:
        return ""
    # 조사·종결어미가 있으면 서술문 → 제외 (기업명에는 거의 없음)
    if any(p in text for p in ("습니다", "입니다", "합니다", "됩니다", "다.")):
        return ""
    # 문장 접속 조사가 포함된 설명문 (길이 15자 이상)
    if len(text) >= 15 and any(
        p in text for p in ("에 관한", "에 대한", "에서의", "와의", "과의")
    ):
        return ""
    # 특정 헤더 용어 완전일치 제외
    for skip in ("비고", "지분율", "당기", "전기", "구분", "관계"):
        if text == skip:
            return ""
    return text.strip()


# ============================================================
# 2c.5 — collect
# ============================================================


def collect(bsns_year: int = 2024) -> dict:
    """공정위 미포함 기업 → 사업보고서 주석 파싱 → dart_filing 엣지 생성.

    Returns: {'targets': int, 'parsed': int, 'edges': int, 'failures': [...]}
    """
    targets = identify_missing_groups()
    if not targets:
        logger.info("공정위 미포함 top50 기업 없음 — filing 파싱 스킵")
        return {"targets": 0, "parsed": 0, "edges": 0, "failures": []}

    logger.info(
        f"filing 파싱 대상 {len(targets)}개: {[t['corp_name'] for t in targets]}"
    )

    ticker_map = build_ticker_map(_TOP50_CSV)

    session = get_local_session()
    parsed_count = 0
    edge_count = 0
    failures: list[str] = []

    try:
        # 기존 dart_filing 엣지 제거 후 재생성
        session.query(RelationRaw).filter_by(source_type="dart_filing").delete()

        for t in targets:
            corp_code = t["corp_code"]
            corp_name = t["corp_name"]
            ticker = t["ticker"]
            try:
                rcept = get_latest_rcept_no(corp_code, bsns_year)
                if not rcept:
                    failures.append(f"{corp_name}: 사업보고서 접수번호 없음")
                    continue

                zip_bytes = download_filing(rcept)
                html = extract_related_party_html(zip_bytes)
                if not html:
                    failures.append(f"{corp_name}: 특수관계자 섹션 없음")
                    continue

                parsed = parse_related_party_section(html)
                parsed_count += 1
                logger.info(f"{corp_name}: 파싱 {len(parsed)}건")

                for item in parsed:
                    normalized = normalize_company_name(item["name"])
                    target_ticker = ticker_map.get(normalized)
                    if not target_ticker or target_ticker == ticker:
                        continue
                    session.add(
                        RelationRaw(
                            source_name=ticker,
                            target_name=target_ticker,
                            relate=item["relation_kind"],
                            ratio=None,
                            stock_knd=None,
                            source_type="dart_filing",
                            bsns_year=bsns_year,
                            raw_response=json.dumps(item, ensure_ascii=False),
                        )
                    )
                    edge_count += 1
            except Exception as e:  # noqa: BLE001
                failures.append(f"{corp_name}: {e}")
                logger.error(f"{corp_name} 파싱 실패: {e}")

        session.commit()
    finally:
        session.close()

    result = {
        "targets": len(targets),
        "parsed": parsed_count,
        "edges": edge_count,
        "failures": failures,
    }
    logger.info(f"filing 수집 완료: {result}")
    return result
