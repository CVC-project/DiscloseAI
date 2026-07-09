"""업종 분류 + EQS 모듈 분기 규칙.

v2: 모든 모듈에 fallback이 추가되어 업종 제외(excluded_modules)는 빈 set 반환.
각 모듈이 내부에서 is_financial/is_holding을 확인해 적절한 fallback을 선택한다.

**금융업(KRX 064~067)**:
- M2: TATA+SGI fallback (매출원가 없음 → 정상 Beneish 불가)
- M3: 소득안정성 fallback (ROE·영업마진 CV → OCF/NI 대체)
- M4: 단축 fallback (DART 3년 데이터 → AR(1) 불가, ROA CV+방향일관성 사용)

**지주/투자회사(내부 코드 "100")**:
- M1: 지주사 fallback (임계 0.40 완화 + 자본누적 일치도)
- M2: TATA+SGI fallback (매출원가 없는 경우)
"""

from __future__ import annotations

from typing import Iterable, Optional, Set

# (CLAUDE.md 기준) 금융업으로 간주할 KRX 업종코드 prefix
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
    """업종에 따라 EQS 산출에서 제외할 모듈 이름 집합.

    v2: 모든 모듈에 fallback이 추가되어 업종 제외 불필요.
    is_financial/is_holding은 각 모듈 내부에서 fallback 분기에 사용.
    """
    return set()


def active_modules(
    all_modules: Iterable[str], industry_code: Optional[str]
) -> list[str]:
    """제외 모듈을 뺀 활성 모듈 리스트."""
    excluded = excluded_modules(industry_code)
    return [m for m in all_modules if m not in excluded]
