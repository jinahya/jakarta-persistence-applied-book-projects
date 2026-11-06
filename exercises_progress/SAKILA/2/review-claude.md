# SAKILA batch 2 — Claude's review

### fix SAKILA_FILM_LIST_I_01
- section: FILM_LIST   tier: Intermediate
- title: whether the view has a row for every film which has a category
- why: The request says the view joins `film_category` and `category` with inner joins, but the DDL uses `LEFT JOIN`s, so a film with no category still has a row (with `category` `NULL`). The comparison is only right if the view's rows without a category are left out, and the text has to say so.
- request: The view joins `film` with `film_category` and `category` by outer joins, so a film without a category still has a row whose `category` is `NULL`. Count the rows of the view which have a category, and the distinct films of `film_category`, and show both in one row, with the view's rows without a category in a third column.
- sql:
    SELECT (SELECT COUNT(*) FROM film_list WHERE category IS NOT NULL) AS film_list,
           (SELECT COUNT(DISTINCT film_id) FROM film_category)        AS films_with_a_category,
           (SELECT COUNT(*) FROM film_list WHERE category IS NULL)     AS film_list_without_a_category

### fix SAKILA_SALES_BY_FILM_CATEGORY_B_01
- section: SALES_BY_FILM_CATEGORY   tier: Basic
- title: the three categories which sold the most
- why: The top 3 comes only from the `ORDER BY` inside the view's definition. That order is not guaranteed when the view is queried, cannot be carried over to JPQL or the Criteria API, and has no tie-breaker.
- request: The `sales_by_film_category` view sums the payments of each category. Show the three categories which sold the most, with their `total_sales`, the most first; on a tie, by `category`.
- sql:
    SELECT *
    FROM sales_by_film_category
    ORDER BY total_sales DESC, category
    LIMIT 3

### fix SAKILA_NICER_BUT_SLOWER_FILM_LIST_A_01
- section: NICER_BUT_SLOWER_FILM_LIST   tier: Advanced
- title: how many rows differ from film_list, column by column, but for the actors
- why: Both views are built with outer joins, so `category` is `NULL` for a film without a category. `l.category = n.category` drops those rows from the join, so the check misses them. The exercise asks for null-safe comparison but does not use it in the one place where it matters.
- request: The two views should differ only in how the actors are written. Join them row by row, by `FID` and `category`, and count the rows where any other column (`title`, `description`, `price`, `length`, `rating`) differs. `category` and the other columns may be `NULL`, so compare all of them, the join included, with the null-safe `<=>`. The answer is `0`.
- sql:
    SELECT COUNT(*) AS differing
    FROM nicer_but_slower_film_list n
             JOIN film_list l ON l.FID = n.FID AND l.category <=> n.category
    WHERE NOT (n.title <=> l.title AND n.description <=> l.description AND n.price <=> l.price
               AND n.length <=> l.length AND n.rating <=> l.rating)

### fix SAKILA_CATEGORY_I_02
- section: CATEGORY   tier: Intermediate
- title: the category whose films are, on average, the longest
- why: `ORDER BY average_length DESC LIMIT 1` has no tie-breaker, and it orders by the rounded value. Two categories whose averages differ only after the second decimal place tie, and the row returned is arbitrary.
- request: For each category, take the average `length` of its films, and find the category whose average is the largest. Show its name and the average, rounded to two decimal places. Order the groups by the unrounded average, then by name, and keep only the first.
- sql:
    SELECT c.*, ROUND(AVG(f.length), 2) AS average_length
    FROM category c
             JOIN film_category fc ON fc.category_id = c.category_id
             JOIN film f ON f.film_id = fc.film_id
    GROUP BY c.category_id
    ORDER BY AVG(f.length) DESC, c.name
    LIMIT 1

### fix SAKILA_NICER_BUT_SLOWER_FILM_LIST_A_02
- section: NICER_BUT_SLOWER_FILM_LIST   tier: Advanced
- title: the longest length in each category, and how many films have it
- why: The view's `category` is `NULL` for a film without a category (outer joins). The correlated `m.category = n.category` never matches that group, so the `NULL` category silently drops out of the answer.
- request: For each category, the films without one included, find the longest `length` of its films, and count the films which are exactly that long. Show the `category`, the longest length and the count, ordered by `category`. A row is kept when its length equals the maximum of its own category, which is a correlated subquery comparing the categories with `<=>`.
- sql:
    SELECT n.category, n.length AS longest, COUNT(*) AS films
    FROM nicer_but_slower_film_list n
    WHERE n.length = (SELECT MAX(m.length) FROM nicer_but_slower_film_list m WHERE m.category <=> n.category)
    GROUP BY n.category, n.length
    ORDER BY n.category

