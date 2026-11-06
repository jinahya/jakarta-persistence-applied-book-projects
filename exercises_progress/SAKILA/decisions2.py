import json
C = []
def fix(i, src, why, **kw): C.append(dict(op='fix', id=i, _src=src, _why=why, rerun=kw.pop('rerun', 'sql' in kw), **kw))
def add(i, src, why, **kw): C.append(dict(op='add', id=i, after=kw.pop('after', 'last'), _src=src, _why=why, rerun=True, **kw))

fix('SAKILA_SALES_BY_FILM_CATEGORY_B_01', 'both', "the top three came only from the view's own ORDER BY, which a query of the view need not keep, with no tie-break",
    request=["The `sales_by_film_category` view sums the payments of each category.",
             "Show the three categories which sold the most, with their `total_sales`, the most first; on a tie, by `category`.",
             "The view's own `ORDER BY` does not carry over to a query of it, so the query orders the rows itself."],
    sql="SELECT *\nFROM sales_by_film_category\nORDER BY total_sales DESC, category\nLIMIT 3")
fix('SAKILA_SALES_BY_FILM_CATEGORY_I_01', 'Codex', 'equal totals do not show that each payment reaches one category; SAKILA_SALES_BY_FILM_CATEGORY_I_04 checks that',
    request=["Check the view: sum its `total_sales` over all categories, sum the `amount` of all payments, and show both in one row.",
             "They are equal if every payment reaches exactly one category, through its rental, copy and film; equal totals alone do not prove it, and SAKILA_SALES_BY_FILM_CATEGORY_I_04 checks it payment by payment."])
fix('SAKILA_FILM_LIST_I_01', 'both', "the request said inner joins, but the view joins film_category and category by outer joins, so a film without a category has a row too",
    request=["The view joins `film` with `film_category` and `category` by outer joins, so a film without a category still has a row, whose `category` is `NULL`.",
             "Count the distinct films of the view which have a category, and the distinct films of `film_category`, and show both in one row, with the view's rows without a category in a third column."],
    sql="SELECT (SELECT COUNT(DISTINCT FID) FROM film_list WHERE category IS NOT NULL) AS film_list,\n       (SELECT COUNT(DISTINCT film_id) FROM film_category)                    AS films_with_a_category,\n       (SELECT COUNT(*) FROM film_list WHERE category IS NULL)                AS film_list_without_a_category")
fix('SAKILA_NICER_BUT_SLOWER_FILM_LIST_A_01', 'both', "the join compared category with =, so the rows of the films without a category, NULL there, never joined",
    request=["The two views should differ only in how the actors are written.",
             "Join them row by row, by `FID` and `category`, and count the rows where any other column (`title`, `description`, `price`, `length`, `rating`) differs.",
             "`category` is `NULL` for a film without one, and the other columns may be `NULL` too, so compare all of them, the join included, with the null-safe `<=>`, not with `=`.",
             "The answer is `0`."],
    sql="SELECT COUNT(*) AS differing\nFROM nicer_but_slower_film_list n\n         JOIN film_list l ON l.FID = n.FID AND l.category <=> n.category\nWHERE NOT (n.title <=> l.title AND n.description <=> l.description AND n.price <=> l.price\n           AND n.length <=> l.length AND n.rating <=> l.rating)")
fix('SAKILA_NICER_BUT_SLOWER_FILM_LIST_A_02', 'Claude', "m.category = n.category never matched the NULL category, which dropped out of the answer",
    request=["For each category, the films without one included, find the longest `length` of its films, and count the films which are exactly that long.",
             "Show the `category`, the longest length and the count, ordered by `category`.",
             "A row is kept when its length equals the maximum of its own category, which is a correlated subquery; it compares the categories with `<=>`, so the films without a category form a group too."],
    sql="SELECT n.category, n.length AS longest, COUNT(*) AS films\nFROM nicer_but_slower_film_list n\nWHERE n.length = (SELECT MAX(m.length) FROM nicer_but_slower_film_list m WHERE m.category <=> n.category)\nGROUP BY n.category, n.length\nORDER BY n.category")
fix('SAKILA_NICER_BUT_SLOWER_FILM_LIST_B_01', 'Codex', "the request compares the two views' rows, but the SQL read one",
    request=["`nicer_but_slower_film_list` is `film_list` with the actors' names written with only the first letter of each name in upper case.",
             "Show the film `1`'s `FID`, `title` and `actors` from both views, one row each, with a column naming the view, to compare how they write the actors."],
    sql="SELECT 'nicer_but_slower_film_list' AS view, FID, title, actors\nFROM nicer_but_slower_film_list\nWHERE FID = 1\nUNION ALL\nSELECT 'film_list', FID, title, actors\nFROM film_list\nWHERE FID = 1")
