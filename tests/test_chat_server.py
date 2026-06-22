"""Tests for modules.disclosure.chat_server pure helpers.

Covers logic that does NOT hit the Bedrock network:
- _mask_secret: redacts ABSK/AKIA/Bearer tokens before surfacing errors to clients
- _bedrock_model_id: normalizes bare model IDs to us.* (cross-region inference)
- _history_to_bedrock: turns the various history shapes the UIs send into
  the Converse API's role/content schema, dropping unknowns and empty turns
"""

from __future__ import annotations

from modules.disclosure import chat_server as cs

# ─── _mask_secret ─────────────────────────────────────────────────────────────


def test_mask_secret_redacts_absk_token():
    out = cs._mask_secret("error: ABSKabcDEF123+/= was rejected")
    assert "ABSK***MASKED***" in out
    assert "abcDEF123" not in out


def test_mask_secret_redacts_aws_access_key():
    out = cs._mask_secret("found AKIAIOSFODNN7EXAMPLE in logs")
    assert "AKIA***MASKED***" in out
    assert "IOSFODNN7EXAMPLE" not in out


def test_mask_secret_redacts_bearer_header():
    out = cs._mask_secret("Authorization: Bearer ey.J0eXAic-bad.foo bar")
    assert "Bearer ***MASKED***" in out
    assert "ey.J0eXAic-bad.foo" not in out


def test_mask_secret_passthrough_when_clean():
    msg = "Bedrock HTTP 503: temporary upstream failure"
    assert cs._mask_secret(msg) == msg


# ─── _bedrock_model_id ───────────────────────────────────────────────────────


def test_model_id_prefixes_bare_with_us():
    assert cs._bedrock_model_id("anthropic.claude-haiku-4-5-20251001-v1:0") == (
        "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    )


def test_model_id_preserves_existing_us_prefix():
    assert cs._bedrock_model_id("us.anthropic.claude-sonnet-4-6") == (
        "us.anthropic.claude-sonnet-4-6"
    )


def test_model_id_preserves_global_prefix():
    assert cs._bedrock_model_id("global.foo") == "global.foo"


def test_model_id_preserves_arn():
    arn = "arn:aws:bedrock:us-east-1:123:foundation-model/anthropic.claude-haiku-4-5"
    assert cs._bedrock_model_id(arn) == arn


def test_model_id_falls_back_to_default_when_blank():
    assert cs._bedrock_model_id(None) == cs._bedrock_model_id(cs.BEDROCK_DEFAULT_MODEL)
    assert cs._bedrock_model_id("") == cs._bedrock_model_id(cs.BEDROCK_DEFAULT_MODEL)


# ─── _history_to_bedrock ─────────────────────────────────────────────────────


def test_history_maps_model_role_to_assistant():
    out = cs._history_to_bedrock([{"role": "model", "text": "hi"}])
    assert out == [{"role": "assistant", "content": [{"text": "hi"}]}]


def test_history_accepts_who_alias():
    out = cs._history_to_bedrock([{"who": "user", "content": "q"}])
    assert out == [{"role": "user", "content": [{"text": "q"}]}]


def test_history_reads_parts_array_when_text_missing():
    out = cs._history_to_bedrock([{"role": "user", "parts": [{"text": "from-parts"}]}])
    assert out == [{"role": "user", "content": [{"text": "from-parts"}]}]


def test_history_drops_unknown_role():
    out = cs._history_to_bedrock(
        [
            {"role": "system", "text": "drop"},
            {"role": "user", "text": "keep"},
        ]
    )
    assert out == [{"role": "user", "content": [{"text": "keep"}]}]


def test_history_drops_empty_text():
    out = cs._history_to_bedrock([{"role": "user", "text": ""}])
    assert out == []


def test_history_truncates_long_turn_to_4000_chars():
    long_text = "x" * 6000
    out = cs._history_to_bedrock([{"role": "user", "text": long_text}])
    assert len(out[0]["content"][0]["text"]) == 4000


def test_history_keeps_only_last_12_turns():
    big = [{"role": "user", "text": f"q{i}"} for i in range(20)]
    out = cs._history_to_bedrock(big)
    assert len(out) == 12
    assert out[0]["content"][0]["text"] == "q8"
    assert out[-1]["content"][0]["text"] == "q19"
