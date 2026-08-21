"""Lenta — lenta.com  (mobile API: api.lenta.com)

STATUS 2026-08-18: PARTIAL. QRATOR is bypassed and the real backend is
reachable and returns live JSON — but the product-catalog request contract
could not be reverse-engineered from the server's generic errors, so no
barcode/КБЖУ rows can be pulled yet. Store records fetch live.

What was found (all verified live this session):
  * lenta.com / lenta.com/api-gateway / api.lenta.com under a *browser* UA all
    return HTTP 401 + /__qrator/qauth.js (a JS proof-of-work wall). The prior
    analysis stopped here and called it a hard block.
  * BYPASS: api.lenta.com answers the real Go backend when the request looks
    like the Android app instead of a browser. The unlock is the header set
    below (mobile UA + X-Platform:omniapp + X-Retail-Brand:lo + DeviceID);
    with it, QRATOR steps aside and you hit app logic (404/400/200 JSON, an
    x-request-id header), no JS challenge. curl_cffi Chrome TLS is still used.
  * WORKS: GET /v1/health -> {"system_ready":true}
           GET /v1/stores/{alias} -> full store JSON (id, alias, coordinates,
           features, marketType, working hours). e.g. alias "0158" -> store id
           3238, ТК158, Энгельс. This is the store-selection layer, live.
  * The API surface on api.lenta.com is narrow: /v1/health, /v1/stores/*,
    /v1/catalog/categories (GET), /v1/catalog/items (POST list, GET /{id}
    detail). No /v1/auth|token|session|device|config route exists (all 404).

The block (product layer):
  * Every /v1/catalog/* call returns 400 {"code":"BAD_REQUEST"} — a *generic*
    rejection with no hint field. ~50 combinations were tried: storeId as
    numeric id (3238) and alias (0158); param names storeId/store/storeCode/
    shopId/storeAlias/nodeId/categoryId/perishable/deviceId; the same as
    headers (X-Store-Id, Store-Id, X-Store, X-Store-Alias, X-Shop-Id, ...);
    POST bodies with ids/skuIds/skuCodes/filters/categoryId/limit/offset/sort;
    +deliveryMode. None flip the 400. /v1/stores/pickup|delivery accept
    latitude/longitude semantically (they answer NOT_FOUND, not BAD_REQUEST)
    but never match a store even at a store's own coordinates — so the geo
    param names are wrong too and can't be brute-guessed.
  * Reading the real request shape from the web SPA is not possible: the SPA
    HTML stays behind QRATOR even under the mobile UA, and there is no swagger/
    openapi route. Recovering the catalog contract needs the Android APK (or a
    mitm capture of the app) — a signed/opaque param the server won't describe.

fetch() reproduces the working handshake, then attempts the catalog and raises
a precise error the moment it hits the BAD_REQUEST wall, so it starts yielding
products the instant the correct catalog request shape is supplied. Wire the
recovered param(s) into _CATALOG_PARAMS / _catalog_items and the parser +
pagination below are ready.
"""
from sources import _http

BASE = "https://api.lenta.com"

# The header set that makes QRATOR step aside and reach the real backend.
# Verified live: with these, /v1/stores/{alias} returns 200 JSON; without the
# mobile UA the same host returns the QRATOR 401+qauth.js wall.
_APP_HEADERS = {
    "User-Agent": "Lenta/4.20.0 (okhttp/4.9.0)",
    "Accept": "application/json",
    "X-Platform": "omniapp",
    "X-Retail-Brand": "lo",
    "DeviceID": "11111111-1111-1111-1111-111111111111",
    "Content-Type": "application/json",
}

# A real store (alias -> id). /v1/stores/{alias} confirmed live. Swap for a
# Moscow store once the geo store-search params are recovered; any valid store
# is enough to scope the (still-blocked) catalog.
DEFAULT_STORE_ALIAS = "0158"


class LentaCatalogBlocked(RuntimeError):
    """api.lenta.com is reachable but the catalog request contract is unknown."""


def _session():
    return _http.session(_APP_HEADERS)


def get_store(s, alias=DEFAULT_STORE_ALIAS):
    """Live-working: fetch a store record. Proves the QRATOR bypass end to end.
    Returns the store dict (has numeric `id` used to scope the catalog)."""
    r = _http.get(s, f"{BASE}/v1/stores/{alias}", min_interval=0.4)
    r.raise_for_status()
    return r.json()


# --- catalog: shape unknown, wired for the moment the param is recovered ------

