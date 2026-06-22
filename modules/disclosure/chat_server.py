"""
Local AI chat proxy for DiscloseAI.

The browser must never call Bedrock directly. This server reads the Bedrock
Bearer token from the local .env file and exposes safe local endpoints for the
prototype UI.

Run:
    python -m modules.disclosure.chat_server

Endpoints:
    POST /disclosure/chat   SSE-compatible disclosure chat
    POST /integration/chat  JSON chat for integration v1/v2 dashboards
    GET  /integration/health
    GET  /disclosure/health
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

BEDROCK_API_KEY = os.getenv("BEDROCK_API_KEY", "")
BEDROCK_REGION = os.getenv("BEDROCK_REGION", "us-east-1")
BEDROCK_DEFAULT_MODEL = os.getenv(
    "BEDROCK_DEFAULT_MODEL", "anthropic.claude-haiku-4-5-20251001-v1:0"
)
BEDROCK_DEEP_MODEL = os.getenv("BEDROCK_DEEP_MODEL", "anthropic.claude-sonnet-4-6")
BEDROCK_TIMEOUT = float(os.getenv("BEDROCK_TIMEOUT", "45"))
# 시스템 프롬프트가 "8~15문장, 200~400자, 더 길어도 좋음"을 요구하므로 700은 잘림.
BEDROCK_MAX_TOKENS = int(os.getenv("BEDROCK_MAX_TOKENS", "1800"))


disclosure_router = APIRouter(prefix="/disclosure", tags=["disclosure-chat"])
integration_router = APIRouter(prefix="/integration", tags=["integration-chat"])


class DisclosureChatRequest(BaseModel):
    question: str
    corp_name: str = ""
    disc_title: str = ""
    disc_type: str = ""
    disc_date: str = ""
    summary: str = ""
    history: list[dict[str, Any]] = Field(default_factory=list)


class IntegrationChatRequest(BaseModel):
    question: str
    system_prompt: str = ""
    history: list[dict[str, Any]] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    model: str = ""


def _mask_secret(text: str) -> str:
    text = re.sub(r"ABSK[A-Za-z0-9+/=]+", "ABSK***MASKED***", text)
    text = re.sub(r"(AKIA|ASIA)[A-Z0-9]{12,}", r"\1***MASKED***", text)
    text = re.sub(r"Bearer\s+[A-Za-z0-9+/=._-]+", "Bearer ***MASKED***", text)
    return text


def _bedrock_model_id(model: str | None = None) -> str:
    model_id = (model or BEDROCK_DEFAULT_MODEL).strip()
    if model_id.startswith(("us.", "global.", "arn:")):
        return model_id
    return f"us.{model_id}"


def _bedrock_url(model: str | None = None) -> str:
    return (
        f"https://bedrock-runtime.{BEDROCK_REGION}.amazonaws.com"
        f"/model/{_bedrock_model_id(model)}/converse"
    )


def _history_to_bedrock(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for item in history[-12:]:
        raw_role = str(item.get("role") or item.get("who") or "").lower()
        if raw_role in {"model", "assistant", "ai"}:
            role = "assistant"
        elif raw_role == "user":
            role = "user"
        else:
            continue

        text = item.get("text")
        if text is None:
            text = item.get("content")
        if text is None and isinstance(item.get("parts"), list):
            parts = item.get("parts") or []
            text = "\n".join(
                str(p.get("text", "")) for p in parts if isinstance(p, dict)
            )
        text = str(text or "").strip()
        if not text:
            continue
        messages.append({"role": role, "content": [{"text": text[:4000]}]})
    return messages


def _extract_bedrock_text(data: dict[str, Any]) -> str:
    parts = data.get("output", {}).get("message", {}).get("content", [])
    texts = [p.get("text", "") for p in parts if isinstance(p, dict) and p.get("text")]
    return "\n".join(texts).strip()


def _call_bedrock(
    *,
    question: str,
    system_prompt: str,
    history: list[dict[str, Any]] | None = None,
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float = 0.35,
) -> dict[str, Any]:
    if not BEDROCK_API_KEY:
        raise RuntimeError("BEDROCK_API_KEY is not set in local .env")

    messages = _history_to_bedrock(history or [])
    messages.append({"role": "user", "content": [{"text": question[:6000]}]})

    body = {
        "system": [{"text": system_prompt}],
        "messages": messages,
        "inferenceConfig": {
            "maxTokens": max_tokens if max_tokens is not None else BEDROCK_MAX_TOKENS,
            "temperature": temperature,
        },
    }

    response = requests.post(
        _bedrock_url(model),
        headers={
            "Authorization": f"Bearer {BEDROCK_API_KEY}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=BEDROCK_TIMEOUT,
    )

    if response.status_code >= 400:
        detail = _mask_secret(response.text[:1500])
        raise RuntimeError(f"Bedrock HTTP {response.status_code}: {detail}")

    data = response.json()
    return {
        "text": _extract_bedrock_text(data),
        "model": _bedrock_model_id(model),
        "usage": data.get("usage", {}),
        "stopReason": data.get("stopReason"),
    }


def _base_system_prompt() -> str:
    return """당신은 DiscloseAI의 재무 분석 어시스턴트입니다.
