"""auchan.ru JSON API -> data/auchan.db. Usage: see scrape.py.

The site's HTML is behind Qrator, the /v1 JSON API it calls is not. Listing pages carry no
barcode, so every card needs its own product-detail request (`mainEan`, «Состав», energy_value).
Cards Auchan no longer sells stay in the catalogue as inactive and still answer, though often
without an EAN; they are fetched after the active ones (~19k active, ~100k in all).
"""
import json
import math
import urllib.parse

import scrape
from normalize import norm_barcode

API = "https://www.auchan.ru/v1"
PER_PAGE = 100  # the API caps perPage at 100
# food, drinks, baby food and supplements; the rest of the hypermarket is not ours
FOOD = (
    "moloko-syr-yayca", "epica", "ptica-myaso", "ryba-ikra-moreprodukty", "fermerskie_produkty_5", "syry",
    "ovoschi-frukty-zelen-griby-yagody", "zamorozhennye-produkty", "kolbasnye-izdeliya", "kulinariya",
    "hlebnaya-vypechka", "bakaleya", "konditerskie_izdeliya", "orehi-suhofrukty-sneki", "chay-kofe-sladosti",
    "voda-soki-napitki", "alkogol", "zdorovyy-vybor", "sportivnoe_pitanie_i_bady", "nastoyashchaya_aziya",
    "regiony_rossii", "sdelano_v_ashan", "detskoe-pitanie", "vitaminy_i_pishchevye_dobavki",
)
# cosmetics are not the focus yet: fetched only after every food card, inactive ones included
COSMETICS = (
    "sredstva-lichnoy-gigieny", "uhod-za-telom", "uhod-za-licom", "uhod-za-volosami", "uhod-za-polostyu-rta",
    "uhod_za_rukami_i_nogami_2", "koreyskaya_kosmetika", "organicheskaya_kosmetika", "professionalnaya_kosmetika",
    "parfyumeriya_i_makiyazh", "butik",
)
DROP = ("stock", "image_titles", "media")  # shop-by-shop stock is 90% of a card's bytes


def listing(category, page):
    body = scrape.get(f"{API}/catalog/products?merchantId=1&page={page}&perPage={PER_PAGE}", {"filter": {
        "category": category, "promo_only": False, "active_only": False, "cashback_only": False}})
    data = json.loads(body)
    return json.dumps({"range": data["range"], "items": [[i["code"], bool(i["active"])] for i in data["items"]]})


def detail(key):
    body = scrape.get(f"{API}/catalog/product-detail?code={urllib.parse.quote(key[2:])}&merchantId=1")
    if body is None:
        return None
    card = json.loads(body)
    for field in DROP:
        card.pop(field, None)
    return json.dumps(card, ensure_ascii=False)


def fetch(limit=None):
    cache = scrape.Cache("auchan")
    active, food = {}, set()
    for category, text in scrape.listings(cache, FOOD + COSMETICS, listing,
                                          lambda first: math.ceil(json.loads(first)["range"] / PER_PAGE),
                                          first_only=bool(limit)):  # a --limit test run lists only page 1 of each category
        for code, is_active in json.loads(text)["items"]:
            active[code] = active.get(code, False) or is_active
            if category in FOOD:
                food.add(code)
    have = cache.keys()
    todo = ["p:" + code for code in sorted(active, key=lambda c: (c not in food, not active[c], c))]
    scrape.crawl(cache, [k for k in todo if k not in have][:limit], detail)


def parse(text):
    card = json.loads(text)
    attrs = {c["title"]: c["value"] for c in card.get("characteristics") or [] if c.get("value") not in (None, "")}
    energy = card.get("energy_value") or {}
    # «Объем, л» is often a stray 1 on goods sold by weight, so the net mass is trusted first
    quantity = next((f"{attrs[k]} {unit}" for k, unit in (("Масса нетто, кг", "кг"), ("Объем, л", "л")) if k in attrs), None)
    brand = (card.get("brand") or {}).get("name")
    extra = {
        "url": f"https://www.auchan.ru/product/{card['code']}/", "gima_id": card.get("gimaId"),
        "active": card.get("active"), "rating": (card.get("rate") or {}).get("rating"),
        "description": (card.get("description") or {}).get("content"),
        "attrs": {k: v for k, v in attrs.items() if k != "Состав"},
    }
    return {
        "barcode": norm_barcode(card.get("mainEan")), "source_id": card["code"], "name": card.get("title"),
        "brand": brand if brand not in ("-", "") else None,
        "category": " / ".join(c["name"] for c in card.get("categoryCodes") or []) or None,
        "quantity": quantity, "ingredients": attrs.get("Состав"),
        **scrape.nutrition(energy.get("calories"), energy.get("proteins"), energy.get("fats"), energy.get("carbohydrates")),
        "photo": (card.get("mediaUrls") or [None])[0],
        "extra": {k: v for k, v in extra.items() if v not in (None, "", {})},
    }


def rows():
    """build_db.py input. Cards still on sale are yielded last, so they win a shared barcode.

    Weighed goods carry Auchan's own 2xxxxxxxxxxxx codes in mainEan; they are kept like any other.
    """
    cards = (parse(text) for _, text in scrape.Cache("auchan").items("p:"))
    yield from sorted((c for c in cards if c["barcode"] and not scrape.NOT_OURS.search(c["name"] or "")),
                      key=lambda c: bool(c["extra"].get("active")))


def test():
    cache, key = scrape.Cache("auchan"), "p:sok-j-7-apelsin-s-myakotyu-ohlazhdennyy-850-ml"
    text = cache.get(key)
    if not text:
        text = detail(key)
        cache.put(key, text)
        cache.con.commit()
    c = parse(text)
    assert c["barcode"] == "4600494694813" and c["brand"] == "J7" and c["name"].startswith("Сок J7 Fresh Taste")
    assert c["quantity"] == "0.85 кг" and c["category"].startswith("Молочные продукты, яйца / ")
    assert c["ingredients"] and c["kcal"] == 45 and c["carbs"] == 11 and c["photo"].startswith("https://www.auchan.ru/files/")
    assert c["extra"]["attrs"]["Страна производства"] == "Россия" and "Состав" not in c["extra"]["attrs"]
    assert "stock" not in json.loads(text)
    print("auchan ok")


if __name__ == "__main__":
    scrape.main(fetch, rows, test)
