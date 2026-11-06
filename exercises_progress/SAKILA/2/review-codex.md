### fix SAKILA_SALES_BY_FILM_CATEGORY_B_01

- section: SALES_BY_FILM_CATEGORY   tier: Basic
- title: the three categories which sold the most
- why: The limiting query needs its own explicit ordering, including a tie breaker.
- request: Show the three categories with the highest total sales, highest first; break ties by category name.
- sql:

    ```sql
    SELECT *
    FROM sales_by_film_category
    ORDER BY total_sales DESC, category
    LIMIT 3
    ```

### fix SAKILA_FILM_LIST_I_01

- section: FILM_LIST   tier: Intermediate
- title: whether every categorized film appears in the view
- why: The DDL uses outer joins, so uncategorized films also appear. Compare distinct categorized films rather than all view rows with distinct films.
- request: Check whether every film with a category appears in film_list. Show the number of distinct categorized films in the view and in film_category, in one row.
- sql:

    ```sql
    SELECT (SELECT COUNT(DISTINCT FID)
            FROM film_list
            WHERE category IS NOT NULL) AS categorized_films_in_view,
           (SELECT COUNT(DISTINCT film_id)
            FROM film_category) AS films_with_a_category
    ```

### fix SAKILA_CATEGORY_I_02

- section: CATEGORY   tier: Intermediate
- title: the category with the longest films on average
- why: Ordering by the rounded average can select a category whose actual average is lower. The limited result also needs a tie breaker.
- request: Show the category whose films have the greatest average known length, with that average rounded to two decimal places. Break ties by category name.
- sql:

    ```sql
    SELECT c.name, ROUND(AVG(f.length), 2) AS average_length
    FROM category c
             JOIN film_category fc ON fc.category_id = c.category_id
             JOIN film f ON f.film_id = fc.film_id
    GROUP BY c.category_id
    HAVING COUNT(f.length) > 0
    ORDER BY AVG(f.length) DESC, c.name
    LIMIT 1
    ```

### fix SAKILA_CATEGORY_I_01

- section: CATEGORY   tier: Intermediate
- title: how many films each category has
- why: The inner join omits categories with no films, although the request asks for each category.
- request: Show every category's name and film count, including zero, ordered by count descending and then by name.
- sql:

    ```sql
    SELECT c.name, COUNT(fc.film_id) AS films
    FROM category c
             LEFT JOIN film_category fc ON fc.category_id = c.category_id
    GROUP BY c.category_id
    ORDER BY films DESC, c.name
    ```

### fix SAKILA_FILM_CATEGORY_I_03

- section: FILM_CATEGORY   tier: Intermediate
- title: every category's film and R-rated film counts
- why: The inner joins omit empty categories. Starting from category preserves them and gives both counts as zero.
- request: For every category, show its name, total film count and R-rated film count, ordered by name.
- sql:

    ```sql
    SELECT c.name,
           COUNT(f.film_id) AS films,
           SUM(CASE WHEN f.rating = 'R' THEN 1 ELSE 0 END) AS r_rated
    FROM category c
             LEFT JOIN film_category fc ON fc.category_id = c.category_id
             LEFT JOIN film f ON f.film_id = fc.film_id
    GROUP BY c.category_id
    ORDER BY c.name
    ```

### fix SAKILA_INVENTORY_I_03

- section: INVENTORY   tier: Intermediate
- title: how many copies each store has out
- why: The current query counts open rental rows and omits stores with none. The question asks for copies, for every store.
- request: Show every store's id and the number of its copies with an unreturned rental, including zero, ordered by store id.
- sql:

    ```sql
    SELECT st.store_id,
           (SELECT COUNT(*)
            FROM inventory i
            WHERE i.store_id = st.store_id
              AND EXISTS (SELECT 1
                          FROM rental r
                          WHERE r.inventory_id = i.inventory_id
                            AND r.return_date IS NULL)) AS copies_out
    FROM store st
    ORDER BY st.store_id
    ```

### fix SAKILA_NICER_BUT_SLOWER_FILM_LIST_A_01

- section: NICER_BUT_SLOWER_FILM_LIST   tier: Advanced
- title: differences between the views outside actor formatting
- why: Both views retain uncategorized films, whose category is NULL. Equality on the join key silently excludes those rows.
- request: Match the two views by FID and category, including NULL categories. Count matched rows whose title, description, price, length or rating differs, using null-safe comparisons.
- sql:

    ```sql
    SELECT COUNT(*) AS differing
    FROM nicer_but_slower_film_list n
             JOIN film_list l ON l.FID = n.FID AND l.category <=> n.category
    WHERE NOT (n.title <=> l.title AND n.description <=> l.description
               AND n.price <=> l.price AND n.length <=> l.length
               AND n.rating <=> l.rating)
    ```

