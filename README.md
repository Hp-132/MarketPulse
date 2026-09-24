# MarketPulse

<p align="center">
  <strong>Multi-Source E-Commerce Price Intelligence System</strong>
</p>

<p align="center">
  Turning marketplace data into actionable pricing insights.
</p>


---

## 📊 Overview

E-commerce pricing changes constantly.

The same product may appear across multiple marketplaces with different names, prices, discounts, ratings, and availability. Manually comparing these listings is slow, difficult to reproduce, and provides little historical or statistical insight.

**MarketPulse** is a Python-based **multi-source e-commerce price intelligence platform** that automates this process.

It collects product listings from **Amazon India and Flipkart**, processes the data through a multi-stage ETL pipeline, identifies matching products across platforms, performs business and statistical analysis, and presents the results through interactive dashboards.

The system was developed during a **six-week internship at Emerging Five, Ahmedabad**, with a focus on practical data engineering and analytics using real, inconsistent web data.

### The core pipeline

```text
Amazon India ──────┐
                   │
                   ▼
              Web Scraping
                   │
                   ▼
              ETL Pipeline
                   │
                   ▼
             SQLite Database
                   │
          ┌────────┼────────┐
          ▼        ▼        ▼
     Product    Analytics  Rating
     Matching    Engine     Proxy
          │        │        │
          └────────┼────────┘
                   ▼
             Dashboards
```

---

# 🎯 Why Price Intelligence Matters

For retailers, brands, marketplaces, and e-commerce analysts, knowing **what competitors are charging** is only the beginning.

A useful price-intelligence system needs to answer questions such as:

* Which products are cheaper on competing platforms?
* Which brands discount their products most aggressively?
* Where are significant price differences occurring?
* Which categories show high price volatility?
* Which products are statistical price outliers?
* How are products distributed across marketplaces?
* How do pricing patterns relate to ratings?
* Is the collected data actually complete and trustworthy?

MarketPulse turns raw marketplace listings into structured answers to these questions.

This mirrors the broader **competitor price-intelligence** problem addressed by commercial retail analytics platforms.

---

# 🚀 Key Features

## 🛒 Multi-Source Product Collection

MarketPulse collects product listings from:

* Amazon India
* Flipkart

Across six product categories:

* Smartphones
* Laptops
* Headphones
* Smart TVs
* Kitchen Tools
* Moisturizers

The scrapers collect fields including:

* Product name
* Brand
* Current price
* MRP
* Discount percentage
* Rating
* Review count
* Availability
* Platform-specific product ID

Sponsored listings are filtered so that promotional placements do not distort the pricing analysis.

---

# 🔄 ETL Pipeline

Raw web data is not immediately suitable for analysis.

MarketPulse therefore processes every scrape through a structured ETL pipeline:

```text
Raw JSON / CSV
      │
      ▼
   Load Raw
      │
      ▼
   Validate
      │
      ▼
    Clean
      │
      ▼
   De-duplicate
      │
      ▼
 Normalize Names
      │
      ▼
   Load to SQLite
      │
      ▼
   Run Log
```

### Pipeline stages

| Stage        | Purpose                                               |
| ------------ | ----------------------------------------------------- |
| Load         | Combine scraped files into a common dataset           |
| Validate     | Remove invalid prices, names, ratings, and MRP values |
| Clean        | Handle missing values and calculate discounts         |
| De-duplicate | Remove duplicate source records                       |
| Normalize    | Standardise product names                             |
| Load         | Store cleaned records in SQLite                       |
| Log          | Record pipeline execution statistics                  |

Every ETL run produces an audit record containing information such as records processed, rows inserted, duplicates removed, and errors.

This separation makes individual pipeline stages independently inspectable and re-runnable instead of hiding everything inside one monolithic script.

---

# 🔗 Cross-Platform Product Matching

One of the core challenges is determining whether two differently named listings represent the **same product**.

For example:

```text
Amazon:
Sony WH-1000XM5 Wireless Noise Cancelling Headphones

Flipkart:
Sony WH1000XM5 Bluetooth ANC Headphones
```

A simple exact-string comparison would fail.

MarketPulse uses:

**RapidFuzz `token_sort_ratio` + brand equality**

