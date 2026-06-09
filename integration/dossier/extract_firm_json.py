"""1회성 추출 — docs/prototype/firm_*.html → integration/dossier/data/firm_*.json

배경 (docs/ARCHITECTURE.md 알려진 문제 #2 해소):
  financial/dashboard.py 가 데이터를 인라인한 완성 HTML(firm_<ticker>.html)을 생성하고
  integration v1·v2가 이를 iframe으로 임베드했다. 이를 "데이터(JSON) + 단일 템플릿(firm.html)"
  구조로 분리하기 위해, 기존 HTML에 박혀 있는 `const DATA = {...}` 객체를 **무손실로** 뽑아
  per-firm JSON으로 저장한다.

원칙:
  - financial 모듈 코드는 건드리지 않는다(integration-only). 기존 HTML의 const DATA 바이트를 그대로 사용 → 데이터 100% 동일.
  - 헤더 표시값(_hdr)은 financial/dashboard.build_dashboard 와 동일한 로직으로 재계산
    (corp_name/corp_code/year_range/total/grade) → firm.html 헤더가 바이트 동일하게 렌더되도록.

실행 (repo 루트에서):
  python integration/dossier/extract_firm_json.py
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
_SRC_GLOB = os.path.join(_ROOT, "docs", "prototype", "firm_*.html")
_OUT_DIR = os.path.join(_HERE, "data")

_DATA_PREFIX = "const DATA = "
_FNAME_RE = re.compile(r"firm_(\w+)\.html$")
_REQUIRED_KEYS = {"corp", "years", "eqs", "ratios", "industry", "summary", "highlights", "glossary"}


def _extract_data_object(html_path: str) -> dict:
    """HTML 내 `const DATA = {...};` 한 줄에서 JSON을 파싱."""
    with open(html_path, "r", encoding="utf-8") as fp:
        for line in fp:
            stripped = line.strip()
            if stripped.startswith(_DATA_PREFIX):
                payload = stripped[len(_DATA_PREFIX):]
                if payload.endswith(";"):
                    payload = payload[:-1]
                return json.loads(payload)
    raise ValueError(f"`const DATA = ` 라인을 찾지 못함: {html_path}")


def _build_hdr(data: dict) -> dict:
    """financial/dashboard.build_dashboard 의 헤더 주입값과 동일하게 재계산.

    원본:
        year_range = f"{min}~{max} ({len}년)"  (years 없으면 "—")
        total      = eqs.total if not None else "—"  (이후 str.format → str())
        grade      = eqs.grade or "F"
    """
    corp = data.get("corp") or {}
    years = [y.get("year") for y in (data.get("years") or []) if y.get("year") is not None]
    if years:
        year_range = f"{min(years)}~{max(years)} ({len(years)}년)"
    else:
        year_range = "—"

    eqs = data.get("eqs") or {}
    total_val = eqs.get("total")
    total = str(total_val) if total_val is not None else "—"
    grade = eqs.get("grade") or "F"

    return {
        "corp_name": corp.get("name") or "(이름 없음)",
        "corp_code": corp.get("code"),
        "year_range": year_range,
        "total": total,
        "grade": grade,
    }


def main() -> int:
    os.makedirs(_OUT_DIR, exist_ok=True)
    sources = sorted(glob.glob(_SRC_GLOB))
    if not sources:
        print(f"[!] 원본 HTML 없음: {_SRC_GLOB}", file=sys.stderr)
        return 1

    ok, fail = 0, 0
    missing_keys_report = []
    for src in sources:
        m = _FNAME_RE.search(os.path.basename(src))
        if not m:
            print(f"[skip] 파일명 패턴 불일치: {src}")
            continue
        ticker = m.group(1)
        try:
            data = _extract_data_object(src)
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {ticker}: {exc}")
            fail += 1
            continue

        missing = _REQUIRED_KEYS - set(data.keys())
        if missing:
            missing_keys_report.append((ticker, sorted(missing)))

        data["_hdr"] = _build_hdr(data)

        out_path = os.path.join(_OUT_DIR, f"firm_{ticker}.json")
        with open(out_path, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, separators=(",", ":"))
        ok += 1

    print(f"\n[done] {ok}개 생성, {fail}개 실패 → {_OUT_DIR}")
    if missing_keys_report:
        print("[warn] 필수 키 누락:")
        for ticker, miss in missing_keys_report:
            print(f"   firm_{ticker}: {miss}")
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