fix('SAKILA_CATEGORY_I_02', 'both', 'ordered by the rounded average with no tie-break, so LIMIT 1 could keep the wrong category',
    request=["For each category, take the average `length` of its films, and find the category whose average is the largest.",
             "Show its name and the average, rounded to two decimal places.",
             "Order the groups by the average itself, not the rounded one, then by name, and keep only the first."],
    sql="SELECT c.*, ROUND(AVG(f.length), 2) AS average_length\nFROM category c\n         JOIN film_category fc ON fc.category_id = c.category_id\n         JOIN film f ON f.film_id = fc.film_id\nGROUP BY c.category_id\nORDER BY AVG(f.length) DESC, c.name\nLIMIT 1")
fix('SAKILA_CATEGORY_I_01', 'Codex', 'the inner join left out a category with no film, though the request counts each category',
    request=["Count the films of each category through the `film_category` link table, a category without a film included, with `0`.",
             "Show each category's name and its number of films, the most first; categories with the same count are ordered by name."],
    sql="SELECT c.*, COUNT(fc.film_id) AS films\nFROM category c\n         LEFT JOIN film_category fc ON fc.category_id = c.category_id\nGROUP BY c.category_id\nORDER BY films DESC, c.name")
fix('SAKILA_FILM_CATEGORY_I_03', 'Codex', 'the query started from film_category, so a category with no film was left out',
    request=["For each category, a category without a film included, count its films, and, in the same row, those of them whose `rating` is `R`.",
             "Show the category's name with both counts, ordered by the name.",
             "Count the R-rated films with a `CASE` inside a `SUM`, so that one pass over the rows gives both counts; the query starts from `category`, with outer joins."],
    sql="SELECT c.*,\n       COUNT(f.film_id) AS films,\n       SUM(CASE WHEN f.rating = 'R' THEN 1 ELSE 0 END) AS r_rated\nFROM category c\n         LEFT JOIN film_category fc ON fc.category_id = c.category_id\n         LEFT JOIN film f ON f.film_id = fc.film_id\nGROUP BY c.category_id\nORDER BY c.name")

add('SAKILA_FILM_LIST_A_02', 'both', "FILM_LIST has no live Advanced exercise; Claude's, which reads the view's own actors string, over Codex's three cheapest per category",
    title='the films with the most actors in each category',
    file_header="Exercises at the advanced level on film_list: a window function over the view's rows. Each poses a question, answers it, and shows what the installed data gives back.",
    request=["Count each film's actors from the view's `actors` string, one more than its commas, or `0` when it is `NULL`.",
             "In each category, find the films with the most actors, all of them when several tie.",
             "Show the `category`, `FID`, `title` and the number of actors, ordered by `category` and then by `FID`.",
             "`RANK()` over each category keeps the ties."],
    sql="WITH counted AS (SELECT category,\n                        FID,\n                        title,\n                        CASE WHEN actors IS NULL THEN 0\n                             ELSE LENGTH(actors) - LENGTH(REPLACE(actors, ',', '')) + 1 END AS actor_count\n                 FROM film_list)\nSELECT category, FID, title, actor_count\nFROM (SELECT counted.*, RANK() OVER (PARTITION BY category ORDER BY actor_count DESC) AS actor_rank\n      FROM counted) ranked\nWHERE actor_rank = 1\nORDER BY category, FID")
add('SAKILA_INVENTORY_I_06', 'both', 'SAKILA_INVENTORY_I_03, I_05 and A_01 assume a copy is out on one rental at most, which the DDL does not enforce',
    title='the copies which are out on more than one rental at once',
    request=["A copy can be out on only one rental at a time; SAKILA_INVENTORY_I_03 counts open rentals as copies out on that ground, and nothing in the schema enforces it.",
             "Find the copies which have more than one rental with no `return_date`, with their number of open rentals, ordered by `inventory_id`; the check passes when nothing comes back."],
    sql="SELECT i.*, COUNT(*) AS open_rentals\nFROM inventory i\n         JOIN rental r ON r.inventory_id = i.inventory_id\nWHERE r.return_date IS NULL\nGROUP BY i.inventory_id\nHAVING COUNT(*) > 1\nORDER BY i.inventory_id")
