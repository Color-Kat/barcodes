"""Export the merged `products` table to JSONL in the user's CatalogFoodLabelData
shape (libs/interfaces/src/catalog/catalog-food-label-data.interface.ts).

One JSON object per line. КБЖУ in our DB is always per-100g, so nutrition.per is
{value:100, unit:'g'|'ml'}. Fields we can't fill are emitted as null so the
consumer sees the full shape. Re-run any time — pure read of the DB.

  python export.py                      # all products with a name -> export.jsonl
  python export.py --enriched           # only products that have КБЖУ or состав
  python export.py --out food.jsonl --limit 1000
"""
import argparse
import json
import re
import sys

import db

_UNIT = {"г": "g", "гр": "g", "кг": "kg", "мл": "ml", "л": "l", "шт": "pcs",
         "g": "g", "kg": "kg", "ml": "ml", "l": "l"}


def _quantity(weight):
    """'930 мл' -> {'value':930.0,'unit':'ml'}, else None."""
    if not weight:
        return None
    m = re.search(r"([\d]+(?:[.,]\d+)?)\s*([а-яa-z]+)", str(weight), re.I)
    if not m:
        return None
    unit = _UNIT.get(m.group(2).lower())
    if not unit:
        return None
    return {"value": float(m.group(1).replace(",", ".")), "unit": unit}


def _nv(value, unit):
    return {"value": value, "unit": unit} if value is not None else None


def _source(sources):
    """Map our provenance to the interface LabelSource enum."""
    s = set(sources or [])
    if s & {"metro", "wildberries", "vkusvill", "magnit", "ozon", "namematch"}:
        return "MANUFACTURER"      # a retailer/label-derived record
    return "BARCODE_DB"            # dump-only identity record


def to_catalog(row, raw):
    """row: dict of products columns. raw: parsed `extra` JSONB dict."""
    per_unit = "ml" if (_quantity(row.get("weight")) or {}).get("unit") in ("ml", "l") else "g"
    has_kbju = any(row.get(k) is not None for k in ("kcal", "protein", "fat", "carbs"))
    nutrition = None
    if has_kbju:
        nutrition = {
            "per": {"value": 100, "unit": per_unit},
            "basis": "AS_SOLD",
            "calories": _nv(row.get("kcal"), "kcal"),
            "energyKj": None,
            "protein": _nv(row.get("protein"), "g"),
            "fat": _nv(row.get("fat"), "g"),
            "saturatedFat": None, "transFat": None,
            "carbohydrates": _nv(row.get("carbs"), "g"),
            "sugar": None, "fiber": None, "salt": None, "sodium": None,
        }
    manufacturer = None
    if raw.get("manufacturer") or row.get("country"):
        manufacturer = {"name": raw.get("manufacturer"),
                        "country": row.get("country"), "address": None,
                        "plantCodes": []}
    storage = None
    if raw.get("storage") or raw.get("shelf_life"):
        storage = {"conditions": raw.get("storage"),
                   "shelfLifeText": raw.get("shelf_life"),
                   "manufacturingDate": None, "expiryDate": None}
    return {
        "source": _source(row.get("sources")),
        "sourceRef": (row.get("sources") or [None])[0],
        "barcode": row.get("barcode"),
        "name": row.get("name"),
        "brand": row.get("brand"),
        "manufacturer": manufacturer,
        "countryOfOrigin": row.get("country"),
        "photoUrl": row.get("photo"),
        "rawIngredients": row.get("ingredients"),
        "ingredientsLang": "ru" if row.get("ingredients") else None,
        "nutrition": nutrition,
        "micronutrients": [],
        "packageSize": _quantity(row.get("weight")),
        "storageInfo": storage,
    }


COLS = ["barcode", "name", "brand", "ingredients", "kcal", "protein", "fat",
        "carbs", "weight", "photo", "country", "extra", "sources"]


def export(con, path, enriched=False, limit=None):
    where = "WHERE name IS NOT NULL"
    if enriched:
        where += " AND (kcal IS NOT NULL OR ingredients IS NOT NULL)"
    sql = f"SELECT {', '.join(COLS)} FROM products {where}"
    if limit:
        sql += f" LIMIT {int(limit)}"
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for r in con.execute(sql):
            row = dict(zip(COLS, r))
            raw = row.pop("extra") or {}
            if isinstance(raw, str):
                raw = json.loads(raw)
            f.write(json.dumps(to_catalog(row, raw), ensure_ascii=False) + "\n")
            n += 1
            if n % 50000 == 0:
                print(f"\r  exported {n}...", end="", file=sys.stderr, flush=True)
    print(f"\rexported {n} products -> {path}", file=sys.stderr)
    return n


def demo():
    row = {"barcode": "4601374000014", "name": "Молоко 3.2%", "brand": "Домик",
           "ingredients": "молоко цельное", "kcal": 59.0, "protein": 2.9,
           "fat": 3.2, "carbs": 4.7, "weight": "930 мл", "photo": "http://x",
           "country": "RU", "sources": ["uhtt", "namematch"]}
    c = to_catalog(row, {"manufacturer": "Danone", "storage": "至 +6C"})
    assert c["barcode"] == "4601374000014"
    assert c["source"] == "MANUFACTURER"
    assert c["nutrition"]["per"] == {"value": 100, "unit": "ml"}
    assert c["nutrition"]["calories"] == {"value": 59.0, "unit": "kcal"}
    assert c["nutrition"]["protein"] == {"value": 2.9, "unit": "g"}
    assert c["packageSize"] == {"value": 930.0, "unit": "ml"}
    assert c["rawIngredients"] == "молоко цельное"
    assert c["manufacturer"]["name"] == "Danone" and c["manufacturer"]["country"] == "RU"
    # dump-only identity row -> BARCODE_DB, null nutrition
    c2 = to_catalog({"barcode": "1", "name": "X", "sources": ["uhtt"]}, {})
    assert c2["source"] == "BARCODE_DB" and c2["nutrition"] is None
    print("export demo ok")


if __name__ == "__main__":
    if "--demo" in sys.argv or len(sys.argv) == 1 and not sys.stdin.isatty():
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="export.jsonl")
    ap.add_argument("--enriched", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        demo()
    else:
        con = db.connect()
        export(con, a.out, a.enriched, a.limit)
