"""기업명 정규화 공용 유틸.

ingest·transform 양쪽에서 import — 순환 의존 회피를 위해 별도 모듈.
정규화 규칙은 설계 변경 시 `modules/relation/transform/CLAUDE.md`에도 반영.
"""

from __future__ import annotations

import re

# DART/FTC 표기 vs KRX 약칭 등 수동 매핑 예외
NAME_ALIASES: dict[str, str] = {
    "현대자동차": "현대차",
    "에스케이": "SK",
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

    # 별칭 매핑 (lowercase 비교)
    s_lower = s.lower()
    for alias_key, alias_value in NAME_ALIASES.items():
        if s_lower == alias_key.lower():
            return alias_value

    return s


def build_ticker_map(top50_csv_path) -> dict[str, str]:
    """top50.csv의 corp_name을 정규화하여 ticker로 매핑한 dict 반환.

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
