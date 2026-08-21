"""Национальный каталог товаров (ЦРПТ / Честный ЗНАК) — национальный-каталог.рф

Public, server-side-rendered product cards. NO auth needed. Each card renders
the full GTIN registry record in HTML: barcode, name, brand (Товарный знак),
состав, КБЖУ (Белки/Жиры/Углеводы/Энергетическая ценность per 100g), weight,
photo, manufacturer codes (ОКПД2/ТНВЭД/ГОСТ). We parse the HTML directly.

The API host (апи.национальный-каталог.рф / api.nationalcatalog.ru) needs an
apikey issued only through Честный ЗНАК with an ЭЦП, so we ignore it and scrape
the free public pages instead.

URL shapes (discovered live):
  /                                 -> category slugs + some product links
  /<category-slug>/                 -> product listing, paginated ?page=N
  /product/<gtin>-ru-<slug>         -> full card (parsed by _parse)
  og:image / /s3/orig/<hash>.jpg    -> product photo

RATE LIMIT: the site aggressively throttles datacenter IPs — after ~6 quick
requests it stops answering (curl 28 timeout) for several minutes. We keep
min_interval high (SLEEP) and it still may get walled from a datacenter IP; a
residential RU IP / proxies.txt clears it. See STATUS in the module report.
"""
import re

from sources import _http

BASE = "https://национальный-каталог.рф"           # human/display URLs (stored)
REQ = "https://xn--80apaohbc3aw9e.xn--p1ai"        # punycode: latin-1 safe for curl/headers
SLEEP = 1.5  # polite: this host bans fast datacenter traffic

# Food umbrella categories (have состав + КБЖУ). Others still carry barcode+name.
FOOD_CATEGORIES = [
    "prodovolstvennye-tovary",
    "myaso-i-myasnaya-produkciya",
    "moloko-i-molochnaya-produkciya",
    "ryba-i-rybnaya-produkciya",
    "napitki",
    "konditerskie-izdeliya",
    "hlebobulochnye-izdeliya",
]

_KCAL = "Энергетическая ценность, ккал, Точное значение"
_LABELS = {
    "brand": "Товарный знак",
    "protein": "Белки, количество, Точное значение",
    "fat": "Жиры, количество, Точное значение",
    "carbs": "Углеводы, количество, Точное значение",
}


def _txt(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html)).strip()


def _num(v):
    if v is None:
        return None
    m = re.search(r"-?\d+(?:[.,]\d+)?", v)
    return float(m.group(0).replace(",", ".")) if m else None


def _parse(t, url=None):
    """Parse one product-card HTML -> contract dict. Pure; unit-tested offline."""
    # all <th>label</th><td>value</td> spec pairs
    kv = {}
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S):
        cells = [_txt(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row, re.S)]
        cells = [c for c in cells if c]
        if len(cells) >= 2 and cells[0] not in kv:
            kv[cells[0]] = cells[1]

    bc = re.search(r"Штрихкод:\s*([0-9]+)", t)
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", t, re.S)
    name = _txt(h1.group(1)) if h1 else kv.get("Полное наименование товара")

    comp = kv.get("Состав") or ""
    comp = re.sub(r"^\s*Состав:\s*", "", comp).strip() or None

    # photo: prefer full-res s3/orig, else og:image
    orig = re.search(r"(https://[^\"' ]+/s3/orig/[^\"' ]+)", t)
    og = re.search(r'og:image"[^>]*content="([^"]+)"', t) or \
        re.search(r'content="([^"]+)"[^>]*property="og:image"', t)
    photo = orig.group(1) if orig else (og.group(1) if og else None)

    # weight: fixed net weight if present, else variable-weight upper bound
    weight = (kv.get("Вес нетто") or kv.get("Масса нетто") or kv.get("Объём")
              or kv.get("Диапазон веса, до, кг"))

    mapped = {"Штрихкод", "Состав", "Полное наименование товара", _KCAL,
              *_LABELS.values()}
    extra = {"url": url, "category": kv.get("Категория продукции")}
    extra.update({k: v for k, v in kv.items() if k not in mapped})

    return {
        "source_id": (bc.group(1) if bc else url),
        "barcode": bc.group(1) if bc else None,
        "name": name,
        "brand": kv.get(_LABELS["brand"]),
        "ingredients": comp,
        "kcal": _num(kv.get(_KCAL)),
        "protein": _num(kv.get(_LABELS["protein"])),
        "fat": _num(kv.get(_LABELS["fat"])),
        "carbs": _num(kv.get(_LABELS["carbs"])),
        "weight": weight,
        "photo": photo,
        "extra": extra,
    }


def _product_links(html):
    return list(dict.fromkeys(re.findall(r"/product/[A-Za-z0-9\-]+", html)))


def _categories(s):
    """Discover category slugs from homepage; fall back to the food list."""
    try:
        t = _http.get(s, BASE + "/", min_interval=SLEEP).text
        slugs = re.findall(r'href="/([a-z0-9-]+)/"', t)
        # prioritize known food slugs, then whatever else the homepage lists
        seen, ordered = set(), []
        for sl in FOOD_CATEGORIES + slugs:
            if sl and sl not in seen:
                seen.add(sl)
                ordered.append(sl)
        return ordered
    except Exception:
        return list(FOOD_CATEGORIES)


def fetch(limit=None):
    s = _http.session({"Accept": "text/html", "Referer": REQ + "/"})
    n = 0
    seen = set()
    for slug in _categories(s):
        page = 1
        empty_streak = 0
        while True:
            url = f"{BASE}/{slug}/?page={page}"
            try:
                r = _http.get(s, url, min_interval=SLEEP)
            except Exception:
                break
            if r.status_code != 200:
                break
            links = _product_links(r.text)
            fresh = [l for l in links if l not in seen]
            if not fresh:
                empty_streak += 1
                if empty_streak >= 2 or page > 200:
                    break
                page += 1
                continue
            empty_streak = 0
            for link in fresh:
                seen.add(link)
                try:
                    pr = _http.get(s, BASE + link, min_interval=SLEEP)
                except Exception:
                    continue
                if pr.status_code != 200:
                    continue
                row = _parse(pr.text, url=BASE + link)
                if not row.get("barcode"):
                    continue
                yield row
                n += 1
                if limit and n >= limit:
                    return
            page += 1


if __name__ == "__main__":
    import os
    here = os.path.dirname(__file__)
    sample = os.path.join(here, "..", "sample_product.html")
    if os.path.exists(sample):
        row = _parse(open(sample, encoding="utf-8").read(), url="/product/test")
        assert row["barcode"] == "4680115889439", row["barcode"]
        assert "Сосиски" in row["name"], row["name"]
        assert row["brand"] == "Стародворье", row["brand"]
        assert row["ingredients"] and "куриное" in row["ingredients"]
        assert row["protein"] == 12 and row["fat"] == 14 and row["carbs"] == 0
        assert row["kcal"] == 170, row["kcal"]
        assert row["photo"] and row["photo"].endswith(".jpg")
        print("parse ok:", row["name"], row["kcal"], "kcal")
    else:
        print("no sample_product.html; skipping offline parse test")
    # live probe (may hit the datacenter-IP wall):
    try:
        print(next(iter(fetch(1))))
    except Exception as e:
        print("LIVE:", repr(e)[:120])
