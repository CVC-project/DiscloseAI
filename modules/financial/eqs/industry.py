"""업종 분류 + EQS 모듈 예외 규칙.

금융업(KRX 064~067)에서 제외되는 모듈:

- **M3 (현금흐름 괴리)**: 영업현금흐름 개념이 비금융과 근본적으로 다름
  (이자수익·예금 변동 등). 추후 BIS비율 등으로 대체 예정.
- **M2 (Beneish 분식 확률)**: 매출/매출원가 개념이 비금융과 다름
  (이자수익이 주수익, 매출원가 없음) → GMI 등 Beneish 지수 계산 자체가
  부적합. 한국 은행·증권·보험 대상 분식 탐지 모델을 별도 개발하기 전까지 제외.

보험업(067)도 CLAUDE.local.md 지침에 따라 동일 예외 적용.
"""

from __future__ import annotations

from typing import Iterable, Optional, Set

# (CLAUDE.local.md 기준) 금융업으로 간주할 KRX 업종코드 prefix
_FINANCIAL_PREFIXES: tuple[str, ...] = ("064", "065", "066", "067")


def is_financial(industry_code: Optional[str]) -> bool:
    """KRX 업종코드가 금융업(은행/증권/카드/보험)인지 판정."""
    if not industry_code:
        return False
    code = str(industry_code).strip()
    return any(code.startswith(p) for p in _FINANCIAL_PREFIXES)


def excluded_modules(industry_code: Optional[str]) -> Set[str]:
    """업종에 따라 EQS 산출에서 제외할 모듈 이름 집합."""
    if is_financial(industry_code):
        return {"M2", "M3"}
    return set()


def active_modules(
    all_modules: Iterable[str], industry_code: Optional[str]
) -> list[str]:
    """제외 모듈을 뺀 활성 모듈 리스트."""
    excluded = excluded_modules(industry_code)
    return [m for m in all_modules if m not in excluded]
