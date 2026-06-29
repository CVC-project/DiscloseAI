"""DART 사업보고서 본문 수집 PoC (모듈 ③ 1단계).

50종목 사업보고서를 DART OpenAPI로 받아오는 첫 검증.

오늘 PoC 범위:
  삼성전자 1건만 — rcept_no 조회 → ZIP 다운로드 → 압축해제 → 구조 확인.
  파싱·UI 표시는 후속 PoC에서.

DART API 사용:
  1) ``list.json`` (pblntf_detail_ty=A001, 사업보고서) → rcept_no 찾기
  2) ``document.xml?rcept_no=...`` → ZIP 다운로드
  3) zip 풀어서 어떤 파일들이 들어있는지 확인

저장 경로:
  modules/disclosure/data/fulltext/<corp_code>/<rcept_no>/

의존성: 표준 라이브러리만 (OpenDartReader 불필요).

실행::

    python -m modules.disclosure.fulltext_collector
"""

from __future__ import annotations

import io
import json
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

DART_API_KEY = os.getenv("DART_API_KEY", "")
DATA_DIR = ROOT / "modules" / "disclosure" / "data" / "fulltext"

# 사업보고서 = A001, 반기보고서 = A002, 분기보고서 = A003
PBLNTF_DETAIL_ANNUAL = "A001"


def find_latest_annual_report(corp_code: str, year: int = 2025) -> dict | None:
    """주어진 corp_code의 사업보고서 중 해당 연도 가장 최근 1건.

    DART list API는 기본적으로 rcept_dt 내림차순 — 첫 번째 항목이 최근.
    A001은 사업보고서 한정 (반기·분기 제외).
    """
    url = (
        f"https://opendart.fss.or.kr/api/list.json"
        f"?crtfc_key={DART_API_KEY}"
        f"&corp_code={corp_code}"
        f"&pblntf_detail_ty={PBLNTF_DETAIL_ANNUAL}"
        f"&bgn_de={year}0101"
        f"&end_de={year + 1}1231"
        f"&page_count=10"
    )
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
    status = data.get("status")
    if status != "000":
        print(
            f"[ERROR] DART list.json status={status}, message={data.get('message')}",
            file=sys.stderr,
        )
        return None
    items = data.get("list", [])
    if not items:
        print(
            f"[WARN] {corp_code} 사업보고서 없음 ({year}~{year + 1})",
            file=sys.stderr,
        )
        return None
    return items[0]


def download_full_report(rcept_no: str, save_dir: Path) -> Path | None:
    """document.xml API로 사업보고서 ZIP 받아 풀어 저장.

    document.xml endpoint는 application/zip을 반환. 에러 시엔 JSON 본문.
    DART는 기본 Python urllib UA를 거부하는 경우가 있어 requests + 명시 UA 사용.
    파일이 10~30MB이라 stream=True로 청크 다운로드.
    """
    url = (
        f"https://opendart.fss.or.kr/api/document.xml"
        f"?crtfc_key={DART_API_KEY}&rcept_no={rcept_no}"
    )
    save_dir.mkdir(parents=True, exist_ok=True)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "*/*",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=180, stream=True)
        resp.raise_for_status()
        content = resp.content  # 전체 메모리 (사업보고서 통상 10~30MB)
    except Exception as e:  # pragma: no cover
        print(f"[ERROR] 다운로드 실패: {e}", file=sys.stderr)
        return None

    # ZIP magic: 'PK\x03\x04'
    if content[:2] != b"PK":
        # 에러 응답(JSON)일 가능성
        try:
            err = json.loads(content)
            print(f"[ERROR] API 응답: {err}", file=sys.stderr)
        except json.JSONDecodeError:
            print(
                f"[ERROR] ZIP 아닌 응답 (앞 200바이트): {content[:200]!r}",
                file=sys.stderr,
            )
        return None

    # 원본 ZIP도 보관 (재추출용)
    zip_path = save_dir / f"{rcept_no}.zip"
    zip_path.write_bytes(content)

    with zipfile.ZipFile(io.BytesIO(content)) as z:
        z.extractall(save_dir)
        names = z.namelist()

    print(f"[OK] {len(names)}개 파일 추출 → {save_dir}")
    return save_dir


def inspect_dir(d: Path) -> None:
    """추출된 디렉토리 구조 출력."""
    print(f"\n[INFO] {d} 내용:")
    for p in sorted(d.rglob("*")):
        if p.is_file():
            size = p.stat().st_size
            rel = p.relative_to(d)
            print(f"  {str(rel):<50s} {size:>12,} bytes")


def update_index(
    corp_code: str,
    corp_name: str,
    rcept_no: str,
    rcept_dt: str,
    report_nm: str,
) -> Path:
    """fulltext/index.json 에 1개 entry 추가·갱신.

    UI(firm.html 본문 뷰어)가 corp_code 로 rcept_no 를 찾을 때 사용.
    동시성 보장 없음 — PoC 단일 프로세스 가정.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    index_path = DATA_DIR / "index.json"
    data: dict = {}
    if index_path.exists():
        try:
            data = json.loads(index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    data[corp_code] = {
        "corp_name": corp_name,
        "rcept_no": rcept_no,
        "rcept_dt": rcept_dt,
        "report_nm": report_nm,
    }
    index_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[INFO] index.json 갱신: {corp_code} → {rcept_no}")
    return index_path


def main() -> int:
    if not DART_API_KEY:
        print("[ERROR] DART_API_KEY가 .env에 설정되지 않았습니다.", file=sys.stderr)
        return 1

    # PoC: 삼성전자
    corp_code = "00126380"
    corp_name = "삼성전자"
    print(f"{'=' * 60}")
    print(f"  사업보고서 본문 수집 PoC — {corp_name} ({corp_code})")
    print(f"{'=' * 60}\n")

    # 가장 최근 사업보고서 찾기 — 2025부터 역순으로 시도
    item = None
    for yr in (2025, 2024):
        item = find_latest_annual_report(corp_code, year=yr)
        if item:
            break
    if item is None:
        print("[ERROR] 사업보고서를 찾지 못했습니다.", file=sys.stderr)
        return 1

    rcept_no = item["rcept_no"]
    print(
        f"[INFO] 찾음: {item.get('report_nm')}\n"
        f"       접수일: {item.get('rcept_dt')}, rcept_no: {rcept_no}"
    )

    save_dir = DATA_DIR / corp_code / rcept_no
    if download_full_report(rcept_no, save_dir) is None:
        return 1

    inspect_dir(save_dir)

    update_index(
        corp_code=corp_code,
        corp_name=corp_name,
        rcept_no=rcept_no,
        rcept_dt=item.get("rcept_dt", ""),
        report_nm=item.get("report_nm", ""),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
