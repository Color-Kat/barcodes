#!/usr/bin/env python3
"""Обогащение состав/КБЖУ поиском по НАЗВАНИЮ на сайтах ритейлеров.

⚠ Запускать с российского IP (из-за границы ритейлеры гео-блокируют).
⚠ Эндпоинты ритейлеров не проверены из песочницы — перед запуском открой
  сайт с DevTools (вкладка Network) и поправь SEARCH_URL/разбор ответа.

Ключевая часть — матчинг: выдаём данные только при уверенном совпадении
(вес/объём сходится, название похоже), иначе пропускаем. Ошибочный матч
опаснее пропуска: чужой состав = чужие аллергены.
"""
import difflib
import re
import sqlite3
import time

import requests

DB = "products.db"
PAUSE = 1.5
CONFIDENCE_MIN = 0.75

WEIGHT_RE = re.compile(r'(\d+[.,]?\d*)\s*(кг|г|гр|л|мл)\b', re.I)
UNIT_G = {"кг": 1000, "г": 1, "гр": 1, "л": 1000, "мл": 1}


def norm(s):
    return re.sub(r'[^a-zа-яё0-9 ]', ' ', s.lower()).split()


def weight_of(s):
    m = WEIGHT_RE.search(s or "")
    if not m:
        return None
    return float(m.group(1).replace(",", ".")) * UNIT_G[m.group(2).lower()]


def match_score(our_name, their_name):
    """0..1. Название по difflib + жёсткая проверка веса/объёма."""
    a, b = " ".join(norm(our_name)), " ".join(norm(their_name))
    score = difflib.SequenceMatcher(None, a, b).ratio()
    wa, wb = weight_of(our_name), weight_of(their_name)
    if wa and wb:
        if abs(wa - wb) / max(wa, wb) > 0.03:
            return 0.0          # вес не сходится — точно другой товар
        score += 0.15           # вес сходится — сильный сигнал
    return min(score, 1.0)


def search_perekrestok(sess, query):
    """Вернуть список dict(name, ingredients, kcal, proteins, fat, carbs).
    TODO: проверь эндпоинт в DevTools на www.perekrestok.ru и поправь."""
    r = sess.get(
        "https://www.perekrestok.ru/api/customer/1.4.1.0/catalog/product/feed",
        params={"search": query, "limit": 5}, timeout=30)
    r.raise_for_status()
    out = []
    for p in r.json().get("content", {}).get("items", []):
        nutr = {n.get("type"): n.get("value") for n in (p.get("nutrition") or [])}
        out.append({
            "name": p.get("title", ""),
            "ingredients": p.get("ingredients"),
            "kcal": nutr.get("energy"), "proteins": nutr.get("protein"),
            "fat": nutr.get("fat"), "carbs": nutr.get("carbohydrate"),
        })
    return out


PROVIDERS = [search_perekrestok]  # добавь купер/ленту/вкусвилл по той же схеме


def main():
    db = sqlite3.connect(DB, timeout=120)
    if not any(r[1] == "match_confidence" for r in db.execute("PRAGMA table_info(products)")):
        db.execute("ALTER TABLE products ADD COLUMN match_confidence REAL")
    todo = db.execute(
        """SELECT barcode, name FROM products
           WHERE name IS NOT NULL AND (ingredients IS NULL OR kcal_100g IS NULL)
             AND match_confidence IS NULL
           ORDER BY popularity DESC""").fetchall()
    print("К обогащению:", len(todo))
    sess = requests.Session()
    sess.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126"

    for barcode, name in todo:
        best, best_score = None, 0.0
        for provider in PROVIDERS:
            try:
                for cand in provider(sess, name):
                    s = match_score(name, cand["name"])
                    if s > best_score:
                        best, best_score = cand, s
            except Exception as e:
                print(barcode, "ERR", e)
            time.sleep(PAUSE)
        if best and best_score >= CONFIDENCE_MIN:
            db.execute(
                """UPDATE products SET ingredients=coalesce(ingredients,?),
                     kcal_100g=coalesce(kcal_100g,?), proteins_100g=coalesce(proteins_100g,?),
                     fat_100g=coalesce(fat_100g,?), carbs_100g=coalesce(carbs_100g,?),
                     match_confidence=? WHERE barcode=?""",
                (best["ingredients"], best["kcal"], best["proteins"], best["fat"],
                 best["carbs"], best_score, barcode))
        else:
            db.execute("UPDATE products SET match_confidence=0 WHERE barcode=?", (barcode,))
        db.commit()


if __name__ == "__main__":
    main()
