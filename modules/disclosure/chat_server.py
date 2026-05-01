"""
modules/disclosure/chat_server.py
공시 분석 챗봇 — Gemini 2.5 Flash 기반

단독 실행:
    python -m modules.disclosure.chat_server   (포트 8001)

메인 앱에 붙이기:
    from modules.disclosure.chat_server import router as disclosure_chat_router
    app.include_router(disclosure_chat_router, prefix="/api")
"""

import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash-preview-04-17"

_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# 메인 앱에서 include_router()로 붙일 수 있는 라우터
router = APIRouter(prefix="/disclosure", tags=["disclosure-chat"])


class ChatRequest(BaseModel):
    question: str
    corp_name: str = ""
    disc_title: str = ""
    disc_type: str = ""
    disc_date: str = ""
    summary: str = ""
    history: list = []


def _build_system_prompt(
    corp_name: str, disc_title: str, disc_type: str, disc_date: str, summary: str
) -> str:
    context_block = ""
    if summary:
        context_block = f"""
아래는 이 공시에 대한 AI 사전 분석 요약입니다. 이를 참고하여 답변하세요.

--- 사전 분석 ---
{summary}
--- 끝 ---
"""
    return f"""당신은 한국 주식시장 공시 전문 AI 어시스턴트입니다.
사용자가 특정 공시에 대해 궁금한 점을 질문하면, 쉽고 명확하게 한국어로 답변하세요.

【현재 공시 정보】
- 기업명: {corp_name}
- 공시 제목: {disc_title}
- 공시 유형: {disc_type}
- 공시 일자: {disc_date}
{context_block}
【답변 원칙】
- 원문이나 분석에 명시된 내용은 근거를 들어 답변하세요.
- 확인되지 않은 추론은 반드시 "추정컨대" 또는 "~일 가능성이 있습니다"로 시작하세요.
- 전문 용어는 반드시 쉬운 말로 풀어 설명하세요.
- 투자 조언이 아닌 정보 제공 목적임을 명심하세요.
- 답변은 간결하게, 핵심만 3~5문장 이내로 작성하세요."""


async def _stream_gemini(system_prompt: str, history: list, question: str):
    if not _client:
        yield "data: GEMINI_API_KEY가 .env에 설정되지 않았습니다.\n\n"
        yield "data: [DONE]\n\n"
        return

    gemini_history = []
    for h in history:
        role = "user" if h.get("role") == "user" else "model"
        gemini_history.append(
            types.Content(role=role, parts=[types.Part(text=h.get("content", ""))])
        )

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=0.3,
    )

    try:
        chat = _client.chats.create(
            model=GEMINI_MODEL, history=gemini_history, config=config
        )
        for chunk in chat.send_message_stream(question):
            if chunk.text:
                data = json.dumps({"text": chunk.text}, ensure_ascii=False)
                yield f"data: {data}\n\n"
    except Exception as e:
        err = json.dumps({"error": str(e)}, ensure_ascii=False)
        yield f"data: {err}\n\n"

    yield "data: [DONE]\n\n"


@router.post("/chat")
async def chat(req: ChatRequest):
    system_prompt = _build_system_prompt(
        req.corp_name, req.disc_title, req.disc_type, req.disc_date, req.summary
    )
    return StreamingResponse(
        _stream_gemini(system_prompt, req.history, req.question),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/health")
def health():
    return {"status": "ok", "model": GEMINI_MODEL, "key_set": bool(GEMINI_API_KEY)}


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

    _app = FastAPI(title="DiscloseAI Chat")
    _app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["POST", "GET"],
        allow_headers=["*"],
    )
    _app.include_router(router)

    port = int(os.getenv("CHAT_SERVER_PORT", "8001"))
    print(f"[DiscloseAI Chat] 서버 시작 → http://localhost:{port}")
    uvicorn.run(_app, host="0.0.0.0", port=port, log_level="warning")
