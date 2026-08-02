"""하네스 A 데이터셋 구축 (valuechain/PLAN.md §3.3·§4.1 — A1 샘플링 ~ A5 골드 분리).

흐름:
  A1  sample_split(): vc_chunk에서 층화 표본 — 시장(2)×섹터×패턴(3) 비례 배분, seed 결정적.
      패턴 근사: named_kw(타사명+관계어휘) | named_only(타사명만) | kw_only(관계어휘만)
      — §3.3 "명시/익명/무관계" 층의 CPU 근사(정확 판정은 라벨 후에만 가능).
  A2  write_batches(): 교사(Claude 서브에이전트) 입력 배치 JSONL 생성.
      ⚠️ 계획상 교사=Claude API였으나 환경에 키 부재 → galaxy 선례(주석 직접 판독)대로
      Claude Code 서브에이전트가 교사 역할. 학생 채점 비관여 원칙(§0.5)은 불변.
  A3  collect_outputs(): 패스1·2 산출 검증(스키마·evidence exact-match) + 자기일치 집계.
  A5  assemble(): {split}.jsonl + CPA 검수 큐(cpa_review_{split}.jsonl) 산출.

전 산출물은 modules/relation/data/vc_dataset/ — 파일 존재 = 진행 상태(재개 멱등).
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "vc_dataset"
BATCH_SIZE = 30
SEED = 7

DIRECTIONS = {"customer", "supplier", "competitor", "raw_material"}
STATUSES = {"active", "past", "planned"}


def _pattern(text: str, name_pat: re.Pattern | None, self_names: set[str],
             kw: tuple[str, ...]) -> str:
    has_kw = any(k in text for k in kw)
    has_name = False
    if name_pat is not None:
        for m in name_pat.finditer(text):
            if m.group(0) not in self_names:
                has_name = True
                break
    if has_name and has_kw:
        return "named_kw"
    if has_name:
        return "named_only"
    return "kw_only"


def sample_split(session, n_val: int = 400, n_test: int = 500,
                 exclude_chunk_ids: set[str] | None = None, seed: int = SEED,
                 prepool: int = 15000) -> dict:
    """층화 표본 → {'val': [chunk dict...], 'test': [...]} (겹침 없음, 결정적).

    815K 전량 정규식·메모리 부하 회피: chunk_id 해시 기반 결정적 프리풀(~15K)을
    먼저 뽑고, 그 풀에만 패턴 판정을 수행해 층화한다(표본 900에 통계적으로 충분).
    """
    import hashlib

    from modules.relation.storage.models import CompanyRegistry, VcChunk
    from modules.relation.valuechain.chunker.pipeline import (
        RELATION_KEYWORDS, build_name_pattern)

    regs = {r.corp_code: r for r in session.query(CompanyRegistry).all()}
    name_pat = build_name_pattern(session)
    exclude = exclude_chunk_ids or set()

    ids = [r[0] for r in session.query(VcChunk.chunk_id).all()
           if r[0] not in exclude]
    def _h(cid: str) -> int:
        return int(hashlib.md5(f"{seed}:{cid}".encode()).hexdigest()[:8], 16)
    pool_ids = set(sorted(ids, key=_h)[:prepool])

    strata: dict[tuple, list[dict]] = {}
    for ch in (session.query(VcChunk)
               .filter(VcChunk.chunk_id.in_(pool_ids)).yield_per(1000)):
        reg = regs.get(ch.corp_code)
        market = reg.market if reg else "?"
        sector = (reg.sector_id if reg else None) or "?"
        self_names = {reg.name_current} if reg and reg.name_current else set()
        pat = _pattern(ch.text, name_pat, self_names, RELATION_KEYWORDS)
        strata.setdefault((market, sector, pat), []).append({
            "chunk_id": ch.chunk_id, "corp_code": ch.corp_code,
            "anchor": (reg.name_current if reg else ch.corp_code),
            "market": market, "sector": sector, "pattern": pat,
            "rcept_no": ch.rcept_no, "text": ch.text,
        })

    rng = random.Random(seed)
    total = sum(len(v) for v in strata.values())
    need = n_val + n_test
    picked: list[dict] = []
    # 비례 배분(최소 1) 후 부족분은 큰 층부터 보충 — 결정적 순회
    keys = sorted(strata.keys())
    for k in keys:
        pool = sorted(strata[k], key=lambda c: c["chunk_id"])
        quota = max(1, round(len(pool) / total * need))
        picked.extend(rng.sample(pool, min(quota, len(pool))))
    rng.shuffle(picked)
    picked = picked[:need]
    while len(picked) < need:  # 이론상 도달 어려움 — 안전망
        k = max(keys, key=lambda k: len(strata[k]))
        extra = [c for c in strata[k] if c not in picked]
        if not extra:
            break
        picked.append(extra[0])
    return {"val": picked[:n_val], "test": picked[n_val:n_val + n_test]}


def write_batches(split_name: str, chunks: list[dict],
                  batch_size: int = BATCH_SIZE) -> list[Path]:
    bdir = DATA_DIR / "batches"
    bdir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(0, len(chunks), batch_size):
        p = bdir / f"{split_name}_{i // batch_size:03d}.input.jsonl"
        with open(p, "w", encoding="utf-8") as f:
            for c in chunks[i : i + batch_size]:
                f.write(json.dumps(
                    {k: c[k] for k in ("chunk_id", "anchor", "text")},
                    ensure_ascii=False) + "\n")
        paths.append(p)
    return paths


def validate_output_line(rec: dict, text_by_chunk: dict[str, str]) -> list[str]:
    """산출 레코드 1건 검증 — 오류 목록 반환(빈 리스트=정상)."""
    errs = []
    cid = rec.get("chunk_id")
    if cid not in text_by_chunk:
        return [f"unknown chunk_id {cid}"]
    for i, rel in enumerate(rec.get("relations", [])):
        if rel.get("direction") not in DIRECTIONS:
            errs.append(f"rel{i}: direction={rel.get('direction')}")
        if rel.get("status") not in STATUSES:
            errs.append(f"rel{i}: status={rel.get('status')}")
        ev = (rel.get("evidence") or "").strip()
        if not ev or ev not in text_by_chunk[cid]:
            errs.append(f"rel{i}: evidence exact-match 실패")
        if not rel.get("anonymous") and not rel.get("counterparty"):
            errs.append(f"rel{i}: counterparty 없음 + anonymous=false")
    return errs


def collect_outputs(split_name: str, chunks: list[dict]) -> dict:
    """패스1·2 output 파일 수합 → chunk_id별 {pass1, pass2, agree, errors}."""
    from modules.relation.valuechain.evaluate import tuple_set

    text_by_chunk = {c["chunk_id"]: c["text"] for c in chunks}
    bdir = DATA_DIR / "batches"
    by_pass: dict[int, dict[str, list]] = {1: {}, 2: {}}
    errors: dict[str, list[str]] = {}
    for pno in (1, 2):
        for p in sorted(bdir.glob(f"{split_name}_*.pass{pno}.output.jsonl")):
            for ln in open(p, encoding="utf-8"):
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    rec = json.loads(ln)
                except json.JSONDecodeError:
                    errors.setdefault(str(p.name), []).append("JSON 파싱 실패 라인")
                    continue
                errs = validate_output_line(rec, text_by_chunk)
                if errs:
                    errors.setdefault(rec.get("chunk_id") or p.name, []).extend(errs)
                by_pass[pno][rec.get("chunk_id")] = rec.get("relations", [])

    merged = {}
    for c in chunks:
        cid = c["chunk_id"]
        p1, p2 = by_pass[1].get(cid), by_pass[2].get(cid)
        agree = (p1 is not None and p2 is not None
                 and tuple_set(p1) == tuple_set(p2))
        merged[cid] = {"pass1": p1, "pass2": p2, "agree": agree}
    n_both = sum(1 for v in merged.values() if v["pass1"] is not None and v["pass2"] is not None)
    n_agree = sum(1 for v in merged.values() if v["agree"])
    return {"merged": merged, "errors": errors,
            "labeled_both": n_both, "agree": n_agree,
            "agree_rate": (n_agree / n_both) if n_both else 0.0}


def assemble(split_name: str, chunks: list[dict], collected: dict) -> Path:
    """최종 {split}.jsonl — CPA 검수 입력(두 패스·일치 여부·본문 포함)."""
    out = DATA_DIR / f"{split_name}.jsonl"
    merged = collected["merged"]
    with open(out, "w", encoding="utf-8") as f:
        for c in chunks:
            m = merged[c["chunk_id"]]
            f.write(json.dumps({
                **{k: c[k] for k in ("chunk_id", "anchor", "corp_code", "market",
                                     "sector", "pattern", "rcept_no", "text")},
                "pass1": m["pass1"], "pass2": m["pass2"], "agree": m["agree"],
                "teacher": m["pass1"] if m["agree"] else None,  # 불일치=CPA 판정 대상
            }, ensure_ascii=False) + "\n")
    return out
