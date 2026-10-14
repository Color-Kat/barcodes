#!/usr/bin/env python3
"""Обогащение существующих штрихкодов из ПОЛНОГО дампа OFF (все страны).

Многие товары с российских полок есть в глобальном OFF без тега russia
(импорт: Alpen Gold, Barilla и т.п., плюс СНГ). Джойним все наши барkhoды
без состава против полного food.parquet и забираем состав/КБЖУ/фото.

Запуск: python3 off_join_enrich.py /путь/к/food.parquet
"""
import sqlite3
import sys

import duckdb

DB = "products.db"
PARQUET = sys.argv[1] if len(sys.argv) > 1 else "food.parquet"


def lang_text(col, lang):
    return f"list_extract(list_filter({col}, x -> x.lang = '{lang}'), 1).text"


def nutr(name):
    return f'list_extract(list_filter(nutriments, x -> x.name = \'{name}\'), 1)."100g"'


QUERY = f"""
SELECT
    code,
    coalesce({lang_text('product_name', 'ru')}, {lang_text('product_name', 'main')},
             {lang_text('product_name', 'en')}) AS name,
    brands,
    quantity,
    coalesce({lang_text('ingredients_text', 'ru')}, {lang_text('ingredients_text', 'main')}) AS ingredients,
    {nutr('energy-kcal')} AS kcal,
    {nutr('proteins')} AS proteins,
    {nutr('fat')} AS fat,
    {nutr('carbohydrates')} AS carbs,
    (SELECT 'https://images.openfoodfacts.org/images/products/' ||
            regexp_replace(lpad(code, 13, '0'), '^(\\d{{3}})(\\d{{3}})(\\d{{3}})(\\d+)$', '\\1/\\2/\\3/\\4') ||
            '/' || i.key || '.' || i.rev || '.400.jpg'
     FROM unnest(images) AS t(i) WHERE i.key LIKE 'front%' LIMIT 1) AS image_url
FROM read_parquet('{PARQUET}')
WHERE code IN (SELECT code FROM codes)
"""


def main():
    con = duckdb.connect()
    src = sqlite3.connect(DB)
    todo = src.execute(
        "SELECT barcode FROM products WHERE ingredients IS NULL OR kcal_100g IS NULL").fetchall()
    con.execute("CREATE TEMP TABLE codes(code VARCHAR)")
    con.executemany("INSERT INTO codes VALUES (?)", todo)
    print(f"Кодов для поиска: {len(todo)}. Джойн против полного дампа (несколько минут)...")
    rows = con.execute(QUERY).fetchall()
    print("Совпадений:", len(rows))

    db = sqlite3.connect(DB, timeout=120)
    for code, name, brands, qty, ingr, kcal, prot, fat, carbs, img in rows:
        db.execute(
            """UPDATE products SET
                 name = coalesce(name, ?), brand = coalesce(brand, ?),
                 quantity = coalesce(quantity, ?), ingredients = coalesce(ingredients, ?),
                 kcal_100g = coalesce(kcal_100g, ?), proteins_100g = coalesce(proteins_100g, ?),
                 fat_100g = coalesce(fat_100g, ?), carbs_100g = coalesce(carbs_100g, ?),
                 image_url = coalesce(image_url, ?)
               WHERE barcode = ?""",
            (name, brands, qty, ingr, kcal, prot, fat, carbs, img, code))
    db.commit()
    n = db.execute("""SELECT count(*) FROM products
                      WHERE ingredients IS NOT NULL AND kcal_100g IS NOT NULL""").fetchone()[0]
    print("Теперь товаров с составом и ккал:", n)


if __name__ == "__main__":
    main()
