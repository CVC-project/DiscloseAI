"""Phase 0 — 섹터 커버리지 프로브.

업종 다양 표본의 사업보고서 전문을 DART에서 받아, '공인 채널'별 키워드 주변
텍스트 윈도우를 추출한다. named 파트너 명시도는 사람이 스니펫을 읽고 판정한다
(휴리스틱 카운트는 보조). 결과는 UTF-8 JSON으로 저장.
"""
from __future__ import annotations
import io, json, re, time, zipfile
from pathlib import Path
import requests
from shared.config import DART_API_KEY

SAMPLE = [
    ("KB금융", "00688996", "금융(은행지주)"),
    ("삼성생명", "00126256", "금융(보험)"),
    ("SK", "00181712", "지주"),
    ("NAVER", "00266961", "플랫폼"),
    ("카카오", "00258801", "플랫폼"),
    ("셀트리온", "00413046", "바이오"),
    ("SK텔레콤", "00159023", "통신"),
    ("KT&G", "00244455", "소비재/기타"),
    ("삼성전자", "00126380", "제조(대조군)"),
]
# 공인 채널 키워드 — 특수관계자(K-IFRS 1024, 보편) + arm's-length 거래처/고객
KEYWORDS = [
    "특수관계자", "주요 매출처", "매출처", "매입처", "주요 거래처",
    "주요 고객", "고객", "매출 비중", "단일판매", "공급계약", "원재료",
]

def latest_rcept(corp_code: str) -> str | None:
    r = requests.get("https://opendart.fss.or.kr/api/list.json", params={
        "crtfc_key": DART_API_KEY, "corp_code": corp_code,
        "bgn_de": "20250101", "end_de": "20251231",
        "pblntf_detail_ty": "A001", "last_reprt_at": "Y", "page_count": 20,
    }, timeout=20).json()
    items = [it for it in (r.get("list") or []) if "사업보고서" in (it.get("report_nm") or "")]
    items.sort(key=lambda x: x.get("rcept_dt", ""), reverse=True)
    return items[0]["rcept_no"] if items else None

def decode_bytes(b: bytes) -> str:
    best, best_bad = None, 1 << 30
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            s = b.decode(enc)
        except Exception:
            continue
        bad = s.count("�")
        if bad < best_bad:
            best, best_bad = s, bad
    return best if best is not None else b.decode("utf-8", errors="replace")

def clean(t: str) -> str:
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()

# 회사명 후보(named) 거친 카운트: ㈜/(주)/주식회사/Inc/Corp/Ltd/Co 패턴
NAME_PAT = re.compile(r"[가-힣A-Za-z][가-힣A-Za-z0-9·\.\s]{1,18}?(㈜|\(주\)|주식회사|Inc\.?|Corp(oration)?\.?|Ltd\.?|Co\.,?\s?Ltd)")
ANON_PAT = re.compile(r"(고객\s?[A-Z가-힣]\b|거래처\s?[A-Z가-힣]\b|○○|△△|\*\*\*|[A-Z]사\b)")

def windows(text: str, kw: str, n: int = 3, half: int = 170):
    cnt = 0
    wins = []
    named = 0
    anon = 0
    for m in re.finditer(re.escape(kw), text):
        cnt += 1
        s = max(0, m.start() - half)
        e = min(len(text), m.start() + half)
        w = clean(text[s:e])
        named += len(NAME_PAT.findall(w))
        anon += len(ANON_PAT.findall(w))
        if len(wins) < n:
            wins.append(w)
    return {"count": cnt, "named_hits": named, "anon_hits": anon, "samples": wins}

def main():
    report = {}
    for name, corp, sector in SAMPLE:
        try:
            rcept = latest_rcept(corp)
            if not rcept:
                report[name] = {"sector": sector, "error": "no 사업보고서 rcept"}
                print(name, "NO_RCEPT")
                continue
            zb = requests.get("https://opendart.fss.or.kr/api/document.xml", params={
                "crtfc_key": DART_API_KEY, "rcept_no": rcept}, timeout=90).content
            zf = zipfile.ZipFile(io.BytesIO(zb))
            full = []
            for nm in zf.namelist():
                if nm.lower().endswith((".xml", ".html", ".htm")):
                    full.append(decode_bytes(zf.read(nm)))
            text = "\n".join(full)
            kwres = {kw: windows(text, kw) for kw in KEYWORDS}
            report[name] = {"sector": sector, "rcept": rcept,
                            "doc_chars": len(text), "keywords": kwres}
            print(name, "OK", rcept, "chars=", len(text))
        except Exception as e:  # noqa: BLE001
            report[name] = {"sector": sector, "error": repr(e)}
            print(name, "FAIL", repr(e))
        time.sleep(0.6)
    out = Path(__file__).parent / "phase0_coverage.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print("WROTE", out)

if __name__ == "__main__":
    main()
