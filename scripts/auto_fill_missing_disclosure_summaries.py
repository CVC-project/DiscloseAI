from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.disclosure.assemble_summary import sync_summaries_to_db, write_json_only

BASE = ROOT / "modules" / "disclosure" / "data" / "fulltext"
DB_PATH = ROOT / "modules" / "disclosure" / "data" / "disclosure.db"

STOP_WORDS = {
    "사업",
    "제품",
    "서비스",
    "매출",
    "부문",
    "기타",
    "합계",
    "계",
    "내부거래",
    "조정",
    "상계",
    "연결",
    "별도",
    "당사",
    "회사",
    "국내",
    "해외",
    "주요",
    "판매",
    "생산",
    "매출유형",
    "품목",
    "품 목",
    "구체적용도",
    "매출액",
    "비율",
    "사업부문",
    "사업소",
    "주요사업",
    "영업부문",
    "보고부문",
    "시스템부문",
    "총부문매출",
    "부문매출",
    "구분",
    "유형",
    "상품",
    "제품명",
    "모델명",
    "기능",
    "용도",
    "매입유형",
    "내수",
    "수출",
    "산출식",
    "사업본부",
    "제품품목명",
    "제 품 명",
    "품목명",
}

PRODUCT_HINTS = [
    "DRAM",
    "NAND",
    "HBM",
    "SSD",
    "Foundry",
    "모바일AP",
    "이미지센서",
    "OLED",
    "MLCC",
    "카메라모듈",
    "배터리",
    "LNG",
    "LNG선",
    "컨테이너선",
    "해양플랜트",
    "특수선",
    "원유",
    "석유제품",
    "화학제품",
    "항공기",
    "항공엔진",
    "선박엔진",
    "방산",
    "의약품",
    "바이오시밀러",
    "CDMO",
    "데이터센터",
    "변압기",
    "전선",
    "철강",
    "구리",
    "아연",
    "비철금속",
    "담배",
    "건강기능식품",
]

FINANCE_HINTS = ["은행", "증권", "보험", "카드", "자산운용", "캐피탈", "저축은행", "신탁"]
EXCLUDE_CELL_HINTS = [
    "금융자산",
    "금융상품",
    "공정가치",
    "상각후원가",
    "리스",
    "법인세",
    "감가상각",
    "손상",
    "매출채권",
    "재고자산",
    "유형자산",
    "무형자산",
    "충당부채",
    "금융부채",
    "부채",
    "자본금",
    "주식수",
    "효과 및",
    "연구과제",
    "정부보조금",
    "회계처리",
    "개발비",
    "연구개발비",
    "단위",
    "비율",
    "매출액",
    "금융수익",
    "금융비용",
    "건설중인자산",
    "판매경로",
    "납품 익월",
    "수 출",
    "제품군",
    "품 목 군",
    "품 목(",
    "매출비중",
    "사업연도",
    "사업년도",
    "사업구분",
    "부문 합계",
    "외화증권",
    "유가증권",
    "은행차입금",
    "담보부 은행차입금",
    "무담보 은행차입금",
    "기업은행",
    "씨티은행",
    "금융기관",
    "소속",
    "개량",
    "개선",
    "우리은행",
    "하나은행",
    "국민은행",
    "대학교",
    "재단법인",
    "Corporation",
    "Limited",
    "Philoptics",
    "USA",
    "China",
    "Taiwan",
    "Canada",
    "사업팀",
    "사업장",
    "사업개발팀",
    "사업기획팀",
    "외",
    "㈜",
    "(주)",
    "주식회사",
    "총부문매출",
    "영업부문",
    "보고부문",
    "부문별 손익",
    "건설공사 도급계약",
    "고객과의 계약",
    "전자공시시스템",
    "https",
]

RAW_TEXT_HINTS = [
    "판매경로 및 판매방법",
    "판매경로",
    "판매방법 및 조건",
    "주요매출처",
    "판매전략",
    "매입 현황",
    "원재료 매입 현황",
    "매출실적",
    "수주현황",
    "생산실적 및 가동률",
    "생산능력 및 생산실적",
    "제품 등의 매출현황",
    "수주총액 =",
    "수주잔고 =",
    "생산능력",
    "상기 매출액",
    "주석",
    "전자공시시스템",
    "참고하여 주시기",
]

