"""sectioner.py — 원문(raw_cache)을 섹션 단위로 분할 → report_section.

목차 기반: 'II. 사업의 내용' 절 + 'III.3 연결재무제표 주석'을 주석 번호(주1..주N) 단위 2차 분할.
표 HTML 보존(text_html) + LLM 투입용 markdown(text_md) 저장. 산업 무관 단일 구현(부록 B-2: 13/14 동일).

⚠️ DART 문서 구조는 기업별 편차가 있어 backfill(실데이터)에서 임계 조정 필요.
실행: python -m modules.report.sectioner

## 주석 머리글 마크업 4변종 (2026-07-30 전수 실측 — V-070)

최신연도 2,570사를 전수 계측한 결과, 주석 제목 마크업이 **회사마다 4가지로 갈린다**.
초기 구현은 F1만 알고 있었고 나머지는 통째로 미섹셔닝이었다(1,559사).

| 변종 | 형태 | 사수 | 처리 |
|---|---|---|---|
| F1  | `<TITLE>N. 제목 (연결)</TITLE>` | 1,007 | `_split_notes` (원본 유지) |
| F1b | `<TITLE>주석N - 제목 (연결)</TITLE>` XBRL TABLE-GROUP형 | 4 | `_NOTE_TITLE_RE` 접두·구분자 확장 |
| F2  | 주석 절 블록 안 `<P>`/`<SPAN>`/`<TITLE>`의 `N. 제목…` | 1,545 | `_split_inbody` (신설) |
| —   | 주석 자체가 원문에 없음(첨부 분리) | 15 | 섹션 없음 |

**F1 로직은 건드리지 않는다** — 별도FS 경계 캡(`_SEP_BOUNDARY_RE`)을 잃으면 마지막
연결주석이 문서 끝까지 삼켜 괴물블록이 된다(프로토타입에서 1,019건 재현). 새 경로는
**F1이 아무것도 못 찾았을 때만** 폴백으로 탄다.

## 별도(개별)재무제표 주석 = 연결 미작성사만 (리더 판정 2026-07-30)

연결재무제표를 작성하지 않는 회사(종속기업 없음)는 개별재무제표가 유일한 재무제표라
내부거래 미제거 문제가 성립하지 않는다 → `III.5.별도주석`으로 섹셔닝한다.
**연결을 보유한 회사의 별도주석은 섹셔닝하지 않는다** — 같은 회사에 연결·별도 두 판의
특수관계자 거래가 공존하면 금액 의미가 섞인다. 소비 측 표기는 relation 소관(별도 PR).
"""

from __future__ import annotations

import os
import re

from .db import get_local_session, init_local_db
from .models import PipelineState, ReportRaw, ReportSection

_HERE = os.path.dirname(__file__)

_SEC_CONN = "III.3.연결주석"
_SEC_SEP = "III.5.별도주석"
# 주석 절 블록이 실체를 가졌다고 볼 최소 길이. 연결 미작성사의 '해당사항 없음' 절은
# 실측 190~800자라 2만자면 넉넉히 가른다(전수에서 오탐 0 · 경계 표본 없음).
_MIN_NOTE_BLOCK = 20_000
# F2 노트 1건의 상한. ⚠️ 2026-07-31 정정: 이 값으로 **md 변환 전에** 잘랐더니 F1과
# 비대칭이 됐다 — F1은 `md = _to_md(note_html)`를 캡 이전 원문에서 만들고 text_html만
# 자른다. 그 결과 F2 노트의 text_md가 표 중간에서 끊겨(실측 특수관계 노트 86건 전부
# 표 태그 불균형·82건이 거래 라벨 보유) 파서가 뒷부분 상대를 통째로 못 본다.
# → 캡을 md 변환 뒤 저장 단계로 옮긴다(section_all의 text_html 슬라이스가 담당).
_INBODY_NOTE_CAP = 3_000_000

