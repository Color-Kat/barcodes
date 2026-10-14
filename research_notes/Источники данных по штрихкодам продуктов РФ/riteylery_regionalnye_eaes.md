# Региональные сети РФ, магазины ЕАЭС и специализированные магазины как источники EAN + состав + КБЖУ (состояние на 13.10.2026)

**Как проверялось.** Все пробы — живые запросы `curl` 13.10.2026 (19:50–20:45 МСК), desktop Chrome UA, `Accept-Language: ru-RU`, ≤40 запросов на хост, ≥1 с между запросами. Антибот-проверки не решались и не обходились.
**Важная оговорка про точку наблюдения:** и «прямой» маршрут WSL, и прокси `172.21.80.1:10809` выходят в интернет с **немецкого датацентрового IP** (185.229.207.38 / 5.145.229.11, dataforest GmbH, Франкфурт — [ip-api](http://ip-api.com/json/?fields=country,city,isp,query)). Поэтому статусы «заблокировано / TLS reset» у российских и белорусских сайтов могут быть гео-/ASN-блокировкой и с российского резидентного IP отличаться. Всё, что не удалось открыть, помечено «не проверено».

Обозначения вердикта: **A** — брать в первую очередь; **B** — полезно, но мало/частично; **C** — маргинально; **X** — EAN в публичных данных нет; **Z** — закрыто challenge/блоком или недоступно (не проверено).

## Сводная таблица

| Магазин | Страна | Доступность (без challenge) | EAN (поле) | Состав | КБЖУ | Перечисление | Размер | Вердикт |
|---|---|---|---|---|---|---|---|---|
| **arbuz.kz** | KZ | 200, HTML | да: `barcode` / `article_index` в карточке товара (в листинге пусто) | да: `ingredients` (133/139) | да: `nutrition{kcal,protein,fats,carbs}` (137/139) | дерево категорий `window.siteCatalogTree` → `?page=N` (40/стр.) → `/catalog/item/{id}-…` | ~10–12 тыс. food (оценка по пагинации); «Россия» 40% (55/139) | **A** |
| **detmir.ru** («Питание и кормление») | RU | 200, HTML | да: `bar_codes[]` и в листинге, и в карточке; EAN даже в `<title>` | да: `attributes[id=sostav]` (4/5 съедобных) | да: `primaryAttributes` (kilokalorii/belki/zhiry/uglevody), реже | категория `…/name/nutrition_feeding/?page=N` (36/стр.) | 14 683 в наличии; ~60% EAN с префиксом 46 | **A** |
| **green-dostavka.by** | BY | 200, HTML и JSON API | да: `gtin`, `barcodes[].code` (22/22) | да: `description` (10/10 food) | да: `energyCost` (текстом) | sitemap 19 756 URL; API `/api/v1/products` (limit ≤100) → деталь по id/slug | 19 771 карточка, food ≈45%; RU-префикс в food мал (1/10) | **A/B** |
| **gippo-market.by** (API `app.willesden.by`) | BY | 200, JSON | да: `barcode` прямо в листинге (600/600) | частично: `description` (≈45% похоже на состав) | частично: `properties.energy/proteins/fats/carbohydrates` (≈30%) | `…/guest/shop/products?market_id=73&page=N&per_page=100` — 144 стр., сортировка по штрихкоду | 14 307; префикс 46 — 19% (114/600) | **B** (очень дёшево) |
| **fix-price.com** | RU | 200, HTML (Nuxt 2) | да: `variants[].barcode` | да: `composition` | да: `nutritionalValueSeparated{energyValue,protein,fats,carbohydrates}` | категории `/catalog/produkty-i-napitki/...` | 1 150 food (`productsCount`) | **B** |
| 5lb.ru (спортпит) | RU | 200 | да: «Штрихкод» в карточке; JSON быстрого поиска с `barcode` | в тексте карточки нет (1/1) | нет (1/1) | sitemap только категории | не проверено | **C** |
| yerevan-city.am | AM | 200, JSON API | да: `barcode` (`/api/Product/GetPublic/{id}`) | нет (`description` пуст, 2/2) | нет | sitemap-products-1…6 (по 5 000) | ≤30 тыс.; названия на армянском | **C** (EAN+фото) |
| sima-land.ru (API v3) | RU | 200, XML API | да: `expand=barcodes` (реальный EAN у 25/50) | нет: `stuff` = «См. на упаковке» (0/50) | редко (4/50) | `/api/v3/item/?category_id=24182` | 2 348 food | **C** |
| europa-market.ru (Курск) | RU | 200 | поля нет; EAN только в имени файла фото (36/65) | да: `params.ingredients` (48/65) | да: `params.energy/nutrition` | категории `/catalog/…` | не проверено | **C** (эвристика) |
| zdravcity.ru | RU | 200 | поле `gtin` есть, но `null`/`""` (2/2) | — | — | sitemap `products-1.xml` 37 873 | — | **X** |
| gorzdrav.org | RU | 200 | ключ `barcodes` есть, но `[]` (1/1) | да (атрибут `ingredients`) | — | — | — | **X**/не проверено шире |
| yarcheplus.ru (Ярче) | RU | 200 | нет | да | да | `/catalog/…`, `/product/…` | не проверено | **X** |
| shop.slata.com (Слата) | RU | 200 | нет (`vendorCode` внутренний) | да `compound` | да `nutrients` | `/product/{код}` | — | **X** |
| shop.samberi.com (Самбери) | RU | 200 | нет | да (`SOSTAV`) | — | `/catalog/…`, `/products/…` | — | **X** |
| maxi-retail.ru (Макси, Вологда) | RU | 200 | нет | да | да | `/vologda/catalog/{id}` | — | **X** |
| shop.mgnl.ru (Магнолия) | RU | 200 | нет | нет на карточке | да | Bitrix `/catalog/…` | — | **X** |
| vkuster.ru (Вкустер) | RU | 200 | нет | да | да | `/catalog/…`, `/product/…` | — | **X** |
| kirmarket.ru (Кировский) | RU | 200 | нет | нет | нет | — | — | **X** |
| globus-online.kg | KG | 200 | нет (платформа типа Лавки) | да | да (на 100 г) | `/ru-kg/good/{id}` | — | **X** |
| kaspi.kz (продукты) | KZ | 200 | нет | да (`food*elements`) | да | XHR `/yml/product-view/pl/results` | — | **X** |
| 21vek.by | BY | 200 | нет | да | да (JSON-LD) | sitemap-cards (≈1,7 млн всего) | — | **X** |
| sas.am | AM | 200 | нет | не найден | не найден | `/catalog?prod=` | — | **X** |
| napolke.ru (B2B) | RU | 200 | нет (uuid, бренд, производитель) | нет | нет | `/catalog/product/…` | — | **X** |
| edostavka.by / emall.by (Евроторг) | BY | **JS-challenge `hg-security`** / 403 «Запрос заблокирован» | не проверено | по стороннему репозиторию — да | не проверено | `?page=N` (по стороннему репо) | 11 425 (по стороннему репо, 07.2026) | **Z** — главный непроверенный лид |
| av.ru (Азбука вкуса) | RU | ServicePipe, HTTP 450 | не проверено | по стороннему репо — да | по стороннему репо — да | — | — | **Z** |
| myspar.ru | RU | Variti, 403 | не проверено | — | — | — | — | **Z** |
| monetka.ru, bristol.ru, planetazdorovo.ru | RU | Qrator, 401 (`/__qrator/qauth.js`) | не проверено | — | — | — | — | **Z** |
| chizhik.club, onlinetrade.ru, megamarket.ru | RU | ServicePipe | не проверено | — | — | — | — | **Z** |
| apteka.ru | RU | 432 «С вашего IP замечена подозрительная активность» (sitemap открыт: 36 410 товаров) | не проверено | — | — | sitemap-product.xml | 36 410 | **Z** |
| eapteka.ru | RU | 403 | не проверено | — | — | — | — | **Z** |
| officemag.ru, krasnoeibeloe.ru (карточка) | RU | «Проверка безопасности» | не проверено | — | — | — | — | **Z** |
| komus.ru | RU | 503 (ngenix) | не проверено | — | — | — | — | **Z** |
| optlist.ru | RU | «Проверяем ваше соединение» | не проверено | — | — | — | — | **Z** |
| small.kz, carrefour.am | KZ / AM | Cloudflare «Just a moment…» | не проверено | — | — | — | — | **Z** |
| yamigom-store.by | BY | 403 Access denied | не проверено | — | — | — | — | **Z** |
| selgros.ru, semya.ru, spar-online.ru | RU | TLS reset (вероятно гео-блок не-RU IP) | не проверено | — | — | — | — | **Z** |
| Без веб-каталога товаров: sosedi.by, korona.by, prostore.by, magnum.kz, airbafresh.kz, sm-komandor.ru, maria-ra.ru, remi.ru, krasyar.ru, bahetle.com, dixy.ru, verno-info.ru, 4fresh.ru | — | 200 | — | — | — | — | — | не источник |

## Вопрос 1. По каждому магазину: доступность, EAN, состав, КБЖУ, перечисление, размер, доля российских товаров

### Takeaway
EAN вместе с составом и/или КБЖУ в открытых HTML/JSON без антибот-проверки отдают пять площадок: **arbuz.kz, detmir.ru, green-dostavka.by, gippo-market.by (API app.willesden.by) и fix-price.com**; ещё четыре дают EAN без нормального состава (5lb.ru, yerevan-city.am, sima-land.ru, europa-market.ru — последний только эвристикой по имени фото). Большинство региональных сетей РФ (Ярче, Слата, Самбери, Макси, Магнолия, Вкустер) публикуют состав и КБЖУ, но **не публикуют штрихкод**, а часть сетей вообще не имеет веб-каталога или закрыта Qrator/Variti/ServicePipe.

### Cited Findings

#### A. arbuz.kz (Казахстан, Алматы)
- `robots.txt` → 200; запрещены только `/api/`, `/search/`, `/cms/`, `/admin/`, `/user/*`; объявленный `Sitemap: https://arbuz.kz/sitemap.xml` отдаёт 404 — [robots.txt](https://arbuz.kz/robots.txt), [sitemap.xml](https://arbuz.kz/sitemap.xml)
- Главная и категории → HTTP 200 без challenge (в коде есть только Cloudflare-beacon `/cdn-cgi/challenge-platform/scripts/jsd/main.js`, это не проверка) — [главная](https://arbuz.kz/)
- Карточка товара → 200, 22 КБ gzip / 131 КБ. В атрибуте `:product` компонента `<div is='product-card'>` лежит **сырая запись БД** (HTML-escaped JSON) с полями `barcode`, `article_index`, `manufacturer_country`, `brand_name`, `ingredients`, `nutrition`, `storage_conditions`, `image`, а также внутренними `profit_percent`, `supplier_id` — [карточка Makfa](https://arbuz.kz/ru/almaty/catalog/item/176799-makarony_makfa_shpinatnye_500_g). Усечённый образец:
  ```
  "article_index":"4601780010775","manufacturer_country":"Россия","brand_name":"Makfa","name":"Макароны Makfa шпинатные 500 г",
  ... "barcode":"4601780010775", ... "profit_percent":"30.00","supplier_id":390, ...
  "nutrition":"{\"fats\": \"1.0\", \"kcal\": \"362\", \"carbs\": \"73.5\", \"protein\": \"14.7\"}",
  "ingredients":"Мука из твёрдой пшеницы для макаронных изделий второго сорта, шпинатный порошок, вода питьевая.<br />Изделия могут содержать следы яичных продуктов."
  ```
- JSON-LD карточки содержит только `sku`/`mpn` = внутренний id (176799), без gtin — [та же карточка](https://arbuz.kz/ru/almaty/catalog/item/176799-makarony_makfa_shpinatnye_500_g)
- Листинг категории → 200, 40 товаров на страницу; в листинге есть `producerCountry`, `brandName`, `ingredients`, `nutrition{fats,kcal,carbs,protein}`, `uri`, `image`, но `"barcode":""` и `"articleIndex":""` пустые — [категория «Макароны и лапша»](https://arbuz.kz/ru/almaty/catalog/cat/224399-makarony_i_lapsha)
- Серверная пагинация `?page=N` работает (стр. 2 отдала 40 других id; стр. 6 — пусто) — [стр. 2](https://arbuz.kz/ru/almaty/catalog/cat/224399-makarony_i_lapsha?page=2), [стр. 6](https://arbuz.kz/ru/almaty/catalog/cat/224399-makarony_i_lapsha?page=6)
- Дерево категорий целиком лежит в `window.siteCatalogTree` на любой странице каталога: 24 раздела верхнего уровня, из них продуктовых ~16 (Овощи/фрукты; Молоко, сыр, яйца; Колбасы; Мясо; Рыба; Заморозка; Вода и напитки; Орехи/снеки; Здоровое питание; Хлеб; Готовая еда; Кофе/чай; Кондитерские; Бакалея; Алкоголь; Детское питание) — [категория](https://arbuz.kz/ru/almaty/catalog/cat/224399-makarony_i_lapsha)
- Листинг раздела верхнего уровня агрегирует подкатегории. Замеры границ пагинации: «Кондитерские изделия» — стр. 30 = 11 товаров (итого 1 171); «Бакалея» — стр. 40 полная, стр. 50 пустая (1 600–2 000); «Молоко, сыр и яйца» — стр. 30 полная, стр. 45 пустая (1 200–1 800); «Вода и напитки» — стр. 12 = 38 (478); «Замороженные продукты» — стр. 15 = 19 (579); «Колбасы и деликатесы» — стр. 12 пустая (<480); «Кофе, чай, какао» — стр. 20 пустая (<800) — [Кондитерские p30](https://arbuz.kz/ru/almaty/catalog/cat/225166-konditerskie_izdeliya?page=30), [Бакалея p40](https://arbuz.kz/ru/almaty/catalog/cat/225169-bakaleya?page=40), [Бакалея p50](https://arbuz.kz/ru/almaty/catalog/cat/225169-bakaleya?page=50), [Молоко p30](https://arbuz.kz/ru/almaty/catalog/cat/225161-moloko_syr_i_yaica?page=30), [Вода p12](https://arbuz.kz/ru/almaty/catalog/cat/14-voda_i_napitki?page=12), [Заморозка p15](https://arbuz.kz/ru/almaty/catalog/cat/225183-zamorozhennye_produkty?page=15)
- По 139 товарам из 5 страниц листинга (Бакалея, Кондитерские, Молочные): `ingredients` заполнен у 133, `nutrition` с ккал у 137; страна-производитель: Россия 55, Казахстан 46, Италия 29, прочие 9 — [Бакалея p40](https://arbuz.kz/ru/almaty/catalog/cat/225169-bakaleya?page=40), [Кондитерские p30](https://arbuz.kz/ru/almaty/catalog/cat/225166-konditerskie_izdeliya?page=30)
- Выборка 9 случайных карточек + 1 исходная: штрихкод есть в 10/10. У уценённых товаров («Дисконт: …») в `barcode` стоит внутренний код (`2501802`), а настоящий EAN — в `article_index` (`4601916004920`) — пример: [карточка Makfa](https://arbuz.kz/ru/almaty/catalog/item/176799-makarony_makfa_shpinatnye_500_g) (остальные 9 карточек той же структуры, URL вида `https://arbuz.kz/ru/almaty/catalog/item/{id}-{slug}`)
- Курьёз: сыр President (`4607037121560`, префикс РФ) помечен `manufacturer_country: Казахстан` — т. е. поле страны и префикс EAN расходятся — [листинг молочных](https://arbuz.kz/ru/almaty/catalog/cat/225161-moloko_syr_i_yaica?page=30)

#### A. detmir.ru (Детский мир — детское питание, бакалея «для всей семьи», БАДы, спортпит)
- Главная, категория, карточка, поиск → HTTP 200 без challenge с немецкого IP (маркер `smartcaptcha` присутствует в коде, но проверка не показывалась) — [главная](https://www.detmir.ru/)
- Листинг категории (SSR-состояние в HTML): у каждого из 36 товаров на странице есть `"bar_codes":["…"]`; `meta.length = 14683` (в наличии, регион по умолчанию), у категории `products_count: 67066` — [«Питание и кормление»](https://www.detmir.ru/catalog/index/name/nutrition_feeding/). Образец: `"bar_codes":["4600209012802"]` → «Смесь молочная Nutrilon Premium 2 1200г»
- Пагинация: `/page/50/` редиректит на `?page=50`, отдаёт 36 других товаров, у всех 36 `bar_codes` непустые; часть товаров имеет 2–3 кода (`["4607174146624","4680681910711"]`) — [стр. 50](https://www.detmir.ru/catalog/index/name/nutrition_feeding/?page=50)
- Префиксы первого штрихкода: стр. 1 — «46» 11 из 33; стр. 50 — 22 из 36; категория «пюре» — 30 из 36 — [стр. 1](https://www.detmir.ru/catalog/index/name/nutrition_feeding/), [стр. 50](https://www.detmir.ru/catalog/index/name/nutrition_feeding/?page=50), [пюре](https://www.detmir.ru/catalog/index/name/pure/)
- Карточка: состав в `attributes[{id:"sostav",title:"Состав",values:[{id:"<текст>"}]}]`, КБЖУ структурно в `primaryAttributes{title:"Пищевая и энергетическая ценность на 100 г", attributes:[{code:"kilokalorii",value:66},{code:"belki",value:1.3},{code:"zhiry",value:3.1},{code:"uglevody",value:7.9}]}`; EAN в `bar_codes` и прямо в `<title>` у части товаров — [Nutrilon Premium 2](https://www.detmir.ru/product/index/id/3168637/), [пример с EAN в title](https://www.detmir.ru/product/index/id/5144048/)
- Выборка 7 случайных карточек со стр. 50: `bar_codes` 7/7 (все с префиксом 46); из 5 съедобных/БАД состав есть у 4, ккал у 1; 2 из 7 — несъедобные (бутылочка, прорезыватель) — [пример: пюре Бибиколь](https://www.detmir.ru/product/index/id/6429825/), [пример без состава: печенье Бибиколь](https://www.detmir.ru/product/index/id/6563997/)
- `robots.txt`: карточки `/product/index/id/N/` и категории `/catalog/index/name/…/` не запрещены; запрещены `/search/results/`, `/*/page/1/`, `/page/`, `*/id*?page`; строки `Sitemap:` нет — [robots.txt](https://www.detmir.ru/robots.txt)
- Старый API `api.detmir.ru/v2/products?filter=categories[].alias:…` вернул 404 `not_found` (дважды, с разными alias) — [проба](https://api.detmir.ru/v2/products?filter=categories%5B%5D.alias:nutrition_feeding;promo:false;withregion:RU-MOW&limit=30&offset=0)

#### A/B. green-dostavka.by (Беларусь, сеть Green)
- `robots.txt` → 200: разрешены `/product/…`, запрещены `/search/`, `*?storeId=*`, `*?offset=`, `*?filters*` — [robots.txt](https://green-dostavka.by/robots.txt)
- Sitemap: один файл, 19 756 URL `/product/…` и 821 `/catalog/…` — [sitemap-0.xml](https://green-dostavka.by/sub-sitemaps/sitemap-0.xml)
- Карточка (HTML 143 КБ gzip, `__NEXT_DATA__`): `gtin`, `barcodes[{code}]`, `description` (состав), `energyCost` (КБЖУ строкой), `producer`, `producingCountry`, `storageConditions`, `brand`; в вёрстке видимая строка «Штрихкод: 4815101004606» — [карточка чипсов Онега](https://green-dostavka.by/product/chipsy-iz-naturalnogo-kartofelya-onega-so-vkusom-smetany-i-zeleni-67-g-1620287/). Образец:
  ```
  "energyCost":"белки – 5,5 г; жиры – 36,0 г; углеводы – 47,0 г; энергетическая ценность – 540 ккал/2250 кДж.",
  "barcodes":[{"id":"5250353406","productId":367791719,"code":"4815101004606"}], "producer":"ООО «Азбука снеков»",
  "gtin":"4815101004606","description":"Картофель, масло растительное*, ароматизатор пищевой «Сметана с зеленью»","producingCountry":"РБ"
  ```
- JSON API без авторизации (`BACKEND_API: https://green-dostavka.by/api` из `runtimeConfig`): листинг `/api/v1/products?storeId=2&limit=100&skip=0` → `count: 19771`; `limit=1000` → 400 `INVALID_LIMIT_VALUE`; в листинге есть `energyCost`, но **нет** `gtin`/`description` — [листинг](https://green-dostavka.by/api/v1/products?storeId=2&limit=100&skip=0), [limit=1000](https://green-dostavka.by/api/v1/products?storeId=2&limit=1000&skip=4000)
- Деталь `/api/v1/products/{id или slug}?storeId=2` → 200, 2,5 КБ JSON с `gtin`, `barcodes`, `description`, `energyCost`, `producingCountry`, `producer` — [деталь](https://green-dostavka.by/api/v1/products/378123400?storeId=2). Формально URL с `?storeId=` подпадает под `Disallow: *?storeId=*` в robots.txt; HTML-карточки из sitemap под запрет не подпадают.
- Категории: `/api/v1/categories?storeId=2` — 31 раздел верхнего уровня, из них ~15 продуктовых — [категории](https://green-dostavka.by/api/v1/categories?storeId=2)
- Случайная выборка 22 карточек из sitemap (seed 42): `gtin` 22/22; food 10 из 22, у всех 10 есть состав и КБЖУ; префиксы food: 481 — 8 (из них один товар со страной «Россия» — вяленая щука), 461 — 1 (цветная капуста AGAMA), 590 — 1; по всей выборке префикс 46 у 6 из 22 (в основном бытовая химия/косметика) — [пример food](https://green-dostavka.by/api/v1/products/378123400?storeId=2)
- Сторонний открытый парсер (README от 29.07.2026) сообщает о 20 226 товарах и 12 811 составах, собранных с green-dostavka.by через `/api/v1/products` — [abmwm4-byte/edostavka_parser](https://github.com/abmwm4-byte/edostavka_parser)

#### B. gippo-market.by (Беларусь, ГИППО) — backend `app.willesden.by`
- Сайт — Angular SPA (3,5 КБ shell), `apiUrl:"https://app.willesden.by/api"`, `companyKey:"gippo"` в `main-*.js`; `robots.txt` сайта: `Disallow: *?*`, `*/search/*` — [главная](https://gippo-market.by/), [robots.txt](https://gippo-market.by/robots.txt)
- Sitemap: 37 425 URL (карточки вида `/раздел/подраздел/…/slug`) — [sitemap.xml](https://gippo-market.by/sitemap.xml)
- Листинг без авторизации: `GET /api/guest/shop/products?market_id=73&page=N&per_page=100` → 200; `meta.total = 14307`, `last_page = 144`; сортировка по штрихкоду как строке — [листинг](https://app.willesden.by/api/guest/shop/products?market_id=73&page=1&per_page=20), [стр. 60](https://app.willesden.by/api/guest/shop/products?market_id=73&page=60&per_page=100). Образец:
  ```
  {"id":"99467589-…","barcode":"054881004718","title":"Чай зеленый Ahmad жасминовый 25х2 г","slug":"chay-zelenyy-ahmad-…",
   "description":"Тип товара чай пакетированный бренд Ahmad","images":["https://app.willesden.by/images/054881004718.png"],
   "properties":{"brandText":{…"value":"Ahmad"},"nameCountry":{…"value":"РОССИЯ"},"energy":{…},"proteins":{…},"fats":{…},"carbohydrates":{…}}}
  ```
- По 600 товарам (6 страниц по 100): `barcode` 600/600; 13-значных с префиксом 481 — 324, с префиксом 46 — 114 (19%), 7-значные внутренние — 39; `energy` у 178, `proteins` 178, `fats` 176, `carbohydrates` 179; `description` не-заглушка у 376, похоже на состав у 269 (эвристика по ключевым словам «состав/мука/сахар/вода/молоко/масло/соль», включает и непродуктовые товары) — [стр. 12](https://app.willesden.by/api/guest/shop/products?market_id=73&page=12&per_page=100), [стр. 84](https://app.willesden.by/api/guest/shop/products?market_id=73&page=84&per_page=100), [стр. 132](https://app.willesden.by/api/guest/shop/products?market_id=73&page=132&per_page=100)
- Среди 114 товаров с префиксом 46: состав-подобное описание у 44, КБЖУ у 31, хотя бы одно из двух у 59 — [стр. 60](https://app.willesden.by/api/guest/shop/products?market_id=73&page=60&per_page=100)
- Деталь `/api/guest/shop/products/{slug}?market_id=73` → 200; у хорошо заполненной карточки состав лежит в `description`, КБЖУ — в `properties` (пример: Агуша кабачок, `barcode 4690228033056`, `energy 20`, `carbohydrates 4`) — [деталь](https://app.willesden.by/api/guest/shop/products/pyure-ovoschnoe-agusha-kabachok-0-0-80g-banka-steklo?market_id=73)
- Список магазинов/`market_id` — [markets](https://app.willesden.by/api/guest/markets); категории — [categories](https://app.willesden.by/api/guest/shop/categories?market_id=73)

#### B. fix-price.com (РФ; федеральная сеть, в список исключений не входит)
- Главная, категория, карточка → 200 без challenge; `sitemap_index.xml` из robots.txt → 503, `/sitemap.xml` → 404 — [главная](https://fix-price.com/), [sitemap_index.xml](https://fix-price.com/sitemap_index.xml)
- Карточка (Nuxt 2, `window.__NUXT__` в виде IIFE с подстановкой переменных): `variants[{…,barcode:"4610003252809",…}]`, свойства с `alias:"composition"`, `alias:"nutritionalValue"`, `alias:"nutritionalValueSeparated"`, `manufacturer`, `manufacturerAddress` — [печенье Любятово](https://fix-price.com/catalog/produkty-i-napitki/konditerskie-izdeliya/p-1950476-pechene-myusli-lyubyatovo-s-klyukvoy-i-izyumom-120-g). Образец:
  ```
  title:"Состав"},{id:Z,alias:"nutritionalValueSeparated",value:{description:"Пищевая ценность на 100г",energyValue:"470",protein:"6",fats:"19",carbohydrates:"69"},…
  variants:[{id:352855,…,barcode:"4610003252809",…},{id:17372,…,barcode:fS,…}]
  ```
  (часть значений — ссылки на аргументы IIFE, например `barcode:fS`, поэтому нужен разбор списка аргументов функции, а не простой regexp)
- Категория «Продукты и напитки»: `productsCount:"1150"`, 17 подкатегорий (бакалея, кондитерские, молочные, соки, воды, консервация, детское питание, БАДы и т. д.) — [категория](https://fix-price.com/catalog/produkty-i-napitki)
- Непродуктовая карточка тоже содержит `barcode:"4602984016549"` и состав — [Белизна гель](https://fix-price.com/catalog/bytovaya-khimiya/p-3010136-chistyaschee-sredstvo-belizna-gel-anfor-3-v-1-450-g)
- `robots.txt`: `Disallow: /search` и набор частных запретов на `?page=` — [robots.txt](https://fix-price.com/robots.txt)

#### C. 5lb.ru (спортивное питание, батончики, БАДы)
- Карточка → 200; в характеристиках видимая строка «Штрихкод 4660298500703»; текста состава и КБЖУ на проверенной карточке нет — [печенье Bombbar Brownie](https://5lb.ru/product/pechene-bombbar-brownie-50-g-bombbar-14789591/)
- JSON быстрого поиска (endpoint прописан в `/i/js/5lb.js`): массив `{id,name,image,barcode,href}` — [поиск «bombbar»](https://5lb.ru/search/?jssearch=enabled&mime=json&show=489395&product_string=bombbar), [5lb.js](https://5lb.ru/i/js/5lb.js?v=1.185). Образец: `{"id":"14789591","name":"Печенье Bombbar Brownie 50 г - вишневый","barcode":"4660298500703","href":"/product/pechene-bombbar-brownie-50-g-bombbar-14789591/"}`
- `robots.txt`: `Disallow: /search`, `Disallow: /*page`, `Crawl-delay: 2`; sitemap (1 135 URL) содержит новости/блог/159 категорий, но не карточки — [robots.txt](https://5lb.ru/robots.txt), [sitemap.xml](https://5lb.ru/sitemap.xml)

#### C. yerevan-city.am (Армения)
- `robots.txt`: `Allow: /`; sitemap-индекс: 6 файлов `sitemap-products-N.xml` (в первом 5 000 URL `/shop/product-details/{id}`) + 58 файлов ресторанного маркетплейса — [robots.txt](https://www.yerevan-city.am/robots.txt), [sitemap.xml](https://yerevan-city.am/sitemap.xml), [sitemap-products-1.xml](https://yerevan-city.am/sitemap-products-1.xml)
- Публичный API без авторизации: `GET https://apishopv2.yerevan-city.am/api/Product/GetPublic/{id}` → `{id,name,description,photo,category,brandName,barcode,price,…}`; пример российского товара: `"barcode":"4610101148011"` (крабовые палочки Vici), `description` пуст, название на армянском; заголовки `language: 2` и `Accept-Language: ru` язык не поменяли — [GetPublic/180174](https://apishopv2.yerevan-city.am/api/Product/GetPublic/180174), [карточка 108569](https://www.yerevan-city.am/shop/product-details/108569)

#### C. sima-land.ru (опт, публичный API v3)
- `GET /api/v3/item/?category_id=24182&expand=barcodes,description,attrs` → 200 XML без ключа; `totalCount 2348` для «Продукты питания» (id 24182); у товара `<barcodes><item>2900104130239</item><item>4627197488587</item>…</barcodes>` (внутренние коды 29…/69… вперемешку с настоящими EAN) — [проба](https://www.sima-land.ru/api/v3/item/?per-page=3&page=1&expand=barcodes,description,attrs&category_id=24182), [категории](https://www.sima-land.ru/api/v3/category/?per-page=100&level=1)
- По 50 товарам ответа: настоящий EAN у 25, с префиксом 46 у 21; поле `stuff` ни разу не содержит реального состава («См. на упаковке»); упоминание калорийности в атрибутах — у 4 — [та же проба](https://www.sima-land.ru/api/v3/item/?per-page=3&page=1&expand=barcodes,description,attrs&category_id=24182)
- Весь каталог API: `totalCount 180987` — [проба](https://www.sima-land.ru/api/v3/item/?per-page=3&page=1)

#### C. europa-market.ru (сеть «Европа», Курск)
- Категория и карточка → 200 (Nuxt 3, `__NUXT_DATA__`); у товара `params{energy,nutrition,ingredients,properties,storage,…}`, поля штрихкода нет; у 36 из 65 товаров на странице имя файла фото — это EAN (`…/image/202604/4660326840962.jpg`), у остальных — внутренний id (`…/201605/10163.jpg`); `ingredients` заполнен у 48 из 65 — [карточка](https://europa-market.ru/product/file_mintaya_bsh_5_glazuri_sm-10163), [категория](https://europa-market.ru/catalog/ryba_svezhemorozhenaya-3114)

#### X. Каталог есть, состав/КБЖУ есть, штрихкода в публичных данных нет
- Ярче (`yarcheplus.ru`): в `__INITIAL_STATE__` у товара `id, code, name, description, calories, fat, protein, carbohydrate, ingredients`; ключей barcode/gtin/ean нет — [карточка](https://yarcheplus.ru/product/abrikosy-v-sirope-5085)
- Слата (`shop.slata.com`): `{vendorCode:"135736", title, compound:"Свинина, мясо куриное…", nutrients:[ккал 150, белки, жиры, углеводы], originCountry, brand}`, штрихкода нет — [карточка](https://shop.slata.com/product/135736)
- Самбери (`shop.samberi.com`): свойства `BREND, VES, CML2_MANUFACTURER, SOSTAV, STRANA_PROISKHOZHDENIYA`; штрихкода нет — [карточка](https://shop.samberi.com/products/syr_plavlenyy_fetaksa_khokhland_200g/)
- Макси (`maxi-retail.ru`): блоки «Состав» и «Пищевая ценность» в вёрстке, в листинге `id, nomenclature_id, name, image_url`; штрихкода нет — [карточка](https://maxi-retail.ru/vologda/catalog/2270/124865)
- Магнолия (`shop.mgnl.ru`): «Калорийность, ккал 520; Белки 7.5; Жиры 34; Углеводы 47», штрихкода нет — [карточка](https://shop.mgnl.ru/catalog/shokolad_tyemnyy_75g_osobyy/)
- Вкустер (`vkuster.ru`): «Состав», «41 ккал», штрихкода нет — [карточка](https://vkuster.ru/product/pivo-grotverg-vaysbir-pshenichnoe-svetloe-0-5l-4-9-zh-b/)
- Кировский (`kirmarket.ru`): ни штрихкода, ни состава — [карточка](https://kirmarket.ru/catalog/product/BANANY-EKVADOR/)
- globus-online.kg (онлайн-магазин Globus, Киргизия): «Состав», КБЖУ на 100 г (`data-testid="traits-list-per100g"`), идентификатор товара — 44-символьный hex, штрихкода нет — [карточка](https://globus-online.kg/ru-kg/good/1498330931d7428cbbc0d258ab837cf0000100010000)
- kaspi.kz: листинг — XHR JSON, в карточке `features` с `food*elements` («Состав»), `food*proteins`, «535 ккал»; штрихкода нет — [листинг](https://kaspi.kz/yml/product-view/pl/results?page=0&q=%3Acategory%3AFood&text&sort=relevance&qs&ui=d&i=-1&c=750000000), [карточка](https://kaspi.kz/shop/p/dubaiskii-molochnyi-shokolad-ulker-meshur-dubai-lezzeti-s-nachinkoi-iz-fistashek-93-g-129068014/?c=750000000)
- 21vek.by: «Состав», «Энергетическая ценность, ккал/100 г» в JSON-LD; штрихкода нет — [карточка](https://www.21vek.by/coffee/baristaeditionscrema_jacobs_02.html)
- sas.am: штрихкода и состава в HTML не найдено — [страница](https://www.sas.am/catalog/_legumes/)
- napolke.ru (B2B-маркетплейс): `productData{uuid, name, brand_name, manufacturer_display_name, attributes{country, weight, expiration}, description}`; штрихкода, состава и КБЖУ нет — [карточка](https://napolke.ru/catalog/product/kreker_tuc_so_smetanoj_i_lukom_100_gr_flou_pak-e081f86e-edf7-428a-8b7c-3c5881b1f735)
- zdravcity.ru: в данных карточки есть ключ `gtin`, но он `null` / `""` в обеих проверенных карточках (перчатки, БАД «ВитаМишки») — [карточка 1](https://zdravcity.ru/p_perchatki-smotrovye-nitrilovye-sinie-r-m-bmnftb003-0192824.html), [карточка 2](https://zdravcity.ru/p_1x-vitamishki-immuno-pastilki-zhevatelnye-2500mg-60sht-1x-vitamishki-smart-fruits-kalcij-vitamin-d-pastilki-zhevatelnye-30sht-0280255.html)
- gorzdrav.org: у товара в `__NUXT_DATA__` есть ключ `barcodes`, но на проверенной карточке это пустой массив; состав лежит в атрибуте `ingredients` — [карточка](https://gorzdrav.org/p/akva-maris-norm-in-pr-sprej-d-nosa-150ml-207904/)

#### Нет веб-каталога товаров (только промо, адреса, приложение)
- sosedi.by — в sitemap только новости и «ProGrill» — [sitemap](https://sosedi.by/sitemap.xml); korona.by — 589 URL про ТЦ и гипермаркеты — [sitemap](https://korona.by/sitemap.xml); prostore.by — [главная](https://www.prostore.by/)
- magnum.kz — Nuxt-сайт с акциями и рецептами, в бандле нет `barcode`/`gtin` — [главная](https://magnum.kz/), [бандл](https://magnum.kz/_nuxt/afe569f.js); airbafresh.kz — лендинг приложения — [главная](https://airbafresh.kz/)
- sm-komandor.ru, maria-ra.ru, remi.ru (только промо-каталоги), krasyar.ru (листовки), bahetle.com (только собственная продукция), dixy.ru, verno-info.ru — на главных нет ссылок на товарный каталог — [Командор](https://sm-komandor.ru/), [Мария-Ра](https://www.maria-ra.ru/), [Реми](https://remi.ru/), [Красный Яр](https://www.krasyar.ru/), [Бахетле](https://bahetle.com/products/), [Дикси](https://dixy.ru/), [Верный](https://www.verno-info.ru/)
- 4fresh.ru — теперь страница бренда со ссылками на Wildberries и Глобус, собственного магазина нет — [главная](https://4fresh.ru/)
- supl.biz, agroserver.ru — доски объявлений/каталоги компаний, не карточки товаров со штрихкодами — [supl.biz sitemap](https://supl.biz/sitemap.xml), [agroserver sitemap](https://agroserver.ru/sitemap/sitemap.xml)

#### Z. Антибот-проверка или блок (вендор и статус; дальше не ходили)
- edostavka.by: главная → 200, страница «Verification» с JS, выставляющим cookie `hg-security` и перезагружающим страницу; `sitemap.xml` → 403 «Запрос заблокирован. Доступ к ресурсу ограничен. IP: 185.229.207.38»; сервер ставит cookie `hg-client-security` — [главная](https://edostavka.by/), [sitemap](https://edostavka.by/sitemap.xml). То же на emall.by (главная 403, sitemap 200 «Verification») — [emall.by](https://emall.by/)
- `api2.edostavka.by/robots.txt` → 200, `User-agent: * / Disallow:` (всё разрешено). Запросы к самому API **не делались**, чтобы не обходить проверку на основном сайте — [robots.txt](https://api2.edostavka.by/robots.txt)
- Сторонний открытый парсер (README от 29.07.2026): edostavka.by — 11 425 товаров и 11 332 состава через `__NEXT_DATA__` (`props.pageProps.listing.products`, `?page=N`, состав из JSON-LD `description`) с помощью Playwright; в его формате данных штрихкода нет (`url, name, price, composition, weight, image, category, brand`) — [abmwm4-byte/edostavka_parser](https://github.com/abmwm4-byte/edostavka_parser)
- av.ru: 450 на robots/sitemap, главная — страница ServicePipe — [av.ru](https://av.ru/). Тот же сторонний README утверждает: ServicePipe гео-блокирует не-RU IP (HTTP 450), а в карточке `/i/{code}/` есть состав (`productComposition`) и КБЖУ (`protein/fats/carbo/energyValue`); про штрихкод там ничего не сказано — [abmwm4-byte/edostavka_parser](https://github.com/abmwm4-byte/edostavka_parser)
- myspar.ru: 403, `Server: Variti/0.9.3a`, тело — JSON с `request_id` и IP — [myspar.ru](https://myspar.ru/)
- monetka.ru, bristol.ru, planetazdorovo.ru: 401, страница со скриптом `/__qrator/qauth.js` — [Монетка](https://www.monetka.ru/), [Бристоль](https://bristol.ru/), [Планета здоровья](https://planetazdorovo.ru/)
- chizhik.club, onlinetrade.ru, megamarket.ru: 200 с заглушкой ServicePipe (1,8 КБ) — [Чижик](https://chizhik.club/), [Онлайнтрейд](https://www.onlinetrade.ru/), [Мегамаркет](https://megamarket.ru/)
- apteka.ru: sitemap открыт (`sitemap-product.xml` — 36 410 URL), но карточки → 432 «С вашего IP замечена подозрительная активность» — [sitemap](https://apteka.ru/sitemap-product.xml), [карточка](https://apteka.ru/product/bio-oil-maslo-dlya-uxoda-za-kozhej-200-ml-5e32788cca7bdc0001934bf7/)
- eapteka.ru: 403 на всё — [eapteka.ru](https://www.eapteka.ru/); officemag.ru: карточки → «Проверка безопасности» — [карточка](https://www.officemag.ru/catalog/goods/237951/); krasnoeibeloe.ru: карточка → 403 «Проверка безопасности» — [карточка](https://krasnoeibeloe.ru/catalog/energetiki_kokteyli/energeticheskie_napitki/toniziruyushchiy_napitok_energiya_volta_yabloko_kryzhovnik/); komus.ru: 503 (ngenix) — [komus.ru](https://www.komus.ru/); optlist.ru: «Проверяем ваше соединение» — [optlist.ru](https://optlist.ru/)
- small.kz и carrefour.am: Cloudflare «Just a moment…» (403) — [small.kz](https://small.kz/), [carrefour.am](https://www.carrefour.am/); yamigom-store.by: 403 Access denied — [yamigom-store.by](https://yamigom-store.by/)
- selgros.ru, semya.ru, spar-online.ru: TLS-соединение рвётся (`SSL_ERROR_SYSCALL`) — [selgros.ru](https://www.selgros.ru/), [semya.ru](https://semya.ru/), [spar-online.ru](https://spar-online.ru/)
- Не ответили за таймаут: akusherstvo.ru, gulliver-um.ru, clevermarket.kz, jmart.kz, interfood.kz, frunze.kg, rigla.ru; victoria-group.ru → 504 — [akusherstvo.ru](https://www.akusherstvo.ru/), [victoria-group.ru](https://victoria-group.ru/)

### Inferences
- Штрихкод в публичных данных — исключение, а не правило: из 23 площадок с открывшимся товарным каталогом EAN отдают 9 (одна из них — только через имя файла фото), и только 5 — вместе с составом. Региональные сети РФ на типовых платформах (Bitrix-магазины, KDV-платформа «Ярче», собственные Nuxt/Next-витрины) держат внутренний артикул, а не EAN.
- У arbuz.kz штрихкод попадает в HTML как побочный эффект сериализации сырой записи БД (рядом лежат `profit_percent`, `supplier_id`). Это похоже на утечку, а не на задуманное поле, значит источник хрупкий: поле могут убрать без предупреждения. Его стоит выкачать первым.
- «Российская релевантность» шире, чем префикс 460–469: всё, что продаёт detmir.ru и fix-price.com, продаётся в РФ независимо от префикса; у белорусских магазинов значимая часть товаров с префиксом 481 (молочка, кондитерка, снеки) экспортируется в РФ с тем же EAN; у arbuz.kz к 40% российских добавляется европейский импорт (в выборке 21% — Италия, но выборка смещена разделом макарон). Но поле страны и префикс расходятся (пример President), поэтому фильтровать надо по совпадению EAN с собственной базой, а не по стране.
- green-dostavka.by формально запрещает в robots.txt URL с `?storeId=`, но разрешает HTML-карточки с теми же данными; gippo-market.by запрещает `*?*` на домене витрины, а API живёт на другом хосте. Юридическую оценку этого я не делал — это наблюдение для того, кто будет решать, как именно обходить каталог.
- Блоки у edostavka.by, av.ru, selgros.ru, myspar.ru могут быть следствием немецкого датацентрового IP; с российского IP картина может отличаться (про av.ru сторонний источник прямо говорит о гео-блоке не-RU адресов).

### Gaps
- edostavka.by / emall.by: есть ли в `__NEXT_DATA__` штрихкод — не проверено (JS-challenge). Это крупнейший каталог Беларуси; сторонний парсер штрихкод не собирал.
- av.ru, myspar.ru, monetka.ru, selgros.ru, semya.ru, spar-online.ru, chizhik.club, apteka.ru, eapteka.ru, komus.ru, officemag.ru, akusherstvo.ru — наличие EAN не проверено (блок/недоступность с нашей точки).
- Региональные сайты SPAR, Командор-онлайн, Гулливер, «Близкий», Табрис (карточки товаров не найдены, только листинг `/pokupatelyam/tovary/`), Гипербола, igooods.ru, galmart.kz (SPA, API не исследован) — не проверено.
- Точный размер продуктового каталога arbuz.kz и 5lb.ru не измерен (у arbuz — оценка по границам пагинации 7 из ~16 разделов; у 5lb карточек нет в sitemap).
- Доля российских товаров в food-части green-dostavka.by измерена на 10 карточках — слишком мало для надёжной цифры.
- Покрытие составом у detmir.ru измерено на 5 съедобных карточках, у fix-price.com — на 2; это ориентиры, а не статистика.
- yerevan-city.am: получить русские названия не удалось; есть ли отдельный endpoint с составом — не проверено.

## Вопрос 2. Принимает ли поиск на сайте EAN (включая тестовые EAN)?

### Takeaway
Поиск по штрихкоду подтверждён на трёх площадках: **detmir.ru** (нашёл тестовый кефир «Агуша» 4602541000028), **green-dostavka.by** (находит по своему gtin, но трёх тестовых российских EAN в ассортименте нет) и **5lb.ru** (быстрый поиск возвращает JSON с `barcode`). На arbuz.kz, gippo и fix-price проверить не удалось — поиск там клиентский.

### Cited Findings
- detmir.ru: `/search/results/?qt=4602541000028` → 200, в выдаче «Кефир Агуша 3.2% 0.200л с 8месяцев» с `"bar_codes":["4602541000028"]` — [поиск](https://www.detmir.ru/search/results/?qt=4602541000028)
- detmir.ru: `qt=4600209012802` → 1 результат (Nutrilon Premium 2); `qt=4601662000016` (молоко Parmalat) → пусто — [поиск Nutrilon](https://www.detmir.ru/search/results/?qt=4600209012802), [поиск Parmalat](https://www.detmir.ru/search/results/?qt=4601662000016)
- detmir.ru: путь `/search/results/` запрещён в robots.txt — [robots.txt](https://www.detmir.ru/robots.txt)
- green-dostavka.by: `/api/v1/products/search/?storeId=2&search=4815101004606` → 1 товар (чипсы Онега), т. е. поиск по gtin работает — [поиск](https://green-dostavka.by/api/v1/products/search/?storeId=2&search=4815101004606&limit=20&skip=0)
- green-dostavka.by: тестовые 4601780000189 (Makfa), 4690388000158 (Cheetos), 4602541000028 (Агуша) → `count: 0` — [Makfa](https://green-dostavka.by/api/v1/products/search/?storeId=2&search=4601780000189&limit=20&skip=0), [Cheetos](https://green-dostavka.by/api/v1/products/search/?storeId=2&search=4690388000158&limit=5&skip=0), [Агуша](https://green-dostavka.by/api/v1/products/search/?storeId=2&search=4602541000028&limit=5&skip=0)
- green-dostavka.by: `/search/` запрещён в robots.txt — [robots.txt](https://green-dostavka.by/robots.txt)
- 5lb.ru: `…&product_string=4660298500703` → JSON-массив товаров Bombbar с полем `barcode`; на сайте есть встроенный сканер штрихкода, ведущий на `/search/?product_string={barcode}` — [поиск по EAN](https://5lb.ru/search/?jssearch=enabled&mime=json&show=489395&product_string=4660298500703), [5lb.js](https://5lb.ru/i/js/5lb.js?v=1.185)
- fix-price.com: `/search?q=4610003252809` → 200, но SSR-страница результатов не содержит товаров (поиск рендерится на клиенте) — [поиск](https://fix-price.com/search?q=4610003252809)
- arbuz.kz: `/ru/almaty/search?q=…` → 404; форма поиска ведёт на `/ru/almaty/search/show#/` (клиентский рендер через `/api/`, который закрыт robots.txt) — [проба](https://arbuz.kz/ru/almaty/search?q=4601780010775)
- gippo (app.willesden.by): параметры `filter[search]=` и `filter[barcode]=` сервер игнорирует (возвращает полный список, total 14307) — [проба](https://app.willesden.by/api/guest/shop/products?market_id=73&page=1&per_page=20&filter%5Bbarcode%5D=4690228033056)

### Inferences
- Для gippo поиск по EAN не нужен: каталог целиком (144 страницы по 100) отсортирован по штрихкоду и выкачивается за ~3 минуты.
- Для arbuz.kz поиск по EAN не нужен по той же причине: адрес карточки строится от внутреннего id, поэтому единственный путь — полный обход категорий.
- На detmir.ru и green листинг уже содержит или позволяет получить все EAN, так что точечный поиск по EAN полезен только для проверки, а не для сбора; к тому же оба пути поиска закрыты в robots.txt.
- Из 10 тестовых EAN найден один (Агуша на detmir.ru). Остальные девять — массовая бакалея/напитки, которой нет ни в детском магазине, ни в белорусском Green; на arbuz.kz их наличие осталось непроверенным. Тест показывает скорее узость ассортимента найденных источников, чем неработающий поиск.

### Gaps
- Поиск по EAN на arbuz.kz, fix-price.com, yerevan-city.am, sima-land.ru — не проверено.
- Остальные 7 тестовых EAN на green и 8 на detmir.ru не прогонялись (лимит запросов на хост).
- Настоящее имя параметра поиска в API gippo не найдено (лежит в ленивых чанках Angular, которые не разбирались).

## Вопрос 3. Какие 3–5 источников дают лучший компромисс объём × наличие EAN × простота, и сколько российских EAN с составом они дадут вместе?

### Takeaway
Лучшая пятёрка — **detmir.ru, arbuz.kz, green-dostavka.by, gippo (app.willesden.by), fix-price.com**: вместе это порядка 34 тыс. карточек «EAN + состав» и, по грубой оценке, **8,5–10 тыс. уникальных EAN с префиксом 46 и составом** — сопоставимо с имеющимися ~11 тыс. строк с составом, но не кратный прирост. Крупнейший потенциальный источник региона, edostavka.by/emall.by, остался непроверенным.

### Cited Findings
- detmir.ru: 14 683 товара в наличии в «Питание и кормление», штрихкоды у 36/36 на странице, префикс 46 у 11/33, 22/36 и 30/36 на трёх страницах; состав у 4 из 5 съедобных карточек выборки — [листинг](https://www.detmir.ru/catalog/index/name/nutrition_feeding/), [стр. 50](https://www.detmir.ru/catalog/index/name/nutrition_feeding/?page=50), [пюре](https://www.detmir.ru/catalog/index/name/pure/)
- arbuz.kz: замеренные 7 продуктовых разделов дают ≈6,4 тыс. товаров (1 171 + 1 600…2 000 + 1 200…1 800 + 478 + 579 + <480 + <800); страна «Россия» у 55 из 139; состав у 133 из 139; штрихкод в 10 из 10 карточек — [Кондитерские p30](https://arbuz.kz/ru/almaty/catalog/cat/225166-konditerskie_izdeliya?page=30), [Бакалея p40](https://arbuz.kz/ru/almaty/catalog/cat/225169-bakaleya?page=40), [карточка](https://arbuz.kz/ru/almaty/catalog/item/176799-makarony_makfa_shpinatnye_500_g)
- green-dostavka.by: 19 771 карточка, gtin у 22/22, food 10/22, состав и КБЖУ у 10/10 food, префикс 46 у 1 из 10 food и у 6 из 22 всего — [листинг API](https://green-dostavka.by/api/v1/products?storeId=2&limit=100&skip=0), [sitemap](https://green-dostavka.by/sub-sitemaps/sitemap-0.xml)
- gippo: 14 307 карточек, штрихкод у 600/600, префикс 46 у 114/600, среди них состав или КБЖУ у 59 — [листинг](https://app.willesden.by/api/guest/shop/products?market_id=73&page=60&per_page=100)
- fix-price.com: 1 150 продуктовых карточек; в обеих проверенных — EAN с префиксом 46, состав и структурное КБЖУ — [категория](https://fix-price.com/catalog/produkty-i-napitki), [карточка](https://fix-price.com/catalog/produkty-i-napitki/konditerskie-izdeliya/p-1950476-pechene-myusli-lyubyatovo-s-klyukvoy-i-izyumom-120-g)
- Стоимость обхода: gippo — 144 запроса на весь каталог (per_page=100); green — деталь 2,5 КБ JSON на товар либо HTML-карточка 143 КБ gzip; arbuz — карточка 22 КБ gzip; detmir — карточка 124 КБ gzip, листинг ~200 КБ gzip; fix-price — карточка 112 КБ gzip — [gippo](https://app.willesden.by/api/guest/shop/products?market_id=73&page=1&per_page=20), [green](https://green-dostavka.by/api/v1/products/378123400?storeId=2), [arbuz](https://arbuz.kz/ru/almaty/catalog/item/176799-makarony_makfa_shpinatnye_500_g), [detmir](https://www.detmir.ru/product/index/id/3168637/), [fix-price](https://fix-price.com/catalog/produkty-i-napitki/konditerskie-izdeliya/p-1950476-pechene-myusli-lyubyatovo-s-klyukvoy-i-izyumom-120-g)

### Inferences
Все цифры ниже — мои оценки из малых выборок; порядок величины, не точность.

| Источник | Карточек с EAN (food/БАД) | из них с составом | EAN с префиксом 46 и составом | Запросов на полный обход | Как считал |
|---|---|---|---|---|---|
| detmir.ru | ~10 тыс. (14 683 × ~70% съедобных) | ~8 тыс. (80%) | ~5 тыс. (60% × 8 тыс.) | ~410 листингов + ~10 тыс. карточек | 5 из 7 карточек выборки съедобные; префикс 46 в среднем ~60% по трём страницам |
| arbuz.kz | ~10–12 тыс. | ~10 тыс. (96%) | ~4–4,5 тыс. (40%) | ~300 листингов + ~11 тыс. карточек | 7 замеренных разделов ≈6,4 тыс.; ещё ~9 разделов по 300–800 |
| green-dostavka.by | ~9 тыс. food (45% от 19,8 тыс.) | ~9 тыс. | ~1–2,5 тыс. (очень неуверенно) | ~19,8 тыс. деталей (или фильтр по категориям → ~9 тыс.) | 1 из 10 food с префиксом 46; интервал широкий |
| gippo | 14,3 тыс. (все, включая non-food) | ~6,4 тыс. (45%) | ~1,0–1,4 тыс. (19% × 14,3 тыс. × 39–52%) | 144 | выборка 600 |
| fix-price.com | 1 150 | ~1,1 тыс. | ~0,8–1,0 тыс. | ~48 листингов + 1 150 карточек | доля 46 не измерена, 2 из 2 |
| **Итого (до дедупликации)** | **~45 тыс.** | **~34 тыс.** | **~12–14 тыс.** | **~43 тыс.** | |

- После дедупликации между источниками (популярные федеральные бренды повторяются; закладываю 20–35% пересечения) остаётся **~8,5–10 тыс. уникальных EAN с префиксом 46 и составом**. Пересечение с уже имеющимися ~11 тыс. строк с составом неизвестно; если оно 30–50%, чистый прирост — порядка 4–7 тыс. EAN.
- Если считать «продаётся в России» шире префикса (весь detmir.ru и fix-price.com, белорусский экспорт с префиксом 481, европейский импорт на arbuz.kz), релевантных карточек с составом будет заметно больше — ориентировочно 15–20 тыс., но проверить это можно только пересечением с собственной базой 1,35 млн EAN.
- Порядок по отдаче на единицу усилий: (1) gippo — 144 запроса дают 14,3 тыс. EAN с названием, брендом, страной, фото и частично составом/КБЖУ; (2) arbuz.kz — самый высокий процент заполнения состава и КБЖУ и самая высокая доля российских товаров, плюс риск, что поле уберут; (3) detmir.ru — единственный крупный российский магазин пятёрки, структурное КБЖУ, несколько EAN на карточку; (4) fix-price.com — мало, но чисто и 100% российский ассортимент; (5) green — много карточек с идеальным заполнением, но российских среди продуктов мало.
- При 1 запросе в секунду на хост и параллельной работе по пяти хостам полный обход укладывается примерно в 5–6 часов (узкое место — green, ~19,8 тыс. запросов).
- Источники категории C добавляют EAN без состава: yerevan-city.am (до 30 тыс. карточек с фото, названия на армянском), sima-land.ru (~1 тыс. российских EAN в продуктах), 5lb.ru (спортпит). Они полезны для пары «EAN → фото», но не решают дефицит состава.
- Ни один из найденных источников не закрывает массовую бакалею и напитки федеральных брендов в российском ассортименте: 9 из 10 тестовых EAN не нашлись. Региональные сети РФ, которые этот ассортимент продают, штрихкод не публикуют; для них остаётся сопоставление по названию (Ярче, Слата, Самбери, Макси дают состав и КБЖУ без EAN).

### Gaps
- edostavka.by / emall.by — если в их данных есть штрихкод, это был бы источник, сопоставимый со всей пятёркой вместе (сторонний парсер насчитал 11 425 товаров с составом только на edostavka). Проверить можно только из настоящего браузера или с другого IP; я этого не делал.
- av.ru, selgros.ru, myspar.ru и другие сети за Qrator/Variti/ServicePipe с российского IP не проверялись — вывод «региональные сети не публикуют EAN» опирается только на те, что открылись.
- Пересечение найденных EAN с имеющейся базой (1,35 млн EAN, ~11 тыс. с составом) не считалось — к базе проекта я не обращался.
- Оценки объёма не учитывают товары не в наличии: у detmir.ru `products_count` категории 67 066 против 14 683 в наличии; доступны ли карточки отсутствующих товаров — не проверено.
- Юридическая сторона (пользовательские соглашения, запреты в robots.txt на `?storeId=`, `/search/`, `*?*`) не оценивалась.
