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

# ── 주석성 병기 제거 (2026-07-29 U-확대 전수 재훑기에서 발견) ────────────────
# 공시 표의 회사명 칸에는 각주 기호와 구사명이 함께 적히는 관행이 있다:
#   "한화오션 주식회사(주1)" · "삼성전자(주)(*1)" · "㈜포스코퓨처엠(구, ㈜포스코케미칼)"
# 이들은 **같은 법인을 가리키는 주석**이라 떼어내도 신원이 바뀌지 않는다(38표기·117회 실측).
#
# ⚠️ 일반 괄호는 절대 떼지 않는다 — 실측에서 `DB(Philippines) Inc.`가 괄호 제거 시
# 상장사 DB(012030)에 붙는 것을 확인했다. 필리핀 자회사를 한국 상장 모회사로 만드는
# HMM 사고(FN-013)와 같은 유형이다. 괄호 안이 **신원을 가르는 정보**일 수 있으므로
# 아래처럼 주석임이 형태로 확실한 것만 대상으로 한다.
_ANNOTATION_RE = re.compile(
    r"\(\s*주\s*\d+\s*\)"          # (주1) (주 6)
    r"|\(\s*\*+\s*[\d,\s]*\)"      # (*) (*1) (**) (*1,9)
    r"|※\s*\d*"                    # ※ ※1
    r"|\(\s*구[,.\s][^)]*\)"       # (구, ㈜포스코케미칼) (구. ㈜지투알)
    # ★U5: 상장 여부 표기 — 신원이 아니라 상태 주석이다. 같은 회사가
    # "㈜하이원파트너스"와 "㈜하이원파트너스(비상장)" 두 노드로 갈라지는 것을 막는다.
    r"|\(\s*(?:비상장|상장|비상장회사|상장회사|비상장법인)\s*\)"
    # ★2026-07-29 2차(검증 에이전트): **괄호로 닫히지 않은 후위 각주**가 미처리라
    # 같은 회사가 2~5개 노드로 갈라졌다(잉여 624건). 실측 잔존: `*`/`※` 1,099 ·
    # `주N)` 1,010 · `(비상장)` 416. 부수 효과로 상장 계열사 13건이 비상장으로
    # 떨어져 그룹 지배구조가 화면에서 끊겼다(한진·위메이드맥스·현대백화점 등).
    # ⚠️ 원칙 ②(일반 괄호 보존)와 충돌 없음 — 형태가 각주로 확정된 것만 대상.
    r"|[,\s]*\*+\s*\d*\s*\)?\s*$"                  # '…코리아**' '*위츠'의 후위 형태
    r"|[,\s]*주\s*[\d,\s]+\s*\)\s*$"               # '㈜티머니 주8)' '… 주3)'
    r"|[,\s]*주\s*[\d,]+\s*$"                      # '한화엔진 주4'
    # ★2026-07-30 (후속18) 실측 잔재 2종 추가 — 표시명에 885엣지가 각주를 안고 있었다.
    # ⚠️ 원칙 ②와 충돌 없음: 둘 다 **형태로 주석임이 확정**된 것이다(신원 정보 아님).
    r"|\(\s*주\s*\d*\s*(?:참조|참고)\s*\)"          # '(주1 참조)' — 각주 지시
    r"|\(\s*(?:보통주|종류주|우선주|의결권\s*없는\s*주식)\s*\)",  # '(보통주)' — 주식종류
)
_LEADING_MARK_RE = re.compile(r"^\s*[*※]+\s*")     # '*위츠' — 선행 각주 기호


def normalize_company_name(name: str | None) -> str:
    """(주)·주식회사·공백·영문 법인 접미어 제거 후 별칭 매핑 적용.

    규칙 (순서대로):
      1. 양끝 공백 제거
      2. 주석성 병기 제거 (각주 기호·구사명 병기 — _ANNOTATION_RE, 일반 괄호는 유지)
      3. 법인 접미어/접두어 제거 (대소문자 무관, 공백 무관)
      4. 모든 공백 제거
      5. NAME_ALIASES 적용

    None/빈 문자열 → 빈 문자열 반환.
    """
    if not name:
        return ""

    s = _LEADING_MARK_RE.sub("", _ANNOTATION_RE.sub("", name)).strip()
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

    # ★2026-07-30 (후속18): 각주를 떼고 나면 **구분자만 남는다**. 실측 사고 —
    # 원문 `코오롱티슈진\n(주1),(주2),(주5)`에서 각주 3개를 제거하면 `코오롱티슈진,,`이
    # 되어 정확일치에 실패했고, 코오롱티슈진이 **상장 노드와 비상장 노드로 동시에**
    # 화면에 나왔다(같은 회사·같은 지분율 39.27% / 39.3%). 각주가 콤마로 나열된 표기가
    # 원인이다. 양끝 구분자만 제거한다 — 내부 콤마는 사명의 일부일 수 있어 보존.
    s = s.strip(",.·、;:")

    # 별칭 매핑 (key/value 모두 lower+공백제거로 정규화 후 비교)
    def _norm(x: str) -> str:
        return _WHITESPACE_RE.sub("", x.lower())

    s_norm = _norm(s)
    for alias_key, alias_value in NAME_ALIASES.items():
        if s_norm == _norm(alias_key):
            return _norm(alias_value)

    return s_norm


