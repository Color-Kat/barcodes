"""Метро (metro-cc.ru) — GraphQL API. The jackpot source: one call returns
EAN barcode + КБЖУ + состав + brand + weight together, and it's bulk-paginable
by category. B2B wholesale, so `barcodes` carries real GTINs.

Endpoint: POST https://api.metro-cc.ru/products-api/graph  (note /graph)
Anonymous; needs a storeId (nutrition/composition/barcodes are store-independent,
only price varies). curl_cffi chrome impersonation required (TLS fingerprint).

Contract confirmed from 5+ GitHub scrapers incl. a production query capture that
included the `barcodes` field. Verify from a RU IP (datacenter IPs are WAF-blocked).
"""
import os
import sys
import time

from curl_cffi import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import normalize

ENDPOINT = "https://api.metro-cc.ru/products-api/graph"
STORE_ID = 83
PAGE = 100
SLEEP = 0.8
HEADERS = {
    "content-type": "application/json",
    "origin": "https://online.metro-cc.ru",
    "referer": "https://online.metro-cc.ru/",
}

# food category slugs; children are discovered via dynamic_categories at runtime
FOOD_ROOTS = [
    "moloko-syr-yaica", "myaso-ptica", "ryba-i-moreprodukty", "bakaleya",
    "napitki", "zamorozhennye-produkty", "ovoshchi-i-frukty", "hleb",
    "konditerskie-izdeliya", "chipsy-suhari-sneki", "sousy-specii",
    "chai-kofe-kakao", "detskoe-pitanie", "konservy",
]

CAT_QUERY = """
query($storeId:Int!,$slug:String!,$from:Int!,$size:Int!){
  category(storeId:$storeId, slug:$slug, inStock:false){
    total
    dynamic_categories(from:0, size:9999){ slug }
    products(from:$from, size:$size, sort:default){
      id name barcodes url images description
      manufacturer{ name }
      packing{ size type }
      attributes{ name text }
    }
  }
}
"""

_NUTR = {
    "белки": "protein", "жиры": "fat", "углеводы": "carbs",
    "калорийность": "kcal", "энергетическая ценность": "kcal",
}


def _num(s):
    import re
    m = re.search(r"[\d]+(?:[.,]\d+)?", str(s or ""))
    return float(m.group(0).replace(",", ".")) if m else None


def _post(s, slug, frm, size):
    r = s.post(ENDPOINT, json={"query": CAT_QUERY,
               "variables": {"storeId": STORE_ID, "slug": slug,
                             "from": frm, "size": size}})
    if r.status_code != 200:
        return None
    return (r.json() or {}).get("data", {}).get("category")


def parse_product(p):
    # pick the first checksum-valid consumer EAN from the barcodes array
    barcode = None
    for b in (p.get("barcodes") or []):
        nb = normalize.norm_barcode(b)
        if nb:
            barcode = nb
            break
    out = {
        "source_id": str(p.get("id")),
        "barcode": barcode,
        "name": p.get("name"),
        "brand": (p.get("manufacturer") or {}).get("name"),
        "photo": (p.get("images") or [None])[0],
        "raw": {"url": p.get("url"), "all_barcodes": p.get("barcodes")},
    }
    pk = p.get("packing") or {}
    if pk.get("size"):
        out["weight"] = f"{pk.get('size')} {pk.get('type') or ''}".strip()
    ingredients = None
    for a in (p.get("attributes") or []):
        nm = (a.get("name") or "").strip().lower()
        val = a.get("text")
        if nm in _NUTR and out.get(_NUTR[nm]) is None:
            out[_NUTR[nm]] = _num(val)
        elif nm.startswith("состав"):
            ingredients = val
    out["ingredients"] = ingredients or (
        p.get("description") if p.get("description") and "состав" in
        (p.get("description") or "").lower() else None)
    return {k: v for k, v in out.items() if v not in (None, "", {})}


def fetch(limit=None):
    from sources import _util
    s = _util.session(headers=HEADERS, impersonate="chrome124")

    # discover full slug set (roots + their children), tolerant of blocks
    slugs, seen = [], set()
    for root in FOOD_ROOTS:
        try:
            cat = _post(s, root, 0, 0)
        except Exception:
            cat = None
        if not cat:
            continue
        for sl in [root] + [c["slug"] for c in (cat.get("dynamic_categories") or [])]:
            if sl not in seen:
                seen.add(sl)
                slugs.append(sl)
    if not slugs:
        print("[metro] no categories reachable — datacenter IP is WAF-blocked; "
              "run from a RU IP.", file=sys.stderr, flush=True)
        return
    print(f"[metro] {len(slugs)} food categories to page", file=sys.stderr, flush=True)

    t0, n, ok, dead = time.time(), 0, 0, 0
    for slug in slugs:
        frm = 0
        while True:
            try:
                cat = _post(s, slug, frm, PAGE)
            except Exception:
                cat = None
            if not cat:
                dead += 1
                break
            prods = cat.get("products") or []
            if not prods:
                break
            for p in prods:
                row = parse_product(p)
                if row.get("name"):
                    ok += 1
                    yield row
                n += 1
                if limit and n >= limit:
                    print(file=sys.stderr)
                    return
            el = time.time() - t0
            print(f"\r[metro] {n} seen | ok {ok} dead {dead} | "
                  f"{n / max(el, 1e-9):.1f}/s | cat {slug[:24]} +{frm}",
                  end="", file=sys.stderr, flush=True)
            frm += PAGE
            total = cat.get("total") or 0
            if frm >= total or frm >= 5000:      # backend caps deep paging
                break
            time.sleep(SLEEP)
    print(file=sys.stderr)


def demo():
    p = {
        "id": 123, "name": "Молоко 3.2%", "barcodes": ["4600000000000", "4601374000014"],
        "manufacturer": {"name": "Простоквашино"},
        "images": ["https://x/img.jpg"], "packing": {"size": "930", "type": "мл"},
        "description": "молоко цельное",
        "attributes": [
            {"name": "Белки", "text": "2.9 г"},
            {"name": "Жиры", "text": "3.2 г"},
            {"name": "Углеводы", "text": "4.7 г"},
            {"name": "Калорийность", "text": "59 ккал"},
            {"name": "Состав", "text": "молоко нормализованное"},
        ],
    }
    d = parse_product(p)
    assert d["barcode"] == "4601374000014", d["barcode"]   # first VALID ean picked
    assert d["protein"] == 2.9 and d["fat"] == 3.2 and d["carbs"] == 4.7
    assert d["kcal"] == 59.0, d["kcal"]
    assert d["ingredients"] == "молоко нормализованное"
    assert d["brand"] == "Простоквашино"
    assert d["weight"] == "930 мл"
    print("metro demo ok")


if __name__ == "__main__":
    if "--live" in sys.argv:
        n = 0
        for d in fetch(limit=5):
            n += 1
            print(n, d.get("barcode"), d["name"][:40], "| kcal", d.get("kcal"))
        print("fetched", n)
    else:
        demo()
