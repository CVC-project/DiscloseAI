"""기업명 정규화 공용 유틸.

ingest·transform 양쪽에서 import — 순환 의존 회피를 위해 별도 모듈.
정규화 규칙은 설계 변경 시 `modules/relation/transform/CLAUDE.md`에도 반영.
"""

from __future__ import annotations

import re

# DART/FTC 정식 법인명 vs KRX 약칭 매핑 (normalize 후 key·value 모두 소문자+공백없음 형태)
#
# 공정위 FTC API는 정식 법인명을 사용 (예: "삼성에스디아이", "에스케이하이닉스").
# top50.csv는 KRX 약칭 (예: "삼성SDI", "SK하이닉스"). 둘을 일치시키기 위한 매핑.
#
# ticker_map은 top50 corp_name을 normalize한 결과를 key로 가지므로,
# ALIAS의 value도 동일하게 normalize된 소문자·공백제거 형태여야 매칭됨.
NAME_ALIASES: dict[str, str] = {
    "현대자동차": "현대차",
    # SK 그룹
    "에스케이하이닉스": "sk하이닉스",
    "에스케이스퀘어": "sk스퀘어",
    "에스케이이노베이션": "sk이노베이션",
    "에스케이텔레콤": "sk텔레콤",
    "에스케이": "sk",
    # LG 그룹
    "엘지에너지솔루션": "lg에너지솔루션",
    "엘지화학": "lg화학",
    "엘지전자": "lg전자",
    # HD현대 그룹
    "에이치디현대중공업": "hd현대중공업",
    "에이치디현대일렉트릭": "hd현대일렉트릭",
    "에이치디한국조선해양": "hd한국조선해양",
    "에이치디현대": "hd현대",
    # 삼성 그룹 (정식 법인명 → 약칭)
    "삼성에스디아이": "삼성sdi",
    "삼성생명보험": "삼성생명",
    "삼성화재해상보험": "삼성화재",
    # 구사명 → 현재 사명 (FN-013: registry는 현재 사명만 보유 — 과거 연도 공시의
    # 구사명 링킹은 여기 별칭으로 흡수. 사명 변경 발견 시마다 추가)
    "에스씨엠생명과학": "풍전약품",  # 2025 풍전약품 인수 후 개명 (298060)
    # 기타
    "네이버": "naver",
    "포스코홀딩스": "posco홀딩스",
    "엘에스일렉트릭": "lselectric",  # top50 "LS ELECTRIC" normalize → "lselectric"
    "케이티앤지": "kt&g",
    "한국항공우주산업": "한국항공우주",
}

# 제거 대상 법인 접미어·접두어 (소문자 비교)
_LEGAL_SUFFIXES = (
    "주식회사",
    "(주)",
    "㈜",
    "co.,ltd.",
    "co.,ltd",
    "co.ltd.",
    "co.ltd",
    "co.,",
    "co.",
    "co",
    "ltd.",
    "ltd",
    "inc.",
    "inc",
    "corporation",
    "corp.",
    "corp",
)

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_company_name(name: str | None) -> str:
    """(주)·주식회사·공백·영문 법인 접미어 제거 후 별칭 매핑 적용.

    규칙 (순서대로):
      1. 양끝 공백 제거
      2. 법인 접미어/접두어 제거 (대소문자 무관, 공백 무관)
      3. 모든 공백 제거
      4. NAME_ALIASES 적용

    None/빈 문자열 → 빈 문자열 반환.
    """
    if not name:
        return ""

    s = name.strip()
    lower = s.lower()

    # 법인 접미어/접두어 제거
    changed = True
    while changed:
        changed = False
        lower = lower.strip()
        for suffix in _LEGAL_SUFFIXES:
            if lower.endswith(suffix):
                lower = lower[: -len(suffix)].rstrip(" ,.")
                changed = True
            if lower.startswith(suffix):
                lower = lower[len(suffix) :].lstrip(" ,.")
                changed = True

    # 원본 대소문자 보존하면서 제거된 길이만큼 자르기
    # (lower는 정규화 비교용이고, 실제 반환은 원본 대소문자 유지)
    # 간단하게: lower 결과를 다시 원본 기준으로 앞뒤 재매칭
    # → MVP는 한글 위주이므로 대소문자 문제 적음. lower 결과를 대체로 사용.
    # 단, 영문 일부가 포함되면 원본 보존이 의미 있음.
    # 여기서는 lower 결과 그대로 사용 (대소문자는 alias 매핑에서 조정).
    s = lower

    # 모든 공백 제거
    s = _WHITESPACE_RE.sub("", s)

    # 별칭 매핑 (key/value 모두 lower+공백제거로 정규화 후 비교)
    def _norm(x: str) -> str:
        return _WHITESPACE_RE.sub("", x.lower())

    s_norm = _norm(s)
    for alias_key, alias_value in NAME_ALIASES.items():
        if s_norm == _norm(alias_key):
            return _norm(alias_value)

    return s_norm


def build_ticker_map(top50_csv_path) -> dict[str, str]:
    """top50.csv의 corp_name을 정규화하여 ticker로 매핑한 dict 반환.

    ★U1: 신규 코드는 build_ticker_map_from_registry()를 쓸 것 — 이 함수는
    top50.csv 기반 레거시 경로 호환용으로 유지(과도기, universe/PLAN.md U-D5).

    Returns: {normalized_name: ticker, ...}
    """
    import csv

    ticker_map: dict[str, str] = {}
    with open(top50_csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("corp_name", "").strip()
            ticker = row.get("ticker", "").strip()
            if name and ticker:
                ticker_map[normalize_company_name(name)] = ticker
    return ticker_map


def build_ticker_map_from_registry(session) -> dict[str, str]:
    """CompanyRegistry(전 상장사) 기준 {normalized_name: ticker} 매핑 (★U1).

    build_ticker_map()과 동일한 정규화 규칙을 전 상장사 규모로 확장 —
    top50.csv 자연 필터를 대체(universe/PLAN.md U-D1 실측: E2E 단절 지점).
    """
    from modules.relation.storage.models import CompanyRegistry

    ticker_map: dict[str, str] = {}
    rows = session.query(CompanyRegistry.name_current, CompanyRegistry.ticker).all()
    for name, ticker in rows:
        if name and ticker:
            ticker_map[normalize_company_name(name)] = ticker
    return ticker_map
