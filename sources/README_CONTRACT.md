# Source module contract

Each `sources/<name>.py` exposes:

    def fetch(limit: int | None) -> Iterable[dict]

Yield dicts (generator preferred, so re-runs stream). Keys:

    source_id     REQUIRED, stable unique id within this source (str/int)
    barcode       EAN/GTIN string (any format; core normalizes+validates)
    name, brand, ingredients, weight, photo   strings
    kcal, protein, fat, carbs                 floats, per 100g
    extra         dict of anything else (category, url, vitamins, sugar,
                  sodium, per-portion vals, etc.) — stored as JSON

Only what you have; omit the rest. Re-running fetch() must upsert (same
source_id → refresh), so it doubles as the actualization mode. Respect
--limit (stop after N products) for cheap test runs.

## HTTP

Use the shared helper (Chrome TLS impersonation + rate limit + proxy rotation):

    from sources import _http
    s = _http.session()                       # or _http.session({"Authorization": ...})
    r = _http.get(s, url, min_interval=0.5)    # rate-limited, retried
    r = _http.post(s, url, json={...})

Never hammer: keep min_interval >= 0.4s per host.
Env: outbound network needs dangerouslyDisableSandbox on Bash calls.
Python: /home/colorkat/projects/barcodes2/.venv/bin/python