add('SAKILA_INVENTORY_A_03', 'Claude', "film.rental_duration is never used, and overdue copies are the first thing a store asks about; a fixed 'now' keeps the answer stable",
    title='the ten copies most overdue, as of the last rental',
    request=["Take the date of the last rental in the data as now.",
             "A copy is overdue when its open rental, with no `return_date`, is older than its film's `rental_duration` in days.",
             "Show the ten most overdue: the `rental_id`, the `inventory_id`, the film's `title`, the `rental_date` and the days overdue, the most first; ties are ordered by `rental_id`."],
    sql="SELECT r.rental_id,\n       i.inventory_id,\n       f.title,\n       r.rental_date,\n       DATEDIFF(m.last_rental, r.rental_date) - f.rental_duration AS days_overdue\nFROM rental r\n         JOIN inventory i ON i.inventory_id = r.inventory_id\n         JOIN film f ON f.film_id = i.film_id\n         CROSS JOIN (SELECT MAX(rental_date) AS last_rental FROM rental) m\nWHERE r.return_date IS NULL\n  AND r.rental_date + INTERVAL f.rental_duration DAY < m.last_rental\nORDER BY days_overdue DESC, r.rental_id\nLIMIT 10")
add('SAKILA_FILM_CATEGORY_B_03', 'Claude', "listing a category's films by its name, across both foreign keys of the link table, has no Basic exercise",
    title='the films of the Comedy category',
    request=["Find the films whose category is `Comedy`, through `film_category`.",
             "Show the films' whole rows, ordered by `title`; ties are ordered by `film_id`."],
    sql="SELECT f.*\nFROM film f\n         JOIN film_category fc ON fc.film_id = f.film_id\n         JOIN category c ON c.category_id = fc.category_id\nWHERE c.name = 'Comedy'\nORDER BY f.title, f.film_id")
add('SAKILA_SALES_BY_FILM_CATEGORY_I_04', 'Codex', 'payment.rental_id is nullable and a film may have several categories; this checks what SAKILA_SALES_BY_FILM_CATEGORY_I_01 assumes',
    title='the payments which reach no category, or more than one',
    request=["A payment reaches its category through its rental, the rental's copy and the copy's film; `rental_id` may be `NULL`, and a film may have more than one category.",
             "Find the payments which reach no category or more than one: the `payment_id`, the `amount` and the number of categories, ordered by `payment_id`; the check passes when nothing comes back."],
    sql="SELECT p.payment_id, p.amount, COUNT(fc.category_id) AS categories\nFROM payment p\n         LEFT JOIN rental r ON r.rental_id = p.rental_id\n         LEFT JOIN inventory i ON i.inventory_id = r.inventory_id\n         LEFT JOIN film_category fc ON fc.film_id = i.film_id\nGROUP BY p.payment_id\nHAVING COUNT(fc.category_id) <> 1\nORDER BY p.payment_id")
add('SAKILA_SALES_BY_FILM_CATEGORY_A_04', 'Claude', 'the view hides the store; subtotals with WITH ROLLUP and GROUPING() check its totals against the tables',
    title="each category's sales at each store, with the view's total beside them",
    request=["Sum the payments of each category at each store, through rental, copy and `film_category`, with a subtotal for each category and a grand total.",
             "Show the `category`, the `store_id`, the sales and, on each category's subtotal row, the view's `total_sales`, which should be equal.",
             "Order by the category, then by the store, with the subtotal after its stores and the grand total last.",
             "`WITH ROLLUP` adds the subtotal rows, and `GROUPING()` tells them from the others."],
    sql="SELECT g.category, g.store_id, g.sales, s.total_sales\nFROM (SELECT c.name                AS category,\n             i.store_id,\n             SUM(p.amount)         AS sales,\n             GROUPING(c.name)      AS g_category,\n             GROUPING(i.store_id)  AS g_store\n      FROM payment p\n               JOIN rental r ON r.rental_id = p.rental_id\n               JOIN inventory i ON i.inventory_id = r.inventory_id\n               JOIN film_category fc ON fc.film_id = i.film_id\n               JOIN category c ON c.category_id = fc.category_id\n      GROUP BY c.name, i.store_id\n      WITH ROLLUP) g\n         LEFT JOIN sales_by_film_category s ON s.category = g.category AND g.g_store = 1\nORDER BY g.g_category, g.category, g.g_store, g.store_id")
add('SAKILA_CATEGORY_I_06', 'Codex', 'the DDL does not make a category name unique, while the views group and join by it',
    title='the category names which more than one category has',
    request=["`sales_by_film_category` and `film_list` work with the category's name, which the schema does not make unique.",
             "Find the names which more than one category has, with how many, ordered by the name; the check passes when nothing comes back."],
    sql="SELECT name, COUNT(*) AS categories\nFROM category\nGROUP BY name\nHAVING COUNT(*) > 1\nORDER BY name")
json.dump({'module': 'mysql-sakila-persistence', 'changes': C}, open('decisions2.json', 'w'), indent=1, ensure_ascii=False)
print(len(C), 'changes')
