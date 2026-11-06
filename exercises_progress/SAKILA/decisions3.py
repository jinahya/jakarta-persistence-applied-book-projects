import json
C = []
def fix(i, src, why, **kw): C.append(dict(op='fix', id=i, _src=src, _why=why, rerun=kw.pop('rerun', 'sql' in kw), **kw))
def add(i, src, why, **kw): C.append(dict(op='add', id=i, after=kw.pop('after', 'last'), _src=src, _why=why, rerun=True, **kw))
def rm(i, src, why): C.append(dict(op='remove', id=i, _src=src, _why=why))
STAFF_COLS = "s.staff_id, s.first_name, s.last_name, s.address_id, s.email, s.store_id, s.active, s.username, s.password, s.last_update"

fix('SAKILA_STAFF_I_01', 'both', 'the inner join dropped a staff member who handled no rental, though the request counts each',
    request=["Count the rentals each staff member handled, by `rental.staff_id`.",
             "Show each staff member's `staff_id` and `first_name` with the count, `0` for one who handled none, ordered by `staff_id`."],
    sql=f"SELECT {STAFF_COLS}, COUNT(r.rental_id) AS rentals -- every column but picture, a BLOB which does not print\nFROM staff s\n         LEFT JOIN rental r ON r.staff_id = s.staff_id\nGROUP BY s.staff_id\nORDER BY s.staff_id")
fix('SAKILA_STAFF_I_03', 'both', 'the inner joins dropped a staff member with no rental',
    request=["A staff member works at one store, but may rent out a copy of another store.",
             "For each staff member, count the rentals they handled whose copy is at their own store, and those whose copy is elsewhere, with `CASE` inside `SUM`; a staff member with no rental shows two zeros.",
             "Show the `staff_id`, `first_name`, `store_id` and the two counts, ordered by `staff_id`."],
    sql=f"SELECT {STAFF_COLS}, -- every column but picture, a BLOB which does not print\n       SUM(CASE WHEN i.store_id = s.store_id THEN 1 ELSE 0 END) AS own_store,\n       SUM(CASE WHEN i.store_id <> s.store_id THEN 1 ELSE 0 END) AS other_store\nFROM staff s\n         LEFT JOIN rental r ON r.staff_id = s.staff_id\n         LEFT JOIN inventory i ON i.inventory_id = r.inventory_id\nGROUP BY s.staff_id\nORDER BY s.staff_id")
fix('SAKILA_STAFF_LIST_I_02', 'Claude', "the title asks whether, but the SQL never compared the two cities, and city names repeat across countries",
    request=["The view's `city` and `country` are where the staff member lives, and `SID` is the store they work at.",
             "Join each row to its store, the store's address, city and country, and show the `ID`, `name`, where they live, where they work, and whether the two are the same city of the same country, ordered by `ID`.",
             "City names repeat across countries, so the comparison takes the country too."],
    sql="SELECT l.*,\n       ci.city                                        AS store_city,\n       co.country                                     AS store_country,\n       (l.city = ci.city AND l.country = co.country) AS lives_in_store_city\nFROM staff_list l\n         JOIN store st ON st.store_id = l.SID\n         JOIN address a ON a.address_id = st.address_id\n         JOIN city ci ON ci.city_id = a.city_id\n         JOIN country co ON co.country_id = ci.country_id\nORDER BY l.ID")
fix('SAKILA_CUSTOMER_B_03', 'Claude', 'no ORDER BY, so the order of the groups was unspecified',
    request=["Every customer has an `email`; SAKILA_CUSTOMER_B_06 checks it.",
             "Take the part after the `@` as the domain, group the customers by it, and show each domain with the number of its customers, the most first; domains with the same number are ordered by name.",
             "The group is by an expression, not by a column."],
    sql="SELECT SUBSTRING_INDEX(email, '@', -1) AS domain, COUNT(*) AS customers\nFROM customer\nGROUP BY domain\nORDER BY customers DESC, domain")
fix('SAKILA_STORE_A_01', 'Codex', 'the inner join dropped a store with no copy, though the request counts each store',
    request=["For each store, a store without a copy included, count the distinct films it has at least one copy of, and, of those, the films no other store has a copy of.",
             "Show the `store_id` and both counts, ordered by `store_id`.",
             "The second count needs a correlated condition on the inventory of the other stores."],
    sql="SELECT st.*,\n       COUNT(DISTINCT i.film_id)                  AS films,\n       COUNT(DISTINCT CASE\n                          WHEN NOT EXISTS (SELECT 1\n                                           FROM inventory o\n                                           WHERE o.film_id = i.film_id\n                                             AND o.store_id <> st.store_id)\n                              THEN i.film_id END) AS films_only_here\nFROM store st\n         LEFT JOIN inventory i ON i.store_id = st.store_id\nGROUP BY st.store_id\nORDER BY st.store_id")
