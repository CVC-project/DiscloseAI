"""P/R/F1 평가 하네스 (valuechain/PLAN.md §3.7 3행 비교표, §4.6 게이트).

지표 정의(§3.7 프로토콜 — 이 정의를 벗어난 비교는 무효):
  - 튜플 = (정규화 counterparty, direction, status). 익명(counterparty 없음)은
    "∅anon"으로 정규화 — 익명 관계도 존재 자체는 채점 대상.
  - 청크 내 중복 튜플은 set으로 접음(동일 관계 반복 서술은 1회).
  - micro: 전 청크 TP/FP/FN 합산 → P/R/F1.
  - 부트스트랩 CI: 청크 단위 재표집(§3.7 "점추정 단독 판정 금지").

게이트 판정은 이 모듈 산출값만 근거로 한다(§0.5 — 주관 판정 금지).
"""

from __future__ import annotations

import random
from collections import Counter

from modules.relation.common.names import normalize_company_name

ANON = "∅anon"


def relation_tuple(rel: dict) -> tuple[str, str, str]:
    """§3.2 relation dict → 채점 튜플."""
    cp = rel.get("counterparty")
    norm = normalize_company_name(cp) if cp else ""
    return (norm or ANON, rel.get("direction") or "", rel.get("status") or "")


def tuple_set(relations: list[dict]) -> set[tuple[str, str, str]]:
    return {relation_tuple(r) for r in relations or []}


def micro_prf(pairs: list[tuple[set, set]]) -> dict:
    """pairs = [(pred_set, gold_set)] per chunk → micro P/R/F1 + TP/FP/FN."""
    tp = fp = fn = 0
    for pred, gold in pairs:
        tp += len(pred & gold)
        fp += len(pred - gold)
        fn += len(gold - pred)
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": p, "recall": r, "f1": f1, "tp": tp, "fp": fp, "fn": fn}


def bootstrap_ci(pairs: list[tuple[set, set]], n_resample: int = 1000,
                 seed: int = 42, alpha: float = 0.05) -> dict:
    """청크 단위 부트스트랩 → F1 95% CI (percentile)."""
    rng = random.Random(seed)
    if not pairs:
        return {"f1_lo": 0.0, "f1_hi": 0.0}
    f1s = []
    for _ in range(n_resample):
        sample = [pairs[rng.randrange(len(pairs))] for _ in pairs]
        f1s.append(micro_prf(sample)["f1"])
    f1s.sort()
    lo = f1s[int((alpha / 2) * n_resample)]
    hi = f1s[min(n_resample - 1, int((1 - alpha / 2) * n_resample))]
    return {"f1_lo": lo, "f1_hi": hi}


def direction_confusion(pairs: list[tuple[set, set]]) -> Counter:
    """상대는 맞았는데 (direction,status)가 어긋난 사례 유형 집계 — B5 오류분석 입력."""
    conf: Counter = Counter()
    for pred, gold in pairs:
        gold_by_cp: dict[str, list[tuple[str, str]]] = {}
        for cp, d, s in gold:
            gold_by_cp.setdefault(cp, []).append((d, s))
        for cp, d, s in pred:
            if (cp, d, s) in gold:
                continue
            for gd, gs in gold_by_cp.get(cp, []):
                if (d, s) != (gd, gs):
                    conf[f"{gd}/{gs}→{d}/{s}"] += 1
    return conf


def evaluate(pred_by_chunk: dict[str, list[dict]],
             gold_by_chunk: dict[str, list[dict]],
             seed: int = 42) -> dict:
    """chunk_id → relations 두 사전을 받아 §3.7 지표 일괄 산출.

    gold에 있는 청크만 채점(gold 없는 청크의 pred는 무시 — 평가셋 밖).
    """
    pairs = [
        (tuple_set(pred_by_chunk.get(cid, [])), tuple_set(gold))
        for cid, gold in sorted(gold_by_chunk.items())
    ]
    out = micro_prf(pairs)
    out.update(bootstrap_ci(pairs, seed=seed))
    out["n_chunks"] = len(pairs)
    out["direction_confusion"] = dict(direction_confusion(pairs).most_common(10))
    return out
