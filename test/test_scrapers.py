"""
test_scrapers.py
----------------
QA test suite for Amazon and Flipkart scrapers.

Tests:
  1. Both scrapers run without exception for every category
  2. CSV and JSON output files are created
  3. Files are non-empty (at least 1 row of data)
  4. Schema is consistent — all expected columns present in every row
  5. No duplicate product IDs within a single run
  6. Critical fields (product_name, current_price) null-rate is acceptable
  7. Data types are correct (price=float, rating=float, review_count=int)
  8. File naming follows the convention amazon_<category>.csv etc.
  9. Source tag matches the scraper
 10. Currency is always INR

Run:
    cd price-comparison-system
    python test/test_scrapers.py

Output: prints a per-category, per-scraper PASS/FAIL table and a summary.
"""

import csv
import json
import random
import sys
import time
import traceback
from pathlib import Path

# ── path setup ─────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
SCRAPERS_DIR = ROOT / "src" / "scrapers"
RAW_DIR = ROOT / "data" / "raw"
sys.path.insert(0, str(SCRAPERS_DIR))

import amazon_scraper
import flipkart_scraper

# ── test configuration ─────────────────────────────────────────────────────
PAGES = 2   # 2 pages per category (≈ 30–48 products per run)

CATEGORIES = [
    # (keyword,              category_label,   amazon?,  flipkart?)
    ("smartphones",          "smartphones",    True,     True),
    ("laptops",              "laptops",        True,     True),
    ("headphones",           "headphones",     True,     True),
    ("smart tv",             "smart_tv",       True,     True),
    ("moisturizer skincare", "moisturizer",    True,     True),
    ("kitchen tools",        "kitchen_tools",  True,     True),
]

AMAZON_REQUIRED_FIELDS   = amazon_scraper.CSV_FIELDS
FLIPKART_REQUIRED_FIELDS = flipkart_scraper.CSV_FIELDS

# Acceptable null rate for non-critical fields (rating/review_count
# can be missing for new/unlisted products).
NULL_TOLERANCE = {
    "product_name":  0.00,   # must always be present
    "current_price": 0.15,   # allow ≤15%: some TVs/appliances show "see price in cart"
    "rating":        0.40,   # many new products have no rating yet
    "review_count":  0.40,
    "availability":  0.00,   # always defaulted to "In Stock" if unknown
}

# ── helpers ────────────────────────────────────────────────────────────────

