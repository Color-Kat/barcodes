"""Load the offline barcode dumps (Layer 1) into raw_items.

Two free community dumps, each barcode+name+brand+category, no nutrition:
  uhtt  — papyrussolution/UhttBarcodeReference, 5.7M rows, tab-separated, mixed
          RU/US/EU, stale ~2018. Cols: ID UPCEAN Name CategoryID CategoryName
          BrandID BrandName.
  aioke — aioke/barcodes, 1.8M rows, RU-market 2021-2022, CSV. Cols vary; we
          read barcode/name/brand/category by header name.

Both go through normalize.norm_barcode, so only checksum-valid EAN-8/13 land.
Rows with an invalid/empty barcode are dropped (Layer 1 is barcode-keyed).

Uses COPY into a staging table then a single INSERT..SELECT — ~50x faster than
row-by-row upsert for millions of rows. Re-running is safe (ON CONFLICT).
"""
import csv
import glob
import io
import os
import sys

import db
from normalize import norm_barcode

DUMPS = os.path.join(os.path.dirname(__file__), "dumps")

STAGE = """
DROP TABLE IF EXISTS _stage;
CREATE UNLOGGED TABLE _stage (source_id TEXT, barcode TEXT, name TEXT, brand TEXT, raw JSONB);
"""

MERGE = """
INSERT INTO raw_items (source, source_id, barcode, name, brand, raw, fetched_at)
SELECT %s, source_id, barcode, name, brand, raw, now() FROM _stage
ON CONFLICT (source, source_id) DO UPDATE SET
  barcode=EXCLUDED.barcode, name=EXCLUDED.name, brand=EXCLUDED.brand,
  raw=EXCLUDED.raw, fetched_at=now()
"""


def _copy(con, source, rows):
    """rows: iterator of (source_id, barcode, name, brand, raw_json_str)."""
    con.execute(STAGE)
    kept = 0
    with con.cursor().copy(
        "COPY _stage (source_id, barcode, name, brand, raw) FROM STDIN"
    ) as cp:
        for r in rows:
            cp.write_row(r)
            kept += 1
    con.execute(MERGE, (source,))
    con.execute("DROP TABLE _stage")
    con.commit()
    return kept


def load_uhtt(con):
    files = sorted(glob.glob(f"{DUMPS}/uhtt/DATA/uhtt_barcode_ref_*.csv"))
    if not files:
        print("uhtt: no files", file=sys.stderr)
        return 0

    def rows():
        seen = 0
        for path in files:
            with open(path, encoding="utf-8", errors="replace") as f:
                rd = csv.reader(f, delimiter="\t")
                header = next(rd, None)
                for rec in rd:
                    if len(rec) < 7:
                        continue
                    _id, upcean, name, _cid, cname, _bid, bname = rec[:7]
                    bc = norm_barcode(upcean)
                    if not bc or not name.strip():
                        continue
                    seen += 1
                    raw = f'{{"category": {_json(cname)}}}'
                    yield (f"uhtt:{_id}", bc, name.strip(), bname.strip() or None, raw)
        print(f"  uhtt valid rows: {seen}")
    return _copy(con, "uhtt", rows())


def load_aioke(con):
    # aioke ships a CSV inside a release zip; support either an extracted .csv
    # anywhere under dumps/aioke or a top-level barcodes*.csv.
    files = (glob.glob(f"{DUMPS}/aioke/**/*.csv", recursive=True)
             or glob.glob(f"{DUMPS}/aioke*.csv"))
    if not files:
        print("aioke: no CSV found (release zip not extracted yet) — skipping")
        return 0

    def rows():
        seen = 0
        for path in files:
            with open(path, encoding="utf-8", errors="replace") as f:
                # sniff delimiter from header
                sample = f.readline()
                f.seek(0)
                delim = ";" if sample.count(";") > sample.count(",") else ","
                rd = csv.DictReader(f, delimiter=delim)
                cols = {c.lower(): c for c in (rd.fieldnames or [])}
                bcol = _pick(cols, "barcode", "штрихкод", "ean", "code")
                ncol = _pick(cols, "name", "название", "наименование", "title")
                vcol = _pick(cols, "vendor", "brand", "бренд", "производитель")
                ccol = _pick(cols, "category", "категория")
                icol = _pick(cols, "id", "код")  # unique row id -> source_id
                if not bcol or not ncol:
                    print(f"  aioke: {os.path.basename(path)} missing barcode/name cols {list(cols)}",
                          file=sys.stderr)
                    continue
                for i, rec in enumerate(rd):
                    bc = norm_barcode(rec.get(bcol))
                    name = (rec.get(ncol) or "").strip()
                    if not bc or not name:
                        continue
                    seen += 1
                    # source_id must be unique per row (barcodes repeat in the dump),
                    # else the same-batch UPSERT hits a cardinality violation.
                    rid = (rec.get(icol) or "").strip() if icol else ""
                    sid = f"aioke:{rid or i}"
                    raw = f'{{"category": {_json(rec.get(ccol))}}}' if ccol else "{}"
                    yield (sid, bc, name, (rec.get(vcol) or "").strip() or None, raw)
        print(f"  aioke valid rows: {seen}")
    return _copy(con, "aioke", rows())


def _pick(cols, *names):
    for n in names:
        if n in cols:
            return cols[n]
    return None


def _json(s):
    import json
    return json.dumps((s or "").strip() or None, ensure_ascii=False)


if __name__ == "__main__":
    con = db.connect()
    db.init(con)
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "uhtt"):
        print("loading uhtt...")
        print(f"uhtt loaded: {load_uhtt(con)}")
    if which in ("all", "aioke"):
        print("loading aioke...")
        print(f"aioke loaded: {load_aioke(con)}")
    tot = con.execute("SELECT count(*), count(DISTINCT barcode) FROM raw_items").fetchone()
    print(f"raw_items: {tot[0]} rows, {tot[1]} distinct barcodes")
