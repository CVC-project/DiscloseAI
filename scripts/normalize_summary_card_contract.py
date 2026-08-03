from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.disclosure.assemble_summary import sync_summaries_to_db

BASE = ROOT / "modules" / "disclosure" / "data" / "fulltext"


SEGMENT_OVERRIDES: dict[str, list[dict]] = {
    "00101220": [
        {"name": "자동차", "desc": "KG모빌리티 완성차 제조·판매", "revenue_share": 0.468},
        {"name": "철강·항만", "desc": "철강제품 생산과 항만 운영", "revenue_share": 0.348},
        {"name": "전자결제", "desc": "온라인·모바일 결제 서비스", "revenue_share": 0.099},
        {"name": "화학·바이오에너지", "desc": "비료·혼화제와 바이오중유", "revenue_share": 0.035},
        {"name": "외식·미디어·교육", "desc": "프랜차이즈, 미디어, 교육 콘텐츠", "revenue_share": 0.047},
    ],
    "00105280": [
        {"name": "푸드·식자재", "desc": "단체급식과 식자재 유통", "revenue_share": 0.21},
        {"name": "유통·홈쇼핑", "desc": "공산품 유통과 TV홈쇼핑", "revenue_share": 0.17},
        {"name": "가구·건축자재", "desc": "가구와 창호·건축자재", "revenue_share": 0.238},
        {"name": "의류", "desc": "의류 제조와 도소매", "revenue_share": 0.183},
        {"name": "중장비·바이오", "desc": "건설기계와 바이오 소재", "revenue_share": 0.068},
        {"name": "기타 서비스", "desc": "모바일식권, 임대, 여행 등", "revenue_share": 0.131},
    ],
    "00105299": [
        {"name": "건설자재", "desc": "강관, 거푸집, 가설재, 모듈러", "revenue_share": 0.406},
        {"name": "사료", "desc": "가축용 배합사료 제조·판매", "revenue_share": 0.352},
        {"name": "단조부품", "desc": "자동차·중장비용 단조 부품", "revenue_share": 0.115},
        {"name": "선박엔진 부품", "desc": "선박용 엔진밸브 제조", "revenue_share": 0.08},
        {"name": "기타", "desc": "부산물 등 기타 매출", "revenue_share": 0.046},
    ],
    "00106881": [
        {"name": "여성복", "desc": "조이너스, 꼼빠니아 등", "revenue_share": 0.535},
        {"name": "캐주얼", "desc": "바인드 등 캐주얼 브랜드", "revenue_share": 0.282},
        {"name": "남성복", "desc": "트루젠, 모스바니 등", "revenue_share": 0.137},
        {"name": "기타 브랜드", "desc": "아위와 기타 상품", "revenue_share": 0.047},
    ],
    "00109718": [
        {"name": "식품제조", "desc": "어묵, 맛살, 식용유 제품", "revenue_share": 0.368},
        {"name": "OEM식품·유통", "desc": "위탁생산 식품과 식자재 유통", "revenue_share": 0.389},
        {"name": "축산·급식", "desc": "가금·양돈과 단체급식", "revenue_share": 0.17},
        {"name": "원양어업", "desc": "참치, 명태, 대구 등", "revenue_share": 0.037},
        {"name": "기타", "desc": "임대와 냉장보관료 등", "revenue_share": 0.036},
    ],
    "00110893": [
        {"name": "트레이딩", "desc": "주식·채권·파생상품 자기매매", "revenue_share": 0.47},
        {"name": "법인·리테일 영업", "desc": "법인 금융서비스와 위탁매매", "revenue_share": 0.29},
        {"name": "투자·부동산금융", "desc": "PE, 부실채권, 부동산개발 투자", "revenue_share": 0.154},
        {"name": "기업금융", "desc": "IB 관련 종합 금융서비스", "revenue_share": 0.033},
        {"name": "저축은행·기타", "desc": "예금·대출, 자산운용, 신탁 등", "revenue_share": 0.053},
    ],
    "00120030": [
        {"name": "건축·주택", "desc": "자이, 재건축, 오피스 건축", "revenue_share": 0.626},
        {"name": "플랜트·인프라", "desc": "EPC와 도로·철도 등 토목", "revenue_share": 0.223},
        {"name": "수처리", "desc": "해수담수화와 상하수도 운영", "revenue_share": 0.07},
        {"name": "개발·신사업", "desc": "부동산 개발과 데이터센터", "revenue_share": 0.035},
        {"name": "Prefab·기타", "desc": "모듈러주택, PC콘크리트, 리조트", "revenue_share": 0.047},
    ],
    "00120526": [
        {"name": "마트·슈퍼", "desc": "할인점과 슈퍼마켓", "revenue_share": 0.487},
        {"name": "백화점", "desc": "국내외 롯데백화점", "revenue_share": 0.243},
        {"name": "가전전문점", "desc": "롯데하이마트 가전 도소매", "revenue_share": 0.167},
        {"name": "홈쇼핑·이커머스", "desc": "TV·모바일 커머스와 롯데ON", "revenue_share": 0.074},
        {"name": "영화상영", "desc": "롯데시네마 영화관 운영", "revenue_share": 0.032},
    ],
    "00144650": [
        {"name": "건설사업관리", "desc": "공사 전 과정 관리 용역", "revenue_share": 0.211},
        {"name": "인프라 설계", "desc": "도로, 철도, 교량, 공항 설계", "revenue_share": 0.34},
        {"name": "수자원·도시계획", "desc": "댐, 하천, 상하수도, 도시개발", "revenue_share": 0.193},
        {"name": "해외용역", "desc": "해외 인프라 설계·감리", "revenue_share": 0.126},
        {"name": "EPC·기타", "desc": "플랜트 건설과 기타 용역", "revenue_share": 0.13},
    ],
    "00148920": [
        {"name": "공업·분체 도료", "desc": "산업용 도료와 분체도료", "revenue_share": 0.428},
        {"name": "UV·전자소재 도료", "desc": "자외선 경화형 도료", "revenue_share": 0.18},
        {"name": "건축·중방식 도료", "desc": "건축용과 중방식용 도료", "revenue_share": 0.157},
        {"name": "자동차보수용 도료", "desc": "차량 보수 도장용 도료", "revenue_share": 0.12},
        {"name": "목공·접착제", "desc": "목재용 도료와 산업용 접착제", "revenue_share": 0.072},
    ],
    "00153339": [
        {"name": "석회·비철금속", "desc": "생석회, 탄산칼슘, 합금철", "revenue_share": 0.467},
        {"name": "휴게소·주유소", "desc": "고속도로 식품류와 휘발유 판매", "revenue_share": 0.119},
        {"name": "연료·탄산가스", "desc": "페트로코크스, 탄산가스, 드라이아이스", "revenue_share": 0.187},
        {"name": "조명", "desc": "LED전구 등 조명제품", "revenue_share": 0.031},
        {"name": "기타 소재", "desc": "화장품, 인조대리석, 합성왁스", "revenue_share": 0.196},
    ],
    "00160588": [
        {"name": "금융", "desc": "보험, 증권, 저축은행", "revenue_share": 0.427},
        {"name": "방산·항공", "desc": "화약, 자주포, 레이더, 항공엔진", "revenue_share": 0.209},
        {"name": "조선", "desc": "LNG운반선과 특수선 건조", "revenue_share": 0.195},
        {"name": "에너지·화학", "desc": "태양광, 석유화학, 소재", "revenue_share": 0.168},
        {"name": "유통·레저·건설", "desc": "무역, 백화점, 리조트, 건설", "revenue_share": 0.159},
    ],
    "00164636": [
        {"name": "건설·개발", "desc": "주택, 토목, 건축, 부동산 개발", "revenue_share": 0.627},
        {"name": "소재", "desc": "자동차·건자재용 플라스틱", "revenue_share": 0.138},
        {"name": "발전", "desc": "LNG 복합화력 전력 생산", "revenue_share": 0.11},
        {"name": "운영·유통", "desc": "건물관리, 호텔, 상업시설 임대", "revenue_share": 0.112},
        {"name": "기타", "desc": "악기, 지주회사 수수료 등", "revenue_share": 0.013},
    ],
    "00164973": [
        {"name": "장기보험", "desc": "건강·상해 등 장기손해보험", "revenue_share": 0.639},
        {"name": "자동차보험", "desc": "개인·업무용 자동차보험", "revenue_share": 0.217},
        {"name": "특종·일반보험", "desc": "화재, 기술, 특수위험 보장", "revenue_share": 0.077},
        {"name": "해외·재보험", "desc": "해외 원보험과 재보험 인수", "revenue_share": 0.035},
        {"name": "연금·해상보험", "desc": "개인연금, 선박·화물 보험", "revenue_share": 0.032},
    ],
    "00165103": [
        {"name": "냉동·간편식", "desc": "만두, 김말이, 소스, 간편식", "revenue_share": 0.242},
        {"name": "건강식품", "desc": "스틱, 정제, 환제형 건강기능식품", "revenue_share": 0.192},
        {"name": "과실가공", "desc": "잼, 시럽, 냉동과실, 퓨레", "revenue_share": 0.325},
        {"name": "음료·베이스", "desc": "음료 원료와 베이스", "revenue_share": 0.105},
        {"name": "통조림·기타", "desc": "통조림, 밤 가공품 등", "revenue_share": 0.136},
    ],
    "00165343": [
        {"name": "CAT 장비·엔진", "desc": "건설기계, 엔진, 발전기세트", "revenue_share": 0.594},
        {"name": "부품", "desc": "건설기계·엔진 부품과 타이어", "revenue_share": 0.276},
        {"name": "정비", "desc": "장비 정비 서비스", "revenue_share": 0.075},
        {"name": "물류·산업장비", "desc": "물류장비와 파쇄·선별 장비", "revenue_share": 0.04},
        {"name": "임대·중개", "desc": "건설기계 렌탈과 중개 매출", "revenue_share": 0.014},
    ],
    "00202060": [
        {"name": "차체 고정부품", "desc": "브라켓, 힌지, 롤러암", "revenue_share": 0.554},
        {"name": "시트부품", "desc": "자동차 의자 프레임 부품", "revenue_share": 0.189},
        {"name": "전동화 부품", "desc": "전기차 배터리케이스 등", "revenue_share": 0.058},
        {"name": "엔진·기타부품", "desc": "오일팬, 축압기, 부산물 등", "revenue_share": 0.2},
    ],
    "00210856": [
        {"name": "사무용 의자", "desc": "사무용 의자 제조·판매", "revenue_share": 0.281},
        {"name": "책상·수납", "desc": "책상, 캐비닛, 서랍", "revenue_share": 0.296},
        {"name": "시스템 가구", "desc": "판넬과 사무공간 시공", "revenue_share": 0.137},
        {"name": "교육·병원 가구", "desc": "특수 공간용 가구 등", "revenue_share": 0.286},
    ],
    "00242934": [
        {"name": "클린룸 소모품", "desc": "방진복, 글러브, 와이퍼", "revenue_share": 0.6},
        {"name": "산업안전·생활용품", "desc": "PPE, 마스크, 생활용품", "revenue_share": 0.109},
        {"name": "디스플레이 소재", "desc": "BLU 광학필름 임가공", "revenue_share": 0.077},
        {"name": "라이프사이언스", "desc": "제약·바이오용 메디컬 파우치", "revenue_share": 0.071},
        {"name": "폴리이미드·기타", "desc": "폴리이미드 반제품과 기타 사업", "revenue_share": 0.144},
    ],
    "00631518": [
        {"name": "석유", "desc": "원유 정제와 석유제품 판매", "revenue_share": 0.59},
        {"name": "가스·전력", "desc": "LNG, 전력, 도시가스", "revenue_share": 0.15},
        {"name": "화학·윤활유", "desc": "화학소재와 윤활유 제품", "revenue_share": 0.16},
        {"name": "배터리·소재", "desc": "전기차 배터리와 분리막", "revenue_share": 0.09},
        {"name": "자원개발", "desc": "원유와 천연가스 탐사·개발", "revenue_share": None},
    ],
}

