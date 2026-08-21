"""Merge raw_items -> products, keyed by barcode.

Layer-1 sources (uhtt, aioke) are name-only. Later enrichment sources
(retailers, OFF) add состав/КБЖУ and override name/brand where more trusted.
Priority is low->high; a higher source overrides a field only when it has a
non-null value, so a name-only high source never blanks an enriched low one.

Done in SQL with DISTINCT ON for speed over millions of rows: order rows by
barcode then priority-desc, take the first per barcode for each field via
coalescing window. Simpler and fast enough: aggregate per barcode picking the
highest-priority non-null value with a CASE ladder is overkill — instead we do
one pass per source in priority order with COALESCE upserts.
"""
import db

# low -> high trust. Retailers/OFF get appended here as they come online;
# aioke (RU 2021-22) outranks uhtt (mixed, 2018) for name/brand. namematch
# (barcode-less enrichment bridged to a barcode) is highest — it carries the
# состав/КБЖУ the dumps lack, and COALESCE means it only fills, never blanks.
PRIORITY = ["uhtt", "aioke", "namematch"]

COUNTRY_SQL = """
UPDATE products SET country = CASE
  WHEN length(barcode)=13 AND substr(barcode,1,3) BETWEEN '460' AND '469' THEN 'RU'
  WHEN length(barcode)=13 AND substr(barcode,1,3)='481' THEN 'BY'
  WHEN length(barcode)=13 AND substr(barcode,1,3)='482' THEN 'UA'
  WHEN length(barcode)=13 AND substr(barcode,1,3)='487' THEN 'KZ'
  WHEN length(barcode)=13 AND substr(barcode,1,3) BETWEEN '400' AND '440' THEN 'DE'
  WHEN length(barcode)=13 AND substr(barcode,1,3) BETWEEN '690' AND '699' THEN 'CN'
  ELSE country END
WHERE country IS NULL;
"""


def merge(con):
    """Rebuild products from all barcode-bearing raw_items in priority order."""
    con.execute("TRUNCATE products")
    for src in PRIORITY:
        # INSERT new barcodes; on conflict, COALESCE so we never overwrite an
        # existing non-null field with a null, and higher-priority (later loop
        # iteration) non-null values do override.
        con.execute("""
            INSERT INTO products (barcode, name, brand, ingredients, kcal, protein,
                                  fat, carbs, weight, photo, sources, updated_at)
            SELECT DISTINCT ON (barcode) barcode, name, brand, ingredients, kcal,
                   protein, fat, carbs, weight, photo, ARRAY[%s], now()
            FROM raw_items WHERE source=%s AND barcode IS NOT NULL
            ORDER BY barcode, fetched_at DESC
            ON CONFLICT (barcode) DO UPDATE SET
              name        = COALESCE(EXCLUDED.name, products.name),
              brand       = COALESCE(EXCLUDED.brand, products.brand),
              ingredients = COALESCE(EXCLUDED.ingredients, products.ingredients),
              kcal    = COALESCE(EXCLUDED.kcal, products.kcal),
              protein = COALESCE(EXCLUDED.protein, products.protein),
              fat     = COALESCE(EXCLUDED.fat, products.fat),
              carbs   = COALESCE(EXCLUDED.carbs, products.carbs),
              weight  = COALESCE(EXCLUDED.weight, products.weight),
              photo   = COALESCE(EXCLUDED.photo, products.photo),
              sources = (SELECT ARRAY(SELECT DISTINCT unnest(products.sources || EXCLUDED.sources))),
              updated_at = now()
        """, (src, src))
        con.commit()
    con.execute(COUNTRY_SQL)
    con.commit()
    return con.execute("SELECT count(*) FROM products").fetchone()[0]


def stats(con):
    total = con.execute("SELECT count(*) FROM products").fetchone()[0]
    ru = con.execute("SELECT count(*) FROM products WHERE country='RU'").fetchone()[0]
    kbju = con.execute("SELECT count(*) FROM products WHERE kcal IS NOT NULL").fetchone()[0]
    ing = con.execute("SELECT count(*) FROM products WHERE ingredients IS NOT NULL").fetchone()[0]
    bysrc = con.execute(
        "SELECT unnest(sources) s, count(*) FROM products GROUP BY s ORDER BY 2 DESC"
    ).fetchall()
    print(f"products: {total}  (RU={ru}, КБЖУ={kbju}, состав={ing})")
    print("by source:", dict(bysrc))


if __name__ == "__main__":
    con = db.connect()
    print(f"merged {merge(con)} products")
    stats(con)
