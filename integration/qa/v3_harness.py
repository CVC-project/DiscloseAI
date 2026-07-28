# -*- coding: utf-8 -*-
"""V-3 렌더 하네스 — universe/PLAN.md §5.5 (integration 소유, U2 게이트 실행 수단).

"엣지가 잘 그려졌는가"를 눈이 아니라 스크립트가 판정한다:
  기대값을 export JSON에서 자동 도출(수기 fixture 금지) → Playwright 실화면 대조 + 스크린샷 아카이브.

검증 층 3겹:
  [D] 데이터 계약  — ego 전 파일: dart_filing detail non-empty(FN-010 회귀), 참조 무결성
  [O] 오라클 대조  — UX-011 축 계약을 파이썬으로 독립 재구현 → 화면의 __egoDebug 분할과 비교
                     (bundle 로직을 그대로 믿지 않는다 — 스펙 재구현이라 양쪽 버그 모두 잡힘)
  [R] 렌더 실측    — 캔버스가 스테이지를 채우는가(FN-009 회귀), 토글 정확히 2개(UX-012),
                     shown 노드가 실제 히트 타깃으로 그려졌는가

시나리오 3종은 JSON에서 자동 선정(§5.5 "2,600사 확장에도 유지비 없음"):
  S1 대기업 계열(named400 + ftc_group 최다 이웃) · S2 비계열 중견(named400·ftc 0·지분≥2)
  · S3 코스닥 소형(dot·cb 0·엣지≥1)

실행: 프로젝트 루트에서  python integration/qa/v3_harness.py
전제: localhost:8777 서빙 중 (python -m http.server 8777) + 현 브랜치 데이터 (FN-007)
산출: integration/qa/v3/out/report.json + 시나리오별 스크린샷 (out/은 gitignore)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EGO_DIR = ROOT / "integration" / "data" / "ego"
INDEX_PATH = ROOT / "integration" / "data" / "companies_index.json"
OUT_DIR = ROOT / "integration" / "qa" / "v3" / "out"
BASE_URL = "http://localhost:8777/integration/v2/index.html"

TOP_N, SIDE_N = 6, 4  # bundle.jsx EgoView와 동일 상수 — 변경 시 양쪽 함께

# ── [O] 오라클: UX-011 축 계약의 독립 재구현 ──────────────────────────────────
# bundle.jsx를 이식하지 않고 원장 조문(UX-011)에서 다시 구현한다. 두 구현이 갈리면
# 어느 한쪽이 계약을 어긴 것 — 그 갈림 자체가 이 하네스의 검출 대상.

EGO_TYPE_MAP = {"subsidiary": "subsidiary", "associate": "associate",
                "investment": "significant", "ftc_group": "group",
                "dart_filing": "related", "manual": "manual"}
PRIO = {"subsidiary": 1, "associate": 2, "investment": 3,
        "ftc_group": 4, "dart_filing": 5, "manual": 6}
EQUITY_RAW = {"subsidiary", "associate", "investment"}


def oracle_merge(gov: list[dict]) -> list[dict]:
    by: dict[str, dict] = {}
    for r in gov:
        t = r.get("t")
        if not t:
            continue
        e = by.setdefault(t, {"code": t, "types": [], "dir_by_type": {}})
        if r["type"] not in e["types"]:
            e["types"].append(r["type"])
        e["dir_by_type"][r["type"]] = r.get("dir")
    out = []
    for e in by.values():
        e["types"].sort(key=lambda t: PRIO.get(t, 9))
        primary = e["types"][0]
        out.append({
            "code": e["code"],
            # UX-011: 세로 방향은 지분 엣지의 dir — primary는 hasEquity면 항상 지분 타입
            "incoming": e["dir_by_type"][primary] == "in",
            "rel_type": EGO_TYPE_MAP.get(primary, "manual"),
            "has_equity": any(t in EQUITY_RAW for t in e["types"]),
        })
    return out


def oracle_split(gov: list[dict]) -> dict:
    merged = oracle_merge(gov)
    vertical = [n for n in merged if n["has_equity"]]
    horizontal = [n for n in merged if not n["has_equity"]]
    sides = {
        "above": [n["code"] for n in vertical if n["incoming"]],
        "below": [n["code"] for n in vertical if not n["incoming"]],
        "left":  [n["code"] for n in horizontal if n["rel_type"] == "group"],
        "right": [n["code"] for n in horizontal if n["rel_type"] != "group"],
    }
    out = {}
    for k, arr in sides.items():
        cap = TOP_N if k in ("above", "below") else SIDE_N
        out[k] = {"shown": set(arr[:cap]) if len(arr) <= cap else None,  # 랭킹 동순위 모호 → 컷 초과 시 집합 대신 개수만 판정
                  "shown_count": min(len(arr), cap), "rest": max(0, len(arr) - cap),
                  "all": set(arr)}
    return out


# ── 시나리오 자동 선정 ────────────────────────────────────────────────────────

def load_ego(ticker: str) -> dict:
    return json.loads((EGO_DIR / f"{ticker}.json").read_text(encoding="utf-8"))


def pick_scenarios() -> list[dict]:
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    by_t = {c["t"]: c for c in index}
    stats = []
    for f in sorted(EGO_DIR.glob("*.json")):
        if f.name == "manifest.json":
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        gov = (d.get("layers") or {}).get("governance") or []
        if not gov:
            continue
        merged = oracle_merge(gov)
        stats.append({
            "t": d["t"], "n": d["n"], "neighbors": len(merged),
            "has_ftc": any("group" == m["rel_type"] or True for m in []) or any(
                e.get("type") == "ftc_group" for e in gov),
            "equity_cnt": sum(1 for m in merged if m["has_equity"]),
            "meta": by_t.get(d["t"], {}),
        })
    named = [s for s in stats if s["meta"].get("tier") == "named400"]
    s1 = max((s for s in named if s["has_ftc"]), key=lambda s: s["neighbors"])
    s2_pool = [s for s in named if not s["has_ftc"] and s["equity_cnt"] >= 2]
    s2 = max(s2_pool, key=lambda s: s["neighbors"])
    s3_pool = [s for s in stats
               if s["meta"].get("mkt") == "KOSDAQ" and s["meta"].get("tier") == "dot"
               and s["meta"].get("cb", 9) == 0]
    s3 = sorted(s3_pool, key=lambda s: s["t"])[0]
    return [
        {"label": "S1 대기업 계열", "t": s1["t"], "n": s1["n"], "meta": s1["meta"]},
        {"label": "S2 비계열 중견", "t": s2["t"], "n": s2["n"], "meta": s2["meta"]},
        {"label": "S3 코스닥 소형", "t": s3["t"], "n": s3["n"], "meta": s3["meta"]},
    ]


# ── [D] 데이터 계약 체크 (브라우저 불요, 전 파일) ────────────────────────────

def data_checks() -> list[dict]:
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    known = {c["t"] for c in index}
    fails = []
    n_files = n_filing = 0
    for f in EGO_DIR.glob("*.json"):
        if f.name == "manifest.json":
            continue
        n_files += 1
        d = json.loads(f.read_text(encoding="utf-8"))
        for e in (d.get("layers") or {}).get("governance") or []:
            if e.get("type") == "dart_filing":
                n_filing += 1
                if not e.get("detail"):
                    fails.append({"check": "FN-010 dart_filing detail non-empty",
                                  "file": f.name, "edge": e.get("t")})
            if ":" in (e.get("detail") or ""):
                fails.append({"check": "detail에 콜론 금지(rl-string 3분할 보호)",
                              "file": f.name, "edge": e.get("t")})
            if e.get("t") and e["t"] not in known:
                fails.append({"check": "이웃 티커 참조 무결성(companies_index)",
                              "file": f.name, "edge": e.get("t")})
    return [{"name": "data", "files": n_files, "dart_filing_edges": n_filing,
             "failures": fails, "ok": not fails}]


# ── [O]+[R] 브라우저 시나리오 ────────────────────────────────────────────────

DRILL_JS = """async ([sectorKo, mkt, name]) => {
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  const chip = [...document.querySelectorAll('.sector-chip')]
    .find(e => (e.querySelector('.sector-ko')||{}).textContent === sectorKo);
  if (!chip) return {err: 'sector chip not found: ' + sectorKo};
  chip.click(); await sleep(300);
  const cta = document.querySelector('.selected-cta');
  if (!cta) return {err: 'ENTER SECTOR cta not found'};
  cta.click(); await sleep(1600);
  const cvs = document.querySelector('.solar-canvas');
  const b = cvs.getBoundingClientRect();
  const baseR = Math.min(b.width, b.height) * 0.34;
  const px = b.left + b.width/2 + (mkt === 'KOSPI' ? -0.85 : 0.85) * baseR;
  for (const t of ['mousedown','mouseup','click'])
    cvs.dispatchEvent(new MouseEvent(t, {clientX: px, clientY: b.top + b.height/2, bubbles: true}));
  await sleep(800);
  const rows = [...document.querySelectorAll('.sector-overview-panel li')];
  const row = rows.find(li => {
    const sp = li.querySelector('span[style*="flex"]');
    return sp && sp.textContent === name;
  });
  if (!row) return {err: 'company row not found: ' + name, rows: rows.length};
  row.click(); await sleep(1500);
  return {ok: true};
}"""

COLLECT_JS = """() => {
  const c = document.querySelector('.ego-canvas');
  const stage = document.querySelector('.sector-map-stage');
  const dbg = window.__egoDebug || null;
  return {
    egoCanvas: !!c,
    canvasBox: c ? (({width,height}) => ({w: Math.round(width), h: Math.round(height)}))(c.getBoundingClientRect()) : null,
    stageBox: stage ? (({width,height}) => ({w: Math.round(width), h: Math.round(height)}))(stage.getBoundingClientRect()) : null,
    topbarButtons: [...document.querySelectorAll('.ego-topbar button')].map(b => b.textContent.trim()),
    dbg,
  };
}"""


def run_scenario(browser, scenario: dict) -> dict:
    from playwright.sync_api import Error as PwError  # noqa: F401
    t, name = scenario["t"], scenario["n"]
    meta = scenario["meta"]
    res = {"label": scenario["label"], "ticker": t, "name": name, "checks": []}

    def check(cname, ok, detail=""):
        res["checks"].append({"check": cname, "ok": bool(ok), "detail": str(detail)[:200]})

    page = browser.new_page(viewport={"width": 1600, "height": 900})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    try:
        page.goto(f"{BASE_URL}?v3={t}", wait_until="load")
        page.wait_for_timeout(900)
        nav = page.evaluate(DRILL_JS, [meta.get("s"), meta.get("mkt"), name])
        if not nav.get("ok"):
            check("드릴인 네비게이션", False, nav)
            return res
        got = page.evaluate(COLLECT_JS)
        dbg = got.get("dbg")

        # [R] 렌더 실측
        check("R: ego 캔버스 마운트", got["egoCanvas"])
        cb, sb = got.get("canvasBox"), got.get("stageBox")
        check("R: 캔버스=스테이지 크기(FN-009)",
              cb and sb and abs(cb["w"] - sb["w"]) < 3 and abs(cb["h"] - sb["h"]) < 3,
              f"canvas={cb} stage={sb}")
        check("R: 토글 정확히 2개(UX-012)",
              got["topbarButtons"] == ["지배구조", "밸류체인"], got["topbarButtons"])
        check("R: __egoDebug 앵커 일치", dbg and dbg.get("anchor") == t,
              dbg and dbg.get("anchor"))

        # [O] 오라클 대조 — 축 소속·개수·잔여
        gov = (load_ego(t).get("layers") or {}).get("governance") or []
        exp = oracle_split(gov)
        if dbg:
            for side in ("above", "below", "left", "right"):
                actual = dbg.get(side) or []
                e = exp[side]
                ok_cnt = len(actual) == e["shown_count"] and dbg.get(side + "Rest") == e["rest"]
                # 컷 미발동(전원 표시)이면 집합까지, 컷 발동이면 소속(all 부분집합)만
                ok_set = (set(actual) == e["shown"]) if e["shown"] is not None \
                    else set(actual).issubset(e["all"])
                check(f"O: {side} 분할 (개수 {e['shown_count']}·잔여 {e['rest']})",
                      ok_cnt and ok_set,
                      f"actual={sorted(actual)} rest={dbg.get(side + 'Rest')}")
            shown_all = set().union(*[set(dbg.get(s) or []) for s in ("above", "below", "left", "right")])
            rendered = set(dbg.get("renderedCodes") or [])
            check("R: shown 전원 실제 렌더(히트 타깃)", shown_all <= rendered,
                  f"missing={sorted(shown_all - rendered)}")
        check("R: JS 페이지 에러 0건", not errors, errors[:2])

        shot = OUT_DIR / f"{scenario['label'].split()[0]}_{t}.png"
        page.screenshot(path=str(shot))
        res["screenshot"] = shot.name
    finally:
        page.close()
    return res


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    report = {"data": data_checks(), "scenarios": []}
    scenarios = pick_scenarios()
    print("scenario picks:", [(s["label"], s["t"], s["n"]) for s in scenarios])

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for sc in scenarios:
            report["scenarios"].append(run_scenario(browser, sc))
        browser.close()

    all_checks = ([c for d in report["data"] for c in [{"check": "D: " + f["check"], "ok": False, "detail": f} for f in d["failures"]]]
                  or [{"check": "D: 전 ego 파일 데이터 계약", "ok": True, "detail": report["data"][0]}])
    all_checks += [c for s in report["scenarios"] for c in s["checks"]]
    n_fail = sum(1 for c in all_checks if not c["ok"])
    report["summary"] = {"total": len(all_checks), "fail": n_fail,
                         "verdict": "PASS" if n_fail == 0 else "FAIL"}
    (OUT_DIR / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    for c in all_checks:
        print(("PASS " if c["ok"] else "FAIL "), c["check"],
              ("" if c["ok"] else " | " + str(c["detail"])[:160]))
    print(f"== V-3 {report['summary']['verdict']} ({len(all_checks) - n_fail}/{len(all_checks)}) -> {OUT_DIR / 'report.json'}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
