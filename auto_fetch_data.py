"""
Auto Fetch Data - Fetches SET sector data directly from TradingView
Runs on schedule during market hours

Usage:
    python auto_fetch_data.py                    # Run once
    python auto_fetch_data.py --schedule         # Run on schedule (market hours)
    python auto_fetch_data.py --interval 1h      # Fetch 1h data only
    python auto_fetch_data.py --interval daily   # Fetch daily data only
"""

import argparse
import os
import time
import schedule
import logging
from datetime import datetime

import pandas as pd
from tvDatafeed import TvDatafeed, Interval

# Setup logging
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "data_fetch.log"), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize TradingView datafeed
tv = TvDatafeed()

# Sectors (same as fetch_sector_data.py)
SECTORS = [
    "SET",
    "AGRI", "FOOD",
    "FASHION", "HOME", "PERSON",
    "BANK", "FIN", "INSUR",
    "AUTO", "IMM", "PAPER", "PETRO", "PKG", "STEEL",
    "CONMAT", "CONS", "PF_REIT", "PROP",
    "ENERG", "MINE",
    "COMM", "HELTH", "MEDIA", "PROF", "TOURISM", "TRANS",
    "ETRON", "ICT"
]

INTERVAL_MAP = {
    "daily": {"interval": Interval.in_daily, "n_bars": 5000, "subdir": "daily"},
    "1h":    {"interval": Interval.in_1_hour, "n_bars": 1000, "subdir": "1h"},
}

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def fetch_with_retry(symbol, interval, n_bars, max_retries=3, wait_time=20):
    """Fetch data with retry mechanism."""
    for attempt in range(max_retries):
        try:
            stock_data = tv.get_hist(
                symbol=symbol,
                exchange='SET',
                interval=interval,
                n_bars=n_bars
            )
            if stock_data is not None and not stock_data.empty:
                return stock_data
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"  [RETRY] {symbol} attempt {attempt + 1}/{max_retries}: {e}")
            else:
                logger.error(f"  [FAIL] {symbol}: {e}")

        if attempt < max_retries - 1:
            time.sleep(wait_time)

    return None


def verify_file(filepath):
    """Verify that CSV file exists and has valid data."""
    try:
        if not os.path.exists(filepath):
            return False, "File not found"

        df = pd.read_csv(filepath)
        if df.empty:
            return False, "Empty file"

        return True, f"{len(df)} rows"
    except Exception as e:
        return False, str(e)


