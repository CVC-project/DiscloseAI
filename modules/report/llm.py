"""llm.py — report 모듈 LLM 클라이언트 (SGLang, OpenAI 호환).

Phase 4 하네스의 유일한 LLM 진입점. 원격 A100 SGLang(Qwen3-32B-AWQ)에 SSH 터널로 접속.
- generate(): 산문 생성 (temp 0.3) — 딥다이브 what/why/five 문장화
- extract(): 구조화 추출 (temp 0, json_schema=xgrammar) — 주석 표 수치 (D7: 숫자는 원문 그대로)
- thinking off, seed 고정, 재시도, usage 레저(토큰 회계 — 토큰 폭주 가드).

접속: shared/config.py의 REPORT_LLM_* (SSH 터널 `ssh -i ~/.ssh/id_ed25519_gpu -N -L 30000:127.0.0.1:30000 tta@123.37.8.42`).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from openai import OpenAI

from shared.config import REPORT_LLM_API_KEY, REPORT_LLM_BASE_URL, REPORT_LLM_MODEL

SEED = 20260713  # 재현성 고정
_THINK_OFF = {"chat_template_kwargs": {"enable_thinking": False}}  # Qwen3 thinking 끔(메모리 지시)


@dataclass
class Usage:
    """토큰 레저 — 런당 누적(토큰 폭주 abort 가드용)."""

    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    errors: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def add(self, u) -> None:
        self.calls += 1
        if u:
            self.prompt_tokens += u.prompt_tokens or 0
            self.completion_tokens += u.completion_tokens or 0


@dataclass
class LLM:
    base_url: str = REPORT_LLM_BASE_URL
    api_key: str = REPORT_LLM_API_KEY or "EMPTY"
    model: str = REPORT_LLM_MODEL
    retries: int = 3
    usage: Usage = field(default_factory=Usage)
    _client: OpenAI | None = None

    def __post_init__(self) -> None:
        if not self.base_url:
            raise RuntimeError(
                "REPORT_LLM_BASE_URL 미설정 — SSH 터널을 먼저 올리세요 "
                "(ssh -i ~/.ssh/id_ed25519_gpu -N -L 30000:127.0.0.1:30000 tta@123.37.8.42)."
            )
        self._client = OpenAI(base_url=self.base_url, api_key=self.api_key)

    def _call(self, messages, *, temperature, max_tokens, response_format=None) -> str:
        extra = dict(_THINK_OFF)
        last = None
        for attempt in range(self.retries):
            try:
                kw = dict(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    seed=SEED,
                    extra_body=extra,
                )
                if response_format is not None:
                    kw["response_format"] = response_format
                r = self._client.chat.completions.create(**kw)
                self.usage.add(r.usage)
                return r.choices[0].message.content or ""
            except Exception as e:  # noqa: BLE001 — 재시도 후 재전파
                last = e
                self.usage.errors += 1
                time.sleep(1.2 * (attempt + 1))
        raise RuntimeError(f"LLM 호출 {self.retries}회 실패: {last}")

    def generate(self, prompt: str, *, system: str | None = None, max_tokens: int = 400) -> str:
        """산문 생성 (temp 0.3). 딥다이브 카피 문장화."""
        msgs = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}
        ]
        return self._call(msgs, temperature=0.3, max_tokens=max_tokens)

    def extract(self, prompt: str, schema: dict, *, system: str | None = None, max_tokens: int = 800) -> str:
        """구조화 추출 (temp 0, json_schema=xgrammar). 주석 표 수치 — D7: 원문 값만."""
        rf = {"type": "json_schema", "json_schema": {"name": "extract", "schema": schema, "strict": True}}
        msgs = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}
        ]
        return self._call(msgs, temperature=0.0, max_tokens=max_tokens, response_format=rf)


if __name__ == "__main__":
    import json

    llm = LLM()
    print("[generate]", repr(llm.generate("매출총이익을 초보자에게 한 문장으로 설명해. 한국어.", max_tokens=80)))
    schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}, "amount_mn": {"type": "integer"}},
                    "required": ["name", "amount_mn"],
                },
            }
        },
        "required": ["items"],
    }
    out = llm.extract(
        "다음 표에서 항목명과 금액(백만원 정수)만 뽑아 JSON으로. 계산·단위변환 금지.\n"
        "판매비와관리비: 연구개발비 37,740,392 / 광고선전비 6,003,350",
        schema,
        max_tokens=200,
    )
    print("[extract]", out)
    print("[검증] 파싱:", json.loads(out))
    print(f"[usage] calls={llm.usage.calls} tokens={llm.usage.total_tokens} errors={llm.usage.errors}")