fix('SAKILA_CITY_B_01', 'Codex', 'city names repeat (across countries), so ordering by the name alone does not fix the order of the rows',
    request=["Find the cities whose name starts with the letter `Q`.",
             "Show the whole rows, ordered by the name, then by `city_id`; names repeat across countries.",
             "A `LIKE` with a trailing wildcard."],
    sql="SELECT *\nFROM city\nWHERE city LIKE 'Q%'\nORDER BY city, city_id")
fix('SAKILA_CITY_I_04', 'Codex', 'two cities may share the name and the count; city_id breaks the tie',
    request=["Count the addresses of each city, and keep the cities with more than one.",
             "Show the `city_id`, the `city` and the count, the most first; cities with the same count are ordered by the name, then by `city_id`."],
    sql="SELECT ci.*, COUNT(*) AS addresses\nFROM city ci\n         JOIN address a ON a.city_id = ci.city_id\nGROUP BY ci.city_id\nHAVING COUNT(*) > 1\nORDER BY addresses DESC, ci.city, ci.city_id")

add('SAKILA_STAFF_LIST_A_01', 'Codex', 'STAFF_LIST has no Advanced exercise; the view\'s home country against the rental-to-customer path',
    title='the staff members who served a customer living outside their own country',
    file_header="Exercises at the advanced level on staff_list: a correlated EXISTS across the rentals, customers and their addresses. Each poses a question, answers it, and shows what the installed data gives back.",
    request=["Find the staff members who handled at least one rental for a customer who lives in another country than the staff member does, as the view says.",
             "Show their `ID`, `name` and `country`, ordered by `ID`.",
             "A correlated `EXISTS` walks from the staff member's rentals to the customers' countries."],
    sql="SELECT l.ID, l.name, l.country\nFROM staff_list l\nWHERE EXISTS (SELECT 1\n              FROM rental r\n                       JOIN customer cu ON cu.customer_id = r.customer_id\n                       JOIN address a ON a.address_id = cu.address_id\n                       JOIN city ci ON ci.city_id = a.city_id\n                       JOIN country co ON co.country_id = ci.country_id\n              WHERE r.staff_id = l.ID\n                AND co.country <> l.country)\nORDER BY l.ID")
add('SAKILA_CUSTOMER_B_06', 'Codex', 'email is nullable, and SAKILA_CUSTOMER_B_03 takes the domain after the @ of every one',
    title='the customers whose email is missing or not one address',
    request=["SAKILA_CUSTOMER_B_03 takes the part of each `email` after the `@`, which `email`, nullable, does not promise.",
             "Find the customers whose `email` is `NULL`, holds a space, or does not have exactly one `@` with something on both sides; show their `customer_id`, names and `email`, ordered by `customer_id`; the check passes when nothing comes back."],
    sql="SELECT customer_id, first_name, last_name, email\nFROM customer\nWHERE email IS NULL\n   OR email NOT LIKE '_%@_%'\n   OR CHAR_LENGTH(email) - CHAR_LENGTH(REPLACE(email, '@', '')) <> 1\n   OR email REGEXP '[[:space:]]'\nORDER BY customer_id")
add('SAKILA_CUSTOMER_I_06', 'Codex', 'the spending exercises join payment with inner joins, assuming every customer has paid',
    title='the customers with no payment',
    request=["The exercises on what customers spent join `payment` with inner joins, which drops a customer who never paid.",
             "Find the customers with no payment: their `customer_id` and names, ordered by `customer_id`; the check passes when nothing comes back."],
    sql="SELECT c.customer_id, c.first_name, c.last_name\nFROM customer c\nWHERE NOT EXISTS (SELECT 1 FROM payment p WHERE p.customer_id = c.customer_id)\nORDER BY c.customer_id")