LENS_KEYWORDS = {
    "finance": ("은행", "증권", "보험", "카드", "여신", "캐피탈", "자산운용", "신탁", "금융", "대출", "예금"),
    "holding": ("지주", "자회사", "종속회사", "투자부문", "배당수익", "브랜드수수료", "경영자문"),
    "bio": ("바이오", "의약품", "제약", "신약", "임상", "CDMO", "바이오시밀러", "의료기기", "진단"),
    "platform": ("플랫폼", "게임", "콘텐츠", "광고", "커머스", "핀테크", "이커머스", "온라인", "모바일"),
    "contract": ("건설", "조선", "방산", "수주", "플랜트", "LNG선", "해양", "특수선", "EPC", "토목"),
    "factory": ("제조", "생산", "공장", "가동률", "원재료", "설비", "부품", "소재", "장비", "반도체", "배터리"),
}

LENS_PRIORITY = ("finance", "holding", "bio", "platform", "contract", "factory")

LENS_SENTENCE_KEYWORDS = {
    "finance": ("이자", "수수료", "충당금", "대출", "예금", "손해율", "운용", "보험", "증권", "카드", "자본"),
    "holding": ("자회사", "종속회사", "투자", "지분", "배당", "브랜드", "포트폴리오", "매각", "인수"),
    "bio": ("제품", "파이프라인", "임상", "품목허가", "기술이전", "개발", "CDMO", "위탁", "진단"),
    "platform": ("이용자", "거래액", "광고", "결제", "구독", "콘텐츠", "IP", "플랫폼", "커머스"),
    "contract": ("수주", "수주잔고", "계약", "납품", "원가", "선박", "방산", "공사", "프로젝트"),
    "factory": ("원재료", "생산능력", "생산실적", "가동률", "설비", "고객", "수요", "제품", "공장"),
    "general": ("영위", "제조", "판매", "제공", "생산", "수주", "시장", "경쟁", "매출", "주요", "고객"),
}

OVERRIDES = {
    "00405320": {
        "products": ["온라인게임", "모바일게임", "게임 IP", "부분유료화 콘텐츠"],
        "segments": [{"name": "게임사업", "desc": "온라인·모바일 게임 서비스와 IP 활용", "revenue_share": None}],
    },
    "00816696": {
        "products": ["디스플레이 제조장비", "반도체 제조장비", "전장 제조장비", "자동화 장비"],
        "segments": [{"name": "제조장비", "desc": "디스플레이·반도체·전장 제조장비", "revenue_share": None}],
    },
    "01051472": {
        "products": ["암 분자진단", "예후예측 유전자검사", "동반진단", "원격검사서비스"],
        "segments": [{"name": "분자진단", "desc": "암 진단과 유전자검사 서비스", "revenue_share": None}],
    },
    "01095722": {
        "products": ["PCB", "패키지 기판", "모듈 PCB", "반도체용 기판"],
        "segments": [{"name": "PCB부문", "desc": "반도체와 전자제품용 인쇄회로기판", "revenue_share": None}],
    },
    "00596677": {
        "products": ["비메모리 반도체", "반도체 유통", "전자부품"],
        "segments": [{"name": "반도체 유통", "desc": "비메모리 반도체와 전자부품 유통", "revenue_share": None}],
    },
    "00616290": {
        "products": ["검색광고", "디지털 마케팅", "온라인 광고대행"],
        "segments": [{"name": "디지털 마케팅", "desc": "검색광고와 온라인 광고 운영 대행", "revenue_share": None}],
    },
    "00616962": {
        "products": ["벤처투자", "투자조합 운용", "관리보수", "성과보수"],
        "segments": [{"name": "벤처캐피탈", "desc": "투자조합 운용과 벤처기업 투자", "revenue_share": None}],
    },
    "01181807": {
        "products": ["패션 의류", "브랜드 의류", "유통"],
        "segments": [{"name": "패션사업", "desc": "의류 브랜드와 유통 사업", "revenue_share": None}],
    },
    "01506617": {
        "products": ["희귀질환 유전자검사", "AI 진단", "유전체 분석"],
        "segments": [{"name": "유전체 진단", "desc": "AI 기반 희귀질환 유전자 분석", "revenue_share": None}],
    },
}


