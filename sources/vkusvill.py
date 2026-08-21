"""ВкусВилл enrichment source — состав + КБЖУ + manufacturer, NO barcode.

vkusvill.ru serves full product cards at 200 even from a foreign IP (unlike
WB/Ozon/Samokat which 403 our datacenter). Cards are Bitrix + a Vue component
(`VV23_DetailProdPage…`) that renders the nutrition/composition as flat divs in
the STATIC html — so a tag-stripped regex pass extracts everything without JS.

No EAN on the page. So rows land with barcode=NULL and are later matched to the
Layer-1 barcode base by normalized name (local pg_trgm), same pattern as magnit.

Enumeration: two product sitemaps under /upload/sitemap/msk/. fetch(limit)
walks them and yields one dict per card. Re-run = actualization (upsert by url).

Contract: fetch(limit) -> iterable of dicts for db.upsert_raw. Fields we fill:
name, brand, ingredients, kcal, protein, fat, carbs, weight, photo, and raw{}
carrying manufacturer/country/storage/shelf_life for the CatalogFoodLabelData
exporter.
"""
import re
import sys
import time

from curl_cffi import requests

SITEMAPS = [
    "https://vkusvill.ru/upload/sitemap/msk/sitemap_goods.xml",
    "https://vkusvill.ru/upload/sitemap/msk/sitemap_goods_2.xml",
]
TIMEOUT = 5          # hard cap, no infinite hangs
SLEEP = 0.4          # be gentle; vkusvill tarpits under bursts like the rest
PRODUCT_RE = re.compile(r"/goods/[^/]+-\d+/?$")   # real card, not a category


def _session():
    from sources import _util
    return _util.session()


def _num(s):
    if not s:
        return None
    s = s.replace(",", ".").strip()
    try:
        return float(s)
    except ValueError:
        return None


def _pipes(html):
    """Flatten tags to ' | ' so Vue-rendered <div>value</div><div>label</div>
    pairs become 'value | label' — the form the card actually renders."""
    t = re.sub(r"<[^>]+>", " | ", html)
    t = re.sub(r"&nbsp;", " ", t)
    t = re.sub(r"(\s*\|\s*)+", " | ", t)
    return t


def parse_card(html, url):
    """Extract one product dict from a card's HTML. Returns None if it doesn't
    look like a product (no name)."""
    def meta(prop):
        m = re.search(rf'<meta property="{prop}" content="([^"]+)"', html)
        return m.group(1).strip() if m else None

    name = meta("og:title")
    if not name:
        m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
        name = re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else None
    if not name:
        return None
    name = name.replace("\xa0", " ").replace("&nbsp;", " ")
    name = re.sub(r"\s*[–-]\s*ВкусВилл\s*$", "", name).strip()

    p = _pipes(html)
    # VkusVill uses TWO card layouts:
    #  (a) inline text: "белки 2.3 г, жиры 25 г, углеводы 3.1 г; 247 ккал"
    #  (b) table: value-before-label "281.2 | Ккал | 0.1 | Белки, г"
    # Try inline first (most cards, manufacturer-declared), fall back to table.
    # First occurrence wins (a product may list several suppliers' values).
    def inline(word):
        m = re.search(word + r"\s*([\d.,]+)\s*г", p, re.I)
        return _num(m.group(1)) if m else None

    def table(label):
        m = re.search(r"([\d.,]+)\s*\|\s*" + label, p)
        return _num(m.group(1)) if m else None

    m = re.search(r"([\d.,]+)\s*ккал", p, re.I)
    kcal = _num(m.group(1)) if m else table(r"Ккал")
    protein = inline("белки") if inline("белки") is not None else table(r"Белки")
    fat = inline("жиры") if inline("жиры") is not None else table(r"Жиры")
    carbs = inline("углеводы") if inline("углеводы") is not None else table(r"Углеводы")

    def after_label(label):
        # "Label | <maybe 'Изготовитель:'> value ;|"  -> value up to ; or |
        m = re.search(label + r"\s*\|\s*([^|]+?)\s*(?:\||$)", p)
        if not m:
            return None
        v = m.group(1).strip()
        # values often prefixed with "ИП …:" — keep the part after the last ':'
        if ":" in v:
            v = v.split(":", 1)[1].strip()
        return v.rstrip(";").strip() or None

    # состав renders as "Состав | Состав | <maker>:<composition>;"
    m = re.search(r"Состав\s*\|\s*Состав\s*\|\s*([^|]+)", p)
    ingredients = None
    if m:
        v = m.group(1).strip()
        if ":" in v:
            v = v.split(":", 1)[1]
        ingredients = v.rstrip(" ;").strip() or None

    weight = after_label("Вес/объем")
    brand = after_label("Бренд")
    country = after_label("Страна производства")
    manufacturer = after_label("Изготовитель")
    storage = after_label(r"Условия хранения[^|]*")
    shelf = after_label("Годен")

    return {
        "source_id": url,
        "barcode": None,
        "name": name,
        "brand": brand,
        "ingredients": ingredients,
        "kcal": kcal, "protein": protein, "fat": fat, "carbs": carbs,
        "weight": weight,
        "photo": meta("og:image"),
        "raw": {
            "url": url, "manufacturer": manufacturer, "country": country,
            "storage": storage, "shelf_life": shelf,
        },
    }


