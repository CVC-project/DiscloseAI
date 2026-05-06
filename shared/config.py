"""환경변수 로드 — 모든 모듈에서 공유"""

import os
from dotenv import load_dotenv

load_dotenv()

# DART OpenAPI
DART_API_KEY = os.getenv("DART_API_KEY", "")

# 공공데이터포털 (data.go.kr) — 공정위 대규모기업집단 OpenAPI 공통 인증키
FTC_API_KEY = os.getenv("FTC_API_KEY", "")

# Supabase (PostgreSQL)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# DB 연결 문자열 (Supabase PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL", "")
