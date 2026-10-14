"""Shared plumbing for the retailer scrapers (auchan.py, globus.py, fixprice.py). Stdlib only.

Each scraper has two stages, like rskrf.py: fetch stores raw answers in data/<name>.db so the
parser can be fixed and re-run without touching the site; build_db.py calls the scraper's rows().

    export HTTPS_PROXY=http://172.21.80.1:10809   # WSL: direct connections to Russian hosts hang
    python3 <scraper>.py [--limit N]   # fetch what is not cached yet, resumable
    python3 <scraper>.py --stats       # parse the cache, print field coverage
    python3 <scraper>.py --test        # parser self-check
"""
import gzip
import http.client
import json
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
FAIL_LIMIT = 10
# The base holds food and cosmetics only. Shops file paper goods and tools under "hygiene" and
# "beauty"; they have a «Состав» too (cellulose, plastic), so they are recognised by name.
NOT_OURS = re.compile(
    r"прокладк|тампон|подгузник|пел[её]нк|туалетн\w+ бумаг|бумажн\w+ (полотен|плат|салфет)|ватн\w+ (диск|палоч)|паффы|спонж"
    r"|станок|станки|бритв(а|ы|енн)|кассет\w* для брит|зубн\w+ щ[её]тк|зубочист|зубн\w+ нит|презерватив|расч[её]ск|мочалк"
    r"|стиральн|кист[ьи] для|пилк\w+ для|ножниц|накладн\w+ (ногт|ресниц)|бигуди|заколк|резинк\w+ для волос|пластыр", re.I)
ERRORS = (OSError, http.client.HTTPException, ValueError, KeyError, TypeError)


def request(url, data=None, tries=3):
    """(body, response headers). `data` (a dict) makes it a JSON POST. Body is None on 404/410.

    Raises OSError after `tries` timeouts, resets or other HTTP errors.
    """
    headers = {"User-Agent": UA, "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
               "Accept-Language": "ru-RU,ru;q=0.9", "Accept-Encoding": "gzip"}
    body = None
    if data is not None:
        body, headers["Content-Type"] = json.dumps(data).encode(), "application/json"
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=headers), timeout=30) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                return raw.decode("utf-8", "replace"), r.headers
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                return None, e.headers
            err = e
        except (OSError, http.client.HTTPException) as e:
            err = OSError(repr(e))
        time.sleep(5 * (attempt + 1))
    raise err


def get(url, data=None):
    return request(url, data)[0]


class Cache:
    """data/<name>.db: key -> zlib(text). A key stored with None is a page that does not exist."""

    def __init__(self, name):
        path = os.path.join(HERE, "data", name + ".db")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.con = sqlite3.connect(path, timeout=120)
        self.con.execute("PRAGMA journal_mode=WAL")  # --stats and build_db.py read while the fetcher writes
        self.con.execute("CREATE TABLE IF NOT EXISTS pages (key TEXT PRIMARY KEY, body BLOB, fetched_at TEXT) WITHOUT ROWID")

    def keys(self):
        return {k for (k,) in self.con.execute("SELECT key FROM pages")}

    def put(self, key, text):
        self.con.execute("INSERT OR REPLACE INTO pages VALUES (?,?,?)", (
            key, zlib.compress(text.encode()) if text is not None else None, time.strftime("%Y-%m-%dT%H:%M:%S")))

    def get(self, key):
        row = self.con.execute("SELECT body FROM pages WHERE key = ?", (key,)).fetchone()
        return zlib.decompress(row[0]).decode() if row and row[0] else None

    def items(self, prefix=""):
        for key, body in self.con.execute("SELECT key, body FROM pages WHERE body IS NOT NULL AND key LIKE ?", (prefix + "%",)):
            yield key, zlib.decompress(body).decode()


