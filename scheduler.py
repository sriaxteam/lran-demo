"""
Scheduler
매일 07:00, 19:00에 orchestrator를 자동 실행
Windows / Mac / Linux 모두 동작
"""

import logging
import sys
import time

import schedule

from config import SCHEDULE_TIMES
from orchestrator import run as run_pipeline

logger = logging.getLogger("scheduler")


def job():
    logger.info("스케줄 실행 시작")
    try:
        run_pipeline()
    except Exception as e:
        logger.error(f"파이프라인 오류: {e}", exc_info=True)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    for t in SCHEDULE_TIMES:
        schedule.every().day.at(t).do(job)
        logger.info(f"스케줄 등록: 매일 {t}")

    logger.info("스케줄러 실행 중... (Ctrl+C로 종료)")
    logger.info("즉시 실행하려면: python orchestrator.py")

    # 시작 시 1회 즉시 실행 옵션 (--now 플래그)
    if "--now" in sys.argv:
        logger.info("--now 플래그 감지: 즉시 실행")
        job()

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
