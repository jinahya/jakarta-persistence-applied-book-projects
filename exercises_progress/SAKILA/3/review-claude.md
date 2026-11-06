# SAKILA batch 3 — Claude's review

### fix SAKILA_STAFF_I_01
- section: STAFF   tier: Intermediate
- title: how many rentals each staff member handled
- why: The request asks for each staff member, but the inner join drops a staff member who handled no rental (nothing in the DDL prevents one, e.g. a newly hired clerk). An outer join with `COUNT(r.rental_id)` answers the question as asked and shows `0`.
- request: Count the rentals each staff member handled, by `rental.staff_id`; show every staff member with the count, `0` for one who handled none, ordered by `staff_id`.
- sql:
    SELECT s.staff_id, s.first_name, s.last_name, s.address_id, s.email, s.store_id, s.active, s.username, s.password, s.last_update, COUNT(r.rental_id) AS rentals -- every column but picture, a BLOB which does not print
    FROM staff s
             LEFT JOIN rental r ON r.staff_id = s.staff_id
    GROUP BY s.staff_id
    ORDER BY s.staff_id

### fix SAKILA_STAFF_I_03
- section: STAFF   tier: Intermediate
- title: how many rentals each staff member handled for their own store's copies, and for the other's
- why: Same defect as STAFF_I_01: "for each staff member" with inner joins loses a staff member with no rental. With outer joins the `CASE` falls to `ELSE 0` on the null-extended row, so both counts come out `0`.
- request: For each staff member, count the rentals they handled whose copy is at their own store, and those whose copy is elsewhere; a staff member with no rental shows two zeros. Order by `staff_id`.
- sql:
    SELECT s.staff_id, s.first_name, s.last_name, s.address_id, s.email, s.store_id, s.active, s.username, s.password, s.last_update, -- every column but picture, a BLOB which does not print
           SUM(CASE WHEN i.store_id = s.store_id THEN 1 ELSE 0 END) AS own_store,
           SUM(CASE WHEN i.store_id <> s.store_id THEN 1 ELSE 0 END) AS other_store
    FROM staff s
             LEFT JOIN rental r ON r.staff_id = s.staff_id
             LEFT JOIN inventory i ON i.inventory_id = r.inventory_id
    GROUP BY s.staff_id
    ORDER BY s.staff_id

### fix SAKILA_STAFF_LIST_I_02
- section: STAFF_LIST   tier: Intermediate
- title: whether each staff member lives in the city of their store
- why: The title asks "whether", but the SQL only lists two cities side by side and never compares them; it also leaves out the store's country, which the comparison needs because city names repeat across countries (CITY_I_05).
- request: For each row of `staff_list`, show the city and country the staff member lives in, the city and country of the store they work at (`SID`), and whether the two are the same, ordered by `ID`.
- sql:
    SELECT l.*, ci.city AS store_city, co.country AS store_country,
           (l.city = ci.city AND l.country = co.country) AS lives_in_store_city
    FROM staff_list l
             JOIN store st ON st.store_id = l.SID
             JOIN address a ON a.address_id = st.address_id
             JOIN city ci ON ci.city_id = a.city_id
             JOIN country co ON co.country_id = ci.country_id
    ORDER BY l.ID

### fix SAKILA_CUSTOMER_B_03
- section: CUSTOMER   tier: Basic
- title: the domains of the customers' emails
- why: The query has no `ORDER BY`, so the order of the groups is unspecified; every other grouped exercise orders by the count and then the key.
- request: Take the part of each customer's `email` after the `@` as the domain, and show each domain with the number of its customers, the most first; domains with the same number are ordered by name.
- sql:
    SELECT SUBSTRING_INDEX(email, '@', -1) AS domain, COUNT(*) AS customers
    FROM customer
    GROUP BY domain
    ORDER BY customers DESC, domain

