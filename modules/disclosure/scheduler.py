"""
modules/disclosure/scheduler.py
공시 자동 수집 스케줄러

실행:
    python -m modules.disclosure.scheduler

스케줄:
    - 매일 07:00 — 배치 수집 (전날 누락분 포함)
    - 장중 09:00~15:30 — 30분마다 폴링
    - 매일 19:00 — 야간 투자자용 추가 수집
"""

import schedule
import time
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def run_collect():
    """신규 공시 수집 → 남은 Groq 한도로 과거 미분석 백필."""
    log.info("수집 시작...")
    try:
        from modules.disclosure.collector import collect, backfill_ai

        collect()
        log.info("수집 완료. 백필 시작...")
        filled = backfill_ai(max_records=50)
        log.info(f"백필 완료: {filled}건")
    except Exception as e:
        log.error(f"수집/백필 중 오류 발생: {e}")


def is_market_hours() -> bool:
    """현재 시각이 장중(09:00~15:30)인지 확인."""
    now = datetime.now().time()
    from datetime import time as t

    return t(9, 0) <= now <= t(15, 30)


def market_hours_job():
    """장중에만 실행되는 30분 폴링 잡."""
    if is_market_hours():
        log.info("[장중 폴링] 실행")
        run_collect()
    else:
        log.debug("[장중 폴링] 장외 시간 — 스킵")


def run_financial_update():
    """분기 재무제표 업데이트 — 매월 1일 새벽 실행."""
    log.info("[재무제표] 업데이트 시작...")
    try:
        from modules.disclosure.collector import fetch_financial_statements

        fetch_financial_statements(quarters=8)
        log.info("[재무제표] 업데이트 완료.")
    except Exception as e:
        log.error(f"[재무제표] 오류: {e}")


def setup_schedule():
    # 오전 7시 배치
    schedule.every().day.at("07:00").do(run_collect).tag("배치")

    # 장중 30분마다 폴링 (09:00~15:30)
    for hour in range(9, 16):
        for minute in ["00", "30"]:
            t = f"{hour:02d}:{minute}"
            if t <= "15:30":
                schedule.every().day.at(t).do(market_hours_job).tag("장중폴링")

    # 오후 7시 야간 수집
    schedule.every().day.at("19:00").do(run_collect).tag("야간")

    # 매월 1일 새벽 6시 재무제표 업데이트
    schedule.every().day.at("06:00").do(
        lambda: run_financial_update() if datetime.now().day == 1 else None
    ).tag("재무업데이트")

    log.info("스케줄 등록 완료:")
    log.info("  - 07:00 배치 수집")
    log.info("  - 09:00~15:30 30분마다 장중 폴링")
    log.info("  - 19:00 야간 수집")
    log.info("  - 매월 1일 06:00 재무제표 업데이트")


if __name__ == "__main__":
    log.info("DiscloseAI 공시 스케줄러 시작")
    setup_schedule()

    # 시작 즉시 1회 수집
    log.info("초기 수집 실행...")
    run_collect()

    log.info("스케줄러 대기 중... (종료: Ctrl+C)")
    while True:
        schedule.run_pending()
        time.sleep(30)
