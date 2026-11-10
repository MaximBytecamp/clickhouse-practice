#!/bin/sh
# Загружает базы стенда: shop из CSV, web и iot — генераторами в самом сервере.
# Запускается контейнером seed (только если shop пуста) или reset (всегда).
set -e
ch() { clickhouse-client --host clickhouse --user student --password student "$@"; }

if [ -z "$FORCE" ] && [ "$(ch -q 'SELECT count() FROM shop.orders' 2>/dev/null || echo 0)" != "0" ]; then
  echo "Базы уже загружены. Вернуть исходное состояние: docker compose run --rm reset"
  exit 0
fi

ch --multiquery < /seed/01-shop.sql
for t in products stock customers orders order_items; do
  ch -q "INSERT INTO shop.$t FORMAT CSVWithNames" < /seed/shop.$t.csv
  printf 'shop.%-12s %8s строк\n' "$t" "$(ch -q "SELECT count() FROM shop.$t")"
done

echo "web.events: генерация, около минуты…"
ch --multiquery < /seed/02-web.sql
printf 'web.events        %8s строк\n' "$(ch -q 'SELECT count() FROM web.events')"

echo "iot.readings: генерация…"
ch --multiquery < /seed/03-iot.sql
printf 'iot.readings      %8s строк\n' "$(ch -q 'SELECT count() FROM iot.readings')"

ch -q "DROP DATABASE IF EXISTS sandbox SYNC; CREATE DATABASE sandbox" --multiquery
echo "Готово: базы shop, web, iot и пустая sandbox"
