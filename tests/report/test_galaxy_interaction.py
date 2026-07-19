# -*- coding: utf-8 -*-
"""S6 인터랙션 QA — galaxy 실브라우저 동작 검증 (R6.7).

오라클 = CASH_GALAXY_STYLE_GUIDE A9(제스처 스크롤·PINNED/JOURNEY 2모드) + 기본 UX 불변식.
사용자 보고 버그 클래스: 스크롤 멈춤 / 한 제스처에 여러 정거장 점프 / 핀 해제 불능 / 펼침 고장.

실행: python -m http.server 8000 기동 후
  python -m pytest tests/report/test_galaxy_interaction.py -v --ticker(환경변수 GALAXY_TICKER, 기본 000660)
"""
import os
import time

import pytest

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # playwright 미설치 환경(CI 등)
    sync_playwright = None

TICKER = os.environ.get("GALAXY_TICKER", "000660")
URL = f"http://localhost:8000/integration/dossier/galaxy.html?ticker={TICKER}"

pytestmark = pytest.mark.skipif(sync_playwright is None, reason="playwright 미설치")


@pytest.fixture(scope="module")
def page():
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception:
            pytest.skip("playwright 브라우저 미설치 — `playwright install chromium` 필요(CI 등)")
        pg = browser.new_page(viewport={"width": 1440, "height": 1000})
        errs = []
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errs.append(str(e)))
        try:
            pg.goto(URL, wait_until="networkidle", timeout=60000)
        except Exception:
            browser.close()
            pytest.skip("http.server:8000 미기동 — 로컬 서빙 후 실행")
        pg.wait_for_selector("[data-left] svg", timeout=20000)
        time.sleep(3)
        pg._errs = errs
        yield pg
        browser.close()


def _active_journey_row(pg):
    """JOURNEY 하이라이트(data-jl=1) 행 id — 현재 정거장의 관측치."""
    el = pg.query_selector('[data-jl="1"]')
    return el.get_attribute("data-row") if el else None


_KNOT_ROWS = None


def _knot_rows():
    """정거장 좌표계 = knots[].row 순서 (DOM 전체 행이 아님 — is-pretax 같은 비정거장 행 제외)."""
    global _KNOT_ROWS
    if _KNOT_ROWS is None:
        import json
        g = json.load(open(f"integration/dossier/data/galaxy_{TICKER}.json", encoding="utf-8"))
        _KNOT_ROWS = [k["row"] for k in g["knots"]]
    return _KNOT_ROWS


def _station_index(pg):
    cur = _active_journey_row(pg)
    rows = _knot_rows()
    return rows.index(cur) if cur in rows else -1


def test_wheel_gesture_single_step(page):
    """A9-② 관성 제스처 안에서는 정거장 최대 1칸. (A9-③의 450ms 유휴 후 >3칸 단번 재동기화는 허용 스펙
    — 측정은 유휴 타이머가 발화하기 '전'(제스처 종료 +0.3s)에 해야 한다.)"""
    page.evaluate("window.scrollTo(0, 600)")
    time.sleep(1.0)
    before = _station_index(page)
    # 관성 스크롤 흉내: 120ms 안에 delta 여러 번 (하나의 제스처)
    for _ in range(6):
        page.mouse.wheel(0, 240)
        time.sleep(0.02)
    time.sleep(0.30)  # 450ms 유휴 동기화 발화 전 관측
    during = _station_index(page)
    if before < 0 or during < 0:
        pytest.skip("JOURNEY 하이라이트 미노출 상태(뷰포트 밖) — 정거장 관측 불가")
    assert during - before <= 1, f"제스처 안에서 {during - before}칸 이동 (A9-② 위반)"
    # A9-③: 유휴 후엔 목표로 재동기화될 수 있다(단번, 허용) — 크래시 없이 정착만 확인
    time.sleep(1.0)
    assert _station_index(page) >= during, "유휴 재동기화 후 정거장 역행"