def _clean(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    text = re.sub(r"^[가-힣]\.\s*", "", text)
    return text


def _norm(text: str) -> str:
    return re.sub(r"\s+", "", _clean(text))


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?다요임음됨함])\s+", text)
    out: list[str] = []
    for part in parts:
        s = _clean(part)
        if 30 <= len(s) <= 280 and not re.search(r"참조|상세표|해당사항 없음|기재를 생략|공시대상", s):
            out.append(s)
    return out


def _walk(node: dict):
    yield node
    for child in node.get("children", []) or []:
        yield from _walk(child)


def _find_chapter(parsed: dict, prefix: str) -> dict | None:
    for chapter in parsed.get("chapters", []) or []:
        if (chapter.get("title") or "").startswith(prefix):
            return chapter
    return None


def _node_text(node: dict) -> str:
    parts: list[str] = []
    for item in _walk(node):
        title = _clean(item.get("title", ""))
        if title:
            parts.append(title)
        parts.extend(_clean(p) for p in item.get("paragraphs", []) or [])
        for table in item.get("tables", []) or []:
            for row in (table.get("headers", []) or []) + (table.get("rows", []) or []):
                parts.append(" ".join(_clean(c) for c in row if _clean(c)))
    return "\n".join(p for p in parts if p)


def _focused_business_text(node: dict | None) -> str:
    if node is None:
        return ""
    parts: list[str] = []
    focus_titles = ("사업의 개요", "주요 제품", "주요제품", "서비스", "매출 및 수주", "원재료", "생산설비", "연구개발")
    for item in _walk(node):
        title = _clean(item.get("title", ""))
        if not title or not any(k in title for k in focus_titles):
            continue
        parts.append(title)
        parts.extend(_clean(p) for p in item.get("paragraphs", []) or [])
        for table in item.get("tables", []) or []:
            for row in (table.get("headers", []) or []) + (table.get("rows", []) or []):
                parts.append(" ".join(_clean(c) for c in row if _clean(c)))
    return "\n".join(p for p in parts if p)


def _focused_business_paragraph_text(node: dict | None) -> str:
    if node is None:
        return ""
    parts: list[str] = []
    focus_titles = ("사업의 개요", "주요 제품", "주요제품", "서비스", "매출 및 수주", "원재료", "생산설비", "연구개발")
    for item in _walk(node):
        title = _clean(item.get("title", ""))
        if not title or not any(k in title for k in focus_titles):
            continue
        parts.extend(_clean(p) for p in item.get("paragraphs", []) or [])
    return "\n".join(p for p in parts if p)


def _table_rows(node: dict) -> list[list[str]]:
    rows: list[list[str]] = []
    for item in _walk(node):
        for table in item.get("tables", []) or []:
            for row in (table.get("rows", []) or []):
                clean_row = [_clean(c) for c in row if _clean(c)]
                if clean_row:
                    rows.append(clean_row)
    return rows


def _unique(items: list[str], limit: int) -> list[str]:
    seen = set()
    out = []
    for item in items:
        value = _clean(item).strip("ㆍ·,;/")
        if not value or value in STOP_WORDS or len(value) < 2 or len(value) > 30:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(value)
        if len(out) >= limit:
            break
    return out


def _looks_like_business_cell(cell: str) -> bool:
    compact = _norm(cell)
    if not cell or len(cell) < 2 or len(cell) > 28:
        return False
    if compact in {_norm(w) for w in STOP_WORDS}:
        return False
    if any(h in cell for h in EXCLUDE_CELL_HINTS):
        return False
    if re.search(r"[<>\\[\\]]", cell):
        return False
    if "당사" in cell or "회사" in cell or "입니다" in cell or "합니다" in cell:
        return False
    if any(x in cell for x in ("는 ", "은 ", "를 ", "을 ", "로 ", "으로 ", "에서 ", "하고 ", "하며 ")):
        return False
    if cell.endswith(("다", "다.", "니다", "니다.")):
        return False
    if cell.count(" ") > 2:
        return False
    if re.search(r"\d{4}|[0-9]{2,}|%|원|주|기말|기초|당기|전기|제\\d+기", cell):
        return False
    return True


