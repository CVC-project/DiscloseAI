"""단일판매ㆍ공급계약체결 수시공시 T1 파서 (valuechain PLAN.md Phase V1).

DART 엔드포인트 조사 결과(2026-07-21, 실측):
  - 전용 구조화 API(fnlttSinglAcntAll류)는 없음 — KRX 수시공시 문서(document.xml)뿐.
  - `list.json`(corp_code 생략 시 전 상장사 대상) + `pblntf_detail_ty="I001"`(거래소 공시)로
    검색 후, `report_nm`에 "단일판매"가 포함된 건만 클라이언트에서 필터링.
    - ★2026-07-22 실측 추가: `list.json`은 조회기간 상한이 있다(1년 범위로 호출 시
      `status="100"`(파라미터 오류) 즉시 반환 — 문서화 안 된 제약을 에러로 발견). 분기
      단위(3개월) 호출은 정상 동작 확인(2024 Q1 I001 19,434건/195페이지). `discover_filings()`가
      내부적으로 ≤89일 구간으로 자동 분할해 호출자는 이 제약을 몰라도 됨.
    - 실측: report_nm 정확 표기는 "단일판매ㆍ공급계약체결"(가운뎃점이 U+318D 한글
      아래아, 일반 U+00B7 middle dot 아님) — "단일판매" 부분 문자열 매칭이 표기 변형에
      안전(별표·기재정정 접두어와 무관하게 항상 포함).
    - "[기재정정]" 접두어 건은 스킵(원본 rcept_no 참조 파싱이 필요한 M3 정정공시 처리는
      후속 과제 — 정직하게 기록, universe/PLAN.md §6.1 드라이버 절차 준수).
  - `document.xml`(ZIP) 응답은 **UTF-8**로 디코딩해야 함 — 응답 meta 태그가
    `charset=euc-kr`이라 주장하지만 실제 바이트는 UTF-8(euc-kr/cp949로 디코드 시
    "illegal multibyte sequence" 즉시 실패로 확인).
  - 문서는 고정 라벨의 HTML 표(`<td>라벨</td><td>값</td>` 쌍) — 단, 회사·연도별로
    **행 번호(1./2./3. …)와 rowspan 그룹 구성이 다르다**(실측: 그린광학 8건 vs 한신공영
    7건 항목 수 차이) — 위치 기반이 아니라 **라벨 문자열 포함 매칭**으로 값을 찾는다.
  - "계약상대방"은 세 갈래로 관측됨: ① 실제 상장사명(예: "스튜디오에스 주식회사") ②
    업종 설명 등 비고유명사(예: "방산 솔루션 공급 업체") ③ "-"(미기재). ②③은
    entity linking이 자연히 실패해 LinkFailQueue에 쌓이거나(②) 애초에 정규화 결과가
    빈 문자열이라 스킵된다(③, resolve_corp가 빈 값 방어). **비공개 상대방이 다수**임은
    valuechain/PLAN.md §7 리스크("공급계약 공시 상대방 '비공개' 다수")로 이미 예견됨 —
    현재 스키마(`ValueChainEdge.dst_corp` NOT NULL)는 "익명 엣지"를 표현할 수 없어
    entity linking에 실패한 건은 **엣지를 만들지 않고 카운트만** 한다(스키마 확장은
    후속 결정 — dst_corp nullable 여부는 다른 T2 파서 요구사항과 함께 판단해야 할
    구조적 변경이라 이 세션에서 단독 결정하지 않음).
  - 계약금액은 "(원)" 단위로 이미 절대 KRW — 백만원 등 배율 변환 불요(related_party.py와
    다름, 표마다 단위 표기가 달라 혼동 주의).
  - disclosing 회사는 KRX 공시규정상 "판매자/공급자" 측(매출액 대비 %를 필터 기준으로
    삼는 규정 자체가 이를 전제) — 방향은 **always customer**(src=공시회사, dst=상대방).
"""

from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup

from modules.relation.ingest._http import dart_get, dart_get_binary
from modules.relation.storage.db import get_local_session
from modules.relation.storage.models import ValueChainEdge
from modules.relation.valuechain.extract.linking import build_name_to_corp_map, resolve_corp

logger = logging.getLogger(__name__)

_PBLNTF_DETAIL_TY = "I001"  # 거래소 공시(수시공시)
_REPORT_NM_MARKER = "단일판매"
_CORRECTION_MARKER = "기재정정"

_AMOUNT_LABELS = ("계약금액 총액", "확정 계약금액")
_COUNTERPARTY_LABEL = "계약상대방"
_CONTRACT_DATE_LABEL = "계약(수주)일자"


_MAX_WINDOW_DAYS = 89  # DART list.json 조회기간 상한 실측 ~3개월 — 안전 마진으로 89일 사용
_STATUS_NO_DATA = "013"
_STATUS_OK = "000"


