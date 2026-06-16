#!/usr/bin/env python3
"""
Claude AI Investment Simulator - スケジューラーエントリーポイント

実行:
  python main.py

スケジュール (JST):
  毎日 07:00 - 朝の市場分析
  毎日 23:00 - 夕の最終判断・売買実行
  毎週日曜 22:00 - 週次反省会
"""
import logging
import sys
import os

from dotenv import load_dotenv
load_dotenv()

import pytz
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/scheduler.log", encoding="utf-8"),
    ],
)

logger = logging.getLogger(__name__)

from src.scheduler.jobs import InvestmentScheduler
from src.config import get_settings


def job_listener(event):
    if event.exception:
        logger.error(f"ジョブエラー: {event.job_id} - {event.exception}")
    else:
        logger.info(f"ジョブ完了: {event.job_id}")


def main():
    settings = get_settings()
    tz = pytz.timezone(settings.TIMEZONE)

    logger.info("=== Claude AI Investment Simulator 起動 ===")
    logger.info(f"タイムゾーン: {settings.TIMEZONE}")
    logger.info(f"Claude モデル: {settings.CLAUDE_MODEL}")

    os.makedirs("logs", exist_ok=True)

    scheduler_instance = InvestmentScheduler()
    scheduler = BlockingScheduler(timezone=tz)
    scheduler.add_listener(job_listener, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)

    # 朝の分析 (毎日 07:00 JST)
    scheduler.add_job(
        scheduler_instance.run_morning_analysis,
        CronTrigger(hour=7, minute=0, timezone=tz),
        id="morning_analysis",
        name="朝の市場分析",
        max_instances=1,
        misfire_grace_time=1800,
    )

    # 夕の判断 (毎日 23:00 JST)
    scheduler.add_job(
        scheduler_instance.run_evening_analysis,
        CronTrigger(hour=23, minute=0, timezone=tz),
        id="evening_analysis",
        name="夕の最終判断",
        max_instances=1,
        misfire_grace_time=1800,
    )

    # 週次反省会 (毎週日曜 22:00 JST)
    scheduler.add_job(
        scheduler_instance.run_weekly_review,
        CronTrigger(day_of_week="sun", hour=22, minute=0, timezone=tz),
        id="weekly_review",
        name="週次反省会",
        max_instances=1,
        misfire_grace_time=3600,
    )

    logger.info("スケジューラー設定完了:")
    for job in scheduler.get_jobs():
        logger.info(f"  - {job.name}: {job.trigger}")

    logger.info("スケジューラー開始... (Ctrl+C で停止)")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("スケジューラー停止")


if __name__ == "__main__":
    main()