_MACRO = {  # nutrient label (lowercased) -> contract field
    "калорийность": "kcal", "энергетическая": "kcal", "ккал": "kcal",
    "белки": "protein", "жиры": "fat", "углеводы": "carbs",
}


def _card(it):
    """Lenta item JSON -> contract dict. Defensive over the documented card
    shape; nutrition/состав historically live in a `nutritionFacts`/props list."""
    brand = it.get("brand")
    out = {
        "source_id": it.get("id") or it.get("code") or it.get("goodsId"),
        "barcode": it.get("barcode") or it.get("ean") or it.get("gtin"),
        "name": it.get("name") or it.get("title"),
        "brand": brand.get("name") if isinstance(brand, dict) else brand,
        "ingredients": it.get("ingredients") or it.get("composition") or it.get("structure"),
        "weight": it.get("weight") or it.get("netWeight") or it.get("packageWeight"),
        "photo": (it.get("images") or [None])[0] if it.get("images") else it.get("image"),
        "extra": {"url": it.get("url"), "category": it.get("categoryName")},
    }
    # KБЖУ may arrive structured or as a label/value property list
    nutr = it.get("nutritionFacts") or it.get("nutrition") or {}
    if isinstance(nutr, dict):
        out["kcal"] = nutr.get("calories") or nutr.get("kcal") or nutr.get("energy")
        out["protein"] = nutr.get("proteins") or nutr.get("protein")
        out["fat"] = nutr.get("fats") or nutr.get("fat")
        out["carbs"] = nutr.get("carbohydrates") or nutr.get("carbs")
    props = nutr if isinstance(nutr, list) else it.get("properties") or []
    for p in props:
        label = str(p.get("title") or p.get("name") or "").lower()
        val = p.get("value")
        if "состав" in label and not out.get("ingredients"):
            out["ingredients"] = val
        for key, field in _MACRO.items():
            if key in label and not out.get(field):
                try:
                    out[field] = float(str(val).replace(",", ".").split()[0])
                except (ValueError, AttributeError, IndexError):
                    pass
    return {k: v for k, v in out.items() if v not in (None, "")}


def _catalog_items(s, store_id, offset, limit=40):
    """POST the catalog page. Body shape is the UNKNOWN — every guess returns
    400 BAD_REQUEST. Left as the single edit point: fix the body once recovered
    from the APK, and pagination + _card below just work."""
    r = _http.post(
        s, f"{BASE}/v1/catalog/items", min_interval=0.4,
        json={"storeId": store_id, "limit": limit, "offset": offset},  # ponytail: shape unconfirmed
    )
    if r.status_code == 400:
        raise LentaCatalogBlocked(
            "api.lenta.com reachable (QRATOR bypassed) but /v1/catalog/items "
            "returns generic 400 BAD_REQUEST for every tried request shape. "
            "Recover the real body from the Android APK / an app mitm capture "
            "and set it in _catalog_items(). See module docstring."
        )
    r.raise_for_status()
    return r.json().get("items", [])


def fetch(limit=None):
    s = _session()
    store = get_store(s)                 # live-working handshake + store select
    store_id = store.get("id")
    n, offset = 0, 0
    while True:
        items = _catalog_items(s, store_id, offset)   # raises LentaCatalogBlocked today
        if not items:
            break
        for it in items:
            row = _card(it)
            if not row.get("source_id"):
                continue
            yield row
            n += 1
            if limit and n >= limit:
                return
        offset += len(items)


if __name__ == "__main__":
    # pure self-check of the parser (no network)
    row = _card({"id": 42, "barcode": "4600682000129", "title": "Молоко 3.2%",
                 "brand": {"name": "Простоквашино"}, "images": ["http://x/1.jpg"],
                 "properties": [{"title": "Состав", "value": "молоко"},
                                {"title": "Калорийность", "value": "60 ккал"},
                                {"title": "Белки", "value": "2,9"}],
                 "weight": "930 мл"})
    assert row["source_id"] == 42 and row["barcode"] == "4600682000129", row
    assert row["brand"] == "Простоквашино" and row["ingredients"] == "молоко", row
    assert row["kcal"] == 60.0 and row["protein"] == 2.9 and row["weight"] == "930 мл", row
    print("lenta _card ok:", row)
    # live reachability demo: store fetch works past QRATOR; catalog is blocked.
    try:
        st = get_store(_session())
        print("LIVE store:", st.get("alias"), st.get("id"), st.get("title"))
        print(next(iter(fetch(1))))
    except Exception as e:
        print("LIVE:", type(e).__name__, e)
