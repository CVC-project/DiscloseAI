"""collector.py — DART 사업보고서 5개년 원문 수집.

corps.csv 순회 → dart.list(정기공시)에서 최신 5개 사업보고서 → dart.document로 원문 → raw_cache/.
idempotent(이미 있으면 스킵). 정정공시 stub 폴백: final=False 로 원본까지 조회 →
연도별 최신 rcept부터 유효성 검사(sub_docs<30 또는 '사업의 내용' 없으면 스텁) → 첫 유효본(첨부정정이면 원본) 채택.

⚠️ disclosure/relation의 DART 패턴을 복제(import 금지). 데이터 생산 모듈 경계.
실행: python -m modules.report.collector   (DART_API_KEY 필요)
"""

from __future__ import annotations

import os
import re
from datetime import datetime

from .db import get_local_session, init_local_db
from .models import PipelineState, ReportRaw

_HERE = os.path.dirname(__file__)
CORPS_CSV = os.path.join(_HERE, "data", "corps.csv")
RAW_CACHE = os.path.join(_HERE, "data", "raw_cache")

REPORT_YEARS = 5  # 최신 5개 사업연도
_MIN_SUBDOCS = 30  # 정정 stub 판정 임계 (부록 B-2)


def _dart_client():
    """OpenDartReader 클라이언트. 키 없으면 None (호출측이 스킵)."""
    key = os.getenv("DART_API_KEY", "")
    if not key:
        try:
            from shared.config import DART_API_KEY

            key = DART_API_KEY
        except Exception:
            key = ""
    if not key:
        return None
    import OpenDartReader as odr  # 지연 import

    return odr(key)


def load_corps() -> list[dict]:
    import csv

    with open(CORPS_CSV, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _is_valid_business_report(dart, rcept_no: str) -> bool:
    """정정 stub 판정: sub_docs 충분 + '사업의 내용' 존재 (부록 B-2)."""
    try:
        subs = dart.sub_docs(rcept_no)
    except Exception:
        return True  # 판정 불가 시 통과(다음 단계에서 걸러짐)
    if subs is None or len(subs) < _MIN_SUBDOCS:
        return False
    titles = " ".join(str(t) for t in subs.get("title", []))
    return "사업의 내용" in titles


def _fetch_annual_reports(dart, ticker: str) -> list[dict]:
    """최신 5개 사업연도의 사업보고서 rcept 목록.

    ⚠️ final=False 로 정정에 가려진 원본까지 조회한 뒤, **연도별로 최신 rcept부터**
    유효성(_is_valid_business_report)을 검사해 첫 유효본을 채택한다. 리스트 반환 순서에
    의존하지 않는다.
    - [기재정정](본문 정정): 최신본이 유효 → 정정 반영본 채택.
    - [첨부정정](첨부만 정정, 본문은 스텁): 최신본이 스텁 → 같은 연도 원본으로 폴백.
      예: 012450 FY2025 [첨부정정](20260319000633, 영업보고서만 정정) → 원본(20260316001112) 채택.
      final=True(기본)면 원본이 리스트에서 가려져 그 연도가 통째로 누락됐다.
    """
    this_year = datetime.now().year
    start = f"{this_year - REPORT_YEARS - 1}-01-01"
    end = f"{this_year}-12-31"
    # final=False: 정정에 가려진 원본까지 노출 (첨부정정 폴백에 필수)
    df = dart.list(ticker, start=start, end=end, kind="A", final=False)  # A = 정기공시
    if df is None or len(df) == 0:
        return []
    # 사업보고서만 (반기·분기보고서 제외)
    biz = df[df["report_nm"].astype(str).str.contains("사업보고서", na=False)]
    # 연도별 후보 수집 (보고서명에서 사업연도 추출: "사업보고서 (2025.12)")
    by_fy: dict[int, list[tuple[str, str]]] = {}
    for _, row in biz.iterrows():
        rcept_no = str(row.get("rcept_no", ""))
        report_nm = str(row.get("report_nm", ""))
        m = re.search(r"\((\d{4})\.\d{2}\)", report_nm)
        if not m:
            continue
        by_fy.setdefault(int(m.group(1)), []).append((rcept_no, report_nm))
    # 최신 연도부터, 연도 안에서는 최신 rcept부터 첫 유효본 채택 (스텁이면 원본으로 폴백)
    picked: dict[int, dict] = {}
    for fy in sorted(by_fy, reverse=True):
        if len(picked) >= REPORT_YEARS:
            break
        for rcept_no, report_nm in sorted(by_fy[fy], key=lambda x: x[0], reverse=True):
            if _is_valid_business_report(dart, rcept_no):
                picked[fy] = {
                    "rcept_no": rcept_no,
                    "fiscal_year": fy,
                    "report_nm": report_nm,
                }
                break  # 이 연도 확정
    return sorted(picked.values(), key=lambda r: -r["fiscal_year"])


def _save_document(dart, ticker: str, rcept_no: str) -> str | None:
    """dart.document 원문을 raw_cache/<ticker>/<rcept_no>.xml 로 저장. 상대경로 반환."""
    outdir = os.path.join(RAW_CACHE, ticker)
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, f"{rcept_no}.xml")
    rel = os.path.relpath(path, _HERE)
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        return rel  # idempotent
    try:
        doc = dart.document(rcept_no)  # 원문 XML/HTML 문자열
    except Exception:
        return None
    if not doc:
        return None
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)
    return rel


def collect(tickers: list[str] | None = None) -> None:
    init_local_db()
    dart = _dart_client()
    if dart is None:
        print("⚠ DART_API_KEY 없음 — 수집 스킵. 키 설정 후 재실행.")
        return
    corps = load_corps()
    if tickers:
        corps = [c for c in corps if c["ticker"] in set(tickers)]
    sess = get_local_session()
    for c in corps:
        ticker, corp_code8, corp_name = c["ticker"], c["corp_code"], c["corp_name"]
        try:
            reports = _fetch_annual_reports(dart, ticker)
        except Exception as e:
            print(f"[{ticker}] list 실패: {e}")
            continue
        if not reports:
            print(f"[{ticker}] {corp_name}: 사업보고서 없음")
            continue
        for r in reports:
            rcept_no, fy = r["rcept_no"], r["fiscal_year"]
            rel = _save_document(dart, ticker, rcept_no)
            exists = sess.get(ReportRaw, rcept_no)
            if not exists:
                sess.add(
                    ReportRaw(
                        rcept_no=rcept_no,
                        ticker=ticker,
                        corp_code8=corp_code8,
                        corp_name=corp_name,
                        fiscal_year=fy,
                        report_nm=r["report_nm"],
                        raw_path=rel,
                    )
                )
            _mark(
                sess, rcept_no, ticker, "collect", "COLLECTED", "OK" if rel else "FAIL"
            )
        sess.commit()
        print(f"[{ticker}] {corp_name}: {len(reports)}개년 수집 완료")
    sess.close()


def _mark(sess, rcept_no, ticker, target, stage, status, error=None):
    st = (
        sess.query(PipelineState)
        .filter_by(rcept_no=rcept_no, target=target)
        .one_or_none()
    )
    if st is None:
        st = PipelineState(rcept_no=rcept_no, ticker=ticker, target=target)
        sess.add(st)
    st.stage, st.status, st.error = stage, status, error
    st.attempts = (st.attempts or 0) + 1


if __name__ == "__main__":
    collect()