# ── 한글 음차 별칭 규칙 생성 (2026-07-29 U-확대 조사에서 발견) ──────────────
# registry는 영문 이니셜 사명(CJ제일제당·SK하이닉스·LG전자)을 쓰는데 공시 원문은
# 한글 음차(씨제이제일제당)를 쓰는 경우가 많다. NAME_ALIASES가 수기 22건이라
# SK·LG·HD만 커버했고 CJ·GS·KT·BGF·HLB·HDC 등은 통째로 링킹 실패했다
# (실측: 실패 표기 120종·누적 807회 — CJ 222·LG 144·GS 58).
#
# ⚠️ normalize_company_name()에 음차 변환을 직접 넣으면 안 된다 — "이마트"→"e마트",
# "에스원"→"s원", "케이카"→"k카", "티웨이항공"→"t웨이항공"처럼 **실제 사명이 깨진다**.
# 안전한 방향은 그 반대: registry의 실제 사명에서 음차 변형을 **생성**해 별칭 키로만
# 등록한다. 생성된 키는 실존 사명에서 나온 것이므로 허위 노드를 만들 수 없다.
_LETTER_TO_KO = {
    "A": "에이", "B": "비", "C": "씨", "D": "디", "E": "이", "F": "에프", "G": "지",
    "H": "에이치", "I": "아이", "J": "제이", "K": "케이", "L": "엘", "M": "엠",
    "N": "엔", "O": "오", "P": "피", "Q": "큐", "R": "알", "S": "에스", "T": "티",
    "U": "유", "V": "브이", "W": "더블유", "X": "엑스", "Y": "와이", "Z": "제트",
}
_ASCII_RUN_RE = re.compile(r"[A-Za-z]+")
_MAX_INITIALISM_LEN = 4  # 5자 이상 영문 덩어리는 이니셜이 아니라 단어(Global·Motor…)


def korean_phonetic_variants(name: str | None) -> set[str]:
    """사명의 영문 이니셜 덩어리를 한글 음차로 바꾼 변형들(정규화 전 문자열).

    "CJ제일제당" → {"씨제이제일제당"} · "LG에너지솔루션" → {"엘지에너지솔루션"}
    영문 덩어리가 없거나 너무 길면 빈 집합(변형 없음).
    """
    if not name:
        return set()
    runs = [r for r in _ASCII_RUN_RE.findall(name) if len(r) <= _MAX_INITIALISM_LEN]
    if not runs:
        return set()
    variant = name
    for run in runs:
        variant = variant.replace(run, "".join(_LETTER_TO_KO[c] for c in run.upper()))
    return {variant} if variant != name else set()


def add_phonetic_aliases(mapping: dict[str, str], name: str, value: str) -> None:
    """name의 음차 변형을 mapping에 보강 등록 (실존 사명 키는 절대 덮지 않음).

    호출 측 규약: 실제 사명 키를 **먼저 전부 넣은 뒤** 이 함수를 돌릴 것.
    충돌(다른 회사가 이미 그 변형을 점유)이면 조용히 건너뛴다 — 모호한 표기를
    임의로 한쪽에 붙이는 것이 링킹 사고의 원인이므로(FN-013).
    """
    for variant in korean_phonetic_variants(name):
        key = normalize_company_name(variant)
        if key and key not in mapping:
            mapping[key] = value


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
    # 실제 사명 키를 전부 채운 뒤 음차 변형 보강 (실존 키 우선 — 덮어쓰기 없음)
    for name, ticker in rows:
        if name and ticker:
            add_phonetic_aliases(ticker_map, name, ticker)
    return ticker_map
