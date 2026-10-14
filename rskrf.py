"""rskrf.ru (Роскачество) product cards -> data/rskrf.db. Stdlib only.

    export HTTPS_PROXY=http://172.21.80.1:10809   # WSL: direct connections to rskrf.ru hang
    python3 rskrf.py                # fetch every card not fetched yet (~14.5k, ~2.5 h), resumable
    python3 rskrf.py --limit 50     # cheap test run
    python3 rskrf.py --stats        # parse what is cached, print field coverage
    python3 rskrf.py --test         # parser self-check on cached cards

Two stages. Fetch stores the trimmed card HTML (zlib) in data/rskrf.db, one row per URL, so the
parser can be fixed and re-run without touching the site. build_db.py calls rows() to load the
parsed cards into barcodes.db as provider `rskrf`.

Cards are static Bitrix HTML: a list of caption/value pairs plus rating, pros and cons. There is
no nutrition field; КБЖУ is regexed out of free text where the label was retyped (~20% of food).
"""
import html as htmllib
import json
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
import zlib

from normalize import norm_barcode

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "data", "rskrf.db")
BASE = "https://rskrf.ru"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
SLEEP = 0.5
GOODS_RE = re.compile(r'href="(/goods/[^"#?/]+/)"')


def get(url, tries=3):
    """Body as str, or None on 404/410. Raises after `tries` failures of any other kind."""
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                return None
            err = e
        except OSError as e:  # timeouts, resets, URLError
            err = e
        time.sleep(5 * (attempt + 1))
    raise err


def trim(page):
    """Keep og:image + breadcrumbs + the card itself; drops ~95% of the page (menus, other goods)."""
    og = re.search(r'<meta property="og:image"[^>]*>', page)
    a = page.find("BreadcrumbList")
    a = page.rfind("<script", 0, a) if a >= 0 else page.find("product__head")
    b = page.find("Другие товары", a)
    return (og.group(0) if og else "") + page[max(a, 0):b if b >= 0 else a + 200_000]


def connect():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    con = sqlite3.connect(DB, timeout=120)
    con.execute("PRAGMA journal_mode=WAL")  # --stats and build_db.py read while the fetcher writes
    con.execute("CREATE TABLE IF NOT EXISTS pages (url TEXT PRIMARY KEY, html BLOB, fetched_at TEXT) WITHOUT ROWID")
    return con


def discover():
    """Card URLs from the sitemap. Walking all 335 /ratings/ pages found no card the sitemap lacks."""
    urls = set()
    for sm in re.findall(r"<loc>([^<]+)", get(f"{BASE}/sitemap_index.xml") or ""):
        urls.update(re.findall(r"<loc>(https://rskrf\.ru/goods/[^/<]+/)<", get(sm) or ""))
    return urls


def fetch(limit=None):
    con = connect()
    done = {u for (u,) in con.execute("SELECT url FROM pages")}
    todo = sorted(discover() - done)[:limit]
    print(f"cached {len(done)}, to fetch {len(todo)}", flush=True)
    fails = 0
    for i, url in enumerate(todo, 1):
        try:
            page = get(url)
        except OSError as e:  # one bad page must not end a 14k-page run; ten in a row mean a ban or no network
            fails += 1
            print(f"{url}: {e!r} ({fails} in a row)", flush=True)
            if fails >= 10:
                con.commit()
                sys.exit("10 failures in a row, stopping. Nothing is lost, rerun later to continue.")
            continue
        fails = 0
        con.execute("INSERT OR REPLACE INTO pages VALUES (?,?,?)",
                    (url, zlib.compress(trim(page).encode()) if page else None, time.strftime("%Y-%m-%dT%H:%M:%S")))
        if i % 20 == 0 or i == len(todo):
            con.commit()
            print(f"{i}/{len(todo)}", flush=True)
        time.sleep(SLEEP)
    con.commit()


def text(fragment):
    # unescaped twice: the site stores some values already escaped (&amp;gt;)
    return re.sub(r"\s+", " ", htmllib.unescape(htmllib.unescape(re.sub(r"<[^>]+>", " ", fragment)))).strip()


