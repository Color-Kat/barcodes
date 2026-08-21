"""Resolve barcodes for barcode-less enriched rows (magnit etc.) via
barcode-list.ru name search — the "поиск данных по названию" step.

magnit has name+состав+КБЖУ but no EAN. barcode-list.ru search accepts a
free-text name and returns barcode+name candidates. For each barcode-less
enriched row we search, pick the candidate whose name best matches by token
Jaccard, and accept only above THRESHOLD (high precision — never attach КБЖУ
to the wrong barcode). Accepted rows are written under source 'namematch'
with barcode + the original enrichment, so core.merge() folds them into
products as fully-enriched (barcode+name+состав+КБЖУ).

Re-runnable: upsert by source_id (the barcode-less row's source:source_id).
"""
import sys
from urllib.parse import quote

import core
from sources import _http
from sources import barcode_list_ru as bl

THRESHOLD = 0.7  # min token overlap-coefficient to accept a name match


def tokens(s):
    return set(core.norm_name(s).split())


def overlap(a, b):
    """Overlap coefficient |a∩b| / min(|a|,|b|): rewards subset matches, so a
    magnit name with extra weight/format tokens still matches its shorter
    barcode-list twin. Higher recall than Jaccard at similar precision."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def resolve(con, limit=None, min_interval=0.5):
    s = _http.session()
    src_rows = con.execute(
        "SELECT source, source_id, name, ingredients, kcal, protein, fat, carbs,"
        " weight, photo, brand, extra FROM raw_items"
        " WHERE barcode IS NULL AND name IS NOT NULL"
        "   AND (ingredients IS NOT NULL OR kcal IS NOT NULL)"
    ).fetchall()
    accepted, n = [], 0
    for r in src_rows:
        if limit and n >= limit:
            break
        src, sid, name = r[0], r[1], r[2]
        want = tokens(name)
        if len(want) < 2:            # too-short names match everything — skip
            continue
        # query with the CLEANED name (weights/% stripped) — barcode-list search
        # returns far more candidates than on the raw noisy name.
        query = core.norm_name(name) or name
        try:
            resp = _http.get(s, bl.SEARCH_URL.format(quote(query)), min_interval=min_interval)
        except Exception:
            continue
        if resp.status_code != 200:
            continue
        best, best_j = None, 0.0
        for barcode, cand_name, _unit, _rating in bl._parse(resp.text):
            j = overlap(want, tokens(cand_name))
            if j > best_j:
                best, best_j = (barcode, cand_name), j
        n += 1
        if not best or best_j < THRESHOLD:
            continue
        if not core.norm_barcode(best[0]):
            continue
        accepted.append({
            "source_id": f"{src}:{sid}",
            "barcode": best[0],
            "name": name,
            "ingredients": r[3], "kcal": r[4], "protein": r[5], "fat": r[6],
            "carbs": r[7], "weight": r[8], "photo": r[9], "brand": r[10],
            "extra": {"matched_name": best[1], "match_score": round(best_j, 2),
                      "from": src},
        })
    core.upsert_raw(con, "namematch", accepted)
    return len(accepted), n


def demo():
    assert overlap(tokens("Чай зеленый Tess Pina Colada"),
                   tokens("Чай TESS Pina Colada зеленый пирамидки")) >= 0.6
    assert overlap(tokens("Молоко 3.2%"), tokens("Пиво светлое")) == 0.0
    print("resolve demo ok")


if __name__ == "__main__":
    if "--live" in sys.argv:
        con = core.connect()
        got, tried = resolve(con, limit=int(sys.argv[-1]) if sys.argv[-1].isdigit() else 50)
        print(f"resolved {got}/{tried} barcodes via name search")
    else:
        demo()
