# CO — Claude's review

### fix CO_CUSTOMER_ORDER_PRODUCTS_B_01
- section: CUSTOMER_ORDER_PRODUCTS   tier: Basic
- title: Orders that included a product
- why: `items LIKE '%' || :productName || '%'` matches substrings, so a recall of `Men's Jacket (Black)` also returns every order of `Women's Jacket (Black)`. Match whole list entries by padding the comma-separated list with its own delimiter. `ORDER BY order_tms DESC` alone is also unstable for orders placed at the same moment.
- request: A supplier has recalled a product. Customer care wants every order that included it, with who placed it, the most recent first.
- sql:
    ```sql
    SELECT order_id, order_tms, full_name, email_address, items
    FROM customer_order_products
    WHERE ', ' || items || ', ' LIKE '%, ' || :productName || ', %'
    ORDER BY order_tms DESC, order_id DESC
    ```

### fix CO_SCHEMA_A_13
- section: SCHEMA   tier: Advanced
- title: Store ranking and share of sales
- why: "Revenue" counts cancelled and refunded orders, which contradicts CO_SCHEMA_I_02 (revenue = completed orders) and inflates stores that lose orders. The running total is also nondeterministic when two stores tie on revenue (`ROWS UNBOUNDED PRECEDING` over a non-unique order).
- request: The regional manager wants each store's revenue from completed orders, its rank, its share of the chain's total, and a running total from the best store down.
- sql:
    ```sql
    SELECT s.store_name,
           SUM(oi.unit_price * oi.quantity) AS revenue,
           RANK() OVER (ORDER BY SUM(oi.unit_price * oi.quantity) DESC) AS revenue_rank,
           ROUND(100 * RATIO_TO_REPORT(SUM(oi.unit_price * oi.quantity)) OVER (), 2) AS share_pct,
           SUM(SUM(oi.unit_price * oi.quantity))
               OVER (ORDER BY SUM(oi.unit_price * oi.quantity) DESC, s.store_name
                   ROWS UNBOUNDED PRECEDING) AS running_total
    FROM stores s
             JOIN orders o ON o.store_id = s.store_id
             JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.order_status = 'COMPLETE'
    GROUP BY s.store_id, s.store_name
    ORDER BY revenue_rank, s.store_name
    ```

### fix CO_SCHEMA_A_11
- section: SCHEMA   tier: Advanced
- title: This year's orders so far
- why: The lower bound uses `SYSDATE` (the database host's clock) and the upper bound `LOCALTIMESTAMP` (the session's time zone); around New Year they can disagree on which year it is. Take both from the same clock, as the JPQL does with one `:yearStart` and `LOCAL DATETIME`.
- request: Finance wants the number and value of the orders placed since the start of the current year, by month.
- sql:
    ```sql
    SELECT EXTRACT(MONTH FROM o.order_tms) AS order_month,
           COUNT(DISTINCT o.order_id) AS orders,
           SUM(oi.unit_price * oi.quantity) AS revenue
    FROM orders o
             JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.order_tms >= TRUNC(LOCALTIMESTAMP, 'YYYY')
      AND o.order_tms < LOCALTIMESTAMP
    GROUP BY EXTRACT(MONTH FROM o.order_tms)
    ORDER BY order_month
    ```

### fix CO_SCHEMA_I_08
- section: SCHEMA   tier: Intermediate
- title: Orders not fully shipped
- why: A cancelled or refunded order will never ship, so listing its unassigned lines gives logistics work that does not exist. The request should say it means the orders still to be fulfilled.
- request: Logistics wants the orders, other than cancelled or refunded ones, that still have lines with no shipment assigned, and how many such lines each has.
- sql:
    ```sql
    SELECT o.order_id, o.order_status, COUNT(*) AS unshipped_lines
    FROM orders o
             JOIN order_items oi ON oi.order_id = o.order_id
    WHERE oi.shipment_id IS NULL
      AND o.order_status NOT IN ('CANCELLED', 'REFUNDED')
    GROUP BY o.order_id, o.order_status
    ORDER BY unshipped_lines DESC, o.order_id
    ```

