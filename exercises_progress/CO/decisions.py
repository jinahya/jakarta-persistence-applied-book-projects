import json, re
C = []
def rr(sql): return ':' not in re.sub(r"'[^']*'", '', sql)  # an exercise with a parameter shows no output
def fix(i, src, why, **kw): C.append(dict(op='fix', id=i, _src=src, _why=why, rerun=('sql' in kw and rr(kw['sql'])), **kw))
def add(i, src, why, **kw): C.append(dict(op='add', id=i, after='last', _src=src, _why=why, rerun=rr(kw['sql']), **kw))
def rm(i, src, why): C.append(dict(op='remove', id=i, _src=src, _why=why))

fix('CO_SCHEMA_A_13', 'both', "revenue counted cancelled and refunded orders, unlike CO_SCHEMA_I_02 (Claude); a store with no line was dropped and tied stores made the running total unstable (Codex)",
    request=["The regional manager wants each store's revenue from completed orders, `0` for a store with none, its rank, its share of the chain's total, and a running total from the best store down; stores with the same revenue are ordered by `store_id`."],
    sql="WITH revenues AS (SELECT s.store_id, s.store_name, COALESCE(SUM(oi.unit_price * oi.quantity), 0) AS revenue\n                  FROM stores s\n                           LEFT JOIN orders o ON o.store_id = s.store_id AND o.order_status = 'COMPLETE'\n                           LEFT JOIN order_items oi ON oi.order_id = o.order_id\n                  GROUP BY s.store_id, s.store_name)\nSELECT store_id,\n       store_name,\n       revenue,\n       RANK() OVER (ORDER BY revenue DESC)                                          AS revenue_rank,\n       ROUND(100 * revenue / NULLIF(SUM(revenue) OVER (), 0), 2)                   AS share_pct,\n       SUM(revenue) OVER (ORDER BY revenue DESC, store_id ROWS UNBOUNDED PRECEDING) AS running_total\nFROM revenues\nORDER BY revenue DESC, store_id")
fix('CO_CUSTOMERS_I_01', 'both', "an address with nothing before an @, or no @, made SUBSTR NULL, so exactly the worst ones were hidden",
    request=["Accounts are meant to be opened as `first.last@...`.",
             "Data quality wants the customers whose email address, before the `@`, is not their full name in lower case with the spaces turned into dots, including the addresses with nothing before an `@` or no `@` at all; customers with the same name are ordered by `customer_id`."],
    sql="SELECT customer_id, full_name, email_address\nFROM customers\nWHERE INSTR(email_address, '@') <= 1\n   OR SUBSTR(email_address, 1, INSTR(email_address, '@') - 1) <> LOWER(REPLACE(full_name, ' ', '.'))\nORDER BY full_name, customer_id")
fix('CO_ORDERS_A_02', 'both', "LAG over order_tms alone: two orders at one moment could each be the other's previous; order_id breaks the tie, as CO_ORDERS_A_03 does",
    request=["Customer care, looking at one customer, wants each of their orders next to the one before it, and the whole days between the two, to see how often they come back; orders placed at the same moment are ordered by `order_id`."],
    sql="SELECT order_id,\n       order_tms,\n       previous_order_tms,\n       EXTRACT(DAY FROM order_tms - previous_order_tms) AS days_since_previous\nFROM (SELECT order_id, order_tms, LAG(order_tms) OVER (ORDER BY order_tms, order_id) AS previous_order_tms\n      FROM orders\n      WHERE customer_id = :customerId)\nORDER BY order_tms, order_id")
fix('CO_SCHEMA_A_11', 'Claude', "the year's start came from SYSDATE, the host's clock, and now from LOCALTIMESTAMP, the session's; around New Year they disagree",
    request=["Finance wants the number and value of the orders placed since the start of the current year, by month.",
             "The start of the year and now are both taken from `LOCALTIMESTAMP`, one clock, as the JPQL takes them from one `:yearStart` and `LOCAL DATETIME`."],
    sql="SELECT EXTRACT(MONTH FROM o.order_tms)  AS order_month,\n       COUNT(DISTINCT o.order_id)        AS orders,\n       SUM(oi.unit_price * oi.quantity)  AS revenue\nFROM orders o\n         JOIN order_items oi ON oi.order_id = o.order_id\nWHERE o.order_tms >= TRUNC(LOCALTIMESTAMP, 'YYYY')\n  AND o.order_tms < LOCALTIMESTAMP\nGROUP BY EXTRACT(MONTH FROM o.order_tms)\nORDER BY order_month")
