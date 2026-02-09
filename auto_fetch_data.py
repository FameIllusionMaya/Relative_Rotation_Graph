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
from datetime import datetime

import pandas as pd
from tvDatafeed import TvDatafeed, Interval

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
            print(f"  [FAIL] {symbol}: {e}")

        if attempt < max_retries - 1:
            time.sleep(wait_time)

    return None


def fetch_data(interval_type="both"):
    """Fetch sector data from TradingView."""
    print(f"\n{'='*60}")
    print(f"  Fetching data from TradingView")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    intervals_to_fetch = []
    if interval_type == "both":
        intervals_to_fetch = ["1h", "daily"]
    else:
        intervals_to_fetch = [interval_type]

    results = {"success": 0, "failed": 0}

    for int_type in intervals_to_fetch:
        cfg = INTERVAL_MAP[int_type]
        out_dir = os.path.join(DATA_DIR, cfg["subdir"])
        os.makedirs(out_dir, exist_ok=True)

        print(f"Fetching {int_type} data...")

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
                    print(f"  [OK] {int_type}/{symbol}.csv")
                    results["success"] += 1
                except Exception as e:
                    print(f"  [FAIL] {symbol}: {e}")
                    results["failed"] += 1
            else:
                print(f"  [FAIL] {symbol}: No data")
                results["failed"] += 1

            time.sleep(2)  # Rate limiting

        print()

    print(f"{'='*60}")
    print(f"  Done: {results['success']} success, {results['failed']} failed")
    print(f"{'='*60}\n")


def run_scheduled():
    """Run on schedule during market hours."""
    print("Starting scheduled data fetcher...")
    print("Schedule:")
    print("  - Hourly (1h data): 10:20, 11:20, 12:20, 14:20, 15:20, 16:20 (Mon-Fri)")
    print("  - Daily data: 18:00 (Mon-Fri)")
    print("\nPress Ctrl+C to stop\n")

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
    while True:
        schedule.run_pending()
        time.sleep(60)


def main():
    parser = argparse.ArgumentParser(description="Auto fetch SET sector data from TradingView")
    parser.add_argument("--schedule", action="store_true", help="Run on schedule (market hours)")
    parser.add_argument("--interval", choices=["daily", "1h", "both"], default="both",
                        help="Data interval to fetch (default: both)")
    args = parser.parse_args()

    if args.schedule:
        run_scheduled()
    else:
        fetch_data(interval_type=args.interval)


if __name__ == "__main__":
    main()
