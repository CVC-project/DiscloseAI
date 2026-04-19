"""용어 사전 단위 테스트."""

from __future__ import annotations

from modules.financial.glossary import GLOSSARY, describe, label
from modules.financial.translator.ratios import LABELS as RATIO_LABELS


def test_all_ratio_keys_have_glossary_entries():
    """수익성 비율 5개는 모두 glossary에 있어야 함 (대시보드 툴팁 용)."""
    missing = [k for k in RATIO_LABELS if k not in GLOSSARY]
    assert missing == [], f"glossary 누락: {missing}"


def test_m1_to_m5_have_glossary_entries():
    """EQS 5개 모듈도 모두 glossary에 있어야 함."""
    for m in ("M1", "M2", "M3", "M4", "M5"):
        assert m in GLOSSARY, f"{m} glossary 누락"


def test_cashflow_three_have_glossary_entries():
    """현금흐름 3종은 사용자가 명시적으로 요청한 용어."""
    for k in ("operating_cashflow", "investing_cashflow", "financing_cashflow"):
        assert k in GLOSSARY, f"{k} 누락"


def test_describe_returns_description():
    """describe(key) → 설명 문자열."""
    desc = describe("roe")
    assert "ROE" in describe("roe") or "자본" in desc or "수익률" in desc
    assert len(desc) > 20  # 최소한 의미 있는 길이


def test_describe_missing_key_returns_empty():
    """없는 key는 빈 문자열."""
    assert describe("없는키XYZ") == ""


def test_label_returns_display_name():
    """label(key) → 표시명."""
    assert "ROE" in label("roe")
    assert "M1" in label("M1")


def test_label_missing_key_returns_key_itself():
    """없는 key는 key 자체를 반환 (fallback)."""
    assert label("unknown_term") == "unknown_term"


def test_all_entries_have_both_label_and_description():
    """모든 glossary 항목은 label + description 필수 필드를 채워야."""
    for key, entry in GLOSSARY.items():
        assert entry.label, f"{key} 표시명 비어있음"
        assert entry.description and len(entry.description) >= 10, (
            f"{key} description이 너무 짧음"
        )


def test_ratios_have_benchmark_and_intuition():
    """수익성 비율 5개는 기준선·직관 섹션을 채워 UI에서 3개 섹션 렌더되게 함."""
    for key in ("gross_margin", "operating_margin", "net_margin", "roe", "roa"):
        entry = GLOSSARY[key]
        assert entry.benchmark, f"{key} benchmark 비어있음"
        assert entry.intuition, f"{key} intuition 비어있음"


def test_eqs_modules_have_how_section():
    """EQS M1~M5는 '산출 방식' 섹션 필수 — 사용자가 어떻게 계산되는지 알아야."""
    for m in ("M1", "M2", "M3", "M4", "M5"):
        entry = GLOSSARY[m]
        assert entry.how, f"{m} how(산출 방식) 비어있음"


def test_as_dict_has_all_fields():
    """as_dict()는 label/description/how/benchmark/intuition 5개 키 반환 (대시보드 JSON 직렬화용)."""
    d = GLOSSARY["roe"].as_dict()
    assert set(d.keys()) == {"label", "description", "how", "benchmark", "intuition"}