PAIR_RE = re.compile(r'card__list-caption">\s*<span>(.*?)</span>\s*</div>\s*<div class="(card__list-val|starrate)\s*">(.*?)</div>', re.S)
NUM = r"(\d+(?:[.,]\d+)?)"
# "75 ккал", "310/75 кДж/ккал", "кДж/ккал: 280/70"
KCAL_RES = [re.compile(rf"{NUM}\s*/\s*{NUM}\s*кдж\s*/\s*ккал"), re.compile(rf"кдж\s*/\s*ккал\D{{0,5}}{NUM}\s*/\s*{NUM}"),
            re.compile(rf"(){NUM}\s*ккал")]
# sections whose goods have a composition worth analysing; anything outside /ratings/ is kept too
KEEP_RE = re.compile(r"/ratings/(produkty-pitaniya|napitki|krasota-i-zdorove|tovary-dlya-detey/(detskoe-pitanie|detskaya-gigiena))/")
# researches inside those sections, and special ones outside /ratings/, that are neither food nor cosmetics
# ponytail: a word list over the research title; a new non-food special research needs its word added here
JUNK_RE = re.compile(r"презерватив|прокладк|туалетн\w+ бумаг|стиральн|подгузник|вейп|одежд|обув|игруш", re.I)


def nutrition(s):
    """kcal/protein/fat/carbs per 100 g out of a retyped label.

    ponytail: naive regexes over free text, first number after the word wins; upgrade to a
    per-field parser if the values turn out wrong on review.
    """
    i = s.lower().find("ценност")
    if i < 0:
        return {}
    s = s[i:].lower()
    out = {}
    for rx in KCAL_RES:
        m = rx.search(s)
        if m:
            out["kcal"] = m.group(2)
            break
    for key, word in (("protein", "бел(?:к|ок)"), ("fat", "жир"), ("carbs", "углевод")):
        m = re.search(rf"{word}\w*[^\d;]{{0,15}}{NUM}", s)
        if m:
            out[key] = m.group(1)
    return {k: float(v.replace(",", ".")) for k, v in out.items()}


def parse_card(page, url):
    """One dict per card, with `barcodes` as a list of valid EANs (possibly empty). None if not a card."""
    def cls(name):
        m = re.search(rf'<div class="{name}">(.*?)</div>', page, re.S)
        return text(m.group(1)) if m else None

    name = cls("product__subtitle")
    if not name:
        return None
    fields, criteria = {}, {}
    for cap, kind, val in PAIR_RE.findall(page):
        if kind == "starrate":
            m = re.search(r'starrate__val[^>]*>([\d.]+)<', val)
            criteria[text(cap)] = float(m.group(1)) if m else None
        else:
            fields[text(cap)] = text(val)

    def bullets(title):
        m = re.search(rf'card__title">{title}<.*?<ul[^>]*>(.*?)</ul>', page, re.S)
        return [text(li) for li in re.findall(r"<li>(.*?)</li>", m.group(1), re.S)] if m else []

    raw = " ".join(fields.pop(k, "") for k in ("Штрихкод", "Штрихкоды"))
    barcodes = list(dict.fromkeys(filter(None, map(norm_barcode, re.findall(r"\d{8,14}", raw)))))
    crumbs = re.findall(r'"name": "([^"]+)",\s*"@id": "([^"]+)"', page)
    link = re.search(r'product__link" href="([^"]+)"', page)
    rating = re.search(r'starrate--big">\s*<span[^>]*>([\d.]+)<', page)
    photo = re.search(r'og:image" content="([^"]+)"', page)
    desc = re.search(r'product__text">(.*?)</div>', page, re.S)
    extra = {
        "url": url, "rating": float(rating.group(1)) if rating else None,
        "rating_url": BASE + link.group(1) if link else (crumbs[-1][1] if crumbs else None),
        "pros": bullets("Достоинства"), "cons": bullets("Недостатки"), "criteria": criteria,
        "description": text(desc.group(1)) if desc else None, "fields": fields,
        "barcode_raw": raw.strip() or None,
    }
    return {
        "barcodes": barcodes, "name": name, "brand": cls("product__title"),
        "category": " / ".join(c[0] for c in crumbs[2:]) or None,
        "quantity": fields.get("Вес") or fields.get("Объём"), "ingredients": fields.pop("Состав", None),
        "photo": "https:" + photo.group(1) if photo and photo.group(1).startswith("//") else None,
        "extra": {k: v for k, v in extra.items() if v not in (None, [], {})},
        **nutrition(fields.get("Пищевая ценность в 100г", "") + " " + fields.get("Дополнительная информация", "")),
    }


