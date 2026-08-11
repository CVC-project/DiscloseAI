"""galaxy lite 회귀 게이트(check_lite_quality.py)의 **음성 테스트**.

원장에 적힌 실수를 하나씩 되살려 넣고, 게이트가 그걸 실제로 잡는지 확인한다.
게이트가 통과만 시키는 고무도장이 되지 않게 하는 것이 이 파일의 목적이다.
규칙을 추가할 때 여기에 음성 케이스도 함께 추가할 것 (규칙 1개 = 케이스 1개).
"""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from typing import Any

MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "integration" / "dossier" / "check_lite_quality.py"
)
SPEC = importlib.util.spec_from_file_location("check_lite_quality", MODULE_PATH)
assert SPEC and SPEC.loader
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


def _doc() -> dict[str, Any]:
    """규칙을 전부 만족하는 최소 lite 문서 (여기서 하나씩 망가뜨린다)."""
    return {
        "corp": {"ticker": "999999", "name": "테스트전자"},
        "std_ref": {"ticker": "000000", "name": "표준전자"},  # dives 파일 없음 → R8은 skip
        "years": ["FY24", "FY25"],
        "series": {"op": [1.0, 2.0], "fin": [-1.0, -1.0], "ocf": [1.0, 1.0], "icf": [-1.0, -1.0]},
        "std_series": {"op": [1.0, 1.0], "fin": [-1.0, -1.0], "ocf": [1.0, 1.0], "icf": [-1.0, -1.0]},
        "pattern": {"code": "+--"},
        "strings": {"hero": "표준과 무엇이 어떻게 다를까요?"},
        "cards": [
            {
                "id": "d1",
                "title": "100원 팔면 몇 원이 남나",
                "lines": ["표준은 [1.0조]를 남겼어요.", "이 회사는 [2.0조]예요.", "그래서 더 넉넉해요."],
                "anchor": {"zone": "B", "std_focus": "zoneB"},
                "order": 1,
                "bridge": None,
            },
            {
                "id": "d3",
                "title": "지금 국면 — 자가발전형",
                "lines": [
                    "표준전자는 최근 연도가 자가발전형이에요.",
                    "테스트전자도 [FY24]부터 [FY25]까지 줄곧 자가발전형이에요.",
                    "재무활동 현금이 (−)면 빚을 갚는 국면이에요 — 돈을 다루는 방식이 표준과 같은 방향이에요.",
                ],
                "anchor": {"zone": "D", "std_focus": "zoneD"},
                "order": 2,
                "bridge": "그런데 최근 연도에 흐름이 바뀌었어요.",
            },
        ],
        "notes": [],
    }


def test_baseline_passes() -> None:
    assert GATE.check_doc("999999", _doc()) == []


def test_r1_catches_migongsi() -> None:
    """FN-021 — 수집 갭을 '미공시'로 단정."""
    d = _doc()
    d["cards"][0]["lines"][2] = "FY21은 현금흐름 미공시예요."
    assert any(e.startswith("R1") for e in GATE.check_doc("999999", d))


def test_r2_catches_metaphor() -> None:
    """UX-041 — lite 카드에서 은유 금지."""
    d = _doc()
    d["cards"][0]["lines"][2] = "돈이 저수지에 고여 있어요."
    assert any(e.startswith("R2") for e in GATE.check_doc("999999", d))


def test_r3_catches_eqs_overlap() -> None:
    """PLAN §1 — EQS 탭과 내용 중복."""
    d = _doc()
    d["cards"][0]["lines"][2] = "업계 평균보다 ROE가 높아요."
    errs = GATE.check_doc("999999", d)
    assert sum(e.startswith("R3") for e in errs) >= 2


def test_r4_catches_formal_style() -> None:
    d = _doc()
    d["cards"][0]["lines"][2] = "그래서 여력이 크다."
    assert any(e.startswith("R4") for e in GATE.check_doc("999999", d))


def test_r5_catches_wrong_standard_claim() -> None:
    """FN-022 — 표준도 (−)인데 '표준과 반대'라고 단정."""
    d = _doc()
    d["cards"][1]["lines"][2] = "재무활동 현금이 (−)면 … 표준은 같은 해 반대로 돈을 당겨왔어요."
    assert any(e.startswith("R5") for e in GATE.check_doc("999999", d))


def test_r5_catches_wrong_same_direction_claim() -> None:
    """FN-022 — 표준 부호가 반대인데 '같은 방향'이라고 단정."""
    d = _doc()
    d["std_series"]["fin"] = [1.0, 1.0]  # 표준은 (+)
    assert any(e.startswith("R5") for e in GATE.check_doc("999999", d))


def test_r6_catches_false_agreement_particle() -> None:
    """FN-022 — 국면이 다른데 '…도'로 동조 서술."""
    d = _doc()
    d["pattern"]["code"] = "++-"  # 표준(+--)과 다른 국면
    d["series"]["icf"] = [1.0, 1.0]
    errs = GATE.check_doc("999999", d)
    assert any(e.startswith("R6") for e in errs)


def test_r7_catches_profit_wording_on_loss() -> None:
    """FN-022 — 적자인데 '남아요'."""
    d = _doc()
    d["series"]["op"] = [1.0, -2.0]
    d["cards"][0]["lines"][1] = "이 회사는 100원당 [-13.0원]이 남아요."
    assert any(e.startswith("R7") for e in GATE.check_doc("999999", d))