### fix CO_INVENTORY_B_02
- section: INVENTORY   tier: Basic
- title: Where a product is running lowest
- why: `SELECT *` drags `INVENTORY_ID` and the already-known `PRODUCT_ID` along, and the note admits the order is unstable among stores with the same stock but leaves it so; fix the query instead of the note.
- request: A merchandiser wants every store's stock of a product, lowest first, to see which stores need it replenished first.
- sql:
    ```sql
    SELECT store_id, product_inventory
    FROM inventory
    WHERE product_id = :productId
    ORDER BY product_inventory, store_id
    ```

### fix CO_CUSTOMERS_I_01
- section: CUSTOMERS   tier: Intermediate
- title: Email addresses that break the house style
- why: An address with no `@` (or one starting with it) makes `SUBSTR(..., INSTR(...) - 1)` empty, which Oracle treats as NULL, so `<>` is unknown and exactly the worst offenders are hidden. `EMAIL_ADDRESS` has no check constraint that would rule them out.
- request: Accounts are meant to be opened as `first.last@...`. Data quality wants the customers whose email address, before the `@`, is not their full name in lower case with the spaces turned into dots, including addresses that have nothing before an `@` or no `@` at all.
- sql:
    ```sql
    SELECT customer_id, full_name, email_address
    FROM customers
    WHERE INSTR(email_address, '@') <= 1
       OR SUBSTR(email_address, 1, INSTR(email_address, '@') - 1) <> LOWER(REPLACE(full_name, ' ', '.'))
    ORDER BY full_name
    ```

### fix CO_ORDERS_A_02
- section: ORDERS   tier: Advanced
- title: Time between a customer's orders
- why: `LAG(...) OVER (ORDER BY order_tms)` has no tie-break, so two orders placed at the same moment each may be the other's "previous" from run to run. CO_ORDERS_A_03 already breaks the same tie by `order_id`; do the same here.
- request: Customer care, looking at one customer, wants each of their orders next to the one before it, to see how often they come back.
- sql:
    ```sql
    SELECT order_id, order_tms,
           LAG(order_tms) OVER (ORDER BY order_tms, order_id) AS previous_order_tms,
           EXTRACT(DAY FROM order_tms - LAG(order_tms) OVER (ORDER BY order_tms, order_id)) AS days_since_previous
    FROM orders
    WHERE customer_id = :customerId
    ORDER BY order_tms, order_id
    ```

### fix CO_STORES_I_01
- section: STORES   tier: Intermediate
- title: Tidy store names for a sign
- why: In Oracle, `SUBSTR(store_name, -4)` returns NULL for a name shorter than four characters, while the JPQL `RIGHT(..., 4)` returns the whole name; the two answers diverge. `STORE_NAME` is only `NOT NULL`, nothing guarantees four characters.
- request: The signage team needs store names without spaces, for file names: `New York City` becomes `New-York-City`, and the last four characters of each (the whole name if shorter) are used as a short code.
- sql:
    ```sql
    SELECT store_name,
           REPLACE(store_name, ' ', '-') AS slug,
           UPPER(SUBSTR(store_name, -LEAST(4, LENGTH(store_name)))) AS short_code
    FROM stores
    ORDER BY store_name
    ```

### fix CO_SCHEMA_A_09
- section: SCHEMA   tier: Advanced
- title: Orders with a premium line
- why: The exercise asks two unrelated questions; the second ("products whose list price is above every price they were sold at") is a narrower case of CO_SCHEMA_I_05 (list price versus prices sold at). Keep the `ANY` question the title names and move the `> ALL` lesson into the note, or drop it.
- request: Finance wants the orders containing at least one line charged above `:price` per unit.
- sql:
    ```sql
    SELECT o.order_id, o.order_tms
    FROM orders o
    WHERE :price < ANY (SELECT oi.unit_price FROM order_items oi WHERE oi.order_id = o.order_id)
    ORDER BY o.order_id
    ```