# 사업의 내용 절(통짜 저장) 패턴
_BIZ_HEAD = (r"II\.\s*사업의\s*내용", "II.사업의내용")
# ── 사업의내용 절 경계 (2026-07-31 신설 — V-074) ────────────────────────────────
# 종전에는 경계가 아예 없었다: `html[m.start() : m.start()+800_000]`, 즉 **첫 매치부터
# 고정 길이**. 표본 300 실측으로 두 방향의 오염이 확인됐다.
#  · 시작: 첫 매치가 절 머리글인 보고서는 172/294뿐. 나머지 122건(41%)은 **목차 표
#    셀**(53, `<TD>II. 사업의 내용</TD>` @7천대)이나 **본문 참조 문장**(69, "…'II. 사업의
#    내용'을 참조하시기 바랍니다") 에서 시작해, I. 회사의 개요부터 담고 있었다.
#  · 종료: 표본 196 중 189건(96%)이 800k를 꽉 채웠고 절 실길이 중앙은 144,978자 —
#    나머지 655k는 III. 재무에 관한 사항 이후가 통째로 딸려온 것(두산 2025는 재무 절
#    414k 포함). 최장 섹션 md 꼬리에 사용권자산·감가상각 명세가 들어있다.
# → 머리글은 **매치 직후가 닫는 태그인지**로 판정하고(TITLE 우선, 본문 P/SPAN 차선),
#   종료는 **다음 절의 TITLE 머리글**로 끊는다.
_BIZ_TITLE_RE = re.compile(r"<TITLE[^>]*>\s*II\.\s*사업의\s*내용\s*</TITLE>", re.I)
_BIZ_INBODY_RE = re.compile(r"<(P|SPAN)[^>]*>\s*II\.\s*사업의\s*내용\s*</\1>", re.I)
# ⚠️ 종료 경계로 **본문 `<P>`/`<SPAN>`의 로마숫자는 쓰지 않는다** — 넷 다 참조 문구라
#    절이 272자(067290 2021)·3,033자(082640 2023)로 잘린다. TITLE 형태만 경계로 인정.
_NEXT_SEC_RE = re.compile(
    r"<TITLE[^>]*>\s*(?:III|IV|IX|VIII|VII|VI|V|XII|XI|X)\.\s*[가-힣]", re.I
)
# 폭주 방어 안전판(경계 탐지가 실패해 문서 끝까지 가는 경우). 실제 저장 절단은
# `text_html[:500_000]`이 담당하고 **text_md는 자르지 않는다** — F1/F2와 같은 규약(V-073).
_BIZ_CAP = 3_000_000
# 연결재무제표 주석 = DART XML의 <TITLE>N. 제목 (연결)</TITLE> 태그로 구분 (주N 아님).
#  · 번호는 하위번호 허용: "N", "N-M"(셀트리온), "N.M"(LG엔솔) — 구분자 [.-] 둘 다.
#  · 제목은 tempered dot로 </TITLE>를 못 넘게 — '(연결)' 없는 사업내용 제목("6. 주요계약…")에서
#    시작해 다음 '(연결)'까지 통째로 삼켜 428KB 괴물 블록을 만들던 사고(NAVER) 방지.
#  · F1b: 번호 앞에 '주석' 접두가 붙는 XBRL TABLE-GROUP형도 같은 식으로 받는다 —
#    '주석33 - 특수관계자 (연결)'(영풍)·'주석 - 38. 특수관계자거래 - 연결 (연결)'(롯데칠성·
#    이마트) 두 표기가 실측된다. 접두를 안 받으면 F1이 0을 내고 F2 폴백이 3~4개짜리
#    엉터리 사슬을 만든다(실측 005300·139480).
#    A/B 전수 대조: 기존 2,559사 산출 동일 · 7사는 제목 앞 구분자('-A'→'A')만 정리되고
#    노트 수 불변 · 신규 획득만 발생 — 경계를 옮기지 않으므로 회귀 없음.
_NOTE_TITLE_RE = re.compile(
    r"<TITLE[^>]*>\s*(?:주\s*석\s*[-–—]?\s*)?\[?\s*"
    r"(\d{1,2}(?:\s*[.\-]\s*(?:\d{1,2}|[A-Za-z])(?![A-Za-z]))?)\s*\]?\s*[.\-]?\s*"
    r"((?:(?!</TITLE>).)+?)\s*\(\s*연결\s*\)\s*</TITLE>",
    re.S,
)
# (별도)/(개별) 접미 — 연결 미작성사에서 F1과 같은 형태를 쓰는 경우.
_SEP_NOTE_TITLE_RE = re.compile(
    r"<TITLE[^>]*>\s*(?:주\s*석\s*[-–—]?\s*)?\[?\s*"
    r"(\d{1,2}(?:\s*[.\-]\s*(?:\d{1,2}|[A-Za-z])(?![A-Za-z]))?)\s*\]?\s*[.\-]?\s*"
    r"((?:(?!</TITLE>).)+?)\s*\(\s*(?:별도|개별)\s*\)\s*</TITLE>",
    re.S,
)
# 연결 주석 영역의 끝 = 별도/개별 재무제표 섹션 시작(제목이 딱 '(N.) (별도/개별)?재무제표'로 끝나는 것).
# '재무제표의 작성기준'(SKT 주2) 같은 정상 주석을 경계로 오인하지 않도록 제목 끝을 </TITLE>로 못박음.
# 마지막 연결주석이 이 경계를 넘어 별도재무제표를 통째로 삼키던 사고(NAVER 주37) 방지 — 여기서 캡.
_SEP_BOUNDARY_RE = re.compile(
    r"<TITLE[^>]*>\s*(?:\d+(?:[.\-]\d+)?\.?\s*)?(?:별도|개별)?재무제표\s*"
    r"(?:\(\s*별도\s*\))?\s*</TITLE>"
)

