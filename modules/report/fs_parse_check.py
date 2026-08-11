"""fs_parse_check.py — G1 게이트: fs_account(정답지) vs fs_account_xml(원문 파싱) 대조.

정답지는 `fs_enrich.py`가 DART API(fnlttSinglAcntAll)로 받은 55사 × 5개년. **읽기 전용**.
양쪽에 **같은 선택기**(`fs_parse.pick_account`)를 적용해야 대조가 성립한다 —
정답지에서 계정을 다른 규칙으로 고르면 파서 충실도가 아니라 규칙 차이를 재게 된다.

- G1 정확도: 교집합에서 값 일치율 (허용오차 0, 원 단위 정수 비교)
- G2 커버리지: 계정별 결측률
- G3 sanity: |영업이익| > 매출 · 매출 급락후급반등 (FN-023 R14·R15)

실행: `python -m modules.report.fs_parse_check`
"""

from __future__ import annotations

import collections
import sys

from .db import get_local_session
from .fs_parse import ACCOUNT_KEYS, pick_account
from .models import FsAccount, FsAccountXml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _gt_values(sess) -> dict[tuple[str, int, str], float]:
    """정답지 — (ticker, fy)별 전 계정 행에 pick_account 적용."""
    rows = (
        sess.query(FsAccount)
        .order_by(FsAccount.ticker, FsAccount.fiscal_year, FsAccount.id)
        .all()
    )
    by_key: dict[tuple[str, int], list] = collections.defaultdict(list)
    for r in rows:
        by_key[(r.ticker, r.fiscal_year)].append(r)
    out = {}
    for (tk, fy), rs in by_key.items():
        for key in ACCOUNT_KEYS:
            hit, _rank = pick_account(rs, key)
            if hit is not None:
                out[(tk, fy, key)] = hit.amount
    return out


def _parsed_values(sess, tickers: set[str]) -> dict[tuple[str, int, str], dict]:
    """파싱값 — 연결(CFS) 우선, 그 다음 **당기 열 우선**(전전기는 재작성값일 수 있다)."""
    rows = (
        sess.query(FsAccountXml)
        .filter(FsAccountXml.ticker.in_(tickers))
        .all()
    )
    best: dict[tuple[str, int, str], tuple] = {}
    for r in rows:
        k = (r.ticker, r.fiscal_year, r.account_key)
        score = (0 if r.fs_div == "CFS" else 1, r.col_kind, r.match_rank or 9)
        cur = best.get(k)
        if cur is None or score < cur[0]:
            best[k] = (score, r)
    return {k: {"amount": v[1].amount, "row": v[1]} for k, v in best.items()}


def classify(gt: float, pv: float) -> str:
    gi, pi = round(gt), round(pv)
    if gi == pi:
        return "일치"
    if gi == 0 or pi == 0:
        return "한쪽0"
    ratio = pi / gi
    for scale, label in ((1e3, "×1000"), (1e-3, "÷1000"), (1e6, "×1e6"), (1e-6, "÷1e6")):
        if abs(ratio - scale) < scale * 1e-6:
            return f"단위{label}"
    if abs(ratio + 1) < 1e-9:
        return "부호반대"
    d = abs(pi - gi) / max(abs(gi), 1)
    if d < 0.001:
        return "근사(≤0.1%)"
    if d < 0.05:
        return "근사(≤5%)"
    return "값상이(>5%)"


