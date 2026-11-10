-- База web: действия посетителей сайта того же магазина, 1 августа — 31 октября 2026.
-- Строки не хранятся в файле, а вычисляются здесь же: каждое случайное на вид
-- значение — хеш номера сессии (cityHash64), поэтому у всех одинаковый результат.
--
-- Сессия: главная страница → иногда поиск → 1–6 карточек товара →
-- иногда корзина → оформление → покупка. В данных заложены:
--   * рост посещаемости к концу периода и суточный ритм;
--   * распродажа 10–11 октября — всплеск сессий;
--   * сбой оплаты 14 сентября с 14:00 до 17:00 — покупок нет, страницы медленные.

DROP DATABASE IF EXISTS web SYNC;
CREATE DATABASE web;

CREATE TABLE web.events
(
    event_time  DateTime,
    session_id  UInt32,
    user_id     UInt32,
    event_type  String,
    url         String,
    product_id  String,
    category    String,
    price       UInt32,
    device      String,
    city        String,
    source      String,
    duration_ms UInt32
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(event_time)
ORDER BY (event_type, event_time);

-- равномерное число из [0, 1) для сессии s и «соли» k
CREATE OR REPLACE FUNCTION seed_u AS (s, k) -> (cityHash64(s, k) % 1000000) / 1000000;
-- номер элемента 1..N по весам w
CREATE OR REPLACE FUNCTION seed_pick AS (r, w) -> arrayFirstIndex(c -> c > r * arraySum(w), arrayCumSum(w));

INSERT INTO web.events
SELECT * EXCEPT (prod) FROM (
WITH

    ['p-001','p-002','p-003','p-004','p-005','p-006','p-007','p-008','p-009','p-010','p-011',
     'p-012','p-013','p-014','p-015','p-016','p-017','p-018','p-019','p-020','p-021'] AS p_id,
    ['ноутбуки','ноутбуки','ноутбуки','ноутбуки','ноутбуки','смартфоны','смартфоны','смартфоны',
     'смартфоны','периферия','периферия','периферия','периферия','периферия','комплектующие',
     'комплектующие','комплектующие','комплектующие','аксессуары','аксессуары','аксессуары'] AS p_cat,
    [42990,51490,67900,114990,89990,18990,32990,79990,27490,8990,9490,
     21990,34990,6790,7890,4590,38990,8490,2990,790,4290] AS p_price,
    [6,5,4,3,4,9,8,7,6,5,5,4,4,3,5,4,4,2,6,7,5] AS p_weight,

    ['Москва','Санкт-Петербург','Новосибирск','Екатеринбург','Казань',
     'Нижний Новгород','Краснодар','Самара','Ярославль','Воронеж'] AS cities,
    [30,15,8,9,7,6,7,5,4,5] AS city_weight,
    ['mobile','desktop','tablet'] AS devices,
    [60,32,8] AS device_weight,
    ['direct','search','ads','email','social'] AS sources,
    [30,30,20,8,12] AS source_weight,
    [1,0.6,0.4,0.3,0.3,0.5,1,2,3,4,4.5,5,5.5,5,5,5,5.2,5.5,6,7,7.5,7,5,3] AS hour_weight

SELECT
    start + toIntervalSecond(offsets[i]) AS event_time,
    -- товар события: свой у каждой карточки, у корзины и дальше — последней карточки
    seed_pick(seed_u(s, 100 + least(i, last_view)), p_weight) AS prod,
    toUInt32(s + 1) AS session_id,
    user_id,
    types[i] AS event_type,
    multiIf(i = 1, '/',
            event_type = 'search', '/search',
            event_type = 'page_view', concat('/product/', p_id[prod]),
            event_type = 'add_to_cart', '/cart',
            event_type = 'checkout', '/checkout',
            '/order/complete') AS url,
    if(i = 1 OR event_type = 'search', '', p_id[prod]) AS product_id,
    if(product_id = '', '', p_cat[prod]) AS category,
    if(product_id = '', 0, p_price[prod]) AS price,
    device,
    city,
    source,
    -- время загрузки с длинным хвостом: большинство страниц быстрые, редкие — в разы медленнее
    toUInt32(load_ms * if(device = 'mobile', 1.4, 1) * if(outage, 6, 1)
             * exp(1.2 * (seed_u(s, 300 + i) + seed_u(s, 400 + i) + seed_u(s, 500 + i) - 1.5))
             * if(seed_u(s, 600 + i) < 0.01, 8, 1)) AS duration_ms
FROM
(
    SELECT
        number AS s,
        -- постоянные посетители заходят часто, большинство — один-два раза:
        -- степень сгущает номера к началу
        toUInt32(1 + floor(pow(seed_u(s, 1), 2.2) * 500000)) AS user_id,
        devices[seed_pick(seed_u(user_id, 2), device_weight)] AS device,
        cities[seed_pick(seed_u(user_id, 3), city_weight)] AS city,
        sources[seed_pick(seed_u(s, 4), source_weight)] AS source,
        toUInt32(if(seed_u(s, 5) < 0.03, 70 + cityHash64(s, 6) % 2, floor(92 * pow(seed_u(s, 7), 0.85)))) AS day,
        seed_pick(seed_u(s, 8), hour_weight) - 1 AS hour,
        toDateTime('2026-08-01 00:00:00') + toIntervalDay(day) + toIntervalHour(hour)
            + toIntervalSecond(cityHash64(s, 9) % 3600) AS start,
        day = 44 AND hour BETWEEN 14 AND 16 AS outage,

        1 + cityHash64(s, 10) % 6 AS views,
        seed_u(s, 11) < 0.45 AS searched,
        seed_u(s, 12) < multiIf(device = 'desktop', 0.15, device = 'tablet', 0.12, 0.09)
            * if(day IN (70, 71), 1.6, 1) AS carted,
        carted AND seed_u(s, 13) < 0.5 AS checked_out,
        checked_out AND NOT outage AND seed_u(s, 14) < if(source = 'ads', 0.6, 0.75) AS purchased,

        arrayConcat(['page_view'],
                    if(searched, ['search'], []),
                    arrayResize(['page_view'], views, 'page_view'),
                    if(carted, ['add_to_cart'], []),
                    if(checked_out, ['checkout'], []),
                    if(purchased, ['purchase'], [])) AS types,
        -- карточка, после которой положили в корзину, — последняя просмотренная
        1 + searched + views AS last_view,
        arrayCumSum(arrayMap(j -> if(j = 1, 0, 5 + cityHash64(s, 20 + j) % 175),
                             arrayEnumerate(types))) AS offsets,
        120 + 80 * seed_u(s, 15) AS load_ms
    FROM numbers(2000000)
)
ARRAY JOIN arrayEnumerate(types) AS i
);

OPTIMIZE TABLE web.events FINAL;

DROP FUNCTION seed_u;
DROP FUNCTION seed_pick;
