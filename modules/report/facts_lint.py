# -*- coding: utf-8 -*-
"""facts_lint.py — note-extractor 산출물(fact-sheet) 기계 검증 (S1 게이트).

승격 근거:
  · **출력 스키마 드리프트** — V-078(`items`→`facts` 키 변경) · V-105(값 키가 배치마다 5종으로
    갈려 조립기가 균일하게 못 읽음). 프롬프트 계약만으로 V-107에서 드리프트 0을 냈지만,
    계약은 사람이 어기면 조용히 통과하므로 코드로 못박는다.
  · **다열 표의 헤더-값 열 밀림** — V-107(A). 주42 특수관계자 표에서 기타채무 1위 거래처가
    한 칸 밀렸는데 `source_quote`가 원문 substring이라 그대로 통과했고, fact-sheet →
    산문까지 오염이 전파됐다. 검출 경로가 accuracy-verifier의 표 재파싱뿐이었다.

검사:
  1. 항목 스키마 = {name, value|cols, value_key, unit, period, source_quote, src} (초과 키 금지)
  2. source_quote가 그 주석 원문 text_md의 실제 substring (공백 무시 비교)
  3. **열 정렬 위험** — source_quote가 다값 행(숫자 토큰 ≥3)인데 `cols` 없이 단일 `value`만
     들고 있으면 어느 열인지 근거가 없다 → WARN(V-107 A의 사고 클래스)
  4. **cols 합계 검산** — '합계'/'계' 키가 있으면 나머지 값의 합과 대조

실행:
  python -m modules.report.facts_lint 139480              # facts_<t>.json + facts_<t>_b*.json
  python -m modules.report.facts_lint 139480 --strict     # WARN도 실패로
"""

from __future__ import annotations

import glob
import json
import os
import re
import sqlite3
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_FACTS = os.path.join(_HERE, "data", "facts")
_DB = os.path.join(os.path.dirname(os.path.dirname(_HERE)), "shared", "data", "reports.db")

FIELDS = {"name", "value", "value_key", "unit", "period", "source_quote", "src", "cols"}
REQUIRED = {"name", "unit", "period", "source_quote", "src"}
_NUM = re.compile(r"\(?-?[\d][\d,]*\)?")
_TOT = {"합계", "계", "소계", "총계", "total"}


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def _raw_notes(rcept: str, db_path: str = _DB) -> dict:
    con = sqlite3.connect(db_path)
    out = {
        str(n): _norm(md)
        for n, md in con.execute(
            "select note_no,text_md from report_section where rcept_no=? and note_no is not null",
            (rcept,),
        )
    }
    con.close()
    return out


def lint(ticker: str, db_path: str = _DB) -> tuple[list[str], list[str], dict]:
    """(errors, warns, stats)."""
    errs: list[str] = []
    warns: list[str] = []
    paths = sorted(glob.glob(os.path.join(_FACTS, f"facts_{ticker}_b*.json"))) or [
        os.path.join(_FACTS, f"facts_{ticker}.json")
    ]
    paths = [p for p in paths if os.path.exists(p)]
    if not paths:
        return [f"facts_{ticker}*.json 없음"], [], {}
    rcept = json.load(open(paths[0], encoding="utf-8")).get("rcept_no")
    raw = _raw_notes(rcept, db_path) if rcept and os.path.exists(db_path) else {}
    n_items = n_notes = 0
    seen_notes = set()
    for p in paths:
        d = json.load(open(p, encoding="utf-8"))
        tag = d.get("batch") or os.path.basename(p)
        for note, blk in (d.get("notes") or {}).items():
            seen_notes.add(note)
            n_notes += 1
            body = raw.get(note)
            if raw and body is None:
                errs.append(f"[{tag}] 주{note} — 원문에 없는 주번호")
                continue
            for it in blk.get("items") or []:
                n_items += 1
                who = f"[{tag}] 주{note} '{str(it.get('name'))[:34]}'"
                extra = set(it) - FIELDS
                miss = REQUIRED - set(it)
                if extra:
                    errs.append(f"{who} 스키마 초과 키 {sorted(extra)}")
                if miss:
                    errs.append(f"{who} 필수 키 누락 {sorted(miss)}")
                if "value" not in it and "cols" not in it:
                    errs.append(f"{who} value·cols 둘 다 없음")
                q = it.get("source_quote") or ""
                if body is not None and _norm(q) not in body:
                    errs.append(f"{who} source_quote 원문 불일치: {q[:40]!r}")
                # ── 열 정렬 위험(V-107 A) ──
                # 대상: `12 | 34 | 56` 꼴 **순수 수치 파이프 행**에서 단일 value만 뽑은 항목.
                # 이 모양은 어느 열인지 근거가 없어 한 칸만 밀려도 라벨-값이 통째로 뒤바뀐다
                # (주42 기타채무 1위 거래처 사고). 텍스트가 섞인 인용은 오탐이라 제외한다.
                cells = [c.strip() for c in q.split("|")]
                numc = [c for c in cells if c and _NUM.fullmatch(c.replace(" ", ""))]
                if (
                    "cols" not in it
                    and it.get("value") is not None
                    and len(cells) >= 3
                    and len(numc) >= 3
                    and len(numc) >= len(cells) - 1
                ):
                    warns.append(
                        f"{who} 순수 수치 파이프 행({len(numc)}열)에서 단일 value를 뽑음 — "
                        f"헤더-값 열 정렬 근거 없음(cols로 쓰거나 quote에 라벨 열을 포함할 것)"
                    )
                # ── cols 합계 검산 ──
                cols = it.get("cols")
                if isinstance(cols, dict) and len(cols) >= 3:
                    # '감가상각누계액'처럼 '계'가 든 계정명이 총계로 오인되지 않게 정확 매칭.
                    tk = [k for k in cols if _norm(str(k)) in _TOT or _norm(str(k)).endswith("합계")]
                    if len(tk) == 1:
                        tv = cols[tk[0]]
                        rest = [v for k, v in cols.items() if k != tk[0] and isinstance(v, (int, float))]
                        if isinstance(tv, (int, float)) and rest and abs(sum(rest) - tv) > max(2, abs(tv) * 0.005):
                            warns.append(
                                f"{who} cols 합계 불일치: 구성합 {sum(rest):,} ≠ '{tk[0]}' {tv:,}"
                            )
    return errs, warns, {"notes": len(seen_notes), "items": n_items, "files": len(paths)}


def main() -> int:
    args = sys.argv[1:]
    strict = "--strict" in args
    args = [a for a in args if a != "--strict"]
    t = args[0] if args else "005930"
    errs, warns, st = lint(t)
    print(f"=== facts_lint {t}: 파일 {st.get('files')} · 주석 {st.get('notes')} · 항목 {st.get('items')} ===")
    print(f"  ERROR {len(errs)} · WARN {len(warns)}")
    for e in errs[:30]:
        print("  E", e)
    for w in warns[:30]:
        print("  W", w)
    if len(errs) > 30 or len(warns) > 30:
        print(f"  … (E {len(errs)} / W {len(warns)})")
    bad = errs if not strict else errs + warns
    print("PASS ✅" if not bad else "FAIL")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
