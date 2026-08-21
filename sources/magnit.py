"""Магнит доставка — dostavka.magnit.ru (name -> details layer).

Data access (reverse-engineered 2026-08):
  * The delivery catalog is a Nuxt SSR app. Every product page
    /product/<id>-<slug> is server-rendered with the full card inline:
    name (h1), КБЖУ (data-test-id nutrition-fact-*), состав + описание
    (v-marked-text), characteristics (Бренд/Производитель/Вес/Артикул…),
    photo (images-foodtech.magnit.ru … /goods/<id>/image/…) and price.
    No store, cookie or bearer token is needed for SSR GETs.
  * Enumeration comes free from the product sitemap
    /__sitemap__/products.xml (~20k product URLs), so we skip the
    JWT-gated /webgate/v2/goods/* JSON API entirely.

Barcode (штрихкод/EAN) is NOT exposed on Magnit's delivery cards — the
characteristics table carries Артикул (internal id) but no GTIN. So this
source is a name/КБЖУ/состав/photo layer; `barcode` is populated only on
the rare card that lists one (scanned defensively, usually None).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sources import _util

BASE = "https://dostavka.magnit.ru"
SITEMAP = f"{BASE}/__sitemap__/products.xml"

_NUTR = {"ккал": "kcal", "белки": "protein", "жиры": "fat", "углеводы": "carbs"}


def _strip(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>|<!--.*?-->", "", html, flags=re.S)).strip()


def _test(html, test_id):
    """Text of every element carrying data-test-id=test_id, document order."""
    return [_strip(m.group(1)) for m in
            re.finditer(r'data-test-id="' + test_id + r'"[^>]*>(.*?)</', html, re.S)]


def _num(s):
    m = re.search(r"[\d]+(?:[.,]\d+)?", s or "")
    return float(m.group(0).replace(",", ".")) if m else None


def _params(html):
    """Characteristics list -> {name: value}. Names/values interleave in order."""
    names = _test(html, "v-product-details-parameters-list-item-name")
    vals = _test(html, "v-product-details-parameters-list-item-value")
    return dict(zip(names, vals))


def parse(html, url=""):
    pid = re.search(r"/product/(\d+)", url)
    pid = pid.group(1) if pid else None

    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    name = _strip(h1.group(1)) if h1 else None

    out = {"source_id": pid, "name": name, "extra": {"url": url}}

    # КБЖУ (per 100g)
    for label, val in zip(_test(html, "v-product-details-nutrition-fact-name"),
                          _test(html, "v-product-details-nutrition-fact-value")):
        field = _NUTR.get(label.lower())
        if field:
            out[field] = _num(val)

    # состав / описание live in v-marked-text blocks, one per tab panel.
    for part in re.split(
            r'data-test-id="product-detail-parameters-tab-context-name"[^>]*>', html)[1:]:
        label = _strip(part.split("</span>")[0]).lower()
        mt = re.search(r'data-test-id="v-marked-text"[^>]*>(.*?)</div>', part, re.S)
        if not mt:
            continue
        val = _strip(mt.group(1))
        if label.startswith("состав"):
            out["ingredients"] = val
        elif label.startswith("описание"):
            out["extra"]["description"] = val[:2000]

    # characteristics
    params = _params(html)
    for k, v in params.items():
        kl = k.lower()
        if kl == "бренд":
            out["brand"] = v
        elif "вес" in kl or "масса" in kl or "объ" in kl:
            unit = re.sub(r"^[^,]*,?\s*", "", k) or "кг"
            out["weight"] = f"{v} {unit}".strip()
        elif "штрих" in kl or kl in ("ean", "gtin"):
            out["barcode"] = v
        elif kl == "производитель":
            out["extra"]["manufacturer"] = v
        elif kl == "артикул":
            out["extra"]["article"] = v
        else:
            out["extra"][k] = v

    # photo — first image inside the product gallery block. Its S3 path is
    # sometimes /goods/<id>/image/… and sometimes legacy /catalog/uf/…, so key
    # off the gallery marker, not the id.
    flat = html.replace("\\u002F", "/")
    g = flat.find("v-product-detail-gallery")
    if g != -1:
        m = re.search(r"https://(?:images-foodtech|img-dostavka)\.magnit\.ru/[^\"'\\ ]+",
                      flat[g:g + 4000])
        if m:
            out["photo"] = m.group(0)
    if not out.get("photo") and pid:
        m = re.search(r"https:[^\"'\\ ]*?/goods/" + pid + r"/image/[^\"'\\ ]+", flat)
        if m:
            out["photo"] = m.group(0)

    price = _test(html, "v-product-detail-price-current")
    if price:
        out["extra"]["price"] = _num(price[0])

    return {k: v for k, v in out.items() if v not in (None, "", {})}


def fetch(limit=None):
    s = _util.session({"Accept": "text/html", "Referer": BASE + "/"})
    try:
        r = s.get(SITEMAP)
        urls = re.findall(r"<loc>(https?://[^<]+/product/[^<]+)</loc>", r.text)
    except Exception:
        urls = []
    urls = [u.replace("https://magnit.ru", BASE) for u in urls]
    if limit:
        urls = urls[:limit]

    def fetch_one(url):
        r = s.get(url)
        if r.status_code != 200:
            return None
        row = parse(r.text, url)
        if not row.get("source_id") or not row.get("name"):
            return None
        return row

    yield from _util.scrape_urls("magnit", urls, fetch_one)


if __name__ == "__main__":
    # self-check: parser is pure — feed it a saved page.
    import sys
    html = open(sys.argv[1]).read() if len(sys.argv) > 1 else ""
    if html:
        row = parse(html, "https://dostavka.magnit.ru/product/1000237597-x")
        assert row["source_id"] == "1000237597", row
        assert row["name"] and row["kcal"] and row["ingredients"], row
        print("parse ok:", {k: row[k] for k in ("name", "kcal", "protein", "brand", "weight")})
