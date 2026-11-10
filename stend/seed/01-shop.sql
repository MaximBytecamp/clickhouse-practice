-- База shop: тот же магазин электроники, что в справочнике по MongoDB.
-- Заказ из одного документа стал строкой orders и строками order_items,
-- склады товара — строками stock. Данные — из CSV рядом с этим файлом.

DROP DATABASE IF EXISTS shop SYNC;
CREATE DATABASE shop;

CREATE TABLE shop.products
(
    product_id String,
    sku        String,
    title      String,
    brand      String,
    category   String,
    price      UInt32,
    discount   Nullable(UInt8),
    rating     Float32,
    reviews    UInt32,
    added      Date
)
ENGINE = MergeTree
ORDER BY product_id;

CREATE TABLE shop.stock
(
    product_id String,
    warehouse  String,
    qty        UInt32
)
ENGINE = MergeTree
ORDER BY (product_id, warehouse);

CREATE TABLE shop.customers
(
    customer_id String,
    name        String,
    email       String,
    city        String,
    registered  Date,
    segment     String,
    phone       String
)
ENGINE = MergeTree
ORDER BY customer_id;

CREATE TABLE shop.orders
(
    order_id       String,
    number         String,
    customer_id    String,
    created        DateTime,
    status         String,
    total          UInt32,
    payment_method String,
    paid           Bool,
    delivery_city  String,
    delivery_type  String,
    delivery_days  UInt8,
    promo          Nullable(String)
)
ENGINE = MergeTree
ORDER BY order_id;

CREATE TABLE shop.order_items
(
    order_id String,
    line     UInt8,
    sku      String,
    title    String,
    category String,
    qty      UInt16,
    price    UInt32
)
ENGINE = MergeTree
ORDER BY (order_id, line);
