"""Раскладывает базу shop из справочника по MongoDB по таблицам ClickHouse.

Документы с вложенными полями становятся строками: заказ — строкой orders,
каждая позиция заказа — строкой order_items, каждый склад товара — строкой
stock. Идентификаторы и числа те же, что в MongoDB: один и тот же отчёт можно
сравнить в двух базах.

    python3 stend/seed/from_mongodb.py ~/mongodb-practice/stend/seed

Результат — CSV с заголовком рядом с этим файлом. Запускается один раз:
CSV хранятся в репозитории, стенд читает их, а не JSON.
"""

import csv
import json
import sys
from pathlib import Path

src = Path(sys.argv[1]).expanduser()
out = Path(__file__).parent


def load(name):
    return json.loads((src / f"{name}.json").read_text(encoding="utf-8"))


def day(value):
    return value["$date"][:10]


def moment(value):
    return value["$date"][:19].replace("T", " ")


def write(name, header, rows):
    with open(out / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)
    print(f"{name:20} {len(rows):4} строк")


products = load("shop.products")
write("shop.products",
      ["product_id", "sku", "title", "brand", "category", "price", "discount",
       "rating", "reviews", "added"],
      [[p["_id"], p["sku"], p["title"], p["brand"], p["category"], p["price"],
        p.get("discount", r"\N"), p["rating"], p["reviews"], day(p["added"])]
       for p in products])
write("shop.stock", ["product_id", "warehouse", "qty"],
      [[p["_id"], s["warehouse"], s["qty"]] for p in products for s in p["stock"]])

write("shop.customers",
      ["customer_id", "name", "email", "city", "registered", "segment", "phone"],
      [[c["_id"], c["name"], c["email"], c["city"], day(c["registered"]),
        c["segment"], c["phone"]] for c in load("shop.customers")])

orders = load("shop.orders")
write("shop.orders",
      ["order_id", "number", "customer_id", "created", "status", "total",
       "payment_method", "paid", "delivery_city", "delivery_type",
       "delivery_days", "promo"],
      [[o["_id"], o["number"], o["customer_id"], moment(o["created"]), o["status"],
        o["total"], o["payment"]["method"], int(o["payment"]["paid"]),
        o["delivery"]["city"], o["delivery"]["type"], o["delivery"]["days"],
        o.get("promo", r"\N")] for o in orders])
write("shop.order_items",
      ["order_id", "line", "sku", "title", "category", "qty", "price"],
      [[o["_id"], n, i["sku"], i["title"], i["category"], i["qty"], i["price"]]
       for o in orders for n, i in enumerate(o["items"], 1)])
