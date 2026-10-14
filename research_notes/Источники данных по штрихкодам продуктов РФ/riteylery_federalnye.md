# Федеральные ритейлеры, маркетплейсы и q-commerce РФ: EAN + состав + КБЖУ в публичных данных (живые пробы, 13.10.2026)

**Как проверялось.** Все пробы — `curl`/`python3` с десктопным Chrome UA и `Accept-Language: ru-RU`, 13.10.2026 ≈16:50–17:45 UTC, ≥1 с между запросами, не более ~40 запросов на хост (Ашан — 44, см. ниже). Challenge/капчи не решались и не обходились. Часть проб (поиск Глобуса и Магнита, API Яндекс Еды) попала в пути, запрещённые robots.txt этих сайтов, — подробности в конце раздела 5.

**Главная оговорка.** И «прямое» соединение из WSL, и прокси `172.21.80.1:10809` выходят в интернет с **немецкого дата-центрового IP** (AS58212 dataforest GmbH; в блок-страницах сайтов светились 5.145.229.11 и 185.229.207.38) — [ipinfo.io/json](https://ipinfo.io/json). Несколько сайтов прямо отвечают «отключите VPN». Поэтому всё, что ниже помечено «блок», проверено **только с не-российского DC-IP**; поведение с российского резидентного IP — «не проверено».

## Сводная таблица

| Ритейлер | Карточка доступна без challenge | EAN (поле, пример) | Состав | КБЖУ | Перечисление каталога | Размер | Вердикт |
|---|---|---|---|---|---|---|---|
| **Глобус** (www.globus.ru, online.globus.ru → 301) | да, HTML 200 и `_next/data/*.json` 200 | **да**: `product.ean` = `"4607053473803"` | да: `attribute_groups[].items[id=atr_ru_ingredients_list]` | да: `food_energy{energy,protein,fat,carbohydrate}` | `sitemappdp1.xml` + `sitemappdp2.xml` | 47 874 карточки (все категории); молочка 3 364 | **A — брать первым** |
| **Ашан** (auchan.ru) | HTML главная — 401 Qrator; **JSON API `/v1`, `/v3` — 200 без challenge** | **да**: `mainEan` = `"4600494694813"` | да: `characteristics[title="Состав"]` | да: `energy_value{calories,proteins,fats,carbohydrates}` | `GET /v1/categories` → `POST /v1/catalog/products` (page/perPage) → `GET /v1/catalog/product-detail?code=` | 329 227 карточек всего / 40 025 активных; еда ≈102,7 тыс. / 18,7 тыс. активных | **A — самый большой источник EAN+состав** |
| **Fix Price** (fix-price.com, api.fix-price.com) | да, HTML 200 и JSON API 200 | **да**: `variants[].barcode` = `"4610030032405"` | да: `extraDescriptions[alias=composition]` | да: `nutritionalValueSeparated{energyValue,protein,fats,carbohydrates}` (бывают нули-заглушки) | `POST /buyer/v1/product/in/{category}` → `GET /buyer/v1/product/{id}` | 990 в «Продукты и напитки» | **A, но маленький** |
| Магнит (magnit.ru) | да (Qrator пропускает) | **нет** (только «Артикул»; перепроверено в Nuxt-payload и в `/webgate/v2`) | да | да | `/__sitemap__/products.xml` | 19 884 | B — только fuzzy по названию |
| Яндекс Лавка | да, HTML 200 | **нет** (`id`, `pigeonId`) | да («Полный состав») | да (`pfcTraits`) | `sitemap-catalog-1.xml` | 24 044 `/good/` | B — только fuzzy |
| Яндекс Еда (retail) | HTML — пустая SPA-оболочка; `POST /api/v2/menu/product` 200 (нужен заголовок `X-Device-Id`) | **нет** | у Перекрёстка — текстом в `description`; у Ленты/Глобуса/Метро/Магнита в выборке пусто | блок `energy_values` | `sitemap/sitemap-products-000…127.xml.gz` | ≈3,4 млн URL (оценка 128×27 тыс.), все ритейлеры и нон-фуд | B/C — обходной путь к карточкам Перекрёстка, без EAN |
| Пятёрочка (5ka.ru) | нет: Servicepipe JS-challenge; API 403 «VPN» | не проверено вживую; в снапшоте API 2025-11 поля нет (`plu`) | в снапшоте — `description`, `attributes` | в снапшоте — `nutrients` | не проверено (sitemap 403) | не проверено | C |
| Перекрёсток | нет: Servicepipe JS-challenge; API 403 «VPN» | не проверено вживую; в снапшоте API 2026-02 поля нет (`plu`) | в снапшоте — `features[key=sostav]` | не проверено | не проверено (sitemap 403) | не проверено | C (контент есть через Яндекс Еду) |
| Впрок (vprok.ru) | нет: главная и sitemap 200, `/catalog` и `/product` — 503 NGENIX JS-challenge | не проверено | не проверено | не проверено | `sku0.xml`, `sku1.xml` (доступны) | 27 551 SKU | C |
| Чижик (chizhik.club) | нет: Servicepipe JS-challenge; API 403 «VPN» | не проверено вживую; в снапшоте API 2026-03 поля нет (`plu`) | в снапшоте — `meta_data[code=composition]` | в снапшоте — `proteins/fats/carboh/energy_value` | не проверено | не проверено | C |
| Лента (lenta.com, online.lenta.com, api.lenta.com) | нет: 401 Qrator JS (`/__qrator/qauth.js`) | не проверено | не проверено | не проверено | не проверено (sitemap.xml 404) | не проверено | C |
| О'КЕЙ (okeydostavka.ru) | нет: Servicepipe JS-challenge; robots/sitemap — 307 на себя | не проверено | не проверено | не проверено | не проверено | не проверено | C |
| Дикси (dixy.ru) | оболочка каталога 200 (Qrator пропускает), товары — `/ajax/listing-json.php` → 403 | не проверено | не проверено | не проверено | sitemap без товаров (7 URL) | не проверено | C |
| Верный (verno-info.ru) | да, но каталога товаров нет («Каталог акций») | — | — | — | — | — | D — нечего брать |
| Светофор (svetoforonline.ru) | да | нет (только «Артикул») | вкладка «Состав» пустая | нет | — | не проверено | D — данные устарели (2021) |
| Азбука вкуса (av.ru) | нет: Servicepipe JS-challenge; прочие пути 450 «Кажется, вы используете VPN» | не проверено | не проверено | не проверено | не проверено | не проверено | C |
| Самокат | нет: Servicepipe JS-challenge; robots и api.samokat.ru — 403 | не проверено | не проверено | не проверено | не проверено | не проверено | C |
| Яндекс Маркет | нет: 302 → `/showcaptcha` (Yandex SmartCaptcha) | не проверено | не проверено | не проверено | не проверено | не проверено | C |
| Мегамаркет | нет: Servicepipe JS-challenge; API — JSON-ошибка «отключите VPN» | не проверено | не проверено | не проверено | не проверено | не проверено | C |
| Ozon | нет: 307-цикл `?__rr=N` (собственный антибот) — известно команде | известно: иногда в характеристиках | — | — | — | — | C (точечный gap-fill) |
| Красное&Белое | нет: главная/sitemap 200, `/catalog/*` — 403 «Проверка безопасности» (JS `/bp_chl.js`) | не проверено | не проверено | не проверено | `sitemap-iblock-9.xml` (доступен) | 3 230 URL | C |
| ВинЛаб (winelab.ru) | нет: главная/sitemap 200, `/catalog` и `/product` — 401 Qrator | не проверено | не проверено | не проверено | `sitemap.xml` (доступен) | 2 752 товара | C |
| Бристоль (bristol.ru) | нет: 401 Qrator | не проверено | не проверено | не проверено | sitemap.xml 404 | не проверено | C |
| SimpleWine | нет: Servicepipe JS-challenge; sitemap 403 | не проверено | не проверено | не проверено | не проверено | не проверено | C |
| Metro / Wildberries / ВкусВилл / Купер / Едадил | известно команде, не перепроверялось | Metro, WB — да; ВкусВилл, Едадил — нет; Купер — блок Servicepipe | — | — | — | — | — |

## 1. Кто отдаёт EAN в публичном HTML/JSON

### Takeaway
EAN вместе с составом и КБЖУ без challenge отдают три источника: **Глобус** (`ean` в `__NEXT_DATA__`), **Ашан** (`mainEan` в JSON API `/v1/catalog/product-detail`) и **Fix Price** (`variants[].barcode`). У Магнита, Яндекс Лавки и Яндекс Еды EAN в публичных данных нет; у остальных карточка с этого IP недоступна, наличие EAN не проверено.

### Cited Findings

#### Глобус — EAN есть (подтверждено)
- `https://online.globus.ru/` отвечает 301 → `https://www.globus.ru/` (200, Next.js, `__NEXT_DATA__`); robots.txt у обоих хостов одинаковый — [online.globus.ru](https://online.globus.ru/), [robots.txt](https://www.globus.ru/robots.txt)
- Карточка `https://www.globus.ru/products/kefir-prostokvashino-32-930g-27692_ST` → 200, 150 КБ. В `__NEXT_DATA__.props.pageProps.dehydratedState.queries[queryKey[0]="product-detail"].state.data.data.product` лежит: `"ean": "4607053473803"`, `"vendor_code": "27692004"`, `"food_energy": {"energy":"57","protein":"3","fat":"3.2","carbohydrate":"4"}`, `attribute_groups[].items[]` с `{"id":"atr_ru_ingredients_list","name":"Состав","value":["молоко нормализованное, закваска на кефирных грибках"]}`, `brand.name`, `images[].url` (`https://image.globus.ru/web/27/63/4682763.jpg`) — [карточка](https://www.globus.ru/products/kefir-prostokvashino-32-930g-27692_ST)
- В видимом HTML подписи «Штрихкод» нет — EAN присутствует только в JSON (одно вхождение `"ean"` на страницу) — [карточка](https://www.globus.ru/products/kefir-prostokvashino-32-930g-27692_ST)
- Тот же JSON без HTML-обвязки отдаёт Next data-route: `https://www.globus.ru/_next/data/xHjjyjcDP1TmgZmG36ihW/products/kefir-prostokvashino-32-930g-27692_ST.json` → 200, `application/json`, 58 КБ, содержит `"ean":"4607053473803"`. `buildId` (`xHjjyjcDP1TmgZmG36ihW`) берётся из `__NEXT_DATA__.buildId` любой страницы — [_next/data](https://www.globus.ru/_next/data/xHjjyjcDP1TmgZmG36ihW/products/kefir-prostokvashino-32-930g-27692_ST.json)
- Бэкенд фронта — `runtimeConfig.browserAPIHost = "https://digitalone.globus.ru/d1-front-bff"` (напрямую не запрашивался) — [главная](https://www.globus.ru/)
- В списке товаров категории (`catalog-product-list`) поля `ean` **нет** (ключи: `id`, `name_optional`, `name_required`, `main_category_id`, `url`, цены…), а в списке результатов поиска (`catalog-search-result`) `ean` **есть** — [категория](https://www.globus.ru/catalog/molochnye-produkty-syr-yajcza-10118965), [поиск](https://www.globus.ru/search?q=4607053473803)
- За 31 запрос к www.globus.ru challenge/403/429 не встретились; в конфиге страницы есть ключ reCAPTCHA (`reCaptchaSiteKey`), на карточках он не срабатывал — [главная](https://www.globus.ru/)

#### Ашан — EAN есть в JSON API
- `https://www.auchan.ru/` → 401, `server: QRATOR`, тело — `<script src="/__qrator/qauth.js">` (HTML закрыт JS-challenge) — [auchan.ru](https://www.auchan.ru/)
- При этом `GET https://www.auchan.ru/v1/categories?merchant_id=1` → 200 `application/json` (97 КБ, `server: QRATOR`, без challenge): дерево категорий с `id, name, code, productsCount, activeProductsCount, items[]` — [categories](https://www.auchan.ru/v1/categories?merchant_id=1)
- `POST https://www.auchan.ru/v1/catalog/products?merchantId=1&page=1&perPage=40`, тело `{"filter":{"category":"bakaleya","promo_only":false,"active_only":false,"cashback_only":false}}` → 200: `{"items":[…], "range":11512, "activeRange":2966, "minPrice":…, "maxPrice":…}`; у элемента списка есть `id, productId, code, title, brand, gimaId, mediaUrls, categoryCodes`, поля `mainEan` в списке **нет** — [catalog/products](https://www.auchan.ru/v1/catalog/products?merchantId=1&page=1&perPage=40)
- `GET https://www.auchan.ru/v1/catalog/product-detail?code=sok-j-7-apelsin-s-myakotyu-ohlazhdennyy-850-ml&merchantId=1` → 200, 7,9 КБ: `"mainEan": "4600494694813"`, `"gimaId": "522199"`, `"energy_value": {"calories":45,"proteins":0.7,"fats":null,"carbohydrates":11}`, `characteristics[]` с `{"title":"Состав","value":"Яблочный сок, антиокислитель: аскорбиновая кислота. Изготовлен из концентрированного сока."}`, «Производитель», «Страна производства», «Масса нетто, кг», `mediaUrls[]` (`https://www.auchan.ru/files/original/38252385`) — [product-detail](https://www.auchan.ru/v1/catalog/product-detail?code=sok-j-7-apelsin-s-myakotyu-ohlazhdennyy-850-ml&merchantId=1)
- Качество данных: у этой же карточки «Сок J7 Апельсин с мякотью» в «Составе» записан «Яблочный сок…» — состав на карточках бывает ошибочным — [product-detail](https://www.auchan.ru/v1/catalog/product-detail?code=sok-j-7-apelsin-s-myakotyu-ohlazhdennyy-850-ml&merchantId=1)
- У весовых товаров `mainEan` — внутренний весовой код, а не GTIN производителя: «Колбаса вареная «Россиянка» Ароматная, ~2,7 кг» → `2527933000009`, «Колбаса варено-копченая «Белорусская традиция»» → `2500576000001` — [product-detail](https://www.auchan.ru/v1/catalog/product-detail?code=sok-j-7-apelsin-s-myakotyu-ohlazhdennyy-850-ml&merchantId=1) (тот же endpoint, другие `code`)
- Всего к auchan.ru сделано 44 запроса (лимит ~40 превышен на 4 ради теста EAN-поиска); один запрос списка вернул не-200 (статус не зафиксирован), повтор прошёл; 429 не было — [catalog/products](https://www.auchan.ru/v1/catalog/products?merchantId=1&page=1&perPage=40)
- Независимое подтверждение, что API Ашана открыт без авторизации (REST `/v3/…`, поиск `/v3/autohints/?merchantId=…&query=…&channel=W`): recon-заметки проекта zakupator, июль 2026 — [TheZavitaev/zakupator docs/recon.md](https://github.com/TheZavitaev/zakupator/blob/HEAD/docs/recon.md)

#### Fix Price — EAN есть
- Карточка `https://fix-price.com/catalog/produkty-i-napitki/p-1001076-moloko-ultrapasterizovannoe-slavyanskoe-krujevo-32-973-ml` → 200 (Nuxt 2, `window.__NUXT__`): в payload `variants:[{id:102434,…,barcode:"4610030032405",…}]`, `extraDescriptions:[{alias:"composition",value:"молоко цельное, молоко обезжиренное",title:"Состав"},{alias:"nutritionalValue",value:"Пищевая ценность на 100г. Продукта: белки 3г.; жиры 3.2г.; углеводы 4.7г. Энергетическая ценность: 64 ккал."},{alias:"nutritionalValueSeparated",value:{energyValue:"64",protein:…,fats:"3.2",carbohydrates:"4.7"}}]` — [карточка](https://fix-price.com/catalog/produkty-i-napitki/p-1001076-moloko-ultrapasterizovannoe-slavyanskoe-krujevo-32-973-ml)
- То же чистым JSON: `GET https://api.fix-price.com/buyer/v1/product/1001076` → 200, 1,5 КБ (gzip): ключи `id, title, sku, category, description, images[], properties[], extraDescriptions[], variants[] (barcode, width/height/length/weight), brand, url` — [api product](https://api.fix-price.com/buyer/v1/product/1001076)
- У варианта может быть несколько кодов и внутренние артикулы вперемешку: «Чай чёрный байховый Daily Joy 150 г» → `['4627151900353','4627151900513','1720074']`; встречаются EAN-8: Orbit → `46196613` — [api product](https://api.fix-price.com/buyer/v1/product/1001076) (тот же endpoint, другие id)
- Наличие `barcode` в ответе карточки подтверждается и снапшотом тестов неофициального клиента — [Open-Inflation/fixprice_api tests/__snapshots__/ProductService.info.json](https://github.com/Open-Inflation/fixprice_api/blob/HEAD/tests/__snapshots__/ProductService.info.json)
- На страницах и в API challenge не встретился (≈23 запроса); на сайте подключён скрипт Cloudflare Turnstile (`challenges.cloudflare.com/turnstile/v0/api.js`), на карточках не срабатывал — [карточка](https://fix-price.com/catalog/produkty-i-napitki/p-1001076-moloko-ultrapasterizovannoe-slavyanskoe-krujevo-32-973-ml)

#### Магнит — EAN нет (перепроверено)
- Карточка `https://magnit.ru/product/1000000732-korovka_iz_korenovki_moloko_sgushch_gost_8_5_d_p_270g_kmkk_24` → 200 (`server: QRATOR`, `x-powered-by: Nuxt`). В `__NUXT_DATA__` объект `goods-detail:1000000732:992301:dostavka:3` содержит `details[]`: `{"name":"На 100 г","type":"nutritionFactsType","parameters":[Ккал 330, Белки 8.5, Жиры 7, Углеводы 56]}`, `{"name":"Состав","type":"stringType","value":"Молоко цельное, обезжиренное молоко, сахар (сахароза)"}`, «Характеристики» (Бренд, Производитель, Вес, **Артикул 1000000732**), «Документы» (`fsaCertificateType` → `https://pub.fsa.gov.ru/rds/declaration/view/17385699`). Ключей `ean/gtin/barcode` в payload нет; два 13-значных числа на странице — фрагменты хешей URL картинок — [карточка](https://magnit.ru/product/1000000732-korovka_iz_korenovki_moloko_sgushch_gost_8_5_d_p_270g_kmkk_24)
- JSON API карточки открыт без токена: `GET https://magnit.ru/webgate/v2/goods/1000000732/stores/992301?storetype=6&catalogtype=1` → 200, 2,1 КБ; ключей `ean/gtin/barcode` нет — [webgate goods](https://magnit.ru/webgate/v2/goods/1000000732/stores/992301?storetype=6&catalogtype=1)
- В schema.org-разметке карточки `"sku":"1000000732"` — внутренний id; `gtin*` на странице не встречается — [карточка](https://magnit.ru/product/1000000732-korovka_iz_korenovki_moloko_sgushch_gost_8_5_d_p_270g_kmkk_24)

#### Яндекс Лавка — EAN нет
- `https://lavka.yandex.ru/good/hleb-kefirnyj-bratya-karavaevy-250-gram` → 200, 90 КБ gzip. В `<script id="storedehydratedstate-data">` → `products.regular[0]`: `id`, `pigeonId: "10134761"`, `longTitle`, `amount`, `brand`, `descriptionBlocks[]` (`"Полный состав"` → `"Мука пшеничная хлебопекарная высшего сорта, вода питьевая, масло подсолнечное…"`, плюс `aiIngredients` «Краткий состав»), `options.ingredients.pfcTraits[]` (`calories 250`, `protein 6,7`, `fat 1,1`, `carbohydrate 53` в `measures.per100g`), `imageUrlTemplates[]`. В ld+json `Product` нет `gtin*`; ключей `ean/gtin/barcode` нет — [карточка Лавки](https://lavka.yandex.ru/good/hleb-kefirnyj-bratya-karavaevy-250-gram)
- На 7 случайных карточках из sitemap объединённый набор ключей товара не содержит ничего похожего на штрихкод (`id, pigeonId, deepLink, title, longTitle, amount, brand, descriptionBlocks, options.ingredients, productTags, privateLabelBrand…`) — [sitemap-catalog-1.xml](https://lavka.yandex.ru/sitemap-catalog-1.xml)
- За 13 запросов к lavka.yandex.ru капча не показывалась; сторонний recon (июль 2026) сообщал о немедленном редиректе на SmartCaptcha для автоматизированного Chrome — [TheZavitaev/zakupator docs/recon.md](https://github.com/TheZavitaev/zakupator/blob/HEAD/docs/recon.md)

#### Яндекс Еда (retail) — EAN нет, но это открытый путь к карточкам Перекрёстка
- `https://eda.yandex.ru/retail/perekrestok/product/…/143b8143-ba4d-4861-bec7-b8920e82c708` → 200, но это пустая SPA-оболочка (`<div id="root">`, без title, без ld+json) — [страница товара](https://eda.yandex.ru/retail/perekrestok/product/file-seldi-atlanticheskoi-slabosolenoi-s-pripravami-v-masle-liudi-liub/143b8143-ba4d-4861-bec7-b8920e82c708)
- `POST https://eda.yandex.ru/api/v2/menu/product`, заголовок `X-Device-Id: <любая строка>` (без него 400 `Missing or empty 'X-Device-Id' header`), тело `{"place_slug":"perekrestok","product_public_id":"143b8143-…","with_categories":true,"location":{"latitude":55.7558,"longitude":37.6173}}` → 200: `menu_item{public_id, name, description, weight, picture.url, price}`, `detailed_data[]` (галерея, `energy_values`, `product_descriptions`), `place.brand_slug`. Пример `description`: «Срок годности в днях: 120\nСостав: Филе сельди, масло: подсолнечное… \nПищевая ценность: Калорийность: 160\nБелки: 10\nЖиры: 33\nУглеводы: 0\nСтрана изготовления: Республика Беларусь\nПроизводитель: Люди Любят». Ключей `ean/gtin/barcode` нет, 13-значных кодов в ответе нет — [api/v2/menu/product](https://eda.yandex.ru/api/v2/menu/product)
- `place_slug` = бренд из URL работает не для всех: `perekrestok`, `lenta`, `globus_new`, `metro_giper`, `magnit_semejnyj_celevaya` → 200; `paterocka`, `okej_new`, `asan_giper` → 404 `place_not_found`; `azbuka_vkusa`, `magnit_celevaya` → 404 `product_not_found` (для точки 55.7558, 37.6173) — [api/v2/menu/product](https://eda.yandex.ru/api/v2/menu/product)

#### X5 (Пятёрочка, Перекрёсток, Чижик) — вживую недоступно; по снапшотам API поля EAN нет
- Снапшот ответа карточки Пятёрочки (коммит 2025-11-16): ключи `plu, name, image_links, uom, prices, description, nutrients[] (белки/жиры/углеводы/ккал), attributes[]`; полей `ean/gtin/barcode` и 13-значных кодов нет — [Open-Inflation/pyaterochka_api ProductService.info.json](https://github.com/Open-Inflation/pyaterochka_api/blob/HEAD/tests/__snapshots__/ProductService.info.json)
- Снапшот карточки Перекрёстка (коммит 2026-02-24): `content.masterData.plu`, `content.title`, `content.features[].items[]` (в т.ч. `key: "sostav"`, title «Состав»), `content.images[]`; полей `ean/gtin/barcode` нет — [Open-Inflation/perekrestok_api ProductService.info.json](https://github.com/Open-Inflation/perekrestok_api/blob/HEAD/tests/endpoints/__snapshots__/ProductService.info.json)
- Снапшот карточки Чижика (коммит 2026-03-29): `id, plu, title, description, images[], meta_data[]` с `code`: `composition` («Состав»), `proteins`, `fats`, `carboh`, `energy_value`, `producer_name`, `brand_name`, `plu` («Артикул»); полей `ean/gtin/barcode` нет — [Open-Inflation/chizhik_api ProductService.info.json](https://github.com/Open-Inflation/chizhik_api/blob/HEAD/tests/__snapshots__/ProductService.info.json)

#### Светофор, Верный — нечего брать
- `https://svetoforonline.ru/bakaleya-i-drugie-produkti/gastronomiya/adzhika-po-kavkazski-360g.htm` → 200 (Apache, windows-1251): «Артикул: 0132033», «Актуально на: 2021-12-31», «Магазин… больше не работает», вкладки «Описание / Состав» пустые; EAN, состава и КБЖУ нет — [svetoforonline.ru](https://svetoforonline.ru/bakaleya-i-drugie-produkti/gastronomiya/adzhika-po-kavkazski-360g.htm)
- `https://www.verno-info.ru/products` → 200: раздел называется «Каталог акций», карточек товаров с составом нет (в HTML нет слов «состав», «штрих», `gtin`, `barcode`) — [verno-info.ru/products](https://www.verno-info.ru/products)

#### Уже известное команде (не перепроверялось)
- Metro (GraphQL, EAN + состав), Wildberries (EAN + состав), ВкусВилл (состав и КБЖУ, без EAN), Купер (Servicepipe; не запрашивался), Едадил (без EAN), Ozon (EAN иногда в характеристиках, антибот) — по вводным задачи; запросы к kuper.ru и rskrf.ru не отправлялись.

### Inferences
- Для задачи «EAN → состав» три источника (Глобус, Ашан, Fix Price) дают прямую связку без fuzzy-матчинга; Ашан — самый объёмный, Глобус — самый «чистый» по доступу (обычный SSR без антибота).
- У Ашана каталог включает ~290 тыс. неактивных карточек; если по ним тоже отдаётся `product-detail` с `mainEan` и составом (не проверялось), это исторический хвост ассортимента, которого нет у других.
- X5 во всех трёх сетях идентифицирует товар через `plu`; судя по снапшотам, даже при доступе через браузер EAN из их API не получить — карточки X5 годятся только для fuzzy-матчинга.
- Весовые коды Ашана с префиксами `25…`/`2…` нужно отфильтровывать: это не GTIN производителя.

### Gaps
- EAN у Ленты, О'КЕЙ, Дикси, Азбуки вкуса, Самоката, Яндекс Маркета, Мегамаркета, Впрока, К&Б, ВинЛаба, Бристоля, SimpleWine — не проверено: карточка с этого IP закрыта challenge/блоком.
- Снапшоты Open-Inflation — вторичный источник (1 товар на сеть, даты ноябрь 2025 – март 2026); вживую API X5 не наблюдался.
- В локальном `sources/perekrestok.py` команды поток описан как «…photo, brand, weight, barcode», но там же помечено UNVERIFIED; снапшот 2026-02 поле не подтверждает.

## 2. Принимает ли поиск по сайту EAN

### Takeaway
Поиск по EAN работает у Глобуса и Ашана (точные попадания 4/10 и 2/6 тестовых кодов соответственно) — это готовый «резолвер» EAN → карточка. У Магнита и Лавки поиск по EAN товар не находит. У Глобуса поиск нечёткий: возвращает и «похожие» штрихкоды, поэтому `ean` из ответа нужно сверять с запросом.

### Cited Findings
- **Глобус**: `GET https://www.globus.ru/search?q=<EAN>` → 200, результат в `__NEXT_DATA__` → `queries[queryKey[0]="catalog-search-result"].state.data.pages[0].data.products.items[]` (с полем `ean`). Контроль: `4607053473803` → «Кефир Простоквашино 3,2%, 930г» — [globus search](https://www.globus.ru/search?q=4607053473803)
- Глобус, 10 тестовых EAN: точное совпадение — `4601662000016` (Молоко Parmalat 3,5%, 1л), `4601576000027` (Майонез Провансаль ЕЖК 67%, 250мл), `4602541000028` (Кефир Агуша 3,2%, 200мл), `4601674000950` (Кетчуп томатный Пикадор, 500г); ложное «похожее»: `4606386000014` → Печенье Акульчев (`ean` 4604386002014), `4601727000036` → Водка Пять озёр (`ean` 4601728000936); пусто: `4690388000158`, `4601780000189`, `4603955000345`, `4680003503294` — [globus search](https://www.globus.ru/search?q=4601662000016)
- **Ашан**: `GET https://www.auchan.ru/v3/autohints/?merchantId=1&query=<EAN>&productsSize=5&channel=W` → 200 JSON `data.products[]{id,name,price,link_url,image_url}`. Контроль: `4607007234474` → «Корнишоны Federici с медом, 720 мл» (`link_url` `https://www.auchan.ru/product/kornishon-s-medom-720ml-federic/`) — [auchan autohints](https://www.auchan.ru/v3/autohints/?merchantId=1&query=4607007234474&productsSize=5&channel=W)
- Ашан, 6 тестовых EAN: найдено — `4601662000016` (Молоко Parmalat 3,5%, 1 л), `4602541000028` (Кефир детский «Агуша» 3,2%, 204 г); пусто — `4601780000189`, `4690388000158`, `4603955000345`, `4680003503294`. Остальные 4 кода не запрашивались (лимит запросов) — [auchan autohints](https://www.auchan.ru/v3/autohints/?merchantId=1&query=4601662000016&productsSize=5&channel=W)
- **Магнит**: `https://magnit.ru/search?term=4601780000189` → 200, текст «По запросу «4601780000189» не нашлось товаров»; `POST https://magnit.ru/webgate/v2/goods/search` с `{"term":"4601780000189",…,"storeCode":"992301","storeType":"6","catalogType":"1"}` → `pagination.totalCount: 0`; тот же endpoint с `"term":"макфа спагетти"` → `totalCount: 7` (первый — «Макароны Makfa Спагетти №16 Группа А 450г», id 1000425470) — [magnit search](https://magnit.ru/search?term=4601780000189), [webgate search](https://magnit.ru/webgate/v2/goods/search)
- **Яндекс Лавка**: `https://lavka.yandex.ru/search?text=4601662000016` → 200, запрос `Search` вернул только виджет `supermarket_products_suggest` («Ещё 740 товаров в большой Лавке»); Parmalat в выдаче нет — [lavka search](https://lavka.yandex.ru/search?text=4601662000016)
- **Яндекс Маркет**: `https://market.yandex.ru/search?text=4601780000189` → редирект на `/showcaptcha` — [market search](https://market.yandex.ru/search?text=4601780000189)
- **Ozon**: `https://www.ozon.ru/search/?text=4601780000189` → цикл 307 `?__rr=1…` — [ozon search](https://www.ozon.ru/search/?text=4601780000189)

### Inferences
- Доля попаданий 4/10 (Глобус) и 2/6 (Ашан) на «первых» кодах производителей — грубый ориентир покрытия; для EAN из реального ассортимента сетей она должна быть выше.
- Для 1,35 млн EAN обход поиском по одному коду (≥1 с на запрос) — это недели; дешевле один раз перечислить каталоги (≈48 тыс. + ≈100 тыс. карточек) и джойнить по EAN локально, а поиск оставить для точечного дозаполнения.
- Поиск Глобуса закрыт для роботов в robots.txt (`Disallow: /search*`), карточки и sitemap — нет; это ещё один довод в пользу перечисления каталога вместо поиска.

### Gaps
- Fix Price: endpoint поиска не найден (`/buyer/v1/search`, `/buyer/v1/product/search`, `/buyer/v1/search/product` → 400 «Page not found»); страница `/search` запрещена в robots.txt и не запрашивалась — не проверено. При 990 карточках поиск не нужен.
- Яндекс Еда, Впрок и все закрытые сайты — поиск по EAN не проверен.
- Лимиты частоты у поиска Ашана и Глобуса не измерялись.

## 3. Кто закрыт антиботом и каким

### Takeaway
С немецкого DC-IP без браузера недоступны: вся X5 (Servicepipe + IP-блок «VPN»), Впрок (NGENIX), Лента, Бристоль, ВинЛаб (Qrator JS), О'КЕЙ, Азбука вкуса, Самокат, Мегамаркет, SimpleWine (Servicepipe), Яндекс Маркет (SmartCaptcha), Ozon (собственный антибот), К&Б (JS-challenge неустановленного вендора). Qrator стоит и перед Магнитом, Ашаном, Дикси, но JSON/SSR там пропускает.

### Cited Findings
- **Пятёрочка**: `https://5ka.ru/` → 200, 1 КБ, заголовок `x-sp-crid`, тело — `<script src="https://servicepipe.tech/loaders/…js">` + `<js-challenge-loader>` (Servicepipe JS-challenge). `https://5d.5ka.ru/api/catalog/v2/stores/Y232/categories?mode=delivery`, `https://5ka.ru/api/v2/special_offers/`, `https://5ka.ru/sitemap.xml` → 403, страница «Проблемы со связью. Проверьте настройки интернета и VPN… IP: 5.145.229.11… Service_connect@x5.ru» — [5ka.ru](https://5ka.ru/), [5d.5ka.ru](https://5d.5ka.ru/api/catalog/v2/stores/Y232/categories?mode=delivery)
- **Перекрёсток**: главная и карточка `/cat/122/p/moloko-parmalat-…-3470` → 200, 1 КБ Servicepipe challenge; `/api/customer/1.4.1.0/catalog/product/plu3470` и `/sitemap.xml` → 403 та же страница «Проблемы со связью… VPN» — [perekrestok.ru](https://www.perekrestok.ru/), [API](https://www.perekrestok.ru/api/customer/1.4.1.0/catalog/product/plu3470)
- **Чижик**: `https://chizhik.club/` → Servicepipe challenge; `https://app.chizhik.club/api/v1/catalog/unauthorized/categories/` и `/sitemap.xml` → 403 «Проблемы со связью… VPN» — [chizhik.club](https://chizhik.club/), [app.chizhik.club](https://app.chizhik.club/api/v1/catalog/unauthorized/categories/)
- **Впрок**: `https://www.vprok.ru/` → 200 (Next.js), `robots.txt`, `sitemap.xml`, `sku0.xml`, `sku1.xml` → 200; `/catalog/1301/moloko-syr-yaytsa` и `/product/…--1361967` → 503 с cookie `ngenix_jscc_66dcf4=challenge_url=/js-challenge-validation-…` (NGENIX JS-challenge); `/web/api/v1/product/1361967` → 401 `{"error":{"code":"unauthorized"}}` — [vprok.ru](https://www.vprok.ru/), [категория](https://www.vprok.ru/catalog/1301/moloko-syr-yaytsa), [API](https://www.vprok.ru/web/api/v1/product/1361967)
- **Лента**: `https://lenta.com/`, `https://online.lenta.com/`, `https://lenta.com/api-gateway/v1/catalog/categories`, `https://api.lenta.com/v1/stores` → 401, `server: QRATOR`, `<script src="/__qrator/qauth.js">`; `https://lenta.com/sitemap.xml` → 404 — [lenta.com](https://lenta.com/), [api.lenta.com](https://api.lenta.com/v1/stores)
- **Ашан**: HTML главная 401 Qrator, JSON API 200 (см. раздел 1) — [auchan.ru](https://www.auchan.ru/)
- **Магнит**: `server: QRATOR`, но SSR-страницы, sitemap и `/webgate/v2/*` → 200 без challenge (9 запросов) — [magnit.ru](https://magnit.ru/)
- **О'КЕЙ**: `https://www.okeydostavka.ru/` → 200, 1 КБ Servicepipe challenge (`x-sp-crid`); `robots.txt` и `sitemap.xml` → бесконечный 307 на тот же URL — [okeydostavka.ru](https://www.okeydostavka.ru/)
- **Дикси**: `https://dixy.ru/`, `/catalog/`, `/catalog/gotovaya-eda/miratorg/` → 200 (`server: QRATOR`), но товары подгружаются через `/ajax/listing-json.php?block=product-list&sid=767` → 403 «Forbidden, Transaction ID: …»; сайт просит адрес доставки «чтобы видеть актуальную информацию по ассортименту»; `sitemap-files.xml` содержит 7 служебных URL без товаров — [dixy.ru catalog](https://dixy.ru/catalog/gotovaya-eda/miratorg/), [ajax](https://dixy.ru/ajax/listing-json.php?block=product-list&sid=767)
- **Азбука вкуса**: `https://av.ru/` → 200, 1 КБ Servicepipe challenge; `https://av.ru/api/v1/catalog`, `/sitemap.xml` → 450, страница «Кажется, вы используете VPN. Попробуйте отключить VPN и обновить страницу» — [av.ru](https://av.ru/)
- **Самокат**: `https://samokat.ru/` → Servicepipe challenge; `https://samokat.ru/robots.txt`, `https://api.samokat.ru/showcase/showcases` → 403 «Forbidden… If you are not a bot, please copy the report» — [samokat.ru](https://samokat.ru/)
- Самокат, вторичный источник: рабочий веб-API `api-web.samokat.ru/search/products` требует Bearer-JWT (TTL 300 с) и подпись запроса `x-creeper` — [TheZavitaev/zakupator docs/recon.md](https://github.com/TheZavitaev/zakupator/blob/HEAD/docs/recon.md)
- **Яндекс Маркет**: `https://market.yandex.ru/` → 302 на `https://market.yandex.ru/showcaptcha?…` (Yandex SmartCaptcha) — [market.yandex.ru](https://market.yandex.ru/)
- **Мегамаркет**: `https://megamarket.ru/` → 200, 1 КБ Servicepipe challenge (`x-sp-crid`); `POST /api/mobile/v1/catalogService/catalog/search` → 200 JSON `{"error":"Произошла ошибка. Попробуйте отключить VPN или подключиться к другой сети…","code":7}`; `robots.txt` → 307-цикл — [megamarket.ru](https://megamarket.ru/)
- **Ozon**: `https://www.ozon.ru/`, `/robots.txt`, `/search/?text=…` → цикл 307 `?__rr=1…9` — [ozon.ru](https://www.ozon.ru/)
- **Красное&Белое**: главная, `robots.txt`, `sitemap.xml`, `sitemap-iblock-9.xml` → 200 (nginx, `x-powered-by: PHP/8.3.8`); `/catalog/moloko_syry_yaytso/` и `/catalog/vino/vino_kyanti_rizerva_kr_p_sukh/` → 403, страница «Проверка безопасности» со скриптом `/bp_chl.js` (вендор не определён) — [категория К&Б](https://krasnoeibeloe.ru/catalog/moloko_syry_yaytso/)
- **ВинЛаб**: главная, `robots.txt`, `sitemap.xml` → 200 (`server: QRATOR`); `/catalog/gazirovannye-napitki`, `/product/1019959` → 401 `qauth.js` (дважды, двумя маршрутами) — [winelab product](https://www.winelab.ru/product/1019959)
- **Бристоль**: `https://bristol.ru/`, `/catalog/` → 401 Qrator `qauth.js`; несуществующий `/sitemap.xml` → 404 с полноценной Nuxt-страницей (175 КБ gzip) — [bristol.ru](https://bristol.ru/)
- **SimpleWine**: `https://simplewine.ru/` → Servicepipe challenge; `/sitemap.xml` → 403 Forbidden — [simplewine.ru](https://simplewine.ru/)
- **Яндекс Лавка, Яндекс Еда, Глобус, Fix Price, Верный, Светофор**: challenge не встретился — см. раздел 1.

### Inferences
- Блоки X5, Азбуки вкуса и Мегамаркета прямо ссылаются на VPN, то есть на IP-репутацию/гео; с российского резидентного IP ответ может быть мягче (у X5 останется как минимум Servicepipe JS-challenge на HTML). Это согласуется с локальной заметкой команды в `sources/perekrestok.py` (блок по IP дата-центра).
- Qrator у Ашана и Магнита настроен избирательно: HTML-главная Ашана закрыта, а JSON API открыт — вероятно, ради мобильных клиентов; такая конфигурация может измениться без предупреждения.
- ВинЛаб и К&Б пропускают главную и sitemap, но закрывают каталог — перечислить URL можно, получить карточки без браузера нельзя.

### Gaps
- Поведение всех «закрытых» сайтов с российского резидентного IP — не проверено (нет такого выхода).
- Вендор антибота К&Б (`/bp_chl.js`) и Ozon — не определён.
- Лента: в локальном `sources/lenta.py` команды описан частичный доступ к `api.lenta.com` под видом мобильного приложения (только слой магазинов, каталог возвращает 400); здесь это не воспроизводилось — эмуляция клиента для прохода антибота вне рамок задания.

## 4. Для пригодных источников: перечисление каталога, размер, доля карточек с составом и КБЖУ

### Takeaway
Глобус перечисляется двумя sitemap (47 874 карточки), Ашан — категорийным JSON API (≈102,7 тыс. продуктовых карточек, из них 18,7 тыс. активных), Fix Price — API категории (990 продуктовых). В выборках EAN был на 100 % карточек, состав — на 100 % продуктовых, КБЖУ — на 83–100 % (у Fix Price половина значений — нули).

### Cited Findings

**Глобус**
- `robots.txt` перечисляет `Sitemap: https://www.globus.ru/sitemappdp1.xml`, `sitemappdp2.xml`, `sitemapplp.xml`; в pdp1 — 27 359 `<loc>`, в pdp2 — 20 515, уникальных URL `/products/…` — 47 874; plp — 7 562 URL брендов/листингов — [sitemappdp1.xml](https://www.globus.ru/sitemappdp1.xml), [sitemappdp2.xml](https://www.globus.ru/sitemappdp2.xml)
- Категория «Молочные продукты, сыр, яйца»: `pagination {per_page: 40, page: 1, total: 3364, total_page: 85}`; верхних категорий в меню 28, из них продуктовых 16 — [категория](https://www.globus.ru/catalog/molochnye-produkty-syr-yajcza-10118965)
- Случайная выборка 10 карточек из sitemap: EAN — 10/10; продуктовых 6 (люля-кебаб «Немясо», малина Franui, макароны Alce Nero, кофе Bialetti, творожная масса, печенье «Петродиет»), состав — 6/6, `food_energy` — 5/6 (нет у кофе); у 3 из 4 нон-фуд карточек в поле «Состав» записан материал («полимер», «плюш») — [sitemappdp1.xml](https://www.globus.ru/sitemappdp1.xml)
- Формат значений КБЖУ не нормализован: встречается `"fat": "18.9 (в творожной основе - 20)"`, `"carbohydrate": "18.4 (в т.ч. сахарозы - 12.3)"` — [sitemappdp2.xml](https://www.globus.ru/sitemappdp2.xml) (карточка «Творожная масса Московская Ростагроэкспорт»)
- Контекст магазина по умолчанию — `store_id: 5011`, `pvz_id: 2` (Красногорск); регион выдачи — Москва, МО, Тверь — [главная](https://www.globus.ru/)

**Ашан**
- Каталог целиком: `POST /v1/catalog/products?merchantId=1&page=1&perPage=1` с фильтром без категории → `range: 329227`, `activeRange: 40025` — [catalog/products](https://www.auchan.ru/v1/catalog/products?merchantId=1&page=1&perPage=1)
- По 15 продуктовым категориям верхнего уровня (`range` / `activeRange`): moloko-syr-yayca 11 357 / 2 362; ptica-myaso 3 693 / 285; ryba-ikra-moreprodukty 4 847 / 582; syry 4 162 / 1 123; ovoschi-frukty-zelen-griby-yagody 3 951 / 588; zamorozhennye-produkty 4 678 / 982; kolbasnye-izdeliya 7 941 / 1 065; hlebnaya-vypechka 5 658 / 492; bakaleya 11 512 / 2 966; konditerskie_izdeliya 16 217 / 1 902; orehi-suhofrukty-sneki 3 994 / 728; chay-kofe-sladosti 5 126 / 881; voda-soki-napitki 4 431 / 1 248; alkogol 9 831 / 2 357; zdorovyy-vybor 5 357 / 1 144. Сумма 102 755 / 18 705 (категории могут пересекаться) — [catalog/products](https://www.auchan.ru/v1/catalog/products?merchantId=1&page=1&perPage=1)
- Пагинация `page`/`perPage=40` работает как минимум до 30-й страницы (bakaleya, page=30 → 40 элементов) — [catalog/products](https://www.auchan.ru/v1/catalog/products?merchantId=1&page=30&perPage=40)
- Выборка 12 карточек (бакалея стр. 2 и 30, колбасы стр. 5, сладости стр. 20): `mainEan` — 12/12 (2 из 12 — весовые коды `25…`), «Состав» — 12/12, `energy_value` — 12/12 (у 1 карточки белки и жиры `null`) — [product-detail](https://www.auchan.ru/v1/catalog/product-detail?code=sok-j-7-apelsin-s-myakotyu-ohlazhdennyy-850-ml&merchantId=1)
- В списке нет `mainEan`, поэтому на каждую карточку нужен отдельный `product-detail` (≈8 КБ) — [catalog/products](https://www.auchan.ru/v1/catalog/products?merchantId=1&page=1&perPage=40)

**Fix Price**
- `GET https://api.fix-price.com/buyer/v1/category/menu` → 200, 30 корневых категорий; продуктовая — `id 2004, alias produkty-i-napitki` с 12 подкатегориями (чай-кофе-сахар, детское питание, молочные продукты, бакалея, кондитерские изделия, БАДы…) — [category/menu](https://api.fix-price.com/buyer/v1/category/menu)
- `POST https://api.fix-price.com/buyer/v1/product/in/produkty-i-napitki?page=1&limit=24&sort=sold`, тело `{"category":"produkty-i-napitki","brand":[],"price":[],"isDividedPrice":false,"isNew":false,"isHit":false,"isSpecialPrice":false}` → 200, массив из 24 товаров (`id, sku, title, url, brand, images`), заголовок ответа `x-count: 990` — [product/in](https://api.fix-price.com/buyer/v1/product/in/produkty-i-napitki?page=1&limit=24&sort=sold)
- Выборка 8 карточек со стр. 20: `barcode` — 8/8, `composition` — 8/8, `nutritionalValueSeparated` присутствует 8/8, но у 4 все значения `"0"` (вода ×2, кофе растворимый, суп с лапшой «Фо-бо») — ноль используется и как заглушка — [api product](https://api.fix-price.com/buyer/v1/product/1001076)
- `https://fix-price.com/sitemap_index.xml` (указан в robots.txt) → 503 в трёх попытках — [sitemap_index.xml](https://fix-price.com/sitemap_index.xml)

**Источники без EAN (для fuzzy-матчинга)**
- Магнит: `sitemap_index.xml` → `__sitemap__/products.xml` с 19 884 URL `/product/<id>-<slug>` — [products.xml](https://magnit.ru/__sitemap__/products.xml)
- Яндекс Лавка: `sitemap.xml` → `sitemap-catalog-1.xml` (26 569 `<loc>`, из них 24 044 товарных: 13 347 `/good/…` и 10 697 `/supermarket/good/…`); выборка 7 карточек: состав — 7/7, КБЖУ — 6/6 продуктовых — [sitemap-catalog-1.xml](https://lavka.yandex.ru/sitemap-catalog-1.xml)
- Яндекс Еда: `sitemap/sitemap-products.xml` — индекс из 128 файлов `sitemap-products-NNN.xml.gz`; в файле 000 — 26 965 URL вида `/retail/<brand>/product/<slug>/<uuid>` по 1 302 брендам (в топе: asan_giper 890, detskij_mir 761, magnit_celevaya 623, lenta 618, okej_new 533, paterocka 517, perekrestok 509) — [sitemap-products.xml](https://eda.yandex.ru/sitemap/sitemap-products.xml), [shard 000](https://eda.yandex.ru/sitemap/sitemap-products-000.xml.gz)
- Яндекс Еда, выборка через `POST /api/v2/menu/product`: Перекрёсток — 4 карточки, состав в `description` 4/4; Лента — 4 карточки (2 еда, 2 нон-фуд), `description` пуст 4/4, у еды есть блок `energy_values`; Глобус, Metro, Магнит Семейный — по 1 продуктовой карточке, `description` пуст, `energy_values` есть — [api/v2/menu/product](https://eda.yandex.ru/api/v2/menu/product)

**Перечисление у закрытых сайтов (sitemap доступен, карточки нет)**
- Впрок: `sku0.xml` — 20 000 URL, `sku1.xml` — 7 551 URL — [sku0.xml](https://www.vprok.ru/sku0.xml), [sku1.xml](https://www.vprok.ru/sku1.xml)
- К&Б: `sitemap-iblock-9.xml` — 3 230 URL каталога (moloko_syry_yaytso 407, khleb_pechene_vafli 352, soki-i-nektary 259, vodka_nastoyki 186, vino 183…) — [sitemap-iblock-9.xml](https://krasnoeibeloe.ru/sitemap-iblock-9.xml)
- ВинЛаб: `sitemap.xml` — 3 027 `<loc>`, из них 2 752 `/product/<id>` — [sitemap.xml](https://www.winelab.ru/sitemap.xml)

### Inferences
- Доля еды у Глобуса: 6 из 10 случайных карточек продуктовые → порядка 25–30 тыс. продуктовых карточек (оценка по очень малой выборке).
- Объём обхода при 1 запрос/с: Глобус ≈13 ч (47,9 тыс. × 58 КБ через `_next/data`), Ашан активные продукты ≈5–6 ч (18,7 тыс.), Ашан вся еда с неактивными ≈29 ч (102,7 тыс.), Fix Price ≈20 мин.
- Общий потолок трёх источников — порядка 130–150 тыс. продуктовых карточек с EAN до дедупликации; реальный прирост к 11 тыс. строк с составом зависит от пересечения ассортиментов Ашана и Глобуса.
- Яндекс Еда даёт состав для Перекрёстка, но без EAN и с неполным покрытием по ритейлерам — имеет смысл только как сырьё для fuzzy-матчинга.

### Gaps
- Отдаёт ли Ашан `product-detail` с `mainEan`/составом для неактивных карточек (≈84 тыс. продуктовых) — целенаправленно не проверено.
- Глубокая пагинация Ашана (страницы 100+), лимиты частоты и поведение при длительном обходе у всех трёх источников — не проверено.
- Доли состава/КБЖУ посчитаны на 7–12 карточках на источник; для Магнита подробно разобрана 1 карточка.
- Доля продуктовых карточек в sitemap Глобуса точно не посчитана (нужен обход категорий).
- Яндекс Еда: общее число URL (≈3,4 млн) — экстраполяция одного файла из 128; доля еды и покрытие по ритейлерам не посчитаны; как получить `place_slug` для Пятёрочки/О'КЕЙ/Ашана — не проверено.

## 5. Публичные API для разработчиков и партнёров

### Takeaway
Документированного публичного API каталога с EAN ни у одной продуктовой сети не найдено; использованные endpoint'ы Глобуса, Ашана, Fix Price, Магнита и Яндекса — недокументированные внутренние API сайтов. У маркетплейсов есть официальные API только для продавцов.

### Cited Findings
- Яндекс Маркет: «API Яндекс Маркета для продавцов» (разделы: кабинеты и магазины, товары, остатки, цены, заказы, отчёты) — [yandex.ru/dev/market/partner-api](https://yandex.ru/dev/market/partner-api/doc/ru/)
- Неофициальные открытые клиенты внутренних API (организация Open-Inflation, обновлялись в 2026 г.): `pyaterochka_api` (27★), `perekrestok_api` (7★), `chizhik_api` (4★), `fixprice_api` (2★), `ozon_api` — со снапшотами реальных ответов и JSON-схемами в `tests/__snapshots__` — [github.com/Open-Inflation](https://github.com/Open-Inflation)
- В `fixprice_api` карточка товара получается через браузерную навигацию (`page.goto(…/catalog/<category>/p-<id>-<slug>)`), а список — через `POST …/v1/product/in/<category>` — [products.py](https://github.com/Open-Inflation/fixprice_api/blob/HEAD/fixprice_api/endpoints/catalog/products.py), [catalog.py](https://github.com/Open-Inflation/fixprice_api/blob/HEAD/fixprice_api/endpoints/catalog/catalog.py)
- Recon внутренних API доставки (Ашан `/v3/autohints`, Metro GraphQL с полем `barcodes`, Лента `/api-gateway/v1`, Самокат `x-creeper`), июль 2026 — [TheZavitaev/zakupator docs/recon.md](https://github.com/TheZavitaev/zakupator/blob/HEAD/docs/recon.md)

### Inferences
- API продавцов маркетплейсов работают в пределах собственных товаров продавца и не дают доступа к чужим карточкам; для сбора EAN → состав по всему каталогу они, вероятнее всего, бесполезны (по общим сведениям, по документации не проверено).

### Gaps
- Документация Ozon Seller API (`https://docs.ozon.ru/api/seller/`) с этого IP — цикл 307 `?__rr=`; портал WB (`https://dev.wildberries.ru/`) — 498; `https://partner-wiki.megamarket.ru/` — Servicepipe challenge. Содержимое не проверено.
- Партнёрские/поставщицкие порталы X5, Магнита, Ленты, Ашана, Глобуса, Fix Price целенаправленно не искались; WebSearch не использовался (по вводным даёт слабые результаты на русском).
- Условия использования (ToS) для массового обхода не анализировались. По robots.txt: у Глобуса `Disallow: /search*` (карточки `/products/` и sitemap не запрещены) — [robots.txt](https://www.globus.ru/robots.txt); у Магнита `Disallow: /*search` и `*term=` — [robots.txt](https://magnit.ru/robots.txt); у Яндекс Еды `Disallow: /api/` и `/eats/` (то есть единственный рабочий путь к карточке запрещён для роботов) — [robots.txt](https://eda.yandex.ru/robots.txt); у Лавки `Disallow: /api/` — [robots.txt](https://lavka.yandex.ru/robots.txt); у Fix Price `Disallow: /search` — [robots.txt](https://fix-price.com/robots.txt). robots.txt Ашана и api.fix-price.com не запрашивались — не проверено.
- В ходе проб запрещённые robots.txt пути всё же запрашивались: Глобус `/search` — 11 раз, Магнит `/search` и `/webgate/v2/goods/search` — 3 раза, Яндекс Еда `/api/v2/menu/product` и `/eats/…` — 18 раз (тест EAN-поиска и карточек был в постановке задачи; правило в robots.txt замечено уже после). Для промышленного обхода это нужно решить отдельно.