def main() -> None:
    sess = get_local_session()
    gt = _gt_values(sess)
    tickers = {k[0] for k in gt}
    pv = _parsed_values(sess, tickers)
    sess.close()

    # 정답지가 가진 (ticker, fy)만 대조 대상
    gt_cells = set(gt)
    inter = [k for k in gt_cells if k in pv]
    only_gt = [k for k in gt_cells if k not in pv]

    verdict = collections.Counter()
    by_acct = collections.defaultdict(collections.Counter)
    detail = []
    for k in inter:
        v = classify(gt[k], pv[k]["amount"])
        verdict[v] += 1
        by_acct[k[2]][v] += 1
        if v != "일치":
            detail.append((k, gt[k], pv[k]["amount"], v, pv[k]["row"]))
    for k in only_gt:
        verdict["파싱미발견"] += 1
        by_acct[k[2]]["파싱미발견"] += 1

    total = len(gt_cells)
    match = verdict["일치"]
    print("=" * 74)
    print(f"G1 — 정답지 셀 {total} · 교집합 {len(inter)} · 일치 {match}")
    print(f"   교집합 기준 일치율 : {match/max(len(inter),1)*100:.2f}%")
    print(f"   정답지 전체 기준   : {match/max(total,1)*100:.2f}%  (미발견 {verdict['파싱미발견']} 포함)")
    print("=" * 74)
    print("\n[불일치 유형]")
    for v, n in verdict.most_common():
        if v == "일치":
            continue
        print(f"  {v:>14} : {n:5d}  ({n/max(total,1)*100:5.2f}%)")

    print("\n[계정별]")
    hdr = ["일치", "파싱미발견", "값상이(>5%)", "근사(≤5%)", "근사(≤0.1%)", "부호반대", "한쪽0"]
    print(f"  {'account':<20} {'정답지':>6} {'일치':>6} {'일치율':>7}  " + " ".join(f"{h:>11}" for h in hdr[1:]))
    for key in ACCOUNT_KEYS:
        c = by_acct[key]
        tot = sum(c.values())
        if not tot:
            continue
        rate = c["일치"] / tot * 100
        print(f"  {key:<20} {tot:>6} {c['일치']:>6} {rate:>6.2f}%  "
              + " ".join(f"{c[h]:>11}" for h in hdr[1:]))

    print(f"\n[불일치 상세 — 상위 40 / 총 {len(detail)+verdict['파싱미발견']}]")
    detail.sort(key=lambda x: (x[3], x[0]))
    for (tk, fy, key), g, p, v, row in detail[:40]:
        print(f"  {tk} FY{fy} {key:<20} {v:<12} 정답={g:>20,.0f} 파싱={p:>20,.0f} "
              f"[{row.fs_div}/{row.sj_div}/col{row.col_kind}/r{row.match_rank}/{row.account_nm}]")

    miss = collections.Counter()
    for tk, fy, key in only_gt:
        miss[(key, fy)] += 1
    if only_gt:
        print(f"\n[파싱 미발견 — 계정×연도 상위 20 / 총 {len(only_gt)}]")
        for (key, fy), n in miss.most_common(20):
            print(f"  {key:<20} FY{fy}: {n}")

    # G2 커버리지 — 파싱값이 (기업, 연도)를 얼마나 덮는가
    print("\n[G2 커버리지 — fs_account_xml]")
    s2 = get_local_session()
    allrows = s2.query(FsAccountXml).all()
    s2.close()
    firms = {r.ticker for r in allrows}
    cells = {(r.ticker, r.fiscal_year, r.account_key) for r in allrows}
    fy_firm = collections.defaultdict(set)
    for r in allrows:
        fy_firm[r.fiscal_year].add(r.ticker)
    print(f"  기업 {len(firms)} · 행 {len(allrows)} · (기업×연도×계정) {len(cells)}")
    print("  연도별 기업수:", {fy: len(v) for fy, v in sorted(fy_firm.items())})
    acct_cov = collections.Counter(k[2] for k in cells)
    print("  계정별 (기업×연도) 셀수:")
    for key in ACCOUNT_KEYS:
        print(f"    {key:<20} {acct_cov[key]:>5}")

    # G3 sanity — 파싱값 자체가 물리적으로 말이 되는지
    print("\n[G3 sanity — 파싱값]")
    bad_op = [(tk, fy) for (tk, fy, k) in pv if k == "revenue"
              and (tk, fy, "operating_income") in pv
              and pv[(tk, fy, "revenue")]["amount"]
              and abs(pv[(tk, fy, "operating_income")]["amount"]) > abs(pv[(tk, fy, "revenue")]["amount"])]
    print(f"  |영업이익| > |매출| : {len(bad_op)}건 {sorted(bad_op)[:10]}")
    rev = collections.defaultdict(dict)
    for (tk, fy, k), d in pv.items():
        if k == "revenue":
            rev[tk][fy] = d["amount"]
    dips = []
    for tk, ys in rev.items():
        for fy in sorted(ys):
            a, b, c = ys.get(fy - 1), ys.get(fy), ys.get(fy + 1)
            if a and b and c and a > 0 and c > 0 and b < a * 0.5 and c > b * 2:
                dips.append((tk, fy))
    print(f"  매출 급락후급반등 : {len(dips)}건 {dips[:10]}")


if __name__ == "__main__":
    main()