### add CO_ORDERS_B_04
- section: ORDERS   tier: Basic
- title: The next page of a customer's order history
- why: No exercise pages past the first rows, though the module's conventions spell out how; a long order history on screen is the textbook case. Oracle's form is `OFFSET ... ROWS FETCH NEXT ... ROWS ONLY`, with a unique tie-break so pages neither repeat nor skip an order (`setFirstResult`/`setMaxResults` in JPQL).
- request: The account page shows a customer's orders `:pageSize` at a time, most recent first. Show the page that starts after the first `:offset` orders.
- sql:
    ```sql
    SELECT order_id, order_tms, order_status, store_id
    FROM orders
    WHERE customer_id = :customerId
    ORDER BY order_tms DESC, order_id DESC
    OFFSET :offset ROWS FETCH NEXT :pageSize ROWS ONLY
    ```

### add CO_SCHEMA_A_17
- section: SCHEMA   tier: Advanced
- title: Month-over-month sales
- why: Dates are only grouped, never compared across periods; `LAG` over an aggregate (rather than over rows, as in CO_ORDERS_A_02) is a staple finance question. `TRUNC(order_tms, 'MM')` keeps the month a date. Note that `LAG` takes the previous month that has sales, not the previous calendar month.
- request: Finance wants the revenue of completed orders per month, next to the month before and the change in per cent.
- sql:
    ```sql
    SELECT order_month, revenue,
           LAG(revenue) OVER (ORDER BY order_month) AS previous_revenue,
           ROUND(100 * (revenue - LAG(revenue) OVER (ORDER BY order_month))
                     / LAG(revenue) OVER (ORDER BY order_month), 1) AS change_pct
    FROM (SELECT TRUNC(o.order_tms, 'MM') AS order_month, SUM(oi.unit_price * oi.quantity) AS revenue
          FROM orders o
                   JOIN order_items oi ON oi.order_id = o.order_id
          WHERE o.order_status = 'COMPLETE'
          GROUP BY TRUNC(o.order_tms, 'MM'))
    ORDER BY order_month
    ```

### add CO_ORDER_ITEMS_I_02
- section: ORDER_ITEMS   tier: Intermediate
- title: Orders with gaps in their line numbers
- why: The DDL documents `LINE_ITEM_ID` as "an incrementing number, starting at one for each order" but does not enforce it; this is the check that guards the fact the receipt (CO_SCHEMA_B_02) relies on. With `(ORDER_ID, LINE_ITEM_ID)` the primary key, `MIN = 1` and `MAX = COUNT` together mean 1..n without gaps.
- request: Data quality wants the orders whose line numbers do not run 1, 2, 3, ... without gaps, with their number of lines and their first and last line number.
- sql:
    ```sql
    SELECT order_id, COUNT(*) AS lines, MIN(line_item_id) AS first_line, MAX(line_item_id) AS last_line
    FROM order_items
    GROUP BY order_id
    HAVING MIN(line_item_id) <> 1
        OR MAX(line_item_id) <> COUNT(*)
    ORDER BY order_id
    ```

### add CO_SCHEMA_A_18
- section: SCHEMA   tier: Advanced
- title: Shipments that carry nothing
- why: `ORDER_ITEMS.SHIPMENT_ID` is a nullable foreign key read only from the item side; no exercise asks the reverse, a shipment no line points to. Logistics would cancel such a shipment before a van leaves empty.
- request: Before dispatch, logistics wants the shipments that no order line is assigned to, with their store, customer and status.
- sql:
    ```sql
    SELECT sh.shipment_id, sh.store_id, sh.customer_id, sh.shipment_status
    FROM shipments sh
    WHERE NOT EXISTS (SELECT 1 FROM order_items oi WHERE oi.shipment_id = sh.shipment_id)
    ORDER BY sh.shipment_id
    ```

### add CO_PRODUCTS_B_04
- section: PRODUCTS   tier: Basic
- title: Products missing a fresh picture
- why: The image columns of `PRODUCTS` (`PRODUCT_IMAGE`, `IMAGE_LAST_UPDATED`, both nullable) are never queried; the web team's "which pictures are missing or out of date" is a natural `IS NULL` plus date-range question, with `NULLS FIRST` putting the products that never had one on top.
- request: The web team wants the products that have no picture, or whose picture was last changed before `:since`, those that never had one first.
- sql:
    ```sql
    SELECT product_id, product_name, image_filename, image_last_updated
    FROM products
    WHERE product_image IS NULL
       OR image_last_updated < :since
    ORDER BY image_last_updated NULLS FIRST, product_name
    ```