def _split_date_windows(bgn_de: str, end_de: str, max_days: int = _MAX_WINDOW_DAYS) -> list[tuple[str, str]]:
    """"YYYYMMDD" 범위 → ≤max_days 연속 구간 리스트 (DART 조회기간 상한 준수)."""
    from datetime import date, timedelta

    start = date(int(bgn_de[:4]), int(bgn_de[4:6]), int(bgn_de[6:8]))
    end = date(int(end_de[:4]), int(end_de[4:6]), int(end_de[6:8]))
    if start > end:
        return []

    windows: list[tuple[str, str]] = []
    cur = start
    step = timedelta(days=max_days)
    while cur <= end:
        window_end = min(cur + step, end)
        windows.append((cur.strftime("%Y%m%d"), window_end.strftime("%Y%m%d")))
        cur = window_end + timedelta(days=1)
    return windows


def discover_filings(bgn_de: str, end_de: str, page_count: int = 100) -> list[dict]:
    """list.json 전 상장사 검색 → "단일판매ㆍ공급계약체결" 원본(정정 제외) 건 목록.

    bgn_de/end_de: "YYYYMMDD". DART list.json은 조회기간 상한(실측 ~3개월, 초과 시
    status="100" 파라미터 오류)이 있어 내부적으로 ≤89일 구간으로 쪼개 순차 조회한다 —
    호출자가 이 제약을 알 필요 없음. 반환: [{"rcept_no","corp_code","corp_name","rcept_dt"}, ...]
    """
    results: list[dict] = []
    for window_bgn, window_end in _split_date_windows(bgn_de, end_de):
        page_no = 1
        while True:
            data = dart_get(
                "list.json",
                {
                    "bgn_de": window_bgn,
                    "end_de": window_end,
                    "pblntf_detail_ty": _PBLNTF_DETAIL_TY,
                    "page_count": page_count,
                    "page_no": page_no,
                },
            )
            status = data.get("status")
            if status == _STATUS_NO_DATA:
                break  # 이 구간엔 해당 유형 공시 없음 — 정상, 다음 구간으로
            if status != _STATUS_OK:
                raise RuntimeError(
                    f"DART list.json 오류(구간 {window_bgn}~{window_end}, "
                    f"page {page_no}): status={status} message={data.get('message')}"
                )
            items = data.get("list", []) or []
            for item in items:
                report_nm = item.get("report_nm", "")
                if _REPORT_NM_MARKER not in report_nm or _CORRECTION_MARKER in report_nm:
                    continue
                results.append(
                    {
                        "rcept_no": item["rcept_no"],
                        "corp_code": item["corp_code"],
                        "corp_name": item.get("corp_name"),
                        "rcept_dt": item.get("rcept_dt"),
                    }
                )
            total_page = int(data.get("total_page", 1) or 1)
            if page_no >= total_page:
                break
            page_no += 1
    return results


def fetch_filing_html(rcept_no: str) -> str:
    """document.xml(ZIP) 다운로드 → 단일 XML 파일 텍스트.

    ★2026-07-22 실측 추가: 인코딩은 회사·연도에 따라 다르다 — 2026년 표본(그린광학·
    아티스트스튜디오)은 UTF-8이었으나, 2020~2021년치 다수는 실제로 **cp949**(meta
    태그의 "euc-kr" 주장과도 다름 — 2026년 표본처럼 meta 태그를 신뢰할 수 없는 건
    같지만, 실제 바이트가 어느 인코딩인지는 그때그때 다름). UTF-8 우선 시도 후
    cp949로 폴백 — 배치 실행(2020~2026 전량) 중 2020년 1,912건 중 6건, 2021년
    2,216건 전량이 이 인코딩 문제로 fetch 실패했던 것을 발견 후 수정.
    """
    import io
    import zipfile

    content = dart_get_binary("document.xml", {"rcept_no": rcept_no})
    z = zipfile.ZipFile(io.BytesIO(content))
    raw = z.read(z.namelist()[0])
    return _decode_document_bytes(raw)


def _decode_document_bytes(raw: bytes) -> str:
    """document.xml 원본 바이트 → 텍스트. UTF-8 우선, 실패 시 cp949 폴백."""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp949")


def _row_cells(tr) -> list[str]:
    return [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]


def _find_value(rows: list[list[str]], label: str) -> str | None:
    """라벨 문자열이 마지막 칸을 제외한 셀 중 하나에 포함된 첫 행 → 마지막 칸 값."""
    for cells in rows:
        if len(cells) < 2:
            continue
        if any(label in c for c in cells[:-1]):
            return cells[-1].strip()
    return None


def _parse_amount(value: str | None) -> float | None:
    if not value:
        return None
    s = value.strip().replace(",", "")
    if not s or s in ("-", "−", "―"):
        return None
    try:
        amount = float(s)
    except ValueError:
        return None
    return amount if amount != 0 else None


