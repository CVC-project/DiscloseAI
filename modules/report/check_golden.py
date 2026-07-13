# -*- coding: utf-8 -*-
"""check_golden.py — galaxy_<ticker>.json 완전성·정확성 기계 체커 (R6 S4·S5의 코드 검증층).

PHASE4_PLAN R6.3 규칙 내장: 항등식(암산 금지)·잔재 스캔(회사 파라미터화)·격식체·연도오인·
빈 브래킷·viz_data 스키마·링크=패널 정합·깊이 지표·서브행 합=부모.

실행: python -m modules.report.check_golden 000660
종료코드: 0=PASS, 1=FAIL(갭 목록 출력). 루프 드라이버(/galaxy-golden)의 수렴 조건.
"""

from __future__ import annotations

import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
_DATA = os.path.join(_ROOT, "integration", "dossier", "data")

GOLDEN_REF = "005930"  # 구조 레지스트리 기준(콘텐츠 dive 27키·APPENDIX 14건)

# 잔재 스캔: 다른 골든의 고유 토큰 (검사 대상 회사에 나타나면 누출)
LEAK_TOKENS: dict[str, list[str]] = {
    "005930": ["에스케이하이닉스", "SK하이닉스", "메모리 다운턴", "62,044", "97.1조"],
    "_default": ["삼성전자", "삼성전기", "삼성SDS", "반도체 한파", "6,605", "333.6조", "52.9조", "215.2조", "308개"],
}
# 골든 수작업 예외(리더 승인 문구) — 해당 티커에서만 금칙어 검사 완화
FORBIDDEN_ALLOW: dict[str, list[str]] = {"005930": ["사상 최대"]}

FORMAL_RE = re.compile(r"(습니다|합니다|입니다|됩니다|납니다|립니다|칩니다|줍니다|봅니다|랍니다|겁니다|였다[.\s]|한다[.\s])")
YEAR_RE = re.compile(r"(20(1\d|2[0-4]))년\s*(기준|현재)")
FORBIDDEN = ["매수", "매도 추천", "투자 조언", "확실히 오", "보장", "사상 최대", "사상최대"]
VIZ_SCHEMA = {  # viz_data 필수 키 (R6.3-7: 형식 불일치=빈 박스 사고 방지)
    "vHBar": ("items", list), "vChips": ("chips", list), "vWater": ("steps", list),
    "vSteps": ("rows", list), "vPuddle": ("ar", (int, float, str)), "vBubbles": ("segs", list),
}
SKIP_ALLOWED_NO_LINKS = True  # appendix는 links 없어도 됨


def _num(v):
    try:
        return float(str(v).replace("−", "-").replace("조", "").replace("+", "").replace(",", ""))
    except (ValueError, TypeError):
        return None


