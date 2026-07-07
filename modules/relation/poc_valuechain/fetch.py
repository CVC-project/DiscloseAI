"""밸류체인 PoC — 사업보고서 'II. 사업의 내용' 섹션 수집 (3개 섹터 × 5사).

목적: 기업→품목→기업 매칭(품목 매개 그래프)의 실현 가능성 검증용 원천 텍스트 확보.
실행: python modules/relation/poc_valuechain/fetch.py  (리포 루트에서)
출력:
  data/{sector}_{ticker}_{name}.txt  — '사업의 내용' 평문 (표 셀은 ' | ' 구분)
  data/_meta.json                    — rcept_no·보고서명·섹션 크기 기록

PoC 한정 — 본 파이프라인(ingest/)에 통합하지 않음.
"""

from __future__ import annotations

import html
import io
import json
import re
import sys
import time
import zipfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT))

from modules.relation.ingest._http import dart_get, dart_get_binary  # noqa: E402

DATA_DIR = Path(__file__).parent / "data"

# (섹터, ticker 6자리, 표기명)
FIRMS = [
    ("semi", "005930", "삼성전자"),
    ("semi", "000660", "SK하이닉스"),
    ("semi", "005290", "동진쎄미켐"),
    ("semi", "357780", "솔브레인"),
    ("semi", "240810", "원익IPS"),
    ("battery", "373220", "LG에너지솔루션"),
    ("battery", "006400", "삼성SDI"),
    ("battery", "247540", "에코프로비엠"),
    ("battery", "003670", "포스코퓨처엠"),
    ("battery", "066970", "엘앤에프"),
    ("auto", "005380", "현대자동차"),
    ("auto", "000270", "기아"),
    ("auto", "012330", "현대모비스"),
    ("auto", "018880", "한온시스템"),
    ("auto", "204320", "HL만도"),
]


def build_corp_map() -> dict[str, str]:
    """corpCode.xml 다운로드(1회) → {ticker(6): corp_code(8)}. PoC 폴더에 캐시."""
    cache = DATA_DIR / "CORPCODE.xml"
    if not cache.exists():
        print("corpCode.xml 다운로드 중...")
        zb = dart_get_binary("corpCode.xml", {})
        with zipfile.ZipFile(io.BytesIO(zb)) as zf:
            cache.write_bytes(zf.read("CORPCODE.xml"))
    import xml.etree.ElementTree as ET

    mapping: dict[str, str] = {}
    for _, elem in ET.iterparse(str(cache)):
        if elem.tag == "list":
            stock = (elem.findtext("stock_code") or "").strip()
            corp = (elem.findtext("corp_code") or "").strip()
            if len(stock) == 6 and corp:
                mapping[stock] = corp
            elem.clear()
    return mapping


def annual_rcept_candidates(corp_code: str) -> list[tuple[str, str]]:
    """사업보고서 rcept_no 후보 목록 (최신순). 원본파일 미제공(014) 폴백용 복수 반환."""
    data = dart_get(
        "list.json",
        {
            "corp_code": corp_code,
            "bgn_de": "20250101",
            "end_de": "20260610",
            "pblntf_detail_ty": "A001",
            "page_count": 20,
        },
    )
    if data.get("status") != "000":
        return []
    items = sorted(
        data.get("list") or [], key=lambda x: x.get("rcept_dt", ""), reverse=True
    )
    return [(it.get("rcept_no", ""), it.get("report_nm", "")) for it in items if it.get("rcept_no")]


def latest_annual_rcept(corp_code: str) -> tuple[str | None, str]:
    """가장 최근 사업보고서 rcept_no (하위호환용)."""
    cands = annual_rcept_candidates(corp_code)
    return cands[0] if cands else (None, "")


def decode_bytes(b: bytes) -> str:
    head = b[:300].decode("ascii", errors="ignore").lower()
    if "euc-kr" in head or "ks_c_5601" in head or "cp949" in head:
        return b.decode("cp949", errors="replace")
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b.decode("cp949", errors="replace")


def fetch_doc_text(rcept_no: str) -> str:
    """document.xml ZIP → 본문 파일 텍스트 (rcept_no 일치 파일 우선, 없으면 최대 크기)."""
    zb = dart_get_binary("document.xml", {"rcept_no": rcept_no})
    try:
        zf = zipfile.ZipFile(io.BytesIO(zb))
    except zipfile.BadZipFile:
        head = zb[:300].decode("utf-8", errors="replace")
        raise RuntimeError(f"ZIP 아님 — 응답 헤드: {head!r}")
    with zf:
        names = [
            n for n in zf.namelist() if n.lower().endswith((".xml", ".html", ".htm"))
        ]
        if not names:
            raise RuntimeError("ZIP 내 문서 파일 없음")
        # 본문 = 정확히 '{rcept_no}.xml' (첨부서류는 '{rcept_no}_00NNN.xml')
        main_name = f"{rcept_no}.xml"
        name = (
            main_name
            if main_name in names
            else max(names, key=lambda n: zf.getinfo(n).file_size)
        )
        raw = zf.read(name)
    return decode_bytes(raw)


