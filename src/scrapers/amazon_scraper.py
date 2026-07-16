

import argparse
import csv
import json
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_URL = "https://www.amazon.in"
DEFAULT_NUM_PAGES = 2
SOURCE_NAME = "amazon"
CURRENCY = "INR"

# Project root is two levels above this file: src/scrapers/amazon_scraper.py
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

CSV_FIELDS = [
    "asin",
    "source",
    "product_name",
    "brand",
    "category",
    "current_price",
    "mrp",
    "discount_pct",
    "currency",
    "product_url",
    "rating",
    "review_count",
    "availability",
    "scraped_at",
]

# Words that signal "the brand name has ended" when scanning the leading
# tokens of a product title. Deliberately generic — not category-specific.
BRAND_STOP_WORDS = {
    "with", "for", "and", "the", "in", "of", "by", "a", "an", "-", "|",
}

# Common non-brand leading words that describe the product rather than the
# maker (e.g. "Silicone Dish Washing Gloves" — "Silicone" is not a brand).
# Kept short; add entries as you encounter false positives.
_MATERIAL_DESCRIPTORS = {
    "silicone", "stainless", "plastic", "steel", "cotton", "wooden",
    "herb", "dry", "mini", "portable", "handheld", "new", "big", "smart",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clean_price(text):
    """'₹12,999' -> 12999.0"""
    if not text:
        return None
    digits = re.sub(r"[^\d.]", "", text)
    try:
        return float(digits) if digits else None
    except ValueError:
        return None


def clean_review_count(text):
    """
    Handles both formats seen on Amazon.in:
      '(831)'  -> 831
      '(3.4K)' -> 3400
      '(1.1K)' -> 1100
    """
    if not text:
        return None
    text = text.strip().strip("()").replace(",", "")
    if not text:
        return None
    match = re.match(r"^([\d.]+)\s*([kK])?$", text)
    if not match:
        return None
    num, suffix = match.groups()
    try:
        value = float(num)
    except ValueError:
        return None
    if suffix:
        value *= 1000
    return int(round(value))


def clean_rating(text):
    """'4.2 out of 5 stars' -> 4.2"""
    if not text:
        return None
    match = re.match(r"^([\d.]+)", text.strip())
    return float(match.group(1)) if match else None


def guess_brand(product_name):
    """
    Generic, category-agnostic brand guess.

    Takes leading capitalised word(s) of the title, stopping at the first
    token that:
      - contains a digit (model numbers / specs)
      - is a pipe or paren
      - is a common filler word (BRAND_STOP_WORDS)
      - is a material/descriptor word (_MATERIAL_DESCRIPTORS) — these
        appear at the start of generic/unbranded listings and are NOT brands

    Capped at 2 tokens.  Returns None when the heuristic cannot confidently
    identify a brand (better to have None than a wrong value for Day 3
    matching).
    """
    if not product_name:
        return None

    tokens = re.split(r"\s+", product_name.strip())
    brand_tokens = []

    for token in tokens:
        clean_token = token.strip("|(),.")
        if not clean_token:
            break
        if any(ch.isdigit() for ch in clean_token):
            break
        if clean_token.lower() in BRAND_STOP_WORDS:
            break
        if clean_token.lower() in _MATERIAL_DESCRIPTORS:
            break
        if token in ("|", "(", ")"):
            break
        brand_tokens.append(clean_token)
        if len(brand_tokens) >= 2:
            break

    return " ".join(brand_tokens) if brand_tokens else None


# ---------------------------------------------------------------------------
# Core scraping logic
# ---------------------------------------------------------------------------

def fetch_page(keyword, page_num):
    search_url = f"{BASE_URL}/s"
    params = {"k": keyword, "page": page_num}
    resp = requests.get(search_url, headers=HEADERS, params=params, timeout=15)
    resp.raise_for_status()
    return resp.text


def parse_cards(html, category):
    soup = BeautifulSoup(html, "lxml")
    records = []

    cards = soup.select('div[data-component-type="s-search-result"]')
    for card in cards:
        # Skip sponsored placements — they pollute price/trend analytics
        # and Module 3 (fuzzy matching) cares about organic listings.
        #
        # The "Sponsored" label markup varies by ad slot type (top/mid/
        # bottom of page) — sometimes a <span>, sometimes an <a>. The
        # reliable signal is the "AdHolder" class Amazon puts directly on
        # this same s-search-result container for every sponsored type.
        card_classes = card.get("class", [])
        is_sponsored = "AdHolder" in card_classes
        if not is_sponsored:
            is_sponsored = card.select_one('[class*="sponsored-label-text"]') is not None
        if is_sponsored:
            continue

        asin = card.get("data-asin")
        if not asin:
            continue

        # --- Title + URL ---
        title_el = card.select_one("h2 span")
        link_anchor = card.select_one("h2")
        href = None
        if link_anchor:
            parent_a = link_anchor.find_parent("a")
            href = parent_a.get("href") if parent_a else None

        product_name = title_el.get_text(strip=True) if title_el else None
        product_url = f"{BASE_URL}{href}" if href else None

        # --- Price / MRP / discount ---
        price_el = card.select_one('span.a-price span.a-offscreen')
        current_price = clean_price(price_el.get_text(strip=True) if price_el else None)

        # Fallback: some listings (e.g. certain TVs) use a plain span.a-color-base
        # for the selling price instead of the standard a-price component.
        if current_price is None:
            for span in card.select("span.a-color-base"):
                txt = span.get_text(strip=True)
                if txt.startswith("₹") and len(txt) < 15:
                    current_price = clean_price(txt)
                    if current_price:
                        break

        mrp_el = card.select_one('span.a-price.a-text-price span.a-offscreen')
        mrp = clean_price(mrp_el.get_text(strip=True) if mrp_el else None)

        discount_pct = None
        if current_price and mrp and mrp > 0:
            discount_pct = round((1 - current_price / mrp) * 100, 1)

        # --- Rating / reviews ---
        rating_el = card.select_one("i.a-icon-star-mini span.a-icon-alt")
        rating = clean_rating(rating_el.get_text(strip=True) if rating_el else None)

        review_el = card.select_one(
            "span.a-size-mini.puis-normal-weight-text.s-underline-text, "
            "span.a-size-base.puis-normal-weight-text.s-underline-text"
        )
        review_count = clean_review_count(review_el.get_text(strip=True) if review_el else None)

        # --- Availability (best-effort; Amazon rarely shows explicit OOS
        # text on search cards, so default to "In Stock" unless flagged) ---
        availability = "In Stock"
        oos_marker = card.select_one("span.a-color-price.a-text-bold")
        if oos_marker and "unavailable" in oos_marker.get_text(strip=True).lower():
            availability = "Out of Stock"

        records.append(
            {
                "asin": asin,
                "source": SOURCE_NAME,
                "product_name": product_name,
                "brand": guess_brand(product_name),
                "category": category,
                "current_price": current_price,
                "mrp": mrp,
                "discount_pct": discount_pct,
                "currency": CURRENCY,
                "product_url": product_url,
                "rating": rating,
                "review_count": review_count,
                "availability": availability,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    return records


def run(keyword, category, num_pages=DEFAULT_NUM_PAGES, output_path=None):
    if output_path is None:
        safe_category = re.sub(r"[^a-z0-9_]+", "_", category.lower())
        output_path = _PROJECT_ROOT / "data" / "raw" / f"amazon_{safe_category}.csv"
    else:
        output_path = Path(output_path)

    all_records = []
    seen_asins = set()

    for page in range(1, num_pages + 1):
        print(f"[amazon_scraper] Fetching page {page} for keyword='{keyword}'...")
        html = fetch_page(keyword, page)
        page_records = parse_cards(html, category)

        new_count = 0
        for rec in page_records:
            if rec["asin"] in seen_asins:
                continue
            seen_asins.add(rec["asin"])
            all_records.append(rec)
            new_count += 1

        print(f"[amazon_scraper] Page {page}: {len(page_records)} cards, {new_count} new unique ASINs.")

        if page < num_pages:
            delay = random.uniform(1.5, 3.0)
            time.sleep(delay)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # --- CSV ---
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(all_records)
    print(f"[amazon_scraper] Wrote {len(all_records)} unique products to {output_path}")

    # --- JSON (same folder, same stem) ---
    json_path = output_path.with_suffix(".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)
    print(f"[amazon_scraper] Wrote JSON to {json_path}")

    return all_records


def main():
    parser = argparse.ArgumentParser(description="Scrape Amazon.in search results for any category.")
    parser.add_argument("--keyword", required=True, help="Search keyword, e.g. 'smartphones' or 'laptops'")
    parser.add_argument("--category", required=True, help="Category label to stamp on every row")
    parser.add_argument("--pages", type=int, default=DEFAULT_NUM_PAGES, help="Number of result pages to scrape")
    parser.add_argument("--output", default=None, help="Optional explicit output CSV path")
    args = parser.parse_args()

    run(keyword=args.keyword, category=args.category, num_pages=args.pages, output_path=args.output)


if __name__ == "__main__":
    main()