def _texts(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from _texts(v)
    elif isinstance(o, list):
        for v in o:
            yield from _texts(v)


def check(ticker: str) -> list[str]:
    gaps: list[str] = []
    path = os.path.join(_DATA, f"galaxy_{ticker}.json")
    if not os.path.exists(path):
        return [f"galaxy_{ticker}.json 없음"]
    G = json.load(open(path, encoding="utf-8"))
    ref = json.load(open(os.path.join(_DATA, f"galaxy_{GOLDEN_REF}.json"), encoding="utf-8")) \
        if ticker != GOLDEN_REF else G

    dives, apx, S = G.get("dives", {}), G.get("appendix", []), G.get("series", {})
    panels = G.get("panels", {})
    row2v = {r.get("row"): r.get("v") for z in panels for r in panels.get(z, [])}

    # ── 1) 구조 커버리지 (골든 레지스트리 대비) ──
    missing = set(ref.get("dives", {})) - set(dives)
    if missing:
        gaps.append(f"[커버리지] 콘텐츠 dive 누락 {len(missing)}: {sorted(missing)}")
    if len(apx) < len(ref.get("appendix", [])):
        gaps.append(f"[커버리지] appendix {len(apx)}/{len(ref.get('appendix', []))}")

    # ── 2) 카드 4절 채움 + 깊이 지표 (R6.1 S5) ──
    # 깊이 지표는 생성물 검증용 — 골든 레퍼런스(기준 그 자체, 재생성 없음)는 공란 검사만.
    depth_scan = ticker != GOLDEN_REF
    for k, d in list(dives.items()) + [("apx:" + a.get("n", "?"), a) for a in apx]:
        is_apx = (not depth_scan) or k.startswith("apx:")
        fv = d.get("five", {})
        # five=skip 카드는 보조 매듭(골든 자체가 얇음) — 완화 임계(links≥1·브래킷≥1)
        min_links, min_br = (1, 1) if fv.get("skip") else (2, 2)
        if not d.get("what") or not [w for w in d["what"] if w.strip()]:
            gaps.append(f"[{k}] what 공란")
        elif not is_apx and len(d["what"]) < 2:
            gaps.append(f"[{k}] 깊이: what {len(d['what'])}문장(<2)")
        if not is_apx and len(d.get("links") or []) < min_links:
            gaps.append(f"[{k}] 깊이: links {len(d.get('links') or [])}(<{min_links})")
        if not (d.get("why", {}).get("body") or []):
            gaps.append(f"[{k}] why.body 공란")
        if not (fv.get("cap") or fv.get("skip")):
            gaps.append(f"[{k}] five 공란")
        if depth_scan and fv.get("cap") and not re.search(r"\d", fv["cap"]):
            gaps.append(f"[{k}] five.cap 숫자 0개")
        if fv.get("key") and fv["key"] not in S:
            gaps.append(f"[{k}] five.key '{fv['key']}' series에 없음")
        blob = " ".join(_texts({"w": d.get("what"), "b": d.get("why", {}).get("body")}))
        if not is_apx and len(re.findall(r"\[[^\[\]]{1,24}\]", blob)) < min_br:
            gaps.append(f"[{k}] 깊이: 브래킷 칩 <{min_br}")

    # ── 3) 텍스트 규율: 격식체·연도오인·빈 브래킷·금칙어·잔재 ──
    # 골든 레퍼런스는 문체 기준 그 자체(리더 수작업 정본) — 문체 스캔 면제, 구조·항등식·잔재는 검사.
    allow = FORBIDDEN_ALLOW.get(ticker, [])
    style_scan = ticker != GOLDEN_REF
    for k, d in list(dives.items()) + [("apx:" + a.get("n", "?"), a) for a in apx]:
        for t in _texts({"w": d.get("what"), "b": d.get("why", {}).get("body"), "f": d.get("five", {})}):
            if not style_scan:
                break
            if FORMAL_RE.search(t or ""):
                gaps.append(f"[{k}] 격식체: {t[:30]}")
            if YEAR_RE.search(t or ""):
                gaps.append(f"[{k}] 연도오인: {t[:36]}")
            if "[·]" in (t or "") or "[?]" in (t or ""):
                gaps.append(f"[{k}] 빈 브래킷")
            for f in FORBIDDEN:
                if f in (t or "") and f not in allow:
                    gaps.append(f"[{k}] 금칙어 '{f}'")
    blob_all = json.dumps(G, ensure_ascii=False)
    for tok in LEAK_TOKENS.get(ticker, LEAK_TOKENS["_default"]):
        if tok in blob_all:
            gaps.append(f"[잔재] '{tok}' 발견")

    # ── 4) 항등식 (R6.3-1: 파생 수치 암산 금지 — 코드가 검산) ──
    def ident(name, lhs, rhs, tol):
        if lhs is None or rhs is None:
            return
        if abs(lhs - rhs) > tol:
            gaps.append(f"[항등식] {name}: {lhs:.2f} ≠ {rhs:.2f} (±{tol})")

    def last(key):
        v = S.get(key)
        return v[-1] if isinstance(v, list) and v else None

    if all(S.get(x) for x in ("revenue", "cogs", "gross")):
        ident("매출−원가=총이익", S["revenue"][-1] - S["cogs"][-1], S["gross"][-1], 0.15)
    if all(S.get(x) for x in ("ni", "oci", "tci")):
        ident("ni+oci=tci", S["ni"][-1] + S["oci"][-1], S["tci"][-1], 0.15)
    if all(S.get(x) for x in ("cash", "ocf", "icf", "fin")) and len(S["cash"]) >= 2:
        ident("현금워크(환율 허용)", S["cash"][-2] + S["ocf"][-1] + S["icf"][-1] + S["fin"][-1], S["cash"][-1], 1.0)
    pb = {r.get("row"): _num(r.get("v")) for r in panels.get("B", [])}
    if all(pb.get(x) is not None for x in ("is-revenue", "is-cogs", "is-grossprofit")):
        ident("패널B 총이익", pb["is-revenue"] + pb["is-cogs"], pb["is-grossprofit"], 0.2)

    # ── 5) 서브행 합 = 부모 (grp, 잔차 '그 외'·'기타' 명시 규약) ──
    PARENT = {"sgna": "is-sgna", "nonop": "is-nonop", "noncash": "cf-noncash", "wc": "cf-wc",
              "inv": "cf-inv", "fin": "cf-fin", "bsa": "bs-assets", "bsl": "bs-liab", "bse": "bs-equity"}
    for z in panels:
        pass
    for g, prow in PARENT.items():
        rows = [r for z in panels for r in panels.get(z, []) if r.get("grp") == g]
        if not rows:
            continue
        kids = [(_num(r.get("v")), r.get("name", "")) for r in rows if "(계)" not in (r.get("name") or "")]
        vals = [v for v, _ in kids if v is not None]
        pv = _num(row2v.get(prow))
        if vals and pv is not None and abs(sum(vals) - pv) > 0.25:
            gaps.append(f"[서브행합] {g}: 합 {sum(vals):.1f} ≠ 부모 {pv:.1f}")

    # ── 6) 링크 a값 정합 / viz_data 스키마 ──
    # 골든 의미론: a는 그 행의 총액이 아니라 '맞물리는 숫자'(구성요소·구성요소 합)일 수 있다.
    # 허용 후보 = 그 행 v ∪ 모든 패널 |v| ∪ 링크 행 grp 자식들의 쌍합 |vi+vj|. 어디에도 없으면 낡은 값(FAIL).
    all_vals = {abs(_num(r.get("v"))) for z in panels for r in panels.get(z, []) if _num(r.get("v")) is not None}
    grp_of_row = {r.get("row"): r.get("grp") for z in panels for r in panels.get(z, [])}
    row_grp_children: dict[str, list[float]] = {}
    for z in panels:
        for r in panels.get(z, []):
            g = r.get("grp")
            if g and _num(r.get("v")) is not None:
                row_grp_children.setdefault(g, []).append(_num(r.get("v")))
    PARENT_GRP = {"is-sgna": "sgna", "is-nonop": "nonop", "cf-noncash": "noncash", "cf-wc": "wc",
                  "cf-inv": "inv", "cf-fin": "fin", "bs-assets": "bsa", "bs-liab": "bsl", "bs-equity": "bse"}
    for k, d in dives.items():
        for ln in d.get("links") or []:
            a, row = ln.get("a"), ln.get("row")
            av = _num(a) if a else None
            if av is None:
                continue
            cands = set(all_vals)
            g = PARENT_GRP.get(row) or grp_of_row.get(row)
            kids = row_grp_children.get(g, [])
            for i in range(len(kids)):
                for j in range(i + 1, len(kids)):
                    cands.add(abs(kids[i] + kids[j]))
            if not any(abs(abs(av) - c) <= 0.15 for c in cands):
                gaps.append(f"[{k}] 링크 {row}: a={a} — 패널 어디에도 없는 값(낡음 의심)")
        w = d.get("why", {})
        if w.get("viz"):
            sch = VIZ_SCHEMA.get(w["viz"])
            if sch is None:
                gaps.append(f"[{k}] 미지의 viz '{w['viz']}'")
            elif w["viz"] != "vLine":
                vd = w.get("viz_data") or {}
                key, typ = sch
                if not isinstance(vd.get(key), typ):
                    gaps.append(f"[{k}] viz_data 스키마: {w['viz']}에 '{key}' 없음/형식 오류")
    # ── 7) 주석 라우팅 원장 — "모든 실주석이 처리됐는가" (사용자 요구: 전 주석 완전성) ──
    # reports.db가 있으면: DB 주석 전수가 ledger에 있고, MISSING 0, excluded는 reason 필수,
    # 본문 주N 인용이 실재 주석인지(유령 인용) 검사.
    db = os.path.join(_HERE, "data", "reports.db")
    rcept = (G.get("corp") or {}).get("rcept_no") or {"005930": "20260310002820", "000660": "20260317000635"}.get(ticker)
    if os.path.exists(db) and rcept:
        import sqlite3
        con = sqlite3.connect(db)
        db_notes = {str(r[0]) for r in con.execute(
            "select note_no from report_section where rcept_no=? and note_no is not null", (rcept,))}
        con.close()
        if db_notes:
            ledger = (G.get("meta") or {}).get("routing_ledger") or {}
            if not ledger:
                gaps.append(f"[원장] routing_ledger 없음 (실주석 {len(db_notes)}개 미처리)")
            else:
                for n in sorted(db_notes, key=int):
                    ent = ledger.get(n)
                    if not ent:
                        gaps.append(f"[원장] 주{n} 원장 누락")
                    elif ent.get("to") == "MISSING":
                        gaps.append(f"[원장] 주{n} '{ent.get('title','')}' 미라우팅")
                    elif ent.get("to") == "excluded" and not ent.get("reason"):
                        gaps.append(f"[원장] 주{n} 제외 사유 없음")
                ghost = set(re.findall(r"주\s?(\d{1,2})(?=\D|$)", blob_all)) - db_notes
                for n in sorted(ghost, key=int):
                    gaps.append(f"[원장] 유령 인용 주{n} — 실주석에 없음")
    return gaps


def main() -> int:
    t = sys.argv[1] if len(sys.argv) > 1 else "000660"
    gaps = check(t)
    print(f"=== check_golden {t}: 갭 {len(gaps)}건 ===")
    for g in gaps:
        print("  -", g)
    print("PASS ✅" if not gaps else "FAIL")
    return 0 if not gaps else 1


if __name__ == "__main__":
    sys.exit(main())
