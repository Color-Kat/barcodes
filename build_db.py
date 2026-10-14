"""Rebuild barcodes.db (SQLite) from everything collected so far. Stdlib only.

    python3 build_db.py          # ~2 min, builds barcodes.db.new, then swaps it in (old one -> .prev)

Inputs (all optional, missing ones are skipped):
    dumps/uhtt/DATA/*.csv, dumps/aioke/barcodes.csv      offline dumps
    data/old/products_v1.db                              v1 research db (OFF, barcode-list, enrichment)
    data/old/products_v2.db                              v2 scraper db (nationalcatalog, namematch, ...)
    data/rskrf.db                                        rskrf.ru cards cached by rskrf.py
    data/chestnyznak.db                                  Нацкаталог cards cached by chestnyznak.py
    data/auchan.db, data/globus.db, data/fixprice.db     retailer cards cached by the scrapers of the same name
    barcodes.db itself                                   Mira rows + mira_checks, carried over as is

One table, `products`, PRIMARY KEY (barcode, provider): the same barcode appears once per
provider that knows it, nothing is merged. Mira rows are named after Mira's own upstream:
mira_yuka, mira_national_catalog, mira_ga, or plain `mira` when it reports none.
Records without a checksum-valid barcode are skipped (they stay in data/old/).
Only food and cosmetics are kept, see KEEP; everything else (tools, books, clothes, the
unclassified bulk of uhtt/aioke) is dropped at the end.
"""
import csv
import glob
import json
import os
import sqlite3
import sys
import time

import auchan as auchan_source
import chestnyznak as chestnyznak_source
import fixprice as fixprice_source
import globus as globus_source
import rskrf as rskrf_source
from normalize import country_of, norm_barcode

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "barcodes.db")
SCHEMA = """
CREATE TABLE products (
    barcode TEXT NOT NULL, provider TEXT NOT NULL,
    source_id TEXT,                                     -- provider's own record id
    name TEXT, brand TEXT, category TEXT, quantity TEXT, ingredients TEXT,
    kcal REAL, protein REAL, fat REAL, carbs REAL,      -- per 100 g
    photo TEXT, extra TEXT,                             -- extra: JSON, anything provider-specific
    country TEXT,                                       -- from GS1 prefix
    PRIMARY KEY (barcode, provider)
) WITHOUT ROWID;
"""


def num(v):
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def clean(v):
    if isinstance(v, (list, tuple)):  # e.g. Mira cosmetics: ingredientsList is a list
        v = ", ".join(x if isinstance(x, str) else json.dumps(x, ensure_ascii=False) for x in v)
    elif isinstance(v, dict):
        v = json.dumps(v, ensure_ascii=False)
    elif v is not None and not isinstance(v, str):
        v = str(v)
    return (v or "").strip() or None


def row(provider, source_id, barcode, **f):
    return (barcode, provider, str(source_id), clean(f.get("name")), clean(f.get("brand")), clean(f.get("category")),
            clean(f.get("quantity")), clean(f.get("ingredients")), num(f.get("kcal")), num(f.get("protein")),
            num(f.get("fat")), num(f.get("carbs")), clean(f.get("photo")), clean(f.get("extra")),
            country_of(barcode) if barcode else None)


def uhtt():
    for path in sorted(glob.glob(f"{HERE}/dumps/uhtt/DATA/uhtt_barcode_ref_*.csv")):
        with open(path, encoding="utf-8", errors="replace", newline="") as f:
            rd = csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
            next(rd, None)
            for rec in rd:
                if len(rec) >= 7 and rec[2].strip():
                    yield row("uhtt", rec[0], norm_barcode(rec[1]), name=rec[2], category=rec[4], brand=rec[6])


def aioke():
    path = f"{HERE}/dumps/aioke/barcodes.csv"
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        for i, rec in enumerate(csv.DictReader(f, delimiter=";")):
            if (rec.get("Name") or "").strip():
                extra = json.dumps({"article": rec["Article"]}, ensure_ascii=False) if rec.get("Article") else None
                yield row("aioke", rec.get("Id") or i, norm_barcode(rec.get("Barcode")), name=rec["Name"],
                          brand=rec.get("Vendor"), category=rec.get("Category"), extra=extra)