def test_r9_catches_broken_thread() -> None:
    """UX-042 — 첫 카드에 bridge가 붙어 스레드가 어긋남."""
    d = _doc()
    d["cards"][0]["bridge"] = "앞에서 이어져요."
    assert any(e.startswith("R9") for e in GATE.check_doc("999999", d))


def test_r9_catches_order_gap() -> None:
    d = _doc()
    d["cards"][1]["order"] = 5
    assert any(e.startswith("R9") for e in GATE.check_doc("999999", d))


def test_r11_catches_line_count() -> None:
    d = _doc()
    d["cards"][0]["lines"] = ["한 줄만 있어요."]
    assert any(e.startswith("R11") for e in GATE.check_doc("999999", d))


def test_r12_catches_text_bracket() -> None:
    """BATCH §4 — 브래킷은 숫자 전용."""
    d = _doc()
    d["cards"][0]["lines"][0] = "표준은 [가장 나빴던 해]에 부진했어요."
    assert any(e.startswith("R12") for e in GATE.check_doc("999999", d))


def test_r13_catches_advice_words() -> None:
    d = _doc()
    d["cards"][0]["lines"][2] = "지금이 매수 기회예요."
    assert any(e.startswith("R13") for e in GATE.check_doc("999999", d))


def test_r14_catches_impossible_normalized_value() -> None:
    """FN-023 — 카카오 실사례: firm JSON 매출이 연결·별도 혼재라 정규화가 242%가 됐다."""
    d = _doc()
    d["norm"] = {"op": [242.3, 9.0]}
    assert any(e.startswith("R14") for e in GATE.check_doc("999999", d))


def test_r14_allows_real_outlier_net_income() -> None:
    """한미반도체 FY23 실측 168% — 지분 처분이익이면 순이익이 매출을 넘을 수 있다(오탐 금지)."""
    d = _doc()
    d["norm"] = {"ni": [168.0, 37.1]}
    assert not any(e.startswith("R14") for e in GATE.check_doc("999999", d))


def test_r15_catches_basis_mix_in_revenue() -> None:
    """FN-023 — 매출이 급락했다가 급반등하면 기준 혼재를 의심한다."""
    d = _doc()
    d["years"] = ["FY23", "FY24", "FY25"]
    d["series"]["revenue"] = [6.8, 0.19, 8.1]
    assert any(e.startswith("R15") for e in GATE.check_doc("999999", d))


def test_notes_thread_is_checked_independently() -> None:
    """notes도 델타와 같은 스레드 규격을 받는다."""
    d = _doc()
    d["notes"] = [
        {"id": "n1", "title": "제목", "what": ["문장이에요."], "why": [], "order": 1, "bridge": None},
        {"id": "n2", "title": "제목", "what": ["문장이에요."], "why": [], "order": 2, "bridge": None},
    ]
    assert any(e.startswith("R9") and "n2" in e for e in GATE.check_doc("999999", d))


def test_segments_schema_drift_is_normalized_not_silently_dropped() -> None:
    """FN-024 — fact 추출은 기업마다 새 실행이라 segments 스키마가 흔들린다.

    `segment`(이름 키가 다름)·`revenue_won_cur`(당기/전기 한 행) 두 변종을 실제로 받았다.
    조용히 누락되면 카드가 근거 없는 값을 참조하게 되므로, 정규화하거나 세워야 한다.
    """
    inject_path = (
        Path(__file__).resolve().parents[1] / "integration" / "dossier" / "inject_lite_notes.py"
    )
    spec = importlib.util.spec_from_file_location("inject_lite_notes", inject_path)
    assert spec and spec.loader
    inject = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inject)

    # 변종 A: name 대신 segment
    flat = inject.flatten_facts(
        {"facts": [], "segments": [{"segment": "A/S", "period": "당기", "revenue_won": 5, "op_won": 1}]}
    )
    assert flat["seg_A/S_rev"] == 5 and flat["seg_A/S_op"] == 1

    # 변종 B: 당기·전기가 한 행에 _cur/_prior로
    flat = inject.flatten_facts(
        {
            "facts": [],
            "segments": [{"segment": "배터리", "revenue_won_cur": 7, "revenue_won_prior": 6,
                          "op_won_cur": -1, "op_won_prior": -2}],
        }
    )
    assert flat["seg_배터리_rev"] == 7 and flat["seg_배터리_rev_prior"] == 6
    assert flat["seg_배터리_op"] == -1 and flat["seg_배터리_op_prior"] == -2

    # 이름이 없으면 조용히 넘기지 않고 세운다 (seg__rev 로 뭉개지는 것 방지)
    import pytest

    with pytest.raises(SystemExit):
        inject.flatten_facts({"facts": [], "segments": [{"period": "당기", "revenue_won": 1}]})


def test_real_outputs_pass_the_gate() -> None:
    """실제 산출물 전수 — 회귀가 들어오면 여기서 먼저 터진다."""
    data = Path(__file__).resolve().parents[1] / "integration" / "dossier" / "data"
    docs = sorted(p for p in data.glob("galaxy_lite_*.json") if p.name != "galaxy_lite_index.json")
    assert docs, "lite 산출물이 하나도 없어요"
    for p in docs:
        import json

        doc = json.loads(p.read_text(encoding="utf-8"))
        t = p.name[len("galaxy_lite_") : -len(".json")]
        assert GATE.check_doc(t, copy.deepcopy(doc)) == [], f"{t} 게이트 위반"