fix('CO_SCHEMA_I_08', 'Claude', "a cancelled or refunded order never ships, so its unassigned lines were work that does not exist",
    request=["Logistics wants the orders, other than cancelled or refunded ones, that still have lines with no shipment assigned, and how many such lines each has, the most first; orders with the same number are ordered by `order_id`."],
    sql="SELECT o.order_id, o.order_status, COUNT(*) AS unshipped_lines\nFROM orders o\n         JOIN order_items oi ON oi.order_id = o.order_id\nWHERE oi.shipment_id IS NULL\n  AND o.order_status NOT IN ('CANCELLED', 'REFUNDED')\nGROUP BY o.order_id, o.order_status\nORDER BY unshipped_lines DESC, o.order_id")
fix('CO_INVENTORY_B_02', 'Claude', "the note admitted the order was unstable among stores with the same stock but left it so; SELECT * brought the known product along",
    request=["A merchandiser wants every store's stock of a product, lowest first, to see which stores need it replenished first; stores with the same stock are ordered by `store_id`."],
    sql="SELECT store_id, product_inventory\nFROM inventory\nWHERE product_id = :productId\nORDER BY product_inventory, store_id")
fix('CO_STORES_I_01', 'Claude', "SUBSTR(name, -4) is NULL in Oracle for a name shorter than 4 characters, while the JPQL RIGHT(name, 4) gives the whole name",
    request=["The signage team needs store names without spaces, for file names: `New York City` becomes `New-York-City`, and the last four characters of each, the whole name if it is shorter, are used as a short code."],
    sql="SELECT store_name,\n       REPLACE(store_name, ' ', '-')                       AS slug,\n       UPPER(SUBSTR(store_name, -LEAST(4, LENGTH(store_name)))) AS short_code\nFROM stores\nORDER BY store_name")
fix('CO_SCHEMA_A_09', 'Claude', "it asked two questions, and its second, list price above every price sold at, is a narrower CO_SCHEMA_I_05",
    request=["Finance wants the orders containing at least one line charged above `:price` per unit."],
    sql="SELECT o.order_id, o.order_tms\nFROM orders o\nWHERE :price < ANY (SELECT oi.unit_price FROM order_items oi WHERE oi.order_id = o.order_id)\nORDER BY o.order_id")
fix('CO_STORES_A_01', 'Codex', "a distance in degrees of latitude and longitude can pick the wrong neighbour; the great-circle distance, with ties",
    request=["For each store with both coordinates, show its nearest other store with both coordinates, all of them at a tie, and the great-circle distance in kilometres."],
    sql="WITH distances AS (SELECT s.store_id,\n                          s.store_name,\n                          n.store_name AS nearest_store,\n                          6371 * ACOS(GREATEST(-1, LEAST(1,\n                              SIN(s.latitude * ACOS(-1) / 180) * SIN(n.latitude * ACOS(-1) / 180)\n                              + COS(s.latitude * ACOS(-1) / 180) * COS(n.latitude * ACOS(-1) / 180)\n                                * COS((s.longitude - n.longitude) * ACOS(-1) / 180)))) AS km\n                   FROM stores s\n                            JOIN stores n ON n.store_id <> s.store_id\n                   WHERE s.latitude IS NOT NULL\n                     AND s.longitude IS NOT NULL\n                     AND n.latitude IS NOT NULL\n                     AND n.longitude IS NOT NULL)\nSELECT store_name, nearest_store, ROUND(km, 2) AS km\nFROM (SELECT d.*, RANK() OVER (PARTITION BY store_id ORDER BY km) AS rnk FROM distances d)\nWHERE rnk = 1\nORDER BY store_name, nearest_store")