def v1():
    path = f"{HERE}/data/old/products_v1.db"
    if not os.path.exists(path):
        return
    src = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    names = {"off": "openfoodfacts", "barcode-list": "barcode_list_ru", "aioke": "v1_enrich"}
    for r in src.execute("SELECT * FROM products"):
        enriched = any(r[k] for k in ("ingredients", "kcal_100g", "image_url", "quantity"))
        if r["source"] == "aioke" and not enriched:
            continue  # plain aioke rows are already in the dump; keep only what v1 enrichment added
        extra = json.dumps({"popularity": r["popularity"]}) if r["popularity"] else None
        yield row(names.get(r["source"], r["source"]), "v1:" + r["barcode"], norm_barcode(r["barcode"]),
                  name=r["name"], brand=r["brand"], category=r["categories"], quantity=r["quantity"],
                  ingredients=r["ingredients"], kcal=r["kcal_100g"], protein=r["proteins_100g"],
                  fat=r["fat_100g"], carbs=r["carbs_100g"], photo=r["image_url"], extra=extra)


def v2():
    path = f"{HERE}/data/old/products_v2.db"
    if not os.path.exists(path):
        return
    src = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    for r in src.execute("SELECT * FROM raw_items"):
        cat = None
        try:
            cat = (json.loads(r["extra"] or "{}") or {}).get("category")
        except ValueError:
            pass
        yield row(r["source"], r["source_id"], norm_barcode(r["barcode"]), name=r["name"], brand=r["brand"],
                  category=cat if isinstance(cat, str) else None, quantity=r["weight"], ingredients=r["ingredients"],
                  kcal=r["kcal"], protein=r["protein"], fat=r["fat"], carbs=r["carbs"], photo=r["photo"],
                  extra=r["extra"])


def scraped(provider, source):
    """Rows of a two-stage scraper (rskrf.py, chestnyznak.py, scrape.py users): its rows() does the parsing."""
    for r in source.rows():
        yield row(provider, r.pop("source_id"), r.pop("barcode"), **r)


def rskrf():
    return scraped("rskrf", rskrf_source)


def chestnyznak():
    return scraped("chestnyznak", chestnyznak_source)


def auchan():
    return scraped("auchan", auchan_source)


def globus():
    return scraped("globus", globus_source)


def fixprice():
    return scraped("fixprice", fixprice_source)


# A barcode stays when any of its rows says food or cosmetics. uhtt is the only big source with a usable
# category tree; aioke (electronics, home goods) has no row that qualifies on its own.
COSMETICS = " OR ".join("category LIKE '%s (folder)%%'" % f
                        for f in ("Косметика", "Парфюмерия", "Уход за волосами", "Гигиена"))
# uhtt files paper goods, tools and appliances under those folders; none has a composition to analyse
NOT_COSMETICS = " OR ".join("category LIKE '%%/%s'" % name for name in (
    "GLOVES & MASK", "Баня и сауна", "Бритва", "Бумага туалетная", "Вата и ватные изделия", "Губка для тела", "Мочалка",
    "Пеленки", "Платки бумажные", "Платки носовые", "Подгузники", "Подгузники для взрослых", "Полотенца бумажные",
    "Презервативы", "Прокладки женские", "Прокладки урологические", "Раствор для контактных линз", "Станок бритвенный",
    "Тампоны женские", "Зубная щетка", "Зубочистки", "Кисть косметическая", "Косметика аппаратная",
    "Косметика, украшения и аксессуары для девочек", "Инструменты для маникюра и педикюра", "Кусачки маникюрные",
    "Маникюрный набор", "Ногти накладные", "Ножницы маникюрные", "Пилка маникюрная", "Стемпинг", "Ресницы накладные",
    "Наращивание ресниц", "Hair Extensions", "Аксессуары для волос", "Бигуди", "Брашинг", "Выпрямитель волос",
    "Машинка для стрижки", "Ножницы парикмахерские", "Плойка", "Расческа", "Резинка для волос", "Щетка для волос",
    "Щипцы для волос"))