def _all_urls(s, limit):
    """Read every product URL from the sitemaps up front, so we know the total
    and can show real progress. Loud if a sitemap is dead."""
    urls = []
    for sm in SITEMAPS:
        print(f"[vkusvill] reading sitemap {sm.split('/')[-1]} ...",
              file=sys.stderr, flush=True)
        try:
            xml = s.get(sm).text
        except Exception as e:
            print(f"[vkusvill] sitemap DEAD ({type(e).__name__}) — skipping. "
                  f"If this is a foreign IP, vkusvill throttles it; run from a "
                  f"RU IP.", file=sys.stderr, flush=True)
            continue
        found = re.findall(r"<loc>([^<]+)</loc>", xml)
        # keep only real product cards /goods/<slug>-<id>/ — the sitemaps also
        # list category/listing pages (/goods/set-novinki/) that carry no
        # nutrition and would pollute raw_items with empty rows.
        found = [u for u in found if PRODUCT_RE.search(u)]
        print(f"[vkusvill]   -> {len(found)} products", file=sys.stderr, flush=True)
        urls += found
        if limit and len(urls) >= limit:
            break
    return urls[:limit] if limit else urls


def fetch(limit=None):
    s = _session()
    urls = _all_urls(s, limit)
    total = len(urls)
    if not total:
        print("[vkusvill] no product URLs — sitemaps unreachable. Aborting.",
              file=sys.stderr, flush=True)
        return
    print(f"[vkusvill] scraping {total} cards (5s timeout, no retry)...",
          file=sys.stderr, flush=True)
    t0, ok, dead = time.time(), 0, 0
    for i, url in enumerate(urls, 1):
        try:
            html = s.get(url).text
            d = parse_card(html, url)
        except Exception:
            d = None
        if d:
            ok += 1
            yield d
        else:
            dead += 1
        if i % 10 == 0 or i == total:
            el = time.time() - t0
            rate = i / max(el, 1e-9)
            eta = int((total - i) / max(rate, 1e-9))
            name = (d["name"][:32] if d else "-")
            print(f"\r[vkusvill] {i}/{total} | ok {ok} dead {dead} | "
                  f"{rate:.1f}/s | ETA {eta}s | {name}",
                  end="", file=sys.stderr, flush=True)
        # if the IP gets throttled, dead-in-a-row spikes — bail loudly instead
        # of grinding for an hour returning nothing
        if dead >= 20 and ok == 0:
            print(f"\n[vkusvill] 20 dead fetches, 0 ok — IP is being throttled. "
                  f"Stop and run from a RU IP / proxy.", file=sys.stderr, flush=True)
            return
        time.sleep(SLEEP)
    print(file=sys.stderr)


# --- offline self-check: synthetic card mirroring the real flat-div DOM ---
_SAMPLE = """
<meta property="og:title" content="Шарики из тапиоки клубника-питахайя">
<meta property="og:image" content="https://vkusvill.ru/img/108448.jpg">
<h1>Шарики из тапиоки</h1>
<div>Пищевая ценность на 100 грамм</div>
<div>281.2</div><div>Ккал</div>
<div>0.1</div><div>Белки, г</div>
<div>70.2</div><div>Углеводы, г</div>
<div>Вес/объем</div><div>200 г</div>
<div>Бренд</div><div>ВкусВилл</div>
<div>Страна производства</div><div>ИП Домбровская:РОССИЯ;</div>
<div>Состав</div><div>Состав</div>
<div>ИП Домбровская:крахмал тапиоковый, вода питьевая, сахар, пюре клубники;</div>
"""


# inline-format card (the common layout): КБЖУ as a free-text sentence,
# name carries the " – ВкусВилл" suffix, состав prefixed with the maker.
_SAMPLE_INLINE = """
<meta property="og:title" content="Сметана 25%, 350&nbsp;г – ВкусВилл">
<meta property="og:image" content="https://vkusvill.ru/img/52.jpg">
<div>Вес/объем</div><div>350 г</div>
<div>Бренд</div><div>ВкусВилл</div>
<div>Пищевая и энергетическая ценность в 100 г.</div>
<div>ООО "ЛЕБЕДЯНЬМОЛОКО": белки 2.3 г, жиры 25 г, углеводы 3.1 г; 247 ккал</div>
<div>Состав</div><div>Состав</div>
<div>ООО "ЛЕБЕДЯНЬМОЛОКО":сливки пастеризованные, заквасочные культуры;</div>
"""


def demo():
    d = parse_card(_SAMPLE, "https://vkusvill.ru/goods/x-108448/")
    assert d["name"].startswith("Шарики"), d["name"]
    assert d["kcal"] == 281.2, d["kcal"]
    assert d["protein"] == 0.1, d["protein"]
    assert d["carbs"] == 70.2, d["carbs"]
    assert d["weight"] == "200 г", d["weight"]
    assert d["brand"] == "ВкусВилл", d["brand"]
    assert d["raw"]["country"] == "РОССИЯ", d["raw"]["country"]
    assert "крахмал тапиоковый" in d["ingredients"], d["ingredients"]
    assert d["barcode"] is None

    e = parse_card(_SAMPLE_INLINE, "https://vkusvill.ru/goods/smetana-25-52/")
    assert e["name"] == "Сметана 25%, 350 г", e["name"]   # suffix stripped
    assert e["kcal"] == 247, e["kcal"]
    assert e["protein"] == 2.3, e["protein"]
    assert e["fat"] == 25, e["fat"]
    assert e["carbs"] == 3.1, e["carbs"]
    assert e["weight"] == "350 г", e["weight"]
    assert "сливки пастеризованные" in e["ingredients"], e["ingredients"]
    print("vkusvill demo ok")


if __name__ == "__main__":
    if "--live" in sys.argv:
        n = 0
        for d in fetch(limit=3):
            n += 1
            print(n, d["name"][:50], "| kcal", d["kcal"], "| состав",
                  (d["ingredients"] or "")[:40])
        print("fetched", n)
    else:
        demo()