def _is_bad_sentence(sent: str) -> bool:
    if not sent:
        return True
    if any(hint in sent for hint in RAW_TEXT_HINTS):
        return True
    if any(mark in sent for mark in ("◆", "●", "[", "]", "(*", "※")):
        return True
    if sent.count("(") != sent.count(")") or sent.count("[") != sent.count("]"):
        return True
    if re.search(r"\([0-9가-힣]\)|^[0-9]+[).]\s*", sent):
        return True
    if re.search(r"https?://|전자공시시스템|정기공시 보고서", sent):
        return True
    if not sent.endswith(("다.", "니다.", "요.", ".")):
        return True
    if sent.count(" ") < 2:
        return True
    return False


def _classify_lens(corp_name: str, text: str, products: list[str], segments: list[dict]) -> str:
    text_blob = " ".join([corp_name or "", text[:5000]])
    seg_blob = " ".join(
        s.get("name", "") + " " + s.get("desc", "") for s in segments if isinstance(s, dict)
    )
    product_blob = " ".join(products)
    corp_blob = corp_name or ""
    scores: dict[str, float] = {}
    text_scores: dict[str, int] = {}
    segment_scores: dict[str, int] = {}
    product_scores: dict[str, int] = {}
    for lens, keywords in LENS_KEYWORDS.items():
        text_scores[lens] = sum(text_blob.count(keyword) for keyword in keywords)
        segment_scores[lens] = sum(seg_blob.count(keyword) for keyword in keywords)
        product_scores[lens] = sum(product_blob.count(keyword) for keyword in keywords)
        scores[lens] = text_scores[lens] * 2.0 + segment_scores[lens] * 0.8 + product_scores[lens] * 0.25

    if "미술품" in text_blob and "경매" in text_blob:
        return "general"
    if any(k in corp_blob for k in ("금융", "은행", "증권", "보험", "카드", "캐피탈")):
        return "finance"
    if any(k in corp_blob for k in ("지주", "홀딩스")) or "지주회사" in text_blob:
        return "holding"
    if "바이오" in corp_blob or "제약" in corp_blob:
        return "bio"

    # Product/segment tables often contain stray accounting or customer words.
    # Do not let those alone flip a manufacturing company into a wrong lens.
    if re.search(r"(은행업|보험업|증권업|카드업|여신전문|금융지주|자산운용업)", text_blob):
        return "finance"
    if text_scores["contract"] >= 3 or segment_scores["contract"] >= 2:
        return "contract"
    if text_scores["factory"] >= 2 or product_scores["factory"] >= 2:
        return "factory"
    if text_scores["platform"] >= 3:
        return "platform"
    if text_scores["bio"] >= 4:
        return "bio"
    for lens in ("bio", "platform", "contract", "factory", "general"):
        if scores.get(lens, 0) >= 3:
            return lens
    return "general"


def _join_names(items: list[str], limit: int = 4) -> str:
    names = [name for name in items if name]
    if not names:
        return ""
    if len(names) <= limit:
        return ", ".join(names)
    return ", ".join(names[:limit]) + " 등"


def _business_lead(corp_name: str, lens: str, products: list[str], segments: list[dict]) -> str:
    seg_names = [s.get("name", "") for s in segments if isinstance(s, dict) and s.get("name")]
    prod_names = products[:6]
    seg_text = _join_names(seg_names, 4)
    prod_text = _join_names(prod_names, 6)

    subject = corp_name or "이 회사"
    if lens == "finance":
        base = seg_text or prod_text or "금융 서비스"
        return f"{subject}의 주요 금융 서비스는 {base}입니다. 예금·대출, 투자, 보험, 카드 등에서 수익을 만듭니다."
    if lens == "holding":
        base = seg_text or prod_text or "핵심 자회사"
        return f"{subject}의 핵심은 {base}입니다. 자회사 실적과 지분가치가 사업의 중심입니다."
    if lens == "bio":
        base = prod_text or seg_text or "의약품·바이오 서비스"
        return f"{subject}의 주요 제품·서비스는 {base}입니다. 현재 판매 제품과 연구개발 성과가 함께 실적을 설명합니다."
    if lens == "platform":
        base = prod_text or seg_text or "디지털 서비스"
        return f"{subject}의 주요 서비스는 {base}입니다. 이용자 활동을 광고·결제·콘텐츠·거래 수익으로 연결합니다."
    if lens == "contract":
        base = seg_text or prod_text or "수주형 사업"
        return f"{subject}의 주요 사업은 {base}입니다. 계약을 따낸 뒤 제작·공사·납품을 거쳐 매출을 만듭니다."
    if lens == "factory":
        base = prod_text or seg_text or "제품"
        return f"{subject}의 주요 제품·서비스는 {base}입니다. 제품을 만들고 판매하는 제조 기반 회사입니다."
    base = seg_text or prod_text or "사업보고서에 기재된 제품과 서비스"
    return f"{subject}의 주요 사업은 {base}입니다."


