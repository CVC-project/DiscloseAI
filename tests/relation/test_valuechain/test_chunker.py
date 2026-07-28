"""chunker/pipeline.py 단위 테스트 (valuechain PLAN.md §3.1 계약).

DB 무접근 — 순수 함수(문장 분할·후보 게이트·윈도우 병합·캡·결정적 id)만 검증.
"""

from __future__ import annotations

import re

from modules.relation.valuechain.chunker.pipeline import (
    MAX_CHUNK_CHARS,
    _is_candidate,
    _split_sentences,
    _windows,
    chunk_section,
)

NAME_PAT = re.compile("|".join(map(re.escape, ["삼성전자", "한화", "SK하이닉스"])))


def test_split_sentences_preserves_offsets():
    text = "첫 문장이다. 둘째 문장이다.\n\n셋째 문장이다."
    sents = _split_sentences(text)
    assert [s for _, _, s in sents] == ["첫 문장이다.", "둘째 문장이다.", "셋째 문장이다."]
    for start, end, s in sents:
        assert text[start:end] == s  # 오프셋 = provenance 역추적 계약


def test_candidate_gate_keyword_and_name():
    assert _is_candidate("당사의 주요 매출처는 다음과 같다.", None, set())
    assert _is_candidate("삼성전자와 거래한다.", NAME_PAT, set())
    # 자기 회사명만 등장하면 후보 아님 (자기 언급은 관계 신호가 아니다)
    assert not _is_candidate("삼성전자는 반도체를 생산한다.", NAME_PAT, {"삼성전자"})
    assert not _is_candidate("일반적인 산업 동향 서술.", NAME_PAT, set())


def test_windows_merge_and_bounds():
    # 후보 0·1번(±2 겹침)은 병합, 멀리 떨어진 9번은 별도 구간
    assert _windows([0, 1, 9], 12) == [(0, 3), (7, 11)]
    assert _windows([], 10) == []
    assert _windows([0], 1) == [(0, 0)]  # 경계 클램프


def test_chunk_section_cap_and_deterministic_ids():
    long_sent = "매출처 관련 서술 " + "가" * 700 + "."
    text = " ".join([long_sent, long_sent, long_sent])
    chunks = chunk_section("R001", "II.사업의내용", "00000001", text, None, set())
    assert chunks, "관계 어휘 포함 — 후보가 나와야 한다"
    assert all(len(c["text"]) <= MAX_CHUNK_CHARS for c in chunks)  # 1.5K 캡 (§3.1 ②)
    assert [c["chunk_id"] for c in chunks] == [
        f"R001:II.사업의내용:{i}" for i in range(len(chunks))
    ]  # 결정적 id (D12 멱등의 전제)
    # 재실행 동일성
    again = chunk_section("R001", "II.사업의내용", "00000001", text, None, set())
    assert [c["chunk_id"] for c in again] == [c["chunk_id"] for c in chunks]


def test_char_span_roundtrip():
    text = "서두 문장. 당사의 주요 매출처는 A사이다. 마무리 문장."
    chunks = chunk_section("R002", "II.사업의내용", "00000002", text, None, set())
    for c in chunks:
        start, end = map(int, c["char_span"].split("-"))
        assert text[start:end] == c["text"]  # char_span으로 원문 복원 가능해야 한다