def fetch_data(interval_type="both"):
    """Fetch sector data from TradingView."""
    start_time = datetime.now()

    logger.info("=" * 60)
    logger.info("  STARTING DATA FETCH")
    logger.info(f"  Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"  Interval: {interval_type}")
    logger.info("=" * 60)

    intervals_to_fetch = []
    if interval_type == "both":
        intervals_to_fetch = ["1h", "daily"]
    else:
        intervals_to_fetch = [interval_type]

    results = {
        "success": 0,
        "failed": 0,
        "failed_symbols": [],
        "success_symbols": []
    }

    for int_type in intervals_to_fetch:
        cfg = INTERVAL_MAP[int_type]
        out_dir = os.path.join(DATA_DIR, cfg["subdir"])
        os.makedirs(out_dir, exist_ok=True)

        logger.info(f"\nFetching {int_type} data ({len(SECTORS)} sectors)...")

        for symbol in SECTORS:
            stock_data = fetch_with_retry(
                symbol,
                cfg["interval"],
                cfg["n_bars"]
            )

            if stock_data is not None:
                try:
                    # Fix timezone for 1h data (Thailand is UTC+7)
                    if int_type == "1h":
                        stock_data.index = stock_data.index + pd.Timedelta(hours=7)

                    filepath = os.path.join(out_dir, f'{symbol}.csv')
                    stock_data.to_csv(filepath)

                    # Verify the saved file
                    is_valid, msg = verify_file(filepath)
                    if is_valid:
                        logger.info(f"  [OK] {int_type}/{symbol}.csv - {msg}")
                        results["success"] += 1
                        results["success_symbols"].append(f"{int_type}/{symbol}")
                    else:
                        logger.error(f"  [FAIL] {int_type}/{symbol}.csv - Verification failed: {msg}")
                        results["failed"] += 1
                        results["failed_symbols"].append(f"{int_type}/{symbol}")

                except Exception as e:
                    logger.error(f"  [FAIL] {symbol}: {e}")
                    results["failed"] += 1
                    results["failed_symbols"].append(f"{int_type}/{symbol}")
            else:
                logger.error(f"  [FAIL] {symbol}: No data returned from TradingView")
                results["failed"] += 1
                results["failed_symbols"].append(f"{int_type}/{symbol}")

            time.sleep(2)  # Rate limiting

    # Calculate duration
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # Determine status
    total = results["success"] + results["failed"]
    if results["failed"] == 0:
        status = "SUCCESS"
    elif results["success"] == 0:
        status = "FAILED"
    else:
        status = "PARTIAL"

    # Print summary
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"  FETCH COMPLETED - {status}")
    logger.info("=" * 60)
    logger.info(f"  Status:    {status}")
    logger.info(f"  Time:      {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"  Duration:  {duration:.1f} seconds")
    logger.info(f"  Success:   {results['success']}/{total}")
    logger.info(f"  Failed:    {results['failed']}/{total}")

    if results["failed_symbols"]:
        logger.warning(f"  Failed symbols: {', '.join(results['failed_symbols'])}")

    logger.info("=" * 60)
    logger.info("")

    return status, results


def run_scheduled():
    """Run on schedule during market hours."""
    logger.info("=" * 60)
    logger.info("  STARTING SCHEDULED DATA FETCHER")
    logger.info("=" * 60)
    logger.info("Schedule:")
    logger.info("  - Hourly (1h data): 10:20, 11:20, 12:20, 14:20, 15:20, 16:20 (Mon-Fri)")
    logger.info("  - Daily data: 18:00 (Mon-Fri)")
    logger.info("")
    logger.info("Log file: logs/data_fetch.log")
    logger.info("Press Ctrl+C to stop")
    logger.info("")

    # Hourly updates during market hours (1h data only)
    schedule.every().monday.at("10:20").do(fetch_data, interval_type="1h")
    schedule.every().monday.at("11:20").do(fetch_data, interval_type="1h")
    schedule.every().monday.at("12:20").do(fetch_data, interval_type="1h")
    schedule.every().monday.at("14:20").do(fetch_data, interval_type="1h")
    schedule.every().monday.at("15:20").do(fetch_data, interval_type="1h")
    schedule.every().monday.at("16:20").do(fetch_data, interval_type="1h")

    schedule.every().tuesday.at("10:20").do(fetch_data, interval_type="1h")
    schedule.every().tuesday.at("11:20").do(fetch_data, interval_type="1h")
    schedule.every().tuesday.at("12:20").do(fetch_data, interval_type="1h")
    schedule.every().tuesday.at("14:20").do(fetch_data, interval_type="1h")
    schedule.every().tuesday.at("15:20").do(fetch_data, interval_type="1h")
    schedule.every().tuesday.at("16:20").do(fetch_data, interval_type="1h")

    schedule.every().wednesday.at("10:20").do(fetch_data, interval_type="1h")
    schedule.every().wednesday.at("11:20").do(fetch_data, interval_type="1h")
    schedule.every().wednesday.at("12:20").do(fetch_data, interval_type="1h")
    schedule.every().wednesday.at("14:20").do(fetch_data, interval_type="1h")
    schedule.every().wednesday.at("15:20").do(fetch_data, interval_type="1h")
    schedule.every().wednesday.at("16:20").do(fetch_data, interval_type="1h")

    schedule.every().thursday.at("10:20").do(fetch_data, interval_type="1h")
    schedule.every().thursday.at("11:20").do(fetch_data, interval_type="1h")
    schedule.every().thursday.at("12:20").do(fetch_data, interval_type="1h")
    schedule.every().thursday.at("14:20").do(fetch_data, interval_type="1h")
    schedule.every().thursday.at("15:20").do(fetch_data, interval_type="1h")
    schedule.every().thursday.at("16:20").do(fetch_data, interval_type="1h")

    schedule.every().friday.at("10:20").do(fetch_data, interval_type="1h")
    schedule.every().friday.at("11:20").do(fetch_data, interval_type="1h")
    schedule.every().friday.at("12:20").do(fetch_data, interval_type="1h")
    schedule.every().friday.at("14:20").do(fetch_data, interval_type="1h")
    schedule.every().friday.at("15:20").do(fetch_data, interval_type="1h")
    schedule.every().friday.at("16:20").do(fetch_data, interval_type="1h")

    # Daily update after market close (daily data)
    schedule.every().monday.at("18:00").do(fetch_data, interval_type="daily")
    schedule.every().tuesday.at("18:00").do(fetch_data, interval_type="daily")
    schedule.every().wednesday.at("18:00").do(fetch_data, interval_type="daily")
    schedule.every().thursday.at("18:00").do(fetch_data, interval_type="daily")
    schedule.every().friday.at("18:00").do(fetch_data, interval_type="daily")

    # Run loop
    logger.info("Waiting for scheduled tasks...")
    while True:
        schedule.run_pending()
        next_run = schedule.next_run()
        if next_run:
            time_until = (next_run - datetime.now()).total_seconds()
            if time_until > 0 and time_until < 120:  # Show when less than 2 minutes
                logger.info(f"Next fetch in {time_until:.0f} seconds...")
        time.sleep(60)


def main():
    parser = argparse.ArgumentParser(description="Auto fetch SET sector data from TradingView")
    parser.add_argument("--schedule", action="store_true", help="Run on schedule (market hours)")
    parser.add_argument("--interval", choices=["daily", "1h", "both"], default="both",
                        help="Data interval to fetch (default: both)")
    args = parser.parse_args()

    if args.schedule:
        try:
            run_scheduled()
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
    else:
        status, results = fetch_data(interval_type=args.interval)
        # Exit with error code if any failures
        if status == "FAILED":
            exit(1)
        elif status == "PARTIAL":
            exit(2)
        else:
            exit(0)


if __name__ == "__main__":
    main()
