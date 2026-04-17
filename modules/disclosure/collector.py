
"""
modules/disclosure/collector.py
DART 공시 수집 + 20년 차 CPA 심화 분석 엔진

사용법:
    python -m modules.disclosure.collector            # 전체 대상 기업
    python -m modules.disclosure.collector 005930     # 특정 종목코드
"""

import os
import sys
import re
import textwrap
from datetime import datetime, timedelta
from dotenv import load_dotenv
import OpenDartReader as odr
import pandas as pd
from bs4 import BeautifulSoup
from groq import Groq

load_dotenv()

# ─── 설정 ────────────────────────────────────────────────────────────────────
DART_API_KEY = os.getenv("DART_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"

# Groq 클라이언트 (키 없으면 None — 템플릿 분석으로 폴백)
_groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

TARGET_CORPS = {
    "005930": "삼성전자",
    "000660": "SK하이닉스",
    "207940": "삼성바이오로직스",
    "373220": "LG에너지솔루션",
    "005380": "현대차",
    # 삼성전자우(005935) — 우선주 제외
    "000270": "기아",
    "068270": "셀트리온",
    "005490": "POSCO홀딩스",
    "105560": "KB금융",
    "035420": "NAVER",
    "055550": "신한지주",
    "006400": "삼성SDI",
    "051910": "LG화학",
    "028260": "삼성물산",
    "012330": "현대모비스",
    "086790": "하나금융지주",
    "035720": "카카오",
    "000810": "삼성화재",
    "138040": "메리츠금융지주",
    "010130": "고려아연",
    "003670": "포스코퓨처엠",
    "011200": "HMM",
    "066570": "LG전자",
    "017670": "SK텔레콤",
    "032830": "삼성생명",
    "316140": "우리금융지주",
    "012450": "한화에어로스페이스",
    "259960": "크래프톤",
    "033780": "KT&G",
    "034020": "두산에너빌리티",
    "034730": "SK",
    "009150": "삼성전기",
    "323410": "카카오뱅크",
    "003550": "LG",
    "329180": "HD현대중공업",
    "015760": "한국전력",
    "267250": "HD현대",
    "024110": "기업은행",
    "090430": "아모레퍼시픽",
    "010950": "S-Oil",
    "047050": "포스코인터내셔널",
    "042660": "한화오션",
    "003490": "대한항공",
    "000100": "유한양행",
    "030200": "KT",
    "096770": "SK이노베이션",
    "018260": "삼성에스디에스",
    "352820": "하이브",
    "078930": "GS",
}

DAYS_BACK = 7

# 노이즈 제외 키워드 (정규식) — 항상 제외
EXCLUDE_PATTERNS = [
    r"주주총회소집공고",
    r"사외이사\s*선임",
    r"보고서\s*제출",
    r"IR\s*개최",
    r"소수주주권.*행사",
]

# 내부자 거래 보고서 식별 패턴 (배치 여부로 노이즈 판별)
INSIDER_PATTERN = re.compile(r"임원.{0,6}주요주주.{0,10}소유상황")

# 같은 날 동일 기업에서 이 건수 초과 시 정기 배치 신고로 간주 → 제외
INSIDER_BATCH_THRESHOLD = 5

# 고관심 포함 키워드
INCLUDE_PRIORITY = [
    "공급계약", "시설투자", "대표이사", "사내이사",
    "유상증자", "무상증자", "전환사채", "신주인수권",
    "합병", "분할", "영업양수도", "자기주식",
    "매출액변동", "손익변동", "실적발표",
    "회사채", "기업어음", "단기사채",
]


# ─── 헬퍼 함수 ───────────────────────────────────────────────────────────────

def _is_noise(report_nm: str) -> bool:
    for pat in EXCLUDE_PATTERNS:
        if re.search(pat, report_nm):
            return True
    return False


def _build_insider_batch_map(df: pd.DataFrame) -> dict:
    """날짜별 내부자 보고서 건수 맵 반환 — 배치 판별에 사용."""
    mask = df["report_nm"].str.contains(INSIDER_PATTERN, regex=True, na=False)
    insider_df = df[mask]
    return insider_df.groupby("rcept_dt").size().to_dict()


def _is_insider_noise(report_nm: str, rcept_dt: str, batch_map: dict) -> bool:
    """내부자 보고서이면서 같은 날 THRESHOLD 초과 시 노이즈로 판단."""
    if not INSIDER_PATTERN.search(report_nm):
        return False
    day_count = batch_map.get(rcept_dt, 0)
    return day_count > INSIDER_BATCH_THRESHOLD


def _priority_score(report_nm: str) -> int:
    score = 0
    for kw in INCLUDE_PRIORITY:
        if kw in report_nm:
            score += 1
    return score


def _fetch_document_text(dart_client, rcept_no: str, max_chars: int = 2000) -> str:
    """공시 원문 HTML을 가져와 순수 텍스트로 변환한다."""
    import warnings
    from bs4 import XMLParsedAsHTMLWarning
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
    try:
        html = dart_client.document(rcept_no)
        if not html:
            return ""
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
    except Exception:
        return ""


def _detect_type(report_nm: str) -> str:
    """공시 명칭으로부터 분류 태그를 추출한다."""
    if INSIDER_PATTERN.search(report_nm):
        return "내부자거래"
    if "최대주주" in report_nm and "변동" in report_nm:
        return "최대주주변동"
    if any(k in report_nm for k in ["유상증자", "무상증자"]):
        return "증자"
    if "전환사채" in report_nm:
        return "전환사채"
    if "신주인수권" in report_nm:
        return "BW"
    if any(k in report_nm for k in ["합병", "분할"]):
        return "M&A/분할"
    if "영업양수" in report_nm or "영업양도" in report_nm:
        return "영업양도"
    if any(k in report_nm for k in ["공급계약", "수주계약", "계약체결"]):
        return "계약"
    if "시설투자" in report_nm or "CAPEX" in report_nm.upper():
        return "CAPEX"
    if any(k in report_nm for k in ["대표이사", "사내이사", "임원"]):
        return "임원변동"
    if any(k in report_nm for k in ["매출액", "손익", "실적"]):
        return "실적"
    if "자기주식" in report_nm:
        return "자기주식"
    if "회사채" in report_nm or "기업어음" in report_nm:
        return "채권발행"
    return "기타"


# ─── CPA 분석 엔진 ────────────────────────────────────────────────────────────

_CPA_TEMPLATES: dict[str, dict] = {
    "증자": {
        "cash": (
            "신주 발행을 통한 자금 조달로 단기 유동성은 개선될 가능성이 높습니다. "
            "다만 조달 목적(운영자금 vs 시설투자)에 따라 Cash 기여의 지속성이 달라지므로 "
            "사용 목적 명시 여부를 반드시 확인해야 합니다."
        ),
        "risk": (
            "기존 주주 지분 희석(Dilution) 효과가 발생합니다. "
            "발행 규모가 기발행 주식 대비 5% 초과 시 EPS 희석 압력이 시장에서 할인 요인으로 작용할 수 있습니다. "
            "부채비율 자체는 낮아지나 ROE 희석에 주의가 필요합니다."
        ),
        "hidden": (
            "증자 배경을 살펴봐야 합니다. 재무 건전성 확보 목적이라면 사업 정체 시그널일 수 있고, "
            "신규 프로젝트 투자 목적이라면 성장 동력 확보 신호로 해석 가능합니다. "
            "최대주주 참여 여부가 실질적 자신감의 바로미터입니다."
        ),
        "verdict": "지분 희석 우려 존재 — 조달 목적과 최대주주 참여율을 확인 후 판단 필요.",
    },
    "전환사채": {
        "cash": (
            "CB 발행은 단기 현금 유입이나, 향후 주식 전환 시점에 추가 희석이 발생합니다. "
            "쿠폰 이자 부담은 낮지만 전환 프리미엄 설정에 따라 실질 조달 비용이 결정됩니다."
        ),
        "risk": (
            "전환가격 조정 조항(Refixing)이 포함된 경우 주가 하락 시 희석 규모가 무한정 확대될 수 있습니다. "
            "최악의 시나리오에서 대규모 주식 공급 압력이 발생하므로 전환 조건을 반드시 원문에서 확인해야 합니다."
        ),
        "hidden": (
            "CB는 전통적 주식 발행이 어려울 때 사용하는 '차선책'인 경우가 많습니다. "
            "인수자가 특수관계인인지 외부 기관투자자인지에 따라 자금 건전성 신뢰도가 달라집니다."
        ),
        "verdict": "주의 깊은 관찰 필요 — Refixing 조항 및 인수자 정체 반드시 확인.",
    },
    "BW": {
        "cash": (
            "BW는 낮은 이자율로 자금을 조달하되, 신주인수권 행사 시 추가 현금 유입이 발생합니다. "
            "행사가격이 현 주가 대비 프리미엄 수준인지 확인 필요합니다."
        ),
        "risk": (
            "신주인수권 행사가 집중되는 시점에 주식 공급 부담이 발생합니다. "
            "분리형 BW의 경우 신주인수권만 별도 유통되어 시장 변동성을 높일 수 있습니다."
        ),
        "hidden": "통상적인 경영 활동 범위 내 공시로 판단됨. 단, 행사가격과 만기 구조 확인 권고.",
        "verdict": "중립 — 행사조건 및 분리형/비분리형 여부 확인 후 재평가.",
    },
    "계약": {
        "cash": (
            "계약 금액이 연간 매출액 대비 Materiality(중요성)를 초과하는 경우 의미 있는 현금 유입 이벤트입니다. "
            "계약 기간과 대금 수령 방식(선급/후급)이 실질 Cash Flow 시점을 결정합니다."
        ),
        "risk": (
            "단일 대형 계약 의존도 상승 시 계약 취소·연기 리스크가 집중됩니다. "
            "계약 상대방의 신용도와 해지 조항 유무를 확인해야 합니다."
        ),
        "hidden": (
            "계약 상대방이 공개된 경우 해당 기업의 업황을 역으로 추적하면 "
            "업종 전반의 수주 사이클을 선행적으로 파악하는 단서가 됩니다."
        ),
        "verdict": "긍정적 시그널 — 계약 규모(매출 대비 %)와 대금 회수 구조 확인 시 투자 판단 정교화 가능.",
    },
    "CAPEX": {
        "cash": (
            "대규모 설비투자는 단기적으로 FCF(잉여현금흐름)를 압박합니다. "
            "감가상각 기간 동안 비용이 분산되지만, 초기 투자 집행 시점에 현금 유출이 집중됩니다."
        ),
        "risk": (
            "투자 집행 후 시장 수요 둔화 또는 기술 변화로 투자 회수가 불확실해질 경우 "
            "자산 손상(Impairment) 리스크가 발생합니다. 부채를 활용한 투자라면 이자비용 증가도 확인해야 합니다."
        ),
        "hidden": (
            "CAPEX 규모와 완공 시점을 역산하면 해당 기업의 차기 생산 능력 증가 시점을 추정할 수 있습니다. "
            "경쟁사 대비 투자 타이밍이 선제적인지 후행적인지가 핵심 판단 포인트입니다."
        ),
        "verdict": "중립~긍정 — 투자 수익률(ROI) 추정과 완공 시점 확인 후 판단.",
    },
    "임원변동": {
        "cash": (
            "임원 변동 자체는 직접적인 현금 영향이 없습니다. "
            "단, 신임 경영진의 전략적 방향 전환이 중장기 CAPEX·M&A 결정에 영향을 미칩니다."
        ),
        "risk": (
            "핵심 경영진의 갑작스러운 교체는 내부 거버넌스 불안정의 시그널일 수 있습니다. "
            "특히 CFO 또는 재무담당 임원 변동은 회계 정책 변경 가능성을 내포합니다."
        ),
        "hidden": (
            "신임 임원의 전 직장과 전문 분야를 분석하면 경영 방향 변화를 예측할 수 있습니다. "
            "예: 영업 전문가 → 매출 확대 드라이브 / 구조조정 전문가 → 비용 절감 사이클 진입 가능성. "
            "공시 본문의 약력 섹션을 반드시 확인하세요."
        ),
        "verdict": "관찰 필요 — 신임 임원 약력을 기반으로 전략 방향 변화 여부 모니터링 권고.",
    },
    "실적": {
        "cash": (
            "실적 공시는 과거 현금 창출 능력의 공식 확인입니다. "
            "영업이익과 순이익 간 괴리가 크다면 비현금 항목(충당금, 평가손익)의 영향을 분리해서 봐야 합니다."
        ),
        "risk": (
            "컨센서스 대비 서프라이즈(Beat/Miss) 여부가 단기 주가 반응을 결정합니다. "
            "일회성 항목 포함 여부를 제거한 Core 이익 추이가 실질적인 사업 체력 지표입니다."
        ),
        "hidden": (
            "경영진 코멘트와 가이던스(Guidance) 변경 여부가 시장 기대치 재설정의 핵심 단서입니다. "
            "전분기 대비 재고 증감 추이도 수요 방향을 가늠하는 선행 지표로 활용됩니다."
        ),
        "verdict": "핵심 분석 대상 — Core 이익 기반 컨센서스 비교와 가이던스 변화 확인 필수.",
    },
    "자기주식": {
        "cash": (
            "자사주 매입은 현금 유출이나, 주주환원 정책의 일환으로 EPS를 제고하는 효과가 있습니다. "
            "소각 시 자본 감소 → ROE 상승 효과가 발생합니다."
        ),
        "risk": (
            "과도한 자사주 매입은 성장 투자 여력 감소를 의미할 수 있습니다. "
            "차입금 기반 자사주 매입은 재무 레버리지를 높여 주의가 필요합니다."
        ),
        "hidden": (
            "자사주 매입은 '현재 주가가 내재가치 대비 저평가'라는 경영진의 시그널로 해석할 수 있습니다. "
            "소각 의도 없이 장기 보유하면 경영권 방어 목적일 가능성도 검토해야 합니다."
        ),
        "verdict": "긍정적 시그널 — 소각 여부와 재원(현금 vs 차입) 구조 확인.",
    },
    "채권발행": {
        "cash": (
            "채권 발행은 단기 현금 유입이나, 이자비용 증가와 만기 상환 의무가 따릅니다. "
            "조달 금리가 현 시장 금리 대비 합리적인 수준인지 확인이 필요합니다."
        ),
        "risk": (
            "총 차입금 증가로 부채비율과 이자보상배율에 영향을 미칩니다. "
            "고금리 환경에서 리파이낸싱 리스크에 노출될 수 있으므로 만기 구조(Maturity Profile)를 확인해야 합니다."
        ),
        "hidden": "통상적인 경영 활동 범위 내 공시로 판단됨. 단, 조달 목적과 기존 차입금 대비 총량 변화 확인 권고.",
        "verdict": "중립 — 조달금리 및 만기 분산 여부 확인 후 재평가.",
    },
    "M&A/분할": {
        "cash": (
            "대규모 M&A는 FCF에 즉각적인 부담을 줍니다. "
            "피인수 기업의 EBITDA 기준 인수 배수(Multiple)가 적정한지, 시너지 실현 기간이 얼마나 걸릴지가 핵심입니다."
        ),
        "risk": (
            "인수 통합(PMI) 실패 리스크와 프리미엄 과다 지불에 따른 영업권(Goodwill) 손상 리스크가 있습니다. "
            "분할의 경우 사업부 독립에 따른 규모의 경제 상실 가능성을 검토해야 합니다."
        ),
        "hidden": (
            "M&A 대상 기업의 사업 영역을 통해 인수기업의 중장기 포트폴리오 전략을 역산할 수 있습니다. "
            "분할 공시는 종종 특정 사업부 매각 또는 별도 상장을 위한 전 단계인 경우가 많습니다."
        ),
        "verdict": "주의 깊은 관찰 필요 — 인수 배수, PMI 계획, 재원 조달 방식의 3개 축 반드시 확인.",
    },
    "영업양도": {
        "cash": (
            "영업 양수도는 일회성 현금 유입/유출 이벤트입니다. "
            "양도가액이 장부가 대비 높다면 처분이익, 낮다면 처분손실이 발생하여 당기손익에 반영됩니다."
        ),
        "risk": (
            "핵심 사업 양도 시 향후 매출 기반이 축소될 수 있습니다. "
            "반대로 비핵심 사업 매각이라면 선택과 집중 전략의 일환으로 긍정적으로 해석 가능합니다."
        ),
        "hidden": (
            "사업 양도 상대방이 경쟁사 또는 사모펀드인지에 따라 전략적 의미가 달라집니다. "
            "경쟁사 매각이라면 사업 정리, 사모펀드 매각이라면 유동성 확보 목적인 경우가 많습니다."
        ),
        "verdict": "관찰 필요 — 양도 대상이 핵심/비핵심 여부와 양도가액의 적정성 확인.",
    },
    "내부자거래": {
        "cash": (
            "내부자의 개인 주식 거래이므로 기업 현금흐름에 직접 영향은 없습니다. "
            "단, 스톡옵션 행사의 경우 희석 효과가 발생하므로 행사가격과 현재 주가 간 차이를 확인해야 합니다."
        ),
        "risk": (
            "임원·주요주주의 대량 매도는 내부 정보에 기반한 선행 매도일 가능성을 배제할 수 없습니다. "
            "특히 실적 발표 직전 매도는 규제 당국의 관심 대상이 되므로 타이밍을 반드시 점검해야 합니다."
        ),
        "hidden": (
            "매수 vs 매도 방향이 핵심입니다. 대표이사·최대주주의 자사주 매수는 "
            "'현재 주가가 저평가'라는 내부자 시그널로 해석 가능합니다. "
            "반대로 대량 매도는 실적 둔화 또는 사업 불확실성을 인지한 선제적 차익 실현일 수 있습니다."
        ),
        "verdict": "주의 깊은 관찰 필요 — 매매 방향·규모·타이밍을 공시 원문에서 직접 확인 권고.",
    },
    "최대주주변동": {
        "cash": (
            "최대주주 변동 자체는 기업 현금흐름에 직접 영향을 주지 않습니다. "
            "단, 경영권 프리미엄을 동반한 지분 매각이라면 해당 주주에게 유의미한 현금 실현이 발생합니다."
        ),
        "risk": (
            "최대주주 교체는 경영 방향의 급격한 전환을 예고하는 가장 강력한 시그널 중 하나입니다. "
            "신규 최대주주의 업종 배경과 기존 사업과의 시너지 여부를 신속히 파악해야 합니다."
        ),
        "hidden": (
            "인수 주체가 사모펀드(PEF)라면 단기 구조조정 후 재매각(Flip) 시나리오를 염두에 둬야 합니다. "
            "전략적 투자자(SI)라면 합병·흡수 가능성, 재무적 투자자(FI)라면 배당 확대·자산 매각 압력이 높아질 수 있습니다."
        ),
        "verdict": "핵심 분석 대상 — 신규 최대주주의 정체와 지배구조 변화 방향을 최우선으로 확인.",
    },
    "기타": {
        "cash": (
            "공시 유형상 직접적인 현금 영향을 즉시 파악하기 어렵습니다. "
            "원문 공시를 통해 구체적인 금액과 결제 조건을 확인해야 합니다."
        ),
        "risk": (
            "공시 내용에 따라 위험 요소가 달라집니다. "
            "규제·소송 관련 공시의 경우 충당 부채 설정 여부를 확인해야 합니다."
        ),
        "hidden": "통상적인 경영 활동 범위 내 공시로 판단됨.",
        "verdict": "중립 — 원문 공시 내용 직접 확인 후 판단 권고.",
    },
}


def _analyze_with_groq(corp_name: str, report_nm: str, disc_type: str, doc_text: str) -> str | None:
    """Groq LLM으로 공시 원문을 읽고 일반인 언어로 분석을 생성한다."""
    if not _groq_client or not doc_text:
        return None

    prompt = f"""당신은 20년 경력의 시니어 공인회계사(CPA)입니다.
아래 한국 상장기업의 공시 원문을 읽고, **일반 개인투자자**가 이해할 수 있는 언어로 분석해주세요.
전문 용어는 반드시 쉬운 말로 풀어서 설명하고, 숫자가 있으면 반드시 인용하세요.

기업명: {corp_name}
공시 제목: {report_nm}
공시 유형: {disc_type}
공시 원문:
{doc_text}

다음 4가지 항목으로 분석해주세요. 각 항목은 2~3문장으로 간결하게 작성하세요.

[Cash] 이 공시가 회사의 돈(현금)에 미치는 영향은?
[Risk] 투자자가 주의해야 할 위험 요소는?
[Hidden Agenda] 이 공시 뒤에 숨겨진 경영진의 의도나 전략적 시그널은?
[Verdict] 회계사로서 한 줄 최종 평가는?

반드시 한국어로 답하고, 항목 제목([Cash] 등)은 그대로 유지하세요."""

    try:
        res = _groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=800,
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        print(f"  [WARN] Groq 분석 실패: {e}")
        return None


def build_cpa_summary(
    corp_name: str, report_nm: str, disc_type: str, rcept_dt: str, doc_text: str = ""
) -> str:
    header = (
        f"[공시] {corp_name} | {report_nm} | {rcept_dt}\n"
        f"[분류] {disc_type}\n\n"
    )

    # Groq AI 분석 시도 (원문 있을 때만)
    ai_analysis = _analyze_with_groq(corp_name, report_nm, disc_type, doc_text)
    if ai_analysis:
        return header + ai_analysis

    # 폴백: 템플릿 기반 분석
    t = _CPA_TEMPLATES.get(disc_type, _CPA_TEMPLATES["기타"])
    doc_section = (
        f"\n\n[원문 발췌]\n{textwrap.fill(doc_text, width=80)}" if doc_text else ""
    )
    summary = (
        header
        + f"[Cash]\n{textwrap.fill(t['cash'], width=80)}\n\n"
        f"[Risk]\n{textwrap.fill(t['risk'], width=80)}\n\n"
        f"[Hidden Agenda]\n{textwrap.fill(t['hidden'], width=80)}\n\n"
        f"[Verdict]\n{t['verdict']}"
        f"{doc_section}"
    )
    return summary


# ─── 메인 수집 로직 ───────────────────────────────────────────────────────────

def collect(stock_codes: list[str] | None = None) -> None:
    if not DART_API_KEY:
        print("[ERROR] DART_API_KEY가 .env에 설정되지 않았습니다.")
        sys.exit(1)

    dart = odr(DART_API_KEY)

    targets = (
        {k: TARGET_CORPS[k] for k in stock_codes if k in TARGET_CORPS}
        if stock_codes
        else TARGET_CORPS
    )
    if not targets:
        print(f"[ERROR] 유효하지 않은 종목코드: {stock_codes}")
        sys.exit(1)

    end_dt = datetime.today()
    start_dt = end_dt - timedelta(days=DAYS_BACK)
    start_str = start_dt.strftime("%Y%m%d")
    end_str = end_dt.strftime("%Y%m%d")

    print(f"\n{'='*60}")
    print(f"  DiscloseAI — DART 공시 수집 & CPA 분석")
    print(f"  대상 기간: {start_str} ~ {end_str}")
    print(f"  대상 기업: {', '.join(targets.values())}")
    print(f"{'='*60}\n")

    # DB 세션
    from modules.disclosure.db import get_local_session
    from modules.disclosure.models import DisclosureLocal

    session = get_local_session()
    saved, skipped, filtered = 0, 0, 0

    for stock_code, corp_name in targets.items():
        print(f"▶ [{corp_name}({stock_code})] 공시 목록 조회 중...")

        try:
            df: pd.DataFrame = dart.list(stock_code, start_str, end_str)
        except Exception as e:
            print(f"  [WARN] API 오류: {e}")
            continue

        if df is None or len(df) == 0:
            print(f"  → 최근 {DAYS_BACK}일간 공시 없음\n")
            continue

        print(f"  → 총 {len(df)}건 수신, 필터링 시작...")

        # 내부자 보고서 날짜별 건수 사전 계산 (배치 판별용)
        insider_batch_map = _build_insider_batch_map(df)

        for _, row in df.iterrows():
            report_nm: str = str(row.get("report_nm", ""))
            rcept_no: str = str(row.get("rcept_no", ""))
            rcept_dt: str = str(row.get("rcept_dt", ""))

            # 1차: 완전 노이즈 제거
            if _is_noise(report_nm):
                filtered += 1
                print(f"  [SKIP-NOISE] {report_nm}")
                continue

            # 2차: 내부자 보고서 배치 판별 — 5건 초과 시 정기 신고로 간주
            if _is_insider_noise(report_nm, rcept_dt, insider_batch_map):
                filtered += 1
                print(f"  [SKIP-BATCH] {report_nm} ({rcept_dt}, {insider_batch_map.get(rcept_dt)}건 중 1)")
                continue

            # 중복 체크
            exists = session.query(DisclosureLocal).filter_by(disclosure_id=rcept_no).first()
            if exists:
                skipped += 1
                print(f"  [SKIP-DUP]   {report_nm} ({rcept_no})")
                continue

            disc_type = _detect_type(report_nm)

            print(f"  [분석중]     [{disc_type}] {report_nm} ({rcept_dt})")

            doc_text = _fetch_document_text(dart, rcept_no)
            summary = build_cpa_summary(corp_name, report_nm, disc_type, rcept_dt, doc_text)

            record = DisclosureLocal(
                disclosure_id=rcept_no,
                corp_code=str(row.get("corp_code", stock_code)),
                corp_name=corp_name,
                disclosure_date=datetime.strptime(rcept_dt, "%Y%m%d").date() if rcept_dt else None,
                disclosure_type=disc_type,
                title=report_nm,
                amount=None,
                summary=summary,
            )
            session.add(record)
            session.commit()
            saved += 1
            print(f"  [저장완료]   rcept_no={rcept_no}")

        print()

    session.close()

    print(f"{'='*60}")
    print(f"  수집 완료 | 신규 저장: {saved}건 | 중복 스킵: {skipped}건 | 노이즈 제거: {filtered}건")
    print(f"{'='*60}\n")


# ─── 진입점 ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    codes = sys.argv[1:] if len(sys.argv) > 1 else None
    collect(codes)
