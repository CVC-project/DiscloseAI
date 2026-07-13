"""
modules/disclosure/chat_server.py
공시 분석 챗봇 — DartChatbot(OpenDART RAG · Amazon Bedrock) 연동 어댑터

기존 Gemini 챗봇을, 별도로 운영되는 DartChatbot 서비스에 연결한다.
DartChatbot는 49개사 공시·정형 재무에 **근거해서만** 답한다(할루시네이션 방지):
숫자는 정형 데이터에서, 서술은 실제 공시 문단에서 찾고, 없으면 "확인할 수 없습니다".

이 파일은 프론트 계약만 유지하고(POST /disclosure/chat, SSE), 질문을
DartChatbot의 POST /api/chat 로 전달한 뒤 답변을 SSE로 흘려보낸다.
DartChatbot의 엔진·1.27GB 데이터·Bedrock 설정은 이 저장소가 아니라
DartChatbot 서비스 쪽에 있으므로, 이 모듈에는 대용량 데이터가 들어오지 않는다.

단독 실행:
    python -m modules.disclosure.chat_server   (포트 8001)

메인 앱에 붙이기:
    from modules.disclosure.chat_server import router as disclosure_chat_router
    app.include_router(disclosure_chat_router, prefix="/api")

전제:
    DartChatbot 서비스가 실행 중이어야 한다 (기본 http://localhost:8000).
    실행법은 DartChatbot 저장소 참조(APP_MODE=bedrock uvicorn dart_chat.api:app ...).

환경 변수:
    DART_CHATBOT_URL   DartChatbot 베이스 URL (기본 http://localhost:8000)
"""

import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

load_dotenv()

import requests
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel

DART_CHATBOT_URL = os.getenv("DART_CHATBOT_URL", "http://localhost:8000").rstrip("/")

# 메인 앱에서 include_router()로 붙일 수 있는 라우터 (기존과 동일한 경로 유지)
router = APIRouter(prefix="/disclosure", tags=["disclosure-chat"])


class ChatRequest(BaseModel):
    question: str
    corp_name: str = ""
    disc_title: str = ""
    disc_type: str = ""
    disc_date: str = ""
    summary: str = ""
    history: list = []


def _build_messages(req: ChatRequest) -> list[dict]:
    """DartChatbot 계약({messages:[{role,content}]})으로 변환.

    DartChatbot는 질문 텍스트에서 회사를 해석하므로, 회사명이 질문에 없으면
    앞에 붙여 회사가 인식되도록 한다. 마지막 메시지는 반드시 user 여야 한다.
    """
    messages: list[dict] = []
    for h in req.history[-6:]:
        role = "user" if h.get("role") == "user" else "assistant"
        content = (h.get("content") or "").strip()
        if content:
            messages.append({"role": role, "content": content})

    question = req.question.strip()
    if req.corp_name and req.corp_name not in question:
        question = f"{req.corp_name} {question}"
    messages.append({"role": "user", "content": question})
    return messages


def _call_dartchatbot(req: ChatRequest) -> str:
    """DartChatbot에 질문을 전달하고 근거 기반 답변 텍스트를 받는다."""
    payload = {"messages": _build_messages(req)}
    resp = requests.post(f"{DART_CHATBOT_URL}/api/chat", json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return (data.get("answer") or "").strip() or "(답변이 비어 있습니다.)"


async def _stream_answer(req: ChatRequest):
    """DartChatbot 답변을 SSE 형식으로 흘려보낸다 (기존 프론트 계약 유지)."""
    try:
        answer = await run_in_threadpool(_call_dartchatbot, req)
    except Exception as exc:
        err = json.dumps({"error": f"DartChatbot 호출 실패: {exc}"}, ensure_ascii=False)
        yield f"data: {err}\n\n"
        yield "data: [DONE]\n\n"
        return

    # DartChatbot은 한 번에 답을 주므로, 프론트의 스트리밍 UI를 위해 잘게 나눠 보낸다.
    step = 40
    for i in range(0, len(answer), step):
        data = json.dumps({"text": answer[i : i + step]}, ensure_ascii=False)
        yield f"data: {data}\n\n"
    yield "data: [DONE]\n\n"


@router.post("/chat")
async def chat(req: ChatRequest):
    return StreamingResponse(
        _stream_answer(req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/health")
def health():
    info = {"status": "ok", "provider": "dartchatbot", "url": DART_CHATBOT_URL}
    try:
        r = requests.get(f"{DART_CHATBOT_URL}/api/health", timeout=5)
        info["dartchatbot"] = r.json() if r.ok else {"status_code": r.status_code}
    except Exception as exc:
        info["dartchatbot"] = {"error": str(exc)}
    return info


@router.get("/report", response_class=HTMLResponse)
def serve_report():
    report_path = Path(__file__).parent / "report_latest.html"
    if report_path.exists():
        return HTMLResponse(content=report_path.read_text(encoding="utf-8"))
    return HTMLResponse(
        content="<p>report_latest.html 없음. 먼저 generate_report.py를 실행하세요.</p>"
    )


# ── 단독 실행 시 ──────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    _app = FastAPI(title="DiscloseAI Chat (DartChatbot adapter)")
    _app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["POST", "GET"],
        allow_headers=["*"],
    )
    _app.include_router(router)

    port = int(os.getenv("CHAT_SERVER_PORT", "8001"))
    print(
        f"[DiscloseAI Chat / DartChatbot adapter] 서버 시작 → http://localhost:{port}"
    )
    print(f"  DartChatbot 연결 대상: {DART_CHATBOT_URL}")
    uvicorn.run(_app, host="0.0.0.0", port=port, log_level="warning")
