"""
run_matching.py
---------------
CLI entry point for product matching.

Usage:
    python src/matching/run_matching.py --db data/price_comparison.db --threshold 85

Options:
    --db          Path to the SQLite database  (default: data/price_comparison.db)
    --threshold   Minimum fuzzy score to accept a match (default: 85)
"""

import argparse
import os
import sys

# Allow running as a script from the project root without installing as a package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.matching.fuzzy_match import match_products


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Match Amazon products to Flipkart products using fuzzy name similarity."
    )
    parser.add_argument(
        "--db",
        default="data/price_comparison.db",
        help="Path to the SQLite database (default: data/price_comparison.db)",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=85,
        help="Minimum token_sort_ratio score to accept a match (default: 85)",
    )
    args = parser.parse_args()

    db_path: str = args.db
    threshold: int = args.threshold

    if not os.path.exists(db_path):
        print(f"[error] Database not found: {os.path.abspath(db_path)}")
        sys.exit(1)

    print(f"[run_matching] DB:        {os.path.abspath(db_path)}")
    print(f"[run_matching] Threshold: {threshold}")
    print()

    summary, results_df = match_products(db_path, threshold=threshold)

    # ------------------------------------------------------------------
    # Print summary
    # ------------------------------------------------------------------
    print("=" * 45)
    print("  Matching Summary")
    print("=" * 45)
    print(f"  Total Amazon products   : {summary['total_amazon']}")
    print(f"  Total Flipkart products : {summary['total_flipkart']}")
    print(f"  Matches found           : {summary['matches_found']}")
    print(f"  New matches saved to DB : {summary['matches_saved']}")
    print("=" * 45)

    # ------------------------------------------------------------------
    # Save full results to CSV
    # ------------------------------------------------------------------
    output_csv = os.path.join(os.path.dirname(db_path), "match_results.csv")
    if not results_df.empty:
        results_df.to_csv(output_csv, index=False)
        print(f"\n[run_matching] Results saved to: {os.path.abspath(output_csv)}")
    else:
        print("\n[run_matching] No matches found; CSV not written.")


if __name__ == "__main__":
    main()
