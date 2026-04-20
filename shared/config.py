"""환경변수 로드 — 모든 모듈에서 공유"""

import os
from dotenv import load_dotenv

load_dotenv()

# DART OpenAPI
DART_API_KEY = os.getenv("DART_API_KEY", "")

# Supabase (PostgreSQL)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# DB 연결 문자열 (Supabase PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL", "")
