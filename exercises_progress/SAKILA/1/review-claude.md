# SAKILA batch 1 — Claude's review

### fix SAKILA_FILM_I_03
- section: FILM   tier: Intermediate
- title: how many films are short, medium and long
- why: `film.length` is nullable, and a NULL length fails both `WHEN` tests and falls into `ELSE 'long'`, so films of unknown length are counted as long. Count only the films whose length is known.
- request: Put each film whose `length` is known in one of three groups: `short` under 60 minutes, `medium` from 60 to 120 minutes, and `long` over 120 minutes. Show each group with its number of films, from the shortest group to the longest.
- sql:
    SELECT CASE WHEN length < 60 THEN 'short' WHEN length <= 120 THEN 'medium' ELSE 'long' END AS size,
           COUNT(*) AS films
    FROM film
    WHERE length IS NOT NULL
    GROUP BY size
    ORDER BY MIN(length)

### fix SAKILA_ACTOR_INFO_B_01
- section: ACTOR_INFO   tier: Basic
- title: the film_info of the actor 1
- why: `SELECT *, LEFT(film_info, 80) AS film_info` returns the whole long `film_info` and then a second column with the same name, so the result has two `film_info` columns and the truncation the request asks for is lost (a native mapping by column name is ambiguous too). Select the named columns and give the prefix its own alias.
- request: Show the row of the actor `1` in `actor_info`: the `actor_id`, the `first_name`, the `last_name` and the first 80 characters of `film_info`, which is long.
- sql:
    SELECT actor_id, first_name, last_name, LEFT(film_info, 80) AS film_info_head
    FROM actor_info
    WHERE actor_id = 1

### fix SAKILA_FILM_TEXT_B_02
- section: FILM_TEXT   tier: Basic
- title: the five longest descriptions
- why: The request measures the description "by its number of characters", but `LENGTH` counts bytes in `utf8mb4`; `CHAR_LENGTH` counts characters (and is what ACTOR_INFO_B_04 already uses). The result is the same on the ASCII data only by accident.
- request: Find the five films whose `description` is the longest, by its number of characters. Show their `film_id`, `title` and the length, the longest first; ties are ordered by `film_id`.
- sql:
    SELECT *, CHAR_LENGTH(description) AS characters
    FROM film_text
    ORDER BY characters DESC, film_id
    LIMIT 5

### fix SAKILA_FILM_B_06
- section: FILM   tier: Basic
- title: the films cheapest to rent and dearest to replace
- why: The request calls `0.99` "the lowest" and `29.99` "the highest", but the SQL hard-codes both, so it no longer answers the question if the prices change. `title` is not unique in the DDL either, so with `LIMIT 10` the order needs `film_id` as a tie-breaker.
- request: Find the films whose `rental_rate` is the lowest of all films and whose `replacement_cost` is the highest of all films. Show the whole rows, ordered by title, and keep the first ten.
- sql:
    SELECT *
    FROM film
    WHERE rental_rate = (SELECT MIN(rental_rate) FROM film)
      AND replacement_cost = (SELECT MAX(replacement_cost) FROM film)
    ORDER BY title, film_id
    LIMIT 10

### fix SAKILA_FILM_TEXT_I_03
- section: FILM_TEXT   tier: Intermediate
- title: the films whose film_text title differs from their title
- why: Under the default case-insensitive `utf8mb4` collation `<>` treats `Academy Dinosaur` and `ACADEMY DINOSAUR` as equal. The `upd_film` trigger compares with the same collation (`old.title != new.title`), so a case-only change is exactly the drift it fails to copy, and the check cannot see it. Compare with a binary collation.
- request: Join `film_text` to `film` by the film id, and find the films whose two titles are not exactly the same, letter case included.
- sql:
    SELECT f.*, ft.*
    FROM film f
             JOIN film_text ft ON ft.film_id = f.film_id
    WHERE ft.title COLLATE utf8mb4_bin <> f.title
    ORDER BY f.film_id

### fix SAKILA_ACTOR_I_06
- section: ACTOR   tier: Intermediate
- title: the five actors whose films are, on average, the longest
- why: The query sorts by the rounded alias, so two actors whose averages differ only after the second decimal place count as tied and are ordered by `actor_id`. The wrong actor can then rank higher, or get into the five. Sort by the unrounded average and show the rounded one.
- request: For each actor, take the average `length` of the films they appear in, through `film_actor`. Show the five actors with the largest average, with the average rounded to two decimal places, the largest first; break ties by `actor_id`.
- sql:
    SELECT a.*, ROUND(AVG(f.length), 2) AS average_length
    FROM actor a
             JOIN film_actor fa ON fa.actor_id = a.actor_id
             JOIN film f ON f.film_id = fa.film_id
    GROUP BY a.actor_id
    ORDER BY AVG(f.length) DESC, a.actor_id
    LIMIT 5

### add SAKILA_LANGUAGE_A_01
- section: LANGUAGE   tier: Advanced
- title: how many films use each language, as language and as original language
- why: LANGUAGE has no Advanced exercise, and `film` refers to `language` through two foreign keys. Counting both roles in one row means turning the two references into rows (`UNION ALL`) and then aggregating with conditions.
- request: For every language, even one no film uses, count the films that use it as their `language_id` and the films that use it as their `original_language_id`, and show both counts in one row per language, ordered by `language_id`.
- sql:
    SELECT l.*,
           COUNT(CASE WHEN u.role = 'language' THEN 1 END) AS as_language,
           COUNT(CASE WHEN u.role = 'original' THEN 1 END) AS as_original_language
    FROM language l
             LEFT JOIN (SELECT language_id, 'language' AS role
                        FROM film
                        UNION ALL
                        SELECT original_language_id, 'original'
                        FROM film
                        WHERE original_language_id IS NOT NULL) u ON u.language_id = l.language_id
    GROUP BY l.language_id
    ORDER BY l.language_id

