CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    product_name TEXT NOT NULL,
    brand TEXT,
    category TEXT,
    current_price REAL,
    mrp REAL,
    discount_pct REAL,
    currency TEXT,
    product_url TEXT,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE price_history (
    history_id INTEGER PRIMARY KEY,
    product_id INTEGER,
    price REAL,
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE reviews (
    review_id INTEGER PRIMARY KEY,
    product_id INTEGER,
    rating REAL,
    review_count INTEGER,
    sentiment_score REAL,
    FOREIGN KEY(product_id) REFERENCES products(product_id)
);

CREATE TABLE product_matches (
    match_id INTEGER PRIMARY KEY,
    amazon_product_id INTEGER,
    flipkart_product_id INTEGER,
    confidence_score REAL,
    FOREIGN KEY (amazon_product_id) REFERENCES products(product_id),
    FOREIGN KEY (flipkart_product_id) REFERENCES products(product_id)
);

CREATE TABLE etl_run_log (
    run_id INTEGER PRIMARY KEY,
    source TEXT,
    records_processed INTEGER,
    status TEXT,

    duplicates_removed INTEGER,
    missing_values_fixed INTEGER,
    invalid_rows_removed INTEGER,

    run_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);