def cards():
    """Every cached card, parsed."""
    if not os.path.exists(DB):
        return
    for url, blob in connect().execute("SELECT url, html FROM pages WHERE html IS NOT NULL"):
        card = parse_card(zlib.decompress(blob).decode(), url)
        if card:
            yield card


def rows():
    """build_db.py input: one dict per (card, barcode), food/drinks/cosmetics only.

    Prefix-2 codes (in-store weighing labels) are loaded too, although the same code can mean
    another product in another shop. A product retested in a later year has a card
    per year with the same barcode; sorted so the newest one is loaded last and wins.
    """
    for card in sorted(cards(), key=lambda c: c["extra"].get("fields", {}).get("Год исследования", "")):
        if "/ratings/" in card["extra"].get("rating_url", "") and not KEEP_RE.search(card["extra"]["rating_url"]):
            continue
        if JUNK_RE.search(card["category"] or ""):
            continue
        for barcode in card["barcodes"]:
            yield {**card, "barcode": barcode, "source_id": card["extra"]["url"].rstrip("/").rsplit("/", 1)[1]}


def stats():
    all_cards, out = list(cards()), list(rows())
    print(f"cards parsed {len(all_cards)}, with a valid barcode {sum(bool(c['barcodes']) for c in all_cards)}, "
          f"rows for barcodes.db {len(out)} ({len({r['barcode'] for r in out})} distinct barcodes)")
    for key in ("name", "brand", "category", "quantity", "ingredients", "kcal", "protein", "fat", "carbs", "photo"):
        print(f"  {key:12} {sum(r.get(key) is not None for r in out)}")


def test():
    assert nutrition("Пищевая ценность: белки 20 г, жиры 1 г, углеводы 0 г, калорийность 89 ккал/373 кДж") == \
        {"kcal": 89, "protein": 20, "fat": 1, "carbs": 0}
    assert nutrition("энергетическая ценность/калорийность: 300/70 кДж/ккал. Спирт 12,5% об.") == {"kcal": 70}
    assert nutrition("средние значения: энергетическая ценность (калорийность), кДж/ккал: 280/70") == {"kcal": 70}
    assert nutrition("Пищевая ценность в 100 г: жиров - 24,6 г., белков -8,0 г.") == {"fat": 24.6, "protein": 8}
    assert nutrition("Пищевая ценность: жир - 10,0 г, белок - 2,6 г") == {"fat": 10, "protein": 2.6}
    assert nutrition("жирность 3,2%") == {}
    url = f"{BASE}/goods/vyazanka-doktorskaya-myasnoy-produkt-kategorii-a-kolbasnoe-izdelie-varenoe/"
    blob = connect().execute("SELECT html FROM pages WHERE url = ?", (url,)).fetchone()
    assert blob, "fetch first: the self-check needs the cached Вязанка card"
    c = parse_card(zlib.decompress(blob[0]).decode(), url)
    assert c["brand"] == "Вязанка" and c["name"].startswith("«Вязанка» «Докторская»")
    assert c["barcodes"] == ["2531199013338"] and c["ingredients"].startswith("свинина, говядина, вода")
    assert c["quantity"] == "1363 г" and c["photo"].endswith("8e2101c67e3d434bb1a3f2cf880906a4.jpg")
    e = c["extra"]
    assert e["rating"] == 4.83 and len(e["pros"]) == 6 and e["cons"] == ["Обнаружены следы антибиотика"]
    assert e["criteria"]["Содержание потенциально опасных веществ"] == 3.88 and len(e["criteria"]) == 7
    assert e["fields"]["Производитель"] == 'ЗАО "Стародворские колбасы"' and "Состав" not in e["fields"]
    assert e["rating_url"].endswith("/kolbasa-doktorskaya/") and "бензилпенициллина" in e["description"]
    assert c["category"].startswith("Продукты питания / Колбасные изделия")
    assert any(r["barcode"] == "2531199013338" for r in rows())  # in-store codes are kept
    assert JUNK_RE.search("Специсследования / Обувь для детей ясельного возраста") and not JUNK_RE.search(
        "Продукты питания / Колбасные изделия / Колбаса «Докторская»")
    print("rskrf ok")


if __name__ == "__main__":
    arg = sys.argv[1:]
    if "--test" in arg:
        test()
    elif "--stats" in arg:
        stats()
    else:
        fetch(int(arg[arg.index("--limit") + 1]) if "--limit" in arg else None)
        stats()
