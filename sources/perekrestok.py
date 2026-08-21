"""Перекрёсток (X5) source — www.perekrestok.ru.

Flow: bootstrap a guest bearer token -> walk catalog tree -> paginate the
category feed -> pull product cards (состав, КБЖУ, photo, brand, weight, barcode).

STATUS as of 2026-08-18: BLOCKED from this host (verified live).
Every path — the homepage AND /api/customer/1.4.1.0/* (auth/token/number,
catalog/tree, catalog/feed) — sits behind the ServicePipe edge (server: nginx,
`x-sp-crid` header on every response). Behaviour observed:
  * Homepage returns 200 but is only the JS-challenge spinner: it inlines
    `spsn`/`spid` cookie seeds and loads servicepipe.tech checkjs
    (static/checkjs/.../mWHr_yLXyf.js) which must run a proof-of-work in a real
    JS engine to earn a validated cookie. Replaying spsn+spid alone -> still 403.
  * The API returns 403 with the "Проблемы со связью" block page that prints
    our datacenter IP (e.g. 5.145.252.209) — an IP-reputation block, not the
    solvable spinner. curl_cffi Chrome impersonation + SPA headers do not help;
    the TCP connection is also frequently dropped outright.
Unblocking needs ONE of:
  * a residential RU IP whitelisted by ServicePipe (drop it in proxies.txt —
    _http rotates entries and this module runs unchanged), or
  * a headless browser to execute checkjs and harvest the validated cookie.
The endpoint/card shapes below are the historical SPA API and are UNVERIFIED
(never observable past the block); adjust once a real payload is in hand.
"""
from sources import _http

API = "https://www.perekrestok.ru/api/customer/1.4.1.0"
MIN_INTERVAL = 0.5


class ServicePipeBlocked(RuntimeError):
    pass


def _guest_token(s):
    """Anonymous bearer token from the SPA bootstrap."""
    r = _http.post(s, f"{API}/auth/token/number", min_interval=MIN_INTERVAL, json={})
    _check(r)
    tok = r.json().get("token") or r.json().get("accessToken")
    if not tok:
        raise RuntimeError(f"no token in bootstrap: {r.text[:200]}")
    s.headers["Authorization"] = f"Bearer {tok}"
    return tok


def _check(r):
    if r.headers.get("x-sp-crid") or (r.status_code == 403 and "servicepipe" in r.text.lower()) \
       or "Проблемы со связью" in r.text:
        raise ServicePipeBlocked(
            f"ServicePipe block {r.status_code} crid={r.headers.get('x-sp-crid')} "
            f"— needs residential RU proxy (see proxies.txt)"
        )
    r.raise_for_status()


def _leaf_categories(s):
    r = _http.get(s, f"{API}/catalog/tree", min_interval=MIN_INTERVAL)
    _check(r)

    def walk(nodes):
        for n in nodes:
            kids = n.get("children") or []
            if kids:
                yield from walk(kids)
            else:
                yield n
    yield from walk(r.json().get("content", r.json()))


def _feed(s, category_id, page):
    r = _http.post(
        s, f"{API}/catalog/product/feed", min_interval=MIN_INTERVAL,
        json={"filter": {"category": category_id}, "page": page, "perPage": 50,
              "orderBy": "popularity", "orderDirection": "desc"},
    )
    _check(r)
    j = r.json()
    return (j.get("content") or {}).get("items", j.get("items", []))


_MACRO_KEYS = {  # nutrient label (lowercased состав/пищевая ценность) -> our field
    "калорийность": "kcal", "энергетическая": "kcal",
    "белки": "protein", "жиры": "fat", "углеводы": "carbs",
}


def _parse(p):
    """One product card -> contract dict. Best-effort over the known card shape."""
    out = {"source_id": p.get("id") or p.get("plu"),
           "name": p.get("title") or p.get("name"),
           "barcode": p.get("barcode") or p.get("ean"),
           "photo": (p.get("image") or {}).get("url") if isinstance(p.get("image"), dict) else p.get("image"),
           "extra": {"url": p.get("url"), "category": p.get("category"), "plu": p.get("plu")}}
    brand = p.get("brand")
    out["brand"] = brand.get("title") if isinstance(brand, dict) else brand

    # nutrition + состав live under properties / nutritionFacts depending on layer
    for prop in (p.get("properties") or []) + (p.get("nutritionFacts") or []):
        label = (prop.get("title") or prop.get("name") or "").lower()
        val = prop.get("value")
        if "состав" in label:
            out["ingredients"] = val
        elif "масса" in label or "вес" in label:
            out["weight"] = val
        else:
            for key, field in _MACRO_KEYS.items():
                if key in label:
                    try:
                        out[field] = float(str(val).replace(",", ".").split()[0])
                    except (ValueError, AttributeError, IndexError):
                        pass
    return {k: v for k, v in out.items() if v not in (None, "")}


def fetch(limit=None):
    s = _http.session()
    _guest_token(s)
    n = 0
    for cat in _leaf_categories(s):
        cid = cat.get("id")
        page = 1
        while True:
            items = _feed(s, cid, page)
            if not items:
                break
            for p in items:
                row = _parse(p)
                if not row.get("source_id"):
                    continue
                yield row
                n += 1
                if limit and n >= limit:
                    return
            page += 1


if __name__ == "__main__":
    # self-check: parser handles a card shape without any live network.
    card = {"id": 42, "plu": "99", "title": "Молоко 3.2%", "barcode": "4600682000129",
            "brand": {"title": "Домик"}, "image": {"url": "http://x/1.jpg"},
            "properties": [{"title": "Состав", "value": "молоко"},
                           {"title": "Калорийность", "value": "60 ккал"},
                           {"title": "Белки", "value": "2,9"}, {"title": "Масса", "value": "930 мл"}]}
    r = _parse(card)
    assert r["ingredients"] == "молоко" and r["kcal"] == 60.0 and r["protein"] == 2.9, r
    assert r["brand"] == "Домик" and r["weight"] == "930 мл", r
    print("parse ok:", r)
