"""«Честный знак» mobile backend (Нацкаталог cards by EAN) -> data/chestnyznak.db. Stdlib only.

    export HTTPS_PROXY=http://172.21.80.1:10809   # WSL: direct connections mostly time out
    python3 chestnyznak.py                # ask about every barcodes.db EAN-13 not asked yet, resumable
    python3 chestnyznak.py --limit 50     # cheap test run
    python3 chestnyznak.py --stats        # parse what is cached, print field coverage
    python3 chestnyznak.py --test         # parser self-check on a cached card

`POST mobile.api.crpt.ru/mobile/check {"code": EAN, "codeType": "ean13"}` answers without
authorization with the Нацкаталог card: name, brand, «Состав», КБЖУ, photos, packaging. The
endpoint is undocumented and other teams have seen it answer 403/451, so the fetcher gives up
after FAIL_LIMIT refusals in a row instead of hammering it.

Two stages, like rskrf.py: raw answers are kept (zlib) in data/chestnyznak.db, one row per
barcode, found or not; build_db.py calls rows() to load the parsed cards as provider `chestnyznak`.
"""
import http.client
import json
import os
import re
import sqlite3
import sys
import time
import urllib.request
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "data", "chestnyznak.db")
MAIN = os.path.join(HERE, "barcodes.db")
URL = "https://mobile.api.crpt.ru/mobile/check"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
SLEEP = 0.5  # ponytail: one polite thread, ~100k barcodes a day; add workers only if that is too slow
FAIL_LIMIT = 10

# card attributes lifted into columns; everything else lands in extra["attrs"]
QUANTITY = ("Заявленный объём / вес нетто", "Масса нетто", "Заявленный объем", "Объём потребительской единицы")
NUTRITION = {"kcal": ("Энергетическая ценность, ккал",), "protein": ("Белки, количество",),
             "fat": ("Жиры, количество",), "carbs": ("Углеводы, количество", "Количество углеводов, г/100 мл")}
NO_BRAND = {"нет", "отсутствует", "без бренда", "без товарного знака", "-"}  # producers type these in
# attribute groups that say nothing about what is inside the pack
SKIP_GROUPS = {"Разрешительная документация", "Нормативно-сопроводительная документация",
               "Данные для ФГИС ВетИС", "Содержимое упаковки"}


def connect():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    con = sqlite3.connect(DB, timeout=120)
    con.execute("PRAGMA journal_mode=WAL")  # --stats and build_db.py read while the fetcher writes
    con.execute("CREATE TABLE IF NOT EXISTS checks (barcode TEXT PRIMARY KEY, found INTEGER, body BLOB, "
                "fetched_at TEXT) WITHOUT ROWID")
    return con


def targets():
    """EAN-13s of barcodes.db, most wanted first: Russian prefix (460-469) without a composition,
    Russian with one, then the rest. Barcodes known only as cosmetics go after all of those:
    cosmetics are not the focus yet. Shuffled inside a group (crc32) so that --stats on a partial
    run is representative. In-store codes (prefix 2) are not GS1 articles and are skipped.
    """
    con = sqlite3.connect(f"file:{MAIN}?mode=ro", uri=True)
    found = con.execute(
        "SELECT barcode, max(ingredients IS NOT NULL), max(provider = 'uhtt'), "
        "       max(category LIKE 'Продукты питания (folder)%' OR kcal IS NOT NULL "
        "           OR provider IN ('openfoodfacts', 'barcode_list_ru')) "
        "FROM products WHERE length(barcode) = 13 AND barcode NOT LIKE '2%' GROUP BY barcode").fetchall()
    # in uhtt, but nothing calls it food: it got into the base through a cosmetics folder
    found.sort(key=lambda r: (bool(r[2]) and not r[3], not "460" <= r[0][:3] <= "469", bool(r[1]), zlib.crc32(r[0].encode())))
    return [r[0] for r in found]