### add SAKILA_LANGUAGE_I_03
- section: LANGUAGE   tier: Intermediate
- title: the first five films with the names of their language and original language
- why: No exercise joins the same table twice under two aliases, which the two foreign keys from `film` to `language` call for. The nullable `original_language_id` also needs an outer join, or every film would drop out.
- request: Show the first five films by `film_id`, each with the name of its language and the name of its original language, which is empty when the film has none.
- sql:
    SELECT f.film_id, f.title, l.name AS language, ol.name AS original_language
    FROM film f
             JOIN language l ON l.language_id = f.language_id
             LEFT JOIN language ol ON ol.language_id = f.original_language_id
    ORDER BY f.film_id
    LIMIT 5

### add SAKILA_FILM_TEXT_I_06
- section: FILM_TEXT   tier: Intermediate
- title: the films whose film_text description differs from their description
- why: `description` is nullable in both tables, and the `upd_film` trigger compares it with `!=`, which is never true when one side is NULL. So setting a NULL description, or clearing one, never reaches `film_text`. A NULL-safe comparison (`<=>`) is the SQL feature this needs, and no exercise uses it yet.
- request: Join `film_text` to `film` by the film id, and find the films whose two descriptions are not the same, counting a NULL on one side and a value on the other as different.
- sql:
    SELECT f.*, ft.*
    FROM film f
             JOIN film_text ft ON ft.film_id = f.film_id
    WHERE NOT (ft.description COLLATE utf8mb4_bin <=> f.description)
    ORDER BY f.film_id

### add SAKILA_FILM_TEXT_I_07
- section: FILM_TEXT   tier: Intermediate
- title: the first words that start more than one title
- why: SAKILA_FILM_TEXT_A_02 relies on "no two titles share a first word", which the DDL does not enforce. Without that fact the recursive chain branches. A check that returns no rows guards the fact.
- request: Group the titles of `film_text` by their first word, and show each first word that starts more than one title, with its number of titles, ordered by the word.
- sql:
    SELECT SUBSTRING_INDEX(title, ' ', 1) AS first_word, COUNT(*) AS titles
    FROM film_text
    GROUP BY first_word
    HAVING COUNT(*) > 1
    ORDER BY first_word

### add SAKILA_FILM_B_07
- section: FILM   tier: Basic
- title: how many films lack each optional value
- why: `film` has five nullable columns (`description`, `release_year`, `length`, `rating`, `special_features`), and no Basic exercise shows that `COUNT(column)` skips NULLs. FILM_I_03 shows why it matters.
- request: Count, in one row, all the films and, for each of `description`, `release_year`, `length`, `rating` and `special_features`, the films where it is `NULL`.
- sql:
    SELECT COUNT(*)                            AS films,
           COUNT(*) - COUNT(description)       AS no_description,
           COUNT(*) - COUNT(release_year)      AS no_release_year,
           COUNT(*) - COUNT(length)            AS no_length,
           COUNT(*) - COUNT(rating)            AS no_rating,
           COUNT(*) - COUNT(special_features)  AS no_special_features
    FROM film

### add SAKILA_FILM_A_02
- section: FILM   tier: Advanced
- title: how many films have each special feature
- why: FILM_B_04 tests one member of the `SET` column. Counting every member at once means turning the set into rows: join a derived table of the members on `FIND_IN_SET`. FILM has only one Advanced exercise.
- request: For each of the four special features (`Trailers`, `Commentaries`, `Deleted Scenes`, `Behind the Scenes`), count the films whose `special_features` hold it. Show each feature with its count, the most first; ties are ordered by the feature.
- sql:
    SELECT sf.feature, COUNT(f.film_id) AS films
    FROM (SELECT 'Trailers' AS feature
          UNION ALL SELECT 'Commentaries'
          UNION ALL SELECT 'Deleted Scenes'
          UNION ALL SELECT 'Behind the Scenes') sf
             LEFT JOIN film f ON FIND_IN_SET(sf.feature, f.special_features) > 0
    GROUP BY sf.feature
    ORDER BY films DESC, sf.feature

### add SAKILA_ACTOR_INFO_I_04
- section: ACTOR_INFO   tier: Intermediate
- title: the actors whose film_info may be cut by GROUP_CONCAT
- why: `film_info` is built by `GROUP_CONCAT`, which cuts its result at `group_concat_max_len` (1024 bytes by default). The actors with the most films come close to that limit. ACTOR_INFO_B_04 (longest film_info), I_02, I_03 and A_01 (colons counted in the string) quietly assume nothing was cut, and this check guards that.
- request: Find the actors whose `film_info` is as long as `GROUP_CONCAT` allows, so it may have been cut. Show the `actor_id`, the `first_name`, the `last_name` and the length in bytes, ordered by `actor_id`.
- sql:
    SELECT actor_id, first_name, last_name, LENGTH(film_info) AS film_info_bytes
    FROM actor_info
    WHERE LENGTH(film_info) >= @@group_concat_max_len
    ORDER BY actor_id
