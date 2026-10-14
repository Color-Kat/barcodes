"""fix-price.com buyer API -> data/fixprice.db. Usage: see scrape.py.

Small (about a thousand food cards) but clean: `variants[].barcode`, «Состав» and nutrition as
separate fields. Listing pages give product ids, each card is one more request.
"""
import json
import math
import re

import scrape
from normalize import norm_barcode

API = "https://api.fix-price.com/buyer/v1"
LIMIT = 24  # what the site itself asks for; the API ignores anything above 28
CATEGORIES = ("produkty-i-napitki", "kosmetika-i-gigiena", "krasota-i-zdorove")


def listing(category, page):
    body, headers = scrape.request(f"{API}/product/in/{category}?page={page}&limit={LIMIT}&sort=sold", {
        "category": category, "brand": [], "price": [], "isDividedPrice": False, "isNew": False, "isHit": False,
        "isSpecialPrice": False})
    return json.dumps({"count": int(headers["x-count"]), "ids": [i["id"] for i in json.loads(body)]})


def menu():
    """Category id -> 'Top / Sub' title, as JSON text."""
    titles = {}

    def walk(nodes, path):
        for node in nodes or []:
            titles[node["id"]] = " / ".join(path + [node["title"]])
            walk(node.get("items"), path + [node["title"]])

    walk(json.loads(scrape.get(f"{API}/category/menu")), [])
    return json.dumps(titles, ensure_ascii=False)


def detail(key):
    return scrape.get(f"{API}/product/{key[2:]}")


def fetch(limit=None):
    cache = scrape.Cache("fixprice")
    if not cache.get("menu"):
        cache.put("menu", menu())
    ids = {i for _, text in scrape.listings(cache, CATEGORIES, listing, lambda first: math.ceil(json.loads(first)["count"] / LIMIT),
                                            first_only=bool(limit)) for i in json.loads(text)["ids"]}
    have = cache.keys()
    scrape.crawl(cache, [k for k in (f"p:{i}" for i in sorted(ids)) if k not in have][:limit], detail)


def parse(text, titles):
    """One card; `barcodes` is a list, a variant can carry several codes and internal article numbers."""
    card = json.loads(text)
    extras = {d["alias"]: d["value"] for d in card.get("extraDescriptions") or []}
    split = extras.get("nutritionalValueSeparated") or {}
    codes = " ".join(str(v.get("barcode") or "") for v in card.get("variants") or [])
    extra = {
        "url": "https://fix-price.com/catalog/" + card["url"] if card.get("url") else None, "sku": card.get("sku"),
        "description": card.get("description"), "nutrition_text": extras.get("nutritionalValue"),
        "manufacturer_address": extras.get("manufacturerAddress"),
        "attrs": {p["title"]: p["value"] for p in card.get("properties") or []},
    }
    return {
        "barcodes": list(dict.fromkeys(filter(None, map(norm_barcode, re.findall(r"\d{8,14}", codes))))),
        "source_id": card["id"], "name": card.get("title"), "brand": (card.get("brand") or {}).get("title") or None,
        "category": titles.get(str(card.get("category"))), "quantity": None,
        "ingredients": re.sub(r"^\s*Состав\s*:\s*", "", extras.get("composition") or "") or None,
        **scrape.nutrition(split.get("energyValue"), split.get("protein"), split.get("fats"), split.get("carbohydrates")),
        "photo": ((card.get("images") or [{}])[0]).get("src"),
        "extra": {k: v for k, v in extra.items() if v not in (None, "", {})},
    }


def rows():
    """build_db.py input: one dict per (card, barcode). Paper goods and tools are left out."""
    cache = scrape.Cache("fixprice")
    titles = json.loads(cache.get("menu") or "{}")
    for _, text in cache.items("p:"):
        card = parse(text, titles)
        if scrape.NOT_OURS.search(card["name"] or ""):
            continue
        for barcode in card.pop("barcodes"):
            yield {**card, "barcode": barcode}


def test():
    cache, key = scrape.Cache("fixprice"), "p:1001076"
    text = cache.get(key)
    if not text:
        text = detail(key)
        cache.put(key, text)
        cache.con.commit()
    c = parse(text, {"2004": "Продукты и напитки"})
    assert c["barcodes"] == ["4610030032405"] and c["name"].startswith("Молоко ультрапастеризованное, Славянское кружево")
    assert c["ingredients"] == "молоко цельное, молоко обезжиренное" and c["category"] == "Продукты и напитки"
    assert (c["kcal"], c["protein"], c["fat"], c["carbs"]) == (64, 3, 3.2, 4.7)
    assert c["photo"].startswith("https://img.fix-price.com/") and c["extra"]["attrs"]["Страна производства"] == "Россия"
    zero = json.dumps({"id": 1, "extraDescriptions": [{"alias": "nutritionalValueSeparated", "value": {
        "energyValue": "0", "protein": "0", "fats": "0", "carbohydrates": "0"}}], "variants": [{"barcode": "46196613, 1720074"}]})
    z = parse(zero, {})
    assert z["kcal"] is None and z["barcodes"] == ["46196613"]
    print("fixprice ok")


if __name__ == "__main__":
    scrape.main(fetch, rows, test)
