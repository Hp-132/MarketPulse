

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

BASE_URL = "https://www.flipkart.com"
SEARCH_URL = f"{BASE_URL}/search"
DEFAULT_NUM_PAGES = 2
SOURCE_NAME = "flipkart"
CURRENCY = "INR"

# Project root is two levels above this file: src/scrapers/flipkart_scraper.py
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/webp,*/*;q=0.8"
    ),
    "Referer": BASE_URL,
}

CSV_FIELDS = [
    "pid",
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

BRAND_STOP_WORDS = {
    "with", "for", "and", "the", "in", "of", "by", "a", "an", "-", "|",
}

# Common non-brand leading words — material/descriptor words that appear
# at the start of generic/unbranded listings and are NOT brands.
_MATERIAL_DESCRIPTORS = {
    "silicone", "stainless", "plastic", "steel", "cotton", "wooden",
    "herb", "dry", "mini", "portable", "handheld", "new", "big", "smart",
}


# ---------------------------------------------------------------------------
# Helpers  (identical API to amazon_scraper.py)
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
    Handles all Flipkart review count formats:

    Grid-view (headphones, kitchen, etc.):
      '(2,76,738)'  -> 276738
      '(14)'        -> 14

    List-view (smartphones, laptops, smart TV):
      '13,267 Ratings&929 Reviews'  -> 929   (take Reviews count)
      '1,234 Ratings'               -> 1234  (no Reviews, use Ratings)
    """
    if not text:
        return None
    text = text.strip()

    # List-view format: "X Ratings&Y Reviews" or "X Ratings"
    # Prefer the Reviews count; fall back to Ratings count.
    reviews_match = re.search(r"([\d,]+)\s*Reviews", text, re.IGNORECASE)
    if reviews_match:
        try:
            return int(reviews_match.group(1).replace(",", ""))
        except ValueError:
            pass
    ratings_match = re.search(r"([\d,]+)\s*Ratings", text, re.IGNORECASE)
    if ratings_match:
        try:
            return int(ratings_match.group(1).replace(",", ""))
        except ValueError:
            pass

    # Grid-view format: "(2,76,738)"
    text = text.strip("()").replace(",", "")
    try:
        return int(text)
    except ValueError:
        return None


def clean_rating(text):
    """'4.1' or '4.1 out of 5' -> 4.1"""
    if not text:
        return None
    match = re.match(r"^([\d.]+)", text.strip())
    return float(match.group(1)) if match else None


def guess_brand(product_name):
    """
    Generic, category-agnostic brand guess — identical logic to
    amazon_scraper.py.  Takes leading capitalised word(s) of the title,
    stopping at the first token that contains a digit, a pipe/paren, a
    common filler word, or a material/descriptor word.  Capped at 2 tokens.
    Returns None when the heuristic cannot confidently identify a brand.
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


def extract_pid_from_url(url):
    """
    Extract Flipkart PID from a product or search-result URL.
    Priority: ?pid= query param  >  /p/ path segment.

    Examples:
      .../p/itmXXX?pid=CPRGTQ5GWAPPHKHB&...  -> 'CPRGTQ5GWAPPHKHB'
      .../p/itmaf5be568e7c32                  -> 'itmaf5be568e7c32'
    """
    match = re.search(r"[?&]pid=([A-Z0-9]+)", url)
    if match:
        return match.group(1)
    match = re.search(r"/p/([a-z0-9]+)", url, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


# ---------------------------------------------------------------------------
# Core scraping logic
# ---------------------------------------------------------------------------

def fetch_page(session, keyword, page_num):
    """
    Flipkart paginates with  ?q=<keyword>&page=<n>&marketplace=FLIPKART.
    The session retains cookies across pages (prevents bot-challenge
    redirects on page 2+).
    """
    params = {
        "q": keyword,
        "page": page_num,
        "marketplace": "FLIPKART",
    }
    resp = session.get(SEARCH_URL, headers=HEADERS, params=params, timeout=15)
    resp.raise_for_status()
    return resp.text


def parse_cards(html, category):
    """
    Parse every product card on a Flipkart search-results page.

    Verified class names (from live HTML, June 2026):
      data-id attribute on card div  — stable unique product hook
      a.pIpigb[title]                — title + URL anchor
      div.hZ3P6w                     — current (selling) price  e.g. ₹185
      div.kRYCnD                     — MRP / struck-through price e.g. ₹699
      div.HQe8jr > span              — discount badge  e.g. "73% off"
      div.MKiFS6                     — star-rating badge  e.g. "4.1"
      span.PvbNMB                    — review count  e.g. "(2,76,738)"
      div.HZ0E6r                     — status label ("Hot Deal" / "Only few left")
    """
    soup = BeautifulSoup(html, "lxml")
    records = []

    cards = soup.find_all("div", attrs={"data-id": True})

    for card in cards:
        pid = card.get("data-id")
        if not pid:
            continue

        # ── Title + URL ────────────────────────────────────────────────────
        # Flipkart uses two card layouts depending on category/viewport:
        #
        # Grid-view (headphones, kitchen, etc.):
        #   <a class="GnxRXv" title="Product Name" href="...">
        #   → title is in the anchor's `title` attribute
        #
        # List-view (smartphones, laptops, smart TV):
        #   <a class="k7wcnx" href="...">  (no `title` attribute)
        #   → title is the `alt` text of the product image inside the card
        #
        # We try both approaches in order and take the first non-empty result.
        title_anchor = card.select_one("a.pIpigb[title]")
        if title_anchor is None:
            title_anchor = card.find("a", attrs={"title": True})

        product_name = None
        product_url = None
        if title_anchor:
            product_name = (
                title_anchor.get("title") or title_anchor.get_text(strip=True) or None
            )
            href = title_anchor.get("href", "")
            product_url = (
                href if href.startswith("http") else f"{BASE_URL}{href}"
            )
            url_pid = extract_pid_from_url(product_url)
            if url_pid:
                pid = url_pid

        # Fallback for list-view cards: use the img alt attribute
        if not product_name:
            img = card.select_one("img[alt]")
            if img:
                alt = img.get("alt", "").strip()
                if alt:
                    product_name = alt
            # Also grab the URL from the only anchor in the card
            if product_url is None:
                anchor = card.find("a", href=True)
                if anchor:
                    href = anchor.get("href", "")
                    product_url = href if href.startswith("http") else f"{BASE_URL}{href}"
                    url_pid = extract_pid_from_url(product_url)
                    if url_pid:
                        pid = url_pid

        # ── Current price ──────────────────────────────────────────────────
        price_el = card.select_one("div.hZ3P6w")
        if price_el is None:
            price_el = card.find(
                lambda tag: tag.name in ("div", "span")
                and tag.get_text(strip=True).startswith("₹")
                and len(tag.get_text(strip=True)) < 12
            )
        current_price = clean_price(
            price_el.get_text(strip=True) if price_el else None
        )

        # ── MRP ────────────────────────────────────────────────────────────
        mrp_el = card.select_one("div.kRYCnD")
        mrp = clean_price(mrp_el.get_text(strip=True) if mrp_el else None)

        # ── Discount % ─────────────────────────────────────────────────────
        discount_pct = None
        disc_el = card.select_one("div.HQe8jr span")
        if disc_el:
            m = re.search(r"(\d+(?:\.\d+)?)\s*%", disc_el.get_text(strip=True))
            if m:
                discount_pct = float(m.group(1))
        if discount_pct is None and current_price and mrp and mrp > 0:
            discount_pct = round((1 - current_price / mrp) * 100, 1)

        # ── Rating ─────────────────────────────────────────────────────────
        rating_el = card.select_one("div.MKiFS6")
        rating = None
        if rating_el:
            rating_text = rating_el.find(string=True, recursive=False)
            rating = clean_rating(
                str(rating_text) if rating_text else rating_el.get_text(strip=True)
            )

        # ── Review count ───────────────────────────────────────────────────
        review_el = card.select_one("span.PvbNMB")
        review_count = clean_review_count(
            review_el.get_text(strip=True) if review_el else None
        )

        # ── Availability ───────────────────────────────────────────────────
        availability = "In Stock"
        for marker in card.select("div.HZ0E6r"):
            label = marker.get_text(strip=True).lower()
            if "out of stock" in label or "unavailable" in label:
                availability = "Out of Stock"
                break
            if "only few left" in label:
                availability = "Only Few Left"
                break

        records.append(
            {
                "pid": pid,
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
        output_path = _PROJECT_ROOT / "data" / "raw" / f"flipkart_{safe_category}.csv"
    else:
        output_path = Path(output_path)

    session = requests.Session()
    all_records = []
    seen_pids = set()

    for page in range(1, num_pages + 1):
        print(f"[flipkart_scraper] Fetching page {page} for keyword='{keyword}'...")
        try:
            html = fetch_page(session, keyword, page)
        except requests.HTTPError as exc:
            print(f"[flipkart_scraper] HTTP error on page {page}: {exc}")
            print(f"  Status: {exc.response.status_code}")
            print(f"  Body (first 500 chars): {exc.response.text[:500]}")
            print("  Stopping — check for CAPTCHA or bot block.")
            break

        page_records = parse_cards(html, category)

        new_count = 0
        for rec in page_records:
            if rec["pid"] in seen_pids:
                continue
            seen_pids.add(rec["pid"])
            all_records.append(rec)
            new_count += 1

        print(
            f"[flipkart_scraper] Page {page}: "
            f"{len(page_records)} cards parsed, {new_count} new unique PIDs."
        )

        if page < num_pages:
            time.sleep(random.uniform(1.5, 3.0))

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # --- CSV ---
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(all_records)
    print(
        f"[flipkart_scraper] Done. Wrote {len(all_records)} unique products "
        f"to {output_path}"
    )

    # --- JSON (same folder, same stem) ---
    json_path = output_path.with_suffix(".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)
    print(f"[flipkart_scraper] Wrote JSON to {json_path}")

    return all_records


def main():
    parser = argparse.ArgumentParser(
        description="Scrape Flipkart search results for any category."
    )
    parser.add_argument("--keyword", required=True,
        help="Search keyword, e.g. 'kitchen gadgets' or 'smartphones'")
    parser.add_argument("--category", required=True,
        help="Category label stamped on every row")
    parser.add_argument("--pages", type=int, default=DEFAULT_NUM_PAGES,
        help=f"Pages to scrape (default: {DEFAULT_NUM_PAGES})")
    parser.add_argument("--output", default=None,
        help="Optional explicit output CSV path")
    args = parser.parse_args()
    run(keyword=args.keyword, category=args.category,
        num_pages=args.pages, output_path=args.output)


if __name__ == "__main__":
    main()