UHTT_KEEP = f"(category LIKE 'Продукты питания (folder)%' OR ({COSMETICS}) AND NOT ({NOT_COSMETICS}))"
KEEP = f"""provider = 'uhtt' AND {UHTT_KEEP}
        OR provider IN ('openfoodfacts', 'barcode_list_ru') OR provider LIKE 'mira%'
        OR ingredients IS NOT NULL OR kcal IS NOT NULL"""


def prune(con):
    con.execute(f"CREATE TEMP TABLE keep AS SELECT DISTINCT barcode FROM products WHERE {KEEP}")
    n = con.execute("DELETE FROM products WHERE barcode NOT IN (SELECT barcode FROM keep)").rowcount
    con.execute("DROP TABLE keep")
    # a kept barcode can still carry a uhtt row from another shelf (a toy, a notebook): drop the row
    n += con.execute(f"DELETE FROM products WHERE provider = 'uhtt' AND NOT {UHTT_KEEP}").rowcount
    con.commit()
    print(f"prune: -{n} rows that are neither food nor cosmetics", flush=True)


def carry_mira(con):
    """Mira data lives only in barcodes.db (../mira-reverse-engineering/check_barcodes.py), so copy it over."""
    if not os.path.exists(OUT):
        return
    con.execute("ATTACH ? AS cur", (OUT,))
    con.execute("INSERT OR REPLACE INTO products SELECT * FROM cur.products WHERE provider LIKE 'mira%'")
    ddl = con.execute("SELECT sql FROM cur.sqlite_master WHERE name='mira_checks'").fetchone()
    if ddl:
        con.execute(ddl[0])
        con.execute("INSERT INTO mira_checks SELECT * FROM cur.mira_checks")
    con.commit()
    con.execute("DETACH cur")
    print("mira: carried over %d products, %d checks" % (
        con.execute("SELECT count(*) FROM products WHERE provider LIKE 'mira%'").fetchone()[0],
        con.execute("SELECT count(*) FROM mira_checks").fetchone()[0] if ddl else 0), flush=True)


def main():
    new = OUT + ".new"  # a failed build must not touch barcodes.db: it is the only copy of the Mira data
    if os.path.exists(new):
        os.remove(new)
    con = sqlite3.connect(new)
    con.executescript("PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;" + SCHEMA)
    t = time.time()
    for load in (uhtt, aioke, v1, v2, rskrf, chestnyznak, auchan, globus, fixprice):
        n = con.execute("SELECT count(*) FROM products").fetchone()[0]
        seen = skipped = 0

        def rows():
            nonlocal seen, skipped
            for r in load():
                seen += 1
                if r[0]:
                    yield r
                else:
                    skipped += 1
        # same provider + barcode twice -> the later record wins
        con.executemany("INSERT OR REPLACE INTO products VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows())
        con.commit()
        added = con.execute("SELECT count(*) FROM products").fetchone()[0] - n
        print(f"{load.__name__}: read {seen}, no valid barcode {skipped}, +{added} rows ({time.time() - t:.0f}s)", flush=True)
    carry_mira(con)
    prune(con)
    con.execute("CREATE INDEX products_provider ON products(provider)")
    con.execute("CREATE INDEX products_country ON products(country)")
    con.commit()
    con.execute("VACUUM")  # prune frees two thirds of the file; without this it stays 1.5 GB instead of 0.5
    total, barcodes = con.execute("SELECT count(*), count(DISTINCT barcode) FROM products").fetchone()
    print(f"rows={total} distinct barcodes={barcodes} ({time.time() - t:.0f}s)")
    for r in con.execute("""SELECT provider, count(*), count(name), count(ingredients), count(kcal), count(photo)
                            FROM products GROUP BY 1 ORDER BY 2 DESC"""):
        print("  %-24s rows=%-8d name=%-8d ingredients=%-6d kcal=%-6d photo=%d" % r)
    assert total
    con.close()
    if os.path.exists(OUT):
        os.replace(OUT, OUT + ".prev")  # keep the previous build instead of deleting it
    os.replace(new, OUT)


if __name__ == "__main__":
    sys.exit(main())
