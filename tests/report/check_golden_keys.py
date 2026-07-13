"""check_golden_keys.py — galaxy_<ticker>.json 골든/생성물 구조 스모크 (Phase 0-E).

pydantic 아님 — 키·enum·산술·시계열 5점 완결만 본다(pydantic 승격은 Phase 4 schemas.py).
스키마 출처: design/prototypes/현금은하수_해방판.html 전수 역산(Phase 0-A) → integration/dossier/GALAXY_JSON_SCHEMA.md.

⚠️ 이 스크립트는 "구조 스모크"다. 골든의 시각 정확성(표시값·색키·amt)은 Phase 1 시각 대조에서
   최종 확정된다(check 통과 ≠ 골든 확정 — DOSSIER_TABS_PLAN §Phase 0 DoD).

사용:
    python tests/report/check_golden_keys.py                       # 기본 골든(005930)
    python tests/report/check_golden_keys.py path/to/galaxy_x.json # 임의 파일
pytest로도 수집됨(test_golden_keys).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# ── 확정 스키마 상수 (해방판 역산) ──────────────────────────────────────────

# S 시계열 24키 (해방판 L1063-1088 자구 그대로)
SERIES_KEYS = [
    "revenue",
    "cogs",
    "gross",
    "sgna",
    "op",
    "pretax",
    "tax",
    "ni",
    "oci",
    "ocf",
    "icf",
    "capex",
    "fin",
    "div",
    "buyback",
    "dep",
    "rnd",
    "cash",
    "assets",
    "debt",
    "equity",
    "dsOp",
    "eps",
    "tci",
]

YEARS_LEN = 5  # 5개년(FY21~FY25) — 5점 완결

VIZ_ENUM = {
    "vLine",
    "vTwin",
    "vWater",
    "vHBar",
    "vSteps",
    "vBubbles",
    "vPuddle",
    "vChips",
}

# 색 키 (해방판 C 상수: 코드가 --var로 해석)
COLOR_ENUM = {"mint", "cyan", "gold", "coral", "steel", "green"}

# 매듭 kind (해방판 KNOTS 자구: res/source/out/node/in/hub/back/bright)
KNOT_KIND_ENUM = {"res", "source", "out", "node", "in", "hub", "back", "bright"}

KNOTS_COUNT = 17  # 해방판 KNOTS k1~k15 + k6b + k10b
DIVES_TOTAL = 41  # 콘텐츠 27 + APPENDIX 강등 14
APPENDIX_COUNT = 14

CORP_KEYS = {"ticker", "name", "fiscal_year", "fiscal_label", "unit"}  # rcept_no 선택
TOP_KEYS = {
    "schema_version",
    "corp",
    "years",
    "series",
    "knots",
    "panels",
    "dives",
    "meta",
}

DEFAULT_GOLDEN = (
    Path(__file__).resolve().parents[2]
    / "integration"
    / "dossier"
    / "data"
    / "galaxy_005930.json"
)

TOL = 0.15  # 조 단위 표시값 반올림 오차 허용(±0.15조)


class GoldenError(Exception):
    pass


def _fail(errs: list[str], msg: str) -> None:
    errs.append(msg)


def check(doc: dict) -> list[str]:
    """골든 문서 구조 검증. 오류 문자열 리스트 반환(빈 리스트=통과)."""
    errs: list[str] = []

    # 1) 최상위 키
    missing = TOP_KEYS - doc.keys()
    if missing:
        _fail(errs, f"최상위 키 결측: {sorted(missing)}")

    # 2) corp
    corp = doc.get("corp", {})
    cmiss = CORP_KEYS - corp.keys()
    if cmiss:
        _fail(errs, f"corp 키 결측: {sorted(cmiss)}")

    # 3) years
    years = doc.get("years", [])
    if len(years) != YEARS_LEN:
        _fail(errs, f"years 길이 {len(years)} ≠ {YEARS_LEN}")

    # 4) series — 24키 존재 + 각 5점 완결(골든은 전 키 완결)
    series = doc.get("series", {})
    smiss = set(SERIES_KEYS) - series.keys()
    if smiss:
        _fail(errs, f"series 키 결측: {sorted(smiss)}")
    for k in SERIES_KEYS:
        if k not in series:
            continue
        v = series[k]
        if not isinstance(v, list) or len(v) != YEARS_LEN:
            _fail(
                errs,
                f"series['{k}'] 5점 미완결: len={len(v) if isinstance(v, list) else '?'}",
            )
        elif any(not isinstance(x, (int, float)) for x in v):
            _fail(errs, f"series['{k}'] 비수치 원소 포함")

    # 5) series 산술 정합 (교육용 단순화 허용 — spot만): gross ≈ revenue - cogs
    if all(k in series for k in ("revenue", "cogs", "gross")):
        for i in range(min(YEARS_LEN, len(series["gross"]))):
            try:
                exp = series["revenue"][i] - series["cogs"][i]
                if abs(exp - series["gross"][i]) > TOL:
                    _fail(
                        errs,
                        f"산술: gross[{i}]={series['gross'][i]} ≠ revenue-cogs={exp:.1f}",
                    )
            except (IndexError, TypeError):
                pass

    # 6) knots — 17개, 필수 필드 + kind enum
    knots = doc.get("knots", [])
    if len(knots) != KNOTS_COUNT:
        _fail(errs, f"knots 개수 {len(knots)} ≠ {KNOTS_COUNT}")
    for kn in knots:
        for f in ("id", "row", "kind", "name", "amt"):
            if f not in kn:
                _fail(errs, f"knot {kn.get('id','?')} 필드 결측: {f}")
        if kn.get("kind") not in KNOT_KIND_ENUM:
            _fail(errs, f"knot {kn.get('id','?')} kind '{kn.get('kind')}' enum 위반")

    # 7) panels — 존 A~E 존재
    panels = doc.get("panels", {})
    for z in ("A", "B", "C", "D", "E"):
        if z not in panels:
            _fail(errs, f"panels 존 결측: {z}")
    for z, rows in panels.items():
        for r in rows if isinstance(rows, list) else []:
            for f in ("row", "name"):
                if f not in r:
                    _fail(errs, f"panel[{z}] 행 필드 결측: {f} ({r.get('row','?')})")
            if r.get("color") and r["color"] not in COLOR_ENUM:
                _fail(
                    errs, f"panel[{z}] 행 {r.get('row')} color '{r['color']}' enum 위반"
                )

    # 8) dives — enum + five 3형 + raw_mn 정수
    dives = doc.get("dives", {})
    for key, d in dives.items():
        why = d.get("why", {})
        viz = why.get("viz")
        if viz is not None and viz not in VIZ_ENUM:
            _fail(errs, f"dive[{key}] viz '{viz}' enum 위반")
        if d.get("color_key") and d["color_key"] not in COLOR_ENUM:
            _fail(errs, f"dive[{key}] color_key '{d['color_key']}' enum 위반")
        if (
            "raw_mn" in d
            and d["raw_mn"] is not None
            and not isinstance(d["raw_mn"], int)
        ):
            _fail(errs, f"dive[{key}] raw_mn 비정수: {d['raw_mn']}")
        five = d.get("five")
        if isinstance(five, dict):
            has = [k for k in ("key", "twin", "skip") if k in five]
            if len(has) != 1:
                _fail(
                    errs, f"dive[{key}] five 형 모호(정확히 key|twin|skip 하나): {has}"
                )
            if five.get("key") and five["key"] not in SERIES_KEYS:
                _fail(errs, f"dive[{key}] five.key '{five['key']}' series 키 아님")
        # links[].row 는 패널 행 참조(존재성은 Phase 4 L2에서 강검증) — 여기선 형만
        for l in d.get("links", []):
            if "t" not in l:
                _fail(errs, f"dive[{key}] link 't'(표 종류) 결측")

    # 9) appendix — 14건, five=skip
    appendix = doc.get("appendix", [])
    if len(appendix) != APPENDIX_COUNT:
        _fail(errs, f"appendix 개수 {len(appendix)} ≠ {APPENDIX_COUNT}")

    # 10) meta.routing 합 = 41
    routing = doc.get("meta", {}).get("routing", {})
    if routing:
        tot = routing.get("dive", 0) + routing.get("appendix", 0)
        if tot != DIVES_TOTAL:
            _fail(errs, f"meta.routing 합 {tot} ≠ {DIVES_TOTAL} (dive+appendix)")

    return errs


def load_and_check(path: Path) -> list[str]:
    if not path.exists():
        return [f"파일 없음: {path}"]
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"JSON 파싱 실패: {e}"]
    return check(doc)


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_GOLDEN
    errs = load_and_check(path)
    if errs:
        print(f"✗ {path.name}: {len(errs)}건 실패")
        for e in errs:
            print(f"  - {e}")
        return 1
    print(f"✓ {path.name}: 구조 스모크 통과 (구조만 — 시각 정확성은 Phase 1)")
    return 0


# ── pytest 진입점 (DART/LLM 무의존, 골든 파일만) ──
def test_golden_keys():
    import pytest

    if not DEFAULT_GOLDEN.exists():
        pytest.skip("골든 galaxy_005930.json 미작성(Phase 0-D 이전)")
    errs = load_and_check(DEFAULT_GOLDEN)
    assert not errs, "골든 구조 실패:\n" + "\n".join(errs)


if __name__ == "__main__":
    raise SystemExit(main())
