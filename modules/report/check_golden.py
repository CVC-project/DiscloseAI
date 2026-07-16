# -*- coding: utf-8 -*-
"""check_golden.py — galaxy_<ticker>.json 완전성·정확성 기계 체커 (R6 S4·S5의 코드 검증층).

MILKYWAY_GENERATOR §5(R6.3) 규칙 내장: 항등식(암산 금지)·잔재 스캔(회사 파라미터화)·격식체·연도오인·
빈 브래킷·viz_data 스키마·링크=패널 정합·깊이 지표·서브행 합=부모.

실행: python -m modules.report.check_golden 000660
종료코드: 0=PASS, 1=FAIL(갭 목록 출력). 루프 드라이버(/galaxy-golden)의 수렴 조건.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
_DATA = os.path.join(_ROOT, "integration", "dossier", "data")


def _golden_ref(default="005930"):
    """corps.csv의 tier==0(T0 최상위 정본) 티커를 GOLDEN_REF로 파생(R8 정본 계층) — 파싱 실패 시 default로 무회귀."""
    try:
        with open(os.path.join(_HERE, "data", "corps.csv"), encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                if (row.get("tier") or "").strip() == "0":
                    return (row.get("ticker") or default).strip()
    except (OSError, csv.Error):
        pass
    return default


GOLDEN_REF = (
    _golden_ref()
)  # T0 최상위 정본(문체·깊이·회귀 기준) — corps.csv tier=0에서 파생(하드코딩 폴백 005930)

# 잔재 스캔: 다른 골든의 고유 토큰 (검사 대상 회사에 나타나면 누출)
LEAK_TOKENS: dict[str, list[str]] = {
    "005930": ["에스케이하이닉스", "SK하이닉스", "메모리 다운턴", "62,044", "97.1조"],
    "_default": [
        "삼성전자",
        "삼성전기",
        "삼성SDS",
        "반도체 한파",
        "6,605",
        "333.6조",
        "52.9조",
        "215.2조",
        "308개",
    ],
}
# 골든 수작업 예외(리더 승인 문구) — 해당 티커에서만 금칙어 검사 완화
FORBIDDEN_ALLOW: dict[str, list[str]] = {"005930": ["사상 최대"]}

FORMAL_RE = re.compile(
    r"(습니다|합니다|입니다|됩니다|납니다|립니다|칩니다|줍니다|봅니다|랍니다|겁니다|였다[.\s]|한다[.\s])"
)
YEAR_RE = re.compile(r"(20(1\d|2[0-4]))년\s*(기준|현재)")
FORBIDDEN = [
    "매수",
    "매도 추천",
    "투자 조언",
    "확실히 오",
    "보장",
    "사상 최대",
    "사상최대",
]
VIZ_SCHEMA = {  # viz_data 필수 키 (R6.3-7: 형식 불일치=빈 박스 사고 방지)
    "vHBar": ("items", list),
    "vChips": ("chips", list),
    "vWater": ("steps", list),
    "vSteps": ("rows", list),
    "vPuddle": ("ar", (int, float, str)),
    "vBubbles": ("segs", list),
}
SKIP_ALLOWED_NO_LINKS = True  # appendix는 links 없어도 됨


def _num(v):
    try:
        return float(
            str(v).replace("−", "-").replace("조", "").replace("+", "").replace(",", "")
        )
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


def check(ticker: str, strict: bool = False) -> list[str]:
    gaps: list[str] = []
    path = os.path.join(_DATA, f"galaxy_{ticker}.json")
    if not os.path.exists(path):
        return [f"galaxy_{ticker}.json 없음"]
    G = json.load(open(path, encoding="utf-8"))

    dives, apx, S = G.get("dives", {}), G.get("appendix", []), G.get("series", {})
    panels = G.get("panels", {})
    row2v = {r.get("row"): r.get("v") for z in panels for r in panels.get(z, [])}

    # ── 1) 구조 커버리지 — ⚠️ 보고서 기반 원칙(R6.9): 골든이 아니라 그 회사 데이터가 기대 집합을 정의한다.
    #  방향A: 회사 데이터(series 완결·패널 행)에 근거 있는 dive만 요구 — 골든에 있어도 근거 없으면 요구 금지.
    #  방향B: 근거 없는 dive가 존재하면(골든 따라 0/—로 만든 것) FAIL — "없는 항목은 아예 없어야 한다".
    def _complete(key):
        v = S.get(key)
        return (
            isinstance(v, list)
            and len(v) >= 5
            and all(isinstance(x, (int, float)) for x in v)
        )

    REQ_SERIES = {
        "k1": "cash",
        "k2": "revenue",
        "k3": "cogs",
        "k4": "gross",
        "k5": "sgna",
        "k6": "op",
        "k6b": "pretax",
        "k7": "tax",
        "k8": "ni",
        "k9": "ocf",
        "k11": "ocf",
        "k12": "icf",
        "k13": "fin",
        "k15": "cash",
        "oci": "oci",
        "totalcomp": "tci",
        "assets": "assets",
        "liab": "debt",
        "eq-begin": "equity",
        "eq-end": "equity",
        "eq-div": "div",
        "ppe": "capex",
    }
    COND_ROW = {
        "k10": "cf-wc",
        "k10b": "cf-paid",
        "k14": "cf-fx",
        "eq-buyback": "eq-buyback",
        "eq-other": "eq-other",
    }
    expected = {k for k, sk in REQ_SERIES.items() if _complete(sk)}
    expected |= {k for k, row in COND_ROW.items() if row in row2v}
    universe = set(REQ_SERIES) | set(COND_ROW)
    for k in sorted(expected - set(dives)):
        gaps.append(
            f"[커버리지] dive '{k}' 누락 — 회사 데이터에 근거 있음(series/행 존재)"
        )
    for k in sorted((set(dives) & universe) - expected):
        gaps.append(
            f"[커버리지] dive '{k}' 근거 없음 — 보고서에 없는 항목은 0/— 표시가 아니라 생략(R6.9)"
        )
    # 회사 고유 신규 dive(universe 밖)는 허용 — 원장 §7의 new-dive 라우팅과 짝.
    # appendix는 개수 강제 없음 — 원장(§7)이 '그 회사 실주석' 기준으로 전수 라우팅을 강제한다.
    # ── 그림자 dive 방지(V-053): 두 dive가 같은 row 참조 시 뒤엣것은 클릭 미도달(_diveKey가 한 row→한 dive).
    #  부문(segment)류 new-dive가 k2(is-revenue) 등과 row 공유하면 산문이 렌더 불가 → 고유 앵커 부여 or k2로 병합.
    _rowdive: dict = {}
    for k, d in dives.items():
        r = d.get("row")
        if r:
            _rowdive.setdefault(r, []).append(k)
    for r, ks in sorted(_rowdive.items()):
        if len(ks) > 1:
            gaps.append(
                f"[그림자] dive {sorted(ks)} 가 row '{r}' 공유 — 뒤엣것 클릭 미도달(고유 앵커 필요/병합)"
            )

    # ── 2) 카드 4절 채움 + 깊이 지표 (R6.1 S5) ──
    # 깊이 지표는 생성물 검증용 — 골든 레퍼런스(기준 그 자체, 재생성 없음)는 공란 검사만.
    depth_scan = ticker != GOLDEN_REF
    for k, d in list(dives.items()) + [("apx:" + a.get("n", "?"), a) for a in apx]:
        is_apx = k.startswith("apx:")
        skip_depth = not depth_scan  # 골든 레퍼런스(삼성)는 깊이 기준 그 자체 — 면제
        fv = d.get("five", {})
        blob = " ".join(_texts({"w": d.get("what"), "b": d.get("why", {}).get("body")}))
        nbr = len(re.findall(r"\[[^\[\]]{1,24}\]", blob))  # 브래킷 칩 수
        ndigit = len(re.findall(r"\[[^\[\]]*\d[^\[\]]*\]", blob))  # 숫자 든 브래킷 수
        if not d.get("what") or not [w for w in d["what"] if w.strip()]:
            gaps.append(f"[{k}] what 공란")
        elif not skip_depth and len(d["what"]) < 2:
            gaps.append(f"[{k}] 깊이: what {len(d['what'])}문장(<2)")
        if not (d.get("why", {}).get("body") or []):
            gaps.append(f"[{k}] why.body 공란")
        if not (fv.get("cap") or fv.get("skip")):
            gaps.append(f"[{k}] five 공란")
        if depth_scan and fv.get("cap") and not re.search(r"\d", fv["cap"]):
            gaps.append(f"[{k}] five.cap 숫자 0개")
        if fv.get("key") and fv["key"] not in S:
            gaps.append(f"[{k}] five.key '{fv['key']}' series에 없음")
        if skip_depth:
            continue
        if is_apx:
            # APPENDIX도 '실주석 기반 리치 카드' — 삼성 골든 수준 하한(V-048): 링크·수치·용어.
            # 일반론(개념 설명만·숫자 없음·링크 없음) 금지. amt도 실값이어야.
            if len(d.get("links") or []) < 1:
                gaps.append(f"[{k}] APPENDIX 링크 0 — 재무제표 연결 필요(일반론 금지)")
            if nbr < 2:
                gaps.append(
                    f"[{k}] APPENDIX 브래킷 <2 — 주석 실수치·용어 부족(일반론 금지)"
                )
            if ndigit < 1:
                gaps.append(
                    f"[{k}] APPENDIX 숫자 브래킷 0 — 그 주석의 실제 수치 필요(일반론 금지)"
                )
            if not re.search(r"\d", str(d.get("amt", ""))):
                gaps.append(f"[{k}] APPENDIX amt에 실수치 없음('{d.get('amt','')}')")
        else:
            min_links, min_br = (1, 1) if fv.get("skip") else (2, 2)
            if len(d.get("links") or []) < min_links:
                gaps.append(
                    f"[{k}] 깊이: links {len(d.get('links') or [])}(<{min_links})"
                )
            if nbr < min_br:
                gaps.append(f"[{k}] 깊이: 브래킷 칩 <{min_br}")

    # ── 3) 텍스트 규율: 격식체·연도오인·빈 브래킷·금칙어·잔재 ──
    # 골든 레퍼런스는 문체 기준 그 자체(리더 수작업 정본) — 문체 스캔 면제, 구조·항등식·잔재는 검사.
    allow = FORBIDDEN_ALLOW.get(ticker, [])
    style_scan = ticker != GOLDEN_REF
    for k, d in list(dives.items()) + [("apx:" + a.get("n", "?"), a) for a in apx]:
        for t in _texts(
            {
                "w": d.get("what"),
                "b": d.get("why", {}).get("body"),
                "f": d.get("five", {}),
            }
        ):
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
        ident(
            "매출−원가=총이익", S["revenue"][-1] - S["cogs"][-1], S["gross"][-1], 0.15
        )
    if all(S.get(x) for x in ("ni", "oci", "tci")):
        ident("ni+oci=tci", S["ni"][-1] + S["oci"][-1], S["tci"][-1], 0.15)
    if all(S.get(x) for x in ("cash", "ocf", "icf", "fin")) and len(S["cash"]) >= 2:
        ident(
            "현금워크(환율 허용)",
            S["cash"][-2] + S["ocf"][-1] + S["icf"][-1] + S["fin"][-1],
            S["cash"][-1],
            1.0,
        )
    pb = {r.get("row"): _num(r.get("v")) for r in panels.get("B", [])}
    if all(pb.get(x) is not None for x in ("is-revenue", "is-cogs", "is-grossprofit")):
        ident(
            "패널B 총이익", pb["is-revenue"] + pb["is-cogs"], pb["is-grossprofit"], 0.2
        )

    # ── 5) 서브행 합 = 부모 (grp, 잔차 '그 외'·'기타' 명시 규약) ──
    PARENT = {
        "sgna": "is-sgna",
        "nonop": "is-nonop",
        "noncash": "cf-noncash",
        "wc": "cf-wc",
        "inv": "cf-inv",
        "fin": "cf-fin",
        "bsa": "bs-assets",
        "bsl": "bs-liab",
        "bse": "bs-equity",
    }
    for z in panels:
        pass
    for g, prow in PARENT.items():
        rows = [r for z in panels for r in panels.get(z, []) if r.get("grp") == g]
        if not rows:
            continue
        kids = [
            (_num(r.get("v")), r.get("name", ""))
            for r in rows
            if "(계)" not in (r.get("name") or "")
        ]
        vals = [v for v, _ in kids if v is not None]
        pv = _num(row2v.get(prow))
        if vals and pv is not None and abs(sum(vals) - pv) > 0.25:
            gaps.append(f"[서브행합] {g}: 합 {sum(vals):.1f} ≠ 부모 {pv:.1f}")

    # ── 6) 링크 a값 정합 / viz_data 스키마 ──
    # 골든 의미론: a는 그 행의 총액이 아니라 '맞물리는 숫자'(구성요소·구성요소 합)일 수 있다.
    # 허용 후보 = 그 행 v ∪ 모든 패널 |v| ∪ 링크 행 grp 자식들의 쌍합 |vi+vj|. 어디에도 없으면 낡은 값(FAIL).
    all_vals = {
        abs(_num(r.get("v")))
        for z in panels
        for r in panels.get(z, [])
        if _num(r.get("v")) is not None
    }
    grp_of_row = {r.get("row"): r.get("grp") for z in panels for r in panels.get(z, [])}
    row_grp_children: dict[str, list[float]] = {}
    for z in panels:
        for r in panels.get(z, []):
            g = r.get("grp")
            if g and _num(r.get("v")) is not None:
                row_grp_children.setdefault(g, []).append(_num(r.get("v")))
    PARENT_GRP = {
        "is-sgna": "sgna",
        "is-nonop": "nonop",
        "cf-noncash": "noncash",
        "cf-wc": "wc",
        "cf-inv": "inv",
        "cf-fin": "fin",
        "bs-assets": "bsa",
        "bs-liab": "bsl",
        "bs-equity": "bse",
    }
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
                gaps.append(
                    f"[{k}] 링크 {row}: a={a} — 패널 어디에도 없는 값(낡음 의심)"
                )
        w = d.get("why", {})
        if w.get("viz"):
            sch = VIZ_SCHEMA.get(w["viz"])
            if sch is None:
                gaps.append(f"[{k}] 미지의 viz '{w['viz']}'")
            elif w["viz"] != "vLine":
                vd = w.get("viz_data") or {}
                key, typ = sch
                if not isinstance(vd.get(key), typ):
                    gaps.append(
                        f"[{k}] viz_data 스키마: {w['viz']}에 '{key}' 없음/형식 오류"
                    )
    # ── 7) 주석 라우팅 원장 — "모든 실주석이 처리됐는가" (사용자 요구: 전 주석 완전성) ──
    # reports.db가 있으면: DB 주석 전수가 ledger에 있고, MISSING 0, excluded는 reason 필수,
    # 본문 주N 인용이 실재 주석인지(유령 인용) 검사.
    db = os.path.join(_HERE, "data", "reports.db")
    rcept = (G.get("corp") or {}).get("rcept_no") or {
        "005930": "20260310002820",
        "000660": "20260317000635",
    }.get(ticker)
    if os.path.exists(db) and rcept:
        import sqlite3

        con = sqlite3.connect(db)
        db_notes = {
            str(r[0])
            for r in con.execute(
                "select note_no from report_section where rcept_no=? and note_no is not null",
                (rcept,),
            )
        }
        con.close()
        if db_notes:
            ledger = (G.get("meta") or {}).get("routing_ledger") or {}
            if not ledger:
                gaps.append(
                    f"[원장] routing_ledger 없음 (실주석 {len(db_notes)}개 미처리)"
                )
            else:
                apx_ids = {a.get("n") for a in apx}

                # 하위번호 주석('24-1'·'11.1') 안전 정렬 (V-031: 주번호는 문자열, int 캐스팅 금지)
                def _nkey(n):
                    parts = re.split(r"[.\-]", str(n))
                    return tuple(int(p) if p.isdigit() else 0 for p in parts)

                for n in sorted(db_notes, key=_nkey):
                    ent = ledger.get(n)
                    to = (ent or {}).get("to", "")
                    if not ent:
                        gaps.append(f"[원장] 주{n} 원장 누락")
                    elif to == "MISSING":
                        gaps.append(
                            f"[원장] 주{n} '{ent.get('title','')}' 미라우팅 — 회사 고유 항목이면 new-dive로 신규 생성(R6.9)"
                        )
                    elif to == "excluded" and not ent.get("reason"):
                        gaps.append(f"[원장] 주{n} 제외 사유 없음")
                    elif (
                        to.startswith("appendix:")
                        and to.split(":", 1)[1] not in apx_ids
                    ):
                        gaps.append(f"[원장] 주{n} → {to} — appendix에 실존하지 않음")
                    elif (
                        to.startswith("new-dive:") and to.split(":", 1)[1] not in dives
                    ):
                        gaps.append(f"[원장] 주{n} → {to} — 신규 dive 미생성")
                    elif to not in ("dive:cited", "excluded") and not to.startswith(
                        ("appendix:", "row:", "new-dive:")
                    ):
                        gaps.append(f"[원장] 주{n} 미지의 라우팅 '{to}'")
                # 주요번호만 포착(소수값 오포착 방지). '주2'는 실주석 '2' 또는 하위번호 '2-1'·'2.1'이
                # 있으면 유령 아님 (V-031: 하위번호 주석 대응, 삼성 소수값 6.07 오탐 방지).
                cited = set(re.findall(r"주\s?(\d{1,2})(?=\D|$)", blob_all))
                ghost = {
                    n
                    for n in cited
                    if not any(
                        d == n or d.startswith(n + "-") or d.startswith(n + ".")
                        for d in db_notes
                    )
                }
                for n in sorted(ghost, key=_nkey):
                    gaps.append(f"[원장] 유령 인용 주{n} — 실주석에 없음")

    # ── 8) (strict) 원문 정합 + amt 표기 계약 + 승격 구조 (V-068·069 캐스케이드 판정기) ──
    # 기본 check()·--all에는 미포함(6본 미소거 상태 green 유지) — 캐스케이드 수렴 판정은 --strict.
    if strict:
        gaps += _check_strict(ticker, G, dives)
    return gaps


_NUMGRP = re.compile(r"[\d][\d,]*\.?\d*\s*(?:조|억|원|%|배|개)?")
_STMT_NEED = {
    "bs": "재무상태표",
    "is": "손익계산서",
    "cis": "포괄손익",
    "eq": "자본변동",
    "cf": "현금흐름",
}


def _check_strict(ticker: str, G: dict, dives: dict) -> list[str]:
    """V-068·069 캐스케이드 계약 판정 — 원문 정합·amt 표기(R6.6c)·승격 구조(.row·note_dive)."""
    gaps: list[str] = []
    # 8-1 사업보고서 원문 정합 (오라벨 방지 — 단일 CIS 회사도 cf 필수)
    rpath = os.path.join(_DATA, f"report_{ticker}.json")
    if not os.path.exists(rpath):
        gaps.append(f"[원문] report_{ticker}.json 없음 — build_report_source.py 필요")
    else:
        st = (json.load(open(rpath, encoding="utf-8")).get("statements")) or {}
        if not st.get("bs"):
            gaps.append("[원문] 재무상태표(bs) 없음")
        if not st.get("cf"):
            gaps.append("[원문] 현금흐름표(cf) 없음 — 번호 하드코딩 오라벨 의심(V-068)")
        if not (st.get("is") or st.get("cis")):
            gaps.append("[원문] 손익/포괄손익(is/cis) 없음")
        for k, need in _STMT_NEED.items():
            s = st.get(k)
            if s and need not in (s.get("title") or ""):
                gaps.append(
                    f"[원문] {k} 제목 '{s.get('title','')}' — '{need}' 불일치(오라벨)"
                )
        if st.get("is") and "포괄" in (st["is"].get("title") or ""):
            gaps.append("[원문] is에 포괄손익계산서가 실림(오라벨)")
    # 8-2 amt 표기 계약(R6.6c) — 흐름·승격 dive(비appendix) 헤드라인. 전 티커(삼성 포함).
    for k, d in dives.items():
        amt, name = str(d.get("amt", "")), str(d.get("name", ""))
        if not re.search(r"\d", amt):
            gaps.append(f"[amt] {k} 헤드라인 숫자 없음('{amt}') — 실값 필요")
            continue
        nums = _NUMGRP.findall(amt)
        if len(nums) < 2:  # 단일 수치인데 라벨이 name을 복창하면 제목반복
            label = _NUMGRP.sub(" ", amt)
            rep = [
                t
                for t in re.split(r"[·・•,\s~\-−()]+", label)
                if len(t) >= 2 and t in name
            ]
            if rep:
                gaps.append(
                    f"[amt] {k} 제목반복 '{amt}' (name '{name}'에 {rep}) — 숫자만 두거나 양면 병기"
                )
    # 8-3 승격 구조 — new-dive 카드 .row 앵커(클릭 도달) + note_dive 유효. 삼성은 레거시 ROW2DIVE라 면제.
    meta = G.get("meta") or {}
    if ticker != GOLDEN_REF:
        for n, ent in (meta.get("routing_ledger") or {}).items():
            to = (ent or {}).get("to", "")
            if to.startswith("new-dive:"):
                key = to.split(":", 1)[1]
                dd = dives.get(key)
                if dd and not dd.get("row"):
                    gaps.append(
                        f"[승격] {key}(주{n}) .row 앵커 없음 — 클릭 도달 불가(V-069)"
                    )
    for n, key in (meta.get("note_dive") or {}).items():
        if key not in dives:
            gaps.append(f"[note_dive] 주{n}→{key} 대상 dive 없음")
    return gaps


def main() -> int:
    args = sys.argv[1:]
    strict = (
        "--strict" in args
    )  # V-068·069 캐스케이드 계약 게이트(원문·amt·승격) 추가 — 수렴 판정용
    args = [a for a in args if a != "--strict"]
    if args and args[0] == "--all":  # 전 골든 회귀 게이트 (galaxy_*.json 전수 — R8)
        import glob

        tickers = sorted(
            os.path.basename(p)[7:-5]
            for p in glob.glob(os.path.join(_DATA, "galaxy_*.json"))
            if os.path.basename(p) != "galaxy_index.json"
        )
        total = 0
        for t in tickers:
            n = len(check(t, strict))
            total += n
            print(f"  {t}: 갭 {n}건" + ("" if not n else "  ← FAIL"))
        print(
            f"=== 전체 {len(tickers)}본: 갭 {total}건 — {'PASS ✅' if total == 0 else 'FAIL'} (GOLDEN_REF={GOLDEN_REF})"
        )
        return 0 if total == 0 else 1
    t = args[0] if args else "000660"
    gaps = check(t, strict)
    print(f"=== check_golden {t}{' --strict' if strict else ''}: 갭 {len(gaps)}건 ===")
    for g in gaps:
        print("  -", g)
    print("PASS ✅" if not gaps else "FAIL")
    return 0 if not gaps else 1


if __name__ == "__main__":
    sys.exit(main())
