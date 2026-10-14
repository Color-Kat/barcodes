"""globus.ru (Next.js) -> data/globus.db. Usage: see scrape.py.

The barcode is not in the visible page, only in the product JSON (`product.ean`), which the
Next data route serves without the HTML: /_next/data/<buildId>/products/<slug>.json. Cards come
from two sitemaps (~48k, the whole hypermarket); rows() keeps food, drinks and cosmetics.
"""
import json
import re

import scrape
from normalize import norm_barcode

BASE = "https://www.globus.ru"
SITEMAPS = ("sitemappdp1.xml", "sitemappdp2.xml")
# catalogue paths to keep: whole food sections, plus the edible and cosmetic parts of two mixed ones
KEEP = {(name,) for name in (
    "Готовая еда", "Почти готово", "Овощи, фрукты, зелень", "Молочные продукты, сыр, яйца", "Мясо, птица, колбасы",
    "Рыба, икра, морепродукты", "Хлеб, выпечка", "Замороженные продукты", "Бакалея", "Чай, кофе, какао", "Сладости",
    "Чипсы, снеки, орехи", "Алкоголь", "Безалкогольные напитки", "Здоровый выбор", "Собственное производство",
)} | {("Детские товары", sub) for sub in (
    "Детское питание", "Детская гигиена и косметика", "Напитки для детей",
)} | {("Косметика и гигиена", sub) for sub in (
    "Уход за волосами", "Уход за телом", "Уход за руками и ногами", "Уход за лицом", "Мужчинам", "Уход за полостью рта",
    "Всё для бритья и депиляции", "Парфюмерия")}
PROMO = {"Акции", "Собственное производство", "Наши марки"}  # these repeat goods of the real sections


def build_id():
    return re.search(r'"buildId":"([^"]+)"', scrape.get(BASE + "/")).group(1)


def fetch(limit=None):
    cache = scrape.Cache("globus")
    slugs = sorted({slug for sitemap in SITEMAPS
                    for slug in re.findall(r"<loc>https://www\.globus\.ru/products/([^/<]+)/?</loc>", scrape.get(f"{BASE}/{sitemap}"))})
    have = cache.keys()
    build = [build_id()]

    def product(slug):
        body = scrape.get(f"{BASE}/_next/data/{build[0]}/products/{slug}.json")
        if body is None:  # a card that is gone, or a new deploy changed the buildId
            fresh = build_id()
            if fresh == build[0]:
                return None
            build[0] = fresh
            body = scrape.get(f"{BASE}/_next/data/{fresh}/products/{slug}.json")
            if body is None:
                return None
        queries = {q["queryKey"][0] if isinstance(q["queryKey"], list) else q["queryKey"]: q["state"]["data"]
                   for q in json.loads(body)["pageProps"].get("dehydratedState", {}).get("queries", [])}
        if "menu" not in have and "header-dropdown-and-menu" in queries:
            cache.put("menu", json.dumps(queries["header-dropdown-and-menu"]["data"]["menu"]["catalog"], ensure_ascii=False))
            have.add("menu")
        card = ((queries.get("product-detail") or {}).get("data") or {}).get("product")
        return json.dumps(card, ensure_ascii=False) if card else None

    scrape.crawl(cache, [s for s in slugs if s not in have][:limit], product)


def paths(menu):
    """Category id -> [top section, ..., own name]. Promo sections go last so the real one wins."""
    found = {}

    def walk(node, path):
        path = path + [node["name"]]
        found.setdefault(node["id"], path)
        for child in node.get("categories") or []:
            walk(child, path)

    for top in sorted(menu, key=lambda t: t["name"] in PROMO):
        walk(top, [])
    return found


def parse(text, tree):
    p = json.loads(text)
    attrs = {i["name"]: "; ".join(map(str, i["value"])) if isinstance(i["value"], list) else i["value"]
             for g in p.get("attribute_groups") or [] for i in g.get("items") or [] if any(i.get("value") or [])}
    energy = p.get("food_energy") or {}
    path = tree.get(p.get("main_category_id")) or []
    extra = {"url": BASE + p["url"] if p.get("url") else None, "vendor_code": p.get("vendor_code"), "active": p.get("active"),
             "attrs": {k: v for k, v in attrs.items() if k not in ("Состав", "Бренд")}}
    return {
        "barcode": norm_barcode(p.get("ean")), "source_id": p.get("id"), "name": p.get("name"),
        "brand": (p.get("brand") or {}).get("name"), "category": " / ".join(path) or None, "path": path,
        "quantity": p.get("weight_text"), "ingredients": attrs.get("Состав"),
        **scrape.nutrition(energy.get("energy"), energy.get("protein"), energy.get("fat"), energy.get("carbohydrate")),
        "photo": ((p.get("image_gallery") or [{}])[0]).get("src"),
        "extra": {k: v for k, v in extra.items() if v not in (None, "", {})},
    }


def rows():
    """build_db.py input: cards of the KEEP sections, plus any card with nutrition values.

    «Состав» alone does not make a card food: for household goods it holds the material («полимер»).
    """
    cache = scrape.Cache("globus")
    tree = paths(json.loads(cache.get("menu") or "[]"))
    for key, text in cache.items():
        if key == "menu":
            continue
        card = parse(text, tree)
        path = card.pop("path")
        ours = tuple(path[:1]) in KEEP or tuple(path[:2]) in KEEP or card["kcal"] is not None
        if card["barcode"] and ours and not scrape.NOT_OURS.search(card["name"] or ""):
            yield card


def test():
    cache = scrape.Cache("globus")
    text = cache.get("kefir-prostokvashino-32-930g-27692_ST")
    assert text, "fetch first: the self-check needs the cached Простоквашино kefir card"
    tree = paths(json.loads(cache.get("menu")))
    c = parse(text, tree)
    assert c["barcode"] == "4607053473803" and c["name"] == "Кефир Простоквашино 3,2%, 930г" and c["brand"] == "Простоквашино"
    assert c["ingredients"] == "молоко нормализованное, закваска на кефирных грибках"
    assert (c["kcal"], c["protein"], c["fat"], c["carbs"]) == (57, 3, 3.2, 4)
    assert c["path"][0] == "Молочные продукты, сыр, яйца" and c["photo"].startswith("https://image.globus.ru/web/")
    assert c["extra"]["attrs"]["Страна-производитель"] == "Россия" and "Состав" not in c["extra"]["attrs"]
    assert paths([{"id": 1, "name": "Акции", "categories": [{"id": 9, "name": "x"}]},
                  {"id": 2, "name": "Бакалея", "categories": [{"id": 9, "name": "Крупы"}]}])[9] == ["Бакалея", "Крупы"]
    print("globus ok")


if __name__ == "__main__":
    scrape.main(fetch, rows, test)
