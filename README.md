# barcodes — БД российских пищевых товаров по штрихкоду

> **Единая база: `barcodes.db` (SQLite).** Пересборка из всего собранного: `python3 build_db.py`
> (только stdlib, Postgres не нужен, ~2 минуты). Одна таблица `products`, ключ — `(barcode, provider)`:
> штрихкод повторяется по строке на каждого провайдера, ничего не сливается.
> Поля: `barcode, provider, source_id, name, brand, category, quantity, ingredients,
> kcal, protein, fat, carbs, photo, extra (JSON), country`.
> Провайдеры Mira называются по её собственному источнику: `mira_yuka`, `mira_national_catalog`,
> `mira_kuper`, `mira_ga`, `mira_mira`, либо просто `mira`, если источник не указан.
>
> Провайдер `rskrf` — карточки Роскачества (состав, рейтинг, достоинства/недостатки в `extra`):
> `HTTPS_PROXY=http://172.21.80.1:10809 python3 rskrf.py` кэширует карточки в `data/rskrf.db`
> (резюмируемо, ~2.5 ч на 14.5 тыс.), затем `python3 build_db.py` подтягивает их в базу.
>
> Провайдер `chestnyznak` — карточки Нацкаталога через бэкенд приложения «Честный знак» (состав,
> КБЖУ, фото): `HTTPS_PROXY=http://172.21.80.1:10809 python3 chestnyznak.py` спрашивает по очереди
> все EAN-13 из `barcodes.db` (сначала российские без состава), кэш в `data/chestnyznak.db`,
> резюмируемо, ~100 тыс. штрихкодов в сутки. Эндпоинт недокументированный: после 10 отказов подряд
> скрипт останавливается сам.
>
> Провайдеры `auchan`, `globus`, `fixprice` — карточки сетей с настоящим EAN, составом и КБЖУ:
> `python3 auchan.py` / `globus.py` / `fixprice.py` (общий код и ключи запуска — в `scrape.py`).
> Все парсеры двухстадийные: сырьё в `data/<имя>.db`, в базу попадает через `build_db.py`.
>
> Пример: `sqlite3 barcodes.db "select * from products where barcode='4607084356922'"`.
>
> Структура папки: `RESEARCH.md` — исследование источников (v1), `legacy_v1/` — скрипты v1,
> `data/old/` — старые БД v1/v2 (вход для `build_db.py`), `dumps/` — офлайн-дампы,
> `mira_teardown/` — разбор APK Миры. Всё ниже — пайплайн v2 на Postgres (парсеры ритейлеров).

Собирает штрихкод → название, бренд, состав, КБЖУ, фото, вес. Три слоя:

1. **Identity (штрихкод → название)** — два бесплатных офлайн-дампа
   (5.9M уникальных штрихкодов, 1.44M российских). Никакой сети, никаких банов.
2. **Enrichment (состав/КБЖУ/фото)** — парсеры ритейлеров (`sources/*.py`).
   Источники с EAN join'ятся напрямую, без EAN — локальным fuzzy-матчем имён
   (`pg_trgm`) к слою 1.
3. **Gap-fill** — точечный дозапрос по неизвестным штрихкодам (`sources/ozon.py`,
   платный ean-db.com, OpenFoodFacts). Не реализован до конца.

Хранилище — Postgres 17 в Docker. Всё идемпотентно: любой шаг можно перезапускать,
повторный `fetch` = режим актуализации (upsert по `source_id`).

**Важно:** ритейлеры (Метро, WB, ВкусВилл, Магнит, Лента, Ozon, Перекрёсток)
блокируют дата-центровые IP. Парсеры надо запускать **с российского IP**
(домашний интернет / RU-VPS) либо через прокси (`BARCODES_PROXY`).

---

## Установка на новом ПК

```bash
git clone https://github.com/Color-Kat/barcodes.git
cd barcodes

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt      # Windows: .venv\Scripts\pip

docker compose up -d                            # Postgres 17 на localhost:5433
```

DSN берётся из env `BARCODES_DSN`, по умолчанию
`host=localhost port=5433 dbname=barcodes user=barcodes password=barcodes`
— т.е. с docker-compose работает из коробки. Схема (`schema.sql`) применяется
автоматически при первом запуске любой команды.

> WSL: интеграция Docker Desktop с WSL слетает после перезапуска WSL — включить
> заново и `docker compose up -d`. Данные лежат в volume `pgdata`, не теряются.

### Слой 1: дампы (обязательно, ~1.6 ГБ, качается один раз)

В репозиторий не коммитятся (гигабайты). Скачать:

```bash
mkdir -p dumps
git clone --depth 1 https://github.com/papyrussolution/UhttBarcodeReference.git dumps/uhtt
git clone --depth 1 https://github.com/aioke/barcodes.git dumps/aioke
unzip -o dumps/aioke/barcodes_csv.zip -d dumps/aioke      # даёт barcodes.csv

.venv/bin/python load_dumps.py            # ~7.4M строк в raw_items, COPY, несколько минут
.venv/bin/python merge.py                 # -> products: 5.9M штрихкодов
```

