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
        browser = p.chromium.launch()
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
    """펼침 캐럿 토글 — 서브행 등장/소멸."""
    page.evaluate("window.scrollTo(0, 400)")
    time.sleep(0.5)
    car = page.query_selector('[data-g="sgna"]')
    assert car, "sgna 캐럿 없음"
    car.click()
    time.sleep(0.8)
    assert page.query_selector('[data-row^="is-sgna-"]'), "펼침 후 서브행 미등장"
    car.click()
    time.sleep(0.8)
    assert not page.query_selector('[data-row^="is-sgna-"]'), "접기 후 서브행 잔존"


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


def test_zero_console_errors(page):
    """상호작용 전 과정 콘솔 에러 0."""
    assert not page._errs, f"콘솔 에러 {len(page._errs)}: {page._errs[:2]}"
