# Сторонние базы, сервисы поиска, нутри-платформы и открытые датасеты: EAN-13 → состав / КБЖУ / фото для продуктов РФ

Состояние на 13.10.2026. Ритейлеры и госреестры (Нацкаталог, GS1, Роскачество) не рассматривались — они в зоне других исследователей.

Как мерили: живые запросы 13.10.2026 с 12 тестовыми EAN из задания, анонимно, без регистраций и оплат. Прямые соединения из WSL зависали, поэтому почти всё шло через прокси с выходом в Германии — гео-зависимое поведение российских сайтов могло отличаться. «Найдено» = сервис вернул карточку; «состав» / «КБЖУ» = в карточке реально есть список ингредиентов / калорийность и БЖУ на 100 г. Всё, что не удалось проверить запросом или первичной страницей, помечено «не проверено».

## Сводная таблица (ранжировано по реальной отдаче EAN → состав/КБЖУ для РФ)

| # | Источник | Тип | Поиск по EAN | Состав | КБЖУ | Hit rate на 12 тестовых EAN | Цена | Лицензия / хранение у себя | Вердикт |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **EAN-DB** (ean-db.com) | платный API + частичные дампы | да: REST `GET /api/v2/product/<ean>` (JWT); анонимная веб-форма 20 успешных запросов/час с IP | да, структурированный список на русском + vegan/vegetarian, `contains` | да, на 100 г | найдено 10/12; **состав 6/12; КБЖУ 5/12**; состав или КБЖУ 7/12; фото 8/12 | €9 / 5 000, €69 / 50 000, €249 / 300 000 успешных запросов; дамп €0,005 за штрихкод; 250 запросов бесплатно после регистрации | ToS: нельзя «make publicly available, sell or resell … Product Data»; прямого запрета хранить нет; права на данные остаются у EAN-DB | **Лучший платный вариант.** Но на случайном «длинном хвосте» из базы команды: найдено 8/8, обогащено только 1/8 — платить придётся и за карточки с одним названием |
| 2 | **Open Food Facts** | открытая база: API + полный дамп | да | да | да | найдено 10/12; **состав 3/12; КБЖУ 6/12** (+1 без ккал); фото 8/12 | бесплатно | ODbL (share-alike) — уже известно команде | Бесплатный максимум. По РФ 36 783 продукта, из них с заполненным составом только 4 825. На длинном хвосте: 1/12 найдено, 0 обогащено |
| 3 | **Go-UPC** (go-upc.com) | платный API | да (публичная страница поиска без ключа) | иногда (в т.ч. машинный перевод на английский) | нет на тесте | найдено 8/12; состав 3/12; КБЖУ 0/12 | $74,95 / 5 000, $245 / 45 000, $795 / 450 000 запросов в месяц | не проверено (страница terms — 404) | Слабо и дорого; замечено перепутанное описание |
| 4 | **FatSecret Platform API** | нутри-платформа | да, метод `food.find_id_for_barcode` (scope `barcode`), регион `RU` есть в списке локализаций | нет (списков ингредиентов нет; аллергены только для generic-продуктов) | да | не проверено (нужен ключ) | Basic — бесплатно, только US; Premier Free — бесплатно, только US-датасет; Premier — по запросу, «based on market access» | хранить нельзя: кэш ≤ 24 ч, бессрочно — только ID | Для своей базы непригоден; годится только как онлайн-фолбэк КБЖУ по платному контракту |
| 5 | **1С:Номенклатура** | каталог учётной системы | да, внутри программ 1С | не подтверждено | не подтверждено | не проверено | 500 ₽/год за 100 карточек … 90 000 ₽/год за 100 000 | не проверено | Каталог вырос до «более 13 млн» карточек, но наличие состава/КБЖУ не подтверждено |
| 6 | **catalog.app** (платная библиотека) | PIM с общей библиотекой карточек | да (в аккаунте; есть демо без регистрации) | нет | нет | найдено 2/12; состав 0/12; КБЖУ 0/12 | по запросу, прайса нет | по договору | Не источник состава: карточки еды — парсинг интернет-магазинов (название, объём, жирность) |
| 7 | **Rate&Goods B2B** | был платный API | — | — | — | недоступен: домен на парковке | исторически 400 ₽ за 500 запросов | — | **Выбыл** (см. поправку ниже) |
| 8 | Chomp (chompthis.com) | food API | да | да | да | не проверено (нужен ключ) | $0,01/запрос; $25/мес + $0,001/запрос; $299/мес | terms запрещают копировать/архивировать базу, кроме кэша < 24 ч | Для своей базы непригоден |
| 9 | Edamam Food Database API | food API | да (UPC) | — | да | не проверено (нужен ключ) | $14 / $69 / $299 в месяц | кэшировать можно только FoodId, название и 4 макро-показателя; «строить копию данных» запрещено | US-центричен (790 000 UPC), для РФ бесполезен |
| 10 | Listex (listex.info, Украина) | контент-платформа, API по apikey | да | в карточках (не проверено) | не проверено | 0/12 (контрольный украинский EAN находится) | не проверено | не проверено | Украинский рынок, российских EAN нет |
| 11 | UPCitemdb | API (есть бесплатный trial) | да | нет | нет | 0/11 верных (1 ложное совпадение) | trial бесплатно | — | Бесполезен |
| 12 | barcodes.olegon.ru, ean-online.ru, service-online.su, barcodes-catalog.ru, disai.org, CloudShop | русскоязычные справочники штрихкодов | да | нет | нет | только названия (service-online: 1/1 — название, бренд, категория) | olegon: API отвечает 429 «ОПЛАТА НА OLEGON.RU»; ean-online: доступ по запросу | — | Name-only, ценности не добавляют |
| 13 | goodsmatrix.ru | был сайт с составами | — | — | — | мёртв | — | — | Сайт не работает |
| 14 | ean13.info, barcodelookup.com, buycott.com, ean-search.org, roscontrol.com, Kaggle | разное | — | — | — | не проверено: антибот-проверки / недоступность | — | — | Не измерено |
| 15 | Российские калорийные сайты (tablicakalorijnosti.ru, health-diet.ru), YAZIO, Lifesum, MyFitnessPal, Nutritionix | нутри-приложения | на вебе — по названию, не по EAN | нет | да (по названию) | не проверено | — | — | Публичного API/выгрузки с EAN не найдено |