fix('CO_SCHEMA_A_05', 'Codex', "it ranked the rounded kilometres, so a farther donor could win, with no tie-break on equal distance or surplus; the ACOS argument unclamped",
    request=["With `0 <= :minStock <= :targetStock`, for each stocked product below `:minStock` at a store, propose the nearest store above `:targetStock` as the donor, the larger surplus and then the lower `store_id` at a tie, and a donor with no distance only as a fallback; propose no more than the need or the surplus."],
    sql="WITH short AS (SELECT store_id, product_id, :targetStock - product_inventory AS need\n               FROM inventory\n               WHERE product_inventory < :minStock),\n     spare AS (SELECT store_id, product_id, product_inventory - :targetStock AS surplus\n               FROM inventory\n               WHERE product_inventory > :targetStock),\n     pairs AS (SELECT sh.store_id AS to_store_id,\n                      sp.store_id AS from_store_id,\n                      sh.product_id,\n                      sh.need,\n                      sp.surplus,\n                      6371 * ACOS(GREATEST(-1, LEAST(1,\n                          SIN(t.latitude * ACOS(-1) / 180) * SIN(f.latitude * ACOS(-1) / 180)\n                          + COS(t.latitude * ACOS(-1) / 180) * COS(f.latitude * ACOS(-1) / 180)\n                            * COS((t.longitude - f.longitude) * ACOS(-1) / 180)))) AS km\n               FROM short sh\n                        JOIN spare sp ON sp.product_id = sh.product_id AND sp.store_id <> sh.store_id\n                        JOIN stores t ON t.store_id = sh.store_id\n                        JOIN stores f ON f.store_id = sp.store_id),\n     ranked AS (SELECT p.*,\n                       ROW_NUMBER() OVER (PARTITION BY to_store_id, product_id\n                           ORDER BY km ASC NULLS LAST, surplus DESC, from_store_id) AS rn\n                FROM pairs p)\nSELECT t.store_name AS to_store, f.store_name AS from_store, r.product_id, ROUND(r.km) AS km,\n       LEAST(r.need, r.surplus) AS transfer_qty\nFROM ranked r\n         JOIN stores t ON t.store_id = r.to_store_id\n         JOIN stores f ON f.store_id = r.from_store_id\nWHERE r.rn = 1\nORDER BY r.km NULLS LAST, t.store_name, r.product_id")
fix('CO_STORE_ORDERS_A_01', 'Codex', "starting from the loss rows dropped a store with no cancellation or refund; the totals may be 0, so the divisions need a guard",
    request=["For every store with a store-total row, show its cancelled and refunded sales, `0` where it has none, and their share of the store's sales and of the chain's, every status counted; a share is NULL where its total is `0`."],
    sql="SELECT st.store_name,\n       COALESCE(SUM(d.total_sales), 0)                                                 AS lost_sales,\n       ROUND(100 * COALESCE(SUM(d.total_sales), 0) / NULLIF(MAX(st.total_sales), 0), 1) AS pct_of_store,\n       ROUND(100 * COALESCE(SUM(d.total_sales), 0) / NULLIF(MAX(g.total_sales), 0), 2)  AS pct_of_chain\nFROM store_orders st\n         LEFT JOIN store_orders d ON d.store_name = st.store_name\n    AND d.total IS NULL\n    AND d.order_status IN ('CANCELLED', 'REFUNDED')\n         CROSS JOIN (SELECT total_sales FROM store_orders WHERE total = 'GRAND TOTAL') g\nWHERE st.total = 'STORE TOTAL'\nGROUP BY st.store_name\nORDER BY pct_of_store DESC NULLS LAST, st.store_name")
fix('CO_PRODUCTS_A_01', 'Codex', "the price-only order decides which ties qualify, but leaves them in any order; an outer order by product_id, outside FETCH ... WITH TIES",
    request=["Show the ten most expensive priced products, every product tied with the tenth included, ordered by price, the highest first, and then by `product_id`.",
             "The order inside decides which products qualify; the one outside only orders them, so a `product_id` does not change which ties are kept."],
    sql="SELECT product_id, product_name, unit_price\nFROM (SELECT product_id, product_name, unit_price\n      FROM products\n      WHERE unit_price IS NOT NULL\n      ORDER BY unit_price DESC\n      FETCH FIRST 10 ROWS WITH TIES)\nORDER BY unit_price DESC, product_id")
