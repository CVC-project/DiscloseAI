"""1회성 추출 — design/prototypes/kospi50_business_tabs.html → integration/dossier/data/business_*.json

배경 (DOSSIER_TABS_PLAN Phase S2·D5):
  business 프로토타입은 48사 데이터를 `const DATA = [ {...}, ... ]` 배열로 한 파일에 내장한다.
  이를 firm.html 전례처럼 "데이터(per-company JSON) + 단일 템플릿(business.html)"로 분리하기 위해
  DATA 배열을 **무손실로** 뽑아 회사별 business_<stock_code>.json 으로 저장한다.

원칙:
  - 프로토타입 코드는 건드리지 않는다(integration-only). const DATA 바이트를 그대로 → 데이터 100% 동일.
  - LLM 무관 — 결정적 파싱·분할.

실행 (repo 루트에서):
  python integration/dossier/extract_business_json.py                    # 전체 48
  python integration/dossier/extract_business_json.py --only 017670,105560,035420
"""

from __future__ import annotations

import argparse
import json
import copy
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
_SRC = os.path.join(_ROOT, "design", "prototypes", "kospi50_business_tabs.html")
_OUT_DIR = os.path.join(_HERE, "data")

_DATA_PREFIX = "const DATA = "
_CUSTOM_REPORT_IDEAS = "CUSTOM_REPORT_IDEAS"
_LOCAL_IMAGE_PREFIX = "../../integration/data/business_images/"
_DEPLOYED_IMAGE_PREFIX = "../data/business_images/"

# 생성기 계약 (D12·부록 A-2) — kind 21종
_KNOWN_KINDS = {
    "factory",
    "finance",
    "platform",
    "energy",
    "battery",
    "signal",
    "shield",
    "chem",
    "ship",
    "card",
    "bio",
    "auto",
    "aero",
    "lab",
    "chip",
    "steel",
    "sensor",
    "game",
    "storage",
    "display",
    "device",
}


def _extract_json_constant(html_path: str, constant_name: str) -> object:
    """HTML의 `const NAME = <JSON>;` 값을 JSON으로 읽는다."""
    source = open(html_path, "r", encoding="utf-8").read()
    marker = f"const {constant_name} = "
    start = source.find(marker)
    if start < 0:
        raise ValueError(f"`{marker}`를 찾지 못함: {html_path}")
    payload = source[start + len(marker) :].lstrip()
    value, _ = json.JSONDecoder().raw_decode(payload)
    return value


def _prepare_for_dossier(row: dict, custom_ideas: dict[str, list]) -> dict:
    """프로토타입 행을 dossier 단일 기업 JSON 계약으로 변환한다."""
    prepared = copy.deepcopy(row)
    code = str(prepared.get("stock_code", "")).zfill(6)
    prepared["custom_report_ideas"] = custom_ideas.get(code, [])
    for card in prepared.get("business_cards") or []:
        image = card.get("image")
        if isinstance(image, str) and image.startswith(_LOCAL_IMAGE_PREFIX):
            card["image"] = _DEPLOYED_IMAGE_PREFIX + os.path.basename(image)
    return prepared


def _validate(row: dict) -> list[str]:
    """생성기 계약 검증 — 위반은 경고(폴백 렌더 전제). 경고 문자열 리스트 반환."""
    warns: list[str] = []
    cards = row.get("business_cards") or []
    if not (2 <= len(cards) <= 4):
        warns.append(f"business_cards {len(cards)}개 (기대 2~4)")
    for c in cards:
        k = c.get("kind")
        if k and k not in _KNOWN_KINDS:
            warns.append(f"미지 kind '{k}'")
    # dart_url 또는 report.rcept_no 중 하나 필수
    has_dart = bool(row.get("dart_url"))
    has_rcept = bool((row.get("report") or {}).get("rcept_no"))
    if not (has_dart or has_rcept):
        warns.append("dart_url·rcept_no 모두 결측")
    # R11: rd_chart.ratios 가 비율(0~100)로 보이면 경고
    rd = (row.get("snippets") or {}).get("rd_chart") or {}
    ratios = rd.get("ratios")
    if (
        isinstance(ratios, list)
        and ratios
        and all(isinstance(x, (int, float)) and 0 <= x <= 100 for x in ratios)
    ):
        warns.append("rd_chart.ratios 비율값 혼입 의심(R11)")
    return warns


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--only", default="", help="쉼표구분 stock_code 일부만 (예: 017670,105560)"
    )
    args = ap.parse_args()
    only = {t.strip() for t in args.only.split(",") if t.strip()} if args.only else None

    data = _extract_json_constant(_SRC, "DATA")
    custom_ideas = _extract_json_constant(_SRC, _CUSTOM_REPORT_IDEAS)
    if not isinstance(data, list):
        raise ValueError("const DATA 가 배열이 아님")
    if not isinstance(custom_ideas, dict):
        raise ValueError("const CUSTOM_REPORT_IDEAS 가 객체가 아님")
    print(f"const DATA: {len(data)}사 파싱")
    os.makedirs(_OUT_DIR, exist_ok=True)

    written, warned = 0, 0
    for row in data:
        code = str(row.get("stock_code", "")).zfill(6)
        if not code or code == "000000":
            print(f"⚠ stock_code 결측 레코드 스킵: {row.get('name','?')}")
            continue
        if only and code not in only:
            continue
        prepared = _prepare_for_dossier(row, custom_ideas)
        warns = _validate(prepared)
        if warns:
            warned += 1
            print(f"  [{code}] {row.get('name','?')}: " + " · ".join(warns))
        out = os.path.join(_OUT_DIR, f"business_{code}.json")
        with open(out, "w", encoding="utf-8") as fp:
            json.dump(prepared, fp, ensure_ascii=False, separators=(",", ":"))
        written += 1

    scope = f"{len(only)}사 지정" if only else "전체"
    print(f"→ business_*.json {written}개 저장 ({scope}), 경고 {warned}사")
    if only:
        missing = only - {str(r.get("stock_code", "")).zfill(6) for r in data}
        if missing:
            print(f"⚠ DATA에 없는 지정 티커: {sorted(missing)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