def crawl(cache, todo, fetch_one, sleep=0.5):
    """Call fetch_one(key) -> text (or None for a page that is gone) for every key and cache it.

    Stops after FAIL_LIMIT errors in a row: a ban or a dead proxy should end the run, not loop.
    A failed key is not stored, so the next run asks again.
    """
    print(f"to fetch {len(todo)}", flush=True)
    fails = 0
    for i, key in enumerate(todo, 1):
        try:
            text = fetch_one(key)
        except ERRORS as e:
            fails += 1
            print(f"{key}: {e!r} ({fails} in a row)", flush=True)
            if fails >= FAIL_LIMIT:
                cache.con.commit()
                sys.exit(f"{FAIL_LIMIT} failures in a row, stopping. Nothing is lost, rerun later to continue.")
            time.sleep(30 * fails)
            continue
        fails = 0
        cache.put(key, text)
        if i % 20 == 0 or i == len(todo):
            cache.con.commit()
            print(f"{i}/{len(todo)}", flush=True)
        time.sleep(sleep)
    cache.con.commit()


def listings(cache, categories, fetch_page, page_count, first_only=False):
    """Cache every listing page of every category under list:<category>:<page>; return (category, text) pairs.

    fetch_page(category, page) -> text; page_count(text of page 1) -> number of pages.
    Cached pages are never re-asked: delete the list:* rows to rediscover the catalogue.
    """
    def one(key):
        return fetch_page(*key.split(":")[1:])

    have = cache.keys()
    crawl(cache, [k for k in (f"list:{c}:1" for c in categories) if k not in have], one)
    rest = []
    for c in categories:
        first = None if first_only else cache.get(f"list:{c}:1")
        if first:
            rest += [f"list:{c}:{p}" for p in range(2, page_count(first) + 1)]
    crawl(cache, [k for k in rest if k not in have], one)
    wanted = set(categories)
    return [(key.split(":")[1], text) for key, text in cache.items("list:") if key.split(":")[1] in wanted]


def num(value):
    """Leading number of '3,2', '18.9 (в творожной основе - 20)', 45; None when there is none."""
    if value is None or isinstance(value, bool):
        return None
    head = str(value).strip().replace(",", ".").split(" ")[0].split("(")[0]
    try:
        return float(head)
    except ValueError:
        return None


def nutrition(kcal, protein, fat, carbs):
    """The four per-100 g columns. All zeros is how shops store "not filled", so it becomes unknown.

    ponytail: this also blanks water and salt, whose real values are all zeros.
    """
    values = [num(v) for v in (kcal, protein, fat, carbs)]
    return dict(zip(("kcal", "protein", "fat", "carbs"), values if any(values) else [None] * 4))


def coverage(rows):
    rows = list(rows)
    print(f"rows for barcodes.db {len(rows)} ({len({r['barcode'] for r in rows})} distinct barcodes)")
    for key in ("name", "brand", "category", "quantity", "ingredients", "kcal", "protein", "fat", "carbs", "photo"):
        print(f"  {key:12} {sum(r.get(key) is not None for r in rows)}")


def main(fetch, rows, test):
    arg = sys.argv[1:]
    if "--test" in arg:
        test()
    elif "--stats" in arg:
        coverage(rows())
    else:
        fetch(int(arg[arg.index("--limit") + 1]) if "--limit" in arg else None)
        coverage(rows())


if __name__ == "__main__":
    assert (num("3,2"), num("18.9 (в творожной основе - 20)"), num(45), num("нет"), num(None)) == (3.2, 18.9, 45, None, None)
    assert all(NOT_OURS.search(s) for s in ("Прокладки Always", "Зубная щётка", "Станок бритвенный", "Ватные диски"))
    assert not any(NOT_OURS.search(s) for s in ("Жевательная резинка", "Сахарная вата", "Зубная паста", "Крем для бритья", "Шампунь"))
    assert nutrition("0", 0, None, "0")["kcal"] is None and nutrition("64", "3", "3,2", None) == {
        "kcal": 64, "protein": 3, "fat": 3.2, "carbs": None}
    print("scrape ok")
