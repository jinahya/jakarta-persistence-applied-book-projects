# SAKILA batch 4 — Claude's review

### fix SAKILA_SCHEMA_A_01
- section: SCHEMA   tier: Advanced
- title: the customer who paid the most in each of the five countries which paid the most
- why: `RANK()` gives every tied customer rank 1, so a country with a tie returns two rows and `LIMIT 5` then cuts rows, not countries; there is also no tie-break on `country_total`, and grouping by the name `country` merges any two countries of the same name (`country.country` is not unique in the DDL). Rank with `ROW_NUMBER()` and a stated tie-break, partition by `country_id`, and break ties in the final order.
- request: Sum each customer's payments, and their country's. For each country, find the customer who paid the most, numbering the customers within the country with `ROW_NUMBER() OVER (PARTITION BY ...)`, the largest total first and ties by `customer_id`, and take the country's total with `SUM() OVER (PARTITION BY ...)`. Show, for the five countries which paid the most, the country, its top customer's `customer_id`, `first_name`, `last_name` and total, and the country's total, the largest country first; ties by `country_id`.
- sql:
    WITH paid AS (SELECT co.country_id, co.country, cu.customer_id, cu.first_name, cu.last_name, SUM(p.amount) AS total
                  FROM payment p
                           JOIN customer cu ON cu.customer_id = p.customer_id
                           JOIN address a ON a.address_id = cu.address_id
                           JOIN city ci ON ci.city_id = a.city_id
                           JOIN country co ON co.country_id = ci.country_id
                  GROUP BY co.country_id, co.country, cu.customer_id, cu.first_name, cu.last_name),
         ranked AS (SELECT paid.*,
                           ROW_NUMBER() OVER (PARTITION BY country_id ORDER BY total DESC, customer_id) AS rank_in_country,
                           SUM(total) OVER (PARTITION BY country_id) AS country_total
                    FROM paid)
    SELECT country, customer_id, first_name, last_name, total, country_total
    FROM ranked
    WHERE rank_in_country = 1
    ORDER BY country_total DESC, country_id
    LIMIT 5

### fix SAKILA_RENTAL_A_01
- section: RENTAL   tier: Advanced
- title: how many rentals came back later than the film's rental duration allows
- why: The exercise counts a rental as late by the clock (`rental_date + INTERVAL n DAY`), while SAKILA_RENTAL_I_03 counts overdue days with `DATEDIFF`, and the schema's own `get_customer_balance` charges late fees by calendar days (`TO_DAYS(return_date) - TO_DAYS(rental_date) > rental_duration`). Two definitions of "late" in one unit give two different answers to the same question; follow the schema's rule.
- request: Each film has a `rental_duration`, the number of days a rental may last. Count the returned rentals which were out more calendar days than that, as the schema's `get_customer_balance` counts them: `DATEDIFF(return_date, rental_date)` is larger than the film's `rental_duration`. The duration is on the film, so the query goes from the rental through the copy to the film.
- sql:
    SELECT COUNT(*) AS late
    FROM rental r
             JOIN inventory i ON i.inventory_id = r.inventory_id
             JOIN film f ON f.film_id = i.film_id
    WHERE DATEDIFF(r.return_date, r.rental_date) > f.rental_duration

### fix SAKILA_RENTAL_B_04
- section: RENTAL   tier: Basic
- title: on which day of the week the most rentals were made
- why: `ORDER BY rentals DESC LIMIT 1` has no tie-break, so on a tie the row returned is unspecified; the exercise is checked by a test, which needs one stable answer.
- request: Group the rentals by the name of the day of the week of `rental_date` (`Monday`, `Tuesday`, ...). Show the day on which the most rentals were made, with its count; on a tie, the day whose name comes first.
- sql:
    SELECT DAYNAME(rental_date) AS day, COUNT(*) AS rentals
    FROM rental
    GROUP BY day
    ORDER BY rentals DESC, day
    LIMIT 1

### fix SAKILA_SCHEMA_I_03
- section: SCHEMA   tier: Intermediate
- title: the five countries whose customers paid the most
- why: `ORDER BY total DESC LIMIT 5` has no tie-break, so a tie at the fifth place makes the result unstable.
- request: Sum the payments by the country of the customer who paid them, through the customer, the address and the city. Show the five countries which paid the most, each with the number of its distinct customers who paid and the sum, the largest first; ties by `country_id`.
- sql:
    SELECT co.*, COUNT(DISTINCT cu.customer_id) AS customers, SUM(p.amount) AS total
    FROM payment p
             JOIN customer cu ON cu.customer_id = p.customer_id
             JOIN address a ON a.address_id = cu.address_id
             JOIN city ci ON ci.city_id = a.city_id
             JOIN country co ON co.country_id = ci.country_id
    GROUP BY co.country_id
    ORDER BY total DESC, co.country_id
    LIMIT 5

