"""
Fetch latest data from GitHub repository
Run this script to update local data files from GitHub

Usage:
    python fetch_from_github.py

For scheduled updates, you can use:
    - Windows Task Scheduler
    - Or run with --schedule flag to keep running with auto-updates
"""

import os
import requests
import time
import argparse
from datetime import datetime
from pathlib import Path

# Configuration
GITHUB_REPO = "FameIllusionMaya/Relative_Rotation_Graph"
GITHUB_BRANCH = "master"
BASE_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}"

# Sectors to download
SECTORS = [
    "SET", "AGRI", "AUTO", "BANK", "COMM", "CONMAT", "CONSUMP", "ENERG",
    "ETRON", "FIN", "FOOD", "HELTH", "HOME", "ICT", "IMM", "INDUS",
    "INSUR", "MEDIA", "MINE", "PAPER", "PERSON", "PETRO", "PF&REIT",
    "PKG", "PROF", "PROP", "STEEL", "TOURISM", "TRANS"
]

# Data directories
DATA_DIR = Path(__file__).parent / "data"
DAILY_DIR = DATA_DIR / "daily"
HOURLY_DIR = DATA_DIR / "1h"


def download_file(url: str, local_path: Path) -> bool:
    """Download a file from URL to local path."""
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(response.content)
            return True
        else:
            print(f"  Failed to download {url}: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"  Error downloading {url}: {e}")
        return False


def fetch_all_data() -> dict:
    """Fetch all sector data from GitHub."""
    print(f"\n{'='*60}")
    print(f"  Fetching data from GitHub")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    results = {"success": 0, "failed": 0}

    # Fetch daily data
    print("Fetching daily data...")
    for sector in SECTORS:
        url = f"{BASE_URL}/data/daily/{sector}.csv"
        local_path = DAILY_DIR / f"{sector}.csv"
        if download_file(url, local_path):
            print(f"  [OK] daily/{sector}.csv")
            results["success"] += 1
        else:
            results["failed"] += 1

    print()

    # Fetch hourly data
    print("Fetching 1h data...")
    for sector in SECTORS:
        url = f"{BASE_URL}/data/1h/{sector}.csv"
        local_path = HOURLY_DIR / f"{sector}.csv"
        if download_file(url, local_path):
            print(f"  [OK] 1h/{sector}.csv")
            results["success"] += 1
        else:
            results["failed"] += 1

    print(f"\n{'='*60}")
    print(f"  Completed: {results['success']} success, {results['failed']} failed")
    print(f"{'='*60}\n")

    return results


def run_scheduled(interval_minutes: int = 60):
    """Run fetch on a schedule."""
    print(f"Running scheduled updates every {interval_minutes} minutes...")
    print("Press Ctrl+C to stop\n")

    while True:
        fetch_all_data()
        print(f"Next update in {interval_minutes} minutes...\n")
        time.sleep(interval_minutes * 60)


def main():
    parser = argparse.ArgumentParser(description="Fetch data from GitHub")
    parser.add_argument(
        "--schedule",
        type=int,
        metavar="MINUTES",
        help="Run continuously with updates every N minutes"
    )
    args = parser.parse_args()

    if args.schedule:
        run_scheduled(args.schedule)
    else:
        fetch_all_data()


if __name__ == "__main__":
    main()