def test_scroll_not_stuck(page):
    """스크롤이 멈추지 않는다 — wheel 후 scrollY 전진."""
    y0 = page.evaluate("window.scrollY")
    page.mouse.wheel(0, 800)
    time.sleep(0.8)
    y1 = page.evaluate("window.scrollY")
    assert y1 > y0, f"스크롤 멈춤: {y0} → {y1}"


def test_pin_and_escape(page):
    """행 클릭=PINNED 고정, Esc=JOURNEY 복귀 (A9 2모드)."""
    page.evaluate("window.scrollTo(0, 400)")
    time.sleep(0.6)
    page.click('[data-row="is-revenue"]')
    time.sleep(1.0)
    right = page.inner_text("[data-right]")
    assert "PINNED" in right, "클릭 후 PINNED 미진입"
    page.keyboard.press("Escape")
    time.sleep(0.8)
    right2 = page.inner_text("[data-right]")
    assert "PINNED" not in right2, "Esc로 핀 해제 안 됨"


def test_expand_toggle(page):
    """펼침 캐럿 토글 — 서브행 등장/소멸. 그룹 키(sgna/opex 등)는 회사 구조 따라 달라
    구조 무관하게 첫 캐럿을 잡아 행 수 증감으로 검증(제조=sgna, 플랫폼=opex)."""
    page.evaluate("window.scrollTo(0, 400)")
    time.sleep(0.5)
    car = page.query_selector("[data-g]")
    assert car, "펼침 캐럿 없음"
    g = car.get_attribute("data-g")
    car.scroll_into_view_if_needed()
    time.sleep(0.3)
    before = len(page.query_selector_all("[data-row]"))
    car.click()
    time.sleep(0.8)
    after = len(page.query_selector_all("[data-row]"))
    assert after > before, f"펼침 후 서브행 미등장 (g={g}: {before}→{after})"
    car.click()
    time.sleep(0.8)
    assert len(page.query_selector_all("[data-row]")) == before, f"접기 후 서브행 잔존 (g={g})"


def test_appendix_card_opens(page):
    """APPENDIX 행 클릭 → 카드에 본문(①)이 실제로 뜬다 (빈 카드 사고 회귀)."""
    apx = page.query_selector('[data-row^="n"]')
    assert apx, "APPENDIX 행 없음"
    apx.scroll_into_view_if_needed()
    time.sleep(0.5)
    apx.click()
    time.sleep(1.0)
    right = page.inner_text("[data-right]")
    assert "무엇인가요" in right, "APPENDIX 카드 본문 공란"
    page.keyboard.press("Escape")


def test_no_horizontal_scroll_1024(page):
    """1024px에서 가로 스크롤 금지 (반응형 불변식)."""
    page.set_viewport_size({"width": 1024, "height": 900})
    time.sleep(1.0)
    over = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    page.set_viewport_size({"width": 1440, "height": 1000})
    assert over <= 2, f"가로 오버플로 {over}px"


