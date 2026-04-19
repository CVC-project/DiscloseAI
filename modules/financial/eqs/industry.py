"""업종 분류 + EQS 모듈 예외 규칙.

**금융업(KRX 064~067)** — M2, M3 제외:

- M3 (현금흐름 괴리): 영업현금흐름 개념이 비금융과 근본적으로 다름
  (이자수익·예금 변동 등). 추후 BIS비율 등으로 대체 예정.
- M2 (Beneish 분식 확률): 매출/매출원가 개념이 비금융과 다름 (이자수익이
  주수익, 매출원가 없음) → Beneish 지수 계산 자체가 부적합.

**지주/투자회사(내부 코드 "100")** — M1 제외:

- M1 (발생액 품질): 단일기업 fallback은 |총발생액/자산|을 신호로 쓰는데,
  지주사의 자회사 지분법이익이 비현금성이라 '이상 발생액'으로 오인됨
  (SK스퀘어 |TA/A|=0.385 → 0점 사례). 자회사별 cross-section이 아닌 이상
  지주사에는 본 모듈 부적합.
- M2·M3·M4·M5는 유지: 지주사도 매출·현금흐름·이익 지속성·재무 건전성은
  의미 있는 신호. 매출원가가 없는 지주사는 M2가 자동으로 결측 판정됨.
"""

from __future__ import annotations

from typing import Iterable, Optional, Set

# (CLAUDE.local.md 기준) 금융업으로 간주할 KRX 업종코드 prefix
_FINANCIAL_PREFIXES: tuple[str, ...] = ("064", "065", "066", "067")

# 지주/투자회사 식별용 내부 코드. KRX 공식 업종코드가 아닌 DiscloseAI 내부 태그.
# batch.py의 _HOLDING_COMPANIES 매핑이 이 코드를 부여.
_HOLDING_PREFIX = "100"


def is_financial(industry_code: Optional[str]) -> bool:
    """KRX 업종코드가 금융업(은행/증권/카드/보험)인지 판정."""
    if not industry_code:
        return False
    code = str(industry_code).strip()
    return any(code.startswith(p) for p in _FINANCIAL_PREFIXES)


def is_holding(industry_code: Optional[str]) -> bool:
    """industry_code가 지주·투자회사 내부 태그인지 판정."""
    if not industry_code:
        return False
    return str(industry_code).strip().startswith(_HOLDING_PREFIX)


def excluded_modules(industry_code: Optional[str]) -> Set[str]:
    """업종에 따라 EQS 산출에서 제외할 모듈 이름 집합."""
    if is_financial(industry_code):
        return {"M2", "M3"}
    if is_holding(industry_code):
        return {"M1"}
    return set()


def active_modules(
    all_modules: Iterable[str], industry_code: Optional[str]
) -> list[str]:
    """제외 모듈을 뺀 활성 모듈 리스트."""
    excluded = excluded_modules(industry_code)
    return [m for m in all_modules if m not in excluded]
