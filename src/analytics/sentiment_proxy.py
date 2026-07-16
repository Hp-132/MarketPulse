"""
Rating-derived sentiment proxy.

IMPORTANT / HONEST LIMITATION:
The scrapers (src/scrapers/amazon_scraper.py, flipkart_scraper.py) do not
extract individual review text — only aggregate `rating` and `review_count`
per product. A genuine text-based sentiment pipeline (VADER / TextBlob, as
originally scoped) needs review text to run on, so it cannot be implemented
against the current dataset without adding review-text scraping first.

This script fills the existing `reviews.sentiment_score` column with a
numeric proxy derived from `rating`, scaled to a -1..1 range the way VADER's
compound score is scaled, so it's a drop-in placeholder that keeps the
schema and downstream analytics working. It is NOT NLP sentiment and should
be labeled as a proxy in any report or dashboard that surfaces it.

Usage:
    python src/analytics/sentiment_proxy.py --db data/price_comparison.db
"""

import argparse
import sqlite3


def rating_to_score(rating: float) -> float:
    """Map a 0-5 rating to a -1..1 proxy score (linear rescale)."""
    if rating is None:
        return None
    return round((rating - 2.5) / 2.5, 3)


def label_for(rating: float) -> str:
    if rating is None:
        return "Unknown"
    if rating >= 4.5:
        return "Positive"
    if rating >= 3.5:
        return "Neutral"
    return "Negative"


def run(db_path: str) -> None:
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    cur.execute("SELECT review_id, rating FROM reviews")
    rows = cur.fetchall()

    updated = 0
    for review_id, rating in rows:
        score = rating_to_score(rating)
        cur.execute(
            "UPDATE reviews SET sentiment_score = ? WHERE review_id = ?",
            (score, review_id),
        )
        updated += 1

    con.commit()
    con.close()
    print(f"Updated sentiment_score (rating-based proxy) for {updated} review rows in {db_path}")
    print("Reminder: this is a proxy, not text sentiment analysis. See module docstring.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Populate reviews.sentiment_score as a rating-derived proxy.")
    parser.add_argument("--db", default="data/price_comparison.db", help="Path to SQLite DB")
    args = parser.parse_args()
    run(args.db)