def _load_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _load_json(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _check_schema(records: list[dict], required_fields: list[str], label: str) -> list[str]:
    """Return list of schema violation messages."""
    errors = []
    for i, row in enumerate(records):
        missing = [f for f in required_fields if f not in row]
        if missing:
            errors.append(f"Row {i}: missing columns {missing}")
    return errors


def _check_types(records: list[dict], id_field: str, label: str) -> list[str]:
    """Return list of type-mismatch messages."""
    errors = []
    for i, row in enumerate(records):
        pid = row.get(id_field, f"row_{i}")

        # price → float or empty string
        for price_field in ("current_price", "mrp"):
            val = row.get(price_field)
            if val not in (None, ""):
                try:
                    float(val)
                except (ValueError, TypeError):
                    errors.append(f"{pid}: {price_field}='{val}' is not numeric")

        # rating → float or empty
        val = row.get("rating")
        if val not in (None, ""):
            try:
                f = float(val)
                if not (0.0 <= f <= 5.0):
                    errors.append(f"{pid}: rating={f} out of [0,5] range")
            except (ValueError, TypeError):
                errors.append(f"{pid}: rating='{val}' is not numeric")

        # review_count → int or empty
        val = row.get("review_count")
        if val not in (None, ""):
            try:
                int(float(val))
            except (ValueError, TypeError):
                errors.append(f"{pid}: review_count='{val}' is not an integer")

    return errors


def _check_nulls(records: list[dict], label: str) -> list[str]:
    """Return messages where null rate exceeds tolerance."""
    warnings = []
    n = len(records)
    if n == 0:
        return ["No records — cannot check null rates"]
    for field, threshold in NULL_TOLERANCE.items():
        null_count = sum(1 for r in records if not r.get(field))
        rate = null_count / n
        if rate > threshold:
            warnings.append(
                f"{field}: {null_count}/{n} null ({rate:.0%}) — "
                f"exceeds tolerance of {threshold:.0%}"
            )
    return warnings


def _check_duplicates(records: list[dict], id_field: str) -> list[str]:
    seen = {}
    dupes = []
    for i, row in enumerate(records):
        pid = row.get(id_field)
        if pid in seen:
            dupes.append(f"Duplicate {id_field}='{pid}' at rows {seen[pid]} and {i}")
        else:
            seen[pid] = i
    return dupes


def _check_source(records: list[dict], expected_source: str) -> list[str]:
    return [
        f"Row {i}: source='{r.get('source')}' expected '{expected_source}'"
        for i, r in enumerate(records)
        if r.get("source") != expected_source
    ]


def _check_currency(records: list[dict]) -> list[str]:
    return [
        f"Row {i}: currency='{r.get('currency')}' expected 'INR'"
        for i, r in enumerate(records)
        if r.get("currency") != "INR"
    ]


# ── single-category test runner ────────────────────────────────────────────

def run_amazon_category(keyword: str, category: str) -> dict:
    result = {
        "scraper": "amazon",
        "category": category,
        "keyword": keyword,
        "status": "PASS",
        "records": 0,
        "issues": [],
        "warnings": [],
        "csv_path": None,
        "json_path": None,
    }

    safe = amazon_scraper.re.sub(r"[^a-z0-9_]+", "_", category.lower())
    csv_path  = RAW_DIR / f"amazon_{safe}.csv"
    json_path = RAW_DIR / f"amazon_{safe}.json"
    result["csv_path"]  = str(csv_path)
    result["json_path"] = str(json_path)

    # ── 1. Run scraper ──────────────────────────────────────────────────
    try:
        records = amazon_scraper.run(
            keyword=keyword, category=category, num_pages=PAGES
        )
    except Exception as exc:
        result["status"] = "FAIL"
        result["issues"].append(f"Scraper raised exception: {exc}")
        result["issues"].append(traceback.format_exc())
        return result

    result["records"] = len(records)

    # ── 2. File existence ───────────────────────────────────────────────
    for path, label in [(csv_path, "CSV"), (json_path, "JSON")]:
        if not path.exists():
            result["issues"].append(f"{label} file not created: {path}")
            result["status"] = "FAIL"

    if result["status"] == "FAIL":
        return result

    # ── 3. Non-empty ────────────────────────────────────────────────────
    if len(records) == 0:
        result["issues"].append("Scraper returned 0 records — possible selector breakage or block")
        result["status"] = "FAIL"
        return result

    # ── 4. CSV ↔ JSON consistency ───────────────────────────────────────
    csv_rows  = _load_csv(csv_path)
    json_rows = _load_json(json_path)
    if len(csv_rows) != len(json_rows):
        result["issues"].append(
            f"CSV has {len(csv_rows)} rows but JSON has {len(json_rows)} — mismatch"
        )
        result["status"] = "FAIL"

    # ── 5. Schema ───────────────────────────────────────────────────────
    schema_errors = _check_schema(csv_rows, AMAZON_REQUIRED_FIELDS, "amazon")
    if schema_errors:
        result["issues"].extend(schema_errors[:5])   # cap verbose output
        result["status"] = "FAIL"

    # ── 6. Types ────────────────────────────────────────────────────────
    type_errors = _check_types(csv_rows, "asin", "amazon")
    if type_errors:
        result["issues"].extend(type_errors[:5])
        result["status"] = "FAIL"

    # ── 7. Duplicates ───────────────────────────────────────────────────
    dupe_errors = _check_duplicates(csv_rows, "asin")
    if dupe_errors:
        result["issues"].extend(dupe_errors[:5])
        result["status"] = "FAIL"

    # ── 8. Source tag ───────────────────────────────────────────────────
    source_errors = _check_source(csv_rows, "amazon")
    if source_errors:
        result["issues"].extend(source_errors[:3])
        result["status"] = "FAIL"

    # ── 9. Currency ─────────────────────────────────────────────────────
    currency_errors = _check_currency(csv_rows)
    if currency_errors:
        result["issues"].extend(currency_errors[:3])
        result["status"] = "FAIL"

    # ── 10. Null rates (warnings, not hard failures) ────────────────────
    null_warnings = _check_nulls(csv_rows, "amazon")
    result["warnings"].extend(null_warnings)

    # ── 11. File naming ─────────────────────────────────────────────────
    expected_csv_name  = f"amazon_{safe}.csv"
    expected_json_name = f"amazon_{safe}.json"
    if csv_path.name != expected_csv_name:
        result["issues"].append(f"CSV filename '{csv_path.name}' != expected '{expected_csv_name}'")
        result["status"] = "FAIL"
    if json_path.name != expected_json_name:
        result["issues"].append(f"JSON filename '{json_path.name}' != expected '{expected_json_name}'")
        result["status"] = "FAIL"

    return result


def run_flipkart_category(keyword: str, category: str) -> dict:
    result = {
        "scraper": "flipkart",
        "category": category,
        "keyword": keyword,
        "status": "PASS",
        "records": 0,
        "issues": [],
        "warnings": [],
        "csv_path": None,
        "json_path": None,
    }

    safe = flipkart_scraper.re.sub(r"[^a-z0-9_]+", "_", category.lower())
    csv_path  = RAW_DIR / f"flipkart_{safe}.csv"
    json_path = RAW_DIR / f"flipkart_{safe}.json"
    result["csv_path"]  = str(csv_path)
    result["json_path"] = str(json_path)

    # ── 1. Run scraper ──────────────────────────────────────────────────
    try:
        records = flipkart_scraper.run(
            keyword=keyword, category=category, num_pages=PAGES
        )
    except Exception as exc:
        result["status"] = "FAIL"
        result["issues"].append(f"Scraper raised exception: {exc}")
        result["issues"].append(traceback.format_exc())
        return result

    result["records"] = len(records)

    # ── 2. File existence ───────────────────────────────────────────────
    for path, label in [(csv_path, "CSV"), (json_path, "JSON")]:
        if not path.exists():
            result["issues"].append(f"{label} file not created: {path}")
            result["status"] = "FAIL"

    if result["status"] == "FAIL":
        return result

    # ── 3. Non-empty ────────────────────────────────────────────────────
    if len(records) == 0:
        result["issues"].append("Scraper returned 0 records — possible selector breakage or block")
        result["status"] = "FAIL"
        return result

    # ── 4. CSV ↔ JSON consistency ───────────────────────────────────────
    csv_rows  = _load_csv(csv_path)
    json_rows = _load_json(json_path)
    if len(csv_rows) != len(json_rows):
        result["issues"].append(
            f"CSV has {len(csv_rows)} rows but JSON has {len(json_rows)} — mismatch"
        )
        result["status"] = "FAIL"

    # ── 5. Schema ───────────────────────────────────────────────────────
    schema_errors = _check_schema(csv_rows, FLIPKART_REQUIRED_FIELDS, "flipkart")
    if schema_errors:
        result["issues"].extend(schema_errors[:5])
        result["status"] = "FAIL"

    # ── 6. Types ────────────────────────────────────────────────────────
    type_errors = _check_types(csv_rows, "pid", "flipkart")
    if type_errors:
        result["issues"].extend(type_errors[:5])
        result["status"] = "FAIL"

    # ── 7. Duplicates ───────────────────────────────────────────────────
    dupe_errors = _check_duplicates(csv_rows, "pid")
    if dupe_errors:
        result["issues"].extend(dupe_errors[:5])
        result["status"] = "FAIL"

    # ── 8. Source tag ───────────────────────────────────────────────────
    source_errors = _check_source(csv_rows, "flipkart")
    if source_errors:
        result["issues"].extend(source_errors[:3])
        result["status"] = "FAIL"

    # ── 9. Currency ─────────────────────────────────────────────────────
    currency_errors = _check_currency(csv_rows)
    if currency_errors:
        result["issues"].extend(currency_errors[:3])
        result["status"] = "FAIL"

    # ── 10. Null rates ──────────────────────────────────────────────────
    null_warnings = _check_nulls(csv_rows, "flipkart")
    result["warnings"].extend(null_warnings)

    # ── 11. File naming ─────────────────────────────────────────────────
    expected_csv_name  = f"flipkart_{safe}.csv"
    expected_json_name = f"flipkart_{safe}.json"
    if csv_path.name != expected_csv_name:
        result["issues"].append(f"CSV filename '{csv_path.name}' != expected '{expected_csv_name}'")
        result["status"] = "FAIL"
    if json_path.name != expected_json_name:
        result["issues"].append(f"JSON filename '{json_path.name}' != expected '{expected_json_name}'")
        result["status"] = "FAIL"

    return result


# ── report renderer ────────────────────────────────────────────────────────

def render_report(all_results: list[dict]) -> None:
    SEP = "=" * 72

    print(f"\n{SEP}")
    print("  SCRAPER QA TEST REPORT")
    print(SEP)

    amazon_results   = [r for r in all_results if r["scraper"] == "amazon"]
    flipkart_results = [r for r in all_results if r["scraper"] == "flipkart"]

    for scraper_name, results in [("AMAZON", amazon_results), ("FLIPKART", flipkart_results)]:
        print(f"\n{'─'*72}")
        print(f"  {scraper_name} SCRAPER")
        print(f"{'─'*72}")
        print(f"  {'Category':<20} {'Records':>8}  {'Status':<8}  Issues/Warnings")
        print(f"  {'─'*18}  {'─'*7}  {'─'*6}  {'─'*30}")

        for r in results:
            status_icon = "✓ PASS" if r["status"] == "PASS" else "✗ FAIL"
            issue_summary = ""
            if r["issues"]:
                issue_summary = f"{len(r['issues'])} issue(s)"
            elif r["warnings"]:
                issue_summary = f"{len(r['warnings'])} warning(s)"
            else:
                issue_summary = "clean"
            print(f"  {r['category']:<20} {r['records']:>8}  {status_icon:<8}  {issue_summary}")

        # Detail block for failures/warnings
        for r in results:
            if r["issues"] or r["warnings"]:
                print(f"\n  ── {r['category']} details ──")
                for issue in r["issues"]:
                    # Truncate long tracebacks in the report
                    print(f"    [ISSUE]   {issue[:120]}")
                for warn in r["warnings"]:
                    print(f"    [WARN]    {warn}")

    # ── Overall summary ────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  OVERALL SUMMARY")
    print(SEP)

    total      = len(all_results)
    passed     = sum(1 for r in all_results if r["status"] == "PASS")
    failed     = total - passed
    categories = sorted({r["category"] for r in all_results})
    total_recs = sum(r["records"] for r in all_results)

    a_pass = all(r["status"] == "PASS" for r in amazon_results)
    f_pass = all(r["status"] == "PASS" for r in flipkart_results)

    print(f"  Amazon scraper   : {'PASS ✓' if a_pass else 'FAIL ✗'}")
    print(f"  Flipkart scraper : {'PASS ✓' if f_pass else 'FAIL ✗'}")
    print(f"  Categories tested: {len(categories)} — {', '.join(categories)}")
    print(f"  Total records    : {total_recs}")
    print(f"  Tests passed     : {passed}/{total}")
    if failed:
        print(f"  Tests FAILED     : {failed}/{total}")
        print("\n  Failed tests:")
        for r in all_results:
            if r["status"] == "FAIL":
                print(f"    • {r['scraper']:8} / {r['category']}")
                for issue in r["issues"][:2]:
                    print(f"        {issue[:110]}")
    print(SEP)


# ── main ───────────────────────────────────────────────────────────────────

def main():
    all_results = []

    print("\n" + "=" * 72)
    print("  QA RUN — scraping all categories")
    print(f"  Pages per category: {PAGES}")
    print("=" * 72)

    for keyword, category, run_amazon, run_flipkart in CATEGORIES:
        if run_amazon:
            print(f"\n[QA] Amazon  | {category} | keyword='{keyword}'")
            result = run_amazon_category(keyword, category)
            all_results.append(result)
            # Amazon rate-limits aggressively when many categories are scraped
            # back-to-back. 8–12 s between category runs keeps it clean.
            time.sleep(random.uniform(8, 12))

        if run_flipkart:
            print(f"\n[QA] Flipkart | {category} | keyword='{keyword}'")
            result = run_flipkart_category(keyword, category)
            all_results.append(result)
            time.sleep(random.uniform(3, 5))

    render_report(all_results)

    # Exit code: 0 if all pass, 1 if any fail
    if any(r["status"] == "FAIL" for r in all_results):
        sys.exit(1)


if __name__ == "__main__":
    main()
