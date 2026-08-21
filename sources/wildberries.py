"""Wildberries FOOD — barcode (EAN-13) + КБЖУ + состав. Two endpoints joined
on nmId:

  enumerate  static-basket-01.wbbasket.ru main-menu -> node 10296 "Продукты"
             -> leaf cats -> catalog.wb.ru/catalog/{shard}/v2/catalog (nmIds)   [RU IP]
  barcode    card.wb.ru/cards/v2/detail?nm=a;b;c -> sizes[].skus[] (EAN-13)     [RU IP]
  КБЖУ/состав basket-NN.wbbasket.ru/volX/partY/nm/info/ru/card.json -> options  [any IP]

catalog + card are geo-blocked to RU IPs; the basket CDN is open. So a full run
needs a RU IP (for barcodes+enumeration), but the nutrition layer works anywhere.
КБЖУ/состав are seller-filled — present on most food cards, null-guarded.
"""
import re
import sys
import time

import os

from curl_cffi import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import normalize

MENU = "https://static-basket-01.wbbasket.ru/vol0/data/main-menu-ru-ru-v3.json"
FOOD_NODE = 10296
DEST = "-1257786"
PAGE_CAP = 100          # WB hard-caps catalog paging at page 100
SLEEP = 0.25

# basket host ranges by vol (drift as WB adds baskets -> neighbor-retry on 404)
_RANGES = [(0,143,1),(144,287,2),(288,431,3),(432,719,4),(720,1007,5),(1008,1061,6),
    (1062,1115,7),(1116,1169,8),(1170,1313,9),(1314,1601,10),(1602,1655,11),
    (1656,1919,12),(1920,2045,13),(2046,2189,14),(2190,2405,15),(2406,2621,16),
    (2622,2837,17),(2838,3053,18),(3054,3269,19),(3270,3485,20),(3486,3701,21),
    (3702,3917,22),(3918,4133,23),(4134,4349,24)]

_NUTR = {
    "пищевая ценность белки": "protein",
    "пищевая ценность жиры": "fat",
    "пищевая ценность углеводы": "carbs",
    "энергетическая ценность калории (на 100 гр.)": "kcal",
}


def _num(s):
    m = re.search(r"[\d]+(?:[.,]\d+)?", str(s or ""))
    return float(m.group(0).replace(",", ".")) if m else None


def _session():
    from sources import _util
    return _util.session()


def _leaf_cats(s):
    """Recurse the menu under node 10296, return leaf (shard, query) pairs."""
    try:
        menu = s.get(MENU).json()
    except Exception:
        return []
    node = _find(menu, FOOD_NODE)
    if not node:
        return []
    leaves = []

    def walk(n):
        kids = n.get("childs") or n.get("nodes") or []
        if not kids:
            if n.get("shard") and n.get("query") and n.get("shard") != "blackhole":
                leaves.append((n["shard"], n["query"]))
        for k in kids:
            walk(k)
    walk(node)
    return leaves


def _find(tree, wid):
    stack = list(tree if isinstance(tree, list) else [tree])
    while stack:
        n = stack.pop()
        if isinstance(n, dict):
            if n.get("id") == wid:
                return n
            stack += n.get("childs") or n.get("nodes") or []
    return None


def _nmids(s, shard, query, limit):
    out = []
    for page in range(1, PAGE_CAP + 1):
        url = (f"https://catalog.wb.ru/catalog/{shard}/v2/catalog?appType=1&{query}"
               f"&curr=rub&dest={DEST}&sort=popular&spp=30&page={page}")
        try:
            j = s.get(url).json()
        except Exception:
            break
        prods = (j.get("data") or {}).get("products") or []
        if not prods:
            break
        out += [p["id"] for p in prods]
        if limit and len(out) >= limit:
            break
        time.sleep(SLEEP)
    return out


def _card_batch(s, nmids):
    """card.wb.ru detail for up to ~100 nmIds -> {nmId: {skus,name,brand,price}}."""
    nm = ";".join(str(x) for x in nmids)
    url = (f"https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest={DEST}"
           f"&spp=30&nm={nm}")
    out = {}
    try:
        prods = (s.get(url).json().get("data") or {}).get("products") or []
    except Exception:
        return out
    for p in prods:
        skus = []
        price = None
        for sz in p.get("sizes") or []:
            skus += sz.get("skus") or []
            if price is None and (sz.get("price") or {}).get("total"):
                price = sz["price"]["total"] / 100
        barcode = next((normalize.norm_barcode(x) for x in skus
                        if normalize.norm_barcode(x)), None)
        out[p["id"]] = {"barcode": barcode, "name": p.get("name"),
                        "brand": p.get("brand"), "price": price}
    return out


def basket_url(nm, host):
    vol, part = nm // 100000, nm // 1000
    return (f"https://basket-{host:02d}.wbbasket.ru/vol{vol}/part{part}/{nm}"
            f"/info/ru/card.json")