def check(barcode):
    """Raw JSON answer for one EAN. Raises OSError on timeouts and on 403/429/451."""
    req = urllib.request.Request(URL, data=json.dumps({"code": barcode, "codeType": "ean13"}).encode(), headers={
        "User-Agent": UA, "Accept": "application/json", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def fetch(limit=None):
    con = connect()
    done = {b for (b,) in con.execute("SELECT barcode FROM checks")}
    todo = [b for b in targets() if b not in done][:limit]
    print(f"cached {len(done)}, to ask {len(todo)}", flush=True)
    fails = found = 0
    for i, barcode in enumerate(todo, 1):
        try:
            body = check(barcode)
            hit = bool(json.loads(body)["codeFounded"])
        except (OSError, http.client.HTTPException, ValueError, KeyError, TypeError) as e:
            fails += 1
            print(f"{barcode}: {e!r} ({fails} in a row)", flush=True)
            if fails >= FAIL_LIMIT:
                con.commit()
                sys.exit(f"{FAIL_LIMIT} failures in a row, stopping. Proxy down or the endpoint is closed; "
                         "nothing is lost, rerun later to continue.")
            time.sleep(30 * fails)
            continue  # not stored, so the next run asks again
        fails = 0
        found += hit
        con.execute("INSERT OR REPLACE INTO checks VALUES (?,?,?,?)",
                    (barcode, hit, zlib.compress(body), time.strftime("%Y-%m-%dT%H:%M:%S")))
        if i % 50 == 0 or i == len(todo):
            con.commit()
            print(f"{i}/{len(todo)} found {found}", flush=True)
        time.sleep(SLEEP)
    con.commit()


def num(value):
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None


def kind(codes):
    """'food', 'cosmetics' or 'other' out of a card's ТН ВЭД and ОКПД2 codes; None when it has none.

    ТН ВЭД chapters 02-22 are food and drinks (23 is pet food, 24 tobacco), 33 and soap (3401) are
    cosmetics. ОКПД2 classes 01, 03, 10, 11 are food, 20.42 and 20.41.3 cosmetics.
    """
    seen = set()
    for code in codes:
        code = str(code).strip()
        if re.match(r"\d\d\.\d\d", code):
            seen.add("food" if code[:2] in ("01", "03", "10", "11") else
                     "cosmetics" if code.startswith(("20.42", "20.41.3")) else "other")
        elif re.match(r"\d{4}", code):
            seen.add("food" if 2 <= int(code[:2]) <= 22 or code.startswith("2501") else
                     "cosmetics" if code.startswith(("33", "3401")) else "other")
    return next((k for k in ("food", "cosmetics", "other") if k in seen), None)


def parse(body):
    """Card dict out of one answer, or None when Нацкаталог does not know the code.

    A card is either published (attributes filled by the producer) or a stub with just a name.
    """
    data = json.loads(body)
    cards = data.get("catalogData") or []
    if not cards:
        return None
    card = cards[0]
    attrs, units, kept = {}, {}, {}
    for a in card.get("good_attrs") or []:
        name, value = a.get("attr_name"), a.get("attr_value")
        if not name or value in (None, ""):
            continue
        attrs.setdefault(name, []).append(value)
        units[name] = a.get("attr_value_type") or ""
        if a.get("attr_group_name") not in SKIP_GROUPS:
            kept.setdefault(name, []).append(value)

    def first(names):
        return next((attrs[n][0] for n in names if n in attrs), None)

    quantity = next((f"{attrs[n][0]} {units[n]}".strip() for n in QUANTITY if n in attrs), None)
    for name in ("Состав", "Товарный знак", "Полное наименование товара", *QUANTITY, *(n for names in NUTRITION.values() for n in names)):
        kept.pop(name, None)
    photos = sorted(card.get("good_images") or [], key=lambda p: p.get("photo_date") or "", reverse=True)
    rsk = card.get("roskachestvo") or {}
    brand = card.get("brand_name") or first(("Товарный знак",))
    extra = {
        "good_id": card.get("good_id"), "url": card.get("good_url"), "status": card.get("good_status"),
        "producer": card.get("producer_name"), "producer_inn": card.get("producer_inn"),
        "updated": card.get("update_date"), "categories": [c.get("cat_name") for c in card.get("categories") or []],
        "nutrition_unit": first(("Единица измерения белков, жиров, углеводов",)),
        "kind": kind(attrs.get("Код ТНВЭД", []) + attrs.get("Группа ТНВЭД", []) + attrs.get("Код ОКПД2", [])
                     + [c.get("cat_name") or "" for c in card.get("categories") or []]),
        "gtins": [i for i in card.get("identified_by") or [] if i.get("level") != "trade-unit"],
        "attrs": {k: v[0] if len(v) == 1 else v for k, v in kept.items()},
        "roskachestvo": {k: rsk.get(k) for k in ("product_link", "total_rating", "has_quality_mark") if rsk.get(k) is not None},
    }
    return {
        "source_id": card.get("good_id"),
        "name": first(("Полное наименование товара",)) or card.get("good_name") or data.get("productName"),
        "brand": brand if brand and brand.lower() not in NO_BRAND else None,
        "category": extra["categories"][0] if extra["categories"] else None,
        "quantity": quantity, "ingredients": first(("Состав",)),
        "photo": photos[0].get("photo_url") if photos else None,
        "extra": {k: v for k, v in extra.items() if v not in (None, "", [], {})},
        **{key: num(first(names)) for key, names in NUTRITION.items() if first(names) is not None},
    }


def rows():
    """build_db.py input: one dict per barcode Нацкаталог knows, minus cards it files as neither
    food nor cosmetics (clothes, tobacco, pet food). Stubs carry no codes and are kept."""
    if not os.path.exists(DB):
        return
    for barcode, body in connect().execute("SELECT barcode, body FROM checks WHERE found"):
        card = parse(zlib.decompress(body))
        if card and card["name"] and card["extra"].get("kind") != "other":
            yield {**card, "barcode": barcode}


def stats():
    asked, found = connect().execute("SELECT count(*), sum(found) FROM checks").fetchone()
    out = list(rows())
    print(f"asked {asked}, found {found or 0}, cards {len(out)}, "
          f"published {sum(r['extra'].get('status') == 'published' for r in out)}")
    for key in ("name", "brand", "category", "quantity", "ingredients", "kcal", "protein", "fat", "carbs", "photo"):
        print(f"  {key:12} {sum(r.get(key) is not None for r in out)}")


def test():
    row = connect().execute("SELECT body FROM checks WHERE barcode = '4601576000027'").fetchone()
    assert row, "fetch first: the self-check needs the cached ЕЖК mayonnaise card"
    c = parse(zlib.decompress(row[0]))
    assert c["name"] == "Майонез Провансаль ЕЖК 67% стакан 241г" and c["brand"] == "ЕЖК"
    assert c["quantity"] == "241 г" and c["ingredients"].startswith("масло подсолнечное рафинированное")
    assert (c["kcal"], c["protein"], c["fat"], c["carbs"]) == (610, 0.6, 67, 2)
    assert c["category"] == "Соусы, приправы, горчица" and c["photo"] is None
    e = c["extra"]
    assert e["kind"] == "food" and kind(["3304990000"]) == kind(["20.42.15.110"]) == "cosmetics"
    assert kind(["6403", "15.20.1"]) == kind(["2309"]) == "other" and kind(["Молочная продукция"]) is None
    assert e["status"] == "published" and e["producer_inn"] == "6664014643" and e["nutrition_unit"] == "г/100г"
    assert e["attrs"]["Содержит ГМО"] == "НЕТ" and len(e["attrs"]["Срок и условия хранения"]) == 2
    assert "Состав" not in e["attrs"] and "Код ТНВЭД" not in e["attrs"]
    assert parse(b'{"codeFounded": false, "status": "not_found"}') is None
    assert num("1,5") == 1.5 and num("нет") is None
    print("chestnyznak ok")


if __name__ == "__main__":
    arg = sys.argv[1:]
    if "--test" in arg:
        test()
    elif "--stats" in arg:
        stats()
    else:
        fetch(int(arg[arg.index("--limit") + 1]) if "--limit" in arg else None)
        stats()
