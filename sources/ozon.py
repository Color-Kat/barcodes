"""Ozon — the only retailer that carries EAN + КБЖУ + состав together. But it
is captcha-walled: cold datacenter requests get 403 + challenge. So Ozon is NOT
a bulk base — it's an EAN-keyed GAP-FILL: given a barcode we already have (from
dumps/Metro/WB) that still lacks КБЖУ, look it up and enrich.

Flow per barcode:
  search  GET composer-api.bx/page/json/v2?url=/search/?text=<ean>
          -> widget tileGridDesktop -> items[].action.link (product slug)
  detail  GET .../page/json/v2?url=/product/<slug>/?layout_container=pdpPage2column&layout_page_index=2
          -> widget webCharacteristics -> characteristics[].{short,long}[].{name,values}
          -> Штрихкод / Состав / Белки / Жиры / Углеводы / Калорийность / Вес / Бренд

Needs RU-residential egress + anti-bot cookies to pass the captcha at any volume
(set BARCODES_PROXY, and expect to feed cookies for sustained use). Parsing is
solved and verified below; access is the whole cost. Use sparingly, throttled.

Out of scope by policy: reconstructions that rely on logged-in third-party
account cookies — we only use anonymous access issued to any client.
"""
import json
import os
import re
import sys
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db

API = "https://api.ozon.ru/composer-api.bx/page/json/v2?url="

_NUTR = {
    "белки": "protein", "жиры": "fat", "углеводы": "carbs",
    "калорийность": "kcal", "энергетическая ценность": "kcal",
    "пищевая ценность": "kcal",
}


def widget(page, name):
    """Return the parsed JSON of the first widgetState whose key (before '-')
    equals `name`. Ozon double-encodes: values are JSON strings."""
    for k, v in (page.get("widgetStates") or {}).items():
        if k.split("-")[0] == name:
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
    return None


def full_chars(page2):
    """Flatten page-2 webCharacteristics into {char_name: 'v1, v2'}."""
    out = {}
    wc = widget(page2, "webCharacteristics") or {}
    for sec in wc.get("characteristics", []):
        for item in (sec.get("short") or []) + (sec.get("long") or []):
            nm, vals = item.get("name"), item.get("values")
            if nm and vals:
                out[nm] = ", ".join(v.get("text", "") for v in vals)
    return out


def _num(s):
    m = re.search(r"[\d]+(?:[.,]\d+)?", str(s or ""))
    return float(m.group(0).replace(",", ".")) if m else None


def parse_chars(chars, barcode=None):
    """Map a flat characteristics dict to our row fields."""
    out = {"raw": {}}
    for name, val in chars.items():
        nl = name.strip().lower()
        if nl == "штрихкод":
            from normalize import norm_barcode
            out["barcode"] = norm_barcode(val.split(",")[0]) or barcode
        elif nl.startswith("состав"):
            out["ingredients"] = val
        elif nl in ("вес", "вес товара", "вес нетто", "масса нетто"):
            out["weight"] = val
        elif nl in ("бренд", "brand"):
            out["brand"] = val
        else:
            for key, field in _NUTR.items():
                if key in nl and out.get(field) is None:
                    out[field] = _num(val)
                    break
            else:
                out["raw"][name] = val
    if barcode and not out.get("barcode"):
        out["barcode"] = barcode
    return out


def lookup(s, ean):
    """barcode -> enriched dict (or None). Two requests: search, then page-2."""
    sr = s.get(API + quote(f"/search/?text={ean}/"))
    if sr.status_code != 200:
        return None
    grid = widget(sr.json(), "tileGridDesktop") or widget(sr.json(), "searchResultsV2")
    slug = None
    for it in ((grid or {}).get("items") or []):
        link = (it.get("action") or {}).get("link") or it.get("link")
        if link and "/product/" in link:
            slug = link.split("/product/")[1].strip("/").split("?")[0]
            break
    if not slug:
        return None
    p2 = s.get(API + quote(f"/product/{slug}/?layout_container=pdpPage2column&layout_page_index=2"))
    if p2.status_code != 200:
        return None
    row = parse_chars(full_chars(p2.json()), barcode=ean)
    row["source_id"] = slug
    hdr = widget(p2.json(), "webProductHeading") or {}
    if hdr.get("title"):
        row["name"] = hdr["title"]
    return {k: v for k, v in row.items() if v not in (None, "", {})}


def enrich(con, limit=None):
    """Gap-fill: for RU products with a barcode but no КБЖУ, look up Ozon."""
    from sources import _util
    s = _util.session()
    rows = con.execute(
        "SELECT barcode, name FROM products WHERE country='RU' AND kcal IS NULL "
        "AND barcode IS NOT NULL %s" % (f"LIMIT {int(limit)}" if limit else "")
    ).fetchall()
    got = []
    for bc, _name in rows:
        try:
            d = lookup(s, bc)
        except Exception:
            d = None
        if d and (d.get("kcal") or d.get("ingredients")):
            got.append(d)
    return db.upsert_raw(con, "ozon", got), len(rows)


# fetch() kept for the uniform contract, but Ozon can't be bulk-enumerated cold.
def fetch(limit=None):
    print("[ozon] not a bulk source — captcha-walled. Use `enrich` (EAN gap-fill) "
          "behind a RU-residential proxy instead.", file=sys.stderr, flush=True)
    return iter(())


# --- self-check on the captured widgetStates shape ---
_PAGE2 = {"widgetStates": {
    "webCharacteristics-3113922-default-1": json.dumps({"characteristics": [
        {"short": [
            {"name": "Штрихкод", "values": [{"text": "4607025392408"}]},
            {"name": "Бренд", "values": [{"text": "Тест"}]},
            {"name": "Вес", "values": [{"text": "250 г"}]},
        ], "long": [
            {"name": "Состав", "values": [{"text": "сахар, какао"}]},
            {"name": "Калорийность", "values": [{"text": "540 ккал"}]},
            {"name": "Белки", "values": [{"text": "6 г"}]},
            {"name": "Жиры", "values": [{"text": "31 г"}]},
            {"name": "Углеводы", "values": [{"text": "58 г"}]},
        ]}]}),
    "webProductHeading-1-default-1": json.dumps({"title": "Шоколад тёмный"}),
}}


def demo():
    ch = full_chars(_PAGE2)
    assert ch["Штрихкод"] == "4607025392408", ch
    d = parse_chars(ch)
    assert d["barcode"] == "4607025392408", d.get("barcode")
    assert d["ingredients"] == "сахар, какао"
    assert d["kcal"] == 540.0 and d["protein"] == 6.0 and d["fat"] == 31.0 and d["carbs"] == 58.0
    assert d["brand"] == "Тест" and d["weight"] == "250 г"
    print("ozon demo ok")


if __name__ == "__main__":
    demo()