_START_PAT = re.compile(r"<TITLE[^>]*>\s*(?:II|Ⅱ)\s*\.?\s*사업의\s*내용", re.I)
_END_PAT = re.compile(r"<TITLE[^>]*>\s*(?:III|Ⅲ)\s*\.?\s*재무에\s*관한\s*사항", re.I)


def slice_business_section(doc: str) -> str | None:
    """원시 XML에서 장 제목 TITLE 태그 기준으로 'II. 사업의 내용' 장 추출.

    상호참조 문구("'II. 사업의 내용'을 참고...")는 TITLE 태그가 아니므로 걸리지 않음.
    """
    ms = _START_PAT.search(doc)
    if not ms:
        return None
    me = _END_PAT.search(doc, ms.end())
    end = me.start() if me else len(doc)
    if end - ms.start() < 3000:
        return None
    return doc[ms.start() : end]


def to_plain(chunk: str) -> str:
    """XML/HTML 조각 → 평문. 표는 셀 ' | ', 행 개행 유지."""
    s = re.sub(r"(?is)<(?:TD|TH|TE|TU)[^>]*>", " | ", chunk)
    s = re.sub(r"(?is)</TR\s*>", "\n", s)
    s = re.sub(r"(?is)<(?:P|BR|TR|TABLE|TITLE|DIV|SECTION[^>]*)[^>]*>", "\n", s)
    s = re.sub(r"(?s)<[^>]+>", "", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t　]+", " ", s)
    s = re.sub(r" ?\n ?", "\n", s)
    s = re.sub(r"\n{2,}", "\n", s)
    return s.strip()


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    corp_map = build_corp_map()
    meta: list[dict] = []
    for sector, ticker, name in FIRMS:
        corp_code = corp_map.get(ticker)
        if not corp_code:
            print(f"[SKIP] {name}({ticker}) corp_code 없음")
            meta.append({"sector": sector, "ticker": ticker, "name": name, "error": "no corp_code"})
            continue
        cands = annual_rcept_candidates(corp_code)
        if not cands:
            print(f"[SKIP] {name} 사업보고서 미발견")
            meta.append({"sector": sector, "ticker": ticker, "name": name, "error": "no annual report"})
            continue
        rcept_no, report_nm = cands[0]
        try:
            doc = None
            for rc, rn in cands:  # 원본파일 미제공(014) 시 이전 접수본 폴백
                try:
                    doc = fetch_doc_text(rc)
                    rcept_no, report_nm = rc, rn
                    break
                except RuntimeError as fe:
                    if "014" in str(fe) or "존재하지 않" in str(fe):
                        print(f"  ({name}: {rc} 원본 미제공 → 이전 접수본 시도)")
                        continue
                    raise
            if doc is None:
                raise RuntimeError("모든 접수본의 원본파일 미제공")
            section = slice_business_section(doc)
            if not section:
                print(f"[WARN] {name} '사업의 내용' 섹션 추출 실패 (본문 {len(doc):,}자)")
                meta.append({"sector": sector, "ticker": ticker, "name": name,
                             "rcept_no": rcept_no, "report_nm": report_nm, "error": "section not found"})
                continue
            plain = to_plain(section)
            out = DATA_DIR / f"{sector}_{ticker}_{name}.txt"
            out.write_text(plain, encoding="utf-8")
            has_material = "원재료" in plain
            has_product = ("주요 제품" in plain) or ("주요 제품" in plain.replace("제품 및", "제품")) or ("매출 및 수주" in plain)
            print(
                f"[OK] {name}: {report_nm} | 섹션 {len(plain):,}자 | "
                f"원재료표={'Y' if has_material else 'N'} 제품/수주={'Y' if has_product else 'N'}"
            )
            meta.append({
                "sector": sector, "ticker": ticker, "name": name,
                "rcept_no": rcept_no, "report_nm": report_nm,
                "chars": len(plain), "has_material": has_material, "has_product": has_product,
                "file": out.name,
            })
        except Exception as e:  # noqa: BLE001
            print(f"[ERR] {name}: {e}")
            meta.append({"sector": sector, "ticker": ticker, "name": name,
                         "rcept_no": rcept_no, "error": str(e)})
        time.sleep(0.3)
    (DATA_DIR / "_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n완료 — {sum(1 for m in meta if 'file' in m)}/{len(FIRMS)}개 저장, _meta.json 기록")


if __name__ == "__main__":
    main()
