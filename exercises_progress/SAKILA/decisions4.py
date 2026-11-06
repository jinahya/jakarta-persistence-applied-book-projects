import json
C = []
def fix(i, src, why, **kw): C.append(dict(op='fix', id=i, _src=src, _why=why, rerun=kw.pop('rerun', 'sql' in kw), **kw))
def add(i, src, why, **kw): C.append(dict(op='add', id=i, after=kw.pop('after', 'last'), _src=src, _why=why, rerun=True, **kw))
def rm(i, src, why): C.append(dict(op='remove', id=i, _src=src, _why=why))
JOINS = "FROM payment p\n         JOIN customer cu ON cu.customer_id = p.customer_id\n         JOIN address a ON a.address_id = cu.address_id\n         JOIN city ci ON ci.city_id = a.city_id\n         JOIN country co ON co.country_id = ci.country_id"
TABLES = ['actor', 'address', 'category', 'city', 'country', 'customer', 'film', 'film_actor', 'film_category', 'film_text', 'inventory', 'language', 'payment', 'rental', 'staff', 'store']

fix('SAKILA_SCHEMA_A_01', 'both', "RANK() gave a country with a tie two rows, so LIMIT 5 cut rows, not countries; the country was grouped by its name, which is not unique; no tie-break on the country's total",
    request=["Sum each customer's payments, and their country's.",
             "For each country, find the customer who paid the most, numbering the customers within the country with a window function (`ROW_NUMBER() OVER (PARTITION BY ...)`), the largest total first and ties by `customer_id`, and take the country's total with another (`SUM() OVER (PARTITION BY ...)`).",
             "Show, for the five countries which paid the most, the country, its top customer's `customer_id`, `first_name`, `last_name` and total, and the country's total, the largest country first; ties by `country_id`.",
             "`ROW_NUMBER` gives each country one first row, so `LIMIT 5` keeps five countries; `RANK` would give a tie two."],
    sql="WITH paid AS (SELECT co.country_id, co.country, cu.customer_id, cu.first_name, cu.last_name, SUM(p.amount) AS total\n" + "\n".join("              " + l for l in JOINS.split("\n")) + "\n              GROUP BY co.country_id, co.country, cu.customer_id, cu.first_name, cu.last_name),\n     ranked AS (SELECT paid.*,\n                       ROW_NUMBER() OVER (PARTITION BY country_id ORDER BY total DESC, customer_id) AS rank_in_country,\n                       SUM(total) OVER (PARTITION BY country_id)                                   AS country_total\n                FROM paid)\nSELECT country, customer_id, first_name, last_name, total, country_total\nFROM ranked\nWHERE rank_in_country = 1\nORDER BY country_total DESC, country_id\nLIMIT 5")
fix('SAKILA_SCHEMA_A_04', 'Codex', "the payments skip months (2005-09 to 2006-01), so LAG compared February 2006 with August 2005; a calendar of months fills the gap with 0",
    request=["Sum the payments of each month, written as `YYYY-MM`, from the first month with a payment to the last, a month without any included with `0`, and, for each month, the difference from the month before it, taken with `LAG`.",
             "The payments skip months, so a recursive `WITH` lists every month of the span first; `LAG` over the payment months alone would compare a month with an older one.",
             "The first month has none, so its difference is `NULL`.",
             "Show each month with its total and the difference."],
    sql="WITH RECURSIVE monthly AS (SELECT CAST(DATE_FORMAT(payment_date, '%Y-%m-01') AS DATE) AS month, SUM(amount) AS total\n                           FROM payment\n                           GROUP BY month),\n               months AS (SELECT MIN(month) AS month\n                          FROM monthly\n                          UNION ALL\n                          SELECT month + INTERVAL 1 MONTH\n                          FROM months\n                          WHERE month < (SELECT MAX(month) FROM monthly))\nSELECT DATE_FORMAT(m.month, '%Y-%m')                                           AS month,\n       COALESCE(p.total, 0)                                                    AS total,\n       COALESCE(p.total, 0) - LAG(COALESCE(p.total, 0)) OVER (ORDER BY m.month) AS change_from_previous\nFROM months m\n         LEFT JOIN monthly p ON p.month = m.month\nORDER BY m.month")
fix('SAKILA_SCHEMA_I_09', 'Codex', "a NULL length fell into ELSE 'long', as in SAKILA_FILM_I_03; the same 'unknown' group",
    request=["Sort the films into four groups by `length`: `short` under 60 minutes, `medium` from 60 to 120, `long` over 120, and `unknown` where `length` is NULL.",
             "Count the rentals of each group's films, through the copy, and sum their payments; a rental may have no payment, so the payments are joined with an outer join.",
             "Show each group with its count and sum, from the group of the shortest films to the group of the longest, `unknown` last.",
             "The group is a `CASE` expression, and the statement groups by it; a rental has one payment at most, which SAKILA_PAYMENT_B_06 checks, so `COUNT(*)` counts the rentals."],
    sql="SELECT CASE\n           WHEN f.length IS NULL THEN 'unknown'\n           WHEN f.length < 60 THEN 'short'\n           WHEN f.length <= 120 THEN 'medium'\n           ELSE 'long'\n           END       AS length_group,\n       COUNT(*)      AS rentals,\n       SUM(p.amount) AS total\nFROM rental r\n         JOIN inventory i ON i.inventory_id = r.inventory_id\n         JOIN film f ON f.film_id = i.film_id\n         LEFT JOIN payment p ON p.rental_id = r.rental_id\nGROUP BY length_group\nORDER BY CASE length_group WHEN 'short' THEN 1 WHEN 'medium' THEN 2 WHEN 'long' THEN 3 ELSE 4 END")