fix('CO_ORDERS_B_01', 'Codex', "order_tms is not unique; order_id breaks the tie",
    request=["Show all of a customer's orders, the most recent first; orders placed at the same moment are ordered by `order_id`, the highest first."],
    sql="SELECT order_id, order_tms, order_status, store_id\nFROM orders\nWHERE customer_id = :customerId\nORDER BY order_tms DESC, order_id DESC")
rm('CO_CUSTOMER_ORDER_PRODUCTS_B_01', 'Codex', "the view's items is a LISTAGG, cut short, and a name matches inside another (Men's / Women's Jacket); no text match is exact. CO_SCHEMA_B_04 answers the recall by product_id; Claude had proposed padding the list with its delimiter")

add('CO_SCHEMA_B_04', 'Codex', "the recall question, answered exactly, by product_id through order_items",
    title='Contact the customers of a recalled product',
    request=["A supplier has recalled a product.", "Customer care wants every order that included it, with the customer's name and email address, the most recent first; orders placed at the same moment are ordered by `order_id`."],
    sql="SELECT o.order_id, o.order_tms, c.full_name, c.email_address\nFROM order_items oi\n         JOIN orders o ON o.order_id = oi.order_id\n         JOIN customers c ON c.customer_id = o.customer_id\nWHERE oi.product_id = :productId\nORDER BY o.order_tms DESC, o.order_id DESC")
add('CO_CUSTOMER_ORDER_PRODUCTS_B_02', 'Codex', "keeps the view's Basic tier after CO_CUSTOMER_ORDER_PRODUCTS_B_01, with what the view is good at: a total and a summary of the products",
    title="Review a customer's completed baskets",
    request=["Customer care wants a customer's completed orders, each with its total and the summary of its products, the most recent first."],
    sql="SELECT order_id, order_tms, order_total, items\nFROM customer_order_products\nWHERE customer_id = :customerId\n  AND order_status = 'COMPLETE'\nORDER BY order_tms DESC, order_id DESC")
add('CO_PRODUCTS_I_03', 'Codex', "several views group by the product's name, and the exercises take a group for a product; nothing makes the name unique",
    title='Product names that more than one product has',
    request=["The views group by a product's name, and the exercises on them take a group for one product; the schema does not make the name unique.",
             "Find the names that more than one product has, with how many; the check passes when nothing comes back."],
    sql="SELECT product_name, COUNT(*) AS products\nFROM products\nGROUP BY product_name\nHAVING COUNT(*) > 1\nORDER BY product_name")
add('CO_SCHEMA_I_09', 'Codex', "the order totals assume every order has lines; the foreign key holds only the other way",
    title='Orders without a line',
    request=["The exercises on order totals assume every order has at least one line; the foreign key holds only from the line to the order.",
             "Find the orders with no line, the most recent first; the check passes when nothing comes back."],
    sql="SELECT o.order_id, o.order_tms, o.order_status, o.customer_id, o.store_id\nFROM orders o\nWHERE NOT EXISTS (SELECT 1 FROM order_items oi WHERE oi.order_id = o.order_id)\nORDER BY o.order_tms DESC, o.order_id DESC")
add('CO_INVENTORY_B_04', 'Codex', "nothing keeps the stock from going below 0, which the replenishment and out-of-stock exercises assume",
    title='Negative stock',
    request=["Nothing in the schema keeps `PRODUCT_INVENTORY` from going below `0`, which the replenishment exercises assume.",
             "Find the inventory rows with a negative stock, the most negative first; the check passes when nothing comes back."],
    sql="SELECT inventory_id, store_id, product_id, product_inventory\nFROM inventory\nWHERE product_inventory < 0\nORDER BY product_inventory, store_id, product_id")
