"""'주목할 점' 카드(LLM 산출)를 검증하고 galaxy_lite_<t>.json에 주입한다.

설계 정본: GALAXY_LITE_PLAN.md §7 — D7("LLM은 숫자를 만들지 않는다") 축소판.
- 카드 산문의 모든 [브래킷] 수치는 fact-sheet(주석 원문 추출) 또는 lite series에서
  **코드가 재도출**할 수 있어야 한다. 재도출 실패 = 그 카드 반려.
- 원문 대조는 코드가 DB에서 수행하므로 검증에 드는 LLM 토큰은 0.

입력:
    data/facts_lite_<t>.json   — note-extractor 산출 fact-sheet (facts[], segments[])
    data/notes_lite_<t>.json   — 카드 원고 (아래 스키마)
출력:
    data/galaxy_lite_<t>.json 의 notes[] 갱신

카드 원고 스키마:
    { "id","title","what":[...],"why":[...],"src":{"note_no","title"},
      "nums":[ {"chip":"1.79조","check":{...}} ... ] }
  check.kind:
    fact    {key, fmt}                     — fact 1건을 fmt로 포맷한 값과 일치
    ratio   {num, den, fmt, minus_one}     — fact 두 건의 비율(-1 옵션)을 퍼센트로
    share   {num, den, fmt}                — 구성비
    series  {key, year, fmt}               — lite series 값
    norm    {key, year|last, fmt}          — 정규화 값
    literal —                              — 연도·라벨 등 수치 검증 면제(FY23 등)

Usage:
    python integration/dossier/inject_lite_notes.py 009150
    python integration/dossier/inject_lite_notes.py 009150 --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

# 윈도우 콘솔(cp949)에서 em dash 등이 섞이면 print가 크래시해 **게이트 PASS가 FAIL로 보인다**(FN-001 계보).
# 카드 제목·주석 원문은 우리가 통제할 수 없으므로 출력 스트림 자체를 UTF-8로 고정한다.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DATA = HERE / "data"
REPORTS_DB = ROOT / "shared" / "data" / "reports.db"

TOL = 0.011  # 표시 반올림 허용 오차 (1.1%)


# ---------- 포맷터 (build_galaxy_lite.py와 동일 규칙) ----------


def fmt_jo(v: float) -> str:
    return f"{v / 1e12:.2f}조"


def fmt_jo1(v: float) -> str:
    return f"{v / 1e12:.1f}조"


def fmt_eok(v: float) -> str:
    return f"{round(v / 1e8):,}억"


def fmt_pct(v: float) -> str:
    return f"{v:.1f}%"


def fmt_pct0(v: float) -> str:
    return f"{round(v)}%"


def fmt_num1(v: float) -> str:
    return f"{v:.1f}"


FMT = {"jo": fmt_jo, "jo1": fmt_jo1, "eok": fmt_eok, "pct": fmt_pct, "pct0": fmt_pct0, "num1": fmt_num1}


def parse_chip(chip: str) -> float | None:
    """'1.79조' / '9,133억' / '28.9%' -> 숫자 (비교용)."""
    s = chip.replace(",", "").strip()
    m = re.match(r"^(-?\d+(?:\.\d+)?)\s*(조|억|%|%p)?$", s)
    if not m:
        return None
    v = float(m.group(1))
    unit = m.group(2)
    if unit == "조":
        return v * 1e12
    if unit == "억":
        return v * 1e8
    return v


# ---------- 검증 ----------


def resolve(check: dict[str, Any], facts: dict[str, float], lite: dict[str, Any]) -> tuple[float | None, str]:
    """(기대값, 포맷된 기대 문자열)"""
    kind = check.get("kind")
    fmt = FMT.get(check.get("fmt", "jo"), fmt_jo)

    def year_idx(y: str | None) -> int:
        if not y or y == "last":
            return len(lite["years"]) - 1
        return lite["years"].index(y)

    if kind == "fact":
        v = facts.get(check["key"])
        return (None, "") if v is None else (v, fmt(v))
    if kind == "ratio":
        a, b = facts.get(check["num"]), facts.get(check["den"])
        if a is None or b in (None, 0):
            return None, ""
        r = (a / b - 1) * 100 if check.get("minus_one") else (a / b) * 100
        return r, fmt(r)
    if kind == "share":
        a, b = facts.get(check["num"]), facts.get(check["den"])
        if a is None or b in (None, 0):
            return None, ""
        r = a / b * 100
        return r, fmt(r)
    if kind == "series":
        vals = lite["series"].get(check["key"], [])
        i = year_idx(check.get("year"))
        v = vals[i] if i < len(vals) else None
        return (None, "") if v is None else (v, fmt(v))
    if kind == "norm":
        vals = lite["norm"].get(check["key"], [])
        i = year_idx(check.get("year"))
        v = vals[i] if i < len(vals) else None
        return (None, "") if v is None else (v, fmt(v))
    if kind == "std_norm":  # 표준(골든)의 정규화 값 — 표준 대비 서술의 근거
        vals = lite["std_norm"].get(check["key"], [])
        i = len(lite["std_years"]) - 1 if check.get("year", "last") == "last" else lite["std_years"].index(check["year"])
        v = vals[i] if i < len(vals) else None
        return (None, "") if v is None else (v, fmt(v))
    return None, ""


def verify_card(card: dict[str, Any], facts: dict[str, float], lite: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    prose = " ".join(card.get("what", []) + card.get("why", []) + [card.get("title", "")])
    chips = re.findall(r"\[([^\]]+)\]", prose)
    declared = {n["chip"]: n for n in card.get("nums", [])}

    # 1) 산문의 모든 칩이 nums에 선언돼 있는가
    for c in chips:
        if c not in declared:
            errs.append(f"미선언 칩 [{c}] — nums에 근거가 없어요")

    # 2) 선언된 칩이 fact/series에서 재도출되는가
    for chip, spec in declared.items():
        check = spec.get("check", {})
        if check.get("kind") == "literal":
            continue
        want, want_s = resolve(check, facts, lite)
        if want is None:
            errs.append(f"[{chip}] 근거 해석 실패 ({check})")
            continue
        got = parse_chip(chip)
        if got is None:
            errs.append(f"[{chip}] 숫자 파싱 실패")
            continue
        denom = max(abs(want), 1e-9)
        if abs(got - want) / denom > TOL:
            errs.append(f"[{chip}] ≠ 재도출값 {want_s} (근거 {check.get('kind')})")

    # 3) 문체 게이트 (STYLE_GUIDE A7 — 격식체 금지)
    for ln in card.get("what", []) + card.get("why", []):
        t = ln.rstrip()
        if re.search(r"(다|음|임)\.$", t) and not re.search(r"(요|죠)\.$", t):
            errs.append(f"격식체 의심 — …{t[-24:]}")

    # 4) 금칙어
    for bad in ("장부이익", "매수", "매도", "추천", "보장", "확실"):
        if bad in prose:
            errs.append(f"금칙어 '{bad}'")
    return errs


def verify_quotes(facts_doc: dict[str, Any], rcept_no: str | None) -> list[str]:
    """fact의 source_quote가 실제 주석 원문에 존재하는지 DB에서 대조 (토큰 0)."""
    errs: list[str] = []
    if not rcept_no or not REPORTS_DB.exists():
        return ["source_quote 대조 생략 — rcept_no 또는 DB 없음"]
    con = sqlite3.connect(f"file:{REPORTS_DB}?mode=ro", uri=True)
    cache: dict[str, str] = {}
    try:
        cur = con.cursor()
        for f in facts_doc.get("facts", []):
            nn = str(f.get("note_no", ""))
            q = (f.get("source_quote") or "").strip()
            if not q:
                continue
            if nn not in cache:
                cur.execute(
                    "select text_md from report_section where rcept_no=? and note_no=?",
                    (rcept_no, nn),
                )
                row = cur.fetchone()
                cache[nn] = (row[0] or "") if row else ""
            body = cache[nn]
            # 공백 정규화 후 substring 대조
            if re.sub(r"\s+", "", q) not in re.sub(r"\s+", "", body):
                errs.append(f"source_quote 원문 불일치: {f.get('key')} — '{q[:30]}'")
    finally:
        con.close()
    return errs


def flatten_facts(doc: dict[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for f in doc.get("facts", []):
        if f.get("value_won") is not None:
            out[f["key"]] = float(f["value_won"])
    for s in doc.get("segments", []):
        per = "_prior" if s.get("period") == "전기" else ""
        nm = s.get("name", "").strip()
        if s.get("revenue_won") is not None:
            out[f"seg_{nm}_rev{per}"] = float(s["revenue_won"])
        if s.get("op_won") is not None:
            out[f"seg_{nm}_op{per}"] = float(s["op_won"])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    t = args.ticker

    lite_p = DATA / f"galaxy_lite_{t}.json"
    facts_p = DATA / f"facts_lite_{t}.json"
    notes_p = DATA / f"notes_lite_{t}.json"
    for p in (lite_p, facts_p, notes_p):
        if not p.exists():
            raise SystemExit(f"[FATAL] 없음: {p}")

    lite = json.loads(lite_p.read_text(encoding="utf-8"))
    facts_doc = json.loads(facts_p.read_text(encoding="utf-8"))
    notes = json.loads(notes_p.read_text(encoding="utf-8"))
    facts = flatten_facts(facts_doc)

    print(f"fact {len(facts)}건 · 카드 {len(notes)}장")
    qerrs = verify_quotes(facts_doc, lite["corp"].get("rcept_no"))
    for e in qerrs:
        print("  [quote]", e)

    ok, bad = [], 0
    for c in notes:
        errs = verify_card(c, facts, lite)
        if errs:
            bad += 1
            print(f"  [FAIL] {c.get('id')} {c.get('title','')[:30]}")
            for e in errs:
                print("      -", e)
        else:
            print(f"  [PASS] {c.get('id')} {c.get('title','')[:40]}")
            ok.append({k: v for k, v in c.items() if k != "nums"})

    if qerrs or bad:
        print(f"[GATE] FAIL — 카드 {bad}장 반려, quote 오류 {len(qerrs)}건")
        raise SystemExit(1)

    if args.dry_run:
        print(f"[DRY] {len(ok)}장 통과 (주입 안 함)")
        return

    lite["notes"] = ok
    lite["meta"]["notes_gate"] = {"passed": len(ok), "facts_used": len(facts)}
    lite_p.write_text(json.dumps(lite, ensure_ascii=False, indent=1), encoding="utf-8")
    # cp949 콘솔에서 em dash는 크래시한다(FN-001 계보) — 성공 직후 print가 죽어 FAIL로 오인되므로 ASCII만
    print(f"[OK] {lite_p.name} / 주목할 점 {len(ok)}장 주입, 게이트 PASS")


if __name__ == "__main__":
    main()
