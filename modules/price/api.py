"""Timemachine Chat API — Gemini가 투자 시뮬레이션 대화를 동적으로 생성"""

import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from google import genai
from google.genai import types
from google.genai.errors import ServerError

load_dotenv(Path(__file__).parent.parent.parent / ".env")

app = FastAPI(title="DiscloseAI Timemachine API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

_client: genai.Client | None = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
    return _client


# 시나리오 데이터 — 답(answer, changePct)은 서버사이드에서만 보관
SCENARIOS: dict[int, dict] = {
    1: {
        "company": "LG화학",
        "ticker": "051910",
        "era": "2020년 9월 17일",
        "category": "물적분할",
        "desc": "배터리 사업부 물적분할·별도 상장 추진 공시",
        "background": (
            "LG화학 배터리 사업부 물적분할로 LG에너지솔루션 설립. "
            "당시 LG화학 주가 약 82만 원, 연초 대비 +290%. "
            "배터리 사업이 시총의 약 65% 차지. "
            "물적분할 후 모회사는 자회사 지분만 보유하는 지주회사 구조로 전환됨. "
            "한국 시장에서 지주회사에는 통상 20~40% 할인 적용."
        ),
        "answer": "악재",
        "changePct": -11.2,
        "kospiPct": -6.7,
        "window": "공시 후 5거래일",
        "insight": (
            "모회사 디스카운트의 속도. 시장은 배터리가 분리되는 순간 즉시 LG화학에 할인을 적용했습니다. "
            "이후 LG에너지솔루션이 2022년 1월 시총 100조로 상장됐지만, LG화학은 물적분할 전 주가를 회복하지 못했습니다."
        ),
        "lesson": (
            "물적분할은 회사 자산 자체는 사라지지 않지만 기존 주주의 직접 권리가 희석된다. "
            "한국 시장에서 물적분할 공시는 단기 악재 패턴이 반복된다."
        ),
    },
    2: {
        "company": "SK하이닉스",
        "ticker": "000660",
        "era": "2020년 10월 20일",
        "category": "대형M&A",
        "desc": "인텔 낸드 플래시 사업부 10.2조 원 인수 결정 공시",
        "background": (
            "SK하이닉스가 인텔의 낸드·SSD 사업부를 약 90억 달러(10.2조 원)에 인수. "
            "당시 낸드 점유율 약 11%, 인수 후 약 20% 예상. "
            "2020년 예상 영업이익 약 5조 원(인수금액 ≈ 2년치 영업이익). "
            "낸드 가격은 2018년 고점 대비 40% 낮은 상태. "
            "AI·HBM 수요 폭발은 당시 시장이 전혀 예상하지 못한 변수."
        ),
        "answer": "악재",
        "changePct": -5.1,
        "kospiPct": -0.7,
        "window": "공시 후 5거래일",
        "insight": (
            "AI 수요 폭발은 당시 아무도 알 수 없었습니다. "
            "2024년 SK하이닉스는 HBM·낸드 수혜로 역대 최고 실적을 기록했고, "
            "이 인수는 '최고의 M&A' 중 하나로 재평가됩니다. 단기 악재가 장기 최고의 투자였던 사례입니다."
        ),
        "lesson": (
            "대형 M&A는 단기 재무 부담으로 주가가 하락해도 장기적으로 완전히 다른 결과를 낳을 수 있다. "
            "'불황에 사는' 전략의 진짜 가치는 3~5년 후에 드러난다."
        ),
    },
    3: {
        "company": "HD현대중공업",
        "ticker": "009540",
        "era": "2026년 4월 22일",
        "category": "대형수주",
        "desc": "미국 데이터센터 발전설비 6,200억 원 수주 공시",
        "background": (
            "HD현대중공업이 미국 에너지 인프라 기업 에이페리온 에너지 그룹(AEG)으로부터 "
            "데이터센터용 발전설비를 6,200억 원에 수주. 연간 매출의 약 6% 규모. "
            "힘센엔진(선박용 엔진의 육상 발전 전용 제품) 활용. "
            "AI 데이터센터 전력 수요 급증, 미국 전력망 부족 심화 상황. "
            "조선사에서 AI 에너지 인프라 플레이어로의 섹터 리레이팅 내러티브."
        ),
        "answer": "수혜",
        "changePct": 12.6,
        "kospiPct": 2.4,
        "window": "공시 후 3거래일",
        "insight": (
            "섹터 리레이팅 내러티브. 시장은 단순히 6,200억 원의 금액에 반응한 게 아니라 "
            "'HD현대중공업 = AI 에너지 인프라 플레이어'라는 새로운 스토리에 반응했습니다."
        ),
        "lesson": (
            "대형 수주는 금액 자체보다 '어느 시장에 진입했는가'라는 내러티브가 주가를 더 크게 움직이는 경우가 많다. "
            "섹터 리레이팅 기대가 실적보다 먼저 반영된다."
        ),
    },
}


def build_system(sc: dict, user_stance: str | None) -> str:
    stance_line = f"\n사용자의 초기 판단: {user_stance}" if user_stance else ""

    return (
        f"당신은 '공시 시간여행' 금융 교육 AI입니다.\n"
        f"사용자가 실제 한국 상장사 공시가 있었던 날의 투자자 역할을 체험하고 있습니다.\n\n"
        f"[시나리오]\n"
        f"종목: {sc['company']} ({sc['ticker']})\n"
        f"공시일: {sc['era']}\n"
        f"공시 내용: {sc['desc']}\n"
        f"배경 정보: {sc['background']}"
        f"{stance_line}\n\n"
        f"[대화 가이드]\n"
        f"- 사용자의 발언에 관련된 재무 수치, 시장 데이터, 역사적 사례, 업종 맥락을 최대한 구체적으로 끌어와서 설명하세요\n"
        f"- 단순 질문 하나로 끝내지 말고, 충분한 정보와 분석을 제공한 뒤 마지막에 질문을 던지세요\n"
        f"- 수치, 날짜, 비율, 회사명, 사건명 등 구체적인 팩트를 적극 활용하세요\n"
        f"- 재무 변수, 시장 컨텍스트, 역사적 선례, 수급 분석, 글로벌 트렌드 등 다양한 각도를 탐구하세요\n"
        f"- 사용자가 이미 언급한 내용은 반복하지 말고 새로운 시각과 정보를 추가하세요\n"
        f"- 실제 결과({sc['answer']}, {sc['changePct']}% 변동)는 절대 사전에 공개하지 마세요\n"
        f"- 투자 조언이 아닌 '과거 통계 기반 학습 시뮬레이션'임을 인지하세요\n"
        f"- 한국어로만 답변하세요\n"
        f"- 이모지는 최대 2개만 사용하세요\n"
        f"- 길이 제한 없이 필요한 만큼 충분히 길게 답변하세요"
    )


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    scenario_id: int
    turn: int
    messages: list[Message]
    user_stance: str | None = None


class ChatResponse(BaseModel):
    reply: str
    chips: list[str] = []
    chips_label: str = "어떻게 생각하세요?"


@app.post("/timemachine/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    sc = SCENARIOS.get(req.scenario_id)
    if not sc:
        return ChatResponse(reply="시나리오를 찾을 수 없습니다.", chips=[])

    system = build_system(sc, req.user_stance)

    contents = [
        types.Content(
            role="user" if m.role == "user" else "model",
            parts=[types.Part(text=m.content)],
        )
        for m in req.messages
    ]
    cfg = types.GenerateContentConfig(
        system_instruction=system,
        max_output_tokens=8192,
    )
    for model in ("gemini-2.5-flash", "gemini-2.5-flash-lite"):
        try:
            response = get_client().models.generate_content(
                model=model, contents=contents, config=cfg
            )
            reply = response.text
            break
        except ServerError:
            continue
    else:
        reply = "일시적으로 AI 서버가 혼잡합니다. 잠시 후 다시 시도해주세요."

    return ChatResponse(reply=reply)


@app.get("/timemachine/scenario/{scenario_id}/reveal")
def reveal(scenario_id: int) -> dict:
    sc = SCENARIOS.get(scenario_id)
    if not sc:
        return {"error": "not found"}
    return {
        "answer": sc["answer"],
        "changePct": sc["changePct"],
        "kospiPct": sc["kospiPct"],
        "window": sc["window"],
        "insight": sc["insight"],
        "lesson": sc["lesson"],
    }


@app.get("/timemachine")
def timemachine_ui() -> FileResponse:
    return FileResponse(Path(__file__).parent / "timemachine.html")

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", port=8001, reload=True)