fix('SAKILA_RENTAL_A_02', 'both', "'in 2005' had no lower bound; rental_id joins the final tie-break",
    request=["For each rental made in 2005, find the same customer's rental just before it in 2005, and the number of days between the two.",
             "Show the five longest waits: the `customer_id`, the earlier and the later `rental_date`, and the days, the longest first; on a tie, by `customer_id`, then by the later `rental_date`, then by `rental_id`.",
             "The rental just before is `LAG(...) OVER (PARTITION BY customer_id ORDER BY rental_date, rental_id)`, over the rentals from January 1, 2005 up to January 1, 2006."],
    sql="SELECT customer_id, previous_rental, rental_date, DATEDIFF(rental_date, previous_rental) AS days\nFROM (SELECT rental_id,\n             customer_id,\n             rental_date,\n             LAG(rental_date) OVER (PARTITION BY customer_id ORDER BY rental_date, rental_id) AS previous_rental\n      FROM rental\n      WHERE rental_date >= '2005-01-01'\n        AND rental_date < '2006-01-01') g\nWHERE previous_rental IS NOT NULL\nORDER BY days DESC, customer_id, rental_date, rental_id\nLIMIT 5")
fix('SAKILA_RENTAL_B_04', 'both', 'LIMIT 1 with no tie-break',
    request=["Group the rentals by the name of the day of the week of `rental_date` (`Monday`, `Tuesday`, ...).",
             "Show the day on which the most rentals were made, with its count; on a tie, the day whose name comes first."],
    sql="SELECT DAYNAME(rental_date) AS day, COUNT(*) AS rentals\nFROM rental\nGROUP BY day\nORDER BY rentals DESC, day\nLIMIT 1")
fix('SAKILA_SCHEMA_I_03', 'both', 'a tie at the fifth place made LIMIT 5 unstable',
    request=["Sum the payments by the country of the customer who paid them, through the customer, the address and the city.",
             "Show the five countries which paid the most, each with the number of its distinct customers who paid and the sum, the largest first; ties by `country_id`."],
    sql="SELECT co.*, COUNT(DISTINCT cu.customer_id) AS customers, SUM(p.amount) AS total\n" + JOINS + "\nGROUP BY co.country_id\nORDER BY total DESC, co.country_id\nLIMIT 5")
fix('SAKILA_RENTAL_A_01', 'Claude', "late by the clock here, by calendar days in SAKILA_RENTAL_I_03 and in the schema's get_customer_balance; one rule, the schema's",
    request=["Each film has a `rental_duration`, the number of days a rental may last.",
             "Count the returned rentals which were out more calendar days than that, as the schema's `get_customer_balance` counts them: `DATEDIFF(return_date, rental_date)` is larger than the film's `rental_duration`.",
             "The duration is on the film, so the query goes from the rental through the copy to the film, and does arithmetic on dates."],
    sql="SELECT COUNT(*) AS late\nFROM rental r\n         JOIN inventory i ON i.inventory_id = r.inventory_id\n         JOIN film f ON f.film_id = i.film_id\nWHERE DATEDIFF(r.return_date, r.rental_date) > f.rental_duration")
fix('SAKILA_PAYMENT_B_05', 'Claude', "BETWEEN ... '23:59:59' holds only while payment_date has no fraction of a second; a half-open range holds for any",
    request=["Show the payments of the customer `1` whose `payment_date` falls in July 2005: the `payment_id`, `amount` and `payment_date`.",
             "Order them by `payment_date`, then by `payment_id`.",
             "`payment_date` has a time, so the range runs from July 1 inclusive up to August 1 exclusive."],
    sql="SELECT *\nFROM payment\nWHERE customer_id = 1\n  AND payment_date >= '2005-07-01'\n  AND payment_date < '2005-08-01'\nORDER BY payment_date, payment_id")
fix('SAKILA_SCHEMA_B_02', 'Claude', 'the rows of a UNION ALL come in no stated order',
    request=["Count the rows of each of the sixteen tables, and show each table's name with its count, one row per table, ordered by the name.",
             "`information_schema` gives only an estimate of the rows, so count them, one `SELECT` per table, joined with `UNION ALL`."],
    sql="SELECT 'actor' AS table_name, COUNT(*) AS row_count FROM actor\n" + "\n".join(f"UNION ALL SELECT '{t}', COUNT(*) FROM {t}" for t in TABLES[1:]) + "\nORDER BY table_name")
