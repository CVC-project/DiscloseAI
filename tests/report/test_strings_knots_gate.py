# -*- coding: utf-8 -*-
"""V-110 회귀 — 저작해 두고도 화면에 닿지 않던 필드의 게이트 (2026-08-05).

실사고: `strings.overview`·`epilogue`·`intro_lines`가 4본(011200·012450·017670·033780)에서
전량 공란인 채, `knots[].story`는 7본에서 전량 공란인 채 `--all --strict` 17본 0을 통과하며
서빙됐다. `check_golden`에 'strings' 참조 자체가 없었고 knots는 존재만 봤다.
렌더러는 둘 다 실제로 그린다(`{{ strings.intro_lead }}`·overview/epilogue 문단·`storyCard()`).
"""
import glob
import json
import os

import pytest

from modules.report import check_golden as CG

_DATA = os.path.join("integration", "dossier", "data")


def _goldens():
    """골든 galaxy_<ticker>.json만 — V-110 게이트는 **골든 렌더러(galaxy.html)가 그리는 필드**의 계약이다.

    ⚠️ `galaxy_lite_*`는 별도 렌더러(galaxy_lite.html)·별도 스키마다(overview·epilogue·knots 자체가
    없고 hero·delta_intro·notes_intro를 쓴다 — 파일 헤더에 "골든과 스키마가 다름" 명시).
    종전 glob이 lite까지 삼켜 24건이 구조적으로 FAIL했다(NEXT_SESSION 데이터부채 #4 → 해소).
    """
    return sorted(
        p for p in glob.glob(os.path.join(_DATA, "galaxy_*.json"))
        if os.path.basename(p) != "galaxy_index.json"
        and not os.path.basename(p).startswith("galaxy_lite_")
    )


@pytest.mark.parametrize("path", _goldens())
def test_strings_required_fields_filled(path):
    """렌더러가 실제로 읽는 strings 필드는 비어 있으면 안 된다."""
    st = (json.load(open(path, encoding="utf-8")).get("strings") or {})
    il = [x for x in (st.get("intro_lines") or []) if (x or "").strip()]
    assert len(il) >= 2, f"{os.path.basename(path)} intro_lines 채워진 줄 {len(il)}개"
    for f in ("overview", "epilogue"):
        assert (st.get(f) or "").strip(), f"{os.path.basename(path)} {f} 공란"


@pytest.mark.parametrize("path", _goldens())
def test_knot_story_filled(path):
    """매듭 카드 본문(knots[].story)은 전부 채워져 있어야 한다."""
    ks = json.load(open(path, encoding="utf-8")).get("knots") or []
    empty = [k.get("id") for k in ks if not (k.get("story") or "").strip()]
    assert not empty, f"{os.path.basename(path)} story 공란 {empty}"


def test_gate_detects_empty_strings():
    """게이트가 공란을 실제로 FAIL로 잡는지(회귀 방지용 음성 테스트)."""
    g = json.load(open(os.path.join(_DATA, "galaxy_005930.json"), encoding="utf-8"))
    g["strings"] = {"intro_lines": ["", ""], "overview": "", "epilogue": ""}
    g["knots"] = [{"id": "k1", "story": ""}]
    gaps = CG._strict_gaps(g, "005930") if hasattr(CG, "_strict_gaps") else None
    if gaps is None:
        pytest.skip("strict 진입점 비공개 — --all --strict 통합 실행이 게이트를 덮는다")
    blob = " ".join(gaps)
    assert "[strings] overview 공란" in blob
    assert "[strings] epilogue 공란" in blob
    assert "[knots] story 공란" in blob
