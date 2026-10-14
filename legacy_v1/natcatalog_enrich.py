#!/usr/bin/env python3
"""Обогащение базы карточками Национального каталога (ЦРПТ / Честный знак).

Требует API-ключ: регистрация в ЛК Честного знака (нужно ИП/юрлицо) или запрос
на support@national-catalog.ru. Документация: https://docs.crpt.ru/gismt/API_НК/

Запуск: NK_APIKEY=xxx python3 natcatalog_enrich.py
Берёт из products.db штрихкоды без названия/состава, тянет карточки батчами,
обновляет записи. Запускать с российского IP.
"""
import json
import os
import sqlite3
import sys
import time

import requests

API = "https://апи.национальный-каталог.рф/v3/product"
APIKEY = os.environ.get("NK_APIKEY")
DB = "products.db"
BATCH = 50          # gtins за запрос
PAUSE = 1.0         # ponytail: фикс. пауза; подстрой под лимиты своего ключа


def pick(d, *keys):
    for k in keys:
        if d.get(k):
            return d[k]
    return None


def parse_card(card):
    """Вытащить нужные поля из карточки НК. Структура атрибутов у категорий
    различается — храним и разобранное, и сырой JSON."""
    attrs = {a.get("attr_name", ""): a.get("attr_value")
             for a in card.get("good_attrs", [])}
    return {
        "name": pick(card, "good_name", "name"),
        "brand": pick(card, "brand", "tm"),
        "ingredients": next((v for k, v in attrs.items() if "состав" in k.lower()), None),
        "image_url": (card.get("good_images") or [{}])[0].get("photo_url"),
        "raw": json.dumps(card, ensure_ascii=False),
    }


def main():
    if not APIKEY:
        sys.exit("Задай NK_APIKEY (см. шапку файла)")
    db = sqlite3.connect(DB)
    db.execute("ALTER TABLE products ADD COLUMN nk_raw TEXT") if not any(
        r[1] == "nk_raw" for r in db.execute("PRAGMA table_info(products)")) else None
    todo = [r[0] for r in db.execute(
        "SELECT barcode FROM products WHERE (name IS NULL OR ingredients IS NULL) AND nk_raw IS NULL")]
    print(f"К обогащению: {len(todo)}")

    for i in range(0, len(todo), BATCH):
        chunk = todo[i:i + BATCH]
        r = requests.get(API, params={"apikey": APIKEY, "gtins": ",".join(chunk)}, timeout=30)
        if r.status_code == 429:
            time.sleep(30)
            continue
        r.raise_for_status()
        for card in r.json().get("result", {}).get("goods", []):
            p = parse_card(card)
            db.execute(
                """UPDATE products SET name=coalesce(name,?), brand=coalesce(brand,?),
                   ingredients=coalesce(ingredients,?), image_url=coalesce(image_url,?),
                   nk_raw=? WHERE barcode=?""",
                (p["name"], p["brand"], p["ingredients"], p["image_url"], p["raw"],
                 str(card.get("gtin"))))
        db.commit()
        print(f"{i + len(chunk)}/{len(todo)}")
        time.sleep(PAUSE)


if __name__ == "__main__":
    main()
