"""evaluate.py 단위 테스트 — §3.7 튜플 채점·경계 사례."""

from modules.relation.valuechain.evaluate import (
    ANON, bootstrap_ci, evaluate, micro_prf, relation_tuple, tuple_set)


def _rel(cp, d="customer", s="active", anon=False):
    return {"counterparty": cp, "anonymous": anon, "direction": d, "status": s,
            "evidence": "e", "sector_hint": None}


def test_tuple_normalizes_name_variants():
    assert relation_tuple(_rel("(주)삼성전자")) == relation_tuple(_rel("삼성전자"))


def test_anonymous_maps_to_anon_token():
    assert relation_tuple(_rel(None, anon=True))[0] == ANON


def test_micro_prf_counts():
    pairs = [
        (tuple_set([_rel("A"), _rel("B")]), tuple_set([_rel("A")])),   # TP1 FP1
        (tuple_set([]), tuple_set([_rel("C")])),                        # FN1
    ]
    out = micro_prf(pairs)
    assert (out["tp"], out["fp"], out["fn"]) == (1, 1, 1)
    assert abs(out["f1"] - 0.5) < 1e-9


def test_perfect_and_empty_cases():
    perfect = [(tuple_set([_rel("A")]), tuple_set([_rel("A")]))]
    assert micro_prf(perfect)["f1"] == 1.0
    # 둘 다 빈 관계(무관계 정답 맞춤) — TP 없음이지만 오류도 없음 → P/R 0 정의 확인
    both_empty = [(set(), set())]
    assert micro_prf(both_empty)["fp"] == 0 and micro_prf(both_empty)["fn"] == 0


def test_duplicate_relations_fold_to_one():
    assert len(tuple_set([_rel("A"), _rel("A")])) == 1


def test_bootstrap_ci_bounds_contain_point():
    pairs = [(tuple_set([_rel("A")]), tuple_set([_rel("A")])) for _ in range(20)]
    ci = bootstrap_ci(pairs, n_resample=200, seed=1)
    assert ci["f1_lo"] == 1.0 and ci["f1_hi"] == 1.0


def test_evaluate_scores_only_gold_chunks():
    pred = {"c1": [_rel("A")], "c2": [_rel("B")], "밖": [_rel("Z")]}
    gold = {"c1": [_rel("A")], "c2": []}
    out = evaluate(pred, gold, seed=1)
    assert out["n_chunks"] == 2
    assert out["tp"] == 1 and out["fp"] == 1 and out["fn"] == 0


def test_direction_confusion_detects_swap():
    pred = {"c1": [_rel("A", d="supplier")]}
    gold = {"c1": [_rel("A", d="customer")]}
    out = evaluate(pred, gold, seed=1)
    assert any("customer" in k and "supplier" in k
               for k in out["direction_confusion"])