def test_toc_note_pin_authored_only(page):
    """주석 착지 결정론(V-084 · R6.10): 주석 클릭은 '저작된 경로'로만 착지한다.

    계약: 각 주석 클릭 시 _pinForNote는 (a) 저작된 카드에 핀(전용카드 n{N}·note_dive[N]·
    원장 명시타깃 appendix:/new-dive:/row:) 하거나 (b) 무핀(원문만 — 저작된 홈 없음)이다.
    ⚠️ 산문 "(주N)" 상호참조 fuzzy 스캔으로 착지하는 '오핀'은 금지(주20 공정가치→위험관리 버그).
    pin/unpin을 가로채 기록만 하므로(상태 무변경) setState 비동기와 무관하게 결정적."""
    import json

    g = json.load(open(f"integration/dossier/data/galaxy_{TICKER}.json", encoding="utf-8"))
    meta = g.get("meta") or {}
    notes = list(meta.get("routing_ledger", {}).keys())
    assert notes, "routing_ledger 비어있음"
    bad = page.evaluate(
        """(notes) => {
      const el = document.querySelector('[data-row]');
      let inst = null;
      for (const k in el) if (k.startsWith('__reactFiber$')) {
        let f = el[k];
        while (f) {
          const s = f.stateNode;
          if (s && s._pinForNote) { inst = s; break; }
          if (s && s.logic && s.logic._pinForNote) { inst = s.logic; break; }  // dc-runtime: 래퍼.logic
          f = f.return;
        }
      }
      if (!inst) return ['NO_INSTANCE'];
      const G = inst._G || {}; const meta = G.meta || {};
      const nd = meta.note_dive || {}, led = meta.routing_ledger || {};
      const D = inst.getDives();
      // 저작된 착지 키인지 판정 (fuzzy 아님)
      const authorized = (n, key) => {
        if (key === 'n' + n) return true;
        if (nd[n] === key) return true;
        const to = (led[n] || {}).to || '';
        if (to === 'appendix:' + key || to === 'new-dive:' + key) return true;
        if (to.indexOf('row:') === 0) return true;  // row 타깃(§9가 실존 검증)
        return false;
      };
      const origP = inst.pin, origU = inst.unpin; const rec = [];
      inst.pin = (key) => { rec.push(key); };
      inst.unpin = () => { rec.push(null); };
      const bad = [];
      try {
        for (const n of notes) {
          rec.length = 0; inst._pinForNote(n);
          const key = rec.length ? rec[rec.length - 1] : null;
          if (key !== null && !authorized(n, key)) bad.push(n + '→' + key);  // 오핀(fuzzy)
        }
      } finally { inst.pin = origP; inst.unpin = origU; }
      return bad;
    }""",
        notes,
    )
    assert bad == [], f"저작되지 않은 오핀(fuzzy) 착지 {len(bad)}건: {bad}"


def test_no_fuzzy_scan_in_renderer(page):
    """R6.10 회귀 방지: _pinForNote에 산문 스캔 fuzzy 폴백('for (const k in D)' + re.test)이 재도입되지 않았는지."""
    src = page.evaluate(
        """() => {
      const el = document.querySelector('[data-row]');
      for (const k in el) if (k.startsWith('__reactFiber$')) {
        let f = el[k];
        while (f) {
          const s = f.stateNode;
          const inst = (s && s._pinForNote) ? s : (s && s.logic && s.logic._pinForNote ? s.logic : null);
          if (inst) return inst._pinForNote.toString();
          f = f.return;
        }
      }
      return 'NO_INSTANCE';
    }"""
    )
    assert src != "NO_INSTANCE", "인스턴스 못 찾음"
    assert "for (const k in D)" not in src, "fuzzy 산문 스캔 폴백이 _pinForNote에 재도입됨(R6.10 위반)"


def test_identity_highlight(page):
    """항등식 HL(V-075, A9 합계→구성): 합계 행 클릭 시 구성 행 동반 발광 + Esc 잔광 0."""
    cases = [
        ("is-grossprofit", ["is-revenue", "is-cogs"]),
        ("is-pretax", ["is-opincome", "is-nonop"]),
    ]
    ran = False
    for via, comps in cases:
        el = page.query_selector(f'[data-row="{via}"]')
        if not el:
            continue  # 플랫폼(cogs 결측) 등 행 없는 티커는 해당 케이스 없음
        ran = True
        el.scroll_into_view_if_needed()
        time.sleep(0.3)
        el.click()
        time.sleep(0.7)
        for c in comps:
            ce = page.query_selector(f'[data-row="{c}"]')
            if ce:
                assert ce.get_attribute("data-hl") == "1", f"{via} 클릭 시 {c} 미발광"
        page.keyboard.press("Escape")
        time.sleep(0.4)
        ce = page.query_selector(f'[data-row="{via}"]')
        assert not (ce and ce.get_attribute("data-hl")), f"Esc 후 {via} 잔광"
    if not ran:
        pytest.skip("항등식 대상 행 없음(이 티커 레이아웃)")


def test_zero_console_errors(page):
    """상호작용 전 과정 콘솔 에러 0."""
    assert not page._errs, f"콘솔 에러 {len(page._errs)}: {page._errs[:2]}"
