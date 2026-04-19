"""초보 개인투자자용 용어 사전 (섹션형).

대시보드 ⓘ 툴팁에서 카드 형태로 분리 표시되며, 챗봇/PRD 등에도 공용 사용.

GlossaryEntry 구조:
- ``label``: 표시명 (툴팁 헤더, 예: "ROE (자기자본이익률)")
- ``description``: 📖 **개념** — 한 줄 정의. 그게 무엇인지.
- ``how``: 🧮 **산출 방식** — 어떻게 계산/측정되나 (EQS 모듈처럼 방법이 중요한 경우)
- ``benchmark``: 📏 **기준선** — 실무에서 좋다/나쁘다 보는 값 (예: "10%+ 양호")
- ``intuition``: 💡 **쉽게 말하면** — 직관적 비유

설명 작성 원칙:
1. 전문용어는 풀어 쓰기 — "유동성"→"단기 현금 여유", "자기자본"→"주주 몫"
2. 숫자 비유 — "100원 팔면 12원 남음"
3. 섹션 하나는 1~2문장, 간결하게
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class GlossaryEntry:
    label: str
    description: str
    how: Optional[str] = None
    benchmark: Optional[str] = None
    intuition: Optional[str] = None

    def as_dict(self) -> dict:
        return asdict(self)


GLOSSARY: Dict[str, GlossaryEntry] = {
    # ------- 수익성 비율 -------
    "gross_margin": GlossaryEntry(
        label="매출총이익률",
        description="매출에서 원가(재료·부품·생산 인건비)를 뺀 이익이 매출에서 차지하는 비율.",
        benchmark="30%+ 우수 / 15%~30% 양호 / 15%↓ 원가 압박 큼",
        intuition="'100원 팔면 원가 빼고 얼마 남는지' — 제품 자체의 경쟁력 지표.",
    ),
    "operating_margin": GlossaryEntry(
        label="영업이익률",
        description="본업 활동으로 번 이익(매출−원가−판관비−인건비)이 매출에서 차지하는 비율.",
        benchmark="15%+ 우수 / 10%~15% 양호 / 5%↓ 약함",
        intuition="'100원 팔아서 본업으로 몇 원 남나' — 회사 운영 효율성을 보여줌.",
    ),
    "net_margin": GlossaryEntry(
        label="순이익률",
        description="세금·이자·일회성 손익까지 모두 빼고 최종으로 남는 돈이 매출에서 차지하는 비율.",
        benchmark="10%+ 우수 / 5%~10% 양호 / 2%↓ 취약",
        intuition="회사의 최종 성적표. 영업이익률보다 낮은 이유는 이자·세금 때문.",
    ),
    "roe": GlossaryEntry(
        label="ROE (자기자본이익률)",
        description="주주가 맡긴 돈(자본) 100원으로 한 해 동안 얼마를 벌었는지.",
        how="순이익 ÷ 자본총계 × 100",
        benchmark="15%+ 우수 / 10%~15% 양호 / 5%↓ 저조",
        intuition="'내가 투자한 돈의 수익률'. 워런 버핏이 가장 중시하는 지표 중 하나.",
    ),
    "roa": GlossaryEntry(
        label="ROA (총자산이익률)",
        description="회사 전체 자산(부채 포함)으로 얼마나 효율적으로 벌었는지.",
        how="순이익 ÷ 자산총계 × 100",
        benchmark="7%+ 우수 / 5%~7% 양호 / 2%↓ 비효율",
        intuition="ROE와 달리 빚도 포함한 전체 자산 기준. 빚에 의존하는 경영인지 가릴 수 있음.",
    ),
    # ------- 현금흐름 3종 -------
    "operating_cashflow": GlossaryEntry(
        label="영업활동 CF",
        description="본업(물건·서비스 판매)으로 실제로 들어온 현금.",
        benchmark="꾸준히 +  / 이익 대비 80%+ 가 이상적",
        intuition="장부상 '이익'보다 '진짜 번 돈'에 가까움. 이익은 +인데 여기가 -면 외상만 쌓이는 신호.",
    ),
    "investing_cashflow": GlossaryEntry(
        label="투자활동 CF",
        description="공장·설비·자회사 주식 등을 사거나 판 현금.",
        benchmark="성장기 기업: − (적극 투자) / 축소기: + (매각)",
        intuition="마이너스면 '돈 써서 미래에 투자 중' — 성장 의지. 플러스면 '자산 팔고 있음' — 축소 신호.",
    ),
    "financing_cashflow": GlossaryEntry(
        label="재무활동 CF",
        description="빚을 내거나 갚고, 주주에게 배당을 지급한 현금.",
        benchmark="안정기: − (빚 상환·배당) / 성장기: + (빚·증자)",
        intuition="마이너스면 '빚 갚거나 배당 주는 중' — 재무구조 개선. 플러스면 '빚 늘리는 중'.",
    ),
    # ------- 재무상태 항목 -------
    "total_assets": GlossaryEntry(
        label="자산총계",
        description="회사가 가진 모든 것(현금·재고·공장·매출채권 등)의 합계.",
        intuition="'회사 크기'의 가장 기본 지표. = 부채총계 + 자본총계.",
    ),
    "total_liabilities": GlossaryEntry(
        label="부채총계",
        description="회사가 갚아야 할 모든 빚(차입금·매입채무·퇴직급여 등)의 합계.",
        benchmark="부채비율(부채/자산) 50%↓ 안전 / 70%+ 고부채",
        intuition="많으면 이자 부담 ↑, 경기 둔화 시 취약해짐.",
    ),
    "total_equity": GlossaryEntry(
        label="자본총계",
        description="자산에서 부채를 뺀 '주주의 몫'.",
        benchmark="마이너스면 '자본잠식' — 상장폐지 사유",
        intuition="회사를 지금 청산하면 주주에게 돌아올 금액에 가까움.",
    ),
    "current_assets": GlossaryEntry(
        label="유동자산",
        description="1년 안에 현금화할 수 있는 자산 (현금·예금·재고·매출채권).",
        benchmark="유동비율(유동자산/유동부채) 150%+ 안전",
        intuition="단기 부채 갚을 여력. 부족하면 흑자 도산 가능.",
    ),
    "current_liabilities": GlossaryEntry(
        label="유동부채",
        description="1년 안에 갚아야 하는 빚 (단기차입·매입채무·미지급금).",
        intuition="이 금액보다 유동자산이 작으면 빚 상환 압박 받음.",
    ),
    # ------- EQS 5개 모듈 -------
    "M1": GlossaryEntry(
        label="M1 발생액 품질",
        description="매출·이익 중 '아직 현금 안 들어온 외상' 비중이 정상 수준인지 측정.",
        how="수정 Jones 모델로 이상 발생액(abnormal accruals) 추정. 단일기업 fallback 시 |총발생액/자산| 신호 사용.",
        benchmark="80+ 양호 / 50↓ 주의 / 20↓ 강한 부풀리기 의심",
        intuition="너무 높으면 장부상 이익만 있고 실제 현금 회수는 안 되는 상태.",
    ),
    "M2": GlossaryEntry(
        label="M2 분식 확률",
        description="Beneish 모델로 '분식회계 가능성'을 8가지 재무비율로 점수화.",
        how="매출채권/매출 증가율·자산구성 변화·감가상각률 등 8지수 가중합 → M-score 산출. 임계값 −1.78 넘으면 조작 위험.",
        benchmark="80+ 정상 / 50 언저리 관찰 / 20↓ 의심",
        intuition="서비스·플랫폼 기업(매출원가 개념 없음)·금융업은 모델 부적합으로 제외.",
    ),
    "M3": GlossaryEntry(
        label="M3 현금흐름 괴리",
        description="순이익(장부)과 영업현금흐름(실제 현금)의 비율을 3~5년 추적해 이익의 '현금 뒷받침 정도'를 측정.",
        how="OCF/NI 평균(50%) + 추세(25%) + 변동성(25%) 가중합. 단일 연도 outlier는 ±3배로 winsorize.",
        benchmark="OCF/NI 1.0+ 이상적 / 0.5↓ 괴리 / 음수 다수 적자·조작 의심",
        intuition="이익은 +인데 OCF는 - 면 '장부상 이익이 실체 없음' 신호. 금융업은 개념이 달라 산출 제외.",
    ),
    "M4": GlossaryEntry(
        label="M4 이익 지속성",
        description="올해 이익이 내년에도 비슷하게 유지될 가능성을 측정.",
        how="AR(1) 자기회귀 φ로 ROA 간 연도별 연관성 측정. 10년+는 robust trim(사이클 침체 1점 제외)으로 보정.",
        benchmark="φ=+1 완전 지속(100점) / φ=0 무관(50점) / φ=-1 반전(0점)",
        intuition="반도체·조선 같은 사이클 산업은 5년 윈도우에서 φ가 낮게 나올 수 있음. 일회성 손익이 크면 점수 감점.",
    ),
    "M5": GlossaryEntry(
        label="M5 재무 건전성",
        description="Piotroski F-score 9개 체크리스트로 재무 상태를 점검.",
        how="흑자 여부·ROA 개선·부채비율 개선·유동비율 개선 등 9가지 이분 기준을 통과 개수로 채점. 각 항목당 약 11점.",
        benchmark="7~9점 건전 / 4~6점 평균 / 0~3점 위험",
        intuition="높을수록 재무가 튼튼해서 부도 위험이 낮음. 학계에서 가치투자 전략에 자주 쓰임.",
    ),
}


def describe(key: str) -> str:
    """호환용: key → 기본 description 반환. 없으면 빈 문자열."""
    entry = GLOSSARY.get(key)
    return entry.description if entry else ""


def label(key: str) -> str:
    """key에 해당하는 표시명 반환. 없으면 key 그대로."""
    entry = GLOSSARY.get(key)
    return entry.label if entry else key
