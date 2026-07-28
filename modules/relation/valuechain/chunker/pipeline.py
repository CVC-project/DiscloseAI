"""문장 윈도우 청킹 파이프라인 (valuechain/PLAN.md §3.1 — V2 ①②단계, GPU 불요).

흐름:
  shared/data/reports.db(read-only, 공식 예외)의 `II.사업의내용` 섹션
    → 문장 분할(원문 오프셋 보존)
    → 후보 게이트: 관계 어휘 OR 타사명(레지스트리+별칭, 자기 회사 제외) 포함 문장
    → 후보 문장 ±2문장 윈도우 → 겹침 병합 → 최대 ~1.5K자
    → VcChunk upsert + VcPipelineState(stage='extract', pending)

멱등(D12): chunk_id = "{rcept_no}:{section_key}:{seq}" — 같은 입력이면 재실행에도
동일 id/seq. LLM 추출(V2 ③, GPU)은 이 큐를 소비한다.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from pathlib import Path

from modules.relation.common.names import NAME_ALIASES
from modules.relation.storage.db import get_local_session
from modules.relation.storage.models import CompanyRegistry, VcChunk, VcPipelineState

logger = logging.getLogger(__name__)

_REPORTS_DB = Path(__file__).resolve().parents[4] / "shared" / "data" / "reports.db"

SECTION_KEY = "II.사업의내용"
WINDOW = 2            # 후보 문장 ± N문장
MAX_CHUNK_CHARS = 1500

# PLAN §3.1 관계 어휘 — 밸류체인 신호가 되는 표현 (휴리스틱: 넓게 잡고 게이트 뒤 LLM이 판별)
RELATION_KEYWORDS = (
    "매출처", "공급처", "공급받", "공급하", "공급계약", "납품", "매입처", "매입",
    "원재료", "원자재", "구매처", "판매처", "거래처", "고객사", "주요 고객", "수주",
    "발주", "협력사", "벤더", "조달", "경쟁사", "경쟁업체", "경쟁회사", "OEM", "ODM",
)

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n{2,}")


def _split_sentences(text: str) -> list[tuple[int, int, str]]:
    """문장 (start, end, text) 목록 — 원문 오프셋 보존 (provenance 역추적, §2.2)."""
    out: list[tuple[int, int, str]] = []
    pos = 0
    for m in _SENT_SPLIT.finditer(text):
        seg = text[pos : m.start()]
        if seg.strip():
            out.append((pos, m.start(), seg))
        pos = m.end()
    tail = text[pos:]
    if tail.strip():
        out.append((pos, len(text), tail))
    return out


def build_name_pattern(session, exclude_norm: set[str] | None = None) -> re.Pattern | None:
    """레지스트리 전 상장사명 + 별칭 표기의 단일 alternation 패턴.

    2자 이상 이름 전부 포함(짧은 약칭도 — 게이트는 후보 수집일 뿐, 판별은 LLM+검증 2패스).
    """
    names: set[str] = set()
    for (nm,) in session.query(CompanyRegistry.name_current).all():
        if nm and len(nm.strip()) >= 2:
            names.add(nm.strip())
    for k, v in NAME_ALIASES.items():
        names.add(k)
        names.add(v)
    if exclude_norm:
        names = {n for n in names if n not in exclude_norm}
    if not names:
        return None
    parts = sorted((re.escape(n) for n in names), key=len, reverse=True)
    return re.compile("|".join(parts))


def _is_candidate(sentence: str, name_pat: re.Pattern | None, self_names: set[str]) -> bool:
    if any(kw in sentence for kw in RELATION_KEYWORDS):
        return True
    if name_pat is None:
        return False
    for m in name_pat.finditer(sentence):
        if m.group(0) not in self_names:
            return True
    return False


def _windows(candidate_idx: list[int], n_sent: int) -> list[tuple[int, int]]:
    """후보 문장 인덱스 → ±WINDOW 구간, 겹치면 병합. [start, end] 폐구간."""
    if not candidate_idx:
        return []
    spans = [(max(0, i - WINDOW), min(n_sent - 1, i + WINDOW)) for i in candidate_idx]
    merged = [spans[0]]
    for s, e in spans[1:]:
        ps, pe = merged[-1]
        if s <= pe + 1:
            merged[-1] = (ps, max(pe, e))
        else:
            merged.append((s, e))
    return merged


def chunk_section(rcept_no: str, section_key: str, corp_code: str, text: str,
                  name_pat: re.Pattern | None, self_names: set[str]) -> list[dict]:
    """한 섹션 → 후보 청크 dict 목록 (결정적 seq)."""
    sents = _split_sentences(text)
    cand = [i for i, (_, _, s) in enumerate(sents) if _is_candidate(s, name_pat, self_names)]
    chunks: list[dict] = []
    seq = 0
    for ws, we in _windows(cand, len(sents)):
        # 1.5K자 캡 — 초과 시 문장 경계에서 분할(후보 문장이 앞쪽에 오도록 순서 유지)
        i = ws
        while i <= we:
            j = i
            total = 0
            while j <= we and total + (sents[j][1] - sents[j][0]) <= MAX_CHUNK_CHARS:
                total += sents[j][1] - sents[j][0]
                j += 1
            j = max(j, i + 1)  # 단일 초장문도 1문장은 담고 하드컷
            start, end = sents[i][0], sents[j - 1][1]
            body = text[start:end]
            if len(body) > MAX_CHUNK_CHARS:
                body = body[:MAX_CHUNK_CHARS]
                end = start + MAX_CHUNK_CHARS
            chunks.append({
                "chunk_id": f"{rcept_no}:{section_key}:{seq}",
                "rcept_no": rcept_no,
                "corp_code": corp_code,
                "section_key": section_key,
                "text": body,
                "char_span": f"{start}-{end}",
                "has_candidate": True,
            })
            seq += 1
            i = j
    return chunks


def run(session=None, section_key: str = SECTION_KEY) -> dict:
    """코퍼스 전량 청킹 → VcChunk·VcPipelineState 적재 (upsert 멱등)."""
    owns = session is None
    if owns:
        session = get_local_session()
    try:
        # 자기 회사명 사전 — registry PK는 corp_code(8자리), report_raw.corp_code8과 동일 체계
        regs = session.query(CompanyRegistry).all()
        by_code8 = {r.corp_code: r for r in regs}
        by_ticker = {r.ticker: r for r in regs if r.ticker}
        name_pat = build_name_pattern(session)

        rdb = sqlite3.connect(str(_REPORTS_DB))
        cur = rdb.cursor()
        cur.execute(
            """select s.rcept_no, r.corp_code8, r.ticker, s.text_md
               from report_section s join report_raw r on r.rcept_no = s.rcept_no
               where s.section_key = ? and s.text_md is not null
               order by s.rcept_no""",
            (section_key,),
        )
        n_sections = n_chunks = 0
        for rcept_no, corp_code8, ticker, text in cur:
            n_sections += 1
            self_reg = by_code8.get(corp_code8) or by_ticker.get(ticker)
            self_names = {self_reg.name_current} if self_reg and self_reg.name_current else set()
            for ch in chunk_section(rcept_no, section_key, corp_code8 or ticker, text,
                                    name_pat, self_names):
                session.merge(VcChunk(**ch))
                session.merge(VcPipelineState(chunk_id=ch["chunk_id"], stage="extract",
                                              status="pending"))
                n_chunks += 1
            if n_sections % 25 == 0:
                session.commit()
        session.commit()
        rdb.close()
        result = {"sections": n_sections, "chunks": n_chunks}
        logger.info(f"청킹 완료: {result}")
        return result
    finally:
        if owns:
            session.close()