Ожидаемо после загрузки: `raw_items` 7 439 266 строк, `products` 5 912 997
уникальных штрихкодов, из них 1 444 281 российских (префикс 46x). КБЖУ и состав
на этом этапе пустые — это слой 2.

---

## Запуск парсеров (слой 2)

Один скрипт «запустил и ушёл» — параллельно все источники, потом автоматом
match + merge + stats:

```bash
.venv/bin/python run_all.py                      # источники по умолчанию
.venv/bin/python run_all.py --limit 200          # смоук-тест: по 200 карточек с источника
.venv/bin/python run_all.py vkusvill magnit      # только эти
```

По умолчанию: `metro, wildberries, vkusvill, magnit`. Каждый источник — отдельный
процесс `run.py fetch <src>`, лог в `logs/<src>.log`, живой дашборд в консоли.
Заблокированный источник не мешает остальным.

Вручную, по шагам:

```bash
.venv/bin/python run.py fetch vkusvill [--limit N]   # скрейп одного источника -> raw_items
.venv/bin/python run.py match [--limit N]            # привязка безштрихкодных карточек к EAN (pg_trgm)
.venv/bin/python run.py merge                        # пересборка products из raw_items
.venv/bin/python run.py stats                        # покрытие по полям
```

### Прокси

Одна переменная проксирует все источники:

```bash
export BARCODES_PROXY=socks5://127.0.0.1:10808     # или http://user:pass@host:port
```

> Из WSL2 локальный прокси на Windows-хосте (`127.0.0.1:10808`) **не виден** —
> у WSL2 свой netns. Либо `.wslconfig` → `[wsl2] networkingMode=mirrored` +
> `wsl --shutdown`, либо забиндить клиент прокси на `0.0.0.0` и открыть файрвол.

### Источники

| Модуль | EAN | Состав/КБЖУ | Объём | Примечание |
|---|---|---|---|---|
| `metro` | ✅ | ✅ | много | GraphQL, всё одним запросом — лучший источник |
| `wildberries` | ✅ | ✅ | много | catalog.wb.ru + card.wb.ru (RU-IP) + wbbasket (любой IP) |
| `vkusvill` | ❌ | ✅ | ~13.7k | 2 sitemap'а, троттлит после ~15-30 быстрых запросов |
| `magnit` | ❌ | ✅ | ~20k | Nuxt SSR, sitemap ~20k |
| `ozon` | ✅ | ✅ | — | gap-fill по EAN, не bulk: капча, нужны residential-прокси |
| `lenta`, `perekrestok`, `nationalcatalog`, `barcode_list_ru` | ✅/❌ | ✅ | — | v1, не портированы в run_all (Qrator/ServicePipe) |

Без EAN (`vkusvill`, `magnit`) карточки привязываются к штрихкодам через
`run.py match` — локальный trigram-поиск по 5.9M имён, порог схожести
`SIM_FLOOR` в `matching.py` (сейчас 0.55).

Свой источник — контракт в [`sources/README_CONTRACT.md`](sources/README_CONTRACT.md):
модуль отдаёт `fetch(limit) -> Iterable[dict]`, HTTP через `sources/_util.py`
(единый прогресс-лог + бэйл при троттлинге + прокси).

---

## Экспорт

```bash
.venv/bin/python export.py                  # все товары с названием -> export.jsonl
.venv/bin/python export.py --enriched       # только с КБЖУ или составом
.venv/bin/python export.py --out food.jsonl --limit 1000
```

JSONL в форме TS-интерфейса `CatalogFoodLabelData` (nutrition per 100g,
packageSize, manufacturer, storageInfo, source).

---

## Файлы

```
run_all.py      оркестратор: все источники параллельно + match/merge/stats
run.py          CLI: fetch / match / merge / stats
db.py           коннект к Postgres, init схемы, bulk upsert
schema.sql      raw_items + products + pg_trgm индексы
normalize.py    norm_barcode (валидация контрольной суммы EAN-8/13), norm_name, страна по префиксу
load_dumps.py   загрузка дампов uhtt/aioke через COPY
matching.py     привязка безштрихкодных карточек к EAN (pg_trgm)
merge.py        сборка products из raw_items по приоритету источников
export.py       products -> CatalogFoodLabelData JSONL
sources/        парсеры источников
core.py, resolve.py, proxy_finder.py   легаси v1 (sqlite), не используются
```

У большинства модулей есть self-check: `python <module>.py` — прогоняет
проверки на зашитых примерах, ничего не скрейпит.

## Известные ограничения

- Полный прогон с RU-IP ещё не делался — реальное число обогащённых товаров
  неизвестно (на тесте: 30 карточек ВкусВилла → 13 полностью обогащённых товаров).
- `vkusvill`: поле «страна» иногда цепляет названия поставщиков.
- `samokat` не написан: нужен живой DevTools-проб detail-эндпоинта с RU-IP.
- `edadeal` выброшен: protobuf-фид промо-цен, ни EAN, ни КБЖУ, ни состава.