Поправки к тому, что команда считала известным:

- **Rate&Goods B2B недоступен.** Домен `ratengoods.com` (и `b2b.ratengoods.com`) делегирован на `NS1/NS2.PARKLOGIC.COM`, отдаёт страницу-редирект парковки; запись в реестре изменена 22.07.2026.
- **1С:Номенклатура — «более 13 млн» карточек**, а не 6,8 млн.
- **Open Food Facts: 36 783 продукта по России**, но состав заполнен только у 4 825.
- **FatSecret Premier Free даёт только US-датасет** — российские штрихкоды в бесплатный тариф не входят.
- **API barcodes.olegon.ru на первый же запрос вернул 429 с текстом про оплату.**
- **EAN-DB возвращает состав и КБЖУ по российским EAN** (раньше было известно только, что это «платный API»).

---

## 1. Какие источники реально возвращают состав и/или КБЖУ по тестовым EAN?

### Takeaway

Состав и КБЖУ по российским EAN реально отдают только два источника из проверенных: EAN-DB (состав 6/12, КБЖУ 5/12) и Open Food Facts (состав 3/12, КБЖУ 6/12); вместе они закрывают 11 из 12 тестовых EAN хотя бы одним из двух полей. Но тестовые EAN — флагманские товары: на случайной выборке «длинного хвоста» из базы команды EAN-DB дал обогащение 1 из 8, OFF — 0 из 12.

### Cited Findings

#### Матрица по 12 тестовым EAN (13.10.2026)

Обозначения: Н — найдено, С — есть состав, К — есть КБЖУ, Ф — есть фото, «—» — не найдено.

| EAN | Товар | Open Food Facts | EAN-DB | Go-UPC | catalog.app (демо) |
|---|---|---|---|---|---|
| 4601662000016 | молоко Parmalat 3,5% | Н С К Ф | Н С К Ф | Н | Н (без состава) |
| 4606386000014 | вода Угличская | Н Ф | Н Ф (только объём) | Н | — |
| 4601576000027 | майонез ЕЖК | Н С К Ф | Н (только название) | Н | — |
| 4602541000028 | кефир Агуша | Н С К Ф | Н С К Ф | Н С | — |
| 4601727000036 | сок 4 Сезона томатный | — | Н С Ф | Н С (состав внутри описания) | Н (без состава) |
| 4690388000158 | Cheetos | — | Н С Ф | — | — |
| 4601780000189 | Makfa спагетти | Н Ф, БЖУ без ккал | Н С К Ф | Н | — |
| 4603955000345 | плитка «Хорошая компания» Рот Фронт | Н Ф | Н К | Н С (на английском) | — |
| 4601674000950 | кетчуп Pikador | Н К | — | — | — |
| 4680003503294 | колбаса Дымов | Н Ф | Н С К (без углеводов) Ф | Н | — |
| 4600493000066 | творог Карат | Н К Ф | Н Ф | — | — |
| 4665304100113 | пельмени Мельников | Н К | — | — | — |
| **Итого** | | Н 10, С 3, К 6 (+1 частично), Ф 8 | Н 10, С 6, К 5, Ф 8 | Н 8, С 3, К 0 | Н 2, С 0, К 0 |

