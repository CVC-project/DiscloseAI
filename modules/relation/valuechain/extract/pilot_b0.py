"""B0 제로샷 파일럿 드라이버 (valuechain/PLAN.md §4.2 B0 · B0_CANDIDATES ⓒ 채움).

대기 큐(vc_pipeline_state extract=pending)에서 10사 표본 청크를 뽑아
Qwen3-32B 제로샷으로 §3.2 추출 → §3.5 2패스 검증 → 방어층 → T2 적재까지 실행.

- 표본은 seed 고정 결정적 추출 (회사 10 × 청크 ≤10 = ≤100청크).
- ⚠️ 파일럿은 파이프라인 큐를 소비하지 않는다(pending 유지) — 본 추출은 B 하네스
  수렴 후 확정 어댑터(extractor_ver 상이)로 전량 실행하며, 그때 이 파일럿 엣지는
  동일 UNIQUE 키 upsert로 자연 갱신된다.
- 검수용 전 레코드(기각 사유 포함)는 modules/relation/data/vc_pilot_zeroshot.jsonl 저장
  (CPA 스팟체크·오류 유형 분석 입력).

실행: python -m modules.relation.valuechain.extract.pilot_b0 [--companies 10] [--per-company 10]
"""

from __future__ import annotations

import argparse
import json
import random
import sqlite3
import time
from collections import Counter
from pathlib import Path

from modules.relation.storage.db import get_local_session
from modules.relation.storage.models import CompanyRegistry, VcChunk, VcPipelineState
from modules.relation.valuechain.extract import llm_extract

_SEED = 42
_OUT_PATH = Path(__file__).resolve().parents[2] / "data" / "vc_pilot_zeroshot.jsonl"
_REPORTS_DB = Path(__file__).resolve().parents[4] / "shared" / "data" / "reports.db"


def sample_chunks(session, n_companies: int, per_company: int) -> list[VcChunk]:
    """pending 청크 보유 기업에서 결정적(seed) 표본 — 기업 n × 청크 ≤k."""
    rows = (
        session.query(VcChunk.corp_code)
        .join(VcPipelineState, VcPipelineState.chunk_id == VcChunk.chunk_id)
        .filter(VcPipelineState.stage == "extract", VcPipelineState.status == "pending")
        .distinct()
        .all()
    )
    corps = sorted(r[0] for r in rows)
    rng = random.Random(_SEED)
    picked = rng.sample(corps, min(n_companies, len(corps)))

    chunks: list[VcChunk] = []
    for corp in picked:
        corp_chunks = (
            session.query(VcChunk)
            .filter(VcChunk.corp_code == corp)
            .order_by(VcChunk.chunk_id)
            .all()
        )
        chunks.extend(rng.sample(corp_chunks, min(per_company, len(corp_chunks))))
    return chunks


def fiscal_year_map(rcept_nos: set[str]) -> dict[str, int | None]:
    con = sqlite3.connect(f"file:{_REPORTS_DB}?mode=ro", uri=True)
    try:
        marks = ",".join("?" * len(rcept_nos))
        cur = con.execute(
            f"SELECT rcept_no, fiscal_year FROM report_raw WHERE rcept_no IN ({marks})",
            tuple(rcept_nos),
        )
        return dict(cur.fetchall())
    finally:
        con.close()


def main(n_companies: int = 10, per_company: int = 10, max_workers: int = 8) -> dict:
    session = get_local_session()
    try:
        chunks = sample_chunks(session, n_companies, per_company)
        anchor_names = {
            r.corp_code: r.name_current
            for r in session.query(CompanyRegistry).filter(
                CompanyRegistry.corp_code.in_({c.corp_code for c in chunks})
            )
        }
        as_of = fiscal_year_map({c.rcept_no for c in chunks})

        print(f"표본: {len({c.corp_code for c in chunks})}사 · {len(chunks)}청크 "
              f"(seed={_SEED}) — 패스1 {len(chunks)}회 + 패스2(관계 수만큼) 호출 예정")
        t0 = time.time()
        records, counters = llm_extract.run_batch(
            session, chunks, anchor_names, as_of, max_workers=max_workers
        )
        elapsed = time.time() - t0

        _OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_OUT_PATH, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        verdicts = Counter(r["verdict"] for r in records)
        summary = {
            "elapsed_sec": round(elapsed, 1),
            "counters": counters,
            "verdicts": dict(verdicts),
            "records_path": str(_OUT_PATH),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return summary
    finally:
        session.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--companies", type=int, default=10)
    ap.add_argument("--per-company", type=int, default=10)
    ap.add_argument("--max-workers", type=int, default=8)
    args = ap.parse_args()
    main(args.companies, args.per_company, args.max_workers)
