"""barcode-list.ru — barcode->name directory (RU), no anti-bot.

No sitemap/category listing exists (checked: /sitemap.xml 404, /index/... is
just the homepage). The only enumeration path is the site's own search box:
https://barcode-list.ru/barcode/RU/Поиск.htm?barcode=<query> accepts either
a barcode or a free-text name and returns an HTML table of up to 5000
barcode+name+unit+rating rows (no further pagination beyond that cap).

So fetch() drives that search with a fixed list of common Russian grocery
terms/letters as seeds, parses the result table, dedupes by barcode, and
yields until `limit` is reached. This harvests real barcode->name pairs
without needing a pre-existing seed list from the DB.
"""
import html
import re
from urllib.parse import quote

from sources import _http

SEARCH_URL = "https://barcode-list.ru/barcode/RU/%D0%9F%D0%BE%D0%B8%D1%81%D0%BA.htm?barcode={}"

# Seed search terms: common Russian grocery/product words. Each query returns
# up to ~5000 rows server-side; rotating terms surfaces different products.
# ponytail: fixed seed list, not exhaustive of the 5M+ catalog — add more
# terms (or read barcodes_seed.txt / raw_items barcodes) if wider coverage matters.
SEED_TERMS = [
    "молоко", "хлеб", "сыр", "масло", "йогурт", "сок", "вода", "чай", "кофе",
    "шоколад", "конфеты", "печенье", "мясо", "колбаса", "рыба", "крупа",
    "макароны", "рис", "сахар", "соль", "мука", "яйца", "творог", "сметана",
    "кефир", "пиво", "вино", "чипсы", "орехи", "мороженое",
]

ROW_RE = re.compile(
    r'barcode-([0-9A-Za-z]+)/[^"]*"\s*title="(.*?) - Штрих-код:[0-9A-Za-z]+"[^>]*>'
    r'[^<]*</a></td>\s*<td[^>]*>\s*([^<]*)</td>\s*<td[^>]*>([^<]*)</td>\s*<td[^>]*>([^<]*)</td>',
)


def _parse(page_html):
    for barcode, name_a, name_td, unit, rating in ROW_RE.findall(page_html):
        name = html.unescape(name_td.strip() or name_a.strip())
        if not name:
            continue
        yield barcode.strip(), name, unit.strip(), rating.strip()


def fetch(limit=None):
    s = _http.session()
    seen = set()
    n = 0
    for term in SEED_TERMS:
        if limit is not None and n >= limit:
            return
        url = SEARCH_URL.format(quote(term))
        r = _http.get(s, url, min_interval=0.5)
        if r.status_code != 200:
            continue
        for barcode, name, unit, rating in _parse(r.text):
            if barcode in seen:
                continue
            seen.add(barcode)
            yield {
                "source_id": barcode,
                "barcode": barcode,
                "name": name,
                "extra": {"unit": unit, "rating": rating, "query": term},
            }
            n += 1
            if limit is not None and n >= limit:
                return


def demo():
    """Smoke test: parser correctly extracts rows from a known table shape."""
    sample = (
        '<tr class="even"><td style="text-align: right;">1</td>'
        '<td style="text-align: left;"> <a href="/barcode/RU/barcode-00000031/'
        'Поиск.htm" title="Молоко '
        'сгущеное - Штрих-код:00000031" '
        '>00000031</a></td><td style="text-align: left;"> Молоко '
        'сгущеное</td>'
        '<td style="text-align: center;">ШТ.</td>'
        '<td style="text-align: right;">1</td></tr>'
    )
    rows = list(_parse(sample))
    assert rows == [("00000031", "Молоко сгущеное", "ШТ.", "1")]
    print("demo ok")


if __name__ == "__main__":
    demo()