def _basket(s, nm):
    """Fetch КБЖУ/состав/weight/country from the basket card.json (any IP)."""
    base = next((h for lo, hi, h in _RANGES if lo <= nm // 100000 <= hi), 1)
    for host in (base, base + 1, base - 1, base + 2):   # ranges drift -> neighbors
        if host < 1:
            continue
        try:
            r = s.get(basket_url(nm, host))
        except Exception:
            continue
        if r.status_code != 200:
            continue
        return r.json()
    return None


def parse_basket(j):
    if not j:
        return {}
    opts = {o.get("name", "").strip().lower(): o.get("value")
            for o in (j.get("options") or [])}
    out = {"name": j.get("imt_name"),
           "brand": (j.get("selling") or {}).get("brand_name")}
    for label, field in _NUTR.items():
        if label in opts:
            out[field] = _num(opts[label])
    ing = opts.get("состав")
    if not ing and j.get("compositions"):
        ing = (j["compositions"][0] or {}).get("name")
    out["ingredients"] = ing
    w = opts.get("вес товара без упаковки (г)") or opts.get("вес товара с упаковкой (г)")
    out["weight"] = w
    out["raw"] = {"country": opts.get("страна производства"),
                  "shelf_life": opts.get("срок годности"),
                  "fat_pct": opts.get("жирность")}
    return {k: v for k, v in out.items() if v not in (None, "", {})}


def fetch(limit=None):
    s = _session()
    leaves = _leaf_cats(s)
    if not leaves:
        print("[wildberries] menu/catalog unreachable — catalog.wb.ru is "
              "geo-blocked to RU IPs. Run from a RU IP.", file=sys.stderr, flush=True)
        return
    print(f"[wildberries] {len(leaves)} food leaf categories", file=sys.stderr, flush=True)

    # 1) enumerate nmIds
    nmids = []
    for shard, query in leaves:
        nmids += _nmids(s, shard, query, limit)
        if limit and len(nmids) >= limit:
            break
    nmids = list(dict.fromkeys(nmids))[:limit] if limit else list(dict.fromkeys(nmids))
    if not nmids:
        print("[wildberries] 0 nmIds (catalog geo-blocked). Run from RU IP.",
              file=sys.stderr, flush=True)
        return
    print(f"[wildberries] {len(nmids)} products; fetching barcodes + КБЖУ...",
          file=sys.stderr, flush=True)

    # 2) barcodes in batches of 100
    cards = {}
    for i in range(0, len(nmids), 100):
        cards.update(_card_batch(s, nmids[i:i + 100]))
        time.sleep(SLEEP)

    # 3) join with basket КБЖУ/состав, per nmId
    t0, ok, dead = time.time(), 0, 0
    for i, nm in enumerate(nmids, 1):
        c = cards.get(nm, {})
        b = parse_basket(_basket(s, nm))
        row = {"source_id": str(nm),
               "barcode": c.get("barcode"),
               "name": c.get("name") or b.get("name"),
               "brand": c.get("brand") or b.get("brand"),
               "ingredients": b.get("ingredients"),
               "kcal": b.get("kcal"), "protein": b.get("protein"),
               "fat": b.get("fat"), "carbs": b.get("carbs"),
               "weight": b.get("weight"), "raw": b.get("raw", {})}
        row["raw"]["price"] = c.get("price")
        if row["name"]:
            ok += 1
            yield {k: v for k, v in row.items() if v not in (None, "", {})}
        else:
            dead += 1
        if i % 10 == 0 or i == len(nmids):
            el = time.time() - t0
            print(f"\r[wildberries] {i}/{len(nmids)} | ok {ok} dead {dead} | "
                  f"{i / max(el, 1e-9):.1f}/s | {(c.get('name') or '-')[:28]}",
                  end="", file=sys.stderr, flush=True)
        time.sleep(SLEEP)
    print(file=sys.stderr)


def demo():
    j = {"imt_name": "Молоко сухое обезжиренное",
         "selling": {"brand_name": "ВкусвиллТест"},
         "compositions": [{"name": "молоко обезжиренное сухое 100%"}],
         "options": [
             {"name": "Состав", "value": "молоко обезжиренное сухое 100%"},
             {"name": "Пищевая ценность белки", "value": "32 г/100г"},
             {"name": "Пищевая ценность жиры", "value": "1.5 г/100г"},
             {"name": "Пищевая ценность углеводы", "value": "50.2 г/100г"},
             {"name": "Энергетическая ценность кал“ории (на 100 гр.)".replace("“", ""),
              "value": "342.3 ккал"},
             {"name": "Страна производства", "value": "Россия"},
             {"name": "Вес товара без упаковки (г)", "value": "1000 г"},
         ]}
    d = parse_basket(j)
    assert d["protein"] == 32.0 and d["fat"] == 1.5 and d["carbs"] == 50.2, d
    assert d["kcal"] == 342.3, d.get("kcal")
    assert "молоко обезжиренное" in d["ingredients"], d["ingredients"]
    assert d["weight"] == "1000 г", d["weight"]
    assert d["raw"]["country"] == "Россия"
    assert basket_url(12300811, 1) == \
        "https://basket-01.wbbasket.ru/vol123/part12300/12300811/info/ru/card.json"
    print("wildberries demo ok")


if __name__ == "__main__":
    if "--live" in sys.argv:
        n = 0
        for d in fetch(limit=5):
            n += 1
            print(n, d.get("barcode"), (d.get("name") or "")[:36], "| kcal", d.get("kcal"))
        print("fetched", n)
    else:
        demo()