def _sentence_score(sent: str, lens: str, corp_name: str) -> int:
    if _is_bad_sentence(sent):
        return 0
    score = 0
    for keyword in LENS_SENTENCE_KEYWORDS.get(lens, ()) + LENS_SENTENCE_KEYWORDS["general"]:
        if keyword in sent:
            score += 1
    if corp_name and corp_name[:3] in sent:
        score += 1
    if 45 <= len(sent) <= 180:
        score += 1
    if len(sent) > 220:
        score -= 2
    return max(score, 0)


def _lens_tail(lens: str) -> str:
    if lens == "finance":
        return "금융회사는 단순 매출보다 이자수익, 수수료, 충당금, 자본 여력이 함께 움직입니다."
    if lens == "holding":
        return "지주사는 개별 제품보다 핵심 자회사 구성과 투자 포트폴리오 변화가 중요합니다."
    if lens == "bio":
        return "바이오·제약사는 현재 팔리는 제품과 앞으로 매출이 될 개발 과제가 실적을 함께 움직입니다."
    if lens == "platform":
        return "플랫폼 기업은 이용자 기반이 광고, 결제, 구독, 콘텐츠 수익으로 이어지는 구조가 핵심입니다."
    if lens == "contract":
        return "수주형 사업은 계약 규모뿐 아니라 납기, 원가, 프로젝트 구성이 이익을 좌우합니다."
    if lens == "factory":
        return "제조업은 제품 수요, 원재료 가격, 생산능력과 가동률이 이익률에 직접 영향을 줍니다."
    return "초보 투자자는 제품·서비스와 매출이 나오는 경로를 먼저 이해하는 것이 좋습니다."


def _extract_products(text: str, rows: list[list[str]], corp_name: str) -> list[str]:
    candidates: list[str] = []
    for hint in PRODUCT_HINTS:
        if hint in text:
            candidates.append(hint)
    is_financial_company = any(k in text or k in corp_name for k in ("은행업", "금융지주", "보험업", "증권업", "카드업", "여신", "투자매매", "손해보험", "생명보험"))
    if is_financial_company:
        for hint in FINANCE_HINTS:
            if hint in text or hint in corp_name:
                candidates.append(hint)
    for row in rows:
        joined = " ".join(row)
        if any(k in joined for k in ("제품", "품목", "서비스", "매출유형")):
            for cell in row:
                if _norm(cell) in {_norm(w) for w in STOP_WORDS}:
                    continue
                for part in re.split(r"[,/ㆍ·및]+", cell):
                    if _looks_like_business_cell(part):
                        candidates.append(part)
    return _unique(candidates, 12)


def _extract_segments(text: str, rows: list[list[str]], products: list[str]) -> list[dict]:
    candidates: list[str] = []
    for row in rows:
        joined = " ".join(row)
        if any(h in joined for h in EXCLUDE_CELL_HINTS):
            continue
        for cell in row[:3]:
            if _looks_like_business_cell(cell) and any(k in cell for k in ("부문", "사업", "금융", "보험", "증권", "은행", "전자", "화학", "건설", "바이오")):
                candidates.append(cell)
    for name in re.findall(r"([A-Za-z0-9가-힣·ㆍ/-]{2,24}(?:부문|사업|금융|보험|증권|은행))", text):
        if _looks_like_business_cell(name):
            candidates.append(name)
    names = _unique(candidates, 5)
    if not names and products:
        names = products[:4]
    segments = []
    for name in names:
        desc = _segment_desc(name, products)
        segments.append({"name": name, "desc": desc, "revenue_share": None})
    return segments


def _segment_desc(name: str, products: list[str]) -> str:
    related = [p for p in products if p.lower() in name.lower() or name.lower() in p.lower()]
    if related:
        return f"{', '.join(related[:3])} 관련 제품·서비스"
    if any(k in name for k in ("은행", "금융")):
        return "예대, 수수료, 투자 등 금융 서비스"
    if "보험" in name:
        return "보험계약과 자산운용 중심 서비스"
    if "증권" in name:
        return "위탁매매, IB, 운용 등 증권 서비스"
    return "사업보고서상 주요 사업부문"