### fix SAKILA_PAYMENT_B_05
- section: PAYMENT   tier: Basic
- title: the payments of the customer 1 in July 2005
- why: `BETWEEN ... '23:59:59'` is correct only while `payment_date` is `DATETIME` without fractional seconds; the half-open range `>= July 1 AND < August 1` is right for any precision and is the form a reader should learn (and the one JPQL/Criteria answers carry over unchanged).
- request: Show the payments of the customer `1` whose `payment_date` falls in July 2005, ordered by `payment_date`, then by `payment_id`. `payment_date` has a time, so take the range from July 1 inclusive up to August 1 exclusive.
- sql:
    SELECT *
    FROM payment
    WHERE customer_id = 1
      AND payment_date >= '2005-07-01'
      AND payment_date < '2005-08-01'
    ORDER BY payment_date, payment_id

### fix SAKILA_RENTAL_A_02
- section: RENTAL   tier: Advanced
- title: the five longest waits between a customer's two rentals in 2005
- why: The request says "in 2005", but the filter is only `rental_date < '2006-01-01'`; it has no lower bound and so answers "before 2006". Bound both ends.
- request: For each rental made in 2005, find the same customer's rental just before it in 2005, and the number of days between the two. Show the five longest waits: the `customer_id`, the earlier and the later `rental_date`, and the days, the longest first; on a tie, by `customer_id`, then by the later `rental_date`.
- sql:
    SELECT customer_id, previous_rental, rental_date, DATEDIFF(rental_date, previous_rental) AS days
    FROM (SELECT customer_id, rental_date,
                 LAG(rental_date) OVER (PARTITION BY customer_id ORDER BY rental_date, rental_id) AS previous_rental
          FROM rental
          WHERE rental_date >= '2005-01-01'
            AND rental_date < '2006-01-01') g
    WHERE previous_rental IS NOT NULL
    ORDER BY days DESC, customer_id, rental_date
    LIMIT 5

### fix SAKILA_SCHEMA_B_02
- section: SCHEMA   tier: Basic
- title: how many rows each table has
- why: The order of the rows of a `UNION ALL` is not guaranteed without an `ORDER BY`; the output is checked by a test, so state the order.
- request: Count the rows of each of the sixteen tables, and show each table's name with its count, one row per table, ordered by the name. `information_schema` gives only an estimate of the rows, so count them, one `SELECT` per table, joined with `UNION ALL`.
- sql:
    SELECT 'actor' AS table_name, COUNT(*) AS row_count FROM actor
    UNION ALL SELECT 'address', COUNT(*) FROM address
    UNION ALL SELECT 'category', COUNT(*) FROM category
    UNION ALL SELECT 'city', COUNT(*) FROM city
    UNION ALL SELECT 'country', COUNT(*) FROM country
    UNION ALL SELECT 'customer', COUNT(*) FROM customer
    UNION ALL SELECT 'film', COUNT(*) FROM film
    UNION ALL SELECT 'film_actor', COUNT(*) FROM film_actor
    UNION ALL SELECT 'film_category', COUNT(*) FROM film_category
    UNION ALL SELECT 'film_text', COUNT(*) FROM film_text
    UNION ALL SELECT 'inventory', COUNT(*) FROM inventory
    UNION ALL SELECT 'language', COUNT(*) FROM language
    UNION ALL SELECT 'payment', COUNT(*) FROM payment
    UNION ALL SELECT 'rental', COUNT(*) FROM rental
    UNION ALL SELECT 'staff', COUNT(*) FROM staff
    UNION ALL SELECT 'store', COUNT(*) FROM store
    ORDER BY table_name

### fix SAKILA_SALES_BY_STORE_B_01
- section: SALES_BY_STORE   tier: Basic
- title: every store's sales
- why: The rows come out in the order of the view's own `ORDER BY`, which MySQL may drop once the view is merged into an outer query; the exercise should state its order, as SAKILA_SALES_BY_STORE_I_02 does (`ORDER BY store`).
- request: The `sales_by_store` view sums the payments of each store, and names the store by its city and country, and its manager. Show every row: the `store`, the `manager` and the `total_sales`, ordered by `store`.
- sql:
    SELECT *
    FROM sales_by_store
    ORDER BY store