PRODUCT_OVERRIDES: dict[str, list[str]] = {
    "00106641": ["승용차", "RV", "상용차", "전기차", "하이브리드차", "PBV"],
}


def _summary_paths() -> list[Path]:
    return sorted(path for path in BASE.glob("*/*/summary.json") if "batch_runs" not in path.parts)


def normalize() -> list[tuple[str, str, str]]:
    changed: list[tuple[str, str, str]] = []
    sync_targets: list[tuple[str, str]] = []
    for path in _summary_paths():
        data = json.loads(path.read_text(encoding="utf-8"))
        corp_code = str(data.get("corp_code") or "")
        reasons: list[str] = []

        if corp_code in SEGMENT_OVERRIDES:
            data["segments"] = SEGMENT_OVERRIDES[corp_code]
            reasons.append("segments")
        if corp_code in PRODUCT_OVERRIDES:
            data["products"] = PRODUCT_OVERRIDES[corp_code]
            reasons.append("products")

        if reasons:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            changed.append((corp_code, data.get("corp_name") or "", ",".join(reasons)))
            sync_targets.append((corp_code, str(data.get("rcept_no") or path.parent.name)))

    if sync_targets:
        sync_summaries_to_db(sync_targets)
    return changed


def main() -> None:
    changed = normalize()
    print(f"normalized={len(changed)}")
    for corp_code, corp_name, reason in changed:
        print(f"- {corp_code} {corp_name}: {reason}")


if __name__ == "__main__":
    main()