def _extract_investor_notes(parsed: dict, chapter_ii: dict | None, products: list[str], segments: list[dict]) -> str:
    corp_name = parsed.get("corp_name") or "이 회사"
    if _is_spac(corp_name):
        return f"{corp_name}은 일반 제조·서비스 회사가 아니라 다른 기업과 합병하는 것을 목적으로 상장된 기업인수목적회사입니다. 투자자는 합병 대상 기업, 합병 조건, 공모자금 운용 현황을 중심으로 봐야 합니다."
    if _is_reit(corp_name):
        return f"{corp_name}은 부동산 자산에 투자해 임대수익과 매각차익을 배당 재원으로 삼는 부동산투자회사입니다. 투자자는 보유 자산의 입지와 임차인 안정성, 차입금리, 배당 지속 가능성을 중심으로 봐야 합니다."
    if chapter_ii is None:
        return f"{corp_name}은 사업보고서 II. 사업의 내용 원문이 충분히 파싱되지 않아 제품·사업부문 중심 요약을 제한적으로 구성했습니다."
    text = _focused_business_paragraph_text(chapter_ii) or _node_text(chapter_ii)
    lens = _classify_lens(corp_name, text, products, segments)
    sents = _sentences(text)
    scored = [
        (score, sent)
        for sent in sents
        if (score := _sentence_score(sent, lens, corp_name)) > 0
    ]
    picked = [s for _, s in sorted(scored, key=lambda x: (-x[0], len(x[1])))[:2]]
    if not picked:
        picked = [s for s in sents[:2] if not _is_bad_sentence(s)]

    lead = _business_lead(corp_name, lens, products, segments)
    cleaned = []
    for sent in picked:
        sent = re.sub(
            r"^(매출 및 수주상황|판매경로 및 판매방법|판매방법 및 조건|원재료 및 생산설비|생산능력.*?가동률|주요매출처)\s*",
            "",
            sent,
        )
        sent = _clean(sent)
        if sent and sent not in cleaned:
            cleaned.append(sent)
    body = " ".join(cleaned[:2])
    for phrase in (
        "매출실적",
        "판매경로 판매방법 및 조건",
        "판매경로 판매방법 및 주요매출처",
        "판매경로 판매방법",
        "판매방법 및 조건",
        "판매방법 및 판매전략",
        "수주현황",
        "원재료 등의 현황",
        "생산설비에 관한 사항",
        "주요매출처",
        "상기 매출액은",
    ):
        body = body.replace(phrase, " ")
    body = _clean(body).replace("주요입니다.", "주요 사업입니다.").replace("주요입니다", "주요 사업입니다")
    parts = [lead]
    if body:
        parts.append(body)
    parts.append(_lens_tail(lens))
    note = _clean(" ".join(parts))
    if len(note) > 640:
        clipped = note[:640]
        last = max(clipped.rfind("다."), clipped.rfind("니다."), clipped.rfind("."))
        note = clipped[: last + 2] if last > 120 else clipped.rstrip()
    if note and not note.endswith(("다.", "니다.", "요.", ".")):
        note += "입니다."
    return note


def _is_spac(corp_name: str) -> bool:
    return "기업인수목적" in corp_name or "스팩" in corp_name


def _is_reit(corp_name: str) -> bool:
    return "위탁관리부동산투자회사" in corp_name or "부동산투자회사" in corp_name or "리츠" in corp_name


def _extract_audit(parsed: dict) -> tuple[str, list[dict], list[dict]]:
    text = "\n".join(_clean(p) for ch in parsed.get("chapters", []) or [] for n in _walk(ch) for p in n.get("paragraphs", []) or [])
    opinion = "적정의견" if "적정" in text and "감사의견" in text else ""
    return opinion, [], []