### add SAKILA_PAYMENT_B_06
- section: PAYMENT   tier: Basic
- title: the rentals paid more than once
- why: SAKILA_SCHEMA_I_07 and SAKILA_SCHEMA_I_09 count rentals with `COUNT(*)` over `rental LEFT JOIN payment`, which is right only if no rental has two payments; the DDL does not enforce it (`payment.rental_id` has no unique key). A check guards the fact once, instead of a `COUNT(DISTINCT ...)` in every exercise; the installed data gives no row.
- request: `payment.rental_id` is not unique in the DDL. Find the rentals which have more than one payment: each `rental_id` with its number of payments, ordered by `rental_id`.
- sql:
    SELECT rental_id, COUNT(*) AS payments
    FROM payment
    WHERE rental_id IS NOT NULL
    GROUP BY rental_id
    HAVING COUNT(*) > 1
    ORDER BY rental_id

### add SAKILA_PAYMENT_I_04
- section: PAYMENT   tier: Intermediate
- title: the payments which do not agree with their rental
- why: `payment` and `rental` both carry `customer_id`, and nothing in the DDL makes a payment's customer the rental's customer, or its date no earlier than the rental's. The exercises that reach a customer through either path rely on it; a check makes the redundancy, and the fact, visible.
- request: A payment names its customer, and so does the rental it pays for. Count the payments with a rental whose customer is not the rental's customer, and those made before the rental, in one row.
- sql:
    SELECT SUM(CASE WHEN p.customer_id <> r.customer_id THEN 1 ELSE 0 END) AS other_customer,
           SUM(CASE WHEN p.payment_date < r.rental_date THEN 1 ELSE 0 END) AS before_rental
    FROM payment p
             JOIN rental r ON r.rental_id = p.rental_id

### add SAKILA_RENTAL_I_04
- section: RENTAL   tier: Intermediate
- title: how many rentals each staff member handled, and how many are still out
- why: `rental.staff_id` and its foreign key to `staff` are used by no exercise, and RENTAL has only two Intermediate exercises left. Conditional counting over the nullable `return_date` is a common question.
- request: Group the rentals by the staff member who handled them. Show each staff member with the number of rentals and the number of them not returned yet, ordered by `staff_id`.
- sql:
    SELECT s.staff_id, s.first_name, s.last_name, s.address_id, s.email, s.store_id, s.active, s.username, s.password, s.last_update, COUNT(*) AS rentals, -- every column but picture, a BLOB which does not print
           SUM(CASE WHEN r.return_date IS NULL THEN 1 ELSE 0 END) AS not_returned
    FROM rental r
             JOIN staff s ON s.staff_id = r.staff_id
    GROUP BY s.staff_id
    ORDER BY s.staff_id

### add SAKILA_SALES_BY_STORE_A_01
- section: SALES_BY_STORE   tier: Advanced
- title: each store's share of all sales
- why: SALES_BY_STORE has no Advanced exercise. A view's rows are a natural place for a window over the whole result, `SUM() OVER ()`, which no exercise uses without a partition or an order.
- request: Show every row of `sales_by_store` with the store's share of the sum of all stores' `total_sales`, as a percentage rounded to two decimal places, the largest first; ties by `store`.
- sql:
    SELECT v.*, ROUND(100 * v.total_sales / SUM(v.total_sales) OVER (), 2) AS percent
    FROM sales_by_store v
    ORDER BY v.total_sales DESC, v.store

### add SAKILA_SCHEMA_A_10
- section: SCHEMA   tier: Advanced
- title: the five customers who owed the most at the end of the data
- why: SAKILA_SCHEMA_B_06 lists the stored functions, but no exercise calls one. `get_customer_balance` folds rentals, films' rates, late days and payments into one number, a question a real user asks, and calling a function in a query is a feature of its own.
- request: The function `get_customer_balance(customer_id, date)` gives what a customer owes on a date: the rates of the films rented, a late fee for each day over the rental duration, less the payments made. Take 2006-02-15, the day after the last rental, and show the five customers who owed the most: the customer and the balance, the largest first; ties by `customer_id`.
- sql:
    SELECT c.*, get_customer_balance(c.customer_id, '2006-02-15') AS balance
    FROM customer c
    ORDER BY balance DESC, c.customer_id
    LIMIT 5

### remove SAKILA_SCHEMA_A_03
- section: SCHEMA   tier: Advanced
- title: the running total of the payments, on the first five days
- why: It reads `payment` alone and teaches the same thing as SAKILA_PAYMENT_A_01, a running total with `SUM(...) OVER (ORDER BY ...)`; the daily grouping adds nothing the other window exercises (SAKILA_SCHEMA_A_04, SAKILA_PAYMENT_A_02) lack. Its `LIMIT 5` is also mis-indented.