```text
Product A ───────┐
                 │
                 ▼
        Name Normalisation
                 │
                 ▼
       Token-Sort Similarity
                 │
                 ▼
          Brand Equality
                 │
          ┌──────┴──────┐
          ▼             ▼
       Match         No Match
```

The similarity threshold is configurable rather than hard-coded, allowing the matching behaviour to be tuned as the catalogue changes.

The final matching stage stores confirmed Amazon–Flipkart pairs and their similarity scores.

---

# 📈 Business & Statistical Analytics

Once the data is cleaned and products are matched, MarketPulse computes **seven categories of analytics**.

| Analytics                 | What it answers                                           |
| ------------------------- | --------------------------------------------------------- |
| Price Analytics           | What are the pricing ranges across categories and brands? |
| Discount Analytics        | Which categories and brands discount most aggressively?   |
| Brand Analytics           | How are brands distributed across platforms?              |
| Rating Analytics          | How do ratings vary across products and categories?       |
| Platform Summary          | How do Amazon and Flipkart compare overall?               |
| Cross-Platform Comparison | Where does the same product have different prices?        |
| Statistical Analysis      | Where are volatility, correlations, and price outliers?   |

These outputs transform scraped listings into information that can support pricing analysis rather than simply displaying raw product data.

---

# 💰 Cross-Platform Price Comparison

For products identified on both platforms, MarketPulse calculates:

* Amazon price
* Flipkart price
* Absolute price difference
* Percentage difference
* Lower-priced platform

Conceptually:

```text
Matched Product
      │
 ┌────┴────┐
 ▼         ▼
Amazon   Flipkart
Price      Price
 │          │
 └────┬─────┘
      ▼
Price Difference
      │
      ▼
Percentage Difference
```

This provides a direct view of competitive pricing for the same product rather than comparing unrelated catalogue items.

---

# 📊 Statistical Analysis

MarketPulse goes beyond simple averages.

The statistical module includes:

### Price Volatility

Measures how much prices vary within categories and brands.

### Price–Rating Correlation

Examines the relationship between product price and rating.

### Z-Score Outlier Detection

Identifies unusually high or low prices relative to the surrounding distribution.

These techniques help surface patterns that may not be obvious from a product-by-product comparison.

---

# ⭐ Rating-Derived Sentiment Proxy

The original design considered text-based sentiment analysis.

However, the source platforms available to the project exposed **aggregate ratings rather than individual review text**.

Instead of presenting this as genuine NLP sentiment analysis, MarketPulse implements a clearly labelled **rating-derived sentiment proxy**:

```text
Rating
  │
  ▼
Rescale to -1 ... +1
  │
  ▼
 ┌──────────┬───────────┬──────────┐
 ▼          ▼           ▼
Positive   Neutral    Negative
```

The dashboard explicitly identifies this as a proxy rather than text-based sentiment analysis.

This distinction is intentional: the system reports what the available data actually supports.

---

# 🖥️ Interactive Dashboard

MarketPulse provides an interactive dashboard designed for business-oriented exploration of the collected data.

### Dashboard sections

**Overview**

* Products tracked
* Average price
* Average rating
* Matched products
* Brand coverage
* Category pricing

**Cross-Platform Comparison**

* Matched product pairs
* Amazon vs Flipkart pricing
* Price difference
* Percentage difference

**Statistical Analysis**

* Price volatility
* Price-rating correlation
* Outlier detection

**Sentiment**

* Rating-derived sentiment proxy
* Explicit proxy limitation

**ETL Health**

* Pipeline execution logs
* Records processed
* Rows inserted
* Duplicates removed
* Errors

Filters for **category, platform, and brand** can be applied across the relevant views.



# 🛠️ Technology Stack

### Data Collection

* **Python 3.11**
* `requests`
* **BeautifulSoup4**
* `lxml`

### Data Engineering

* **pandas**
* ETL pipeline
* Data validation
* Cleaning
* Deduplication
* Normalisation

### Product Matching

* **RapidFuzz**
* `token_sort_ratio`
* Brand-equality validation

### Database

* **SQLite3**

### Analytics

* pandas
* Statistical analysis
* Correlation analysis
* Z-score outlier detection

### Dashboard

* **Streamlit**
* **Plotly**

### Extended Frontend

* **React 18**
* **TypeScript**
* **Vite**
* **Tailwind CSS**
* **Recharts**
* **Radix UI / shadcn**