def _is_deterministic_summary(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    return data.get("model_used") == "deterministic-local-parser-v1"


def build_one(parsed_path: Path, *, overwrite_deterministic: bool = False) -> bool:
    out = parsed_path.parent / "summary.json"
    if out.exists() and not (overwrite_deterministic and _is_deterministic_summary(out)):
        return False
    parsed = json.loads(parsed_path.read_text(encoding="utf-8"))
    corp_code = parsed["corp_code"]
    rcept_no = parsed["rcept_no"]
    corp_name = parsed.get("corp_name") or ""
    chapter_ii = _find_chapter(parsed, "II.")
    if corp_code in OVERRIDES:
        products = OVERRIDES[corp_code]["products"]
        segments = OVERRIDES[corp_code]["segments"]
    elif _is_spac(corp_name):
        products = ["기업인수합병", "공모자금 운용"]
        segments = [{"name": "기업인수목적회사", "desc": "합병 대상 기업 탐색과 합병 추진", "revenue_share": None}]
    elif _is_reit(corp_name):
        products = ["부동산투자", "임대수익", "배당"]
        segments = [{"name": "부동산투자", "desc": "부동산 자산 운용과 임대수익", "revenue_share": None}]
    else:
        text = _focused_business_text(chapter_ii) or (_node_text(chapter_ii) if chapter_ii else "")
        rows = _table_rows(chapter_ii) if chapter_ii else []
        products = _extract_products(text, rows, corp_name)
        segments = _extract_segments(text, rows, products)
        if not products and "미술품" in text and "경매" in text:
            products = ["미술품 경매", "미술품 중개", "미술품 담보대출"]
            segments = [
                {"name": "미술품 경매", "desc": "미술품 경매와 중개 수수료", "revenue_share": None},
                {"name": "미술품 판매", "desc": "미술품 직접 판매와 관련 서비스", "revenue_share": None},
                {"name": "담보대출", "desc": "미술품 담보 대출 이자수익", "revenue_share": None},
            ]
        if not products and segments:
            products = _unique([s.get("name", "") for s in segments if isinstance(s, dict)], 8)
        if products and not segments:
            segments = [
                {"name": name, "desc": f"{name} 관련 제품·서비스", "revenue_share": None}
                for name in products[:4]
            ]
    investor_notes = _extract_investor_notes(parsed, chapter_ii, products, segments)
    audit_opinion, kam, emphasis = _extract_audit(parsed)
    write_json_only(
        corp_code,
        rcept_no,
        products=products,
        segments=segments,
        investor_notes=investor_notes,
        audit_opinion=audit_opinion,
        kam=kam,
        emphasis=emphasis,
        model_used="deterministic-local-parser-v1",
    )
    return True


def main(limit: int | None = None) -> None:
    parsed_paths = []
    for p in BASE.glob("*/*/parsed.json"):
        if "batch_runs" in p.parts:
            continue
        summary_path = p.parent / "summary.json"
        if not summary_path.exists() or _is_deterministic_summary(summary_path):
            parsed_paths.append(p)
    parsed_paths.sort(key=lambda p: (p.parent.parent.name, p.parent.name))
    if limit is not None:
        parsed_paths = parsed_paths[:limit]
    made = 0
    failed: list[tuple[str, str]] = []
    for idx, parsed_path in enumerate(parsed_paths, 1):
        try:
            if build_one(parsed_path, overwrite_deterministic=True):
                made += 1
        except Exception as exc:
            failed.append((str(parsed_path), repr(exc)))
        if idx % 100 == 0:
            print(f"processed {idx}/{len(parsed_paths)} made={made} failed={len(failed)}")

    pairs = [
        (p.parent.parent.name, p.parent.name)
        for p in BASE.glob("*/*/summary.json")
        if "batch_runs" not in p.parts
    ]
    synced = sync_summaries_to_db(pairs)
    parsed_count = sum(1 for p in BASE.glob("*/*/parsed.json") if "batch_runs" not in p.parts)
    summary_count = sum(1 for p in BASE.glob("*/*/summary.json") if "batch_runs" not in p.parts)
    with sqlite3.connect(DB_PATH) as con:
        db_count = con.execute("select count(*) from company_summary").fetchone()[0]
    print({"made": made, "failed": len(failed), "sync": synced, "parsed": parsed_count, "summary": summary_count, "db": db_count, "remaining": parsed_count - summary_count})
    if failed:
        fail_path = ROOT / "scripts" / "_auto_summary_failures.json"
        fail_path.write_text(json.dumps(failed, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"failures saved: {fail_path}")


if __name__ == "__main__":
    arg_limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    main(arg_limit)
