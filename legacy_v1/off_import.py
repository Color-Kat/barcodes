#!/usr/bin/env python3
"""Импорт российских товаров из Open Food Facts (parquet-дамп на Hugging Face) в products.db.

Берёт все товары с countries_tags = en:russia: штрихкод, название (ru, фолбэк en/main),
бренд, объём упаковки, состав, КБЖУ на 100г, категории, URL фото.
"""
import sqlite3
import sys

import duckdb

# можно указать локальный путь к food.parquet первым аргументом
PARQUET = sys.argv[1] if len(sys.argv) > 1 else \
    "https://huggingface.co/datasets/openfoodfacts/product-database/resolve/main/food.parquet"
DB = "products.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    barcode TEXT PRIMARY KEY,
    name TEXT,
    brand TEXT,
    quantity TEXT,
    ingredients TEXT,
    kcal_100g REAL,
    proteins_100g REAL,
    fat_100g REAL,
    carbs_100g REAL,
    categories TEXT,
    image_url TEXT,
    source TEXT,
    popularity INTEGER
);
CREATE INDEX IF NOT EXISTS idx_name ON products(name);
"""

def lang_text(col, lang):
    return f"list_extract(list_filter({col}, x -> x.lang = '{lang}'), 1).text"

def nutr(name):
    return f'list_extract(list_filter(nutriments, x -> x.name = \'{name}\'), 1)."100g"'

QUERY = f"""
SELECT
    code AS barcode,
    coalesce({lang_text('product_name', 'ru')}, {lang_text('product_name', 'main')},
             {lang_text('product_name', 'en')}) AS name,
    brands AS brand,
    quantity,
    coalesce({lang_text('ingredients_text', 'ru')}, {lang_text('ingredients_text', 'main')}) AS ingredients,
    {nutr('energy-kcal')} AS kcal_100g,
    {nutr('proteins')} AS proteins_100g,
    {nutr('fat')} AS fat_100g,
    {nutr('carbohydrates')} AS carbs_100g,
    categories,
    (SELECT 'https://images.openfoodfacts.org/images/products/' ||
            regexp_replace(lpad(code, 13, '0'), '^(\\d{{3}})(\\d{{3}})(\\d{{3}})(\\d+)$', '\\1/\\2/\\3/\\4') ||
            '/' || i.key || '.' || i.rev || '.400.jpg'
     FROM unnest(images) AS t(i) WHERE i.key LIKE 'front%' LIMIT 1) AS image_url,
    'off' AS source,
    coalesce(unique_scans_n, 0) AS popularity
FROM read_parquet('{PARQUET}')
WHERE list_contains(countries_tags, 'en:russia') AND code IS NOT NULL
"""

def main():
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    print("Качаю и фильтрую parquet OFF (несколько минут)...")
    rows = con.execute(QUERY).fetchall()
    print(f"Получено {len(rows)} товаров")

    db = sqlite3.connect(DB)
    db.executescript(SCHEMA)
    db.executemany(
        "INSERT OR REPLACE INTO products VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    db.commit()
    n = db.execute("SELECT count(*) FROM products WHERE source='off'").fetchone()[0]
    print(f"В базе {n} товаров OFF")

if __name__ == "__main__":
    main()
