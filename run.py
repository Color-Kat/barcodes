"""CLI backbone. All steps are re-runnable (upsert) = actualization mode.

  python run.py fetch <source> [--limit N]   # scrape one source -> raw_items
  python run.py merge                         # rebuild products from raw_items
  python run.py match [--limit N]             # attach barcode-less enrichment
  python run.py stats

Sources live in sources/<name>.py exposing fetch(limit)->iterable of dicts.
Enrichment sources without EAN (vkusvill, magnit) are bridged to Layer-1
barcodes by `match` (local pg_trgm name search over the 5.9M base — no network,
the thing that made v1's name-matching unusable).
"""
import argparse
import importlib
import sys

import db
import merge as merge_mod


def cmd_fetch(con, source, limit):
    mod = importlib.import_module(f"sources.{source}")
    print(f"[{source}] fetching (limit={limit})...", flush=True)
    n = db.upsert_raw(con, source, mod.fetch(limit))
    print(f"[{source}] upserted {n} rows")


def cmd_match(con, limit):
    """Attach barcode-less enrichment rows to Layer-1 products by fuzzy name.

    For each enriched, barcode-less raw row, find the best pg_trgm name match
    among products that still lack КБЖУ, above a similarity floor. High
    precision: never attach nutrition to the wrong barcode.
    """
    import matching
    got, tried = matching.match(con, limit)
    print(f"matched {got}/{tried} enrichment rows to barcodes -> source 'namematch'")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["fetch", "merge", "match", "stats"])
    ap.add_argument("source", nargs="?")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    con = db.connect()
    db.init(con)

    if args.cmd == "fetch":
        if not args.source:
            sys.exit("fetch needs a source name")
        cmd_fetch(con, args.source, args.limit)
    elif args.cmd == "merge":
        print(f"merged {merge_mod.merge(con)} products")
        merge_mod.stats(con)
    elif args.cmd == "match":
        cmd_match(con, args.limit)
    else:
        merge_mod.stats(con)


if __name__ == "__main__":
    main()
