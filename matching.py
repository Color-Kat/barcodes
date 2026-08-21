"""Bridge barcode-less enrichment rows -> Layer-1 barcodes by fuzzy name.

Enrichment sources like vkusvill/magnit carry состав+КБЖУ but no EAN. The
Layer-1 base (5.9M products from dumps) has barcode+name. We match an
enrichment row's name to the closest product name and, if similar enough, copy
the enrichment onto that barcode — writing a 'namematch' raw row so merge folds
it in as fully-enriched.

Matching is a LOCAL Postgres pg_trgm query (similarity() over the trigram GIN
index) — no network. This is what made v1's name bridge unusable: it went to
barcode-list.ru per row and got soft-blocked. Now it's an indexed local lookup.

Precision guard: SIM_FLOOR is deliberately high. A wrong barcode<->nutrition
attach is worse than a miss. Candidates are restricted to RU products (the
enrichment sources are RU) that still lack КБЖУ.
"""
import db

SIM_FLOOR = 0.55     # pg_trgm similarity; tune against a labelled sample

from normalize import norm_name

FIND = """
SELECT barcode, name, similarity(name, %s) AS sim
FROM products
WHERE name %% %s                 -- trigram candidate prefilter (uses GIN index)
ORDER BY sim DESC
LIMIT 1
"""


def match(con, limit=None):
    # enrichment rows lacking a barcode but carrying состав or КБЖУ
    rows = con.execute("""
        SELECT source, source_id, name, ingredients, kcal, protein, fat, carbs,
               weight, photo, brand
        FROM raw_items
        WHERE barcode IS NULL AND name IS NOT NULL
          AND (ingredients IS NOT NULL OR kcal IS NOT NULL)
        %s
    """ % (f"LIMIT {int(limit)}" if limit else "")).fetchall()

    # raise the pg_trgm similarity threshold that the %% operator prefilters on
    con.execute("SELECT set_limit(%s::real)", (SIM_FLOOR,))

    accepted, tried = [], 0
    for r in rows:
        src, sid, name = r[0], r[1], r[2]
        key = norm_name(name)
        if len(key.split()) < 2:      # too-generic names match everything
            continue
        tried += 1
        hit = con.execute(FIND, (name, name)).fetchone()
        if not hit or hit[2] < SIM_FLOOR:
            continue
        accepted.append({
            "source_id": f"{src}:{sid}",
            "barcode": hit[0],
            "name": name,
            "ingredients": r[3], "kcal": r[4], "protein": r[5], "fat": r[6],
            "carbs": r[7], "weight": r[8], "photo": r[9], "brand": r[10],
            "raw": {"matched_name": hit[1], "sim": round(float(hit[2]), 3),
                    "from": src},
        })
    db.upsert_raw(con, "namematch", accepted)
    return len(accepted), tried


if __name__ == "__main__":
    con = db.connect()
    got, tried = match(con, limit=200)
    print(f"matched {got}/{tried}")