fix('SAKILA_SALES_BY_STORE_B_01', 'Claude', "the rows came in the view's own order, which a query of the view need not keep",
    request=["The `sales_by_store` view sums the payments of each store, and names the store by its city and country, and its manager.",
             "Show every row: the `store`, the `manager` and the `total_sales`, ordered by `store`."],
    sql="SELECT *\nFROM sales_by_store\nORDER BY store")

add('SAKILA_PAYMENT_B_06', 'Claude', 'SAKILA_SCHEMA_I_07 and I_09 count rentals with COUNT(*) over rental LEFT JOIN payment, right only if a rental has one payment, which no key enforces',
    title='the rentals paid more than once',
    request=["`payment.rental_id` is not unique in the schema, while SAKILA_SCHEMA_I_07 and I_09 count the rentals joined to their payments as if a rental had one payment at most.",
             "Find the rentals which have more than one payment: each `rental_id` with its number of payments, ordered by `rental_id`; the check passes when nothing comes back."],
    sql="SELECT rental_id, COUNT(*) AS payments\nFROM payment\nWHERE rental_id IS NOT NULL\nGROUP BY rental_id\nHAVING COUNT(*) > 1\nORDER BY rental_id")
add('SAKILA_PAYMENT_I_04', 'Claude', "payment and rental both name the customer, and nothing makes them agree, nor a payment no earlier than its rental",
    title='the payments which do not agree with their rental',
    request=["A payment names its customer, and so does the rental it pays for; nothing in the schema makes them the same, or the payment no earlier than the rental.",
             "Count the payments whose customer is not their rental's customer, and those made before their rental, in one row; both counts are `0` when the data agrees."],
    sql="SELECT SUM(CASE WHEN p.customer_id <> r.customer_id THEN 1 ELSE 0 END) AS other_customer,\n       SUM(CASE WHEN p.payment_date < r.rental_date THEN 1 ELSE 0 END) AS before_rental\nFROM payment p\n         JOIN rental r ON r.rental_id = p.rental_id")
add('SAKILA_SALES_BY_STORE_A_01', 'both', 'SALES_BY_STORE has no Advanced exercise; a window over the whole result, SUM() OVER ()',
    title="each store's share of all sales",
    file_header="Exercises at the advanced level on sales_by_store: a window over the whole result. Each poses a question, answers it, and shows what the installed data gives back.",
    request=["Show every row of `sales_by_store` with the store's share of the sum of all stores' `total_sales`, as a percentage rounded to two decimal places, the largest first; ties by `store`.",
             "`SUM(...) OVER ()`, a window with no partition and no order, gives every row the sum of all rows."],
    sql="SELECT v.*, ROUND(100 * v.total_sales / SUM(v.total_sales) OVER (), 2) AS percent\nFROM sales_by_store v\nORDER BY v.total_sales DESC, v.store")
add('SAKILA_SCHEMA_A_10', 'Claude', 'SAKILA_SCHEMA_B_06 lists the stored functions, but no exercise calls one',
    title='the five customers who owed the most at the end of the data',
    request=["The function `get_customer_balance(customer_id, date)` gives what a customer owes on a date: the rates of the films rented, a late fee for each day over the rental duration, less the payments made.",
             "Take 2006-02-15, the day after the last rental, and show the five customers who owed the most: the customer and the balance, the largest first; ties by `customer_id`.",
             "A query calls a stored function as it calls a built-in one."],
    sql="SELECT c.*, get_customer_balance(c.customer_id, '2006-02-15') AS balance\nFROM customer c\nORDER BY balance DESC, c.customer_id\nLIMIT 5")
add('SAKILA_SCHEMA_I_14', 'Codex', "SAKILA_SALES_BY_STORE_I_02 joins by the manager's name, which no key makes unique",
    title="the manager names of sales_by_store which more than one staff member has",
    request=["`sales_by_store` names each store's manager by first and last name, and SAKILA_SALES_BY_STORE_I_02 joins back to `staff` by that name, which nothing makes unique.",
             "Find the manager names of the view which more than one staff member has, with how many, ordered by the name; the check passes when nothing comes back."],
    sql="SELECT CONCAT(s.first_name, ' ', s.last_name) AS manager, COUNT(*) AS staff_members\nFROM staff s\nWHERE EXISTS (SELECT 1 FROM sales_by_store v WHERE v.manager = CONCAT(s.first_name, ' ', s.last_name))\nGROUP BY CONCAT(s.first_name, ' ', s.last_name)\nHAVING COUNT(*) > 1\nORDER BY manager")

rm('SAKILA_SCHEMA_A_03', 'Claude', 'a running total over payment alone, which SAKILA_PAYMENT_A_01 teaches already')
json.dump({'module': 'mysql-sakila-persistence', 'changes': C}, open('decisions4.json', 'w'), indent=1, ensure_ascii=False)
print(len(C), 'changes')
