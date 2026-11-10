-- База iot: датчики на складах магазина, замер раз в минуту, 1 августа — 31 октября 2026.
-- На каждом из четырёх складов шесть датчиков: три в зале, один в серверной,
-- один у стеллажа с аккумуляторами и один на улице. Значения вычисляются
-- из номера датчика и минуты, как в 02-web.sql. В данных заложены:
--   * суточные колебания и похолодание на улице к октябрю;
--   * пропуски: датчик MSK2-HALL-2 не отвечал 5–7 сентября, EKB-BAT — 20 октября с 8:00 до 20:00;
--   * авария кондиционера в серверной склада «Москва-2» 22 сентября с 10:00 до 13:00.

DROP DATABASE IF EXISTS iot SYNC;
CREATE DATABASE iot;

CREATE TABLE iot.readings
(
    ts          DateTime,
    sensor_id   String,
    warehouse   String,
    zone        String,
    temperature Float32,
    humidity    UInt8
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts)
ORDER BY (sensor_id, ts);

INSERT INTO iot.readings
SELECT ts, sensor_id, warehouse, zone, temperature, humidity
FROM
(
    SELECT
        minutes.number AS m,
        toDateTime('2026-08-01 00:00:00') + toIntervalMinute(m) AS ts,
        ['Москва-1', 'Москва-2', 'Екатеринбург', 'Санкт-Петербург'][w] AS warehouse,
        ['MSK1', 'MSK2', 'EKB', 'SPB'][w] AS code,
        ['зал', 'зал', 'зал', 'серверная', 'аккумуляторы', 'улица'][z] AS zone,
        concat(code, '-', ['HALL-1', 'HALL-2', 'HALL-3', 'SRV', 'BAT', 'OUT'][z]) AS sensor_id,
        m / 1440 AS day,
        -- сутки: минимум в 5 утра, максимум в 17
        sin((m % 1440 - 660) / 1440 * 2 * pi()) AS daily,
        (cityHash64(w, z, m) % 1000) / 1000 - 0.5 AS noise,
        multiIf(
            zone = 'улица', 21 - 0.17 * day - [0, 0, 3, 1][w] + 5 * daily + 2 * noise,
            zone = 'серверная' AND w = 2 AND ts BETWEEN '2026-09-22 10:00:00' AND '2026-09-22 13:00:00',
                22 + 13 * (dateDiff('minute', toDateTime('2026-09-22 10:00:00'), ts) / 180),
            zone = 'серверная', 22 + 0.6 * daily + 0.6 * noise,
            zone = 'аккумуляторы', 17 + 0.8 * daily + 0.6 * noise,
            20.5 + 1.5 * daily + 0.8 * noise + 0.2 * z) AS t,
        toFloat32(round(t, 1)) AS temperature,
        toUInt8(if(zone = 'улица', 70 - 15 * daily + 10 * noise, 42 + 4 * daily + 6 * noise)) AS humidity
    FROM numbers(92 * 1440) AS minutes
    CROSS JOIN (SELECT number + 1 AS w FROM numbers(4)) AS warehouses
    CROSS JOIN (SELECT number + 1 AS z FROM numbers(6)) AS zones
)
WHERE NOT (sensor_id = 'MSK2-HALL-2' AND ts >= '2026-09-05 00:00:00' AND ts < '2026-09-08 00:00:00')
  AND NOT (sensor_id = 'EKB-BAT' AND ts >= '2026-10-20 08:00:00' AND ts < '2026-10-20 20:00:00');

OPTIMIZE TABLE iot.readings FINAL;