### add SAKILA_CUSTOMER_I_06
- section: CUSTOMER   tier: Intermediate
- title: the five customers who returned late most often
- why: Nothing in the batch uses `film.rental_duration` against the rental dates, the schema's own notion of lateness (`get_customer_balance` counts a rental late when the days between `rental_date` and `return_date` exceed it). It walks rental, inventory and film, and the nullable `return_date` drops out of the comparison by itself.
- request: A rental is late when it was returned more days after it was rented than its film's `rental_duration`. Show the five customers with the most late returns, with their counts, the most first; ties are ordered by `customer_id`.
- sql:
    SELECT c.*, COUNT(*) AS late_returns
    FROM customer c
             JOIN rental r ON r.customer_id = c.customer_id
             JOIN inventory i ON i.inventory_id = r.inventory_id
             JOIN film f ON f.film_id = i.film_id
    WHERE DATEDIFF(r.return_date, r.rental_date) > f.rental_duration
    GROUP BY c.customer_id
    ORDER BY late_returns DESC, c.customer_id
    LIMIT 5

### add SAKILA_CUSTOMER_A_04
- section: CUSTOMER   tier: Advanced
- title: the five customers with the longest gap between two rentals
- why: The Advanced exercises use ranking and running windows, but none uses `LAG` over dates, which `rental.rental_date` makes natural. The `rental_id` tie-break matters because `rental_date` is not unique per customer (the unique key also holds `inventory_id`).
- request: For each customer, take the days between each rental and the customer's previous one, and keep the longest. Show the five customers with the longest gap, with the gap in days, the longest first; ties are ordered by `customer_id`.
- sql:
    WITH gaps AS (SELECT r.customer_id,
                         DATEDIFF(r.rental_date,
                                  LAG(r.rental_date) OVER (PARTITION BY r.customer_id ORDER BY r.rental_date, r.rental_id)) AS gap_days
                  FROM rental r)
    SELECT c.*, MAX(g.gap_days) AS longest_gap
    FROM customer c
             JOIN gaps g ON g.customer_id = c.customer_id
    GROUP BY c.customer_id
    ORDER BY longest_gap DESC, c.customer_id
    LIMIT 5

### add SAKILA_COUNTRY_I_05
- section: COUNTRY   tier: Intermediate
- title: the country names found more than once
- why: COUNTRY_B_02 says the names are unique so no tie-break is needed, and COUNTRY_A_01 and A_02 order their windows and results by the name, but `country.country` has no unique key in the DDL. A check that guards the fact is better than a tie-break in every exercise; the installed data should give no row.
- request: Find the country names that more than one row of `country` has, with how many rows have each, ordered by the name.
- sql:
    SELECT country, COUNT(*) AS countries
    FROM country
    GROUP BY country
    HAVING COUNT(*) > 1
    ORDER BY country

### add SAKILA_ADDRESS_B_05
- section: ADDRESS   tier: Basic
- title: how many addresses have no postal code, as NULL and as an empty string
- why: `postal_code` is nullable (`DEFAULT NULL`), and ADDRESS_A_02 leaves out only the empty one; no exercise shows that a missing postal code can take both forms, or that `= ''` is not true for `NULL`.
- request: Count the addresses whose `postal_code` is `NULL`, and, apart, those whose `postal_code` is the empty string, in one row.
- sql:
    SELECT SUM(postal_code IS NULL) AS null_postal_codes,
           SUM(postal_code = '')    AS empty_postal_codes
    FROM address

### add SAKILA_CUSTOMER_LIST_B_05
- section: CUSTOMER_LIST   tier: Basic
- title: the first ten customers in the United States by zip code
- why: The view's `zip code` column has a space in its name, and no exercise reads it; a reader must learn to quote it with backticks. It is also nullable (from `address.postal_code`), and MySQL puts `NULL` first in an ascending order.
- request: Show the first ten customers in the United States, the whole rows of the view, ordered by their zip code and then by `ID`.
- sql:
    SELECT *
    FROM customer_list
    WHERE country = 'United States'
    ORDER BY `zip code`, ID
    LIMIT 10

### remove SAKILA_CUSTOMER_LIST_I_03
- section: CUSTOMER_LIST   tier: Intermediate
- title: the rows whose name is not the customer's first and last name
- why: The view defines `name` as exactly `CONCAT(cu.first_name, ' ', cu.last_name)`, so the query is a tautology that can never return a row; no user would ask it.

### remove SAKILA_ADDRESS_A_01
- section: ADDRESS   tier: Advanced
- title: the addresses no customer, staff member or store has
- why: ADDRESS_I_03 already answers the same question: its `none` class is exactly these addresses, counted. Three `NOT EXISTS` is no harder than I_03's `CASE` of `EXISTS`, so the exercise is not Advanced either. A_02 and A_03 keep the tier populated.
