"""
run_all_scrapers.py
-------------------
Convenience entry point to scrape all configured categories from both
Amazon and Flipkart in one shot.

Usage (from project root):
    python src/scrapers/run_all_scrapers.py
    python src/scrapers/run_all_scrapers.py --pages 3

Each scraper writes a pair of files to data/raw/:
    amazon_<category>.csv  /  amazon_<category>.json
    flipkart_<category>.csv / flipkart_<category>.json
"""

import argparse
import sys
import time
import random

from amazon_scraper import run as amazon_run
from flipkart_scraper import run as flipkart_run

# ---------------------------------------------------------------------------
# Configure scrape targets here.
# Each entry: (keyword, category_label)
# ---------------------------------------------------------------------------
AMAZON_TARGETS = [
    ("smartphones", "smartphones"),
    ("kitchen gadgets", "kitchen"),
]

FLIPKART_TARGETS = [
    ("smartphones", "smartphones"),
    ("kitchen gadgets", "kitchen"),
]


def main():
    parser = argparse.ArgumentParser(
        description="Run all configured Amazon + Flipkart scrapers."
    )
    parser.add_argument(
        "--pages", type=int, default=2,
        help="Number of search-result pages to fetch per target (default: 2)"
    )
    args = parser.parse_args()

    total_amazon = 0
    total_flipkart = 0
    errors = []

    # ── Amazon ────────────────────────────────────────────────────────────
    print("=" * 60)
    print("AMAZON SCRAPERS")
    print("=" * 60)
    for keyword, category in AMAZON_TARGETS:
        print(f"\n>>> Amazon | keyword='{keyword}' | category='{category}'")
        try:
            records = amazon_run(
                keyword=keyword,
                category=category,
                num_pages=args.pages,
            )
            total_amazon += len(records)
        except Exception as exc:
            msg = f"Amazon '{keyword}': {exc}"
            print(f"[ERROR] {msg}")
            errors.append(msg)
        # Polite gap between category runs
        time.sleep(random.uniform(2.0, 4.0))

    # ── Flipkart ──────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("FLIPKART SCRAPERS")
    print("=" * 60)
    for keyword, category in FLIPKART_TARGETS:
        print(f"\n>>> Flipkart | keyword='{keyword}' | category='{category}'")
        try:
            records = flipkart_run(
                keyword=keyword,
                category=category,
                num_pages=args.pages,
            )
            total_flipkart += len(records)
        except Exception as exc:
            msg = f"Flipkart '{keyword}': {exc}"
            print(f"[ERROR] {msg}")
            errors.append(msg)
        time.sleep(random.uniform(2.0, 4.0))

    # ── Summary ───────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Amazon   : {total_amazon} products collected")
    print(f"Flipkart : {total_flipkart} products collected")
    if errors:
        print(f"\n{len(errors)} error(s) encountered:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("\nAll scrapers completed successfully.")


if __name__ == "__main__":
    main()
