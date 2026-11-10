# Стенд справочника по ClickHouse

Сервер ClickHouse с базами для «Справочника по ClickHouse» (МДК.04.01
«Разработка и защита баз данных»). Все примеры, числа и кадры книги получены
на этом стенде: у вас выйдет то же самое.

## Запуск

Нужен Docker: Docker Desktop на Windows и macOS, Docker Engine на Linux.

```bash
git clone https://github.com/MaximBytecamp/clickhouse-practice.git
cd clickhouse-practice
docker compose up -d
```

Первый запуск занимает несколько минут: Docker скачивает образ сервера
(около 270 МБ), затем контейнер `seed` загружает базы. Готово, когда
`docker compose logs seed` заканчивается строкой «Готово».

| Что | Где |
|---|---|
| Клиент в браузере | http://localhost:8123/play — пользователь `student`, пароль `student` |
| Клиент в терминале | `docker compose exec clickhouse clickhouse-client` |
| Вернуть базы в исходное состояние | `docker compose run --rm reset` (около 25 секунд) |
| Остановить | `docker compose down` — данные остаются |
| Удалить вместе с данными | `docker compose down -v` |

Порт занят — создайте рядом с `compose.yaml` файл `.env` со строкой
`HTTP_PORT=8124` или `NATIVE_PORT=9001`.

## Базы

| База | Таблицы | Строк |
|---|---|---|
| `shop` | `products`, `stock`, `customers`, `orders`, `order_items` | 21, 42, 20, 120, 271 |
| `web` | `events` — действия посетителей сайта, 1.08–31.10.2026 | 10 324 592 |
| `iot` | `readings` — датчики на складах, замер раз в минуту | 3 174 480 |
| `sandbox` | пустая — для упражнений | — |

`shop` — тот же магазин, что в справочнике по MongoDB, разложенный по таблицам
(`stend/seed/from_mongodb.py`). `web` и `iot` не хранятся файлами: их строки
вычисляет сам сервер по скриптам `stend/seed/02-web.sql` и `03-iot.sql`.
Каждое значение — хеш номера строки, поэтому результат у всех одинаковый.

Сервер — `clickhouse/clickhouse-server:26.8.36.3`, часовой пояс UTC.