add('CO_PRODUCTS_B_04', 'both', "the image columns of PRODUCTS are read by no exercise; Claude's (missing or out of date) over Codex's (missing)",
    title='Products missing a fresh picture',
    request=["The web team wants the products that have no picture, or whose picture was last changed before `:since`, those that never had one first."],
    sql="SELECT product_id, product_name, image_filename, image_last_updated\nFROM products\nWHERE product_image IS NULL\n   OR image_last_updated < :since\nORDER BY image_last_updated NULLS FIRST, product_name")
add('CO_ORDERS_B_04', 'Claude', "no exercise pages past the first rows; Oracle's OFFSET ... FETCH NEXT, and a unique tie-break",
    title="The next page of a customer's order history",
    request=["The account page shows a customer's orders `:pageSize` at a time, the most recent first.", "Show the page that starts after the first `:offset` orders; `order_id` breaks a tie, so a page neither repeats nor skips an order."],
    sql="SELECT order_id, order_tms, order_status, store_id\nFROM orders\nWHERE customer_id = :customerId\nORDER BY order_tms DESC, order_id DESC\nOFFSET :offset ROWS FETCH NEXT :pageSize ROWS ONLY")
add('CO_SCHEMA_A_17', 'Claude', "dates are grouped but never compared across periods; LAG over an aggregate",
    title='Month-over-month sales',
    request=["Finance wants the revenue of completed orders per month, next to the month before and the change in per cent.",
             "`LAG` takes the previous month that has sales, not the previous calendar month."],
    sql="SELECT order_month,\n       revenue,\n       LAG(revenue) OVER (ORDER BY order_month)                                       AS previous_revenue,\n       ROUND(100 * (revenue - LAG(revenue) OVER (ORDER BY order_month)) / LAG(revenue) OVER (ORDER BY order_month), 1) AS change_pct\nFROM (SELECT TRUNC(o.order_tms, 'MM') AS order_month, SUM(oi.unit_price * oi.quantity) AS revenue\n      FROM orders o\n               JOIN order_items oi ON oi.order_id = o.order_id\n      WHERE o.order_status = 'COMPLETE'\n      GROUP BY TRUNC(o.order_tms, 'MM'))\nORDER BY order_month")
add('CO_SCHEMA_A_18', 'Claude', "ORDER_ITEMS.SHIPMENT_ID is read only from the line's side; a shipment no line points to is the reverse",
    title='Shipments that carry nothing',
    request=["Before dispatch, logistics wants the shipments that no order line is assigned to, with their store, customer and status."],
    sql="SELECT sh.shipment_id, sh.store_id, sh.customer_id, sh.shipment_status\nFROM shipments sh\nWHERE NOT EXISTS (SELECT 1 FROM order_items oi WHERE oi.shipment_id = sh.shipment_id)\nORDER BY sh.shipment_id")
add('CO_ORDER_ITEMS_I_02', 'Claude', "the DDL says LINE_ITEM_ID runs from 1 within an order, but does not enforce it; the receipt relies on it",
    title='Orders with gaps in their line numbers',
    request=["The schema describes `LINE_ITEM_ID` as a number starting at one for each order, but does not enforce it.",
             "Data quality wants the orders whose line numbers do not run 1, 2, 3, ... without gaps, with their number of lines and their first and last line number; the check passes when nothing comes back."],
    sql="SELECT order_id, COUNT(*) AS lines, MIN(line_item_id) AS first_line, MAX(line_item_id) AS last_line\nFROM order_items\nGROUP BY order_id\nHAVING MIN(line_item_id) <> 1\n    OR MAX(line_item_id) <> COUNT(*)\nORDER BY order_id")
C = [x for x in C if x['op'] != 'remove'] + [x for x in C if x['op'] == 'remove']  # adds first: a remove may empty a tier an add continues
json.dump({'module': 'oracle-sample-schemas-persistence/oracle-sample-schemas-persistence-co', 'changes': C}, open('decisions.json', 'w'), indent=1, ensure_ascii=False)
from collections import Counter; print(Counter(c['op'] for c in C))