# ── F2(본문 머리글형) 지원 ─────────────────────────────────────────────
# 목차의 주석 절 머리. 실측 절 번호는 연결='3.' 1,053사 / 별도='5.' 491사로 전량 일정.
_TITLE_ITER_RE = re.compile(r"<TITLE[^>]*>(.{0,200}?)</TITLE>", re.S)
_CONN_SECT_RE = re.compile(r"^\s*(?:[\d.\-]+\s*)?연결\s*재무제표\s*(?:에\s*대한\s*)?주석\s*$")
_SEP_SECT_RE = re.compile(r"^\s*(?:[\d.\-]+\s*)?(?:별도|개별)?\s*재무제표\s*(?:에\s*대한\s*)?주석\s*$")
# 절 블록의 끝 = 다음 목차 절. 주석 제목 자체가 <TITLE>인 변종(금융사 다수)이 있어
# '다음 TITLE'을 경계로 삼으면 블록이 190자로 측정된다 — 목차 절만 경계로 인정한다.
_SECT_BOUND_RE = re.compile(
    r"^\s*(?:[IVX]+\s*\.|【)"
    r"|^\s*[\d.\-]+\s*(?:요약재무정보|연결재무제표|재무제표|배당에\s*관한\s*사항"
    r"|증권의\s*발행|기타\s*재무에\s*관한\s*사항|대손충당금|재고자산)\s*(?:\(.*\))?\s*$"
)
# ⚠️ 위 경계 어휘 중 `대손충당금`·`재고자산`은 **주석 제목으로도 쓰이는 계정과목**이라
# 충돌한다(V-098, HPSP 2025 실측): 주1~10이 <P>/<SPAN>이다가 **주11부터 <TITLE>로
# 마크업이 전환**되는 문서에서 `<TITLE>11. 재고자산</TITLE>`이 목차 절로 오판돼 블록이
# 잘리고, 주11~33(특수관계자 포함)이 통째로 유실됐다. 목차 절 TITLE은 문서 구조 앵커
# `AASSOCNOTE="D-..."`를 갖고 본문 주석 TITLE은 갖지 않는다 — 계정과목형 경계는
# **AASSOCNOTE가 있을 때만** 인정한다(로마숫자·【·재무제표류 절 이름은 종전 그대로).
_ACCOUNT_BOUND_RE = re.compile(
    r"^\s*[\d.\-]+\s*(?:대손충당금|재고자산)\s*(?:\(.*\))?\s*$"
)
_TITLE_ATTR_ITER_RE = re.compile(r"<TITLE([^>]*)>(.{0,200}?)</TITLE>", re.S)
# 블록 안 주석 머리글 — 원소 첫머리의 'N. 제목'. 머리글 원소가 본문까지 품는 공시가
# 많아(`<P>33. 특수관계자 거래(1) 보고기간종료일 현재…</P>`) 닫는 태그를 요구하지 않고
# 제목은 _clean_note_title이 자른다. 뒤에 숫자·점·닫는 괄호가 오면 하위번호(2.1)·
# 열거((1))라 제외.
_INBODY_HDR_RE = re.compile(
    r"<(SPAN|P|TITLE)\b[^>]*>\s*(\d{1,2})\s*\.\s*(?![\d\s.)])([^<]{1,200})", re.I
)
# 같은 <P> 안에서 앞 주석 본문이 끝나고 다음 머리글이 이어 붙는 공시가 있다
# (`…희석주당이익과 동일합니다. 28. 특수관계자 (1) 지배회사는…`). 원소 첫머리만 보면
# 그 주석이 통째로 사라진다 — 실측 28사가 이 유형이고 전부 특수관계자 주석을 잃었다.
# 한국어 종결어미 뒤(`다.`/`요.`)만 인정해 표 셀의 번호 나열과 섞이지 않게 한다.
# 선행 형태 실측 4종 — 공백 없이 바로 붙는 쪽이 오히려 흔하다.
#   `…없습니다.18. 특수관계자와의 거래(1)…`   종결어미+마침표
#   `…동일합니다32. 특수관계자`               마침표 없음
#   `…(주석9참조).35. 특수관계자 등`          괄호+마침표
#   `</SPAN>38. 특수관계자 거래`              강조 태그 종료 직후
# 잡음이 섞여도 아래 최장 증가 사슬이 걸러낸다(후보가 늘어 사슬이 짧아지는 일은 없다).
_INBODY_MID_RE = re.compile(
    r"(?:</(?:SPAN|B|U|I|EM|STRONG)>|[다요]\.|니다|\)\.)\s{0,4}"
    r"(\d{1,2})\s*\.\s*(?![\d\s.)])([^<]{1,200})",
    re.I,
)
# 제목이 본문으로 흘러갈 때의 절단점. 소비 측 계약(relation의 title LIKE '특수관계%')이
# 제목 접두에 걸려 있으므로 절단 규칙이 곧 재현율이다.
_TITLE_CUT_RE = re.compile(
    r"\(\s*\d+\s*\)|\(\s*단위|보고기간|당기말|전기말|당기와|당기\s*중|당사의|회사의\s*|"
    r"연결회사|연결기업|다음과\s*같"
)


