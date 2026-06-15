#!/usr/bin/env python3
"""夕の最終判断・売買実行を手動実行"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from src.scheduler.jobs import InvestmentScheduler


if __name__ == "__main__":
    scheduler = InvestmentScheduler()
    scheduler.run_evening_analysis()