### fix SAKILA_NICER_BUT_SLOWER_FILM_LIST_B_01

- section: NICER_BUT_SLOWER_FILM_LIST   tier: Basic
- title: compare the actor formatting for film 1
- why: The request asks to compare both views, but the answer reads only one.
- request: Show FID, title and actors for film 1 from each view, so I can compare how they format the actors' names.
- sql:

    ```sql
    SELECT FID, title, actors
    FROM nicer_but_slower_film_list
    WHERE FID = 1;

    SELECT FID, title, actors
    FROM film_list
    WHERE FID = 1;
    ```

### fix SAKILA_SALES_BY_FILM_CATEGORY_I_01

- section: SALES_BY_FILM_CATEGORY   tier: Intermediate
- title: compare category sales with all payments
- why: Equal totals do not prove that every payment reaches exactly one category: omissions and multiple attribution can cancel. Keep the comparison, but correct its interpretation.
- request: Show total sales across all categories and the total amount of all payments in one row. This compares amounts; equality alone does not establish that every payment was attributed exactly once.
- sql:

    ```sql
    SELECT (SELECT SUM(total_sales)
            FROM sales_by_film_category) AS by_category,
           (SELECT SUM(amount)
            FROM payment) AS all_payments
    ```

### add SAKILA_FILM_LIST_A_02

- section: FILM_LIST   tier: Advanced
- title: the three cheapest films in each category
- why: FILM_LIST has no active Advanced exercise. This adds a useful per-category shortlist with deterministic selection.
- request: Show up to three cheapest films in each category, including the uncategorized group. Show category, FID, title and price; break price ties by title and then FID, and order the results by category and position.
- sql:

    ```sql
    SELECT category, FID, title, price
    FROM (SELECT category, FID, title, price,
                 ROW_NUMBER() OVER (PARTITION BY category
                                    ORDER BY price, title, FID) AS position
          FROM film_list) ranked
    WHERE position <= 3
    ORDER BY category, position
    ```

### add SAKILA_SALES_BY_FILM_CATEGORY_I_04

- section: SALES_BY_FILM_CATEGORY   tier: Intermediate
- title: payments not attributed to exactly one category
- why: Nullable payment.rental_id and the film-category composite key permit missing or multiple attribution. This directly guards the assumption behind the totals comparison.
- request: Find payments that reach either no category or more than one category through their rental and copy. Show payment id, amount and category count, ordered by payment id.
- sql:

    ```sql
    SELECT p.payment_id, p.amount, COUNT(fc.category_id) AS categories
    FROM payment p
             LEFT JOIN rental r ON r.rental_id = p.rental_id
             LEFT JOIN inventory i ON i.inventory_id = r.inventory_id
             LEFT JOIN film_category fc ON fc.film_id = i.film_id
    GROUP BY p.payment_id
    HAVING COUNT(fc.category_id) <> 1
    ORDER BY p.payment_id
    ```

### add SAKILA_CATEGORY_I_06

- section: CATEGORY   tier: Intermediate
- title: category names used by more than one category
- why: The DDL does not make category names unique. This guards the existing name-based joins, ordering and view grouping without complicating every exercise.
- request: Find category names used by more than one category, using the column's collation. Show each name and its count, ordered by name.
- sql:

    ```sql
    SELECT name, COUNT(*) AS categories
    FROM category
    GROUP BY name
    HAVING COUNT(*) > 1
    ORDER BY name
    ```

### add SAKILA_INVENTORY_I_06

- section: INVENTORY   tier: Intermediate
- title: copies with multiple unreturned rentals
- why: The rental unique key does not prevent multiple open rentals for one copy. This guards a fact needed by the published inventory_held_by_customer function.
- request: Find copies with more than one unreturned rental. Show inventory id and the number of open rentals, ordered by inventory id.
- sql:

    ```sql
    SELECT inventory_id, COUNT(*) AS open_rentals
    FROM rental
    WHERE return_date IS NULL
    GROUP BY inventory_id
    HAVING COUNT(*) > 1
    ORDER BY inventory_id
    ```

### add SAKILA_FILM_LIST_B_05

- section: FILM_LIST   tier: Basic
- title: films whose descriptions mention dinosaurs
- why: The view's nullable description is unused. Searching descriptions adds a practical text filter at Basic level.
- request: Find films whose descriptions contain 'Dinosaur', using the column's collation. Show FID, title, category and description, ordered by title, FID and category.
- sql:

    ```sql
    SELECT FID, title, category, description
    FROM film_list
    WHERE description LIKE '%Dinosaur%'
    ORDER BY title, FID, category
    ```