# 합본 주석 제목('10, 11. 매출채권…' · '7,8,9,22. 당기손익…')의 잔여 번호와,
# XBRL 표기의 꼬리표('… - 연결')를 걷어낸다. 소비 측이 제목 접두로 필터하므로
# 제목 머리에 번호가 남으면 그 노트는 도달하지 못한다.
_TITLE_LEAD_NUM_RE = re.compile(r"^\s*\d{1,2}\s*[.,]\s*")
_TITLE_TAIL_RE = re.compile(r"\s*[-–—]\s*(?:연결|별도|개별)\s*$")


def _tidy_title(t: str) -> str:
    t = _TITLE_TAIL_RE.sub("", t.strip(" :·-—.,"))
    for _ in range(4):
        new = _TITLE_LEAD_NUM_RE.sub("", t)
        if new == t:
            break
        t = new
    return t.strip(" :·-—.,")


def _clean_note_title(raw: str) -> str:
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", raw)).strip()
    cut = _TITLE_CUT_RE.split(t)[0]
    return (_tidy_title(cut) or _tidy_title(t))[:60]


def _find_note_section(full_xml: str, kind: str) -> str:
    """목차의 주석 절 블록(최장) 반환 — kind in {'conn','sep'}. 없으면 ''."""
    titles = [
        (
            m.start(),
            re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(2))).strip(),
            m.group(1),  # 태그 속성 원문 — 계정과목형 경계의 목차 앵커 판정용(V-098)
        )
        for m in _TITLE_ATTR_ITER_RE.finditer(full_xml)
    ]

    def is_head(t: str) -> bool:
        if kind == "conn":
            return bool(_CONN_SECT_RE.match(t))
        return bool(_SEP_SECT_RE.match(t)) and "연결" not in t

    def is_bound(t: str, attrs: str) -> bool:
        if _CONN_SECT_RE.match(t) or (_SEP_SECT_RE.match(t) and "연결" not in t):
            return True
        if not _SECT_BOUND_RE.match(t):
            return False
        # 계정과목형(`N. 재고자산`·`N. 대손충당금`)은 주석 제목과 충돌한다 —
        # 목차 앵커(AASSOCNOTE)가 있는 진짜 절일 때만 경계로 본다(V-098).
        if _ACCOUNT_BOUND_RE.match(t) and "AASSOCNOTE" not in attrs.upper():
            return False
        return True

    best = ""
    for i, (pos, t, _a) in enumerate(titles):
        if not is_head(t):
            continue
        end = len(full_xml)
        for pos2, t2, a2 in titles[i + 1 :]:
            if is_bound(t2, a2):
                end = pos2
                break
        if end - pos > len(best):
            best = full_xml[pos:end]
    return best


