"""Core: sqlite storage + barcode normalization + merge.

Two layers:
  raw_items  — every record as fetched from a source (re-runnable upsert by (source, source_id))
  products   — merged view keyed by barcode, built by merge()
"""
import json
import re
import sqlite3
import time

DB_PATH = "products.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_items (
    source      TEXT NOT NULL,
    source_id   TEXT NOT NULL,
    barcode     TEXT,
    name        TEXT,
    brand       TEXT,
    ingredients TEXT,
    kcal        REAL, protein REAL, fat REAL, carbs REAL,
    weight      TEXT,
    photo       TEXT,
    extra       TEXT,               -- JSON: everything else (vitamins, category, url, ...)
    fetched_at  INTEGER NOT NULL,
    PRIMARY KEY (source, source_id)
);
CREATE INDEX IF NOT EXISTS idx_raw_barcode ON raw_items(barcode);

CREATE TABLE IF NOT EXISTS products (
    barcode     TEXT PRIMARY KEY,
    name        TEXT,
    brand       TEXT,
    ingredients TEXT,
    kcal        REAL, protein REAL, fat REAL, carbs REAL,
    weight      TEXT,
    photo       TEXT,
    extra       TEXT,
    sources     TEXT,               -- JSON list of contributing sources
    updated_at  INTEGER
);
"""

# merge priority: later sources override earlier ones field-by-field
SOURCE_PRIORITY = []  # filled per-source module registration order; low index = low priority


def connect(path=DB_PATH):
    con = sqlite3.connect(path, timeout=60)
    con.execute("PRAGMA journal_mode=WAL")   # concurrent readers + one writer
    con.execute("PRAGMA busy_timeout=60000")  # wait for lock instead of erroring
    con.executescript(SCHEMA)
    return con


_WEIGHT_RE = re.compile(r"\b\d+[.,]?\d*\s*(?:кг|гр?|мл|л|шт|%|g|ml|l)\b", re.I)
_PCT_RE = re.compile(r"\b\d+[.,]?\d*\s*%")
_PUNCT_RE = re.compile(r"[^\w\s]", re.U)


def norm_name(s):
    """Normalize a product name for cross-source matching: lowercase, drop
    weight/volume tokens (300г, 1.5 л, 15%) and punctuation, collapse spaces.
    Returns '' for empty — never matches (guarded by callers)."""
    if not s:
        return ""
    s = s.lower().replace("ё", "е")
    s = _PCT_RE.sub(" ", s)       # 3.2% before generic weight (% breaks \b)
    s = _WEIGHT_RE.sub(" ", s)
    s = _PUNCT_RE.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_barcode(raw):
    """Return normalized EAN-8/13 digits or None if invalid."""
    if not raw:
        return None
    d = re.sub(r"\D", "", str(raw))
    if len(d) == 12:          # UPC-A -> EAN-13
        d = "0" + d
    if len(d) not in (8, 13):
        return None
    digits = [int(c) for c in d]
    check = digits[-1]
    body = digits[:-1][::-1]
    s = sum(v * (3 if i % 2 == 0 else 1) for i, v in enumerate(body))
    if (10 - s % 10) % 10 != check:
        return None
    return d


def upsert_raw(con, source, items):
    """items: iterable of dicts with keys matching raw_items columns (extra as dict)."""
    n = 0
    now = int(time.time())
    for it in items:
        con.execute(
            """INSERT INTO raw_items
               (source, source_id, barcode, name, brand, ingredients,
                kcal, protein, fat, carbs, weight, photo, extra, fetched_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(source, source_id) DO UPDATE SET
                 barcode=excluded.barcode, name=excluded.name, brand=excluded.brand,
                 ingredients=excluded.ingredients, kcal=excluded.kcal, protein=excluded.protein,
                 fat=excluded.fat, carbs=excluded.carbs, weight=excluded.weight,
                 photo=excluded.photo, extra=excluded.extra, fetched_at=excluded.fetched_at""",
            (
                source, str(it["source_id"]), norm_barcode(it.get("barcode")),
                it.get("name"), it.get("brand"), it.get("ingredients"),
                it.get("kcal"), it.get("protein"), it.get("fat"), it.get("carbs"),
                it.get("weight"), it.get("photo"),
                json.dumps(it.get("extra") or {}, ensure_ascii=False), now,
            ),
        )
        n += 1
        if n % 50 == 0:          # frequent commits: slow throttled runs may die mid-way
            con.commit()
    con.commit()
    return n


FIELDS = ["name", "brand", "ingredients", "kcal", "protein", "fat", "carbs", "weight", "photo"]


def merge(con, priority):
    """Rebuild products from raw_items. priority: list of source names, low->high."""
    rank = {s: i for i, s in enumerate(priority)}
    rows = con.execute(
        "SELECT source, barcode, name, brand, ingredients, kcal, protein, fat, carbs,"
        " weight, photo, extra FROM raw_items WHERE barcode IS NOT NULL"
    ).fetchall()
    rows.sort(key=lambda r: rank.get(r[0], -1))  # low priority first, high overrides
    merged = {}
    for r in rows:
        src, bc = r[0], r[1]
        p = merged.setdefault(bc, {"sources": set(), "extra": {}})
        p["sources"].add(src)
        for i, f in enumerate(FIELDS):
            v = r[2 + i]
            if v not in (None, ""):
                p[f] = v
        try:
            ex = json.loads(r[11] or "{}")
            for k, v in ex.items():
                if v not in (None, ""):
                    p["extra"][k] = v
        except json.JSONDecodeError:
            pass
    now = int(time.time())
    con.execute("DELETE FROM products")
    con.executemany(
        "INSERT INTO products VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                bc, p.get("name"), p.get("brand"), p.get("ingredients"),
                p.get("kcal"), p.get("protein"), p.get("fat"), p.get("carbs"),
                p.get("weight"), p.get("photo"),
                json.dumps(p["extra"], ensure_ascii=False),
                json.dumps(sorted(p["sources"]), ensure_ascii=False), now,
            )
            for bc, p in merged.items()
        ],
    )
    con.commit()
    return len(merged)


ENRICH = ["ingredients", "kcal", "protein", "fat", "carbs", "photo", "brand"]


def enrich_by_name(con):
    """Attach состав/КБЖУ/photo from barcode-less rows (e.g. magnit, which has
    no EAN) to products that share a normalized name but lack those fields.

    Exact normalized-name match only — high precision, safe (won't attach the
    wrong состав). ponytail: exact match, low recall; upgrade to token-overlap
    fuzzy matching if too few products get enriched.
    """
    # candidates: barcode-less rows that actually carry enrichment
    cand = {}
    for row in con.execute(
        "SELECT name, ingredients, kcal, protein, fat, carbs, photo, brand, source"
        " FROM raw_items WHERE barcode IS NULL AND (ingredients IS NOT NULL OR kcal IS NOT NULL)"
    ):
        key = norm_name(row[0])
        if not key:
            continue
        vals = dict(zip(ENRICH, row[1:8]))
        # keep the most-complete candidate per name
        score = sum(1 for v in vals.values() if v not in (None, ""))
        prev = cand.get(key)
        if not prev or score > prev[0]:
            cand[key] = (score, vals, row[8])

    matched = 0
    for pr in con.execute(
        "SELECT barcode, name, sources FROM products"
        " WHERE ingredients IS NULL OR kcal IS NULL"
    ).fetchall():
        hit = cand.get(norm_name(pr[1]))
        if not hit:
            continue
        _, vals, src = hit
        sets, args = [], []
        for f, v in vals.items():
            if v not in (None, ""):
                sets.append(f"{f}=COALESCE({f}, ?)")   # never overwrite existing
                args.append(v)
        if not sets:
            continue
        try:
            srcs = sorted(set(json.loads(pr[2] or "[]")) | {f"{src}~name"})
        except json.JSONDecodeError:
            srcs = [f"{src}~name"]
        args += [json.dumps(srcs, ensure_ascii=False), pr[0]]
        con.execute(
            f"UPDATE products SET {', '.join(sets)}, sources=? WHERE barcode=?", args
        )
        matched += 1
    con.commit()
    return matched


if __name__ == "__main__":
    # self-check
    assert norm_name("Молоко 3.2% 930 мл") == "молоко"
    assert norm_name("Сыр Российский 500г") == "сыр российский"
    assert norm_barcode("4600682000129") == "4600682000129"   # valid EAN-13
    assert norm_barcode("4600682000121") is None              # bad checksum
    assert norm_barcode("012000161155") == "0012000161155"    # UPC-A -> EAN-13
    assert norm_barcode("abc") is None
    con = connect(":memory:")
    upsert_raw(con, "s1", [{"source_id": 1, "barcode": "4600682000129", "name": "A", "kcal": 42}])
    upsert_raw(con, "s2", [{"source_id": "x", "barcode": "4600682000129", "name": "B"}])
    assert merge(con, ["s1", "s2"]) == 1
    row = con.execute("SELECT name, kcal, sources FROM products").fetchone()
    assert row == ("B", 42.0, '["s1", "s2"]'), row  # s2 overrides name, s1 keeps kcal
    # enrich-by-name: barcode-less magnit-like row attaches состав/КБЖУ by name
    upsert_raw(con, "magnit", [{"source_id": "m1", "name": "B 500г",
                                "ingredients": "молоко", "kcal": 60}])
    assert enrich_by_name(con) == 1
    r = con.execute("SELECT ingredients, kcal FROM products").fetchone()
    assert r == ("молоко", 42.0), r  # состав attached; existing kcal NOT overwritten
    print("core ok")