### add SAKILA_FILM_LIST_A_02
- section: FILM_LIST   tier: Advanced
- title: the films with the most actors in each category
- why: FILM_LIST has no Advanced exercise left (A_01 is retired), so the level is empty. This one uses the view's own `actors` string and adds a top-n per group with `RANK()`, keeping ties.
- request: Count each film's actors from the view's `actors` string, one more than its commas, or `0` when it is `NULL`. In each category, find the films with the most actors, all of them when several tie. Show the `category`, `FID`, `title` and the number of actors, ordered by `category` and then by `FID`.
- sql:
    WITH counted AS (SELECT category, FID, title,
                            CASE WHEN actors IS NULL THEN 0
                                 ELSE LENGTH(actors) - LENGTH(REPLACE(actors, ',', '')) + 1 END AS actor_count
                     FROM film_list)
    SELECT category, FID, title, actor_count
    FROM (SELECT counted.*,
                 RANK() OVER (PARTITION BY category ORDER BY actor_count DESC) AS actor_rank
          FROM counted) ranked
    WHERE actor_rank = 1
    ORDER BY category, FID

### add SAKILA_INVENTORY_I_06
- section: INVENTORY   tier: Intermediate
- title: the copies which are out on more than one rental at once
- why: I_03 counts open rentals as copies out, and I_05 and A_01 assume one open rental per copy. The DDL does not enforce this. A check guards the fact once, so no exercise needs a `COUNT(DISTINCT ...)` workaround. The installed data should have none.
- request: A copy can be out on only one rental at a time. Find the copies which have more than one rental with no `return_date`. Show the whole rows with their number of open rentals, ordered by `inventory_id`.
- sql:
    SELECT i.*, COUNT(*) AS open_rentals
    FROM inventory i
             JOIN rental r ON r.inventory_id = i.inventory_id
    WHERE r.return_date IS NULL
    GROUP BY i.inventory_id
    HAVING COUNT(*) > 1
    ORDER BY i.inventory_id

### add SAKILA_INVENTORY_A_03
- section: INVENTORY   tier: Advanced
- title: the ten copies most overdue, as of the last rental
- why: `film.rental_duration` is never used, but overdue copies are the first thing a rental-store user asks about. The exercise uses date arithmetic against a per-row duration and a fixed point of reference, so the answer does not change with the clock.
- request: Take the date of the last rental in the data as "now". A copy is overdue when its open rental (no `return_date`) is older than its film's `rental_duration` in days. Show the ten most overdue: the `rental_id`, `inventory_id`, the film's `title`, the `rental_date` and the days overdue, the most first; ties are ordered by `rental_id`.
- sql:
    SELECT r.rental_id, i.inventory_id, f.title, r.rental_date,
           DATEDIFF(m.last_rental, r.rental_date) - f.rental_duration AS days_overdue
    FROM rental r
             JOIN inventory i ON i.inventory_id = r.inventory_id
             JOIN film f ON f.film_id = i.film_id
             CROSS JOIN (SELECT MAX(rental_date) AS last_rental FROM rental) m
    WHERE r.return_date IS NULL
      AND r.rental_date + INTERVAL f.rental_duration DAY < m.last_rental
    ORDER BY days_overdue DESC, r.rental_id
    LIMIT 10

### add SAKILA_FILM_CATEGORY_B_03
- section: FILM_CATEGORY   tier: Basic
- title: the films of the Comedy category
- why: The link table's main use, listing the films of a category by name across both foreign keys, has no Basic exercise. The current Basic exercises only count `category_id`s or list raw id pairs.
- request: Find the films whose category is `Comedy`, through `film_category`. Show the films' whole rows, ordered by `title`; ties are ordered by `film_id`.
- sql:
    SELECT f.*
    FROM film f
             JOIN film_category fc ON fc.film_id = f.film_id
             JOIN category c ON c.category_id = fc.category_id
    WHERE c.name = 'Comedy'
    ORDER BY f.title, f.film_id

### add SAKILA_SALES_BY_FILM_CATEGORY_A_04
- section: SALES_BY_FILM_CATEGORY   tier: Advanced
- title: each category's sales at each store, with the view's total beside them
- why: The view hides which store made the sales, and no exercise splits it by store or checks the view's totals per category against the base tables. Subtotals with `WITH ROLLUP` and `GROUPING()` are an Advanced MySQL feature this unit lacks.
- request: Sum the payments of each category at each store, through rental, copy and `film_category`, with a subtotal for each category and a grand total. Show the `category`, the `store_id`, the sales and, on each category's subtotal row, the view's `total_sales`, which should be equal. Order by the category, then by the store, with the subtotal after its stores and the grand total last.
- sql:
    SELECT g.category, g.store_id, g.sales, s.total_sales
    FROM (SELECT c.name AS category, i.store_id, SUM(p.amount) AS sales,
                 GROUPING(c.name) AS g_category, GROUPING(i.store_id) AS g_store
          FROM payment p
                   JOIN rental r ON r.rental_id = p.rental_id
                   JOIN inventory i ON i.inventory_id = r.inventory_id
                   JOIN film_category fc ON fc.film_id = i.film_id
                   JOIN category c ON c.category_id = fc.category_id
          GROUP BY c.name, i.store_id WITH ROLLUP) g
             LEFT JOIN sales_by_film_category s ON s.category = g.category AND g.g_store = 1
    ORDER BY g.g_category, g.category, g.g_store, g.store_id