add('SAKILA_CUSTOMER_I_07', 'Claude', "film.rental_duration against the rental dates is the schema's own notion of lateness (get_customer_balance), and no exercise uses it per customer",
    title='the five customers who returned late most often',
    request=["A rental is late when it was returned more days after it was rented than its film's `rental_duration`, as `get_customer_balance` counts it.",
             "Show the five customers with the most late returns, with their counts, the most first; ties are ordered by `customer_id`.",
             "A rental not yet returned has no `return_date`, so it drops out of the comparison."],
    sql="SELECT c.*, COUNT(*) AS late_returns\nFROM customer c\n         JOIN rental r ON r.customer_id = c.customer_id\n         JOIN inventory i ON i.inventory_id = r.inventory_id\n         JOIN film f ON f.film_id = i.film_id\nWHERE DATEDIFF(r.return_date, r.rental_date) > f.rental_duration\nGROUP BY c.customer_id\nORDER BY late_returns DESC, c.customer_id\nLIMIT 5")
add('SAKILA_CUSTOMER_A_04', 'Claude', 'no exercise uses LAG over dates, which rental_date makes natural',
    title='the five customers with the longest gap between two rentals',
    request=["For each customer, take the days between each rental and the customer's previous one, and keep the longest.",
             "Show the five customers with the longest gap, with the gap in days, the longest first; ties are ordered by `customer_id`.",
             "`LAG` gives each rental the one before it; `rental_id` breaks a tie of `rental_date`, which is not unique per customer."],
    sql="WITH gaps AS (SELECT r.customer_id,\n                     DATEDIFF(r.rental_date,\n                              LAG(r.rental_date) OVER (PARTITION BY r.customer_id ORDER BY r.rental_date, r.rental_id)) AS gap_days\n              FROM rental r)\nSELECT c.*, MAX(g.gap_days) AS longest_gap\nFROM customer c\n         JOIN gaps g ON g.customer_id = c.customer_id\nGROUP BY c.customer_id\nORDER BY longest_gap DESC, c.customer_id\nLIMIT 5")
add('SAKILA_COUNTRY_I_05', 'both', 'SAKILA_COUNTRY_B_02 says the names are unique and the A tier orders by them, but country.country has no unique key',
    title='the country names found more than once',
    request=["SAKILA_COUNTRY_B_02 relies on the country names being unique, and the Advanced exercises order by them; the schema does not make them unique.",
             "Find the names that more than one row of `country` has, with how many, ordered by the name; the check passes when nothing comes back."],
    sql="SELECT country, COUNT(*) AS countries\nFROM country\nGROUP BY country\nHAVING COUNT(*) > 1\nORDER BY country")
add('SAKILA_CITY_I_06', 'Codex', 'city names identify a city within its country in several exercises, which no key enforces',
    title='the city names found more than once in a country',
    request=["Some exercises name a city by its country and its name, which no key of `city` makes unique.",
             "Find each `country_id` and city name that more than one city has, with how many, ordered by `country_id` and the name; the check passes when nothing comes back."],
    sql="SELECT country_id, city, COUNT(*) AS cities\nFROM city\nGROUP BY country_id, city\nHAVING COUNT(*) > 1\nORDER BY country_id, city")
add('SAKILA_ADDRESS_B_05', 'Claude', 'postal_code is nullable, and no exercise shows that a missing one takes two forms, nor that = \'\' is not true for NULL',
    title='how many addresses have no postal code, as NULL and as an empty string',
    request=["A missing `postal_code` may be `NULL` or the empty string.",
             "Count the addresses whose `postal_code` is `NULL`, and, apart, those whose `postal_code` is the empty string, in one row.",
             "`postal_code = ''` is not true for a `NULL`; in MySQL a condition sums as `1` or `0`."],
    sql="SELECT SUM(postal_code IS NULL) AS null_postal_codes,\n       SUM(postal_code = '')    AS empty_postal_codes\nFROM address")
add('SAKILA_CUSTOMER_LIST_B_05', 'Claude', "the view's `zip code` column has a space in its name, which only backticks quote, and no exercise reads it",
    title='the first ten customers in the United States by zip code',
    request=["The view's `zip code` column has a space in its name, so a query quotes it with backticks; it may be `NULL`, which MySQL sorts first.",
             "Show the first ten customers in the United States, the whole rows of the view, ordered by their zip code and then by `ID`."],
    sql="SELECT *\nFROM customer_list\nWHERE country = 'United States'\nORDER BY `zip code`, ID\nLIMIT 10")

rm('SAKILA_CUSTOMER_LIST_I_03', 'both', "the view defines name as exactly that CONCAT, so the query can never return a row")
rm('SAKILA_ADDRESS_A_01', 'Claude', "SAKILA_ADDRESS_I_03's 'none' class counts exactly these addresses; three NOT EXISTS is not Advanced either")
json.dump({'module': 'mysql-sakila-persistence', 'changes': C}, open('decisions3.json', 'w'), indent=1, ensure_ascii=False)
print(len(C), 'changes')