_YEAR_RE = re.compile(r"(\d{4})-\d{2}-\d{2}")


def parse_filing_html(html: str, fallback_year: int) -> dict:
    """단일판매ㆍ공급계약체결 문서 HTML → {counterparty, amount, as_of}.

    fallback_year: 계약(수주)일자를 못 찾으면 rcept_no 접수연도로 대체.
    """
    soup = BeautifulSoup(html, "lxml")
    rows = [_row_cells(tr) for tr in soup.find_all("tr")]
    rows = [r for r in rows if r]

    amount = None
    for label in _AMOUNT_LABELS:
        amount = _parse_amount(_find_value(rows, label))
        if amount is not None:
            break

    counterparty = _find_value(rows, _COUNTERPARTY_LABEL)

    date_value = _find_value(rows, _CONTRACT_DATE_LABEL)
    as_of = fallback_year
    if date_value:
        m = _YEAR_RE.search(date_value)
        if m:
            as_of = int(m.group(1))

    return {"counterparty": counterparty, "amount": amount, "as_of": as_of}


def _upsert_edge(session, **fields) -> None:
    """UNIQUE(src_corp, dst_corp, edge_type, as_of, rcept_no) upsert (D12 멱등)."""
    key = {
        "src_corp": fields["src_corp"],
        "dst_corp": fields["dst_corp"],
        "edge_type": fields["edge_type"],
        "as_of": fields["as_of"],
        "rcept_no": fields["rcept_no"],
    }
    existing = session.query(ValueChainEdge).filter_by(**key).one_or_none()
    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
        existing.status = "active"
    else:
        session.add(ValueChainEdge(**fields, status="active"))


def apply(session=None, filings: list[dict] | None = None) -> dict:
    """단일판매ㆍ공급계약체결 공시 전량 처리 → ValueChainEdge(T1) upsert.

    session: 주입 시 그 세션 사용(테스트용 — 닫지 않음, 커밋은 호출). None이면 로컬 relation.db.
    filings: 주입 시 [{"rcept_no","corp_code","corp_name","rcept_dt","html"}, ...] 사용(테스트용 —
             실 DART API 호출 회피). None이면 이 함수 자체는 discover하지 않는다 — 호출자가
             discover_filings()로 얻은 목록에 fetch_filing_html()로 html을 채워 넘겨야 한다
             (discover와 fetch를 분리해 대량 호출 시 진행상황 로깅/재시도를 호출자가 제어).

    Returns: {'filings_scanned', 'edges_kept', 'link_failed', 'no_counterparty'}
    """
    owns_session = session is None
    if owns_session:
        session = get_local_session()

    if filings is None:
        raise ValueError(
            "filings를 명시적으로 넘겨야 함 — discover_filings()+fetch_filing_html()로 준비 후 호출"
        )

    counters = {
        "filings_scanned": 0,
        "edges_kept": 0,
        "link_failed": 0,
        "no_counterparty": 0,
    }
    try:
        name_to_corp = build_name_to_corp_map(session)

        for filing in filings:
            counters["filings_scanned"] += 1
            rcept_no = filing["rcept_no"]
            self_corp = filing["corp_code"]
            fallback_year = int(filing["rcept_dt"][:4]) if filing.get("rcept_dt") else 0

            parsed = parse_filing_html(filing["html"], fallback_year)
            if not parsed["counterparty"]:
                counters["no_counterparty"] += 1
                continue

            corp_code = resolve_corp(
                parsed["counterparty"], name_to_corp, session, sample_chunk_id=rcept_no
            )
            if not corp_code:
                counters["link_failed"] += 1
                continue
            if corp_code == self_corp:
                continue

            _upsert_edge(
                session,
                src_corp=self_corp,
                dst_corp=corp_code,
                edge_type="customer",
                tier="T1",
                source_kind="supply_contract",
                rcept_no=rcept_no,
                provenance=f"단일판매ㆍ공급계약체결 · {parsed['counterparty']}",
                amount=parsed["amount"],
                as_of=parsed["as_of"],
            )
            counters["edges_kept"] += 1
        session.commit()
    finally:
        if owns_session:
            session.close()

    logger.info(f"supply_contract.apply 결과: {counters}")
    return counters


if __name__ == "__main__":
    import json
    from datetime import UTC, datetime

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    end = datetime.now(UTC).strftime("%Y%m%d")
    bgn = (datetime.now(UTC).replace(year=datetime.now(UTC).year - 1)).strftime("%Y%m%d")
    found = discover_filings(bgn, end)
    for f in found:
        f["html"] = fetch_filing_html(f["rcept_no"])
    print(json.dumps(apply(filings=found), ensure_ascii=False, indent=2))
