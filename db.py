"""Postgres connection + schema init + bulk upsert.

DSN comes from env BARCODES_DSN, defaulting to the docker-compose service on
host port 5433 so it works out of the box.
"""
import json
import os

import psycopg
from psycopg.types.json import Jsonb

DSN = os.environ.get(
    "BARCODES_DSN",
    "host=localhost port=5433 dbname=barcodes user=barcodes password=barcodes",
)

COLUMNS = ["source", "source_id", "barcode", "name", "brand", "ingredients",
           "kcal", "protein", "fat", "carbs", "weight", "photo", "raw"]


def connect():
    return psycopg.connect(DSN)


def init(con):
    with open(os.path.join(os.path.dirname(__file__), "schema.sql")) as f:
        con.execute(f.read())
    con.commit()


def _row(source, it):
    # "raw" is the v2 name for the catch-all JSON; v1 parsers call it "extra".
    return (
        source, str(it["source_id"]), it.get("barcode"), it.get("name"),
        it.get("brand"), it.get("ingredients"), it.get("kcal"), it.get("protein"),
        it.get("fat"), it.get("carbs"), it.get("weight"), it.get("photo"),
        Jsonb(it.get("raw") or it.get("extra") or {}),
    )


UPSERT = f"""
INSERT INTO raw_items ({", ".join(COLUMNS)}, fetched_at)
VALUES ({", ".join(["%s"] * len(COLUMNS))}, now())
ON CONFLICT (source, source_id) DO UPDATE SET
  barcode=EXCLUDED.barcode, name=EXCLUDED.name, brand=EXCLUDED.brand,
  ingredients=EXCLUDED.ingredients, kcal=EXCLUDED.kcal, protein=EXCLUDED.protein,
  fat=EXCLUDED.fat, carbs=EXCLUDED.carbs, weight=EXCLUDED.weight,
  photo=EXCLUDED.photo, raw=EXCLUDED.raw, fetched_at=now()
"""


def upsert_raw(con, source, items, batch=50, progress=True):
    """Bulk UPSERT via executemany. items: iterable of dicts. Returns count.

    Commits every `batch` rows (small, so a scrape that gets throttled mid-run
    still persists what it got — never an hour of work lost to no commit) and
    prints a heartbeat so the run is observably alive.
    """
    import sys
    import time
    n, t0, last = 0, time.time(), 0.0
    buf = []
    with con.cursor() as cur:
        for it in items:
            buf.append(_row(source, it))
            if len(buf) >= batch:
                cur.executemany(UPSERT, buf)
                con.commit()
                n += len(buf)
                buf.clear()
                now = time.time()
                if progress and now - last > 1.0:      # at most ~1 line/sec
                    rate = n / max(now - t0, 1e-9)
                    print(f"\r[{source}] saved {n} | {rate:.1f}/s | "
                          f"{int(now - t0)}s", end="", file=sys.stderr, flush=True)
                    last = now
        if buf:
            cur.executemany(UPSERT, buf)
            con.commit()
            n += len(buf)
    if progress:
        print(f"\r[{source}] saved {n} total in {int(time.time() - t0)}s",
              file=sys.stderr, flush=True)
    return n


if __name__ == "__main__":
    con = connect()
    init(con)
    print("db init ok:", con.execute("SELECT current_database(), version()").fetchone()[0])
    print("pg_trgm:", con.execute(
        "SELECT extname FROM pg_extension WHERE extname='pg_trgm'").fetchone())
