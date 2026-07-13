"""
modules/disclosure/chat_server.py
공시 분석 챗봇 — Amazon Bedrock 기반 (근거 기반 / 환각 방지)

이전 버전은 Gemini를 사용했으나, DB 값과 실제 공시에 근거해서만 답하도록
Amazon Bedrock 기반으로 교체했다. 근거에 없는 내용은 지어내지 않고
"확인할 수 없습니다"라고 답한다(할루시네이션 방지).

근거 자료:
  1) 프론트가 넘겨준 "지금 보고 있는 공시"(제목·유형·일자·AI 요약)
  2) 이 모듈의 로컬 DB(disclosure.db) — 해당 기업의 최근 공시 + 최신 분기 재무

단독 실행:
    python -m modules.disclosure.chat_server   (포트 8001)

메인 앱에 붙이기:
    from modules.disclosure.chat_server import router as disclosure_chat_router
    app.include_router(disclosure_chat_router, prefix="/api")

환경 변수(.env):
    AWS_REGION                 Bedrock 리전 (예: us-east-1)
    BEDROCK_MODEL_ID           사용할 모델/inference profile ID
    AWS_BEARER_TOKEN_BEDROCK   Bedrock 인증 토큰 (boto3가 자동 인식) — 비밀값, 커밋 금지
    BEDROCK_MAX_TOKENS         답변 최대 토큰 (기본 1200)
"""

import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

load_dotenv()

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel

from .db import get_local_session
from .models import DisclosureLocal, FinancialStatement

AWS_REGION = os.getenv("AWS_REGION", "")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "")
BEDROCK_MAX_TOKENS = int(os.getenv("BEDROCK_MAX_TOKENS", "1200"))
# boto3가 AWS_BEARER_TOKEN_BEDROCK 환경변수를 자동 인식한다. 값은 로그에 남기지 않는다.
_BEDROCK_AUTH_SET = bool(
    os.getenv("AWS_BEARER_TOKEN_BEDROCK") or os.getenv("AWS_PROFILE")
)

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


# ── Bedrock 클라이언트 (지연 초기화) ──────────────────────────
_bedrock_client = None