대상 사용자는 주식 투자가 처음인 초보 개인투자자입니다.

답변 원칙:
- 한국어로 친절하고 천천히 설명합니다.
- 어려운 재무·회계 용어는 쉬운 말로 한 줄 풀이를 붙입니다.
- 기업 데이터가 주어지면 그 숫자를 근거로 설명합니다.
- 모르는 내용은 추측하지 말고 확인이 필요하다고 말합니다.
- "사세요", "파세요", "매수 추천" 같은 투자 조언은 금지합니다.
- 항상 과거 공시와 재무정보 기반 참고 정보라고 표현합니다."""


def _build_disclosure_prompt(req: DisclosureChatRequest) -> str:
    context = ""
    if req.summary:
        context = f"""
아래는 이 공시에 대한 사전 분석 요약입니다.

--- 사전 분석 ---
{req.summary}
--- 끝 ---
"""
    return f"""{_base_system_prompt()}

현재 사용자가 보고 있는 공시:
- 기업명: {req.corp_name or "-"}
- 공시 제목: {req.disc_title or "-"}
- 공시 유형: {req.disc_type or "-"}
- 공시 일자: {req.disc_date or "-"}
{context}
공시 해석 시에는 공시 원문과 사전 분석에서 확인되는 내용만 근거로 삼으세요."""


def _build_integration_prompt(req: IntegrationChatRequest) -> str:
    prompt = _base_system_prompt()
    if req.system_prompt:
        prompt += "\n\n화면에서 전달된 현재 맥락:\n" + req.system_prompt[:6000]
    if req.context:
        prompt += (
            "\n\n구조화된 화면 컨텍스트 JSON:\n"
            + json.dumps(req.context, ensure_ascii=False)[:4000]
        )
    return prompt


async def _stream_answer(answer_fn):
    try:
        result = answer_fn()
        yield f"data: {json.dumps({'text': result['text']}, ensure_ascii=False)}\n\n"
        if result.get("usage"):
            yield f"data: {json.dumps({'usage': result['usage']}, ensure_ascii=False)}\n\n"
    except Exception as exc:  # pragma: no cover - exercised through integration
        yield f"data: {json.dumps({'error': _mask_secret(str(exc))}, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"


@disclosure_router.post("/chat")
async def disclosure_chat(req: DisclosureChatRequest):
    return StreamingResponse(
        _stream_answer(
            lambda: _call_bedrock(
                question=req.question,
                system_prompt=_build_disclosure_prompt(req),
                history=req.history,
                model=BEDROCK_DEFAULT_MODEL,
            )
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@integration_router.post("/chat")
def integration_chat(req: IntegrationChatRequest):
    return _call_bedrock(
        question=req.question,
        system_prompt=_build_integration_prompt(req),
        history=req.history,
        model=req.model or BEDROCK_DEFAULT_MODEL,
    )


@disclosure_router.get("/health")
@integration_router.get("/health")
def health():
    return {
        "status": "ok",
        "provider": "bedrock",
        "model": _bedrock_model_id(BEDROCK_DEFAULT_MODEL),
        "deep_model": _bedrock_model_id(BEDROCK_DEEP_MODEL),
        "region": BEDROCK_REGION,
        "key_set": bool(BEDROCK_API_KEY),
        "max_tokens": BEDROCK_MAX_TOKENS,
    }


@disclosure_router.get("/report", response_class=HTMLResponse)
def serve_report():
    report_path = Path(__file__).parent / "report_latest.html"
    if report_path.exists():
        return HTMLResponse(content=report_path.read_text(encoding="utf-8"))
    return HTMLResponse(
        content="<p>report_latest.html not found. Run generate_report.py first.</p>"
    )


def create_app() -> FastAPI:
    app = FastAPI(title="DiscloseAI Bedrock Chat")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["POST", "GET", "OPTIONS"],
        allow_headers=["*"],
    )
    app.include_router(disclosure_router)
    app.include_router(integration_router)
    return app


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("CHAT_SERVER_PORT", "8001"))
    print(f"[DiscloseAI Chat] Bedrock proxy on http://localhost:{port}")
    uvicorn.run(create_app(), host="0.0.0.0", port=port, log_level="warning")