def _split_inbody(block: str) -> list[tuple[str, str, str]]:
    """F2 — 절 블록 안 머리글로 주석 분할 → [(note_no, title, html), ...].

    머리글 후보에는 표 본문의 '1. …' 같은 잡음이 섞이므로, **번호가 증가하는 가장 긴
    사슬**만 채택한다(간격 4 이하). 첫 히트를 무조건 시작점으로 삼으면 절 머리 TITLE의
    번호('3. 연결재무제표 주석')나 결번 때문에 사슬이 통째로 무너진다 — 실측 310사가
    이 방식에서 0건이었다.
    """
    hits: list[tuple[int, str, int]] = []
    for m in _INBODY_HDR_RE.finditer(block):
        if m.start() == 0:  # 절 머리 TITLE 자신
            continue
        body = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(3))).strip()
        if _CONN_SECT_RE.match(body) or _SEP_SECT_RE.match(body):
            continue
        hits.append((int(m.group(2)), _clean_note_title(m.group(3)), m.start()))
    for m in _INBODY_MID_RE.finditer(block):
        hits.append((int(m.group(1)), _clean_note_title(m.group(2)), m.start()))
    hits.sort(key=lambda h: h[2])
    if not hits:
        return []
    n = len(hits)
    length = [1] * n
    prev = [-1] * n
    for i in range(n):
        for j in range(i):
            if hits[j][0] < hits[i][0] <= hits[j][0] + 4 and length[j] + 1 > length[i]:
                length[i], prev[i] = length[j] + 1, j
    idx = max(range(n), key=lambda i: length[i])
    chain: list[tuple[int, str, int]] = []
    while idx != -1:
        chain.append(hits[idx])
        idx = prev[idx]
    chain.reverse()
    out: list[tuple[str, str, str]] = []
    for i, (no, title, s) in enumerate(chain):
        e = chain[i + 1][2] if i + 1 < len(chain) else len(block)
        out.append((str(no), title, block[s : min(e, s + _INBODY_NOTE_CAP)]))
        # ↑ 상한은 폭주 방어용 안전판일 뿐 — 실제 저장 절단은 section_all의
        #   text_html[:500_000]이 하고, text_md는 F1과 같이 **온전한 원문**에서 만든다.
    return out


def _split_sep_notes(full_xml: str) -> list[tuple[str, str, str]]:
    """별도(개별)재무제표 주석 — 접미 (별도) 우선, 없으면 절 블록 F2."""
    hits = list(_SEP_NOTE_TITLE_RE.finditer(full_xml))
    if len(hits) >= 5:
        out = []
        for i, m in enumerate(hits):
            if out and _note_key(m.group(1)) <= _note_key(out[-1][0]):
                break
            e = hits[i + 1].start() if i + 1 < len(hits) else min(len(full_xml), m.start() + 300_000)
            title = _tidy_title(re.sub(r"\s+", " ", m.group(2)))[:60]
            out.append((m.group(1), title, full_xml[m.start() : e]))
        if len(out) >= 5:
            return out
    block = _find_note_section(full_xml, "sep")
    return _split_inbody(block) if len(block) > _MIN_NOTE_BLOCK else []


def _load_raw(raw_path: str) -> str | None:
    p = os.path.join(_HERE, raw_path) if raw_path else None
    if not p or not os.path.exists(p):
        return None
    return open(p, encoding="utf-8", errors="ignore").read()