def _get_bedrock():
    global _bedrock_client
    if _bedrock_client is None:
        import boto3
        from botocore.config import Config

        session = boto3.Session(region_name=AWS_REGION or None)
        _bedrock_client = session.client(
            "bedrock-runtime",
            config=Config(
                connect_timeout=10,
                read_timeout=120,
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )
    return _bedrock_client


def _converse(system: str, user_prompt: str) -> str:
    """Bedrock Converse 호출 — 한 번에 완성된 답을 반환."""
    if not BEDROCK_MODEL_ID:
        raise RuntimeError("BEDROCK_MODEL_ID가 .env에 설정되지 않았습니다.")
    client = _get_bedrock()
    try:
        response = client.converse(
            modelId=BEDROCK_MODEL_ID,
            system=[{"text": system}],
            messages=[{"role": "user", "content": [{"text": user_prompt}]}],
            inferenceConfig={"temperature": 0.1, "maxTokens": BEDROCK_MAX_TOKENS},
        )
        blocks = response["output"]["message"]["content"]
        return "".join(b.get("text", "") for b in blocks).strip()
    except Exception as exc:
        name = exc.__class__.__name__
        if name in {
            "AccessDeniedException",
            "UnauthorizedException",
        } or "AccessDenied" in str(exc):
            raise RuntimeError(
                "Bedrock 모델 호출 권한 또는 모델 액세스를 확인해 주세요."
            ) from exc
        raise RuntimeError(f"Bedrock 호출 실패: {name}") from exc


# ── 로컬 DB에서 근거 자료 조회 ────────────────────────────────
def _load_evidence(corp_name: str) -> str:
    """해당 기업의 최근 공시 + 최신 분기 재무를 근거 텍스트로 만든다."""
    if not corp_name:
        return ""
    session = get_local_session()
    try:
        lines: list[str] = []

        recent = (
            session.query(DisclosureLocal)
            .filter(DisclosureLocal.corp_name == corp_name)
            .order_by(DisclosureLocal.disclosure_date.desc())
            .limit(5)
            .all()
        )
        if recent:
            lines.append(f"[{corp_name} 최근 공시]")
            for d in recent:
                flag = " (중요)" if d.high_impact else ""
                lines.append(
                    f"- {d.disclosure_date or ''} {d.disclosure_type or ''} {d.title or ''}{flag}"
                )
                if d.summary:
                    lines.append(f"    요약: {d.summary}")

        fin = (
            session.query(FinancialStatement)
            .filter(FinancialStatement.corp_name == corp_name)
            .order_by(FinancialStatement.year.desc(), FinancialStatement.quarter.desc())
            .first()
        )
        if fin:
            lines.append("")
            lines.append(
                f"[{corp_name} 최신 분기 재무 — {fin.year}년 {fin.quarter}분기]"
            )

            def _num(label, value, unit=""):
                if value is not None:
                    lines.append(f"- {label}: {value}{unit}")

            _num("매출액", fin.revenue)
            _num("영업이익", fin.operating_income)
            _num("당기순이익", fin.net_income)
            _num("ROE", fin.roe, "%")
            _num("부채비율", fin.debt_ratio, "%")
            _num("영업이익률", fin.operating_margin, "%")

        return "\n".join(lines)
    finally:
        session.close()


def _build_system_prompt() -> str:
    return """당신은 한국 상장사 공시 분석 AI 어시스턴트입니다.
반드시 아래에 제공된 【근거 자료】와 【현재 공시】에 있는 내용만으로 답변하세요.

【답변 원칙】
- 근거에 없는 수치·사실은 절대 지어내지 마세요.
- 근거에서 확인되지 않는 내용은 "제공된 자료에서는 확인할 수 없습니다"라고 답하세요.
- 숫자는 근거에 나온 값을 그대로 인용하고, 임의로 계산하거나 바꾸지 마세요.
- 전문 용어는 반드시 쉬운 말로 풀어 설명하세요.
- 답변은 핵심만 3~5문장 이내로, 한국어로 작성하세요.
- 투자 조언이 아닌 정보 제공 목적임을 명심하세요."""


def _build_user_prompt(req: ChatRequest, evidence: str) -> str:
    parts: list[str] = []

    parts.append("【현재 보고 있는 공시】")
    parts.append(f"- 기업명: {req.corp_name or '-'}")
    parts.append(f"- 공시 제목: {req.disc_title or '-'}")
    parts.append(f"- 공시 유형: {req.disc_type or '-'}")
    parts.append(f"- 공시 일자: {req.disc_date or '-'}")
    if req.summary:
        parts.append(f"- AI 사전 분석 요약: {req.summary}")

    if evidence:
        parts.append("")
        parts.append("【근거 자료 — 이 기업 DB】")
        parts.append(evidence)

    # 직전 대화 최대 5턴만 포함 (맥락 유지 + 비용 절감)
    if req.history:
        parts.append("")
        parts.append("【이전 대화】")
        for h in req.history[-5:]:
            role = "사용자" if h.get("role") == "user" else "어시스턴트"
            parts.append(f"{role}: {h.get('content', '')}")

    parts.append("")
    parts.append("【사용자 질문】")
    parts.append(req.question)
    parts.append("")
    parts.append(
        "위 근거 자료에 근거해서만 답하세요. 근거에 없으면 확인할 수 없다고 답하세요."
    )
    return "\n".join(parts)


async def _stream_answer(req: ChatRequest):
    """Bedrock 답변을 SSE 형식으로 흘려보낸다 (기존 프론트 계약 유지)."""
    try:
        evidence = await run_in_threadpool(_load_evidence, req.corp_name)
        system_prompt = _build_system_prompt()
        user_prompt = _build_user_prompt(req, evidence)
        answer = await run_in_threadpool(_converse, system_prompt, user_prompt)
    except Exception as exc:
        err = json.dumps({"error": str(exc)}, ensure_ascii=False)
        yield f"data: {err}\n\n"
        yield "data: [DONE]\n\n"
        return

    # Bedrock은 한 번에 답을 주므로, 프론트의 스트리밍 UI를 위해 잘게 나눠 보낸다.
    step = 40
    for i in range(0, len(answer), step):
        piece = answer[i : i + step]
        data = json.dumps({"text": piece}, ensure_ascii=False)
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
    return {
        "status": "ok",
        "provider": "bedrock",
        "model": BEDROCK_MODEL_ID,
        "region": AWS_REGION,
        "auth_set": _BEDROCK_AUTH_SET,
    }


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

    _app = FastAPI(title="DiscloseAI Chat (Bedrock)")
    _app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["POST", "GET"],
        allow_headers=["*"],
    )
    _app.include_router(router)

    port = int(os.getenv("CHAT_SERVER_PORT", "8001"))
    print(f"[DiscloseAI Chat / Bedrock] 서버 시작 → http://localhost:{port}")
    uvicorn.run(_app, host="0.0.0.0", port=port, log_level="warning")
