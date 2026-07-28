"""Build a static KOSPI top-company business report first-tab prototype.

The page is intentionally self-contained so it can be opened directly from
docs/prototype without a local server. It combines local DART-derived data with
a cached yfinance market snapshot for market-cap and PER sorting.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
EQS_PATH = ROOT / "docs" / "prototype" / "eqs_data.json"
FULLTEXT_INDEX = ROOT / "modules" / "disclosure" / "data" / "fulltext" / "index.json"
OUT_PATH = ROOT / "docs" / "prototype" / "kospi50_business_tabs.html"
MARKET_SNAPSHOT_PATH = ROOT / "docs" / "prototype" / "kospi50_market_snapshot.json"
DISCLOSURE_DB_PATH = ROOT / "modules" / "disclosure" / "data" / "disclosure.db"

CATEGORY_BY_STOCK: dict[str, tuple[str, str, str]] = {
    "005930": ("반도체/전자부품", "종합반도체", "종합반도체"),
    "000660": ("반도체/전자부품", "메모리반도체", "메모리"),
    "005380": ("자동차", "완성차", "자동차"),
    "373220": ("2차전지/배터리", "배터리셀", "배터리"),
    "012450": ("중공업/방산/전기장비", "방산·항공우주", "방산"),
    "402340": ("지주/복합기업", "투자지주", "지주"),
    "207940": ("바이오/제약", "바이오 CDMO", "CDMO"),
    "034020": ("중공업/방산/전기장비", "발전설비", "발전설비"),
    "105560": ("금융/보험", "금융업", "금융업"),
    "000270": ("자동차", "완성차", "자동차"),
    "329180": ("조선", "조선", "조선"),
    "032830": ("금융/보험", "생명보험", "보험"),
    "028260": ("지주/복합기업", "건설·상사 복합", "복합"),
    "055550": ("금융/보험", "금융업", "금융업"),
    "068270": ("바이오/제약", "바이오의약품", "바이오"),
    "009150": ("반도체/전자부품", "전자부품", "전자부품"),
    "006400": ("2차전지/배터리", "배터리", "배터리"),
    "042660": ("조선", "조선·방산", "조선"),
    "267260": ("중공업/방산/전기장비", "전력기기", "전력기기"),
    "006800": ("금융/보험", "증권업", "증권"),
    "012330": ("자동차", "자동차부품", "부품"),
    "010130": ("화학/정유/소재", "제련", "제련"),
    "086790": ("금융/보험", "금융업", "금융업"),
    "015760": ("통신/유틸리티/운송/기타", "전력", "전력"),
    "011200": ("통신/유틸리티/운송/기타", "해운", "해운"),
    "035420": ("인터넷/IT서비스", "플랫폼", "플랫폼"),
    "096770": ("화학/정유/소재", "에너지", "에너지"),
    "272210": ("중공업/방산/전기장비", "방산·ICT", "방산ICT"),
    "267250": ("지주/복합기업", "조선·정유 지주", "지주"),
    "298040": ("중공업/방산/전기장비", "전력기기", "전력기기"),
    "034730": ("지주/복합기업", "투자지주", "지주"),
    "316140": ("금융/보험", "금융업", "금융업"),
    "017670": ("통신/유틸리티/운송/기타", "통신", "통신"),
    "010140": ("조선", "조선해양", "조선"),
    "051910": ("화학/정유/소재", "화학·첨단소재", "화학"),
    "064350": ("중공업/방산/전기장비", "방산·철도", "방산철도"),
    "000810": ("금융/보험", "손해보험", "보험"),
    "000150": ("지주/복합기업", "지주·전자소재", "지주"),
    "035720": ("인터넷/IT서비스", "플랫폼", "플랫폼"),
    "079550": ("중공업/방산/전기장비", "방산", "방산"),
    "033780": ("통신/유틸리티/운송/기타", "담배·건기식", "소비재"),
    "009540": ("조선", "조선", "조선"),
    "010120": ("중공업/방산/전기장비", "전력기기", "전력기기"),
    "003670": ("2차전지/배터리", "배터리소재", "배터리소재"),
    "005490": ("화학/정유/소재", "철강·소재 지주", "소재"),
    "042700": ("반도체/전자부품", "반도체장비", "반도체장비"),
    "000720": ("통신/유틸리티/운송/기타", "건설", "건설"),
}


def _idea(title: str, value: str, fact: str, view: str) -> dict[str, str]:
    return {"title": title, "value": value, "fact": fact, "view": view}


# Company-specific reading notes based on the collected annual-report business
# sections. Product lists remain in the orbit cards; these entries explain the
# change, operating structure, or business implication behind those products.
CUSTOM_REPORT_IDEAS: dict[str, list[dict[str, str]]] = {
    "005930": [
        _idea("DS 부문 이익 회복", "영업이익 24.9조원", "DS 부문은 2023년 영업손실에서 2024년 흑자로 돌아섰고, 2025년에는 영업이익 약 24.9조원까지 회복했습니다.", "메모리 가격과 AI 서버 수요, HBM 같은 고부가 제품 비중이 회복세를 이어 가는지 확인할 필요가 있습니다."),
        _idea("원재료 가격과 가동률", "Wafer -10% · Cover Glass +12%", "사업보고서에는 부문별 원재료 가격 변화와 TV·모니터 78.8%, 스마트폰 79.3%, 메모리·SDC 100%의 가동률이 함께 제시됩니다.", "DX의 가격 방어력과 원가 전가, 가동률이 낮은 부문의 고정비 부담을 함께 봐야 합니다."),
    ],
    "000660": [
        _idea("AI 수요가 메모리 전반으로 확산", "HBM · 일반 DRAM · 기업용 SSD", "2025년 사업보고서는 AI 확산으로 HBM뿐 아니라 일반 DRAM 수요도 커졌고, NAND는 데이터센터용 고용량 기업용 SSD가 수요 증가를 이끌었다고 설명합니다.", "메모리 가격과 AI 서버 수요, HBM·기업용 SSD의 제품 비중이 다음 실적에서도 유지되는지 확인할 필요가 있습니다."),
        _idea("공장 풀가동", "평균 가동률 100%", "SK하이닉스는 4조 3교대와 연중 365일 운영을 기준으로 2025년 생산능력과 생산실적을 각각 41조 2,165억원으로 집계했고, 평균 가동률 100%를 공시했습니다.", "수요 회복이 실제 생산라인 가동으로 이어졌는지 보여주는 지표이며, 추가 설비 투자에 따른 비용 부담도 함께 확인해야 합니다."),
        _idea("NAND·SSD의 데이터센터 확장", "Intel NAND 인수 최종 종결", "사업보고서에는 Intel NAND 사업 인수가 2025년 3월 최종 종결됐고, 데이터센터용 PCIe Gen5 SSD와 CMM-DDR5 개발이 제시됩니다.", "HBM뿐 아니라 기업용 SSD와 서버 메모리까지 포트폴리오가 넓어지는지를 보는 것이 좋습니다."),
    ],
    "005380": [
        _idea("여러 동력원을 병행하는 전환", "전기차 · 하이브리드 · 수소전기차", "사업보고서는 전기차, 하이브리드차, 수소전기차를 모두 주요 제품으로 제시합니다.", "한 가지 동력원보다 지역별 충전 환경과 소비자 수요에 맞춘 제품 구성이 어떻게 바뀌는지 봐야 합니다."),
        _idea("차량 판매와 금융의 연결", "할부금융 · 리스 · 신용카드", "차량 제조·판매 외에 자동차할부금융, 리스, 신용카드가 별도 금융부문으로 운영됩니다.", "완성차 판매가 금융 계약과 고객 유지로 얼마나 이어지는지를 함께 읽는 것이 좋습니다."),
    ],
    "373220": [
        _idea("수요처가 다른 배터리 포트폴리오", "EV · ESS · IT기기", "사업보고서는 EV, ESS, IT기기 등 다양한 분야에 쓰이는 2차전지 제조·판매를 단일 사업으로 설명합니다.", "전기차 수요 변화가 ESS와 소형전지 수요로 얼마나 보완되는지를 확인할 필요가 있습니다."),
        _idea("제품 형태와 고객 수요의 차이", "파우치형 · 원통형 · 소형전지", "IT기기용 파우치형, 원통형 전지, 전동공구와 e-mobility용 전지가 함께 제시됩니다.", "같은 배터리라도 어떤 제품군이 성장하는지에 따라 생산과 수익성의 방향이 달라질 수 있습니다."),
    ],
    "012450": [
        _idea("수주부터 납품까지의 시간", "항공 · 방산 · 해양", "항공기 엔진·부품, 자주포·유도무기, 선박·해양플랜트가 장기 프로젝트 성격의 사업으로 함께 제시됩니다.", "수주 증가가 실제 매출로 반영되는 시점과 납품 일정의 안정성을 따로 봐야 합니다."),
        _idea("방산 수출의 확장", "자주포 · 장갑차 · 유도무기", "방산 부문은 자주포, 장갑차, 유도무기, 탄약 등 군수장비 생산을 중심으로 구성됩니다.", "수출 계약 이후 생산·정비·부품 공급까지 이어지는 사업의 지속성을 확인할 필요가 있습니다."),
    ],
    "402340": [
        _idea("제조사가 아닌 투자 포트폴리오", "투자 · 커머스 · 플랫폼 · 모빌리티", "사업보고서에는 투자사업과 11번가 커머스, 플랫폼, 모빌리티 사업이 함께 구분되어 있습니다.", "각 자회사의 매출과 지주회사 자체의 성과를 구분해 읽는 것이 중요합니다."),
        _idea("자회사마다 다른 성장 방식", "커머스 · TMAP · 앱 플랫폼", "커머스는 거래액, 모빌리티는 이동·데이터 서비스, 플랫폼은 이용자 기반이 사업의 핵심이 됩니다.", "포트폴리오 전체가 어떤 사업에 투자하고 재편되는지를 중심으로 볼 필요가 있습니다."),
    ],
    "207940": [
        _idea("생산과 개발을 함께 맡는 CDMO", "위탁생산 · 위탁개발", "바이오의약품 위탁생산뿐 아니라 세포주와 제형, 공정 개발 서비스를 함께 제공합니다.", "고객과의 관계가 생산 물량과 개발 서비스로 길게 이어지는지 확인하는 것이 좋습니다."),
        _idea("생산 품목의 확장", "mRNA · ADC · 세포·유전자 치료제", "항체의약품 외에 mRNA, ADC, 세포·유전자 치료제 등이 사업보고서의 주요 서비스로 제시됩니다.", "새로운 의약품 형태를 실제 생산 서비스로 얼마나 빠르게 확장하는지가 다음 성장 축입니다."),
    ],
    "034020": [
        _idea("발전원 전환을 아우르는 설비", "원전 · 가스터빈 · 해상풍력", "원자력·복합화력 발전설비 제작과 EPC, 해상풍력 기자재, 연료전지 사업이 함께 제시됩니다.", "국가별 전력 수요와 에너지 정책 변화가 어느 사업으로 연결되는지 나눠 봐야 합니다."),
        _idea("EPC 사업의 긴 매출 경로", "설계 · 제작 · 설치", "발전설비 EPC는 계약 이후 설계와 제작, 설치 과정을 거쳐 매출이 발생합니다.", "수주 금액뿐 아니라 프로젝트의 진행과 납품 단계가 안정적인지 확인할 필요가 있습니다."),
    ],
    "105560": [
        _idea("은행 밖의 수익원", "증권 · 보험 · 카드", "은행의 여신·수신 업무 외에 증권, 손해보험, 신용카드가 주요 사업부문으로 구성됩니다.", "이자수익과 수수료, 보험·투자 수익이 각각 어떻게 움직이는지 구분해 봐야 합니다."),
        _idea("하나의 고객 접점", "예금 · 대출 · 카드 · 보험 · 증권", "KB스타뱅킹과 은행·카드·보험·증권 서비스가 그룹 안에서 함께 제공됩니다.", "고객이 한 서비스를 이용한 뒤 다른 금융상품으로 얼마나 확장되는지를 보는 것이 좋습니다."),
    ],
    "000270": [
        _idea("차종 구성이 수익성을 바꾼다", "승용 · RV · 상용 · 전기차", "승용차, RV, 상용차에 전기차와 하이브리드 제품이 더해지는 완성차 사업으로 제시됩니다.", "전체 판매 대수보다 수익성이 높은 차종의 비중이 어떻게 바뀌는지를 확인할 필요가 있습니다."),
        _idea("판매 뒤까지 이어지는 책임", "판매보증", "완성차 판매 뒤에는 품질보증과 리콜 관련 책임이 뒤따를 수 있습니다.", "판매 확대와 별개로 보증 부담이 이익률을 누르지 않는지 함께 봐야 합니다."),
    ],
    "329180": [
        _idea("선박과 엔진이 함께 움직이는 구조", "조선 · 해양플랜트 · 엔진기계", "LNG선·컨테이너선·유조선 건조, 해양플랜트, 선박용 엔진과 발전설비 사업이 함께 구성됩니다.", "어떤 선종의 수주가 늘고 있는지와 엔진 수요가 어떻게 따라오는지를 나눠 볼 필요가 있습니다."),
        _idea("장기 프로젝트의 원가 관리", "선가 · 기자재 · 납기", "조선 사업은 계약 후 건조 기간이 길고, 원가와 납품 일정이 수익성에 영향을 줍니다.", "고부가 선종의 비중과 프로젝트 원가 관리가 안정적인지 확인하는 것이 중요합니다."),
    ],
    "032830": [
        _idea("보험 판매와 자산 운용", "생명 · 건강 · 연금 · 저축", "생명·건강·연금·저축성 보험을 판매하고, 장기 보험 자산을 운용하는 구조입니다.", "보험 계약에서 나오는 수익과 자산 운용 성과를 한쪽만 보지 않는 것이 좋습니다."),
        _idea("장기 고객 기반", "보장성 보험 · 연금", "보험 상품은 단기 판매량보다 계약이 장기간 유지되며 보험료가 계속 들어오는 구조가 중요합니다.", "보장성 보험과 연금보험의 비중 변화가 고객 기반의 질을 보여줄 수 있습니다."),
    ],
    "028260": [
        _idea("서로 다른 경기 사이클", "건설 · 상사 · 패션 · 리조트", "건설은 수주 산업, 상사는 원자재·에너지 거래, 패션은 소비, 리조트는 방문객 수요에 영향을 받는 사업으로 구성됩니다.", "전체 매출보다 어느 부문이 실적을 움직였는지 나눠 읽어야 합니다."),
        _idea("건설 수주의 실행력", "건축 · 토목 · 플랜트 · 주택", "건설 부문은 계약을 맺은 뒤 공사를 진행하며 매출을 인식합니다.", "신규 수주뿐 아니라 진행 중인 프로젝트의 원가와 회수 가능성도 함께 확인해야 합니다."),
    ],
    "055550": [
        _idea("금융 수익원의 분산", "은행 · 카드 · 증권 · 보험", "여신·수신을 맡는 은행 외에 카드, 증권, 생명·손해보험 사업이 함께 제시됩니다.", "은행 실적만으로 그룹 전체를 판단하지 말고 사업부문별 이익원을 나눠 봐야 합니다."),
        _idea("대손충당금의 의미", "대출 성장 · 신용손실 관리", "대출채권에 대한 신용손실충당금 측정이 사업보고서의 주요 감사사항으로 제시됩니다.", "대출이 늘어도 차주의 상환 능력이 악화되면 충당금이 증가할 수 있다는 점을 함께 봐야 합니다."),
    ],
    "068270": [
        _idea("현재 매출과 다음 제품", "바이오시밀러 · 신약", "항체 바이오시밀러와 신약 개발·판매, 케미컬 의약품 판매가 함께 사업을 이룹니다.", "판매 중인 제품의 현금 창출력과 신제품 개발의 성과를 구분해 보는 것이 좋습니다."),
        _idea("개발비의 불확실성", "개발비 인식 · 손상", "내부창출 개발비의 인식과 손상이 주요 감사사항으로 제시됩니다.", "연구개발 투자가 미래 제품으로 이어지는지와 비용 부담을 함께 확인할 필요가 있습니다."),
    ],
    "009150": [
        _idea("고객 산업이 다른 세 부품", "MLCC · 패키지기판 · 카메라모듈", "컴포넌트, 반도체 패키지기판, 광학솔루션이 서로 다른 고객 산업에 공급됩니다.", "스마트폰·자동차·AI 서버 수요가 각 부문에 다르게 반영된다는 점을 봐야 합니다."),
        _idea("고사양 제품의 비중", "고용량 MLCC · 고난도 기판", "수동소자와 기판, 카메라모듈은 범용 제품과 고사양 제품이 함께 존재합니다.", "매출 증가보다 어떤 부품의 제품 구성이 좋아지는지가 수익성에 더 중요할 수 있습니다."),
    ],
    "006400": [
        _idea("서로 다른 배터리 수요", "EV · ESS · 전자재료", "전기차와 ESS, IT기기용 전지 및 반도체·디스플레이 소재가 함께 사업부문으로 제시됩니다.", "전기차 수요 변화가 전자재료와 다른 배터리 제품군으로 얼마나 보완되는지 봐야 합니다."),
        _idea("고객 생산계획과 배터리 주문", "생산능력 · 고객 수요", "배터리 판매는 고객사의 전기차·ESS 생산 계획과 연결됩니다.", "증설 자체보다 실제 가동과 판매까지 이어지는지를 확인하는 것이 중요합니다."),
    ],
    "042660": [
        _idea("세 가지 수주 시장", "상선 · 해양 · 특수선", "LNG·원유·컨테이너선 같은 상선, 해양플랜트, 잠수함·구축함 같은 특수선 사업이 함께 구성됩니다.", "해운·에너지·방산 수요가 각각 어느 부문에 반영되는지 나눠 봐야 합니다."),
        _idea("고부가 선종의 비중", "LNG선 · FPSO · 특수선", "기술 난도가 높은 LNG선과 FPSO, 특수선은 일반 상선과 계약과 수익 구조가 다릅니다.", "단순 수주 금액보다 어떤 선종이 늘어나는지를 중심으로 읽는 것이 좋습니다."),
    ],
    "267260": [
        _idea("전력망을 구성하는 장비", "변압기 · 차단기 · 배전기기", "변압기, 차단기, 회전기, 배전기기 등 전력기기를 제조·공급합니다.", "전력망 확장과 교체, 산업단지·데이터센터 투자가 장비 수요로 이어지는지 확인할 필요가 있습니다."),
        _idea("해외 수주와 납품의 시간", "사양 · 제작 · 납품", "대형 전력기기는 고객별 사양과 인증, 제작 기간이 중요한 사업입니다.", "수주 증가가 매출과 이익으로 넘어오는 속도를 함께 봐야 합니다."),
    ],
    "006800": [
        _idea("서로 다른 증권사 수익원", "WM · IB · 트레이딩 · PI", "고객자산 관리, 기업금융, 주식·채권 매매, 자기자본투자가 함께 사업부문으로 제시됩니다.", "고객 거래에서 나오는 수수료와 시장 가격 변동에 민감한 운용수익을 구분해야 합니다."),
        _idea("장기 투자와 기업금융", "IPO · M&A · 인수금융", "IB는 IPO와 인수금융, M&A 등 기업 거래를 지원하고 PI는 자체 자본으로 투자합니다.", "거래 환경과 투자자산 가치 변화가 이익에 어떤 영향을 주는지 확인할 필요가 있습니다."),
    ],
    "012330": [
        _idea("완성차와 A/S의 두 축", "모듈·부품 · A/S 부품", "자동차 핵심모듈과 제동·조향·전장 부품을 공급하는 사업, 판매된 차량의 보수용 부품을 공급하는 사업이 함께 있습니다.", "완성차 생산에 민감한 모듈과 반복 수요가 있는 A/S 부품을 구분해 봐야 합니다."),
        _idea("전동화로 바뀌는 부품 구성", "전장 · 전동화 부품", "기존 제동·조향·램프 부품에 전장과 전동화 부품이 더해지고 있습니다.", "어떤 부품이 성장하고 기존 부품 수요가 어떻게 바뀌는지 보는 것이 중요합니다."),
    ],
    "010130": [
        _idea("여러 금속을 함께 회수하는 제련", "아연 · 연 · 금 · 은 · 동", "아연과 연을 제련하면서 금·은·동 같은 금속도 회수해 판매하는 사업입니다.", "한 금속 가격보다 여러 금속 가격과 제련 수수료가 함께 실적에 영향을 준다는 점을 봐야 합니다."),
        _idea("자원순환과 배터리 원료", "전자폐기물 · 황산니켈", "전자폐기물과 제강분진을 처리하는 자원순환, 황산니켈 등 2차전지 원료 사업이 함께 제시됩니다.", "원료 확보와 재활용 능력이 신규 소재 사업으로 이어지는지 확인할 필요가 있습니다."),
    ],
    "086790": [
        _idea("은행과 비은행의 조합", "은행 · 증권 · 카드 · 캐피탈", "예금·대출·외환을 맡는 은행 외에 증권, 카드, 캐피탈, 보험이 함께 운영됩니다.", "순이자이익과 비은행 수수료 수익이 각각 어떻게 움직이는지 구분해 봐야 합니다."),
        _idea("대출 성장의 질", "충당금 · 연체 관리", "상각후원가측정 대출채권의 신용손실충당금 측정이 주요 감사사항으로 제시됩니다.", "대출 성장과 건전성 관리가 함께 유지되는지를 확인해야 합니다."),
    ],
    "035420": [
        _idea("검색에서 거래로 이어지는 플랫폼", "서치 · 커머스 · 핀테크", "검색광고와 디스플레이 광고, 쇼핑·라이브커머스, 간편결제와 금융 비교 서비스가 함께 운영됩니다.", "이용자 트래픽이 광고·거래·결제로 얼마나 수익화되는지 보는 것이 좋습니다."),
        _idea("콘텐츠 IP의 확장", "웹툰 · 웹소설 · 카메라앱", "웹툰·웹소설과 카메라앱 등 디지털 콘텐츠 사업이 별도 부문으로 제시됩니다.", "이용자 기반이 구독·광고·해외 유통과 2차 사업으로 어떻게 연결되는지 확인할 필요가 있습니다."),
    ],
    "005490": [
        _idea("고객 산업이 다른 철강 제품", "자동차 · 조선 · 가전 · 건설", "열연·냉연·후판·스테인리스 등 철강 제품은 자동차, 조선, 가전, 건설 등 서로 다른 산업에 공급됩니다.", "전체 철강 수요보다 어떤 고객 산업의 수요가 변하는지 나눠 봐야 합니다."),
        _idea("철강 밖의 인프라 사업", "무역 · LNG · 건설 · 물류", "철강 외에 무역과 LNG, 건설, 물류 등 인프라 사업이 함께 구성됩니다.", "철강 본업과 인프라 자회사가 각각 어떤 역할을 하는지 구분해 읽는 것이 좋습니다."),
    ],
    "298040": [
        _idea("전력기기와 건설의 다른 시장", "변압기 · 차단기 · 건설", "전력기기·산업설비 제조와 주택·상업시설·SOC 건설이 함께 사업부문으로 제시됩니다.", "전력기기 호조가 건설 부문의 변동성을 얼마나 보완하는지 볼 필요가 있습니다."),
        _idea("전력망 투자 수요", "변압기 · STATCOM · ESS", "변압기, 차단기, 전동기와 STATCOM·ESS 등 전력 시스템 제품을 제공합니다.", "해외 전력망 투자와 신재생에너지 확장이 실제 수주와 납품으로 이어지는지 확인해야 합니다."),
    ],
    "009540": [
        _idea("여러 자회사가 나누는 조선 사업", "조선 · 해양 · 엔진 · 그린에너지", "선박 건조와 해양플랜트, 선박용 엔진, 태양광·연료전지·수전해 사업이 함께 제시됩니다.", "어느 자회사가 수주와 이익을 이끄는지 구분해 보는 것이 좋습니다."),
        _idea("선종별 수주의 질", "LNG선 · 컨테이너선 · 유조선", "LNG선, 컨테이너선, 원유운반선과 해양플랜트는 건조 난도와 계약 기간이 서로 다릅니다.", "고부가 선종의 비중과 프로젝트 원가 관리가 안정적인지 확인할 필요가 있습니다."),
    ],
    "015760": [
        _idea("판매가격과 발전원가의 차이", "전기요금 · 연료비", "전력 판매와 원자력·화력 발전, 발전소 설계·정비 사업이 함께 구성됩니다.", "전기 판매가격과 연료비가 얼마나 벌어져 있는지가 사업의 핵심입니다."),
        _idea("발전원 구성의 변화", "원전 · 화력 · 신재생", "원전, 화력, 신재생 발전은 설비와 연료비 구조가 다릅니다.", "발전량보다 어떤 발전원이 전기를 생산했는지를 함께 봐야 비용 구조를 이해할 수 있습니다."),
    ],
    "010120": [
        _idea("전력망과 공장을 함께 겨냥", "전력기기 · 자동화 · IT", "전력기기·전력시스템, PLC·인버터 자동화, 데이터센터·스마트팩토리 IT 사업이 함께 운영됩니다.", "전력 인프라 투자와 제조업 자동화가 각각 어느 부문에 반영되는지 구분해 봐야 합니다."),
        _idea("데이터센터와 신재생 수요", "전력 시스템 · 스마트팩토리", "전력을 안정적으로 공급하고 제어하는 제품과 시스템을 제공합니다.", "데이터센터와 신재생에너지 확장이 기기 판매를 넘어 시스템·IT 서비스로 이어지는지 확인할 필요가 있습니다."),
    ],
    "042700": [
        _idea("AI 메모리 공정의 장비", "HBM TC 본더 · 검사장비", "HBM TC 본더와 하이브리드 본더, 검사장비 등 반도체 제조용 장비를 주요 제품으로 제시합니다.", "메모리 업체의 HBM 투자 계획이 장비 주문으로 얼마나 연결되는지가 핵심입니다."),
        _idea("고객 설비투자의 시간차", "수주 · 제작 · 납품", "장비 매출은 고객사가 증설하거나 공정 세대 전환을 결정하는 시점에 영향을 받습니다.", "수주가 늘어난 뒤 실제 납품과 매출로 이어지는 시점을 함께 봐야 합니다."),
    ],
    "034730": [
        _idea("지주회사 안의 여러 업황", "IT · 정유화학 · 배터리", "지주·투자사업 외에 IT서비스, 석유·화학, 배터리, 에너지·전력 사업이 함께 제시됩니다.", "단일 제품 실적보다 자회사별 업황이 그룹 전체에 어떻게 반영되는지 봐야 합니다."),
        _idea("에너지 사업의 서로 다른 논리", "정유 · 화학 · 배터리", "정유는 유가와 정제마진, 화학은 제품 스프레드, 배터리는 전기차 수요와 설비투자에 영향을 받습니다.", "사업별 회복 속도가 다를 수 있으므로 하나의 에너지 지표로 묶어 보지 않는 것이 좋습니다."),
    ],
    "316140": [
        _idea("은행 중심에서 비은행 확장", "보험 · 카드 · 캐피탈 · 증권", "은행 외에 보험, 신용카드, 자동차·기업금융 캐피탈, 증권 사업이 함께 구성됩니다.", "순이자이익과 비은행 수수료·보험 수익이 각각 어떤 역할을 하는지 볼 필요가 있습니다."),
        _idea("대출과 건전성의 균형", "순이자이익 · 충당금", "은행 사업은 예금과 대출에서 이자수익을 만들고, 대출채권의 신용손실충당금 측정이 주요 감사사항으로 제시됩니다.", "대출 성장과 충당금 부담이 함께 관리되는지 확인해야 합니다."),
    ],
    "272210": [
        _idea("방산전자와 ICT의 다른 계약", "레이다 · 전투체계 · IT서비스", "감시정찰·지휘통제통신·항공전자·해양시스템 등 방산과 IT 아웃소싱·SI·디지털 플랫폼이 함께 운영됩니다.", "수주형 방산 매출과 반복 서비스 성격의 ICT 매출을 나눠 봐야 합니다."),
        _idea("위성과 방산 전자기술", "위성 탑재체 · 감시정찰", "위성 탑재체와 레이다, 전자광학 장비가 주요 제품으로 제시됩니다.", "개발 단계와 실제 납품 단계가 어디인지 구분해 보는 것이 중요합니다."),
    ],
    "010140": [
        _idea("고부가 선박과 해양플랫폼", "LNG선 · 컨테이너선 · LNG-FPSO", "LNG선과 초대형 컨테이너선, 유조선, LNG-FPSO와 FPU가 주요 제품으로 제시됩니다.", "수주 금액보다 고부가 프로젝트의 비중이 어떻게 바뀌는지 보는 것이 좋습니다."),
        _idea("수주 뒤의 원가와 납기", "기자재 · 공정 관리", "조선해양 사업은 계약 이후 원가와 일정 변화가 수익성에 영향을 줄 수 있습니다.", "복잡한 공정률 산식보다 원가 상승과 납기 지연 위험이 줄고 있는지 확인하는 편이 이해하기 쉽습니다."),
    ],
    "051910": [
        _idea("네 가지 사업의 다른 사이클", "석유화학 · 첨단소재 · 생명과학 · 배터리", "석유화학, 첨단소재, 생명과학과 LG에너지솔루션이 함께 연결되어 있습니다.", "전통 화학 경기와 배터리 소재·의약품 사업이 같은 방향으로 움직이지 않는다는 점을 봐야 합니다."),
        _idea("첨단소재의 고객 산업", "전지소재 · 전자소재", "양극재·분리막·전자소재는 자동차, 반도체, 디스플레이 산업과 연결됩니다.", "화학 제품 가격뿐 아니라 고객 산업의 투자와 수요 변화도 함께 확인할 필요가 있습니다."),
    ],
    "064350": [
        _idea("방산과 철도의 장기 수주", "K2전차 · 철도차량", "K2전차·장갑차 등 방산과 고속철·전동차 등 레일 사업이 함께 제시됩니다.", "수주가 늘어도 매출은 생산과 납품을 거쳐 여러 해에 걸쳐 나타날 수 있습니다."),
        _idea("새 사업의 확장 단계", "수소 · 로봇 · 스마트물류", "에코플랜트 부문에서 수소 인프라, 산업용 로봇, 스마트물류 사업을 추진합니다.", "초기 사업은 수주와 실적 전환 단계를 구분해 보는 것이 좋습니다."),
    ],
    "000810": [
        _idea("보험마다 다른 손익 구조", "자동차 · 일반 · 장기보험", "자동차보험, 화재·해상 등 일반보험, 장기손해보험이 함께 주요 사업으로 제시됩니다.", "보험료 수입만 보지 말고 사고율·수리비·계약 유지에 따라 달라지는 손익을 나눠 봐야 합니다."),
        _idea("해외 보험의 역할", "해외 손해보험", "인도네시아·베트남·유럽 등 해외 보험 사업이 함께 운영됩니다.", "해외 매출 확대가 현지 손해율과 규제, 환율을 감안해 이익으로 이어지는지 확인할 필요가 있습니다."),
    ],
    "000150": [
        _idea("자회사 포트폴리오", "전자소재 · IT · 발전 · 건설기계", "CCL 전자소재, IT 시스템·클라우드, 발전플랜트, 건설기계 등 서로 다른 사업이 함께 구성됩니다.", "특정 자회사의 성과를 그룹 전체 실적과 구분해 보는 것이 중요합니다."),
        _idea("반도체와 전자기기용 소재", "CCL", "전자BG는 PCB 기판소재인 CCL을 생산·공급합니다.", "서버·통신·자동차 전장 수요 변화가 전자소재 사업에 어떻게 반영되는지 확인할 필요가 있습니다."),
    ],
    "035720": [
        _idea("카카오톡에서 거래로", "광고 · 커머스 · 모빌리티 · 결제", "카카오톡 기반의 광고·커머스·모빌리티·결제 서비스가 플랫폼 부문에 함께 제시됩니다.", "이용자 기반이 광고, 거래, 결제로 얼마나 수익화되는지 보는 것이 좋습니다."),
        _idea("콘텐츠 IP의 확장", "게임 · 음악 · 웹툰 · 영상", "게임, 음악, 웹툰, 영상 콘텐츠 제작과 유통이 별도 콘텐츠 부문으로 구성됩니다.", "플랫폼과 달리 흥행 변동성이 큰 콘텐츠가 해외 유통과 2차 사업으로 이어지는지 확인할 필요가 있습니다."),
    ],
    "079550": [
        _idea("방산 전자 체계", "유도무기 · 레이다 · C4I", "유도무기, 감시정찰 레이다·센서, 지휘통제·통신 체계가 주요 사업 카드로 분류됩니다.", "무기 한 종류보다 체계별 수주가 어떻게 늘어나는지 구분해 보는 것이 좋습니다."),
        _idea("수주 이후의 양산", "생산능력 · 납품 일정", "방산 사업은 수주 뒤 생산능력을 확보하고 장기간에 걸쳐 납품하는 구조입니다.", "해외 수출 계약이 실제 양산과 납품으로 이어지는지를 확인해야 합니다."),
    ],
    "096770": [
        _idea("같은 에너지 안의 다른 사업", "정유 · 화학 · LNG · 배터리", "원유 정제와 화학소재, LNG·전력, 전기차·ESS용 배터리 사업이 함께 구성됩니다.", "유가와 정제마진, 화학 스프레드, 전기차 수요를 각각 나눠 봐야 합니다."),
        _idea("배터리의 성장 투자", "생산능력 · 고객 수요", "배터리 사업은 생산능력을 미리 확보해야 하지만 고객 수요가 기대보다 늦어지면 투자 부담이 커질 수 있습니다.", "기존 정유·에너지 사업이 배터리 투자 부담을 얼마나 보완하는지 확인할 필요가 있습니다."),
    ],
    "011200": [
        _idea("두 가지 해운 운임", "컨테이너 · 벌크", "컨테이너 수송과 유조선·건화물선 등 벌크 운송, 터미널 운영이 함께 사업을 이룹니다.", "소비재·제조업 물동량에 민감한 컨테이너와 원자재·에너지 수송에 연결된 벌크를 구분해 봐야 합니다."),
        _idea("선대와 터미널의 경쟁력", "운항 · 항만 · 연료", "선박 운송 외에 터미널 운영과 LNG 연료선 등도 사업에 포함됩니다.", "운임이 약해지는 국면에는 선대 운영과 항만·연료 효율이 비용 경쟁력으로 이어지는지 확인할 필요가 있습니다."),
    ],
    "017670": [
        _idea("반복 매출의 통신 기반", "5G · 초고속인터넷 · IPTV", "이동통신과 유선통신, IPTV, 데이터센터 서비스가 함께 운영됩니다.", "가입자 기반에서 나오는 반복 매출과 신규 서비스의 성장을 구분해 보는 것이 좋습니다."),
        _idea("통신망 위의 데이터센터", "AI · 데이터센터", "통신 네트워크 역량을 바탕으로 데이터센터와 기업용 서비스로 사업을 넓히고 있습니다.", "신규 사업은 기존 통신 서비스와 달리 투자와 초기 비용이 함께 발생한다는 점을 봐야 합니다."),
    ],
    "000720": [
        _idea("서로 다른 건설 수주", "주택 · 토목 · 플랜트 · 원전", "국내 주택과 토목, 석유화학 플랜트, 원전·SMR, 신재생에너지·송변전 사업이 함께 제시됩니다.", "부동산 경기, 해외 에너지 투자, 장기 정책 수요가 어느 부문에 반영되는지 나눠 봐야 합니다."),
        _idea("수주보다 실행력", "원가 · 일정 · 회수", "건설업은 계약 뒤 공사를 진행하는 동안 원가와 일정이 바뀔 수 있습니다.", "신규 수주와 별개로 진행 중인 프로젝트의 원가와 납기, 대금 회수가 안정적인지 확인해야 합니다."),
    ],
    "267250": [
        _idea("서로 다른 업황의 그룹", "조선 · 정유 · 전력기기 · 건설기계", "선박·해양플랜트, 석유제품, 전력기기, 건설기계가 한 그룹 안에 함께 제시됩니다.", "한 사업의 부진을 다른 사업이 보완할 수 있지만, 사업별 업황이 동시에 움직이지 않는다는 점을 봐야 합니다."),
        _idea("사업별로 다른 실적 변수", "선가 · 정제마진 · 전력망 · 인프라", "조선은 장기 수주, 정유는 유가·정제마진, 전력기기는 전력망 투자, 건설기계는 경기와 인프라 투자에 영향을 받습니다.", "그룹 전체 수치보다 어떤 사업이 성과를 이끌었는지 구분해 보는 것이 좋습니다."),
    ],
    "138040": [
        _idea("금융 자회사별 이익 원리", "손해보험 · 증권 · 여신금융", "손해보험, 증권중개·자산관리·기업금융, 리스·할부금융·대출이 함께 사업부문으로 제시됩니다.", "보험의 손해율, 증권의 거래·운용 성과, 여신의 신용위험을 나눠 봐야 합니다."),
        _idea("보험과 투자 성과의 구분", "보험금 · 운용손익", "보험은 사고와 보험금 지급, 금융투자는 시장 가격과 운용 성과에 영향을 받습니다.", "금융시장 호조만으로 그룹 이익을 설명하지 말고 어느 부문에서 이익이 났는지 확인할 필요가 있습니다."),
    ],
    "003670": [
        _idea("배터리 소재와 기존 소재", "양극재 · 음극재 · 내화물", "양극재·음극재 등 에너지소재와 내화물·라임화성 사업이 함께 구성됩니다.", "배터리 소재 수요가 약할 때 기존 철강 관련 소재 사업이 어떤 역할을 하는지 봐야 합니다."),
        _idea("증설과 실제 판매의 차이", "생산능력 · 고객 수요", "양극재와 음극재 공장 확대는 고객사의 배터리 주문과 연결되어야 실적으로 이어집니다.", "생산능력 증가뿐 아니라 실제 가동과 판매가 따라오는지 확인하는 것이 중요합니다."),
    ],
    "033780": [
        _idea("본업과 별도 성장 축", "담배 · 차세대담배 · 건강기능식품", "궐련과 HNB가 담배사업의 중심이고, 홍삼 등 건강기능식품이 별도 사업부문으로 구성됩니다.", "담배와 건강기능식품은 고객 수요와 유통 구조가 다르므로 따로 봐야 합니다."),
        _idea("차세대담배의 직접 판매", "온라인몰 전환", "사업보고서에는 위탁 방식의 HNB 디바이스 온라인 판매를 직접 사업 방식으로 전환한 내용이 제시됩니다.", "단순 판매지역 확대가 아니라 고객 접점과 유통 효율을 높이는 변화로 읽는 편이 적절합니다."),
    ],
}


def _flatten_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _flatten_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _flatten_strings(item)


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _truncate(text: str | None, limit: int = 360) -> str | None:
    if not text:
        return None
    text = _clean(text)
    if len(text) <= limit:
        return text
    cut = text[:limit].rstrip()
    last = max(cut.rfind("."), cut.rfind("다."), cut.rfind("니다."))
    if last > limit * 0.55:
        return cut[: last + 1]
    return text


def _first_snippet(strings: list[str], patterns: list[str], limit: int = 380) -> str | None:
    lowered_patterns = [p.lower() for p in patterns]
    for raw in strings:
        text = _clean(raw)
        if len(text) < 45:
            continue
        lower = text.lower()
        if any(pattern in lower for pattern in lowered_patterns):
            return _truncate(text, limit)
    return None


def _extract_raw_moves(text: str | None) -> list[dict[str, Any]]:
    if not text:
        return []
    moves: list[dict[str, Any]] = []
    clauses = re.split(r"[.。,;]", _clean(text).replace("하였고", "하였고.").replace("하였으며", "하였으며."))
    pattern = re.compile(r"([가-힣A-Za-z0-9·ㆍ\-\s]{2,36}?)\s*가격(?:은|이)?\s*[^.]{0,42}?약\s*([0-9.]+)%\s*(상승|하락)")
    for clause in clauses:
        match = pattern.search(clause)
        if not match:
            continue
        name, pct, direction = match.groups()
        name = re.sub(r"^(및|중|부문의|원재료인|주요 원재료인)\s*", "", _clean(name))
        name = re.sub(r"^.*?(DX 부문|DS 부문|SDC|Harman)의\s+", "", name)
        if not name or len(name) > 30 or "유사한 수준" in name:
            continue
        signed = float(pct) * (1 if direction == "상승" else -1)
        moves.append({"name": name, "pct": signed, "direction": direction})
    return moves[:8]


def _extract_utilization(text: str | None) -> list[dict[str, Any]]:
    if not text:
        return []
    items: list[dict[str, Any]] = []
    pattern = re.compile(r"([가-힣A-Za-z0-9·ㆍ,\s]{2,24}?)(?:은|는)\s*([0-9.]+)%")
    for name, pct in pattern.findall(text):
        value = float(pct)
        if value <= 0 or value > 100:
            continue
        name = _clean(name).strip(" ,")
        if len(name) < 2 or "년" in name:
            continue
        items.append({"name": name, "rate": value})
    deduped: list[dict[str, Any]] = []
    seen = set()
    for item in items:
        key = (item["name"], item["rate"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped[:6]


def _load_report_snippets(corp_code: str, report_index: dict[str, Any]) -> dict[str, Any]:
    meta = report_index.get(corp_code) or {}
    rcept_no = meta.get("rcept_no")
    parsed_path = ROOT / "modules" / "disclosure" / "data" / "fulltext" / corp_code / str(rcept_no) / "parsed.json"
    summary_path = ROOT / "modules" / "disclosure" / "data" / "fulltext" / corp_code / str(rcept_no) / "summary.json"
    snippets = {
        "overview": None,
        "raw_material": None,
        "capacity": None,
        "segment_finance": None,
        "segment_breakdown": [],
        "investor_note": None,
        "products": [],
        "raw_moves": [],
        "utilization": [],
    }
    if not parsed_path.exists():
        return snippets
    try:
        parsed = json.loads(parsed_path.read_text(encoding="utf-8"))
    except Exception:
        return snippets

    strings = [_clean(s) for s in _flatten_strings(parsed)]
    snippets["overview"] = _first_snippet(
        strings,
        ["사업별로 보면", "사업의 개요", "주요 제품 및 서비스", "제품을 생산", "서비스를 제공"],
        420,
    )
    snippets["raw_material"] = _first_snippet(
        strings,
        ["주요 원재료 가격 변동", "원재료 가격", "주요 원재료"],
        460,
    )
    snippets["capacity"] = _first_snippet(
        strings,
        ["생산능력, 생산실적, 가동률", "가동률", "생산능력"],
        460,
    )
    snippets["segment_finance"] = _first_snippet(
        strings,
        ["사업부문별 요약 재무 현황", "부문별 요약 재무", "부문별 매출"],
        460,
    )
    if summary_path.exists():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            snippets["segment_breakdown"] = [
                {
                    "name": _clean(segment.get("name")),
                    "desc": _clean(segment.get("desc")),
                    "revenue_share": float(segment.get("revenue_share")),
                }
                for segment in summary.get("segments", [])
                if segment.get("name") and segment.get("revenue_share") is not None
            ]
            snippets["investor_note"] = _clean(summary.get("investor_notes"))
            snippets["products"] = [
                _clean(product)
                for product in summary.get("products", [])
                if _clean(product)
            ]
        except Exception:
            pass
    snippets["raw_moves"] = _extract_raw_moves(snippets["raw_material"])
    snippets["utilization"] = _extract_utilization(snippets["capacity"])
    return snippets


def _to_krw_from_eok(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number == 0:
        return None
    return number * 100_000_000


def _load_market_snapshot(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    today = datetime.now().strftime("%Y-%m-%d")
    if MARKET_SNAPSHOT_PATH.exists():
        try:
            cached = json.loads(MARKET_SNAPSHOT_PATH.read_text(encoding="utf-8"))
            if cached.get("date") == today and isinstance(cached.get("items"), dict):
                return cached["items"]
        except Exception:
            pass

    items: dict[str, dict[str, Any]] = {}
    try:
        import yfinance as yf  # type: ignore
    except Exception as exc:
        print(f"market snapshot skipped: yfinance import failed ({exc})")
        return items

    for row in rows:
        code = str(row.get("stock_code") or "").zfill(6)
        if not code or not code.isdigit():
            continue
        ticker = f"{code}.KS"
        try:
            info = yf.Ticker(ticker).fast_info
            market_cap = getattr(info, "market_cap", None)
            last_price = getattr(info, "last_price", None)
            if market_cap:
                items[code] = {
                    "ticker": ticker,
                    "market_cap": float(market_cap),
                    "last_price": float(last_price) if last_price else None,
                }
        except Exception:
            continue

    try:
        MARKET_SNAPSHOT_PATH.write_text(
            json.dumps({"date": today, "items": items}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass
    return items


def _load_business_cards() -> dict[str, list[dict[str, Any]]]:
    """Restore the archived orbit-card visuals for the static reader."""
    if not DISCLOSURE_DB_PATH.exists():
        return {}

    cards_by_stock: dict[str, list[dict[str, Any]]] = {}
    try:
        with sqlite3.connect(DISCLOSURE_DB_PATH) as conn:
            rows = conn.execute(
                """
                SELECT stock_code, card_title, card_caption, card_kind, visual_label,
                       image_url, image_source, local_path
                FROM business_card_visual
                ORDER BY stock_code, id
                """
            ).fetchall()
    except sqlite3.Error:
        return {}

    for (
        stock_code,
        title,
        caption,
        kind,
        visual,
        image_url,
        image_source,
        local_path,
    ) in rows:
        code = str(stock_code or "").zfill(6)
        image = image_url
        if local_path:
            local_file = ROOT / str(local_path)
            if local_file.exists():
                image = os.path.relpath(local_file, OUT_PATH.parent).replace("\\", "/")
        cards_by_stock.setdefault(code, []).append(
            {
                "title": title,
                "caption": caption,
                "kind": kind,
                "visual": visual,
                "image": image,
                "image_source": image_source,
            }
        )
    return cards_by_stock


def _simplify_row(
    row: dict[str, Any],
    rank: int,
    report_index: dict[str, Any],
    market_snapshot: dict[str, dict[str, Any]],
    business_cards: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    corp_code = row.get("corp_code") or ""
    report_meta = report_index.get(corp_code) or {}
    stock_code = str(row.get("stock_code") or "").zfill(6)
    latest_year = row.get("latest_year") or {}
    snapshot = market_snapshot.get(stock_code) or {}
    market_cap = snapshot.get("market_cap") or row.get("market_cap")
    net_income_krw = _to_krw_from_eok(latest_year.get("net_income"))
    ttm_per = None
    if market_cap and net_income_krw and net_income_krw > 0:
        ttm_per = float(market_cap) / net_income_krw
    percentile = row.get("percentile") or {}
    sector, display_category, badge_label = CATEGORY_BY_STOCK.get(
        stock_code,
        (percentile.get("_sector") or "사업", percentile.get("_sector") or "사업", "사업"),
    )
    return {
        "rank": rank,
        "name": row.get("name"),
        "stock_code": stock_code,
        "corp_code": corp_code,
        "sector": sector,
        "display_category": display_category,
        "badge_label": badge_label,
        "grade": row.get("grade"),
        "total": row.get("total"),
        "market_cap": market_cap,
        "last_price": snapshot.get("last_price"),
        "ttm_per": ttm_per,
        "dart_url": row.get("dart_url"),
        "latest_year": latest_year,
        "history": row.get("history") or {},
        "modules": row.get("modules") or {},
        "percentile": percentile,
        "report": {
            "name": report_meta.get("report_nm"),
            "date": report_meta.get("rcept_dt"),
            "rcept_no": report_meta.get("rcept_no"),
        },
        "snippets": _load_report_snippets(corp_code, report_index),
        "business_cards": business_cards.get(stock_code, []),
    }


HTML_TEMPLATE = r"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>국내상장기업 사업보고서 reader</title>
  <style>
    :root {
      color-scheme: dark;
      --bg:#060914;
      --panel:#0c1222;
      --panel2:#11182b;
      --line:rgba(148,163,184,.18);
      --text:#edf6ff;
      --soft:#b8c6d9;
      --muted:#7d8ba3;
      --cyan:#41dcff;
      --teal:#36e5bd;
      --pink:#ff4f7e;
      --gold:#f7d56f;
      --violet:#9d81ff;
      font-family: Inter, Pretendard, "Noto Sans KR", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin:0;
      min-height:100vh;
      background:
        radial-gradient(circle at 15% 4%, rgba(65,220,255,.18), transparent 28%),
        radial-gradient(circle at 86% 0%, rgba(255,79,126,.18), transparent 30%),
        radial-gradient(circle at 54% 74%, rgba(157,129,255,.14), transparent 38%),
        var(--bg);
      color:var(--text);
    }
    body::before {
      content:"";
      position:fixed;
      inset:0;
      pointer-events:none;
      background-image:
        radial-gradient(circle, rgba(255,255,255,.35) 0 1px, transparent 1.6px),
        radial-gradient(circle, rgba(65,220,255,.25) 0 1px, transparent 1.5px);
      background-size: 92px 92px, 137px 137px;
      background-position: 0 0, 42px 24px;
      opacity:.16;
    }
    a { color: inherit; }
    button, input { font: inherit; }
    .page { position:relative; z-index:1; width:min(1440px, calc(100% - 32px)); margin:0 auto; padding:22px 0 30px; }
    .hero {
      display:grid;
      grid-template-columns:minmax(0, 1fr) auto;
      gap:16px;
      align-items:start;
      margin-bottom:18px;
    }
    .eyebrow { color:var(--cyan); font-size:11px; font-weight:950; letter-spacing:.08em; text-transform:uppercase; }
    h1 { margin:5px 0 8px; font-size:clamp(32px, 4.2vw, 54px); line-height:1.04; letter-spacing:0; white-space:nowrap; }
    .subtitle { display:flex; flex-wrap:wrap; gap:8px; color:var(--soft); font-size:12px; line-height:1.55; }
    .subtitle span, .hero-badge {
      border:1px solid rgba(255,255,255,.10);
      border-radius:999px;
      background:rgba(6,10,20,.62);
      padding:6px 10px;
    }
    .hero-actions { display:flex; flex-wrap:wrap; gap:8px; justify-content:flex-end; }
    .hero-badge { color:var(--soft); font-size:12px; font-weight:850; white-space:nowrap; }
    .tabs { display:flex; gap:8px; border:1px solid var(--line); border-radius:18px; background:rgba(6,10,20,.74); padding:8px; margin-bottom:16px; }
    .tab { border:0; border-radius:999px; padding:10px 16px; background:transparent; color:var(--muted); font-size:12px; font-weight:950; }
    .tab.active { background:linear-gradient(135deg, var(--cyan), var(--teal)); color:#031018; box-shadow:0 0 28px rgba(65,220,255,.25); }
    .tab[disabled] { opacity:.48; }
    .workspace { display:grid; grid-template-columns:320px minmax(0,1fr); gap:16px; align-items:start; }
    .rail, .panel {
      border:1px solid var(--line);
      border-radius:16px;
      background:rgba(8,13,27,.78);
      box-shadow:0 18px 50px rgba(0,0,0,.26);
    }
    .rail { position:sticky; top:14px; max-height:calc(100vh - 28px); overflow:hidden; }
    .rail-head { padding:15px; border-bottom:1px solid var(--line); }
    .rail-head h2 { margin:0 0 10px; font-size:17px; }
    .search { width:100%; border:1px solid rgba(255,255,255,.12); border-radius:12px; background:rgba(255,255,255,.05); color:var(--text); padding:10px 11px; outline:0; }
    .sorts { display:grid; grid-template-columns:repeat(2, 1fr); gap:6px; margin-top:9px; }
    .sort-btn { border:1px solid rgba(255,255,255,.10); border-radius:10px; background:rgba(255,255,255,.04); color:var(--soft); padding:7px 6px; font-size:11px; font-weight:900; cursor:pointer; }
    .sort-btn.active { border-color:rgba(65,220,255,.58); color:var(--cyan); background:rgba(65,220,255,.10); }
    .company-list { max-height:calc(100vh - 166px); overflow:auto; padding:8px; }
    .company-btn {
      width:100%;
      border:1px solid transparent;
      border-radius:12px;
      background:transparent;
      color:var(--soft);
      text-align:left;
      padding:10px;
      cursor:pointer;
      display:grid;
      grid-template-columns:34px minmax(0,1fr) auto;
      gap:9px;
      align-items:center;
    }
    .company-btn:hover, .company-btn.active { border-color:rgba(65,220,255,.28); background:rgba(65,220,255,.08); }
    .rank { color:var(--muted); font-size:11px; font-weight:950; }
    .cname { color:var(--text); font-size:13px; font-weight:950; overflow:visible; white-space:normal; text-overflow:clip; line-height:1.3; }
    .cticker { color:var(--muted); font-size:10px; margin-top:2px; }
    .sector-pill {
      max-width:92px;
      overflow:visible;
      text-overflow:clip;
      white-space:normal;
      border:1px solid rgba(65,220,255,.18);
      border-radius:999px;
      background:rgba(65,220,255,.08);
      color:var(--cyan);
      padding:5px 8px;
      font-size:10px;
      font-weight:950;
      line-height:1.25;
    }
    .panel { overflow:hidden; }
    .company-hero {
      position:relative;
      min-height:430px;
      border-bottom:1px solid var(--line);
      background:
        radial-gradient(ellipse at 50% 46%, rgba(65,220,255,.14), transparent 40%),
        radial-gradient(ellipse at 74% 72%, rgba(255,79,126,.11), transparent 36%),
        linear-gradient(135deg, rgba(8,15,34,.96), rgba(18,11,32,.92));
      padding:28px 32px;
      overflow:hidden;
    }
    .orbit-lines, .planet, .planet-ring { position:absolute; left:50%; top:50%; transform:translate(-50%, -50%); }
    .orbit-lines { width:720px; height:300px; border:1px solid rgba(65,220,255,.10); border-radius:50%; transform:translate(-50%, -50%) rotate(-9deg); animation:orbitDrift 18s ease-in-out infinite; }
    .orbit-lines::before, .orbit-lines::after {
      content:""; position:absolute; inset:38px 70px; border:1px solid rgba(157,129,255,.10); border-radius:50%;
    }
    .orbit-lines::after { inset:76px 130px; border-color:rgba(247,213,111,.10); }
    .planet {
      width:178px; height:178px; border-radius:50%;
      display:grid; place-items:center; text-align:center; padding:26px;
      background:
        radial-gradient(circle at 34% 26%, rgba(255,255,255,.86) 0 5px, transparent 8px),
        radial-gradient(circle at 36% 30%, rgba(255,255,255,.16), transparent 18%),
        radial-gradient(circle at 62% 65%, rgba(3,8,16,.92), rgba(16,79,96,.75) 45%, rgba(65,220,255,.22) 100%);
      border:1px solid rgba(65,220,255,.42);
      box-shadow:0 0 42px rgba(65,220,255,.18), inset -34px -36px 45px rgba(0,0,0,.46);
      z-index:3;
      animation:planetFloat 5.8s ease-in-out infinite;
      will-change:transform;
    }
    .planet-ring {
      width:310px; height:80px; border-radius:50%; border:13px solid rgba(247,213,111,.32); border-left-color:rgba(65,220,255,.22); border-right-color:rgba(255,79,126,.26); transform:translate(-50%, -50%) rotate(-10deg); z-index:2;
      mask-image:linear-gradient(to bottom, transparent 0 42%, #000 43% 100%);
      animation:planetRingFloat 5.8s ease-in-out infinite;
      will-change:transform;
    }
    .planet strong { display:block; font-size:23px; line-height:1.1; }
    .planet span { display:block; margin-top:8px; color:var(--soft); font-size:11px; line-height:1.4; }
    .hero-grid { position:relative; z-index:4; display:grid; grid-template-columns:260px 260px; gap:18px; justify-content:space-between; height:100%; }
    .company-hero:has(.hero-grid.cards-3) .orbit-lines,
    .company-hero:has(.hero-grid.cards-3) .planet,
    .company-hero:has(.hero-grid.cards-3) .planet-ring { top:34%; }
    .company-hero:has(.hero-grid.cards-3) .hero-grid { align-content:space-between; }
    .hero-grid.cards-3 .orbit-card:nth-child(3) { grid-column:1 / -1; justify-self:center; }
    .hero-grid.cards-2 { align-content:center; }
    .hero-grid.cards-2 .orbit-card:nth-child(2) { grid-column:2; }
    .orbit-card {
      width:260px; min-height:205px;
      border:1px solid rgba(65,220,255,.20);
      border-radius:16px;
      background:rgba(5,10,22,.75);
      padding:12px;
      box-shadow:0 12px 36px rgba(0,0,0,.28);
      transition:transform .22s ease, border-color .22s ease, box-shadow .22s ease;
    }
    .orbit-card:hover {
      transform:translateY(-4px);
      border-color:rgba(65,220,255,.45);
      box-shadow:0 22px 44px rgba(0,0,0,.32), 0 0 28px rgba(65,220,255,.10);
    }
    .orbit-card:nth-child(2), .orbit-card:nth-child(4) { border-color:rgba(255,79,126,.22); }
    .orbit-card h3 { margin:12px 2px 7px; font-size:14px; }
    .orbit-card p { margin:0 2px; color:var(--soft); font-size:12px; line-height:1.5; }
    .product-visual {
      position:relative;
      height:112px;
      overflow:hidden;
      border:1px solid rgba(255,255,255,.10);
      border-radius:11px;
      background:
        radial-gradient(circle at 72% 24%, rgba(65,220,255,.22), transparent 22%),
        linear-gradient(135deg, rgba(255,255,255,.10), rgba(255,255,255,.02));
    }
    .product-visual.has-image {
      background:rgba(2,6,15,.90);
    }
    .product-visual.has-image::before {
      z-index:1;
      inset:0;
      background:
        linear-gradient(90deg, rgba(2,6,15,.62), transparent 44%, rgba(2,6,15,.16)),
        linear-gradient(180deg, transparent 52%, rgba(2,6,15,.72));
      transform:none;
    }
    .product-visual.has-image::after,
    .product-visual.has-image .art { display:none; }
    .segment-image {
      position:absolute;
      inset:0;
      width:100%;
      height:100%;
      object-fit:cover;
      filter:saturate(1.05) contrast(1.05);
    }
    .photo-source {
      position:absolute;
      right:8px;
      top:8px;
      z-index:2;
      border:1px solid rgba(255,255,255,.18);
      border-radius:999px;
      background:rgba(0,0,0,.46);
      color:rgba(255,255,255,.78);
      padding:3px 7px;
      font-size:9px;
      font-weight:900;
    }
    @keyframes planetFloat {
      0%, 100% { transform:translate(-50%, -50%) translateY(0) rotate(-.4deg); }
      50% { transform:translate(-50%, -50%) translateY(-12px) rotate(.7deg); }
    }
    @keyframes planetRingFloat {
      0%, 100% { transform:translate(-50%, -50%) translateY(0) rotate(-10deg); }
      50% { transform:translate(-50%, -50%) translateY(-12px) rotate(-7deg); }
    }
    @keyframes orbitDrift {
      0%, 100% { transform:translate(-50%, -50%) rotate(-9deg) scale(1); opacity:.88; }
      50% { transform:translate(-50%, -50%) rotate(-6deg) scale(1.02); opacity:1; }
    }
    .product-visual::before {
      content:"";
      position:absolute;
      inset:-30% -20%;
      background:linear-gradient(115deg, transparent 0 36%, rgba(255,255,255,.18) 46%, transparent 58%);
      transform:translateX(-22%);
    }
    .product-visual::after {
      content:"";
      position:absolute;
      right:12px;
      bottom:10px;
      width:58px;
      height:40px;
      border-radius:10px;
      border:2px solid rgba(255,255,255,.26);
      background:rgba(0,0,0,.20);
      box-shadow:0 0 22px rgba(65,220,255,.18);
    }
    .product-visual .art {
      position:absolute;
      z-index:1;
      display:block;
      border:2px solid rgba(255,255,255,.22);
      background:rgba(3,8,18,.42);
      box-shadow:0 0 24px rgba(65,220,255,.16);
    }
    .product-visual.device .art.a { right:38px; bottom:14px; width:34px; height:58px; border-radius:13px; border-color:rgba(65,220,255,.72); }
    .product-visual.device .art.b { right:82px; bottom:22px; width:70px; height:44px; border-radius:12px; border-color:rgba(54,229,189,.55); }
    .product-visual.device .art.c { right:18px; bottom:20px; width:22px; height:42px; border-radius:8px; border-color:rgba(255,255,255,.28); }
    .product-visual.chip .art.a,
    .product-visual.storage .art.a,
    .product-visual.sensor .art.a {
      right:34px; bottom:15px; width:58px; height:58px; border-radius:12px;
      background:linear-gradient(135deg, rgba(255,79,126,.38), rgba(7,10,23,.86));
      border-color:rgba(255,79,126,.68);
      box-shadow:inset 0 0 0 8px rgba(255,255,255,.04), 0 0 26px rgba(255,79,126,.22);
    }
    .product-visual.chip .art.b,
    .product-visual.storage .art.b {
      right:96px; bottom:25px; width:58px; height:38px; border-radius:8px;
      transform:skewX(-15deg);
      border-color:rgba(247,213,111,.48);
    }
    .product-visual.sensor .art.b { right:104px; bottom:28px; width:44px; height:44px; border-radius:50%; border-color:rgba(65,220,255,.55); }
    .product-visual.display .art.a { right:36px; bottom:18px; width:86px; height:50px; border-radius:10px; border-color:rgba(157,129,255,.78); background:linear-gradient(135deg, rgba(157,129,255,.26), rgba(65,220,255,.12)); }
    .product-visual.display .art.b { right:16px; bottom:26px; width:52px; height:34px; border-radius:8px; transform:rotate(6deg); border-color:rgba(65,220,255,.40); }
    .product-visual.auto .art.a { right:30px; bottom:24px; width:96px; height:34px; border-radius:20px 20px 10px 10px; border-color:rgba(247,213,111,.78); }
    .product-visual.auto .art.b { right:47px; bottom:19px; width:12px; height:12px; border-radius:50%; background:var(--gold); border:0; }
    .product-visual.auto .art.c { right:104px; bottom:19px; width:12px; height:12px; border-radius:50%; background:var(--gold); border:0; }
    .product-visual.finance .art.a { right:35px; bottom:18px; width:86px; height:54px; border-radius:8px; border-color:rgba(65,220,255,.52); }
    .product-visual.finance .art.a::before { content:""; position:absolute; left:12px; right:12px; top:10px; height:6px; border-radius:99px; background:rgba(65,220,255,.55); box-shadow:0 14px 0 rgba(65,220,255,.35), 0 28px 0 rgba(65,220,255,.25); }
    .product-visual.card .art.a { right:28px; bottom:22px; width:98px; height:56px; border-radius:13px; border-color:rgba(65,220,255,.55); background:linear-gradient(135deg, rgba(65,220,255,.24), rgba(54,229,189,.10)); }
    .product-visual.card .art.a::before { content:""; position:absolute; left:10px; top:13px; width:24px; height:16px; border-radius:5px; background:rgba(247,213,111,.55); }
    .product-visual.shield .art.a { right:52px; bottom:14px; width:58px; height:66px; border-radius:30px 30px 14px 14px; border-color:rgba(54,229,189,.58); background:linear-gradient(180deg, rgba(54,229,189,.22), rgba(65,220,255,.08)); }
    .product-visual.bio .art.a { right:44px; bottom:15px; width:22px; height:62px; border-radius:12px 12px 8px 8px; border-color:rgba(54,229,189,.62); }
    .product-visual.bio .art.b { right:78px; bottom:16px; width:22px; height:58px; border-radius:12px 12px 8px 8px; border-color:rgba(157,129,255,.58); }
    .product-visual.battery .art.a { right:30px; bottom:24px; width:100px; height:48px; border-radius:12px; border-color:rgba(54,229,189,.62); }
    .product-visual.battery .art.a::before { content:""; position:absolute; inset:10px 12px; background:repeating-linear-gradient(90deg, rgba(54,229,189,.50) 0 10px, transparent 10px 16px); }
    .product-visual.ship .art.a { right:26px; bottom:20px; width:118px; height:38px; border-radius:4px 4px 26px 26px; border-color:rgba(65,220,255,.48); transform:skewX(-12deg); }
    .product-visual.aero .art.a { right:40px; bottom:28px; width:98px; height:24px; border-radius:50%; border-color:rgba(247,213,111,.55); transform:rotate(-8deg); }
    .product-visual.energy .art.a { right:56px; bottom:14px; width:42px; height:70px; border-radius:9px; border-color:rgba(247,213,111,.60); }
    .product-visual.platform .art.a,
    .product-visual.game .art.a,
    .product-visual.lab .art.a,
    .product-visual.factory .art.a,
    .product-visual.chem .art.a,
    .product-visual.steel .art.a,
    .product-visual.signal .art.a {
      right:34px; bottom:16px; width:82px; height:56px; border-radius:16px;
      border-color:rgba(65,220,255,.48);
    }
    .product-visual.platform .art.a::before,
    .product-visual.game .art.a::before,
    .product-visual.lab .art.a::before,
    .product-visual.factory .art.a::before,
    .product-visual.chem .art.a::before,
    .product-visual.steel .art.a::before,
    .product-visual.signal .art.a::before {
      content:""; position:absolute; inset:13px; border-radius:50%; border:2px solid rgba(255,255,255,.26);
    }
    .product-visual.chip::after,
    .product-visual.storage::after,
    .product-visual.sensor::after {
      width:58px; height:58px; border-radius:12px;
      background:linear-gradient(135deg, rgba(255,79,126,.36), rgba(6,10,20,.82));
      box-shadow:inset 0 0 0 8px rgba(255,255,255,.04), 0 0 26px rgba(255,79,126,.22);
    }
    .product-visual.finance::after,
    .product-visual.card::after,
    .product-visual.shield::after {
      width:76px; height:42px; border-radius:12px;
      background:linear-gradient(135deg, rgba(65,220,255,.28), rgba(54,229,189,.14));
      border-color:rgba(65,220,255,.38);
    }
    .product-visual.auto::after { width:82px; height:32px; border-radius:18px 18px 8px 8px; border-color:rgba(247,213,111,.58); }
    .product-visual.display::after { width:78px; height:48px; border-radius:12px; border-color:rgba(157,129,255,.60); }
    .product-visual.bio::after { width:52px; height:52px; border-radius:50%; border-color:rgba(54,229,189,.55); }
    .visual-word {
      position:absolute;
      left:10px;
      bottom:9px;
      z-index:2;
      max-width:132px;
      border:1px solid rgba(255,255,255,.16);
      border-radius:999px;
      background:rgba(0,0,0,.42);
      color:#fff;
      padding:4px 8px;
      font-size:11px;
      font-weight:950;
      text-shadow:0 1px 8px rgba(0,0,0,.60);
    }
    .summary-list {
      display:grid;
      gap:8px;
      margin:0;
      padding:0;
      list-style:none;
    }
    .summary-list li {
      position:relative;
      border:1px solid rgba(148,163,184,.12);
      border-radius:10px;
      background:rgba(255,255,255,.035);
      color:var(--soft);
      padding:10px 12px 10px 30px;
      font-size:12.5px;
      line-height:1.55;
    }
    .summary-list li::before {
      content:"";
      position:absolute;
      left:11px;
      top:15px;
      width:7px;
      height:7px;
      border-radius:50%;
      background:linear-gradient(135deg, var(--cyan), var(--teal));
      box-shadow:0 0 14px rgba(65,220,255,.42);
    }
    .check-row { display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:10px; margin-top:12px; }
    .check-card {
      border:1px solid rgba(65,220,255,.16);
      border-radius:13px;
      background:linear-gradient(135deg, rgba(65,220,255,.07), rgba(255,255,255,.025));
      padding:12px;
    }
    .check-card b { display:block; color:var(--text); font-size:13px; margin-bottom:6px; }
    .check-card span { display:block; color:var(--soft); font-size:11px; line-height:1.5; }
    .check-row + .grid-2 { margin-top:12px; }
    .content { padding:18px; display:grid; gap:16px; }
    .section { border:1px solid var(--line); border-radius:14px; background:rgba(4,8,19,.64); padding:16px; }
    .section-head { display:flex; justify-content:space-between; gap:12px; align-items:start; margin-bottom:12px; }
    .section-head h2 { margin:0; font-size:20px; }
    .section-head p { margin:0; max-width:620px; color:var(--soft); font-size:12px; line-height:1.55; }
    .grid-2 { display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:12px; }
    .grid-3 { display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:10px; }
    .grid-4 { display:grid; grid-template-columns:repeat(4, minmax(0,1fr)); gap:10px; }
    .card { min-width:0; border:1px solid rgba(148,163,184,.14); border-radius:12px; background:rgba(255,255,255,.04); padding:13px; }
    .card h3 { margin:0 0 9px; font-size:14px; }
    .card p { margin:0; color:var(--soft); font-size:12px; line-height:1.55; }
    .report-map {
      background:
        radial-gradient(circle at 10% 0%, rgba(65,220,255,.10), transparent 30%),
        radial-gradient(circle at 86% 4%, rgba(255,79,126,.10), transparent 30%),
        rgba(4,8,19,.70);
    }
    .report-grid {
      display:grid;
      grid-template-columns:1fr 1fr;
      gap:14px;
      align-items:stretch;
    }
    .report-panel {
      border:1px solid rgba(65,220,255,.16);
      border-radius:16px;
      background:linear-gradient(135deg, rgba(65,220,255,.055), rgba(255,255,255,.025));
      padding:16px;
      min-width:0;
    }
    .report-panel h3 { margin:0 0 12px; font-size:16px; }
    .engine-tiles {
      display:grid;
      grid-template-columns:repeat(2, minmax(0,1fr));
      gap:10px;
    }
    .engine-tile {
      border:1px solid rgba(255,255,255,.10);
      border-radius:13px;
      background:rgba(255,255,255,.04);
      padding:12px;
      min-height:96px;
    }
    .engine-tile strong { display:block; margin-bottom:6px; color:var(--text); font-size:13.5px; }
    .engine-tile span { display:block; color:var(--soft); font-size:12px; line-height:1.5; }
    .money-flow {
      display:grid;
      gap:9px;
      margin:0;
      padding:0;
      list-style:none;
      counter-reset:flow;
    }
    .money-flow li {
      counter-increment:flow;
      position:relative;
      border:1px solid rgba(148,163,184,.12);
      border-radius:11px;
      background:rgba(255,255,255,.04);
      color:var(--soft);
      padding:11px 12px 11px 42px;
      font-size:12.5px;
      line-height:1.55;
    }
    .money-flow li::before {
      content:counter(flow);
      position:absolute;
      left:11px;
      top:10px;
      width:20px;
      height:20px;
      display:grid;
      place-items:center;
      border-radius:50%;
      background:linear-gradient(135deg, var(--cyan), var(--teal));
      color:#031018;
      font-size:11px;
      font-weight:950;
    }
    .segment-breakdown {
      margin-top:12px;
      border:1px solid rgba(65,220,255,.18);
      border-radius:16px;
      background:
        radial-gradient(circle at 10% 0%, rgba(65,220,255,.10), transparent 28%),
        linear-gradient(135deg, rgba(65,220,255,.055), rgba(255,79,126,.035));
      padding:16px;
    }
    .segment-breakdown-head {
      display:flex;
      justify-content:space-between;
      gap:12px;
      align-items:flex-start;
      margin-bottom:12px;
    }
    .segment-breakdown-head h3 { margin:0; font-size:17px; }
    .segment-breakdown-head p { margin:4px 0 0; color:var(--soft); font-size:12px; line-height:1.5; }
    .segment-grid {
      display:grid;
      grid-template-columns:repeat(4, minmax(0,1fr));
      gap:10px;
    }
    .segment-card {
      border:1px solid rgba(255,255,255,.12);
      border-radius:14px;
      background:rgba(5,10,22,.62);
      padding:12px;
      min-width:0;
    }
    .segment-card strong { display:block; font-size:14px; margin-bottom:4px; }
    .segment-share { color:var(--cyan); font-size:24px; font-weight:950; letter-spacing:0; }
    .segment-desc { margin:8px 0 10px; color:var(--soft); font-size:12px; line-height:1.5; }
    .segment-bar {
      height:9px;
      border-radius:999px;
      background:rgba(255,255,255,.08);
      overflow:hidden;
    }
    .segment-bar span {
      display:block;
      width:var(--w);
      height:100%;
      border-radius:999px;
      background:linear-gradient(90deg, var(--cyan), var(--teal), var(--gold));
      box-shadow:0 0 18px rgba(65,220,255,.26);
    }
    .segment-tip {
      margin-top:10px;
      color:var(--muted);
      font-size:11px;
      line-height:1.5;
    }
    .business-evidence {
      margin-top:12px;
      display:grid;
      grid-template-columns:1fr 1fr;
      gap:12px;
    }
    .evidence-card {
      min-width:0;
      border:1px solid rgba(148,163,184,.14);
      border-radius:14px;
      background:rgba(255,255,255,.04);
      padding:14px;
    }
    .evidence-card h3 {
      margin:0 0 10px;
      font-size:15px;
    }
    .evidence-card .source-sentence {
      margin-top:10px;
    }
    .business-finance-panel {
      margin-top:12px;
      border:1px solid rgba(148,163,184,.15);
      border-radius:16px;
      background:
        radial-gradient(circle at 5% 0%, rgba(65,220,255,.10), transparent 26%),
        rgba(255,255,255,.035);
      padding:15px;
    }
    .business-finance-panel h3 {
      margin:0 0 11px;
      font-size:16px;
    }
    .business-finance-grid {
      display:grid;
      grid-template-columns:repeat(4, minmax(0,1fr));
      gap:10px;
    }
    .finance-mini {
      border:1px solid rgba(255,255,255,.11);
      border-radius:13px;
      background:rgba(5,10,22,.62);
      padding:12px;
      min-width:0;
    }
    .finance-mini strong {
      display:block;
      font-size:13px;
      margin-bottom:6px;
    }
    .finance-mini span {
      display:block;
      color:var(--soft);
      font-size:11.5px;
      line-height:1.45;
    }
    .finance-mini .segment-bar {
      margin-top:10px;
    }
    .custom-report-cards {
      margin-top:12px;
      border:1px solid rgba(65,220,255,.18);
      border-radius:16px;
      background:
        radial-gradient(circle at 8% 0%, rgba(65,220,255,.11), transparent 28%),
        linear-gradient(135deg, rgba(65,220,255,.045), rgba(255,79,126,.025));
      padding:16px;
    }
    .custom-report-grid {
      display:grid;
      gap:14px;
    }
    .custom-report-card {
      border:1px solid rgba(255,255,255,.12);
      border-radius:14px;
      background:rgba(5,10,22,.64);
      padding:17px 18px;
      min-width:0;
    }
    .custom-report-card strong {
      display:block;
      color:var(--text);
      font-size:17px;
      margin-bottom:8px;
    }
    .report-reading-intro {
      margin:0 0 13px;
      color:var(--soft);
      font-size:13px;
      line-height:1.6;
    }
    .report-reading-list {
      display:grid;
      gap:0;
      margin:0;
      padding:0;
      list-style:none;
    }
    .report-reading-item {
      position:relative;
      padding:13px 0 13px 18px;
      border-top:1px solid rgba(148,163,184,.13);
    }
    .report-reading-item::before {
      content:'';
      position:absolute;
      left:0;
      top:20px;
      width:7px;
      height:7px;
      border-radius:50%;
      background:var(--cyan);
      box-shadow:0 0 12px rgba(65,220,255,.8);
    }
    .report-reading-item:first-child { border-top:0; }
    .report-reading-item h4 {
      margin:0 0 6px;
      color:var(--text);
      font-size:14px;
      line-height:1.42;
    }
    .report-reading-item h4 span {
      color:var(--cyan);
      font-weight:950;
    }
    .report-reading-item p {
      margin:0;
      color:var(--soft);
      font-size:13px;
      line-height:1.65;
    }
    .report-reading-item p b {
      color:var(--cyan);
      font-size:14px;
    }
    .term-note {
      position:relative;
      display:inline;
      color:#dff8ff;
      border-bottom:1px dotted rgba(65,220,255,.78);
      cursor:help;
      font-weight:850;
      line-height:1.25;
    }
    .term-note::after {
      content:none;
    }
    .term-note::before {
      display:none;
    }
    .term-tooltip {
      position:fixed;
      z-index:9999;
      max-width:min(320px, calc(100vw - 28px));
      padding:10px 12px;
      border-radius:12px;
      border:1px solid rgba(65,220,255,.34);
      background:linear-gradient(135deg, rgba(5,10,22,.98), rgba(18,28,50,.98));
      color:rgba(232,247,255,.96);
      box-shadow:0 18px 40px rgba(0,0,0,.50), 0 0 24px rgba(65,220,255,.14);
      font-size:11.5px;
      font-weight:750;
      line-height:1.55;
      opacity:0;
      pointer-events:none;
      transform:translateY(4px);
      transition:opacity .12s ease, transform .12s ease;
      word-break:keep-all;
      overflow-wrap:anywhere;
    }
    .term-tooltip.show {
      opacity:1;
      transform:translateY(0);
    }
    .source-chip {
      display:inline-flex;
      align-items:center;
      gap:5px;
      margin-top:10px;
      border:1px solid rgba(65,220,255,.22);
      border-radius:999px;
      color:var(--cyan);
      background:rgba(65,220,255,.07);
      padding:4px 8px;
      font-size:10.5px;
      font-weight:900;
    }
    .utilization-detail,
    .segment-financial-detail {
      margin-top:12px;
      border:1px solid rgba(65,220,255,.18);
      border-radius:16px;
      background:
        radial-gradient(circle at 8% 0%, rgba(65,220,255,.10), transparent 28%),
        rgba(255,255,255,.035);
      padding:16px;
    }
    .detail-head {
      display:flex;
      justify-content:space-between;
      gap:12px;
      align-items:flex-start;
      margin-bottom:12px;
    }
    .detail-head h3 {
      margin:0;
      font-size:17px;
    }
    .detail-head p {
      margin:4px 0 0;
      color:var(--soft);
      font-size:12px;
      line-height:1.5;
    }
    .util-grid {
      display:grid;
      grid-template-columns:repeat(5, minmax(0,1fr));
      gap:10px;
    }
    .util-card {
      border:1px solid rgba(255,255,255,.12);
      border-radius:14px;
      background:rgba(5,10,22,.62);
      padding:12px;
      min-width:0;
    }
    .util-card strong {
      display:block;
      font-size:13.5px;
      margin-bottom:4px;
    }
    .util-card .rate {
      color:var(--cyan);
      font-size:24px;
      font-weight:950;
    }
    .util-card p {
      margin:7px 0 9px;
      color:var(--soft);
      font-size:11.5px;
      line-height:1.45;
    }
    .util-card .track {
      height:9px;
    }
    .segment-finance-grid {
      display:grid;
      grid-template-columns:repeat(4, minmax(0,1fr));
      gap:10px;
    }
    .segment-finance-card {
      border:1px solid rgba(255,255,255,.12);
      border-radius:14px;
      background:rgba(5,10,22,.64);
      padding:12px;
      min-width:0;
    }
    .segment-finance-card h4 {
      margin:0 0 10px;
      font-size:14px;
    }
    .metric-line {
      display:grid;
      grid-template-columns:56px 1fr;
      gap:8px;
      align-items:center;
      margin-top:9px;
    }
    .metric-line b {
      color:var(--soft);
      font-size:11px;
    }
    .mini-bars {
      display:grid;
      grid-template-columns:repeat(3, 1fr);
      gap:5px;
      align-items:end;
      height:48px;
      border-bottom:1px solid rgba(255,255,255,.12);
    }
    .mini-bars span {
      position:relative;
      display:block;
      height:var(--h);
      min-height:4px;
      border-radius:6px 6px 0 0;
      background:linear-gradient(180deg, var(--cyan), var(--teal));
    }
    .mini-bars.pink span {
      background:linear-gradient(180deg, var(--pink), rgba(247,213,111,.62));
    }
    .mini-bars.gold span {
      background:linear-gradient(180deg, var(--gold), var(--violet));
    }
    .mini-bars span.neg {
      background:linear-gradient(180deg, rgba(255,79,126,.95), rgba(255,79,126,.32));
    }
    .metric-values {
      display:block;
      margin-top:4px;
      color:var(--muted);
      font-size:10.5px;
      white-space:nowrap;
    }
    .driver-radar {
      display:grid;
      grid-template-columns:repeat(4, minmax(0,1fr));
      gap:8px;
      margin-top:12px;
    }
    .driver-chip {
      border:1px solid rgba(255,255,255,.12);
      border-radius:13px;
      background:rgba(255,255,255,.04);
      padding:10px;
      color:var(--text);
      font-size:12px;
      font-weight:900;
      min-height:54px;
      display:flex;
      align-items:center;
      gap:8px;
    }
    .driver-chip::before {
      content:"";
      flex:0 0 auto;
      width:8px;
      height:8px;
      border-radius:50%;
      background:var(--pink);
      box-shadow:0 0 16px rgba(255,79,126,.50);
    }
    .impact-lanes {
      display:grid;
      grid-template-columns:repeat(4, minmax(0,1fr));
      gap:10px;
      margin-top:12px;
    }
    .impact-lane {
      position:relative;
      border:1px solid rgba(148,163,184,.14);
      border-radius:12px;
      background:rgba(255,255,255,.04);
      padding:13px;
      overflow:hidden;
    }
    .impact-lane::before {
      content:"";
      position:absolute;
      left:14px;
      right:14px;
      top:38px;
      height:3px;
      border-radius:999px;
      background:linear-gradient(90deg, var(--cyan), var(--teal), var(--gold));
      opacity:.42;
    }
    .impact-lane h3 { position:relative; margin:0 0 17px; font-size:13px; }
    .impact-lane p { position:relative; margin:0; color:var(--soft); font-size:11px; line-height:1.5; }
    .evidence-board {
      display:grid;
      grid-template-columns:1fr 1fr;
      gap:12px;
    }
    .signal-card {
      border:1px solid rgba(65,220,255,.15);
      border-radius:13px;
      background:linear-gradient(135deg, rgba(65,220,255,.06), rgba(255,255,255,.025));
      padding:13px;
    }
    .signal-card h3 { margin:0 0 8px; font-size:14px; }
    .signal-card p { margin:0; color:var(--soft); font-size:12px; line-height:1.55; }
    .source-sentence {
      margin-top:12px;
      border-top:1px solid rgba(255,255,255,.08);
      padding-top:10px;
      color:var(--muted);
      font-size:11px;
      line-height:1.55;
    }
    .snippet { min-height:122px; }
    .empty { color:var(--muted) !important; }
    .raw-row { display:grid; grid-template-columns:minmax(80px,120px) minmax(0,1fr) 48px; gap:8px; align-items:center; margin-top:8px; }
    .raw-name, .raw-pct { color:var(--soft); font-size:11px; font-weight:900; }
    .raw-pct { justify-self:end; color:var(--text); }
    .track { height:8px; border-radius:999px; background:rgba(255,255,255,.08); overflow:hidden; position:relative; }
    .track::before { content:""; position:absolute; left:50%; top:-3px; bottom:-3px; width:1px; background:rgba(255,255,255,.24); }
    .bar { position:absolute; top:0; bottom:0; border-radius:999px; }
    .bar.up { left:50%; background:linear-gradient(90deg, var(--teal), var(--gold)); }
    .bar.down { right:50%; background:linear-gradient(90deg, var(--pink), var(--cyan)); }
    .util-row { margin-top:9px; }
    .util-head { display:flex; justify-content:space-between; gap:8px; color:var(--soft); font-size:11px; font-weight:900; margin-bottom:5px; }
    .util-fill { display:block; height:9px; border-radius:999px; background:linear-gradient(90deg, var(--cyan), var(--teal), var(--gold)); }
    .metric { display:grid; gap:5px; }
    .metric-label { color:var(--muted); font-size:11px; font-weight:900; }
    .metric-value { color:var(--text); font-size:22px; font-weight:950; }
    .metric-note { color:var(--soft); font-size:11px; line-height:1.4; }
    .trend { display:flex; align-items:end; gap:8px; height:82px; border-bottom:1px solid rgba(255,255,255,.14); padding:0 2px 4px; }
    .trend span { flex:1; min-width:0; min-height:3px; border-radius:7px 7px 2px 2px; background:linear-gradient(180deg, var(--cyan), rgba(54,229,189,.55)); position:relative; height:var(--h); }
    .trend.pink span { background:linear-gradient(180deg, var(--pink), rgba(247,213,111,.52)); }
    .trend.gold span { background:linear-gradient(180deg, var(--gold), rgba(157,129,255,.50)); }
    .trend span.neg { background:linear-gradient(180deg, rgba(255,79,126,.80), rgba(255,79,126,.30)); }
    .trend span::after { content:attr(data-y); position:absolute; left:50%; bottom:-20px; transform:translateX(-50%); color:var(--muted); font-size:9px; font-weight:900; }
    .trend-value { display:block; margin-top:22px; color:var(--soft); font-size:11px; line-height:1.4; }
    .source-row { display:flex; flex-wrap:wrap; gap:8px; margin-top:12px; }
    .source-link { display:inline-flex; align-items:center; min-height:30px; border:1px solid rgba(65,220,255,.30); border-radius:999px; padding:0 12px; color:var(--cyan); text-decoration:none; font-size:12px; font-weight:950; background:rgba(65,220,255,.08); }
    .mini-label { display:inline-flex; border:1px solid rgba(255,255,255,.12); border-radius:999px; padding:4px 8px; color:var(--muted); font-size:10px; font-weight:950; }
    @media (max-width: 1100px) {
      .workspace { grid-template-columns:1fr; }
      .rail { position:relative; top:auto; max-height:none; }
      .company-list { max-height:340px; }
      .hero-grid { grid-template-columns:repeat(2, minmax(0, 240px)); }
      .grid-4 { grid-template-columns:repeat(2, minmax(0,1fr)); }
      .report-grid, .evidence-board, .business-evidence { grid-template-columns:1fr; }
      .driver-radar, .impact-lanes, .segment-grid, .business-finance-grid, .util-grid, .segment-finance-grid { grid-template-columns:repeat(2, minmax(0,1fr)); }
    }
    @media (max-width: 720px) {
      .page { width:min(100% - 20px, 680px); padding-top:16px; }
      h1 { font-size:clamp(24px, 7vw, 40px); white-space:nowrap; }
      .hero { grid-template-columns:1fr; }
      .hero-actions { justify-content:flex-start; }
      .tabs { overflow:auto; }
      .company-hero { min-height:auto; }
      .orbit-lines, .planet-ring { display:none; }
      .planet { position:relative; left:auto; top:auto; transform:none; margin:0 auto 16px; animation:none; }
      .hero-grid { grid-template-columns:1fr; height:auto; }
      .orbit-card { width:100%; }
      .grid-2, .grid-3, .grid-4, .check-row, .engine-tiles, .driver-radar, .impact-lanes, .segment-grid, .business-finance-grid, .util-grid, .segment-finance-grid, .custom-report-grid { grid-template-columns:1fr; }
      .raw-row { grid-template-columns:minmax(74px,108px) minmax(0,1fr) 42px; }
    }
    @media (prefers-reduced-motion: reduce) {
      .planet, .planet-ring, .orbit-lines, .orbit-card { animation:none; transition:none; }
      .orbit-card:hover { transform:none; }
    }
  </style>
</head>
<body>
  <main class="page">
    <header class="hero">
      <div>
        <div class="eyebrow">DiscloseAI Galaxy Annual Report Reader</div>
        <h1>국내상장기업 사업보고서 reader</h1>
        <div class="subtitle">
          <span>DART 사업보고서 기반으로 각 회사가 무엇을 팔고 만드는지 먼저 보여줍니다</span>
          <span>행성 주변 사업·제품 카드는 사업보고서 문구와 업종 키워드로 구성</span>
          <span>원문 스니펫은 로컬 수집된 사업보고서에서 추출</span>
        </div>
      </div>
      <div class="hero-actions">
        <span class="hero-badge" id="coverageBadge">수집 기업</span>
        <span class="hero-badge">2025 연결 기준</span>
        <span class="hero-badge">단위: 억원/조원</span>
      </div>
    </header>

    <nav class="tabs" aria-label="prototype tabs">
      <button class="tab active" type="button">사업 우주지도</button>
      <button class="tab" type="button" disabled>재무제표 갤럭시 맵</button>
      <button class="tab" type="button" disabled>주석 달린 사업보고서</button>
    </nav>

    <section class="workspace">
      <aside class="rail" aria-label="company selector">
        <div class="rail-head">
          <h2>기업 선택</h2>
          <input class="search" id="searchInput" type="search" placeholder="종목명 또는 티커 검색">
          <div class="sorts">
            <button class="sort-btn active" type="button" data-sort="market_cap">시총순</button>
            <button class="sort-btn" type="button" data-sort="ttm_per">TTM PER순</button>
          </div>
        </div>
        <div class="company-list" id="companyList"></div>
      </aside>
      <section class="panel" id="readerPanel" aria-live="polite"></section>
    </section>
  </main>
  <script>
    const DATA = __APP_DATA__;
    const CUSTOM_REPORT_IDEAS = __CUSTOM_REPORT_IDEAS__;
    const GENERATED_AT = "__GENERATED_AT__";
    let selected = DATA[0] ? DATA[0].stock_code : null;
    let sortMode = "market_cap";
    const $ = (sel) => document.querySelector(sel);
    const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (m) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
    const categoryOf = (row, fallback = '업종 미분류') =>
      row.display_category || row.sector || (row.percentile && row.percentile._sector) || fallback;
    const sectorOf = (row) => row.sector || (row.percentile && row.percentile._sector) || categoryOf(row);
    const badgeOf = (row, fallback = '사업') => row.badge_label || row.display_category || row.sector || fallback;
    const BUSINESS_GLOSSARY = {
      'DRAM':'전원이 켜져 있을 때 데이터를 빠르게 읽고 쓰는 메모리 반도체. 서버·PC·스마트폰 성능에 중요합니다.',
      'NAND Flash':'전원이 꺼져도 데이터가 남는 저장용 메모리. SSD와 스마트폰 저장공간에 쓰입니다.',
      'NAND':'전원이 꺼져도 데이터가 남는 저장용 메모리. SSD와 스마트폰 저장공간에 쓰입니다.',
      'HBM':'여러 메모리 칩을 위로 쌓아 AI 반도체 옆에서 대량 데이터를 빠르게 넘겨주는 고부가 메모리입니다.',
      'DDR5':'서버와 PC에 쓰이는 최신 세대 DRAM 규격. 속도와 전력 효율이 이전 세대보다 좋습니다.',
      'LPDDR5X':'스마트폰·노트북처럼 전력소모가 중요한 기기에 쓰이는 저전력 DRAM입니다.',
      'GDDR7':'그래픽카드와 AI 연산 장치에 쓰이는 고속 그래픽 메모리 규격입니다.',
      'SSD':'낸드플래시로 만든 저장장치. PC·서버의 하드디스크를 대체하는 빠른 저장공간입니다.',
      'UFS':'스마트폰 안의 저장장치 규격. 앱 실행과 파일 저장 속도에 영향을 줍니다.',
      'eMMC':'보급형 스마트폰·기기에 쓰이는 내장 저장장치 규격입니다.',
      '모바일AP':'스마트폰의 두뇌 역할을 하는 반도체. 앱 실행, 카메라, 통신 기능을 통합해 처리합니다.',
      'AP':'기기의 두뇌 역할을 하는 반도체. 연산과 통신, 멀티미디어 처리를 담당합니다.',
      '이미지센서':'카메라 렌즈로 들어온 빛을 디지털 사진 정보로 바꾸는 반도체입니다.',
      'CIS':'카메라 이미지센서의 한 종류. 스마트폰·자동차 카메라에서 빛을 전기신호로 바꿉니다.',
      'Foundry':'고객사가 설계한 반도체를 대신 생산해주는 위탁생산 사업입니다.',
      '파운드리':'고객사가 설계한 반도체를 대신 생산해주는 위탁생산 사업입니다.',
      'OLED':'스스로 빛을 내는 디스플레이. 얇고 색 표현이 좋아 스마트폰·TV에 많이 쓰입니다.',
      'QD-OLED':'퀀텀닷 기술을 결합한 OLED 패널. 색 재현과 밝기를 개선한 고급 디스플레이입니다.',
      'MLCC':'전자제품 회로에서 전기를 잠깐 저장하고 잡음을 줄이는 작은 세라믹 부품입니다.',
      '패키징':'완성된 반도체 칩을 보호하고 회로기판과 연결할 수 있게 포장·조립하는 공정입니다.',
      '전장':'자동차에 들어가는 전자장치. 디지털 콕핏, 카메라, 센서, 오디오, 제어장치가 포함됩니다.',
      '디지털 콕핏':'자동차 안의 계기판·내비게이션·엔터테인먼트 화면을 통합한 운전석 전자 시스템입니다.',
      'EV':'전기차. 엔진 대신 배터리와 모터로 움직이는 자동차입니다.',
      '전기차':'엔진 대신 배터리와 모터로 움직이는 자동차입니다.',
      '하이브리드':'엔진과 전기모터를 함께 쓰는 자동차. 연비와 배출가스 개선을 노립니다.',
      '수소전기차':'수소로 전기를 만들어 모터를 돌리는 차량. 충전 인프라와 원가가 핵심 변수입니다.',
      'SUV':'차체가 높고 실내가 넓은 스포츠유틸리티 차량. 자동차 회사의 수익성에 중요한 차종입니다.',
      'A/S':'판매 후 정비·수리 서비스. 반복 매출과 고객 충성도에 영향을 줍니다.',
      '리스':'차량이나 장비를 사지 않고 일정 기간 빌려 쓰며 비용을 내는 금융 방식입니다.',
      '할부금융':'차량 대금을 한 번에 내지 않고 나눠 내도록 금융사가 돈을 빌려주는 사업입니다.',
      'ESS':'전기를 저장했다가 필요할 때 쓰는 대형 배터리 시스템입니다.',
      '양극재':'배터리 성능과 원가를 크게 좌우하는 핵심 소재. 리튬·니켈 등이 들어갑니다.',
      '음극재':'배터리에서 리튬이온을 저장했다 내보내는 소재. 충전 속도와 수명에 영향을 줍니다.',
      '분리막':'배터리 안에서 양극과 음극이 직접 닿지 않게 막아주는 얇은 막입니다.',
      '전해액':'배터리 안에서 리튬이온이 움직일 수 있게 도와주는 액체 소재입니다.',
      '전구체':'양극재를 만들기 전 단계의 핵심 중간 소재. 배터리 소재 원가와 품질에 중요합니다.',
      '리튬':'배터리 핵심 원재료. 가격이 오르면 배터리 원가에 큰 영향을 줍니다.',
      '니켈':'고성능 배터리 양극재에 많이 쓰이는 금속. 에너지밀도와 원가에 영향을 줍니다.',
      '원통형 전지':'원통 모양 배터리 셀. 전기차와 전동공구 등에 쓰입니다.',
      '파우치형 전지':'납작한 주머니 형태의 배터리 셀. 공간 활용도가 좋아 전기차에 많이 쓰입니다.',
      'CDMO':'제약사의 의약품을 대신 개발·생산해주는 위탁개발생산 사업입니다.',
      'CMO':'의약품을 대신 생산해주는 위탁생산 사업입니다.',
      '바이오시밀러':'특허가 끝난 바이오 의약품을 비슷하게 만든 후속 의약품입니다.',
      'ADC':'항체에 약물을 붙여 암세포 같은 목표 세포에 약을 보내는 차세대 치료제 기술입니다.',
      'mRNA':'세포에 특정 단백질을 만들라는 설계도를 전달하는 물질. 백신·치료제 개발에 활용됩니다.',
      '임상':'사람을 대상으로 의약품의 안전성과 효과를 확인하는 시험입니다.',
      '품목허가':'정부가 의약품 판매를 허용하는 절차. 허가가 나야 본격 매출이 가능합니다.',
      '파이프라인':'개발 중인 신약·치료제 후보 목록. 단계가 높을수록 상업화에 가까워집니다.',
      '수주잔고':'아직 매출로 잡히지 않았지만 이미 계약된 일감. 미래 매출의 재료입니다.',
      '수주':'고객에게서 제품·공사·서비스 계약을 따내는 일입니다.',
      '납품':'계약한 제품이나 장비를 고객에게 넘기는 단계. 이때 매출이 잡히는 경우가 많습니다.',
      '공정률':'공사나 선박 건조가 얼마나 진행됐는지를 나타내는 비율입니다.',
      '선가':'선박 한 척의 가격. 조선사 수익성에 큰 영향을 줍니다.',
      'LNG선':'액화천연가스를 매우 낮은 온도로 실어 나르는 고부가 선박입니다.',
      '컨테이너선':'표준 컨테이너 화물을 싣고 다니는 선박. 글로벌 교역량 영향을 받습니다.',
      '원유운반선':'원유를 대량으로 운송하는 유조선입니다.',
      'LPG선':'액화석유가스를 운송하는 선박입니다.',
      '군함':'해군이 사용하는 특수 선박. 정부 예산과 방산 수주 영향을 받습니다.',
      '해양플랜트':'바다에서 석유·가스 등을 생산하거나 처리하는 대형 설비입니다.',
      '가스터빈':'고온 가스를 이용해 터빈을 돌려 전기를 만드는 발전 설비입니다.',
      '스팀터빈':'증기의 힘으로 터빈을 돌려 전기를 만드는 발전 설비입니다.',
      '원자로':'원자력발전소에서 핵분열 열을 만들어내는 핵심 설비입니다.',
      '증기발생기':'원자로의 열로 물을 끓여 터빈을 돌릴 증기를 만드는 설비입니다.',
      '변압기':'전기의 전압을 높이거나 낮추는 전력기기. 전력망 투자와 함께 수요가 늘 수 있습니다.',
      '전선':'전기를 보내는 선. 전력망·해저케이블·통신망 투자와 연결됩니다.',
      '전력망':'발전소에서 만든 전기를 기업과 가정까지 보내는 송전·배전 네트워크입니다.',
      '해저케이블':'바닷속에 까는 전력 또는 통신 케이블. 국가 간 전력망·데이터망 연결에 쓰입니다.',
      '운임':'화물을 실어 나르고 받는 운송료. 해운사 매출과 이익률의 핵심입니다.',
      '운임지수':'해운 운임 수준을 보여주는 지표. 업황이 좋고 나쁜지 빠르게 볼 수 있습니다.',
      '물동량':'실제로 이동하는 화물의 양. 세계 교역과 경기 흐름을 반영합니다.',
      '선대':'회사가 보유하거나 운용하는 선박 집단입니다.',
      '용선료':'배를 빌려 쓰고 내는 비용입니다.',
      '예대마진':'예금 금리와 대출 금리의 차이. 은행의 기본 수익원입니다.',
      '순이자마진':'은행이 자산을 굴려 이자로 얼마나 남기는지 보여주는 수익성 지표입니다.',
      '충당금':'나중에 손실이 날 가능성에 대비해 미리 비용으로 쌓아두는 금액입니다.',
      '연체율':'대출금을 제때 갚지 못한 비율. 높아지면 금융사의 건전성이 나빠질 수 있습니다.',
      '대손비용':'빌려준 돈을 못 받을 가능성 때문에 비용 처리하는 금액입니다.',
      '자본비율':'금융사가 위험을 견딜 자기자본을 얼마나 보유했는지 보여주는 지표입니다.',
      '손해율':'보험료로 받은 돈 대비 보험금으로 나간 돈의 비율. 낮을수록 보험영업에 유리합니다.',
      '지급여력':'보험사가 보험금을 지급할 능력이 충분한지 보는 건전성 지표입니다.',
      '운용자산':'보험사·금융사가 고객 돈이나 자기 돈을 투자해 굴리는 자산입니다.',
      '브로커리지':'주식·채권 거래를 중개하고 수수료를 받는 증권사 사업입니다.',
      'IB':'기업금융. 인수합병, 상장, 채권 발행 같은 기업 거래를 도와 수수료를 받는 사업입니다.',
      'ROE':'자기자본으로 얼마나 이익을 냈는지 보는 수익성 지표입니다.',
      '배당':'회사가 번 돈 일부를 주주에게 나눠주는 것.',
      '자사주':'회사가 자기 회사 주식을 사서 보유한 주식입니다.',
      '지분법손익':'투자한 회사의 이익이나 손실 중 우리 지분만큼을 우리 손익에 반영한 금액입니다.',
      '순자산가치':'회사가 가진 자산에서 빚을 뺀 가치. 지주사 평가 때 자주 봅니다.',
      '플랫폼':'이용자와 판매자, 광고주 등을 연결해 거래·광고·수수료 매출을 만드는 디지털 장터입니다.',
      '커머스':'온라인 쇼핑과 거래 사업입니다.',
      '트래픽':'서비스에 들어오는 이용자 방문량입니다.',
      '체류시간':'이용자가 서비스 안에 머무는 시간. 광고·콘텐츠 매출과 연결될 수 있습니다.',
      '광고':'기업이 소비자에게 제품을 알리기 위해 내는 비용. 플랫폼 회사의 주요 매출원입니다.',
      '클라우드':'서버와 소프트웨어를 인터넷으로 빌려 쓰는 서비스입니다.',
      'AI':'사람의 판단·언어·이미지 인식 등을 컴퓨터가 흉내 내는 기술입니다.',
      '데이터센터':'서버를 대량으로 모아 데이터를 저장·처리하는 시설입니다.',
      'ARPU':'가입자 한 명당 평균 매출. 통신사 본업 단가를 보는 지표입니다.',
      'CAPEX':'공장·설비·네트워크 같은 장기 자산에 쓰는 투자금입니다.',
      '5G':'4세대보다 빠른 이동통신 기술. 통신사 네트워크 투자와 요금제에 연결됩니다.',
      '가입자':'서비스를 이용하는 고객 수. 통신·플랫폼 반복 매출의 출발점입니다.',
      '원가율':'매출 중 제품을 만들거나 서비스를 제공하는 데 든 비용 비율입니다.',
      '가동률':'공장이나 설비가 가능한 시간 대비 실제로 돌아간 비율입니다.',
      '감가상각비':'비싼 설비를 여러 해에 나누어 비용 처리하는 금액입니다.',
      '판관비':'판매비와 관리비. 영업, 마케팅, 인건비, 사무비 등이 포함됩니다.',
      '매출총이익':'매출에서 제품 원가를 뺀 이익. 본업 마진의 첫 단계입니다.',
      '영업이익':'매출총이익에서 판관비 등을 뺀 본업 이익입니다.',
      '영업현금흐름':'본업을 하면서 실제로 들어오고 나간 현금 흐름입니다.',
      '유형자산':'공장, 장비, 건물처럼 눈에 보이는 장기 자산입니다.',
      '무형자산':'특허권, 개발비, 영업권처럼 눈에 보이지 않는 자산입니다.',
      '재고자산':'아직 팔리지 않은 제품, 원재료, 반제품입니다.',
      '미분양':'건설사가 지은 주택 중 아직 팔리지 않은 물량입니다.',
      'PF':'프로젝트파이낸싱. 특정 개발사업의 미래 현금흐름을 담보로 돈을 빌리는 구조입니다.',
      'CSM':'보험계약에서 앞으로 이익으로 인식될 미실현 이익을 뜻하는 보험 회계 지표입니다.',
      'HNB':'가열담배. 담뱃잎을 태우지 않고 가열해 사용하는 제품입니다.',
      '건기식':'건강기능식품. 건강 유지에 도움을 줄 수 있는 기능성을 인정받은 식품입니다.',
      '홍삼':'인삼을 찌고 말려 만든 건강기능식품 원료입니다.',
      '가격결정력':'원가가 올라도 판매가격을 올려 이익을 지킬 수 있는 힘입니다.',
    };
    const TERM_KEYS = Object.keys(BUSINESS_GLOSSARY).sort((a, b) => b.length - a.length);
    const TERM_PATTERN = new RegExp('(' + TERM_KEYS.map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|') + ')', 'g');
    const TERM_SKIP_AFTER = {
      '리스': ['크'],
    };
    let renderedTermNotes = new Set();
    function isAsciiWordChar(value) {
      return /^[A-Za-z0-9]$/.test(value || '');
    }
    function isEmbeddedLatinTerm(term, previous, next) {
      const startsLatin = /^[A-Za-z0-9]/.test(term);
      const endsLatin = /[A-Za-z0-9]$/.test(term);
      return (startsLatin && isAsciiWordChar(previous)) || (endsLatin && isAsciiWordChar(next));
    }
    function rich(value) {
      const text = esc(value);
      return text.replace(TERM_PATTERN, (term, _match, offset, source) => {
        const previous = source.slice(Math.max(0, offset - 1), offset);
        const next = source.slice(offset + term.length, offset + term.length + 1);
        if (isEmbeddedLatinTerm(term, previous, next)) return term;
        if ((TERM_SKIP_AFTER[term] || []).includes(next)) return term;
        const tip = BUSINESS_GLOSSARY[term];
        if (!tip) return term;
        if (renderedTermNotes.has(term)) return term;
        renderedTermNotes.add(term);
        return '<span class="term-note" tabindex="0" data-tip="' + esc(tip) + '">' + term + '</span>';
      });
    }
    const num = (value) => Number.isFinite(Number(value)) ? Number(value) : null;
    function moneyEok(value) {
      const v = num(value);
      if (v == null) return "N/A";
      const sign = v < 0 ? "-" : "";
      const a = Math.abs(v);
      if (a >= 10000) return sign + (a / 10000).toLocaleString("ko-KR", {maximumFractionDigits: 1}) + "조";
      return sign + a.toLocaleString("ko-KR", {maximumFractionDigits: 0}) + "억";
    }
    function pct(value) {
      const v = num(value);
      if (v == null) return "N/A";
      return v.toLocaleString("ko-KR", {maximumFractionDigits: 1}) + "%";
    }
    function marketCapText(value) {
      const v = num(value);
      if (!v) return "시총 N/A";
      const jo = v / 1_0000_0000_0000;
      if (jo >= 1) return "시총 " + jo.toLocaleString("ko-KR", {maximumFractionDigits: 1}) + "조";
      return "시총 " + (v / 1_0000_0000).toLocaleString("ko-KR", {maximumFractionDigits: 0}) + "억";
    }
    function perText(value) {
      const v = num(value);
      if (!v || v <= 0) return "PER N/A";
      return "PER " + v.toLocaleString("ko-KR", {maximumFractionDigits: v >= 100 ? 0 : 1}) + "배";
    }
    function ratio(a, b) {
      a = num(a); b = num(b);
      if (a == null || b == null || b === 0) return null;
      return a / b;
    }
    function changeText(values) {
      if (!values || values.length < 2) return "추이 부족";
      const first = num(values[0]); const last = num(values[values.length - 1]);
      if (first == null || last == null || first === 0) return "추이 부족";
      const chg = (last / first - 1) * 100;
      return (chg >= 0 ? "+" : "") + chg.toFixed(1) + "%";
    }
    function miniTrend(values, years, cls) {
      values = values || [];
      years = years || [];
      const absMax = Math.max(1, ...values.map((v) => Math.abs(num(v) || 0)));
      const bars = values.map((v, i) => {
        const n = num(v) || 0;
        const h = Math.max(5, Math.round(Math.abs(n) / absMax * 76));
        return '<span class="' + (n < 0 ? 'neg' : '') + '" data-y="' + esc(String(years[i] || "")) + '" style="--h:' + h + 'px"></span>';
      }).join("");
      return '<div class="trend ' + (cls || "") + '">' + bars + '</div><span class="trend-value">' + esc(values.map(moneyEok).join(" → ")) + '</span>';
    }
    function moneyBaekman(value) {
      const v = num(value);
      if (v == null) return "N/A";
      const sign = v < 0 ? "-" : "";
      const a = Math.abs(v);
      if (a >= 1000000) return sign + (a / 1000000).toLocaleString("ko-KR", {maximumFractionDigits: 1}) + "조";
      return sign + (a / 100).toLocaleString("ko-KR", {maximumFractionDigits: 0}) + "억";
    }
    function rdTrend(values, years, cls, formatter) {
      if (!values || !values.length) return '<p class="empty">숫자표가 없을 때는 신제품, 수주, 설비투자, 연구개발활동 문단을 함께 봅니다.</p>';
      const absMax = Math.max(1, ...values.map((v) => Math.abs(num(v) || 0)));
      const bars = values.map((v, i) => {
        const n = num(v) || 0;
        const h = Math.max(6, Math.round(Math.abs(n) / absMax * 76));
        return '<span class="' + (n < 0 ? 'neg' : '') + '" data-y="' + esc(String(years[i] || "")) + '" style="--h:' + h + 'px"></span>';
      }).join("");
      return '<div class="trend ' + (cls || "") + '">' + bars + '</div><span class="trend-value">' + esc(values.map(formatter).join(" → ")) + '</span>';
    }
    function compactSentence(text, limit) {
      let value = String(text || '').replace(/\s+/g, ' ').trim();
      value = value.replace(/☞.*$/, '').replace(/※.*$/, '').trim();
      const sentenceEndPos = (snippet, before) => {
        const ends = ['습니다.', '입니다.', '니다.', '다.', '.'];
        const cap = before == null ? snippet.length : before;
        let best = -1;
        for (const end of ends) {
          let idx = snippet.lastIndexOf(end, cap);
          while (idx > 0 && end === '.' && /\d/.test(snippet[idx - 1] || '')) {
            idx = snippet.lastIndexOf(end, idx - 1);
          }
          if (idx >= 0) best = Math.max(best, idx + end.length);
        }
        return best;
      };
      const finish = (snippet) => {
        let out = String(snippet || '').trim().replace(/[,\s·ㆍ-]+$/g, '');
        out = completeKoreanSentence(out);
        if (/\d+\.$/.test(out)) {
          const prev = sentenceEndPos(out, out.length - 4);
          if (prev > 0) return out.slice(0, prev);
          return out.replace(/\s+\S*\d+\.$/, '').trim();
        }
        return out;
      };
      if (value.length <= limit) return finish(value);
      const cut = value.slice(0, limit).trim();
      const last = sentenceEndPos(cut);
      if (last > limit * 0.45) return finish(cut.slice(0, last));
      const next = value.indexOf('다.', limit);
      if (next > 0 && next < Math.max(limit * 2.4, 420)) return finish(value.slice(0, next + 2));
      const breakAt = Math.max(cut.lastIndexOf('며,'), cut.lastIndexOf('지만,'), cut.lastIndexOf('고,'), cut.lastIndexOf(','));
      if (breakAt > limit * 0.55) return finish(cut.slice(0, breakAt));
      const spaceAt = cut.lastIndexOf(' ');
      if (spaceAt > limit * 0.65) return finish(cut.slice(0, spaceAt));
      return finish(cut);
    }
    function sentenceList(text, fallback, maxItems = 3) {
      const source = String(text || '').replace(/\s+/g, ' ').trim();
      if (!source) return '<p class="empty">' + rich(fallback) + '</p>';
      const sentences = source
        .split(/(?<=다\.|니다\.|입니다\.|습니다\.|음\.|함\.)\s+/)
        .map((s) => compactSentence(s, 104))
        .filter((s) => s.length >= 12 && !/^[-※]/.test(s))
        .slice(0, maxItems);
      const items = sentences.length ? sentences : [compactSentence(source, 120)];
      return '<ul class="summary-list">' + items.map((s) => '<li>' + rich(s) + '</li>').join('') + '</ul>';
    }
    function completeKoreanSentence(text) {
      let out = String(text || '').trim().replace(/[,\s·ㆍ-]+$/g, '');
      if (!out) return out;
      if (/(습니다|입니다|합니다|됩니다|됩니다|했습니다|있습니다|없습니다|다|음|함)\.$/.test(out) || /[.!?]$/.test(out)) return out;
      const replacements = [
        [/생산하며$/, '생산한다고 설명합니다.'],
        [/판매하며$/, '판매한다고 설명합니다.'],
        [/운영하며$/, '운영한다고 설명합니다.'],
        [/제공하며$/, '제공한다고 설명합니다.'],
        [/수행하며$/, '수행한다고 설명합니다.'],
        [/영위하며$/, '영위한다고 설명합니다.'],
        [/포함하며$/, '포함한다고 설명합니다.'],
        [/구성되며$/, '구성된다고 설명합니다.'],
        [/연결되며$/, '연결된다고 설명합니다.'],
        [/차지하며$/, '차지한다고 설명합니다.'],
        [/보유하며$/, '보유한다고 설명합니다.'],
        [/개발하며$/, '개발한다고 설명합니다.'],
        [/제조하며$/, '제조한다고 설명합니다.'],
        [/하며$/, '한다고 설명합니다.'],
        [/이고$/, '입니다.'],
        [/이며$/, '입니다.'],
        [/되며$/, '됩니다.'],
        [/하고$/, '한다고 설명합니다.'],
        [/\s및$/, ' 등입니다.'],
      ];
      for (const [pattern, replacement] of replacements) {
        if (pattern.test(out)) return out.replace(pattern, replacement);
      }
      if (/[가-힣](을|를|은|는|이|가|의|에|에서|으로|로|와|과)$/.test(out)) {
        return out + ' 관련 내용입니다.';
      }
      return out + '.';
    }
    function rawMovesHtml(moves) {
      if (!moves || !moves.length) return fallbackList([
        '가격 변화율 표가 없으면 매출원가율, 재고자산 증가, 판매가격 전가 가능성을 먼저 봅니다.',
        '금융·지주·플랫폼 기업은 원재료보다 금리, 수수료, 운용자산, 고객 지표가 더 자연스러운 관찰 대상입니다.',
        '제조업은 원재료 가격 상승이 재고자산 단가와 매출총이익률에 늦게 반영될 수 있습니다.'
      ]);
      return moves.map((m) => {
        const v = num(m.pct) || 0;
        const w = Math.min(48, Math.max(3, Math.abs(v) * 3.6));
        const cls = v >= 0 ? "up" : "down";
        return '<div class="raw-row"><span class="raw-name">' + rich(m.name) + '</span><span class="track"><span class="bar ' + cls + '" style="width:' + w + '%"></span></span><span class="raw-pct">' + (v >= 0 ? '+' : '') + v.toFixed(1).replace('.0','') + '%</span></div>';
      }).join("");
    }
    function utilizationHtml(items) {
      if (!items || !items.length) return fallbackList([
        '가동률 표가 없으면 유형자산, 감가상각비, 설비투자, 수주잔고 문단을 함께 봅니다.',
        '장치산업은 고정비가 커서 가동률이 낮아지면 제품 하나당 부담하는 비용이 커질 수 있습니다.',
        '금융·지주사는 공장 가동률 대신 자회사 실적, 자본비율, 손해율, 운용자산 흐름을 봅니다.'
      ]);
      return items.map((item) => {
        const r = Math.max(0, Math.min(100, num(item.rate) || 0));
        return '<div class="util-row"><div class="util-head"><span>' + rich(item.name) + '</span><span>' + pct(r) + '</span></div><div class="track"><span class="util-fill" style="width:' + r + '%"></span></div></div>';
      }).join("");
    }
    function snippetCard(title, text, fallback) {
      return '<article class="card snippet"><h3>' + esc(title) + '</h3>' + sentenceList(text, fallback, 3) + '</article>';
    }
    function fallbackList(items) {
      return '<ul class="summary-list">' + items.map((item) => '<li>' + rich(item) + '</li>').join('') + '</ul>';
    }
    function cardTitles(row) {
      return (row.business_cards || []).map((card) => card.title).filter(Boolean);
    }
    function cardCaptions(row) {
      return (row.business_cards || []).map((card) => card.caption).filter(Boolean);
    }
    function compactList(items, maxItems) {
      return '<ul class="summary-list">' + (items || []).filter(Boolean).slice(0, maxItems || 4).map((item) => '<li>' + rich(item) + '</li>').join('') + '</ul>';
    }
    function industryKey(row) {
      const code = String(row.stock_code || '');
      if (['105560','055550','086790','316140'].includes(code)) return 'bank';
      if (['032830','000810'].includes(code)) return 'insurance';
      if (['006800'].includes(code)) return 'securities';
      if (['138040'].includes(code)) return 'holding';
      const text = [row.name, categoryOf(row, ''), badgeOf(row, ''), sectorOf(row)].join(' ');
      if (/금융업/.test(text)) return 'bank';
      if (/증권업|증권/.test(text)) return 'securities';
      if (/지주|복합/.test(text)) return 'holding';
      if (/생명보험|손해보험|보험/.test(text)) return 'insurance';
      if (/종합반도체|메모리반도체|반도체장비|전자부품/.test(text)) return 'semiconductor';
      if (/배터리|2차전지|배터리소재/.test(text)) return 'battery';
      if (/완성차|자동차부품/.test(text)) return 'auto';
      if (/조선|해운/.test(text)) return /해운/.test(text) ? 'shipping' : 'shipbuilding';
      if (/방산|항공우주|철도/.test(text)) return 'defense';
      if (/바이오|CDMO|의약품/.test(text)) return 'bio';
      if (/전력|발전|유틸리티/.test(text)) return 'power';
      if (/화학|철강|금속|소재|정유|에너지/.test(text)) return 'materials';
      if (/인터넷|플랫폼/.test(text)) return 'platform';
      if (/통신/.test(text)) return 'telecom';
      if (/건설/.test(text)) return 'construction';
      if (/담배|건기식/.test(text)) return 'consumer';
      return 'general';
    }
    const LENS = {
      bank: {
        money: ['은행·카드·증권·보험 자회사에서 이자이익, 수수료, 운용손익이 나옵니다.', '금리가 오르면 예대마진은 좋아질 수 있지만, 연체와 대손비용도 같이 봐야 합니다.', '투자자는 ROE, 보통주자본비율, 대손충당금, 배당성향을 함께 봅니다.'],
        shakes: ['금리와 예대마진', '대출 성장과 연체율', '대손충당금 전입액', '자본비율과 배당 여력'],
        signalTitle: '은행·금융지주 핵심 신호',
        signalLead: '금융지주는 공장 가동률보다 돈을 빌려주고 회수하는 능력, 자본 여력, 배당 지속성이 중요합니다.',
        signals: [
          ['ROE·자본비율', '자본을 얼마나 효율적으로 굴리는지와 배당 여력을 같이 보여줍니다.'],
          ['순이자마진', '예금 조달비용과 대출금리 차이가 이자이익을 움직입니다.'],
          ['대손충당금', '경기가 나빠질 때 손실을 먼저 비용으로 잡는 항목입니다.'],
          ['비이자이익', '카드, 증권, 수수료, 운용손익이 이익 변동성을 만듭니다.']
        ],
        impacts: [
          ['순이자마진', '손익계산서의 이자수익·이자비용, 순이자이익에 직접 연결됩니다.'],
          ['연체와 충당금', '대손상각비와 대출채권 손상, 충당부채 성격의 계정에 영향을 줍니다.'],
          ['자본비율', '재무상태표의 자본총계와 위험가중자산 대비 여력을 보는 지표입니다.'],
          ['배당', '이익잉여금과 현금흐름, 주주환원 정책으로 이어집니다.']
        ],
        strategyTitle: '건전성·배당·자본 체크',
        strategy: [['ROE', '자본 대비 이익 창출력을 봅니다.'], ['보통주자본비율', '배당과 성장의 안전판입니다.'], ['충당금', '나쁜 대출을 미리 비용화했는지 봅니다.']]
      },
      insurance: {
        money: ['보험료를 받고, 보험금·사업비·준비금을 뺀 뒤 보험손익과 투자손익으로 돈을 법니다.', '장기보험은 유지율과 손해율, 자동차보험은 손해율 변동이 실적을 크게 흔듭니다.', '금리 변화는 운용자산 수익률과 보험부채 평가에 모두 영향을 줍니다.'],
        shakes: ['손해율과 유지율', '보험부채와 준비금', '운용자산 수익률', '금리와 지급여력비율'],
        signalTitle: '보험사 핵심 신호',
        signalLead: '보험사는 매출보다 보험계약마진, 손해율, 투자손익, 지급여력 흐름이 더 중요합니다.',
        signals: [
          ['손해율', '받은 보험료 대비 나간 보험금 비율입니다. 높아지면 보험손익이 약해집니다.'],
          ['투자손익', '보험료로 운용하는 자산의 이익입니다. 금리와 시장 가격에 민감합니다.'],
          ['보험부채', '미래 보험금 지급 의무입니다. 재무상태표의 핵심 부담입니다.'],
          ['배당 여력', '자본규제와 지급여력비율이 주주환원의 상한을 만듭니다.']
        ],
        impacts: [
          ['보험료', '보험수익과 계약서비스마진 인식으로 이어집니다.'],
          ['보험금·손해율', '보험서비스비용과 보험계약부채에 영향을 줍니다.'],
          ['운용자산', '투자수익, 기타포괄손익, 금융자산 평가에 연결됩니다.'],
          ['지급여력', '자본총계와 배당 가능성의 안전판입니다.']
        ],
        strategyTitle: '보험 손익과 운용자산 체크',
        strategy: [['손해율', '보험 본업의 마진을 봅니다.'], ['투자손익', '운용자산 수익성이 실적을 보탭니다.'], ['지급여력', '배당과 성장의 제약 조건입니다.']]
      },
      securities: {
        money: ['주식·채권 중개 수수료, IB 자문·인수 수수료, 자기자본 운용손익에서 돈을 법니다.', '거래대금이 늘면 위탁매매가 좋아지고, 금리와 시장 가격은 운용손익을 흔듭니다.', '부동산 PF와 대체투자는 수익원이면서 동시에 손상 위험입니다.'],
        shakes: ['시장 거래대금', '금리와 채권 평가손익', 'IB·PF 수수료', '자기자본 투자손익'],
        signalTitle: '증권사 핵심 신호',
        signalLead: '증권사는 제조업의 가동률보다 시장 거래대금, 금리, IB 딜, 운용손익 변동성이 핵심입니다.',
        signals: [
          ['거래대금', '개인·기관 매매가 활발하면 브로커리지 수수료가 늘어납니다.'],
          ['IB 수수료', '인수금융, IPO, 구조화금융 딜이 비이자수익을 만듭니다.'],
          ['운용손익', '채권·주식·파생 평가손익이 분기 실적을 흔듭니다.'],
          ['PF 익스포저', '부동산 경기 악화 시 충당금과 손상 위험이 커집니다.']
        ],
        impacts: [
          ['수수료수익', '영업수익의 안정적인 축입니다.'],
          ['운용손익', '당기손익공정가치 금융상품 평가손익에 반영됩니다.'],
          ['충당금·손상', '대출채권·보증·PF 관련 손실 비용으로 연결됩니다.'],
          ['자본규모', 'IB와 운용 한도를 결정하는 재무상태표 기반입니다.']
        ],
        strategyTitle: '시장 민감도와 리스크 체크',
        strategy: [['거래대금', '브로커리지 회복 신호입니다.'], ['IB 파이프라인', '수수료 성장성을 봅니다.'], ['PF·충당금', '나쁜 자산 비용화를 확인합니다.']]
      },
      holding: {
        money: ['자회사 배당, 브랜드수수료, 지분법손익, 투자자산 가치 변화가 핵심입니다.', '별도 현금흐름은 배당 재원이고, 연결 실적은 자회사 업황을 반영합니다.', '인수·매각·신사업 투자는 단기 손익보다 포트폴리오 재편 신호로 읽습니다.'],
        shakes: ['자회사 실적과 배당', '지분법손익', '투자자산 평가', '인수·매각과 차입금'],
        signalTitle: '지주사·복합기업 핵심 신호',
        signalLead: '지주사는 제품 가동률보다 어떤 자회사가 현금을 보내는지, 투자와 처분이 자산구조를 어떻게 바꾸는지가 중요합니다.',
        signals: [
          ['자회사 배당', '지주사의 별도 현금흐름과 배당 여력을 만듭니다.'],
          ['지분법손익', '연결되지 않는 투자회사의 실적이 손익에 들어옵니다.'],
          ['투자·처분', '일회성 이익과 포트폴리오 방향성을 동시에 보여줍니다.'],
          ['차입금', '투자를 많이 하는 지주사는 이자비용 부담도 봐야 합니다.']
        ],
        impacts: [
          ['배당금수익', '별도 손익계산서와 현금흐름표의 핵심입니다.'],
          ['지분법손익', '관계기업투자와 당기순이익을 동시에 움직입니다.'],
          ['투자자산', '재무상태표의 장기금융자산·관계기업투자에 쌓입니다.'],
          ['차입금', '재무상태표 부채와 이자비용으로 이어집니다.']
        ],
        strategyTitle: '포트폴리오와 현금흐름 체크',
        strategy: [['자회사', '어디서 배당과 이익이 오는지 봅니다.'], ['투자·처분', '그룹 방향 전환의 신호입니다.'], ['차입금', '투자 재원의 부담을 확인합니다.']]
      },
      semiconductor: {
        money: ['메모리·시스템반도체·장비·부품 판매가 매출을 만들고, 판가는 업황 사이클을 강하게 탑니다.', 'HBM, 서버 DRAM, 첨단 패키징처럼 고부가 제품 비중이 올라가면 이익률이 개선됩니다.', '대규모 설비투자는 미래 매출의 씨앗이지만 감가상각비 부담도 만듭니다.'],
        shakes: ['메모리 가격과 출하량', '고객사 CAPEX', '가동률과 재고', '감가상각비와 연구개발'],
        signalTitle: '반도체 핵심 신호',
        signalLead: '반도체는 제품 가격, 출하량, 가동률, 재고, 설비투자가 손익과 현금흐름을 동시에 흔듭니다.',
        signals: [
          ['판가·출하량', '매출액과 매출총이익률을 가장 빠르게 움직입니다.'],
          ['재고', '업황 둔화 때 재고평가손실과 가격 하락 위험을 보여줍니다.'],
          ['CAPEX', '현금은 먼저 나가고 이후 감가상각비로 비용화됩니다.'],
          ['R&D', '공정 전환과 신제품 경쟁력의 비용이자 투자입니다.']
        ],
        impacts: [
          ['판가', '매출액과 매출총이익률을 움직입니다.'],
          ['재고', '재고자산과 재고평가손실, 운전자본에 연결됩니다.'],
          ['설비투자', '투자활동현금흐름, 유형자산, 감가상각비로 이어집니다.'],
          ['가동률', '고정비 흡수율을 바꿔 영업이익률을 흔듭니다.']
        ],
        strategyTitle: '기술·설비투자 체크',
        strategy: [['HBM·선단제품', '제품 믹스 개선 신호입니다.'], ['CAPEX', '미래 생산능력과 감가상각비를 동시에 만듭니다.'], ['재고', '업황 반전 또는 둔화의 단서입니다.']]
      },
      battery: {
        money: ['배터리 셀·소재 판매에서 매출이 나오고, 고객사 생산계획과 원재료 가격이 이익률을 흔듭니다.', '장기 공급계약은 매출 가시성을 높이지만, 램프업 지연과 판가 연동 조건을 함께 봐야 합니다.', '원재료 가격 변화는 매출원가와 재고자산 평가에 시차를 두고 반영됩니다.'],
        shakes: ['리튬·니켈 등 원재료', '고객사 전기차 판매', '공장 램프업과 가동률', '재고평가와 장기공급계약'],
        signalTitle: '배터리·소재 핵심 신호',
        signalLead: '배터리는 원재료 가격, 고객사 수요, 신규 공장 가동률, 재고평가가 실적을 크게 바꿉니다.',
        signals: [
          ['원재료 가격', '매출원가와 재고 단가에 영향을 줍니다.'],
          ['가동률', '새 공장이 정상 속도에 올라왔는지 보여줍니다.'],
          ['고객사 수요', '전기차 판매 둔화는 출하량과 판가를 누릅니다.'],
          ['재고평가', '원재료 가격 하락기에는 평가손실 가능성이 커집니다.']
        ],
        impacts: [
          ['원재료', '매출원가, 재고자산, 매출총이익률에 연결됩니다.'],
          ['증설', '유형자산과 투자활동현금흐름을 키웁니다.'],
          ['가동률', '고정비 부담과 영업이익률을 흔듭니다.'],
          ['장기계약', '수주잔고와 매출 가시성의 근거가 됩니다.']
        ],
        strategyTitle: '수요·원재료·가동률 체크',
        strategy: [['원재료', '가격 전가 여부가 마진을 결정합니다.'], ['램프업', '신공장 효율을 확인합니다.'], ['고객사', '전기차 수요와 연결됩니다.']]
      },
      auto: {
        money: ['완성차·부품 판매와 금융·서비스가 매출을 만들고, 판매량과 평균판매가격이 이익률을 좌우합니다.', 'SUV·전기차·고급차 비중이 높아지면 믹스 효과로 마진이 좋아질 수 있습니다.', '환율, 인센티브, 원재료, 리콜 비용이 실적을 흔듭니다.'],
        shakes: ['판매대수와 ASP', '차종 믹스', '환율과 인센티브', '원재료·리콜·보증비'],
        signalTitle: '자동차·부품 핵심 신호',
        signalLead: '자동차는 판매량만큼 가격 믹스, 환율, 인센티브, 보증비가 중요합니다.',
        signals: [
          ['판매대수', '매출 규모의 출발점입니다.'],
          ['ASP·믹스', '고가 차종 비중이 매출총이익률을 올립니다.'],
          ['환율', '수출 기업은 원화 약세 때 이익이 좋아질 수 있습니다.'],
          ['보증비·리콜', '판매 후 비용이 영업이익을 누를 수 있습니다.']
        ],
        impacts: [
          ['판매량', '매출액과 재고자산 회전에 연결됩니다.'],
          ['인센티브', '매출 차감 또는 판매비 부담으로 나타납니다.'],
          ['보증비', '충당부채와 판매관리비를 키울 수 있습니다.'],
          ['금융부문', '금융수익과 신용손실 위험을 함께 만듭니다.']
        ],
        strategyTitle: '판매량·믹스·보증비 체크',
        strategy: [['판매대수', '수요 흐름을 봅니다.'], ['ASP', '가격과 차종 믹스입니다.'], ['보증비', '품질 비용의 신호입니다.']]
      },
      shipbuilding: {
        money: ['선박·해양플랜트 수주가 먼저 쌓이고, 인도와 납품을 거치며 매출로 바뀝니다.', '선가가 높을 때 받은 수주는 몇 년 뒤 매출과 이익률로 나타납니다.', '후판 가격, 납기 지연, 환율, 충당금이 실적을 흔듭니다.'],
        shakes: ['수주잔고와 선가', '선종 믹스', '후판 가격', '납기 지연·충당금'],
        signalTitle: '조선 핵심 신호',
        signalLead: '조선사는 지금 매출보다 수주잔고, 선가, 고부가 선박 비중, 원가 리스크를 같이 봐야 몇 년 뒤 실적이 보입니다.',
        signals: [
          ['수주잔고', '미래 매출의 재료입니다.'],
          ['선가', '고가 수주가 이익률 개선으로 이어집니다.'],
          ['선종 믹스', 'LNG선·해양플랜트·특수선 비중이 수익성을 바꿉니다.'],
          ['후판 가격', '매출원가를 크게 흔드는 원재료입니다.'],
        ],
        impacts: [
          ['수주', '계약자산·계약부채와 미래 매출 가시성에 연결됩니다.'],
          ['선종 믹스', '고부가 선박 비중이 매출과 이익률을 바꿉니다.'],
          ['후판', '매출원가와 재고·원재료 부담을 키웁니다.'],
          ['납기 지연', '지연이나 원가 초과가 생기면 이익률과 충당금에 영향을 줍니다.']
        ],
        strategyTitle: '수주잔고·선가·선종 믹스 체크',
        strategy: [['수주잔고', '몇 년치 일감인지 봅니다.'], ['선가', '좋은 가격에 받은 계약인지 봅니다.'], ['선종 믹스', 'LNG선·특수선 같은 고부가 물량을 봅니다.']]
      },
      shipping: {
        money: ['컨테이너선과 벌크선 운임이 매출과 이익을 좌우합니다.', '운임이 오르면 매출은 빨리 좋아지지만, 선박·연료·항만 비용도 함께 봐야 합니다.', '장기계약과 현물운임 비중이 실적 변동성을 결정합니다.'],
        shakes: ['해상운임', '물동량', '유가와 항만비', '선복 공급'],
        signalTitle: '해운 핵심 신호',
        signalLead: '해운은 공장보다 선복 공급, 운임, 물동량, 유가가 손익을 움직입니다.',
        signals: [
          ['운임', '매출과 영업이익률의 핵심 변수입니다.'],
          ['물동량', '세계 교역량과 경기 흐름을 반영합니다.'],
          ['유가', '연료비 부담으로 매출원가를 흔듭니다.'],
          ['선복 공급', '선박 공급이 많으면 운임이 눌릴 수 있습니다.']
        ],
        impacts: [
          ['운임', '매출액과 영업이익률에 직접 연결됩니다.'],
          ['연료비', '매출원가와 현금흐름을 흔듭니다.'],
          ['선박투자', '유형자산, 리스부채, 감가상각비로 이어집니다.'],
          ['장기계약', '매출 안정성과 변동성을 결정합니다.']
        ],
        strategyTitle: '운임·물동량·유가 체크',
        strategy: [['운임', '수익성의 출발점입니다.'], ['물동량', '수요의 방향입니다.'], ['연료비', '비용 압박을 봅니다.']]
      },
      defense: {
        money: ['방산·항공·철도는 계약을 따낸 뒤 납품과 진행률에 따라 매출이 인식됩니다.', '정부 예산, 수출 허가, 납품 일정, 수주잔고가 실적 가시성을 만듭니다.', '개발비와 품질 보증비, 공정 지연은 비용 리스크입니다.'],
        shakes: ['수주잔고', '정부 예산과 수출 계약', '납품 일정', '개발비·품질비용'],
        signalTitle: '방산·항공 핵심 신호',
        signalLead: '방산은 단기 판매량보다 수주잔고, 납품 일정, 정부 예산, 개발비 회수가 중요합니다.',
        signals: [
          ['수주잔고', '미래 매출의 가시성을 줍니다.'],
          ['납품 일정', '매출 인식과 현금 회수를 결정합니다.'],
          ['정부 예산', '방산 수요의 출발점입니다.'],
          ['개발비', '미래 제품 경쟁력과 비용 부담을 동시에 만듭니다.']
        ],
        impacts: [
          ['수주', '계약자산·계약부채와 매출 인식에 연결됩니다.'],
          ['개발비', '연구개발비 또는 무형자산으로 이어질 수 있습니다.'],
          ['납품 지연', '매출 지연과 충당금 위험을 만듭니다.'],
          ['환율', '수출 계약의 매출과 이익률을 흔듭니다.']
        ],
        strategyTitle: '수주·납품·개발비 체크',
        strategy: [['수주잔고', '일감의 두께입니다.'], ['납품', '매출 인식의 시점입니다.'], ['개발비', '신제품과 비용 부담입니다.']]
      },
      bio: {
        money: ['위탁생산, 바이오시밀러, 신약 파이프라인에서 매출과 성장성이 나옵니다.', '공장 가동률과 품질 인증은 CDMO 매출의 신뢰도를 높입니다.', '임상·허가·특허·약가가 장기 가치를 크게 흔듭니다.'],
        shakes: ['공장 가동률', '수주와 고객사', '임상·허가', '품질 규제'],
        signalTitle: '바이오 핵심 신호',
        signalLead: '바이오는 현재 매출뿐 아니라 수주, 공장 가동률, 허가 일정, 품질 규제가 중요합니다.',
        signals: [
          ['수주·고객사', 'CDMO 매출 가시성을 보여줍니다.'],
          ['가동률', '대형 공장이 얼마나 차 있는지 확인합니다.'],
          ['허가·임상', '제품 출시와 매출 시작 시점을 좌우합니다.'],
          ['품질 규제', '생산 중단 리스크를 낮추는 핵심입니다.']
        ],
        impacts: [
          ['수주', '계약부채와 향후 매출 가시성에 연결됩니다.'],
          ['공장투자', '유형자산과 감가상각비를 키웁니다.'],
          ['연구개발', '비용 또는 무형자산으로 처리될 수 있습니다.'],
          ['허가', '매출 발생 시점과 재고자산 회전을 바꿉니다.']
        ],
        strategyTitle: '수주·가동률·허가 체크',
        strategy: [['수주', '매출 가시성입니다.'], ['가동률', '고정비 흡수율입니다.'], ['허가', '제품 출시의 관문입니다.']]
      },
      power: {
        money: ['전력 판매, 발전설비, 전력기기, 송배전망 투자에서 매출이 나옵니다.', '원전·발전·전력망 투자는 수주잔고와 장기 프로젝트로 실적이 쌓입니다.', '연료비, 전기요금, 구리·철강 가격, 정부 정책이 수익성을 흔듭니다.'],
        shakes: ['전기요금과 연료비', '전력망 투자', '수주잔고', '원재료 가격'],
        signalTitle: '전력·발전 핵심 신호',
        signalLead: '전력 업종은 요금·연료비·전력망 투자·수주잔고가 손익과 현금흐름을 움직입니다.',
        signals: [
          ['전기요금', '원가 상승분을 회수할 수 있는지 봅니다.'],
          ['연료비', '매출원가와 현금흐름을 크게 흔듭니다.'],
          ['전력망 투자', '변압기·전력기기 수요의 출발점입니다.'],
          ['수주잔고', '장기 프로젝트 매출의 가시성입니다.']
        ],
        impacts: [
          ['연료비', '매출원가와 영업이익률에 연결됩니다.'],
          ['설비투자', '유형자산, 감가상각비, 차입금으로 이어집니다.'],
          ['수주', '계약자산과 향후 매출 가시성을 만듭니다.'],
          ['요금', '매출액과 정책 리스크를 동시에 보여줍니다.']
        ],
        strategyTitle: '요금·수주·설비투자 체크',
        strategy: [['요금', '원가 회수 여부입니다.'], ['수주잔고', '미래 매출입니다.'], ['설비투자', '현금 유출과 감가상각입니다.']]
      },
      platform: {
        money: ['광고, 커머스, 콘텐츠, 결제, 클라우드 같은 디지털 서비스에서 매출이 납니다.', '이용자 트래픽과 체류시간은 광고와 거래액으로 연결됩니다.', 'AI·클라우드 투자는 장기 성장 동력이지만 서버비와 인건비 부담을 키웁니다.'],
        shakes: ['이용자 트래픽', '광고 경기', '커머스 거래액', 'AI·클라우드 투자비'],
        signalTitle: '플랫폼 핵심 신호',
        signalLead: '플랫폼은 공장 가동률 대신 이용자, 광고 경기, 거래액, 서버·AI 투자비를 봅니다.',
        signals: [
          ['이용자 지표', '트래픽이 광고와 커머스 매출의 출발점입니다.'],
          ['광고 경기', '경기가 나빠지면 광고주 예산이 줄 수 있습니다.'],
          ['거래액', '수수료 매출과 결제 매출의 기반입니다.'],
          ['AI 투자', '서버비와 인건비를 늘리지만 미래 서비스를 만듭니다.']
        ],
        impacts: [
          ['광고·수수료', '매출액과 영업이익률에 연결됩니다.'],
          ['서버투자', '유형자산, 감가상각비, 클라우드 비용으로 이어집니다.'],
          ['콘텐츠 투자', '무형자산 또는 비용으로 처리될 수 있습니다.'],
          ['인건비', '판관비와 연구개발비의 큰 축입니다.']
        ],
        strategyTitle: '트래픽·광고·AI 투자 체크',
        strategy: [['트래픽', '매출의 출발점입니다.'], ['광고', '경기 민감 수익입니다.'], ['AI 투자', '비용과 성장 동력을 동시에 봅니다.']]
      },
      telecom: {
        money: ['이동통신 요금, 인터넷·미디어, 데이터센터·AI 서비스에서 반복 매출이 나옵니다.', '가입자 수와 ARPU가 본업 매출을 만들고, 5G·AI 투자는 비용과 성장성을 동시에 만듭니다.', 'CAPEX와 감가상각비, 마케팅비가 이익률을 흔듭니다.'],
        shakes: ['가입자와 ARPU', '마케팅비', '5G·AI CAPEX', '배당 정책'],
        signalTitle: '통신 핵심 신호',
        signalLead: '통신사는 반복 매출이 강하지만 CAPEX, 감가상각비, 마케팅비, 배당 정책을 같이 봐야 합니다.',
        signals: [
          ['ARPU', '가입자 한 명당 매출입니다.'],
          ['가입자 순증', '본업 매출의 안정성을 보여줍니다.'],
          ['CAPEX', '네트워크 투자와 감가상각비의 출발점입니다.'],
          ['배당', '현금창출력과 주주환원 정책을 보여줍니다.']
        ],
        impacts: [
          ['요금 매출', '반복 매출과 영업현금흐름을 만듭니다.'],
          ['CAPEX', '투자활동현금흐름과 유형자산에 연결됩니다.'],
          ['감가상각비', '영업이익률을 누르는 고정비입니다.'],
          ['마케팅비', '가입자 확보 비용으로 판관비에 반영됩니다.']
        ],
        strategyTitle: 'ARPU·CAPEX·배당 체크',
        strategy: [['ARPU', '본업 단가입니다.'], ['CAPEX', '미래망 투자입니다.'], ['배당', '현금창출력의 결과입니다.']]
      },
      construction: {
        money: ['주택·건축·토목·플랜트 수주를 따낸 뒤 공정률에 따라 매출을 인식합니다.', '원가율 관리와 미분양, 공사 지연, 해외 프로젝트 손실 여부가 이익을 좌우합니다.', '수주잔고는 미래 매출의 재료지만, 좋은 수주인지 나쁜 수주인지 원가율을 같이 봐야 합니다.'],
        shakes: ['수주잔고', '원가율', '미분양·분양률', '공사손실충당금'],
        signalTitle: '건설 핵심 신호',
        signalLead: '건설은 수주잔고, 원가율, 미분양, 공사손실충당금이 재무제표를 크게 흔듭니다.',
        signals: [
          ['수주잔고', '미래 매출의 재료입니다.'],
          ['원가율', '매출총이익률을 좌우합니다.'],
          ['미분양', '현금 회수와 재고 리스크입니다.'],
          ['충당금', '손실 예상 프로젝트를 미리 비용화합니다.']
        ],
        impacts: [
          ['공정률', '매출액, 계약자산, 계약부채를 움직입니다.'],
          ['원가율', '매출원가와 매출총이익률에 연결됩니다.'],
          ['미분양', '재고자산과 현금흐름 부담을 키웁니다.'],
          ['충당금', '영업이익과 부채를 동시에 흔듭니다.']
        ],
        strategyTitle: '수주·원가율·미분양 체크',
        strategy: [['수주잔고', '일감입니다.'], ['원가율', '이익률입니다.'], ['충당금', '나쁜 현장의 비용입니다.']]
      },
      materials: {
        money: ['철강·화학·정유·소재는 제품 가격과 원재료 가격의 차이, 즉 스프레드가 이익률을 만듭니다.', '유가, 금속 가격, 환율, 중국 수요가 매출과 재고 평가를 흔듭니다.', '장치산업 특성상 가동률과 감가상각비가 영업이익률에 크게 작용합니다.'],
        shakes: ['제품-원재료 스프레드', '유가·금속 가격', '환율', '가동률과 재고평가'],
        signalTitle: '소재·정유·철강 핵심 신호',
        signalLead: '소재 업종은 매출보다 제품 가격과 원재료 가격의 차이, 재고평가, 가동률을 함께 봐야 합니다.',
        signals: [
          ['스프레드', '제품 가격에서 원재료 가격을 뺀 마진입니다.'],
          ['재고평가', '가격 하락기에는 평가손실이 생길 수 있습니다.'],
          ['가동률', '고정비 부담을 나누는 정도입니다.'],
          ['환율', '수출입 가격과 원가에 영향을 줍니다.']
        ],
        impacts: [
          ['원재료', '매출원가와 재고자산 단가에 연결됩니다.'],
          ['제품 가격', '매출액과 매출총이익률을 움직입니다.'],
          ['가동률', '고정비 흡수와 영업이익률을 바꿉니다.'],
          ['재고평가', '재고자산과 손익계산서 비용에 반영됩니다.']
        ],
        strategyTitle: '스프레드·재고·가동률 체크',
        strategy: [['스프레드', '마진의 핵심입니다.'], ['재고', '가격 하락 위험입니다.'], ['가동률', '고정비 흡수율입니다.']]
      },
      consumer: {
        money: ['담배, 전자담배, 건강기능식품 판매에서 반복 매출이 나옵니다.', '가격 인상, 세금, 글로벌 매출 비중, 브랜드 점유율이 이익률을 좌우합니다.', '규제와 소비 트렌드 변화가 장기 성장성을 흔듭니다.'],
        shakes: ['판매량과 가격', '세금·규제', '글로벌 매출', '브랜드 점유율'],
        signalTitle: '소비재 핵심 신호',
        signalLead: '소비재는 가격 인상력, 규제, 브랜드 점유율, 글로벌 매출 흐름이 중요합니다.',
        signals: [
          ['가격 인상력', '매출과 이익률을 동시에 올릴 수 있습니다.'],
          ['규제·세금', '수요와 마진을 제한할 수 있습니다.'],
          ['글로벌 매출', '성장률과 환율 효과를 만듭니다.'],
          ['브랜드', '반복 구매와 점유율의 기반입니다.']
        ],
        impacts: [
          ['판매량', '매출액과 재고 회전에 연결됩니다.'],
          ['가격', '매출총이익률을 움직입니다.'],
          ['세금', '판매가격과 비용 구조에 영향을 줍니다.'],
          ['해외 매출', '환율과 매출 성장성에 연결됩니다.']
        ],
        strategyTitle: '가격·규제·해외 성장 체크',
        strategy: [['가격', '마진의 핵심입니다.'], ['규제', '장기 리스크입니다.'], ['해외', '성장 축입니다.']]
      },
      general: {
        money: ['대표 제품·서비스 판매가 매출을 만들고, 비용 구조와 고객 수요가 이익률을 결정합니다.', '사업부별 매출과 이익이 잡히면 어느 사업이 회사를 움직이는지 먼저 봅니다.', '수주, 가격, 원가, 투자, 재무구조가 핵심 체크포인트입니다.'],
        shakes: ['매출 성장', '원가율', '투자 부담', '재무구조'],
        signalTitle: '핵심 사업 신호',
        signalLead: '업종 특성이 뚜렷하지 않을 때는 매출 동력, 원가율, 투자 부담, 재무구조를 함께 봅니다.',
        signals: [
          ['매출 동력', '무엇이 돈을 버는지 확인합니다.'],
          ['원가율', '돈을 벌수록 이익이 남는 구조인지 봅니다.'],
          ['투자', '미래 성장을 위한 현금 유출입니다.'],
          ['재무구조', '부채와 이자비용의 부담을 봅니다.']
        ],
        impacts: [
          ['매출 동력', '매출액과 영업현금흐름에 연결됩니다.'],
          ['원가율', '매출총이익률을 움직입니다.'],
          ['투자', '유형자산과 감가상각비로 이어집니다.'],
          ['재무구조', '차입금과 이자비용을 만듭니다.']
        ],
        strategyTitle: '사업·원가·투자 체크',
        strategy: [['매출', '성장의 출발점입니다.'], ['원가', '마진의 핵심입니다.'], ['투자', '미래 비용과 자산입니다.']]
      }
    };
    function lensFor(row) {
      return LENS[industryKey(row)] || LENS.general;
    }
    function whatSellsText(row) {
      const names = cardTitles(row);
      const captions = cardCaptions(row);
      const category = categoryOf(row, '핵심 사업');
      const asSentence = (text) => {
        const value = String(text || '').trim();
        if (!value) return '';
        return /[.!?。]|다$|요$|임$/.test(value) ? value : value + '입니다.';
      };
      return [
        names.length ? row.name + '의 사업 축은 ' + names.join(' · ') + '입니다.' : row.name + '은 ' + category + ' 사업을 중심으로 매출을 만듭니다.',
        captions.length ? asSentence('사업보고서 기준 핵심 품목은 ' + captions.slice(0, 3).join(' / ') + '입니다') : '사업보고서의 사업개요 문단을 바탕으로 회사가 돈을 버는 방식을 요약했습니다.',
        '아래 카드는 원문을 그대로 옮기지 않고, 회사 이해에 필요한 내용만 쉬운 말로 압축했습니다.'
      ];
    }
    function sourceSentence(text) {
      const value = compactSentence(text || '', 170);
      if (!value) return '';
      return '<p class="source-sentence">사업보고서 근거 문장: ' + rich(value) + '</p>';
    }
    function businessSourceList(row) {
      const snippets = row.snippets || {};
      const key = industryKey(row);
      if (key === 'holding' || String(row.stock_code || '') === '402340') {
        const segments = snippets.segment_breakdown || [];
        const segmentText = segments.length
          ? segments.slice(0, 5).map((segment) => {
              const share = Number(segment.revenue_share || 0);
              const pctText = Number.isFinite(share) ? ' ' + (share > 1 ? share : share * 100).toFixed(1).replace(/\\.0$/, '') + '%' : '';
              return segment.name + pctText + ': ' + segment.desc;
            }).join(' / ')
          : '';
        const items = [
          ['사업개요', snippets.overview],
          ['투자·포트폴리오 구조', segmentText || snippets.investor_note],
          ['초보 투자자 요약', snippets.investor_note],
        ].map((item) => [item[0], compactSentence(item[1] || '', 170)]).filter((item) => item[1]);
        if (!items.length) {
          return '<p class="source-sentence">' + rich('이 회사는 지주·투자회사 성격이 강해 제조업용 원재료·가동률보다 투자 포트폴리오와 자회사 이익 기여도를 먼저 확인하는 편이 좋습니다.') + '</p>';
        }
        return '<ol class="money-flow">' + items.map((item) => '<li><strong>' + esc(item[0]) + '</strong><br>' + rich(item[1]) + '</li>').join('') + '</ol>';
      }
      const items = [
        ['사업개요', snippets.overview],
        ['원재료·생산설비', snippets.raw_material || snippets.capacity],
        ['연구개발·신제품', snippets.rd],
      ].map((item) => [item[0], compactSentence(item[1] || '', 150)]).filter((item) => item[1]);
      if (!items.length) {
        return '<p class="source-sentence">' + rich('로컬에 수집된 사업보고서 원문에서 사업개요 문단을 찾지 못했습니다. DART 원문에서 II. 사업의 내용 중 사업의 개요와 주요 제품 및 서비스를 확인해주세요.') + '</p>';
      }
      return '<ol class="money-flow">' + items.map((item) => '<li><strong>' + esc(item[0]) + '</strong><br>' + rich(item[1]) + '</li>').join('') + '</ol>';
    }
    function segmentBreakdownHtml(row) {
      const segments = row.snippets && Array.isArray(row.snippets.segment_breakdown) ? row.snippets.segment_breakdown : [];
      if (!segments.length) return '';
      const maxShare = Math.max(...segments.map((segment) => Number(segment.revenue_share || 0)), 0.01);
      const cards = segments.slice(0, 6).map((segment) => {
        const share = Number(segment.revenue_share || 0);
        const pct = share > 1 ? share : share * 100;
        const width = Math.max(6, Math.min(100, (share / maxShare) * 100));
        return '<article class="segment-card">' +
          '<strong>' + rich(segment.name || '사업부문') + '</strong>' +
          '<div class="segment-share">' + pct.toFixed(1).replace(/\\.0$/, '') + '%</div>' +
          '<p class="segment-desc">' + rich(segment.desc || '사업보고서에 표시된 주요 사업부문입니다.') + '</p>' +
          '<div class="segment-bar"><span style="--w:' + width.toFixed(1) + '%"></span></div>' +
        '</article>';
      }).join('');
      return '<div class="segment-breakdown">' +
        '<div class="segment-breakdown-head"><div><h3>부문별 매출비중과 사업 설명</h3><p>사업보고서 요약 데이터 기준으로 어느 부문이 회사 매출을 크게 움직이는지 먼저 보여줍니다.</p></div><div class="mini-label">보고서 표시 기준</div></div>' +
        '<div class="segment-grid">' + cards + '</div>' +
        '<p class="segment-tip">부문 간 내부거래 제거 방식에 따라 단순 합계가 100%와 다를 수 있어, 막대는 전체 파이 비중보다 사업 규모를 비교하는 신호판으로 읽으면 됩니다.</p>' +
      '</div>';
    }
    function sortedSegments(row) {
      const segments = row.snippets && Array.isArray(row.snippets.segment_breakdown) ? row.snippets.segment_breakdown : [];
      return segments
        .map((segment) => ({
          name: segment.name || '',
          desc: segment.desc || '',
          share: Number(segment.revenue_share || 0),
        }))
        .filter((segment) => segment.name)
        .sort((a, b) => b.share - a.share);
    }
    function productList(row) {
      const products = row.snippets && Array.isArray(row.snippets.products) ? row.snippets.products : [];
      const fromCards = (row.business_cards || []).map((card) => card.title).filter(Boolean);
      if (industryKey(row) === 'holding') {
        const segmentNames = sortedSegments(row).map((segment) => segment.name).filter(Boolean);
        return Array.from(new Set(fromCards.concat(segmentNames))).filter(Boolean);
      }
      return Array.from(new Set(products.concat(fromCards))).filter(Boolean);
    }
    function shareText(segment) {
      if (!segment) return '';
      const pct = segment.share > 1 ? segment.share : segment.share * 100;
      if (!Number.isFinite(pct) || pct <= 0) return segment.name;
      return segment.name + ' ' + pct.toFixed(1).replace(/\\.0$/, '') + '%';
    }
    function reportFocusFor(row) {
      const key = industryKey(row);
      const category = categoryOf(row, '사업');
      const map = {
        bank: ['예대마진, 수수료, 충당금', '은행은 대출 성장보다 순이자마진, 연체율, 충당금, 자본비율이 이익의 질을 좌우합니다.'],
        insurance: ['손해율, 운용자산, 지급여력', '보험사는 보험영업 손해율과 투자자산 운용수익, 지급여력 비율을 같이 봐야 합니다.'],
        securities: ['위탁매매, IB, 운용손익', '증권사는 시장 거래대금, IB 딜 흐름, 자기자본 운용손익이 실적 변동을 크게 만듭니다.'],
        holding: ['포트폴리오, 배당, 지분가치', '지주사는 직접 매출보다 보유회사 가치, 지분법손익, 배당수입, 투자회수 가능성이 핵심입니다.'],
        semiconductor: ['제품 믹스, 가격, 가동률', '반도체는 HBM·서버DRAM처럼 고부가 제품 비중과 가격 사이클, 공장 가동률이 같이 움직입니다.'],
        battery: ['수주잔고, 고객사, 소재가격', '배터리는 고객사 물량, 증설 속도, 리튬·니켈 등 원재료 가격 전가력이 중요합니다.'],
        auto: ['판매량, 차종 믹스, 전동화', '자동차는 판매대수뿐 아니라 SUV·전기차·하이브리드 비중, 금융부문 건전성이 이익을 바꿉니다.'],
        shipbuilding: ['수주잔고, 선가, 선종 믹스', '조선은 수주잔고와 선가가 미래 매출을 만들고, LNG선·해양플랜트·특수선 같은 고부가 선종 비중과 원가 리스크가 이익률을 흔듭니다.'],
        shipping: ['운임, 선대, 물동량', '해운은 운임지수와 선대 운영, 장기계약 비중이 매출과 현금흐름을 좌우합니다.'],
        defense: ['수주, 납품, 수출계약', '방산은 장기 수주와 납품 일정, 해외계약 확대가 실적 가시성을 만듭니다.'],
        bio: ['생산능력, 품목, 고객계약', '바이오는 생산능력과 수주계약, 품목허가·임상 단계가 미래 매출의 핵심 단서입니다.'],
        power: ['수주, 전력망 투자, 설비', '전력기기는 전력망 투자와 수주잔고, 변압기·전선 등 제품 믹스가 중요합니다.'],
        materials: ['스프레드, 원재료, 재고', '소재 기업은 판매가격과 원재료 가격 차이, 재고평가, 고객 산업 수요를 같이 봐야 합니다.'],
        platform: ['트래픽, 광고, 커머스, AI', '플랫폼은 이용자 체류, 광고·커머스 전환, 콘텐츠·AI 투자 회수력이 관건입니다.'],
        telecom: ['가입자, ARPU, CAPEX', '통신은 가입자와 ARPU가 매출을 만들고, 설비투자와 주파수 비용이 현금흐름을 누릅니다.'],
        construction: ['수주잔고, 원가율, 미분양', '건설은 수주잔고와 공정률, 원가율, 미분양·PF 리스크를 함께 읽어야 합니다.'],
        consumer: ['브랜드, 가격, 해외판매', '소비재는 브랜드 가격결정력, 판매량, 해외법인 성장, 원재료·광고비 부담을 봅니다.'],
      };
      return map[key] || ['매출동력, 비용구조, 투자부담', category + ' 기업은 무엇을 팔아 매출을 만들고 어떤 비용과 투자가 이익을 흔드는지 먼저 보면 됩니다.'];
    }
    function firstEvidence(row, keys, fallback) {
      const snippets = row.snippets || {};
      for (const key of keys) {
        const value = snippets[key];
        if (!value) continue;
        const candidate = compactSentence(value, 280);
        if (/주\d\)|산출대상|산출단위|단위\s*:|단위 :|연결 및 누계 기준|내부거래를 소거|해당사항 없음/.test(candidate)) continue;
        return candidate;
      }
      return fallback || '';
    }
    function cardFact(text) {
      const cleanTail = (out) => String(out || '')
        .replace(/\s*(연구개발비용|연구개발실적|생산실적|가동률)\s*[가-힣]\.?$/g, '')
        .replace(/\s*(생산실적\s*가동률|생산실적|가동률)$/g, '')
        .replace(/\s+[가-힣]\.$/, '')
        .replace(/[,\s]+$/g, '')
        .trim();
      let value = String(text || '').replace(/\s+/g, ' ').trim();
      value = value
        .replace(/^(\d+[.)]\s*)+/, '')
        .replace(/^[가-힣]\.\s*/, '')
        .replace(/(?:가|나|다|라)\.\s*(경영상의 주요 계약 등|연구개발활동의 개요 및 연구개발비용|생산실적 및 가동률)\s*/g, '')
        .replace(/\s+\d+\.\s+/g, ' ')
        .replace(/^(사업의 개요|주요계약 및 연구개발활동|연구개발활동|생산능력, 생산실적, 가동률)\s*/g, '')
        .replace(/\s*\(\d+\)\s*/g, ' ')
        .replace(/연구개발 담당조직/g, '연구개발 담당 조직: ')
        .replace(/\s*(연구개발비용|연구개발실적|생산실적|가동률)\s+[가-힣]\.$/, '')
        .replace(/\s+[가-힣]\.$/, '')
        .trim();
      const finishFact = (out) => completeKoreanSentence(cleanTail(out));
      if (value.length <= 220) return finishFact(value);
      const cut = value.slice(0, 220).trim();
      const ends = ['습니다.', '입니다.', '합니다.', '됩니다.', '다.'];
      let best = -1;
      for (const end of ends) {
        const idx = cut.lastIndexOf(end);
        if (idx >= 70) best = Math.max(best, idx + end.length);
      }
      if (best > 0) return finishFact(cut.slice(0, best));
      let next = -1;
      for (const end of ends) {
        const idx = value.indexOf(end, 220);
        if (idx > 0 && idx < 380) next = next < 0 ? idx + end.length : Math.min(next, idx + end.length);
      }
      if (next > 0) return finishFact(value.slice(0, next));
      const comma = Math.max(cut.lastIndexOf(','), cut.lastIndexOf('며'), cut.lastIndexOf('고'), cut.lastIndexOf('하고'));
      if (comma >= 115) return finishFact(cut.slice(0, comma));
      const space = cut.lastIndexOf(' ');
      if (space >= 130) return finishFact(cut.slice(0, space));
      return finishFact(cut);
    }
    function segmentNames(row, limit) {
      return sortedSegments(row).slice(0, limit || 4).map((segment) => segment.name).join(' · ');
    }
    function industryInsightTemplate(row) {
      const key = industryKey(row);
      const products = productList(row).slice(0, 4).join(' · ');
      const allProducts = productList(row);
      const semiconductorProducts = allProducts
        .filter((name) => /HBM|DRAM|NAND|SSD|UFS|eMMC|반도체|메모리|모바일AP|이미지센서|CIS|Foundry|OLED|패키징|장비/i.test(name))
        .slice(0, 5)
        .join(' · ');
      const segments = segmentNames(row, 4);
      const note = firstEvidence(row, ['investor_note', 'overview'], '사업보고서의 사업개요와 사업현황 문단을 기준으로 투자자가 먼저 볼 포인트를 정리했습니다.');
      const capex = firstEvidence(row, ['capacity', 'raw_material', 'rd'], note);
      const finance = firstEvidence(row, ['segment_finance', 'investor_note', 'overview'], note);
      const templates = {
        bank: [
          ['순이자마진·충당금', '은행 이익의 출발점은 대출마진과 부실 관리입니다.', finance, '금리가 바뀌어도 이익이 유지되는지 보려면 순이자마진, 연체율, 충당금을 같이 봐야 합니다.'],
          ['비은행 이익 기여', '증권·카드·보험 자회사가 그룹 실적을 보완합니다.', segments || products, '비은행 이익이 커질수록 은행 금리 사이클에 덜 흔들릴 수 있습니다.'],
          ['자본정책', '배당과 자사주, 자본비율은 금융지주 투자자의 핵심 체크포인트입니다.', note, '자본여력이 있어야 배당을 늘리거나 자사주를 소각할 수 있습니다.'],
        ],
        insurance: [
          ['손해율과 신계약', '보험영업은 얼마나 잘 받고 덜 지급하는지가 핵심입니다.', finance, '손해율과 신계약 흐름을 보면 보험 본업의 체력이 보입니다.'],
          ['운용자산 수익률', '보험료로 쌓인 자산 운용이 투자손익을 만듭니다.', note, '금리와 시장가격 변화가 보험사 이익에 크게 반영될 수 있습니다.'],
          ['지급여력·배당', '지급여력은 배당 지속성과 규제 대응력을 보여줍니다.', note, '보험사는 재무건전성이 흔들리면 주주환원보다 자본 보강이 우선됩니다.'],
        ],
        securities: [
          ['브로커리지·IB', '거래대금과 기업금융 딜 흐름이 수수료 수익을 좌우합니다.', finance, '시장이 활발할 때 어떤 수익원이 커지는지 보면 증권사 체질을 알 수 있습니다.'],
          ['운용손익', '채권·주식 운용손익은 시장 변동에 민감합니다.', note, '증권사는 본업 수수료와 운용손익을 나눠 봐야 실적의 지속성을 판단할 수 있습니다.'],
          ['자본 활용도', '자기자본을 어떻게 굴리는지가 ROE와 배당여력을 만듭니다.', note, '자본이 큰 증권사는 IB, 트레이딩, 대체투자 성과가 실적 차이를 만듭니다.'],
        ],
        holding: [
          ['포트폴리오 구성', '지주사는 어떤 자회사와 사업축을 들고 있는지가 회사가치의 출발점입니다.', segments || products, '직접 제품보다 자회사 가치, 지분법손익, 투자자산 변동이 더 중요할 수 있습니다.'],
          ['배당·투자회수', '자회사 배당과 지분 매각이 지주사의 현금흐름을 만듭니다.', note, '보유회사의 실적이 좋아도 현금이 모회사로 올라오지 않으면 주주환원은 제한됩니다.'],
          ['할인 요인', '복잡한 지배구조와 상장 자회사 중복 보유는 할인 요인입니다.', finance, '순자산가치 대비 주가가 낮게 거래되는 이유를 사업보고서 구조에서 찾을 수 있습니다.'],
        ],
        semiconductor: String(row.stock_code || '') === '005930' ? [
          ['완제품·부품 포트폴리오', '스마트폰·TV 같은 완제품과 반도체·디스플레이 부품을 함께 보유합니다.', products || segments || note, '삼성전자는 한 업황만 보는 회사가 아니라 완제품 수요와 부품 사이클을 같이 봐야 합니다.'],
          ['부문별 경기 사이클', 'DX는 소비경기, DS는 반도체 가격, SDC는 패널 수요에 민감합니다.', finance, '삼성전자는 부문별 업황이 서로 달라 한쪽이 부진해도 다른 부문이 실적을 완충할 수 있습니다.'],
          ['R&D와 기술 축', '연구개발은 스마트폰·TV·반도체·디스플레이 경쟁력을 동시에 떠받칩니다.', firstEvidence(row, ['rd', 'capacity'], capex), 'R&D는 당장 비용이지만 제품 차별화와 공정 경쟁력의 기반입니다.'],
        ] : [
          ['반도체 제품 믹스', '어떤 반도체 제품군이 매출을 만드는지 먼저 봅니다.', semiconductorProducts || products || note, 'HBM, DRAM, 장비, 패키징 등 제품 구성이 이익률과 업황 민감도를 바꿉니다.'],
          ['생산능력·가동률', '반도체는 생산능력과 가동률이 가격 사이클과 같이 움직입니다.', capex, '공장이 얼마나 차는지와 재고가 얼마나 쌓이는지가 다음 실적의 단서가 됩니다.'],
          ['설비투자·연구개발', '설비와 기술 투자는 미래 매출의 씨앗이지만 비용 부담도 만듭니다.', firstEvidence(row, ['rd', 'capacity'], capex), '투자가 매출 성장으로 이어지는지, 감가상각 부담만 커지는지 구분해야 합니다.'],
        ],
        battery: [
          ['수주잔고와 고객사', '장기 공급계약과 고객사 물량이 매출 가시성을 만듭니다.', note, '배터리는 공장을 지어도 고객 물량이 따라와야 가동률과 이익이 안정됩니다.'],
          ['원재료 가격 전가', '리튬·니켈·전구체 가격을 판가에 반영할 수 있는지가 마진을 좌우합니다.', firstEvidence(row, ['raw_material', 'investor_note'], note), '소재 가격이 흔들릴 때 판가 전가력이 약하면 매출은 늘어도 이익률이 눌립니다.'],
          ['증설 속도', '공장 증설은 성장 신호이지만 초기 가동률과 감가상각 부담도 만듭니다.', capex, '증설이 실제 매출로 이어지는 시점과 비용 부담을 같이 봐야 합니다.'],
        ],
        auto: [
          ['차종·제품 라인업', '어떤 차종과 부품군을 파는지가 평균판매가격과 이익률을 바꿉니다.', products || note, 'SUV, 전기차, 고급차, 핵심부품 비중이 올라가면 같은 판매량에서도 이익이 달라집니다.'],
          ['전동화 전환', '전기차·하이브리드·배터리 내재화는 경쟁력과 투자부담을 함께 만듭니다.', note, '전동화는 성장 기회지만 개발비와 설비투자도 같이 늘어납니다.'],
          ['금융부문 리스크', '할부·리스 금융은 수익원이지만 금리와 연체율에 민감합니다.', finance, '차량 판매 뒤에도 금융자산 건전성이 그룹 실적에 영향을 줄 수 있습니다.'],
        ],
        shipbuilding: [
          ['수주잔고와 선가', '조선사는 올해 매출보다 수주잔고와 선가가 미래 이익을 먼저 말해줍니다.', finance, '비싼 선박을 많이 수주했는지가 몇 년 뒤 매출과 이익률의 출발점입니다.'],
          ['고부가 선박', 'LNG선·해양플랜트·특수선 비중은 수익성 개선 여지를 보여줍니다.', products || segments, '선박 종류가 달라지면 같은 건조량이어도 마진이 크게 달라집니다.'],
          ['원가·납기 리스크', '후판가, 기자재, 납기 지연은 수주가 좋아도 이익률을 깎을 수 있습니다.', firstEvidence(row, ['raw_material', 'investor_note'], capex), '사업보고서에서 원재료 가격, 납기, 손실충당금 언급이 있으면 실제 부담 신호로 읽습니다.'],
        ],
        shipping: [
          ['운임 민감도', '운임지수와 장기계약 비중이 매출 변동성을 좌우합니다.', note, '운임이 오르면 실적이 빠르게 좋아지지만 하락기에는 이익이 급격히 줄 수 있습니다.'],
          ['선대 운영', '선박 보유·용선 구조는 비용과 현금흐름을 동시에 바꿉니다.', capex, '비싼 용선료를 부담하는지, 자체 선대를 활용하는지가 수익성 차이를 만듭니다.'],
          ['물동량과 노선', '글로벌 교역량과 주요 노선 수요가 실적의 출발점입니다.', products || segments, '어떤 화물과 노선에 강한지 보면 업황 민감도를 더 잘 이해할 수 있습니다.'],
        ],
        defense: [
          ['수주형 사업', '방산 매출은 계약한 장비를 개발·생산·납품하는 과정에서 만들어집니다.', finance, '사업보고서의 수주·납품 문단은 이미 계약된 일감과 실제 매출로 이어지는 사업 흐름을 설명합니다.'],
          ['사업부문 구성', '유도무기·감시정찰·항공전자처럼 성격이 다른 제품군이 함께 실적을 만듭니다.', segments || products || note, '사업보고서는 어느 제품군이 회사의 주력 사업인지, 각 부문이 어떤 역할을 맡는지 보여줍니다.'],
          ['연구개발 활동', '방산 회사는 개발 조직, 개발비, 시험·인증 활동을 통해 다음 제품군을 준비합니다.', firstEvidence(row, ['rd', 'capacity'], note), '연구개발 문단은 회사가 어떤 기술을 개발하고 있고 그 과정에 비용을 얼마나 쓰는지 요약한 부분입니다.'],
        ],
        bio: [
          ['생산능력과 수주', 'CDMO와 의약품은 생산능력, 고객계약, 품목허가가 매출 가시성을 만듭니다.', capex, '공장 규모가 커도 수주와 허가가 따라와야 실적이 안정됩니다.'],
          ['파이프라인 단계', '임상·허가·상업화 단계에 따라 기대 매출과 리스크가 달라집니다.', firstEvidence(row, ['rd', 'investor_note'], note), '초기 파이프라인과 상업화 제품은 위험과 가치평가 방식이 다릅니다.'],
          ['고객 집중도', '대형 고객 의존도가 높으면 성장성과 계약 변동 리스크가 같이 커집니다.', finance, '한 고객의 물량 변화가 전체 실적을 흔들 수 있는지 확인해야 합니다.'],
        ],
        power: [
          ['전력망 투자 수혜', '변압기·전선·전력기기는 전력망 증설과 노후 교체 투자의 영향을 받습니다.', products || note, 'AI 데이터센터와 전력망 투자가 늘면 수요가 장기간 이어질 수 있습니다.'],
          ['수주잔고', '장기 프로젝트 수주잔고는 향후 매출의 가시성을 보여줍니다.', finance, '납기가 긴 제품은 현재 수주가 미래 매출을 미리 보여줍니다.'],
          ['원재료와 납기', '구리·철강 가격과 납기 관리가 수익률을 흔들 수 있습니다.', firstEvidence(row, ['raw_material', 'capacity'], note), '원가와 납기 지연은 수주가 좋아도 마진을 낮출 수 있습니다.'],
        ],
        materials: [
          ['스프레드', '판매가격과 원재료 가격 차이가 소재 기업의 핵심 이익률입니다.', firstEvidence(row, ['raw_material', 'investor_note'], note), '원재료가 올라도 판가를 올리지 못하면 매출보다 이익이 먼저 눌립니다.'],
          ['재고평가', '원재료 가격이 빠르게 움직이면 재고평가손익이 실적을 흔들 수 있습니다.', finance, '가격 하락기에는 보유 재고가 손실로 바뀔 수 있습니다.'],
          ['전방산업 수요', '철강·화학·배터리·자동차 같은 고객 산업 수요가 매출을 끌고 갑니다.', products || segments, '소재 기업은 자기 제품보다 고객 산업의 업황이 먼저 움직이는 경우가 많습니다.'],
        ],
        platform: [
          ['이용자와 체류시간', '플랫폼은 이용자 규모와 체류시간이 광고·커머스 매출의 출발점입니다.', note, '사용자가 오래 머물수록 광고, 결제, 콘텐츠 판매 기회가 커집니다.'],
          ['수익화 방식', '광고, 수수료, 구독, 콘텐츠 판매 중 어디서 돈을 버는지 분리해서 봅니다.', products || segments, '같은 플랫폼이라도 수익화 방식에 따라 성장률과 이익률이 다릅니다.'],
          ['AI·콘텐츠 투자', '신사업 투자는 성장 옵션이지만 비용 증가와 회수기간을 함께 만듭니다.', firstEvidence(row, ['rd', 'investor_note'], note), 'AI와 콘텐츠 투자가 실제 매출로 바뀌는지 확인해야 합니다.'],
        ],
        telecom: [
          ['ARPU와 가입자', '통신사는 가입자 수보다 가입자당 매출과 요금제 믹스가 이익을 좌우합니다.', note, '성숙 산업에서는 가입자 증가보다 고가 요금제와 해지율 관리가 더 중요합니다.'],
          ['CAPEX 부담', '망 투자와 주파수 비용은 현금흐름을 누르는 핵심 비용입니다.', capex, '통신사는 돈을 잘 벌어도 네트워크 투자가 크면 현금이 덜 남을 수 있습니다.'],
          ['AI·데이터센터', '통신 본업 외 AI, 클라우드, IDC가 성장 축으로 붙는지 확인합니다.', products || segments, '통신 본업의 저성장을 보완할 새 매출원이 되는지 봐야 합니다.'],
        ],
        construction: [
          ['수주잔고', '신규수주와 수주잔고가 미래 매출의 출발점입니다.', finance, '건설사는 오늘의 수주가 몇 년 뒤 매출로 인식됩니다.'],
          ['원가율과 공정률', '공사비 상승과 공정 지연은 매출보다 이익을 먼저 흔듭니다.', capex, '매출이 커도 원가율이 나빠지면 이익은 줄어들 수 있습니다.'],
          ['PF·미분양', '부동산 경기와 자금조달 리스크가 재무 안정성에 영향을 줍니다.', note, '분양과 PF 리스크는 현금흐름과 대손 부담으로 연결될 수 있습니다.'],
        ],
        consumer: [
          ['브랜드 가격결정력', '가격을 올려도 수요가 유지되는 브랜드인지 봐야 합니다.', products || note, '소비재는 브랜드 힘이 약하면 원가 상승을 소비자가격에 반영하기 어렵습니다.'],
          ['원재료·광고비', '원재료와 마케팅비 부담은 매출 성장에도 이익률을 누를 수 있습니다.', firstEvidence(row, ['raw_material', 'investor_note'], note), '판매량이 늘어도 비용이 더 빨리 늘면 영업이익률이 나빠질 수 있습니다.'],
          ['해외 성장', '해외법인과 신규 채널이 내수 정체를 보완하는지 확인합니다.', finance, '국내 수요가 정체된 기업은 해외 매출이 장기 성장의 핵심이 될 수 있습니다.'],
        ],
      };
      return templates[key] || [
        ['매출을 움직이는 요인', '무엇을 팔아 매출을 만들고 어떤 고객군에 의존하는지 먼저 봅니다.', products || segments || note, '사업의 출발점을 알아야 재무제표 숫자가 왜 움직였는지 이해할 수 있습니다.'],
        ['이익률을 흔드는 비용', '원재료, 인건비, 설비투자, 연구개발비 중 어디가 부담인지 확인합니다.', capex, '매출이 늘어도 비용 구조가 나쁘면 이익은 좋아지지 않습니다.'],
        ['재무제표 연결 지점', '사업보고서 문단이 매출, 영업이익, 현금흐름으로 이어지는지 봅니다.', finance, '좋은 사업 설명은 결국 숫자로 확인되어야 합니다.'],
      ];
    }
    function dynamicReportIdeas(row) {
      const overview = compactSentence(row.snippets && row.snippets.overview || '', 260);
      const investorNote = compactSentence(row.snippets && row.snippets.investor_note || '', 260);
      const focus = reportFocusFor(row);
      const templates = industryInsightTemplate(row);
      const hasStructuredData = overview || investorNote || sortedSegments(row).length || productList(row).length;
      if (!hasStructuredData) {
        return [
          {
            title: '수집 필요',
            value: categoryOf(row, '사업보고서'),
            fact: '이 회사는 로컬에 구조화된 사업보고서 요약이 충분히 저장되어 있지 않습니다.',
            view: 'DART 사업보고서를 다시 수집하면 사업개요와 사업현황을 직접 요약한 카드로 채울 수 있습니다.'
          },
          {
            title: '업종 기준 후보',
            value: focus[0],
            fact: '현재 화면은 업종 분류와 행성 주변 사업 카드만으로 임시 후보를 만들었습니다.',
            view: focus[1]
          }
        ];
      }
      return templates.slice(0, 3).map((item) => ({
        title: item[0],
        value: item[1],
        fact: cardFact(item[2] || investorNote || overview || '사업보고서의 사업개요와 사업현황 문단을 읽고 요약한 내용입니다.'),
        view: item[3] || focus[1],
      }));
    }
    function businessSourceListV2(row) {
      const snippets = row.snippets || {};
      const segments = sortedSegments(row);
      const products = productList(row);
      const segmentText = segments.length
        ? segments.slice(0, 5).map((segment) => shareText(segment) + (segment.desc ? ': ' + segment.desc : '')).join(' / ')
        : '';
      const productText = products.length ? products.slice(0, 8).join(' · ') : '';
      const items = [
        ['사업개요', snippets.overview],
        ['사업부문 요약', segmentText || snippets.segment_finance],
        ['주요 제품·서비스', productText],
        ['초보 투자자 요약', snippets.investor_note],
      ].map((item) => [item[0], compactSentence(item[1] || '', 170)]).filter((item) => item[1]);
      if (!items.length) {
        const focus = reportFocusFor(row);
        return '<p class="source-sentence">' + rich('이 회사는 로컬 사업보고서 요약이 충분하지 않아 업종 기준 후보만 표시했습니다. 다시 수집하면 DART II. 사업의 내용에서 회사별 문단을 연결할 수 있습니다. 현재 후보: ' + focus[0]) + '</p>';
      }
      return '<ol class="money-flow">' + items.map((item) => '<li><strong>' + esc(item[0]) + '</strong><br>' + rich(item[1]) + '</li>').join('') + '</ol>';
    }
    function showFactoryEvidence(row) {
      return !['bank','insurance','securities','holding','platform','telecom','shipping','consumer'].includes(industryKey(row));
    }
    function customReportIdeas(row) {
      const data = {
        '005930': [
          { title:'2025 변화', value:'DS 부문 영업이익 24.9조원', fact:'DS 부문은 2023년에 영업손실을 냈지만 2024년에 흑자 전환했고, 2025년에는 영업이익이 약 24.9조원까지 회복되었습니다.', view:'삼성전자는 전체 매출보다 반도체 업황 회복이 이익에 얼마나 반영되는지가 중요한 회사입니다.' },
          { title:'원가와 가동률', value:'Wafer -10% · Cover Glass +12% · 메모리 가동률 100%', fact:'사업보고서에는 모바일AP +4%, TV·모니터 패널 -3%, 반도체 Wafer -10%, FPCA +6%, Cover Glass +12%, DS 메모리와 SDC 가동률 100%가 표시됩니다.', view:'같은 삼성전자 안에서도 원가 부담과 공장 가동 상황이 부문별로 다르므로 부문별 이익률을 나눠 읽어야 합니다.' },
          { title:'투자자 확인 포인트', value:'DS 회복 · DX 수익성 · 원가 전가 · 가동률', fact:'사업보고서의 부문별 매출, 원재료 가격 변동, 생산능력·가동률 표를 함께 보면 다음 실적에서 확인할 질문이 정리됩니다.', view:'삼성전자는 매출 규모만 보는 회사가 아니라 DS 반도체 회복 속도와 DX 완제품 수익성, 부문별 원가·가동률 변화를 함께 봐야 합니다.' },
        ],
        '000660': [
          { title:'사업 구조', value:'반도체 부문 100%', fact:'사업보고서 요약 기준 SK하이닉스는 DRAM, NAND Flash 등 메모리 반도체 제조·판매를 단일 반도체 부문으로 표시합니다.', view:'사업이 메모리에 집중되어 있어 업황 회복기에는 탄력이 크지만 가격 하락기에는 이익 변동도 커질 수 있습니다.' },
          { title:'AI 메모리 축', value:'HBM · DDR5 · LPDDR5X', fact:'주요 제품 목록에 DRAM, HBM, DDR5, LPDDR5X, GDDR7 등이 포함되어 있습니다.', view:'AI 서버와 고성능 연산 수요가 메모리 제품 믹스를 얼마나 좋게 바꾸는지가 핵심입니다.' },
          { title:'저장장치 축', value:'NAND · SSD · UFS', fact:'사업보고서 요약 제품에는 NAND Flash, SSD, UFS, eMMC 등 저장장치 제품군이 함께 잡혀 있습니다.', view:'DRAM과 NAND의 가격 사이클이 다를 수 있으므로 제품별 회복 속도를 분리해서 봐야 합니다.' },
        ],
        '402340': [
          { title:'사업 구조', value:'투자 · 커머스 · 플랫폼 · 모빌리티', fact:'사업보고서 요약 기준 SK스퀘어는 투자사업, 커머스사업, 플랫폼사업, 모빌리티사업, 기타사업으로 구분됩니다.', view:'SK스퀘어는 직접 제조보다 포트폴리오 가치와 플랫폼 사업의 성장성을 함께 보는 편이 자연스럽습니다.' },
          { title:'매출 축', value:'모빌리티 39.2% · 커머스 31.0%', fact:'요약 데이터 기준 모빌리티사업 39.2%, 커머스사업 31.0%, 플랫폼사업 25.5%가 주요 매출 축입니다.', view:'투자자에게는 어떤 플랫폼 사업이 실제 매출을 만들고 있는지 구분해 보여주는 것이 좋습니다.' },
          { title:'투자 포트폴리오', value:'SK하이닉스 · 11번가 · TMAP · 원스토어', fact:'사업보고서 요약에는 SK하이닉스 투자와 11번가, TMAP, 원스토어, OK캐쉬백, Syrup, 기프티콘 등이 함께 나타납니다.', view:'SK하이닉스는 제조사업이 아니라 투자 포트폴리오로 읽고, 플랫폼 자회사와 구분해서 보여줘야 합니다.' },
        ],
        '005380': [
          { title:'사업 구조', value:'차량 78.2% · 금융 16.2%', fact:'현대차는 차량부문, 금융부문, 기타부문으로 구분되고 차량부문이 매출의 대부분을 차지합니다.', view:'자동차 판매량과 차종 믹스가 중심이고, 금융부문은 할부·리스 수익으로 실적을 보완합니다.' },
          { title:'친환경 라인업', value:'전기차 · 하이브리드 · 수소전기차', fact:'사업보고서 요약 제품에는 전기차, 하이브리드차, 수소전기차가 포함되어 있습니다.', view:'친환경차 비중은 판매 단가와 브랜드 경쟁력, 규제 대응력을 함께 보여주는 신호입니다.' },
          { title:'금융 연결', value:'할부금융 · 리스 · 신용카드', fact:'금융부문은 자동차할부금융, 리스, 신용카드 등 금융서비스를 제공하는 부문으로 분류됩니다.', view:'금리와 중고차 가격, 연체율이 자동차 판매 이후의 수익성에도 영향을 줄 수 있습니다.' },
        ],
        '012450': [
          { title:'사업 포트폴리오', value:'항공 · 방산 · 해양 · 우주', fact:'사업보고서 요약 기준 한화에어로스페이스는 항공, 방산, 해양, IT서비스, 항공우주 부문으로 나뉩니다.', view:'이 회사는 항공엔진만 보는 회사가 아니라 방산과 해양 사업까지 함께 실적을 만드는 구조로 읽어야 합니다.' },
          { title:'수주가 매출로 바뀌는 시간', value:'계약 · 납품 · 일정', fact:'사업보고서의 사업 내용에는 자주포, 장갑차, 탄약, 항공기 엔진과 부품, LNG운반선과 해양플랜트 등 장기 프로젝트형 제품이 함께 나타납니다.', view:'계약이 체결돼도 매출은 납품 일정에 따라 나뉘어 잡히므로, 수주 뉴스와 실제 매출 반영 시점을 분리해서 봐야 합니다.' },
          { title:'연구개발은 양산 확정이 아님', value:'개발비 · 인증 · 품질', fact:'사업보고서의 연구개발 문단은 연구개발 조직과 비용, 항공엔진·가스터빈 관련 개발 활동을 보여줍니다.', view:'이 문단만으로 특정 무기체계가 양산 중이라고 단정하지 않고, 제품 준비와 비용 부담을 보여주는 신호로 읽어야 합니다.' },
        ],
        '105560': [
          { title:'사업 구조', value:'은행 66.0% 중심', fact:'KB금융은 은행, 증권, 손해보험, 신용카드, 생명보험 부문으로 구분되며 은행부문 비중이 가장 큽니다.', view:'순이자마진과 대출 성장, 충당금이 그룹 이익의 가장 큰 축입니다.' },
          { title:'비은행 축', value:'손보 · 증권 · 카드', fact:'사업보고서 요약에는 KB증권, KB손해보험, KB국민카드, KB라이프생명 등 주요 금융 자회사가 나타납니다.', view:'비은행 이익이 커질수록 은행 금리 사이클 의존도가 낮아질 수 있습니다.' },
          { title:'고객 접점', value:'KB스타뱅킹', fact:'요약 제품·서비스 목록에 KB스타뱅킹, 예금, 대출, 카드, 보험, 증권 서비스가 포함되어 있습니다.', view:'금융사는 제품보다 고객 접점과 교차판매가 장기 경쟁력으로 이어집니다.' },
        ],
        '010140': [
          { title:'사업 집중도', value:'선박 · 해양플랜트 중심', fact:'삼성중공업은 LNG선, 초대형컨테이너선, 원유운반선, LNG-FPSO, FPU 등 대형 선박과 해양플랜트를 주요 제품으로 공시합니다.', view:'주린이 관점에서는 여러 사업을 넓게 하는 회사라기보다 고부가 선박과 해양 프로젝트에 집중된 조선사로 읽는 편이 쉽습니다.' },
          { title:'고부가 선종', value:'LNG선 · 초대형컨테이너선 · VLCC', fact:'사업보고서 요약 제품에는 LNG선, 초대형컨테이너선, 원유운반선(VLCC), LNG-FPSO, FPU가 포함되어 있습니다.', view:'선가가 높은 선종이 많을수록 매출 규모와 이익률 개선 여지가 커집니다. 다만 현재 파싱 데이터에는 선종별 수주잔고 비중이 별도 수치로 구조화되어 있지는 않습니다.' },
          { title:'원가와 납기', value:'후판 · 기자재 · 프로젝트 관리', fact:'현재 요약 데이터에서는 원재료 가격이나 납기 지연 수치가 별도로 구조화되어 있지 않지만, 조선사는 후판과 기자재 가격이 매출원가에 직접 영향을 줍니다.', view:'실제로 지연이나 원가 초과가 생기면 사업보고서의 손실충당금, 원가율, 미청구공사 관련 문단에서 부담 신호가 나타날 수 있습니다.' },
        ],
        '329180': [
          { title:'사업 구조', value:'조선 70.9% · 엔진 21.6%', fact:'HD현대중공업은 조선, 해양플랜트, 엔진기계 부문으로 구분되고 조선부문 비중이 가장 큽니다.', view:'선박 수주와 선가가 중심이고, 엔진 부문은 선박 수요와 함께 움직이는 후방 사업으로 읽으면 됩니다.' },
          { title:'주요 제품', value:'LNG선 · 컨테이너선 · 원유운반선', fact:'사업보고서 요약 제품에는 LNG선, 컨테이너선, 원유운반선, LPG선, 군함 등이 포함됩니다.', view:'고부가 선박 비중이 높을수록 수익성 개선 여지가 커집니다.' },
          { title:'엔진 경쟁력', value:'HiMSEN 엔진', fact:'엔진기계 부문은 선박용 엔진, HiMSEN 엔진, 디젤발전설비 등을 제조한다고 요약되어 있습니다.', view:'엔진은 조선 수주와 함께 움직이는 후방 사업이면서 친환경 선박 전환의 수혜를 받을 수 있습니다.' },
        ],
        '042660': [
          { title:'사업 구조', value:'상선 · 해양 · 특수선', fact:'한화오션은 LNG 운반선, 원유 운반선, 컨테이너선, LPG 운반선과 FPSO, RIG, Drillship, 잠수함, 구축함, 구난함, 경비함 등을 건조하는 종합 조선·해양 회사로 공시합니다.', view:'상선 경기만 보는 회사가 아니라 해양 프로젝트와 방산 특수선까지 함께 봐야 합니다.' },
          { title:'사업 확장', value:'플랜트 · 해상풍력 편입', fact:'사업보고서에는 2024년 한화로부터 플랜트 사업과 풍력 사업을 양수했다는 내용이 포함되어 있습니다.', view:'기존 조선 수주 외에 플랜트와 해상풍력이 추가 성장축이 될 수 있지만, 새 사업은 수익성 검증이 함께 필요합니다.' },
          { title:'현금화 포인트', value:'계약자산 · 미청구수익', fact:'요약 데이터에는 진행 중인 선박 건조와 관련한 미청구수익이 향후 현금화될 예정이라는 설명이 포함되어 있습니다.', view:'조선사는 수주가 바로 현금이 되는 구조가 아니므로, 매출 증가와 실제 현금 회수가 같이 따라오는지 보는 것이 중요합니다.' },
        ],
      };
      return CUSTOM_REPORT_IDEAS[String(row.stock_code || '')] || data[String(row.stock_code || '')] || dynamicReportIdeas(row);
    }
    function reportSummaryTone(text) {
      return String(text || '')
        .replace(/보려면 ([^.]+?)을 같이 봐야 합니다\./g, '$1이 함께 실적에 영향을 줍니다.')
        .replace(/보려면 ([^.]+?)를 같이 봐야 합니다\./g, '$1가 함께 실적에 영향을 줍니다.')
        .replace(/같이 봐야 합니다\./g, '함께 실적에 반영됩니다.')
        .replace(/함께 봐야 합니다\./g, '함께 실적에 반영됩니다.')
        .replace(/같이 봐야 합니다/g, '함께 실적에 반영됩니다')
        .replace(/함께 봐야 합니다/g, '함께 실적에 반영됩니다')
        .replace(/분리해서 봐야 합니다\./g, '제품별 흐름이 따로 움직일 수 있다는 뜻입니다.')
        .replace(/분리해서 봐야 합니다/g, '제품별 흐름이 따로 움직일 수 있다는 뜻입니다')
        .replace(/확인해야 합니다\./g, '사업보고서에서 관련 흐름을 설명합니다.')
        .replace(/확인해야 합니다/g, '사업보고서에서 관련 흐름을 설명합니다')
        .replace(/읽어야 합니다\./g, '함께 실적을 만드는 구조입니다.')
        .replace(/읽어야 합니다/g, '함께 실적을 만드는 구조입니다')
        .replace(/보는 것이 중요합니다\./g, '함께 움직이는 사업 구조입니다.')
        .replace(/먼저 봅니다\./g, '먼저 요약됩니다.')
        .replace(/어디서 ([^.]+?)이 오는지 봅니다\./g, '$1이 어디서 오는지 보여줍니다.')
        .replace(/어디서 ([^.]+?)가 오는지 봅니다\./g, '$1가 어디서 오는지 보여줍니다.')
        .replace(/([가-힣A-Za-z0-9·\-\s]+)을 봅니다\./g, '$1을 보여줍니다.')
        .replace(/([가-힣A-Za-z0-9·\-\s]+)를 봅니다\./g, '$1를 보여줍니다.')
        .replace(/([가-힣A-Za-z0-9·\-\s]+)인지 봅니다\./g, '$1인지 설명합니다.')
        .replace(/확인합니다\./g, '설명합니다.')
        .replace(/보여주는 신호입니다\./g, '보여주는 내용입니다.')
        .replace(/단서입니다\./g, '내용입니다.')
        .replace(/핵심 체크포인트입니다\./g, '핵심 내용입니다.')
        .replace(/체크포인트/g, '요약 포인트')
        .replace(/신호입니다\./g, '내용입니다.')
        .replace(/입니다\.입니다\./g, '입니다.')
        .replace(/습니다\.입니다\./g, '습니다.')
        .replace(/니다\.입니다\./g, '니다.');
    }
    function customReportIdeasHtml(row) {
      const ideas = customReportIdeas(row);
      if (!ideas.length) return '';
      const summaryItems = ideas.map((idea) =>
        '<li class="report-reading-item"><h4>' + esc(idea.title) + '</h4><p><b>' + rich(reportSummaryTone(idea.value)) + '</b><br>' + rich(reportSummaryTone(idea.fact)) + '</p></li>'
      ).join('');
      const investorItems = ideas.map((idea) =>
        '<li class="report-reading-item"><h4>' + esc(idea.title) + '</h4><p>' + rich(reportSummaryTone(idea.view)) + '</p></li>'
      ).join('');
      return '<div class="custom-report-cards">' +
        '<div class="detail-head"><div><h3>우리가 읽고 요약한 사업보고서 핵심</h3><p>위에서 사업 구조와 제품을 봤으므로, 여기서는 사업보고서가 말하는 변화와 그 의미를 문단으로 풀어썼습니다.</p></div><div class="mini-label">회사별 직접 요약</div></div>' +
        '<div class="custom-report-grid">' +
          '<article class="custom-report-card"><strong>1. 사업보고서에서 확인된 변화</strong><p class="report-reading-intro">사업보고서의 수치와 서술을 바탕으로, 이 회사의 사업 환경이 최근 어떻게 움직였는지 정리했습니다.</p><ul class="report-reading-list">' + summaryItems + '</ul></article>' +
          '<article class="custom-report-card"><strong>2. 투자자가 확인해야 할 포인트</strong><p class="report-reading-intro">위 변화가 다음 실적에서 어떤 질문으로 이어지는지, 사업별 특성에 맞춰 풀어 설명합니다.</p><ul class="report-reading-list">' + investorItems + '</ul></article>' +
        '</div>' +
      '</div>';
    }
    function reportDetailData(row) {
      if (String(row.stock_code || '') !== '005930') return {};
      return {
        utilization: [
          { segment:'DX', item:'TV·모니터', rate:78.8, capacity:56283, actual:44361, unit:'천대' },
          { segment:'DX', item:'스마트폰', rate:79.3, capacity:270050, actual:214259, unit:'천대' },
          { segment:'DS', item:'메모리', rate:100, capacity:87600, actual:87600, unit:'시간' },
          { segment:'SDC', item:'디스플레이 패널', rate:100, capacity:43800, actual:43800, unit:'시간' },
          { segment:'Harman', item:'디지털 콕핏', rate:75.4, capacity:7815, actual:5897, unit:'천개' },
        ],
        segmentFinance: [
          { name:'DX 부문', revenue:[1699923,1748877,1879673], operating:[143847,124399,128527], assets:[2342534,2596713,2810397] },
          { name:'DS 부문', revenue:[665945,1110660,1301282], operating:[-148795,150945,248581], assets:[2871411,3430454,3719620] },
          { name:'SDC', revenue:[309754,291578,298417], operating:[55665,37334,41163], assets:[792752,821980,936339] },
          { name:'Harman', revenue:[143885,142749,157833], operating:[11737,13076,15311], assets:[179566,209347,223957] },
        ],
        years:['제55기','제56기','제57기'],
      };
    }
    function compactNumber(value) {
      const v = num(value);
      if (v == null) return 'N/A';
      const sign = v < 0 ? '△' : '';
      const a = Math.abs(v);
      if (a >= 10000) return sign + (a / 10000).toLocaleString('ko-KR', { maximumFractionDigits: 1 }) + '조';
      return sign + a.toLocaleString('ko-KR', { maximumFractionDigits: 0 }) + '억';
    }
    function miniMetricBars(values, cls) {
      const nums = (values || []).map((v) => num(v) || 0);
      const maxAbs = Math.max(1, ...nums.map((v) => Math.abs(v)));
      const bars = nums.map((v) => {
        const h = Math.max(5, Math.round(Math.abs(v) / maxAbs * 42));
        return '<span class="' + (v < 0 ? 'neg' : '') + '" style="--h:' + h + 'px"></span>';
      }).join('');
      return '<div class="mini-bars ' + (cls || '') + '">' + bars + '</div><span class="metric-values">' + nums.map(compactNumber).join(' → ') + '</span>';
    }
    function utilizationDetailHtml(row) {
      const data = reportDetailData(row);
      const items = data.utilization || [];
      if (!items.length) return '';
      const cards = items.map((item) => {
        const rate = Math.max(0, Math.min(100, num(item.rate) || 0));
        return '<article class="util-card">' +
          '<strong>' + esc(item.item) + '</strong>' +
          '<div class="rate">' + pct(rate) + '</div>' +
          '<p>' + esc(item.segment) + ' · 생산능력 ' + esc(Number(item.capacity).toLocaleString('ko-KR')) + esc(item.unit) + ' / 실제 ' + esc(Number(item.actual).toLocaleString('ko-KR')) + esc(item.unit) + '</p>' +
          '<div class="track"><span class="util-fill" style="width:' + rate + '%"></span></div>' +
        '</article>';
      }).join('');
      return '<div class="utilization-detail">' +
        '<div class="detail-head"><div><h3>생산능력과 2025년 가동률</h3><p>DART 사업보고서의 생산능력·생산실적·가동률 표를 초보 투자자가 읽기 쉬운 막대 카드로 바꿨습니다.</p></div><div class="mini-label">제57기 기준</div></div>' +
        '<div class="util-grid">' + cards + '</div>' +
        '<p class="segment-tip">가동률은 공장이 얼마나 빽빽하게 돌아가는지 보여줍니다. 장치산업에서는 가동률이 낮아지면 고정비 부담이 커져 이익률이 흔들릴 수 있습니다.</p>' +
      '</div>';
    }
    function segmentFinancialDetailHtml(row) {
      const data = reportDetailData(row);
      const segments = data.segmentFinance || [];
      if (!segments.length) return '';
      const cards = segments.map((segment) =>
        '<article class="segment-finance-card"><h4>' + rich(segment.name) + '</h4>' +
          '<div class="metric-line"><b>매출액</b><div>' + miniMetricBars(segment.revenue, '') + '</div></div>' +
          '<div class="metric-line"><b>영업이익</b><div>' + miniMetricBars(segment.operating, 'pink') + '</div></div>' +
          '<div class="metric-line"><b>총자산</b><div>' + miniMetricBars(segment.assets, 'gold') + '</div></div>' +
        '</article>'
      ).join('');
      return '<div class="segment-financial-detail">' +
        '<div class="detail-head"><div><h3>사업부문별 요약 재무현황 3개년</h3><p>제55기부터 제57기까지 사업부문별 매출액·영업이익·총자산을 한 장에서 비교합니다.</p></div><div class="mini-label">단위: 억원</div></div>' +
        '<div class="segment-finance-grid">' + cards + '</div>' +
        '<p class="segment-tip">매출은 사업 규모, 영업이익은 본업 수익성, 총자산은 해당 부문에 묶인 투자 규모를 보는 신호입니다.</p>' +
      '</div>';
    }
    function businessEvidenceHtml(row) {
      const lens = lensFor(row);
      const factory = showFactoryEvidence(row);
      const rawBody = factory && row.snippets && row.snippets.raw_moves && row.snippets.raw_moves.length
        ? rawMovesHtml(row.snippets.raw_moves)
        : fallbackList((lens.signals || []).slice(0, 3).map((item) => item[0] + ': ' + item[1]));
      const utilBody = factory && row.snippets && row.snippets.utilization && row.snippets.utilization.length
        ? utilizationHtml(row.snippets.utilization)
        : sentenceList(row.snippets && row.snippets.capacity, factory ? '생산능력·가동률 표가 구조화되지 않은 경우에는 사업보고서의 생산실적, 설비투자, 수주잔고 문단을 함께 봅니다.' : '이 업종은 공장 가동률보다 자본비율, 충당금, 운용자산, 고객 기반 같은 사업 신호가 더 중요합니다.', 3);
      const rawTitle = factory ? '주요 원재료 가격 변화: 매출원가가 흔들리는 신호' : lens.signalTitle || '업종별 핵심 사업 신호';
      const utilTitle = factory ? '생산능력 3개년 흐름과 가동률' : lens.strategyTitle || '투자자가 먼저 볼 체크포인트';
      return '<div class="business-evidence">' +
        '<article class="evidence-card"><h3>' + esc(rawTitle) + '</h3>' + rawBody + sourceSentence(row.snippets && row.snippets.raw_material) + '</article>' +
        '<article class="evidence-card"><h3>' + esc(utilTitle) + '</h3>' + utilBody + sourceSentence(row.snippets && row.snippets.capacity) + '</article>' +
      '</div>';
    }
    function segmentFinanceHtml(row) {
      const segments = row.snippets && Array.isArray(row.snippets.segment_breakdown) ? row.snippets.segment_breakdown : [];
      const history = row.history || {};
      const years = history.years || [];
      const latestRevenue = num(row.latest_year && row.latest_year.revenue) || 0;
      if (segments.length) {
        const maxShare = Math.max(...segments.map((segment) => Number(segment.revenue_share || 0)), 0.01);
        const cards = segments.slice(0, 4).map((segment) => {
          const share = Number(segment.revenue_share || 0);
          const pct = share > 1 ? share : share * 100;
          const amount = latestRevenue ? moneyEok(latestRevenue * (share > 1 ? share / 100 : share)) : '';
          const width = Math.max(6, Math.min(100, (share / maxShare) * 100));
          return '<article class="finance-mini"><strong>' + rich(segment.name || '사업부문') + '</strong><span>매출비중 ' + pct.toFixed(1).replace(/\\.0$/, '') + '%' + (amount ? ' · 약 ' + amount : '') + '</span><span>' + rich(segment.desc || '사업보고서에 표시된 주요 사업부문입니다.') + '</span><div class="segment-bar"><span style="--w:' + width.toFixed(1) + '%"></span></div></article>';
        }).join('');
        return '<div class="business-finance-panel"><h3>사업부문별 요약 재무현황: 매출비중으로 먼저 읽기</h3><div class="business-finance-grid">' + cards + '</div><p class="segment-tip">부문별 영업이익·총자산까지 구조화된 회사는 이후 같은 자리에서 3개년 그래프로 확장할 수 있습니다.</p></div>';
      }
      const metrics = [
        ['매출액', history.revenue || []],
        ['영업이익', history.operating_income || []],
        ['순이익', history.net_income || []],
        ['영업현금흐름', history.operating_cashflow || []],
      ].filter((item) => item[1] && item[1].length);
      if (!metrics.length) return '';
      const cards = metrics.map((item) => {
        const values = item[1].slice(-3);
        const labelYears = years.slice(-3);
        return '<article class="finance-mini"><strong>' + esc(item[0]) + '</strong>' + trendHtml(values, labelYears, item[0] === '매출액' ? '' : 'pink') + '</article>';
      }).join('');
      return '<div class="business-finance-panel"><h3>전체 회사 재무 흐름: 사업이 숫자로 이어지는 길</h3><div class="business-finance-grid">' + cards + '</div></div>';
    }
    function reportMapHtml(row) {
      return '<section class="section report-map"><div class="section-head"><div><h2>DART II. 사업의 내용 요약</h2><div class="mini-label">' + esc(categoryOf(row, '사업')) + '</div></div><p>우리가 사업보고서의 사업개요와 사업현황을 읽고, 초보 투자자가 바로 이해할 수 있게 요약했습니다.</p></div>' +
        '<div class="report-grid" style="grid-template-columns:1fr">' +
          '<article class="report-panel"><h3>요약 한눈에</h3>' + compactList(whatSellsText(row), 3) + sourceSentence(row.snippets && row.snippets.overview) + '</article>' +
        '</div>' +
        segmentBreakdownHtml(row) +
        customReportIdeasHtml(row) +
        utilizationDetailHtml(row) +
      '</section>';
    }
    function businessStatusPanelHtml(row) {
      const lens = lensFor(row);
      const key = industryKey(row);
      const showFactoryData = !['bank','insurance','securities','holding','platform','telecom','shipping','consumer'].includes(key);
      const rawBlock = showFactoryData && row.snippets && row.snippets.raw_moves && row.snippets.raw_moves.length
        ? '<article class="card"><h3>사업보고서 수치: 원재료 변화</h3>' + rawMovesHtml(row.snippets.raw_moves) + '</article>'
        : '';
      const utilBlock = showFactoryData && row.snippets && row.snippets.utilization && row.snippets.utilization.length
        ? '<article class="card"><h3>사업보고서 수치: 생산능력·가동률</h3>' + utilizationHtml(row.snippets.utilization) + '</article>'
        : '';
      const signalCards = lens.signals.map((item) =>
        '<article class="signal-card"><h3>' + rich(item[0]) + '</h3><p>' + rich(item[1]) + '</p></article>'
      ).join('');
      return '<section class="section"><div class="section-head"><div><h2>사업현황 체크포인트</h2><p>사업보고서의 사업현황을 읽을 때 업종별로 먼저 눈에 들어와야 하는 변수만 추렸습니다.</p></div><span class="mini-label">' + esc(badgeOf(row, '맞춤')) + ' 맞춤</span></div>' +
        '<div class="grid-4">' + signalCards + '</div>' +
        (rawBlock || utilBlock ? '<div class="evidence-board" style="margin-top:12px">' + rawBlock + utilBlock + '</div>' : '') +
      '</section>';
    }
    function businessCardsHtml(row) {
      const cards = row.business_cards || [];
      return cards.map((card) => {
        const image = card.image ? '<img class="segment-image" src="' + esc(card.image) + '" alt="' + esc(card.title || '사업 이미지') + '" loading="lazy" referrerpolicy="no-referrer" onerror="this.parentElement.classList.remove(\'has-image\');this.parentElement.querySelector(\'.photo-source\')?.remove();this.remove();">' : '';
        const source = card.image_source ? '<span class="photo-source">' + esc(card.image_source) + '</span>' : '';
        const caption = reportSummaryTone(card.caption || '사업보고서에 표시된 주요 제품 또는 서비스입니다.');
        return '<article class="orbit-card"><div class="product-visual ' + esc(card.kind || '') + (card.image ? ' has-image' : '') + '">' + image + '<span class="art a"></span><span class="art b"></span><span class="art c"></span><span class="visual-word">' + esc(card.visual || card.title || 'BUSINESS') + '</span>' + source + '</div><h3>' + rich(card.title || '주요 사업') + '</h3><p>' + rich(caption) + '</p></article>';
      }).join("");
    }
    function latestRdValue(row) {
      const costs = row.snippets && row.snippets.rd_chart && row.snippets.rd_chart.costs;
      return costs && costs.length ? num(costs[costs.length - 1]) || 0 : -1;
    }
    function rdSectionHtml(row) {
      const rd = row.snippets && row.snippets.rd_chart ? row.snippets.rd_chart : {};
      const years = rd.years || [];
      const validCosts = rd.costs && rd.costs.length >= 3 && rd.costs.every((v) => Math.abs(num(v) || 0) >= 1000);
      const validRatios = rd.ratios && rd.ratios.length >= 3 && rd.ratios.every((v) => (num(v) || 0) > 0 && (num(v) || 0) < 80);
      const has = validCosts || validRatios;
      if (!has && !(row.snippets && row.snippets.rd)) {
        return '<div class="grid-3">' +
          '<article class="card"><h3>신제품·서비스</h3>' + fallbackList(['숫자표가 없으면 신제품, 서비스 출시, 수주, 고객사 확대 문단을 먼저 봅니다.']) + '</article>' +
          '<article class="card"><h3>투자 강도</h3>' + fallbackList(['연구개발비가 없더라도 설비투자와 인력투자가 미래 매출을 준비하는 비용일 수 있습니다.']) + '</article>' +
          '<article class="card"><h3>초보 체크</h3>' + fallbackList(['R&D는 당장 비용이지만 성공하면 가격 경쟁력, 신제품, 진입장벽으로 돌아올 수 있습니다.']) + '</article>' +
        '</div>';
      }
      return '<div class="grid-3">' +
        '<article class="card"><h3>연구개발비용 합계</h3>' + rdTrend(validCosts ? rd.costs : [], years, '', moneyBaekman) + '</article>' +
        '<article class="card"><h3>매출액 대비 비율</h3>' + rdTrend(validRatios ? rd.ratios : [], years, 'gold', (v) => pct(v)) + '</article>' +
        '<article class="card"><h3>연구개발 요약</h3>' + sentenceList(row.snippets && row.snippets.rd, '연구개발 표가 잡히지 않으면 신제품 출시, 공장 증설, 고객사 확대를 성장 신호로 봅니다.', 3) + '</article>' +
      '</div>';
    }
    function innovationSectionHtml(row) {
      const key = industryKey(row);
      if (['bank','insurance','securities','holding','shipping','consumer'].includes(key)) return '';
      return '<section class="section"><div class="section-head"><h2>연구개발·신제품 현황</h2><p>R&D나 기술 투자가 중요한 업종은 사업보고서의 연구개발활동 문단과 표를 사업현황 관점에서 보여줍니다.</p></div>' +
        rdSectionHtml(row) +
      '</section>';
    }
    function listRows() {
      const q = $('#searchInput').value.trim().toLowerCase();
      let rows = DATA.filter((r) => !q || String(r.name).toLowerCase().includes(q) || String(r.stock_code).includes(q));
      rows = rows.slice().sort((a,b) => {
        if (sortMode === "ttm_per") {
          const av = num(a.ttm_per);
          const bv = num(b.ttm_per);
          const ar = av && av > 0 ? av : Infinity;
          const br = bv && bv > 0 ? bv : Infinity;
          if (ar !== br) return ar - br;
          return (num(b.market_cap) || -1) - (num(a.market_cap) || -1);
        }
        if (sortMode === "market_cap") return (num(b.market_cap) || -1) - (num(a.market_cap) || -1);
        return (a.rank || 999) - (b.rank || 999);
      });
      $('#companyList').innerHTML = rows.map((r, index) => {
        const metric = sortMode === "ttm_per" ? perText(r.ttm_per) : marketCapText(r.market_cap);
        return '<button class="company-btn ' + (r.stock_code === selected ? 'active' : '') + '" type="button" data-code="' + esc(r.stock_code) + '"><span class="rank">#' + esc(index + 1) + '</span><span><span class="cname">' + esc(r.name) + '</span><span class="cticker">' + esc(r.stock_code) + ' · ' + esc(categoryOf(r)) + '<br>' + esc(metric) + '</span></span><span class="sector-pill">' + esc(badgeOf(r)) + '</span></button>';
      }).join("");
    }
    function render(row) {
      if (!row) return;
      renderedTermNotes = new Set();
      const category = categoryOf(row);
      const sector = sectorOf(row);
      const reportLabel = row.report && row.report.name ? row.report.name : '최근 사업보고서';
      const dart = row.dart_url || (row.report && row.report.rcept_no ? 'https://dart.fss.or.kr/dsaf001/main.do?rcpNo=' + row.report.rcept_no : '#');
      $('#readerPanel').innerHTML =
        '<section class="company-hero">' +
          '<div class="orbit-lines"></div><div class="planet-ring"></div>' +
          '<div class="planet"><div><strong>' + esc(row.name) + '</strong><span>' + esc(row.stock_code) + '<br>' + esc(category) + '<br>' + esc(reportLabel.replace('사업보고서 ', '')) + '</span></div></div>' +
          '<div class="hero-grid cards-' + Math.min(4, Math.max(1, (row.business_cards || []).length)) + '">' + businessCardsHtml(row) + '</div>' +
        '</section>' +
        '<div class="content">' +
          reportMapHtml(row) +
          '<div class="source-row"><a class="source-link" href="' + esc(dart) + '" target="_blank" rel="noreferrer">DART 원문 열기</a><span class="mini-label">generated ' + esc(GENERATED_AT) + '</span></div>' +
        '</div>';
    }
    function selectByCode(code) {
      selected = code;
      listRows();
      render(DATA.find((r) => r.stock_code === code) || DATA[0]);
    }
    function setupTermTooltip() {
      const tooltip = document.createElement('div');
      tooltip.className = 'term-tooltip';
      tooltip.setAttribute('role', 'tooltip');
      document.body.appendChild(tooltip);
      let active = null;
      const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
      const place = (target) => {
        if (!target) return;
        const rect = target.getBoundingClientRect();
        tooltip.textContent = target.dataset.tip || '';
        tooltip.classList.add('show');
        const tipRect = tooltip.getBoundingClientRect();
        const gap = 10;
        let left = rect.left + rect.width / 2 - tipRect.width / 2;
        let top = rect.top - tipRect.height - gap;
        if (top < 10) top = rect.bottom + gap;
        left = clamp(left, 10, window.innerWidth - tipRect.width - 10);
        top = clamp(top, 10, window.innerHeight - tipRect.height - 10);
        tooltip.style.left = left + 'px';
        tooltip.style.top = top + 'px';
      };
      const show = (target) => {
        active = target;
        place(active);
      };
      const hide = () => {
        active = null;
        tooltip.classList.remove('show');
      };
      document.addEventListener('mouseover', (event) => {
        const target = event.target.closest && event.target.closest('.term-note');
        if (target) show(target);
      });
      document.addEventListener('focusin', (event) => {
        const target = event.target.closest && event.target.closest('.term-note');
        if (target) show(target);
      });
      document.addEventListener('mouseout', (event) => {
        if (event.target.closest && event.target.closest('.term-note')) hide();
      });
      document.addEventListener('focusout', (event) => {
        if (event.target.closest && event.target.closest('.term-note')) hide();
      });
      window.addEventListener('scroll', () => active ? place(active) : null, true);
      window.addEventListener('resize', () => active ? place(active) : null);
    }
    $('#searchInput').addEventListener('input', listRows);
    document.querySelectorAll('.sort-btn').forEach((btn) => btn.addEventListener('click', () => {
      sortMode = btn.dataset.sort;
      document.querySelectorAll('.sort-btn').forEach((b) => b.classList.toggle('active', b === btn));
      listRows();
    }));
    $('#companyList').addEventListener('click', (event) => {
      const btn = event.target.closest('.company-btn');
      if (btn) selectByCode(btn.dataset.code);
    });
    $('#coverageBadge').textContent = '수집 완료 ' + DATA.length + '개 기업';
    setupTermTooltip();
    listRows();
    render(DATA[0]);
  </script>
</body>
</html>
"""


def main() -> int:
    rows = json.loads(EQS_PATH.read_text(encoding="utf-8"))
    report_index = {}
    if FULLTEXT_INDEX.exists():
        report_index = json.loads(FULLTEXT_INDEX.read_text(encoding="utf-8"))

    market_snapshot = _load_market_snapshot(rows)
    business_cards = _load_business_cards()
    simplified = [
        _simplify_row(row, idx + 1, report_index, market_snapshot, business_cards)
        for idx, row in enumerate(rows)
    ]
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    html = HTML_TEMPLATE.replace(
        "__APP_DATA__",
        json.dumps(simplified, ensure_ascii=False, separators=(",", ":")),
    ).replace(
        "__CUSTOM_REPORT_IDEAS__",
        json.dumps(CUSTOM_REPORT_IDEAS, ensure_ascii=False, separators=(",", ":")),
    ).replace("__GENERATED_AT__", generated_at)
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"wrote {OUT_PATH}")
    print(f"companies {len(simplified)}")
    print(
        "snippets",
        sum(1 for row in simplified if any(row["snippets"].get(k) for k in ("overview", "raw_material", "capacity", "segment_finance"))),
    )
    print("business cards", sum(len(row["business_cards"]) for row in simplified))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
