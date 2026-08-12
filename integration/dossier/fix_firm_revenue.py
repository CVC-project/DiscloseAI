"""fix_firm_revenue.py — firm_<t>.json의 오염 매출을 원문 파싱값으로 보정 (FS_PARSE_PLAN P4).

배경: [DECISIONS.md](../DECISIONS.md) **FN-025** — financial `collector.py`가 `이자수익`류를
조건 없이 revenue로 매핑하고 첫 값 우선으로 채워, 이자수익 행이 먼저 오면 진짜 매출을 밀어냈다.
근본 수정은 financial(A) 소관이라 여기서 고치지 않는다. integration은 **표시값만** 보정한다.

원천: `shared/data/reports.db`의 `fs_account_xml` (report 모듈이 원문 XML에서 규칙 파싱 —
G1 대조 55사 × 13계정 **일치율 100.00%**). **read-only**로만 연다.

## 왜 휴리스틱이 아니라 직접 대조인가

FN-025의 "오염 269사"는 `|영업이익| > 매출`로 센 수치인데, 그 규칙은 **매출이 미미한
적자 R&D형**을 대량 오탐한다(fs_parse 실측: 509사에서 129건 중 127건이 오탐).
firm JSON 매출을 파싱값과 **직접 비교**하면 추정이 아니라 실측이 된다.

실행:
  python -m integration.dossier.fix_firm_revenue            # 리포트만
  python -m integration.dossier.fix_firm_revenue --apply    # 보정 적용 (meta.revenue_fix 기록)
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import sqlite3
import sys

if hasattr(sys.stdout, "reconfigure"):  # cp949 콘솔 크래시 방지
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
DB = os.path.join(_ROOT, "shared", "data", "reports.db")
DATA = os.path.join(_HERE, "data")

# 같은 값으로 볼 상대 허용오차. firm JSON은 financial 파이프라인 산출이라 반올림·단위
# 처리가 우리와 다를 수 있다 — 0.5%는 '표기 차이'와 '계정 오매칭'을 충분히 가른다
# (실측 오염은 배수 단위로 어긋난다: 카카오 FY23 0.19조 vs 7.56조).
TOL = 0.005


def parsed_revenue() -> dict[tuple[str, int], tuple[float, str]]:
    """(ticker, fy) → (매출, rcept_no). 연결 우선 → 당기 열 우선 → 표준계정ID 우선."""
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    cur = con.cursor()
    cur.execute(
        "SELECT ticker, fiscal_year, fs_div, col_kind, match_rank, amount, rcept_no "
        "FROM fs_account_xml WHERE account_key='revenue'"
    )
    best: dict[tuple[str, int], tuple] = {}
    out: dict[tuple[str, int], tuple[float, str]] = {}
    for tk, fy, fs_div, col, rank, amt, rcept in cur.fetchall():
        if amt is None:
            continue
        k = (tk, fy)
        score = (0 if fs_div == "CFS" else 1, col, rank or 9)
        if k not in best or score < best[k]:
            best[k] = score
            out[k] = (amt, rcept)
    con.close()
    return out


def financial_tickers() -> set[str]:
    """금융사 — 보정 대상에서 제외한다.

    보험·증권·지주는 top line이 `보험수익`·`수수료수익`·`영업수익`으로 갈리고, firm JSON과
    원문 본표가 **서로 다른 개념**을 매출로 부를 수 있다(IFRS17 전환기 특히). FN-025의
    영향 범위도 '비금융·비지주'로 정의돼 있다 → 여기서 손대지 않는다.
    """
    p = os.path.join(DATA, "company_master.json")
    with open(p, encoding="utf-8") as f:
        return {x["ticker"] for x in json.load(f)["companies"] if x.get("is_financial")}


def classify(firm_v, parsed_v) -> str:
    if firm_v is None:
        return "firm결측"
    if parsed_v is None:
        return "파싱없음"
    if firm_v == 0:
        return "firm0"
    if abs(parsed_v - firm_v) / max(abs(firm_v), 1.0) <= TOL:
        return "일치"
    return "불일치"


def main() -> None:
    ap = argparse.ArgumentParser(description="firm JSON 매출 보정 (FN-025)")
    ap.add_argument("--apply", action="store_true", help="실제로 파일을 고친다")
    ap.add_argument("--limit", type=int, default=40, help="상세 출력 건수")
    ap.add_argument(
        "--include-financial",
        action="store_true",
        help="금융사도 포함 (기본은 제외 — 매출 정의가 다르다)",
    )
    ap.add_argument(
        "--force-all",
        action="store_true",
        help="역방향(firm > 파싱)도 보정 — 기본은 제외",
    )
    args = ap.parse_args()

    pv = parsed_revenue()
    fin = set() if args.include_financial else financial_tickers()
    files = [
        p
        for p in sorted(glob.glob(os.path.join(DATA, "firm_*.json")))
        if os.path.basename(p)[5:-5] not in fin
    ]
    verdict = collections.Counter()
    bad: list[tuple] = []
    fixed_files = 0
    fixed_cells = 0
    print(f"대상 {len(files)}사 (금융 {len(fin)}사 제외)")

    for p in files:
        tk = os.path.basename(p)[5:-5]
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            verdict["읽기실패"] += 1
            continue
        years = d.get("years") or []
        fixes = []
        for y in years:
            fy = y.get("year")
            firm_v = y.get("revenue")
            hit = pv.get((tk, fy))
            parsed_v = hit[0] if hit else None
            v = classify(firm_v, parsed_v)
            verdict[v] += 1
            if v == "불일치":
                bad.append((tk, fy, firm_v, parsed_v, y.get("operating_income")))
                # ⚠️ **firm < 파싱**(= 작은 값이 매출 자리를 차지함)일 때만 고친다.
                # 그게 FN-025 오염의 지문이다. 반대 방향은 우리 파싱이 틀렸을 가능성이
                # 있어(별도/연결 혼동·표 변형) 손대지 않고 리포트만 한다 — 보정이
                # 원본보다 나쁜 값을 심는 일은 없어야 한다.
                if abs(firm_v) < abs(parsed_v) or args.force_all:
                    fixes.append((y, fy, firm_v, parsed_v, hit[1]))
        if args.apply and fixes:
            log = d.setdefault("meta", {}).setdefault("revenue_fix", [])
            for y, fy, firm_v, parsed_v, rcept in fixes:
                y["revenue"] = parsed_v
                log.append(
                    {
                        "year": fy,
                        "from": firm_v,
                        "to": parsed_v,
                        "source": "fs_account_xml",
                        "rcept_no": rcept,
                        "reason": "FN-025 이자수익 오매핑 — 원문 XML 본표 파싱값으로 대체",
                    }
                )
                fixed_cells += 1
            with open(p, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
            fixed_files += 1

    print("=" * 72)
    print(f"firm JSON {len(files)}개 · (기업×연도) 셀 {sum(verdict.values())}")
    for k, n in verdict.most_common():
        print(f"  {k:<10} {n:>7}")
    print("=" * 72)
    firms = {b[0] for b in bad}
    print(f"\n[불일치] {len(bad)}셀 · {len(firms)}사")
    # 오염의 지문: firm 매출이 파싱값보다 **작다**(이자수익이 매출을 밀어냄)
    smaller = [b for b in bad if b[2] is not None and b[3] and abs(b[2]) < abs(b[3])]
    larger = [b for b in bad if b not in smaller]
    print(
        f"  firm < 파싱 (오염 지문) : {len(smaller)}셀 · {len({b[0] for b in smaller})}사"
    )
    print(
        f"  firm > 파싱             : {len(larger)}셀 · {len({b[0] for b in larger})}사"
    )
    print(f"\n[상세 상위 {args.limit}]")
    for tk, fy, fv, pvv, op in sorted(bad, key=lambda b: -(abs(b[3] or 0)))[
        : args.limit
    ]:
        ratio = (pvv / fv) if fv else float("inf")
        print(
            f"  {tk} FY{fy}  firm={fv:>20,.0f}  파싱={pvv:>20,.0f}  배율={ratio:>8.1f}x"
            f"  영업이익={op if op is None else format(op, ',.0f')}"
        )
    if args.apply:
        print(
            f"\n적용: 파일 {fixed_files}개 · 셀 {fixed_cells}개 보정 (meta.revenue_fix 기록)"
        )
    else:
        print("\n(리포트 전용 — 실제 보정은 --apply)")


if __name__ == "__main__":
    main()
