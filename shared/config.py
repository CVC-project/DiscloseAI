"""환경변수 로드 — 모든 모듈에서 공유"""

import os
from dotenv import load_dotenv

load_dotenv()

# DART OpenAPI
DART_API_KEY = os.getenv("DART_API_KEY", "")

# 공공데이터포털 (data.go.kr) — 공정위 대규모기업집단 OpenAPI 공통 인증키
FTC_API_KEY = os.getenv("FTC_API_KEY", "")

# 한국은행 ECOS OpenAPI (https://ecos.bok.or.kr/api) — 산업연관표 등
BOK_ECOS_API_KEY = os.getenv("BOK_ECOS_API_KEY", "")

# Supabase (PostgreSQL)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# DB 연결 문자열 (Supabase PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL", "")

# report 모듈 LLM 서빙 (Phase 4 — A100 SGLang, OpenAI 호환). DOSSIER_TABS_PLAN R4 착수 조건.
#   REPORT_LLM_BASE_URL : SGLang 엔드포인트 URL  (예: http://<GPU_IP>:30000/v1  ← SGLang 기본 포트 30000)
#   REPORT_LLM_API_KEY  : 엔드포인트 인증키        (기본 임의값 가능, 예: "EMPTY")
#   REPORT_LLM_MODEL    : 요청 모델명             (예: Qwen/Qwen3.5-35B-A3B ← 단일 A100 80GB 권장. 최종은 /galaxy-bench 판정)
# 서버: `python -m sglang.launch_server --model <REPORT_LLM_MODEL> --port 30000` (구조화 출력=xgrammar).
# ⚠️ SSH 접속정보(IP·ID·PW)는 여기 넣지 않는다 — 서버 로그인용일 뿐. 여긴 SGLang 엔드포인트 URL·키만.
REPORT_LLM_BASE_URL = os.getenv("REPORT_LLM_BASE_URL", "")
REPORT_LLM_API_KEY = os.getenv("REPORT_LLM_API_KEY", "")
REPORT_LLM_MODEL = os.getenv("REPORT_LLM_MODEL", "Qwen/Qwen3.5-35B-A3B")