- Объединение OFF ∪ EAN-DB на тесте: состав у 7/12, КБЖУ у 9/12, хотя бы одно из двух у 11/12 (пусто только у воды Угличской) — расчёт по строкам матрицы выше; источники строк — [OFF API](https://world.openfoodfacts.org/api/v2/product/4601662000016.json) и [форма поиска EAN-DB](https://ean-db.com/).

#### EAN-DB (ean-db.com)

- Сервис заявляет «over 70 million products», «detailed product information, including title, category, manufacturer, images, ingredients and other metadata»; в базе 70 801 605 продуктов, 60% с метаданными, 41% с изображениями — [EAN-DB, главная](https://ean-db.com/).
- Русский — второй язык названий в базе: 13 986 078 продуктов с русским названием (английский — 40 399 808) — [EAN-DB stats](https://ean-db.com/stats).
- Анонимный поиск через веб-форму ограничен: «Anonymous usage is limited to 20 requests per hour from one IP address (only successful requests are counted)» — [EAN-DB, форма поиска](https://ean-db.com/barcode/search).
- Результат по 12 тестовым EAN: найдено 10 (нет кетчупа Pikador и пельменей Мельников — ответ `"code": 404, "description": "Product not found"`), состав у 6, КБЖУ у 5, фото у 8 — живые запросы к [форме поиска EAN-DB](https://ean-db.com/barcode/search), 13.10.2026.
- Урезанный пример ответа (кефир Агуша, 4602541000028): `"titles": {"ru": "Кефир \"Агуша\" для детского питания."}`, `"metadata": {"food": {"nutrimentsPer100Grams": {"proteins": 3 g, "fat": 3.2 g, "carbohydrates": 4 g, "energy": 57 kcal}}, "generic": {"ingredients": [{"ingredientsGroup": [{"originalNames": {"ru": "Нормализованное Молоко"}, "id": "milk", "properties": {"contains": ["milk"]}, "isVegan": false, "isVegetarian": true}, {"originalNames": {"ru": "Кефирная Закваска"}}]}], "storageConditions": {"shelfLife": 10 day, "temperature": < 6 °C}}}`, `"images": [{"url": "https://images.ean-db.com/…jpg", "isCatalog": true, "width": 1000, "height": 1000}]`, `"barcodeDetails": {"description": "GS1 Russia", "country": "ru"}` — [форма поиска EAN-DB](https://ean-db.com/barcode/search).
- Пример состава со вложенностью (Cheetos, 4690388000158): «Крупа кукурузная, Масло Растительное, Ароматизатор [Соль, Вкусоароматические Вещества, Сухая Молочная Сыворотка, Сахар, Усилитель Вкуса И Аромата (Глутамат Натрия 1-Замещенный)]» — собрано из `originalNames.ru` и `subIngredients` ответа [EAN-DB](https://ean-db.com/barcode/search).
- Состав отдаётся не текстом с этикетки, а разобранным деревом: группы, `originalNames` («как на упаковке»), `canonicalNames`, `amount`, `isVegan`, `isVegetarian`, `subIngredients`, ссылки на CosIng и Wikidata — [EAN-DB, Product ingredients metadata](https://ean-db.com/docs/product-metadata-ingredients).
- Замечены ошибки в цифрах: у плитки Рот Фронт (4603955000345) отдано «fat 5 g, proteins 5 g, carbohydrates 52 g, energy 570 kcal» — такие БЖУ не дают 570 ккал; у молока Parmalat 3,5% отдан жир 3,2 г (в OFF — 3,5 г) — [EAN-DB](https://ean-db.com/barcode/search), сравнение с [OFF](https://world.openfoodfacts.org/api/v2/product/4601662000016.json).
- Случайная выборка «длинного хвоста» (12 штрихкодов с префиксом 46 из категории «Продукты питания» провайдера `uhtt` в базе команды; успели проверить 8, дальше сработал лимит «You have reached the limit of 20 requests per hour»): найдено 8/8, состав и КБЖУ — только у 1/8 (паста Nutella, 4607086411476), фото 1/8 — [форма поиска EAN-DB](https://ean-db.com/barcode/search), 13.10.2026.
- В этой выборке названия в EAN-DB посимвольно совпадают с названиями из дампа UHTT, например «Масло сладкосливочное 82.5% 200g #2» (4607011830044) и «Тарталетки невские берега песочные 324g тв/уп» (4601526073743) — [форма поиска EAN-DB](https://ean-db.com/barcode/search).

#### Open Food Facts

- На 13.10.2026 поиск по стране «Россия» возвращает `count = 36783` — [OFF search API, countries_tags_en=russia](https://world.openfoodfacts.org/api/v2/search?countries_tags_en=russia&page_size=1&fields=code).
- Из них с состоянием `ingredients-completed` — 4 825 — [OFF search API](https://world.openfoodfacts.org/api/v2/search?countries_tags_en=russia&states_tags=en:ingredients-completed&page_size=1&fields=code).
- С состоянием `nutrition-facts-completed` — 17 517 — [OFF search API](https://world.openfoodfacts.org/api/v2/search?countries_tags_en=russia&states_tags=en:nutrition-facts-completed&page_size=1&fields=code).
- С обоими состояниями сразу — 4 502; с загруженными фото — 26 055; продуктов с русским языком по всему миру — 42 004 — [OFF search API, фильтр по двум состояниям](https://world.openfoodfacts.org/api/v2/search?countries_tags_en=russia&states_tags=en:ingredients-completed,en:nutrition-facts-completed&page_size=1&fields=code), [photos-uploaded](https://world.openfoodfacts.org/api/v2/search?countries_tags_en=russia&states_tags=en:photos-uploaded&page_size=1&fields=code), [languages_tags=en:russian](https://world.openfoodfacts.org/api/v2/search?languages_tags=en:russian&page_size=1&fields=code).
- Результат по 12 тестовым EAN: найдено 10 (нет сока 4 Сезона и Cheetos), состав у 3 (Parmalat, ЕЖК, Агуша), ккал + БЖУ у 6, у Makfa БЖУ без ккал, фото у 8 — [OFF product API](https://world.openfoodfacts.org/api/v2/product/4601576000027.json).
- Пример: 4601576000027 → «Майонез Провансаль ЕЖК мдж 67%», состав «Масло подсолнечное рафинированное дезодорированное, вода питьевая, сахар, желток яичный, …», 610 ккал, белки 0,6, жиры 67, углеводы 2 — [OFF product API](https://world.openfoodfacts.org/api/v2/product/4601576000027.json).
- На той же случайной выборке «длинного хвоста» (12 штрихкодов): найден 1 (Nutella, пустая карточка без названия, состава и ккал, но с фото), остальные 11 — 404 — [OFF product API](https://world.openfoodfacts.org/api/v2/product/4607086411476.json).
- Поисковый API OFF нестабилен: часть запросов возвращала 503 «Page temporarily unavailable», ответ приходил со 2–3-й попытки — [OFF search API](https://world.openfoodfacts.org/api/v2/search?countries_tags_en=russia&page_size=1&fields=code).
- Платформа для производителей существует на русском: «Полностью бесплатная платформа, позволяющая производителям легко управлять данными и фотографиями своих продуктов» — [ru.pro.openfoodfacts.org](https://ru.pro.openfoodfacts.org/).

#### Go-UPC

- Публичная страница поиска работает без ключа и показывает название, бренд, описание, размер, страну — [go-upc.com/search](https://go-upc.com/search?q=4601662000016).
- Результат по 12 тестовым EAN: найдено 8, состав у 3 (Агуша — «Молоко Нормализованное, Закваска На Кефирных Грибках»; сок 4 Сезона — состав «томатное пюре, соль» внутри описания; плитка Рот Фронт — на английском «Sugar Non-tempering Cocoa Butter Substitute…»), КБЖУ нет ни у одного — [go-upc.com/search](https://go-upc.com/search?q=4602541000028).
- У плитки Рот Фронт (4603955000345) в поле описания стоит текст про другой продукт: «Рататуй классический овощной в духовке…» — [go-upc.com/search](https://go-upc.com/search?q=4603955000345).

#### catalog.app (платная библиотека)

- Сейчас это PIM-платформа: «библиотека на 80 млн товаров», «Отдаём: 80M карточек · 7M штрихкодов · 300M изображений» — [catalog.app](https://catalog.app/).
- Есть демо-аккаунт без регистрации с доступом к «Общей библиотеке» — [ru.demo.catalog.app](https://ru.demo.catalog.app/Library/ProductCards?libraryType=Common).
- Точный поиск 12 тестовых EAN в общей библиотеке: найдено 2 (молоко Parmalat и сок 4 Сезона), состава и КБЖУ нет ни у одного — [демо catalog.app, общая библиотека](https://ru.demo.catalog.app/Library/ProductCards?libraryType=Common&query=4601662000016&flexible=false).
- Карточка молока Parmalat: «Источник: www.old-version.onlinetrade.ru … Объем: 1 л. Жирность: 3.5 % Вид: молоко ультрапастеризованное» — то есть свойства спарсены из интернет-магазина — [демо catalog.app](https://ru.demo.catalog.app/Library/ProductCards?libraryType=Common&query=4601662000016&flexible=false).

#### Rate&Goods

- `ratengoods.com`: регистрация 16.07.2012, истечение 16.07.2027, последнее изменение 22.07.2026, серверы имён `NS1.PARKLOGIC.COM` / `NS2.PARKLOGIC.COM` — [RDAP Verisign](https://rdap.verisign.com/com/v1/domain/ratengoods.com).
- `https://b2b.ratengoods.com/` и `https://ratengoods.com/` отдают страницу «Redirecting… Loading» со скриптом, который обращается к `router.parklogic.com` — [b2b.ratengoods.com](https://b2b.ratengoods.com/).
- В App Store приложение числится: версия 5.18.7 от 11.09.2025 с пометкой «Мы вернулись и обновили приложение», предыдущая версия — 04.08.2023; разработчик LLC Axiom (ООО «Аксиома»); заявлено «в нашей базе их более 30 млн»; сайт и политика конфиденциальности указывают на ratengoods.com — [App Store, Rate&Goods](https://apps.apple.com/ru/app/id649420054).
- В Telegram-канале @ratengoods (51 подписчик, создан 25.04.2025) два поста: опрос «Скучаете по Rate&Goods?» (03.05.2025) и «Скоро опубликуем анонс нового проекта» (03.06.2025) — [t.me/s/ratengoods](https://t.me/s/ratengoods).
- Исторические данные: «RateNGoods — 500 запросов по цене 400 рублей» (публикация 19.03.2021) — [Хабр, песочница](https://habr.com/ru/sandbox/152192/).
- Модель наполнения: «Rate&Goods — база товаров, которую пополняют пользователи», плюс с 14.04.2020 бесплатное размещение карточек производителями — [WEproject](https://www.weproject.media/articles/detail/skaner-shtrikh-kodov-rate-goods-otkryvaet-besplatnyy-dostup-dlya-proizvoditeley/).

#### FatSecret Platform API

- Метод поиска по штрихкоду принимает GTIN-13, параметр `region` («If not specified this will default to "US"»), scope OAuth2 — `barcode`; метод помечен как Premier Exclusive — [FatSecret docs, food.find_id_for_barcode](https://platform.fatsecret.com/docs/v1/food.find_id_for_barcode).
- Локализация — «a premium feature only made available to select accounts for specific languages and regions»; в списке регионов есть «RU Russia Russian», а также BY, KZ (русский язык) и UA — [FatSecret docs, Localization](https://platform.fatsecret.com/docs/guides/localization).
- Тарифы: Basic — бесплатно, 5 000 вызовов в день, «US Only»; Premier Free — бесплатно после верификации, «US Only»; Premier — «Upon request. Based on market access», «More than 62 Countries» — [FatSecret API Editions](https://platform.fatsecret.com/api-editions).
- Условия Premier Free: «Start-ups meaning a company earning less than US$1 million in annual revenue and having raised less than US$1 million in funding», некоммерческие организации и студенты; обязательна атрибуция; «Access to non-US datasets for those meeting eligibility requirements can be provided at a discount» — [FatSecret API Editions](https://platform.fatsecret.com/api-editions).
- В перечне возможностей нет списков ингредиентов брендовых продуктов: есть «Allergens and Dietary Preferences» и «Food images» со сноской «For all generic foods globally» — [FatSecret API Editions](https://platform.fatsecret.com/api-editions).

#### Прочие сервисы поиска по штрихкоду

- UPCitemdb, бесплатный trial-эндпоинт: по 10 тестовым EAN `"total":0`, по Cheetos (4690388000158) вернул чужой товар «Zenitar 16 Mc Fisheye For Samsung Nx Lens», один запрос получил 429 `TOO_FAST`; полей состава/КБЖУ в схеме нет — [api.upcitemdb.com trial](https://api.upcitemdb.com/prod/trial/lookup?upc=4690388000158).
- Listex: украинская площадка, «Продукты питания, напитки 94366», «Поиск более чем по 170000 товаров»; подсказки поиска по 12 российским EAN пустые, контрольный украинский 4820200896830 находится — [listex.info](https://listex.info/), [эндпоинт подсказок](https://listex.info/search/getSearchResult?query=4820200896830&type=goods).
- Listex API требует `apikey`, лимит «обычно в 500 запросов к API за 5 минут», метод `product` принимает `gtin` — [api.listex.info](https://api.listex.info).
- barcodes.olegon.ru: на первый запрос `GET /api/card/name/4601662000016` ответ `{"status":429,"names":["ОПЛАТА НА OLEGON.RU : https://olegon.ru/forumdisplay.php?f=374"]}`; структура ответа содержит только массив `names` — [barcodes.olegon.ru API](https://barcodes.olegon.ru/api/card/name/4601662000016).
- ean-online.ru: «более 27000000 товаров», API `GET /api/v1/barcode/{barcode}` с Bearer-токеном возвращает `barcode, name, category, vendor, balance`; «Для получения доступа к API свяжитесь с нами» — [ean-online.ru/api](https://ean-online.ru/api/).
- service-online.su: по 4601662000016 отдаёт название, бренд «Parmalat», категорию «Продукты питания / Молочные продукты / Молоко, сливки» и связанные штрихкоды; состава нет — [service-online.su](https://service-online.su/text/shtrih-kod/?cod=4601662000016).
- goodsmatrix.ru: главная отдаёт заглушку хостинга «Домен не прилинкован ни к одной из директорий на сервере!», страница товара — 404 — [goodsmatrix.ru](http://goodsmatrix.ru/).
- disai.org — регистратор штрихкодов (альтернативная GS1 система) с каталогом товаров участников, а не справочник состава — [disai.org](https://disai.org/).
- napolke.ru — оптовый маркетплейс; в HTML карточки товара (крекер Tuc) нет ни состава, ни штрихкода, ни КБЖУ — [napolke.ru, карточка](https://napolke.ru/catalog/product/kreker_tuc_so_smetanoj_i_lukom_100_gr_flou_pak-e081f86e-edf7-428a-8b7c-3c5881b1f735).
- Антибот-проверки, из-за которых измерение не делалось: ean13.info («Перевірка браузера… захищає каталог від автоматичного масового копіювання») — [ean13.info](https://ean13.info/4601662000016.htm); barcodelookup.com (Cloudflare «Security Verification», 403) — [barcodelookup.com](https://www.barcodelookup.com/4601662000016); buycott.com (Cloudflare «Just a moment…») — [buycott.com](https://www.buycott.com/upc/4601662000016); ean-search.org («You were blocked from that page. Please get an account for automated mass queries») — [ean-search.org](https://www.ean-search.org/?q=4601662000016); api.barcodes-catalog.ru («Checking your browser») — [api.barcodes-catalog.ru](https://api.barcodes-catalog.ru/barcode/free_search?barcode=4601576000027&limit=3).

#### Каталоги учётных систем и касс

- 1С:Номенклатура: «Сегодня это более 13 млн. карточек товаров. В каталоге широко представлены потребительские товары, продукты, напитки, табак…»; требования к публикации — «штрихкод, наименование, характеристики и фото если есть» — [Портал 1С:ИТС](https://portal.1c.ru/applications/1C-Nomenclature).
- CloudShop заявляет «База товаров на 13 млн. штрихкодов» — [cloudshop.ru](https://cloudshop.ru/).
- Cloud API Эвотора работает только с товарами конкретного магазина (`GET /stores/{store-id}/products`), метода поиска по общему каталогу в справочнике нет — [developer.evotor.ru](https://developer.evotor.ru/docs/rest_overview.html).

#### Нутри-платформы и калорийные сайты

- Edamam: «790,000 unique UPCs/barcodes», есть UPC/Barcode Search — [Edamam Food Database API](https://developer.edamam.com/food-database-api).
- Chomp: «800k+ Grocery Items», «700k+ Scannable Barcodes» — [Chomp, поиск по базе](https://chompthis.com/api/lookup.php).
- На странице Go-UPC карточка кефира Агуша озаглавлена «Агуша,ВБД 3,2 On CHOMP» — [go-upc.com/search](https://go-upc.com/search?q=4602541000028).
- tablicakalorijnosti.ru и health-diet.ru: на главных страницах нет упоминаний поиска по штрихкоду или API — [tablicakalorijnosti.ru](https://www.tablicakalorijnosti.ru/), [health-diet.ru](https://health-diet.ru/).

#### Откуда берут данные конкуренты и аналоги

- mira.team: «Откуда берутся данные? Из открытых данных о составе и пищевой ценности, научных источников и продуктов, которые ежедневно сканирует сообщество. Производители тоже могут присылать проверенную информацию»; «Продукта нет или данные неверны — … Отсканируйте его, чтобы добавить» — [mira.team, база знаний](https://mira.team/ru/help).
- mira.team: есть панель производителя — «Зарегистрируйтесь в панели производителя Мира, чтобы добавлять данные о продуктах и технические карты» — [mira.team, производителям](https://mira.team/ru/manufacturers).
- mira.team: оценка еды опирается «на метод Nutri-Score»; юрлицо — IMAGENIC LTD (Лондон, company number 13950150) — [mira.team](https://mira.team/ru).
- Yuka: собственная база, пополняется пользователями и брендами — по выдаче поиска со ссылкой на [help.yuka.io](https://help.yuka.io/l/en/article/qcdty8rmrv/); при прямом запросе 13.10.2026 страница вернула 404, цитата не перепроверена.
- Yuka: по французской статье, сервис сейчас опирается на некраудсорсингового поставщика Salsify (бывш. Alkemics) и продолжает передавать данные в Open Food Facts — по выдаче поиска, [15marches](https://15marches.substack.com/p/lopen-data-au-service-de-la-transparence); первоисточник не открывался, не перепроверено.
- CodeCheck: база собиралась краудсорсингом, с 2010 года — в основном через приложение; оценки ингредиентов — от внешних организаций; куплен в 2022 году (источники расходятся: Producto GmbH либо Testberichte) — по выдаче поиска, [Wikipedia](https://en.wikipedia.org/wiki/CodeCheck), [PitchBook](https://pitchbook.com/profiles/company/98220-52), [CB Insights](https://www.cbinsights.com/company/codecheck); не перепроверено.

### Inferences

- Массовый источник «EAN → состав» для российского длинного хвоста среди сторонних баз не обнаружен: флагманские SKU покрыты и OFF, и EAN-DB, а случайные штрихкоды из UHTT — почти нет (EAN-DB 1/8, OFF 0/12). Выборки малы (N = 8 и 12), оценка грубая.
- EAN-DB, судя по посимвольно совпадающим названиям, залил тот же дамп UHTT, который уже есть у команды. Поэтому высокий показатель «найдено» у EAN-DB на базе команды обманчив: значительная часть платных ответов будет содержать только уже известное название.
- Для флагманских товаров EAN-DB и OFF дополняют друг друга, а не дублируют: состав по 4 тестовым EAN есть только в EAN-DB, по 1 — только в OFF.
- Цифры КБЖУ из EAN-DB нельзя брать без проверки: нужна хотя бы сверка «ккал ≈ 4·Б + 9·Ж + 4·У».
- Mira, Yuka, CodeCheck и Rate&Goods пришли к одной и той же модели: стартовые открытые данные + краудсорсинг сканов/фото этикеток + кабинет производителя. Ни один из них публично не называет купленную стороннюю базу составов для РФ.
- Chomp, вероятно, наследует российские позиции из Open Food Facts (карточка «On CHOMP» на Go-UPC совпадает по составу с OFF), так что прироста относительно OFF от него ждать не стоит.

### Gaps

- Hit rate FatSecret, Edamam, Chomp, Nutritionix, 1С:Номенклатуры и платного API Go-UPC не измерен: нужен ключ или регистрация, а регистрации были запрещены условиями.
- Содержит ли 1С:Номенклатура состав и КБЖУ у продуктов — не проверено: на странице сервиса говорится только о «характеристиках», структура карточки без доступа не видна.
- Работает ли само приложение Rate&Goods и есть ли у B2B-сервиса другой адрес — не проверено; зафиксировано только, что домен на парковке. Страницы ratengoods.com читались с отключённой проверкой сертификата (цепочка Let's Encrypt с новым корнем отсутствует в локальном хранилище WSL); вывод о парковке опирается ещё и на независимые данные RDAP.
- roscontrol.com (Росконтроль, каталог с составами) недоступен из нашей сети: TLS-соединение обрывается, по HTTP — 503. brandquad.ru — аналогично. Наличие поиска по штрихкоду там не проверено.
- Kaggle: API поиска датасетов отдал страницу reCAPTCHA, поиск не выполнен.
- YAZIO, Lifesum, MyFitnessPal, Nutritionix, Калоризатор, Dietbox, EatFit, МойСклад, Контур.Маркет, Дримкас, АТОЛ, Бизнес.Ру, «Сканер состава», халяль-сканеры, приложение Роскачества — первичные страницы не открывались или не запрашивались, выводов по ним нет.
- Долю российских продуктов с составом внутри EAN-DB сервис не публикует; оценка есть только по двум маленьким выборкам.

---

## 2. Цена за запрос или за дамп, лимиты, лицензия (можно ли хранить данные у себя)?

### Takeaway

Единственный платный источник с подтверждённым составом по РФ, понятным прайсом и без прямого запрета на хранение — EAN-DB: от €0,00083 за успешный запрос. Нутри-платформы (FatSecret, Edamam, Chomp) хранить данные запрещают, поэтому для построения собственной базы не подходят независимо от цены.

### Cited Findings

- EAN-DB, пакеты: «5000 API calls 9.00 EUR», «50000 API calls 69.00 EUR», «300000 API calls 249.00 EUR»; «Get 250 API calls free of charge after registration» — [EAN-DB, главная](https://ean-db.com/).
- EAN-DB, биллинг: «Only successful (200 OK) requests are registered»; при этом «every successful request is billed, even if you make several requests for the same product» — [EAN-DB, Billing](https://ean-db.com/docs/billing).
- EAN-DB, лицензия: запрещено «make publicly available, sell or resell the Services or Product Data resulting therefrom» и собирать данные скриптами «except in connection with your use of the API Services»; «The Proprietor reserves all right, title and interest in the Services and Product Data»; часть данных — «Third Party Content», прав на который условия не дают — [EAN-DB, Terms of Service](https://ean-db.com/policy/terms).
- EAN-DB: оператор — EAN-DB DOO, зарегистрирован в Черногории; оплату принимает Paddle.com как Merchant of Record; условия датированы 01.01.2022 — [EAN-DB, Terms of Service](https://ean-db.com/policy/terms).
- Go-UPC: Developer $74,95/мес — 5 000 запросов; Startup $245/мес — 45 000; Enterprise $795/мес — 450 000 — [Go-UPC, API plans](https://go-upc.com/plans/api).
- FatSecret, хранение: «you may not cache any user data for more than 24 hours, with the exception of information that is explicitly "storable indefinitely"»; бессрочно можно хранить только идентификаторы (`food_id`, `serving_id`, `recipe_id` и т.п.) — [FatSecret docs, Storable Data](https://platform.fatsecret.com/docs/guides/storable-data).
- Edamam: Enterprise Basic $14/мес (100 000 вызовов), Core $69/мес (750 000), Plus $299/мес (5 000 000); UPC-запросы 50 / 100 / 300 в минуту; атрибуция обязательна на всех тарифах — [Edamam Food Database API](https://developer.edamam.com/food-database-api).
- Edamam, хранение: условия «do not permit data caching unless explicitly permitted»; кэшировать можно только белок, жир, углеводы, калории, FoodId, название и изображение; кэш «does not allow API subscribers to build a copy of the Edamam data» — [Edamam Food Database API](https://developer.edamam.com/food-database-api).
- Chomp, тарифы: Limited $0/мес + $0,01 за запрос; Standard $25/мес + $0,001 за запрос; Premium $299/мес без платы за запрос, плюс плата за активных пользователей $0,001 за MAU на первом уровне — [Chomp API](https://chompthis.com/api/).
- Chomp, хранение: на странице тарифов для Premium написано «Store Data Indefinitely», но лицензия запрещает «copying or archiving any part of the Chomp Database», кроме кэша < 24 часов и данных, которые пользователь сам добавил в свой дневник — [Chomp, тарифы](https://chompthis.com/api/), [Chomp, License Information](https://chompthis.com/api/terms.php).
- 1С:Номенклатура, тарифы (карточек в год): 100 — 500 ₽; 1 000 — 2 500 ₽; 5 000 — 7 500 ₽; 10 000 — 10 000 ₽; 100 000 — 90 000 ₽; в ИТС ПРОФ включён пакет 10 000, в базовые версии программ — пакет 3 000 — [Портал 1С:ИТС](https://portal.1c.ru/applications/1C-Nomenclature).
- catalog.app: публичного прайса нет — «в течение суток пришлём расчёт стоимости»; контакт admin@catalog.app — [catalog.app](https://catalog.app/).
- Курс ЦБ РФ, установленный на 14.10.2026: EUR 93,7723 ₽, USD 83,8675 ₽ — [ЦБ РФ](https://www.cbr.ru/scripts/XML_daily.asp).

### Inferences

- В рублях по курсу ЦБ: EAN-DB — от 0,078 ₽ (пакет 300 000) до 0,169 ₽ (пакет 5 000) за успешный запрос; Go-UPC — от 0,15 ₽ (Enterprise) до 1,26 ₽ (Developer) за запрос.
- Формулировка EAN-DB про «make publicly available» двусмысленна для приложения, которое показывает карточку пользователю: хранить у себя условия не запрещают, а публичный показ и перепродажа формально под запретом. До оплаты нужно письменное подтверждение от support@ean-db.com, что показ данных в приложении допустим.
- Оплата EAN-DB идёт через Paddle; оплатить российской картой, скорее всего, не получится — не проверено, понадобится зарубежная карта или юрлицо.
- Из-за запретов на хранение FatSecret, Edamam и Chomp годятся максимум как онлайн-фолбэк на момент сканирования, но не как способ наполнить свою базу.
- Данные 1С:Номенклатуры лицензируются для работы внутри программ 1С; переносить их в стороннее приложение, вероятно, нельзя — условия не читались, не проверено.

### Gaps

- Условия использования Go-UPC не прочитаны: `https://go-upc.com/terms` вернул 404.
- Цена Premier-контракта FatSecret для рынка РФ и размер скидки для стартапов — только по запросу, не проверено.
- Цена и лицензия библиотеки catalog.app, цена API Listex и ean-online.ru — не опубликованы.
- Актуальные тарифы barcodelookup.com и ean-search.org не проверены (страницы закрыты антибот-проверкой); в публикации 2021 года для Barcodelookup называлось «5000 запросов по цене 99$» — [Хабр, песочница](https://habr.com/ru/sandbox/152192/).
- Условия оплаты API olegon.ru не прочитаны: форум закрыт страницей «Проверка на ботов».

---

## 3. Есть ли bulk-дампы, а не только API по одному запросу?

### Takeaway

Дампы с составом по РФ есть только у двух источников: бесплатный полный дамп Open Food Facts и платные частичные дампы EAN-DB (по категории или по стране выдачи штрихкода, €0,005 за штрихкод). Открытых датасетов с российскими EAN и составом сверх OFF на Hugging Face, GitHub и Zenodo не найдено.

### Cited Findings

- EAN-DB: «Bulk lookups and partial database dumps, such as by product categories or barcode issuing country, are available at a flat rate of 0.005 EUR per barcode» — [EAN-DB, главная](https://ean-db.com/).
- Официальный дамп OFF лежит на Hugging Face как `openfoodfacts/product-database` (обновлён 13.10.2026, 35 331 загрузок) — [Hugging Face API, поиск «openfoodfacts»](https://huggingface.co/api/datasets?search=openfoodfacts&limit=40&sort=downloads&direction=-1).
- `Alexey240577/openfoodfacts` — «OpenFoodFacts: продукты питания России… Источник: OpenFoodFacts (ODbL)», один файл `data.json`, лицензия в карточке указана cc0-1.0 — [Hugging Face](https://huggingface.co/datasets/Alexey240577/openfoodfacts).
- `EAN-data/ean-product-dataset` — 2 175 272 товара с названием, описанием и фото, но это датские интернет-магазины, тексты на датском, лицензия «other» — [Hugging Face](https://huggingface.co/datasets/EAN-data/ean-product-dataset).
- `thefoodapi/foodproducts` — бесплатный образец на 993 продукта, продающихся в США (состав, аллергены, нутриенты, фото), CC BY-NC 4.0; полный каталог — по листу ожидания — [Hugging Face](https://huggingface.co/datasets/thefoodapi/foodproducts).
- Поиск по Hugging Face по запросам «barcode», «ean», «gtin», «perekrestok», «magnit», «lenta», «food products» не дал ни одного датасета с российскими EAN и составом; запросы «vkusvill», «продукты», «состав продуктов», «калорийность» — 0 результатов — [Hugging Face API](https://huggingface.co/api/datasets?search=barcode&limit=40&sort=downloads&direction=-1).
- Поиск репозиториев GitHub по 7 запросам («штрихкод состав продуктов», «barcode russian food products dataset», «ean russia products database», «открытая база штрихкодов» и др.) — 0 результатов — [GitHub search API](https://api.github.com/search/repositories?q=barcode%20russian%20food%20products%20dataset&per_page=8&sort=stars).
- Поиск по Zenodo («barcode food Russia», «штрихкод продукты», «EAN products Russia») релевантных датасетов не дал — [Zenodo API](https://zenodo.org/api/records?q=EAN%20products%20Russia&size=6&sort=bestmatch).
- catalog.app предлагает банкам и аналитическим компаниям «товарную базу как актив»: «80M карточек · 7M штрихкодов · 300M изображений» — [catalog.app](https://catalog.app/).

### Inferences

- Дамп EAN-DB «по стране выдачи штрихкода» (GS1 Russia) по прайсу стоит в 6 раз дороже за штрихкод, чем API-пакет на 300 000 запросов (€0,005 против €0,00083), и по умолчанию тоже включит карточки с одним названием. Смысл он имеет только если договориться о фильтре «только записи с ingredients или nutriments» — возможность такого фильтра не проверена.
- `Alexey240577/openfoodfacts` — перевыкладка подмножества OFF: новых данных не даёт, а пометка CC0 противоречит лицензии ODbL исходника, опираться на неё нельзя.
- Библиотека catalog.app как дамп для задачи бесполезна: на тесте в ней 2/12 без состава.

### Gaps

- Kaggle не проверен (reCAPTCHA).
- Хакатонные датасеты Яндекса, Сбера, X5 и Ленты целенаправленно не найдены: поиск по Hugging Face и GitHub их не выдал, отдельные площадки хакатонов не просматривались.
- Не выяснено, можно ли заказать у EAN-DB дамп с фильтром по наличию состава и сколько в нём будет российских продуктов питания.

---

## 4. Какова лучшая цена за один обогащённый российский продуктовый штрихкод среди платных вариантов?

### Takeaway

Лучший платный вариант — EAN-DB: около 0,11 ₽ за штрихкод с составом или КБЖУ на флагманских товарах и порядка 0,6 ₽ на длинном хвосте (оценка по выборке из 8 штук). Это дешевле исторической цены Rate&Goods (0,8 ₽ за запрос) и Go-UPC, но экономику определяет не цена запроса, а доля ответов с одним названием.

### Cited Findings

- EAN-DB: максимальный пакет — 300 000 успешных запросов за €249, оплачиваются только ответы 200 OK — [EAN-DB, главная](https://ean-db.com/), [EAN-DB, Billing](https://ean-db.com/docs/billing).
- EAN-DB на тесте: из 10 найденных (оплачиваемых) ответов 7 содержат состав или КБЖУ; на выборке длинного хвоста — 1 из 8 — живые запросы к [форме поиска EAN-DB](https://ean-db.com/barcode/search), 13.10.2026.
- Go-UPC: самый дешёвый запрос — на тарифе Enterprise, $795 за 450 000 в месяц; на тесте состав есть в 3 из 12 ответов, КБЖУ — ни в одном — [Go-UPC, API plans](https://go-upc.com/plans/api), [go-upc.com/search](https://go-upc.com/search?q=4602541000028).
- Rate&Goods: исторически 400 ₽ за 500 запросов; сервис сейчас недоступен — [Хабр, песочница](https://habr.com/ru/sandbox/152192/), [RDAP Verisign](https://rdap.verisign.com/com/v1/domain/ratengoods.com).
- 1С:Номенклатура: 90 000 ₽ в год за 100 000 карточек — [Портал 1С:ИТС](https://portal.1c.ru/applications/1C-Nomenclature).

### Inferences

Расчёты ниже — мои, по курсу ЦБ на 14.10.2026 (EUR 93,7723 ₽, USD 83,8675 ₽).

| Вариант | Цена за оплачиваемый запрос | Доля запросов с составом или КБЖУ | Цена за обогащённый штрихкод |
|---|---|---|---|
| EAN-DB, пакет 300 000, флагманские товары | €0,00083 ≈ 0,078 ₽ | 7 из 10 оплаченных | ≈ 0,11 ₽ |
| EAN-DB, пакет 300 000, длинный хвост | €0,00083 ≈ 0,078 ₽ | 1 из 8 оплаченных | ≈ 0,62 ₽ |
| EAN-DB, дамп без фильтра | €0,005 ≈ 0,47 ₽ | та же доля, что у API | от ≈ 0,67 ₽ (флагманы) до ≈ 3,75 ₽ (хвост) |
| Go-UPC Enterprise | $0,00177 ≈ 0,15 ₽ | 3 из 12 (только состав) | ≈ 0,59 ₽, если оплачиваются все запросы |
| Go-UPC Developer | $0,015 ≈ 1,26 ₽ | 3 из 12 | ≈ 5,0 ₽ |
| Rate&Goods (исторически) | 0,8 ₽ | не измерено | не менее 0,8 ₽; сервис недоступен |
| 1С:Номенклатура, пакет 100 000 | 0,9 ₽ за карточку в год | не подтверждено | не определить |

- Прогон всей базы команды через EAN-DB (по локальной `barcodes.db` в ней 1 345 528 уникальных штрихкодов, из них 1 310 743 записи провайдера `uhtt` без состава и КБЖУ): если находятся почти все 1,35 млн штрихкодов (что вероятно, раз UHTT уже внутри EAN-DB), нужно 5 пакетов по 300 000 — €1 245, около 117 тыс. ₽. При доле обогащения как на длинном хвосте (1/8) это даст порядка 170 тыс. штрихкодов с составом или КБЖУ; при доле как на флагманах — в разы больше. Реальная доля лежит между этими оценками и неизвестна.
- Дешевле всего её узнать на 250 бесплатных запросах EAN-DB после регистрации: прогнать случайную выборку из базы команды и посчитать долю ответов с `metadata.generic.ingredients` или `metadata.food.nutrimentsPer100Grams`. Если она ниже ~15%, выгоднее прогонять не всю базу, а только штрихкоды, которые пользователи реально сканируют.
- Go-UPC проигрывает EAN-DB по всем параметрам: меньше найдено, нет КБЖУ, хуже качество, дороже и абонентская плата вместо пакетов.
- Open Food Facts остаётся обязательным бесплатным слоем: на тесте он дал состав или КБЖУ по четырём EAN, для которых в EAN-DB данных нет: Pikador и Мельникова в EAN-DB нет вообще, а ЕЖК и Карат там только с названием.

### Gaps

- Оценка для длинного хвоста стоит на 8 измеренных штрихкодах — доверительный интервал очень широкий; анонимный лимит EAN-DB (20 успешных запросов в час с IP) не позволил проверить больше.
- Не проверено, оплачиваются ли в Go-UPC запросы с ответом «не найдено».
- Не проверено, даст ли EAN-DB дамп с фильтром по наличию состава и по какой цене.
- Цена обогащённого штрихкода у FatSecret Premier неизвестна (цена по запросу), и хранить результат всё равно нельзя.