def _to_md(html: str) -> str:
    """표 구조를 대략 보존한 markdown 근사 (LLM 투입용). 표는 |셀| 형태로."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    parts = []
    # DART XML: 표 셀은 <TE>·<TU>(+표준 td/th), 문단은 <P> (html.parser가 소문자화)
    for el in soup.find_all(["p", "table"]):
        if el.name == "table":
            for tr in el.find_all("tr"):
                cells = [c.get_text(strip=True) for c in tr.find_all(["td", "th", "te", "tu"])]
                if any(cells):
                    parts.append("| " + " | ".join(cells) + " |")
            parts.append("")
        else:
            t = el.get_text(strip=True)
            if t:
                parts.append(t)
    return "\n".join(parts)


def _note_key(no: str) -> tuple[int, int]:
    """'2-1'·'11.1'·'3'·'6-A' → (주번호, 하위번호) 정렬키. 하위번호 없으면 0.

    ⚠️ 알파벳 하위번호(`6-A`·`6-B`)를 못 읽으면 둘 다 주번호 6이 되어 "번호 역행 =
    주석 끝"으로 오판하고 그 뒤 전부를 버린다 — 유안타증권은 34개 중 6개만 남고
    특수관계자 주석(35)이 통째로 사라져 있었다(실측). A→1, B→2로 읽는다.
    """
    parts = [p.strip() for p in re.split(r"[.\-]", no, maxsplit=1)]
    minor = 0
    if len(parts) > 1 and parts[1]:
        if parts[1].isdigit():
            minor = int(parts[1])
        elif parts[1][:1].isalpha():
            minor = ord(parts[1][:1].upper()) - 64
    return (int(parts[0]), minor)


def _split_notes(full_xml: str) -> list[tuple[str, str, str]]:
    """연결재무제표 주석을 주석 번호 단위로 분할 → [(note_no, title, html), ...].

    각 연결 주석은 <TITLE>N. 제목 (연결)</TITLE>로 시작('(연결)' 접미로 별도 주석과 구분).
    '연결재무제표 주석' 헤더는 목차·요약에도 반복 등장(NAVER는 11회)해 신뢰 불가 →
    주석 번호 1(연결)이 처음 나오는 지점을 연결 주석 시작으로 잡는다. 사업의 내용 절 제목엔
    '(연결)' 접미가 없어 오검출되지 않는다. 별도재무제표 섹션 경계 또는 번호 역행에서 중단.
    """
    hits = list(_NOTE_TITLE_RE.finditer(full_xml))
    if not hits:
        return []
    start = next((i for i, m in enumerate(hits) if _note_key(m.group(1))[0] == 1), 0)
    hits = hits[start:]
    # 연결 주석 영역 뒤에 오는 별도재무제표 섹션 시작 = 마지막 주석의 상한(과다 포획 방지)
    sb = _SEP_BOUNDARY_RE.search(full_xml, hits[0].start())
    sep = sb.start() if sb else len(full_xml)
    # ① 채택할 히트를 먼저 고르고 ② 그 다음에 구간을 자른다.
    #    한 단계로 하면 '건너뛴 히트'의 위치가 앞 주석의 끝이 되어 본문이 잘려나간다.
    kept: list[tuple[str, str, int]] = []
    stop_at = sep  # 마지막 주석의 상한 — 중단 지점을 넘어 별도 주석을 삼키지 않게
    for m in hits:
        no = re.sub(r"\s+", "", m.group(1))  # '26. 27' → '26.27' (합본 제목)
        s = m.start()
        if s >= sep:  # 별도재무제표 섹션 진입 → 연결 주석 끝
            break
        if kept:
            k, last = _note_key(no), _note_key(kept[-1][0])
            # 번호가 1~2로 **리셋**되면 별도 주석 진입 = 연결 주석 끝(NAVER 주37 사고 방어).
            if k[0] <= 2 and last[0] >= 5:
                stop_at = s
                break
            # 리셋이 아닌 역행·중복은 종료 신호가 아니다. 종료로 오판해 버린 실측:
            #  · 같은 번호 재등장(신세계 주16이 표별로 TITLE 2회) → 뒤 33개 소실(주42 특수관계자)
            #  · 원문 자체의 순서 뒤바뀜(동양생명 19-A→20-A→19-B) → 뒤 15개 소실(주39 특수관계자)
            if k == last:
                continue
        kept.append((no, _tidy_title(re.sub(r"\s+", " ", m.group(2))), s))
    out: list[tuple[str, str, str]] = []
    for i, (no, title, s) in enumerate(kept):
        # 다음 채택 주석까지가 한 주석 — 건너뛴 중복 히트에서 끊으면 본문이 잘린다.
        # 마지막 주석만은 중단 지점(stop_at)이 상한이다.
        e = kept[i + 1][2] if i + 1 < len(kept) else min(len(full_xml), s + 300_000)
        out.append((no, title, full_xml[s : min(e, stop_at)]))
    return out


def _split_conn_notes(full_xml: str) -> list[tuple[str, str, str]]:
    """연결주석 — F1/F1b(접미 TITLE) 우선, 아무것도 못 잡으면 F2(절 블록 본문 머리글).

    F1 결과를 그대로 믿는 조건은 **주1에서 시작하거나 충분히 많을 때**다. 주석과 무관한
    자리에 '(연결)' 접미 제목이 딱 하나 있는 공시가 있어(제이알글로벌리츠의 증권 발행 절
    `<TITLE>5-1) 회사채 미상환 잔액(연결)</TITLE>`), 그 한 줄 때문에 F1이 1건을 돌려주고
    폴백이 막혀 진짜 주석 33개가 통째로 사라졌다.
    """
    notes = _split_notes(full_xml)
    if notes and (_note_key(notes[0][0])[0] == 1 or len(notes) >= 12):
        return notes
    block = _find_note_section(full_xml, "conn")
    alt = _split_inbody(block) if len(block) > _MIN_NOTE_BLOCK else []
    return alt if len(alt) > len(notes) else notes


def find_biz_section(html: str) -> tuple[int, int] | None:
    """`II. 사업의 내용` 절의 [시작, 끝) 위치. 머리글이 없으면 None.

    시작은 **머리글 형태**를 우선한다(TITLE → 본문 P/SPAN → 옛 동작 폴백).
    폴백을 남기는 이유: 머리글이 어떤 태그에도 안 싸인 보고서가 실제로 있고(표본 300 중
    매치없음 4·SPAN머리글 1), 그 경우 옛 동작이라도 유지하는 편이 0건보다 낫다.
    끝은 다음 절의 TITLE 머리글 — 없으면 문서 끝(둘 다 `_BIZ_CAP` 안전판으로 상한).
    """
    m = _BIZ_TITLE_RE.search(html) or _BIZ_INBODY_RE.search(html)
    if m:
        start = m.start()
    else:
        m0 = re.search(_BIZ_HEAD[0], html)
        if not m0:
            return None
        start = m0.start()
    nxt = _NEXT_SEC_RE.search(html, start + 10)
    end = nxt.start() if nxt else len(html)
    return start, min(end, start + _BIZ_CAP)


def section_all(
    tickers: list[str] | None = None, rcept_nos: list[str] | None = None
) -> None:
    """rcept_nos: 보고서 단위 필터(V-098 절단 의심군처럼 **특정 연도만** 재섹셔닝할 때).
    ticker 필터는 그 회사 전 연도를 다시 돌므로, 표적이 rcept 목록이면 이쪽이 정확하고 싸다."""
    init_local_db()
    sess = get_local_session()
    q = sess.query(ReportRaw)
    if tickers:
        q = q.filter(ReportRaw.ticker.in_(set(tickers)))
    if rcept_nos:
        q = q.filter(ReportRaw.rcept_no.in_(set(rcept_nos)))
    for raw in q.all():
        html = _load_raw(raw.raw_path)
        if not html:
            _mark(sess, raw.rcept_no, raw.ticker, "FAIL")
            continue
        # 기존 섹션 삭제 후 재적재 (idempotent)
        sess.query(ReportSection).filter_by(rcept_no=raw.rcept_no).delete()
        n = 0
        # ① II. 사업의 내용 (절 경계까지 통짜)
        bounds = find_biz_section(html)
        if bounds:
            seg = html[bounds[0] : bounds[1]]
            md = _to_md(seg)
            sess.add(
                ReportSection(
                    rcept_no=raw.rcept_no,
                    section_key=_BIZ_HEAD[1],
                    note_no=None,
                    title=_BIZ_HEAD[1],
                    text_html=seg[:500_000],
                    text_md=md,
                    char_len=len(md),
                )
            )
            n += 1
        # ② 연결재무제표 주석 → 주석 번호 단위 (F1/F1b → F2 폴백)
        notes = _split_conn_notes(html)
        section_key = _SEC_CONN
        # ③ 연결주석이 아예 없는 회사(= 연결재무제표 미작성)만 별도·개별 주석을 채운다.
        #    연결 보유사의 별도주석은 담지 않는다(리더 판정 2026-07-30, 모듈 docstring 참조).
        if not notes:
            notes = _split_sep_notes(html)
            section_key = _SEC_SEP
        for note_no, title, note_html in notes:
            md = _to_md(note_html)
            sess.add(
                ReportSection(
                    rcept_no=raw.rcept_no,
                    section_key=section_key,
                    note_no=note_no,
                    title=title,
                    text_html=note_html[:500_000],
                    text_md=md,
                    char_len=len(md),
                )
            )
            n += 1
        _mark(sess, raw.rcept_no, raw.ticker, "OK" if n > 1 else "FAIL")
        sess.commit()
        print(f"[{raw.ticker}] {raw.fiscal_year} rcept={raw.rcept_no}: {n} 섹션")
    sess.close()


def resection_biz(tickers: list[str] | None = None, progress_every: int = 200) -> dict:
    """`II.사업의내용` 섹션**만** 재생성한다(주석 섹션은 손대지 않는다).

    왜 `section_all`을 안 쓰는가 — `section_all`은 rcept_no의 **모든 섹션을 delete 후
    재적재**한다. 주석 섹션(`III.3.연결주석`·`III.5.별도주석`)은 relation의 특수관계자
    엣지 20,441건(source_kind='rp_note')과 지배구조의 원천이라, 절 경계 수정과 무관한
    경로를 같이 흔들면 회귀 원인을 가릴 수 없다. 사업의내용만 갱신하면 **주석 무변이
    구조적으로 보장**된다(A/B로 세지 않아도 됨).

    Returns: {'updated','inserted','deleted','no_head','raw_missing','len_delta'}
    """
    init_local_db()
    sess = get_local_session()
    q = sess.query(ReportRaw)
    if tickers:
        q = q.filter(ReportRaw.ticker.in_(set(tickers)))
    rows = q.all()
    st = {"updated": 0, "inserted": 0, "deleted": 0, "no_head": 0, "raw_missing": 0}
    len_delta: list[tuple[str, int, int]] = []
    for i, raw in enumerate(rows, 1):
        html = _load_raw(raw.raw_path)
        if not html:
            st["raw_missing"] += 1
            continue
        cur = (
            sess.query(ReportSection)
            .filter_by(rcept_no=raw.rcept_no, section_key=_BIZ_HEAD[1])
            .one_or_none()
        )
        bounds = find_biz_section(html)
        if not bounds:
            st["no_head"] += 1
            if cur is not None:  # 머리글이 사라졌으면 낡은 행을 남기지 않는다
                sess.delete(cur)
                st["deleted"] += 1
            continue
        seg = html[bounds[0] : bounds[1]]
        md = _to_md(seg)
        before = cur.char_len if cur is not None else 0
        if cur is None:
            sess.add(
                ReportSection(
                    rcept_no=raw.rcept_no,
                    section_key=_BIZ_HEAD[1],
                    note_no=None,
                    title=_BIZ_HEAD[1],
                    text_html=seg[:500_000],
                    text_md=md,
                    char_len=len(md),
                )
            )
            st["inserted"] += 1
        else:
            cur.text_html, cur.text_md, cur.char_len = seg[:500_000], md, len(md)
            st["updated"] += 1
        len_delta.append((raw.rcept_no, before, len(md)))
        if i % progress_every == 0:
            sess.commit()
            print(f"  {i}/{len(rows)} … {st}", flush=True)
    sess.commit()
    sess.close()
    st["len_delta"] = len_delta
    return st


def _mark(sess, rcept_no, ticker, status):
    st = (
        sess.query(PipelineState)
        .filter_by(rcept_no=rcept_no, target="section")
        .one_or_none()
    )
    if st is None:
        st = PipelineState(rcept_no=rcept_no, ticker=ticker, target="section")
        sess.add(st)
    st.stage, st.status = "SECTIONED", status
    st.attempts = (st.attempts or 0) + 1


def sectioning_health(ticker: str) -> list[str]:
    """빌드 전 프리플라이트(S0) — 최신 사업보고서 주석이 제대로 분할됐는지 검증.
    이번 세션 3종 사고(1주석 붕괴·괴물블록·하위번호 조용한 누락)를 자동 포착.
    반환: 문제 목록(빈 리스트=정상). /galaxy-golden이 착수 전 게이트로 호출.
    """
    sess = get_local_session()
    raw = (
        sess.query(ReportRaw)
        .filter(ReportRaw.ticker == ticker)
        .order_by(ReportRaw.fiscal_year.desc())
        .first()
    )
    if not raw:
        sess.close()
        return [f"[{ticker}] 수집된 보고서 없음 — collector 먼저"]
    secs = (
        sess.query(ReportSection)
        .filter(ReportSection.rcept_no == raw.rcept_no, ReportSection.note_no.isnot(None))
        .all()
    )
    notes = [(s.note_no, s.char_len or 0) for s in secs]
    sess.close()
    issues: list[str] = []
    n = len(notes)
    if n < 12:  # 제조·플랫폼 표준 보고서는 30+; <12 = 붕괴/포맷 미지원(금융·지주는 스코프아웃)
        issues.append(f"주석 {n}개(<12) — 분할 붕괴/포맷 미지원(금융·지주면 스코프아웃)")
    big = [no for no, cl in notes if cl > 200_000]
    if big:
        issues.append(f"괴물블록(>20만자) 주{big} — 별도FS 유입/미분할 의심")
    majors = sorted({_note_key(no)[0] for no, _ in notes}) if notes else []
    if majors:
        gaps = [m for m in range(1, majors[-1] + 1) if m not in majors]
        if len(gaps) > majors[-1] * 0.3:
            issues.append(f"번호 결번 과다 {gaps} — 하위번호/포맷 누락 의심")
    return issues


if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 3 and sys.argv[1] == "--health":
        tk = sys.argv[2]
        probs = sectioning_health(tk)
        print(f"[{tk}] sectioning health:", "OK ✅" if not probs else "FAIL ❌")
        for p in probs:
            print("  -", p)
        sys.exit(1 if probs else 0)
    section_all()
