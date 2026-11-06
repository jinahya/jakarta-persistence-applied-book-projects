### fix SAKILA_FILM_TEXT_B_02
- section: FILM_TEXT   tier: Basic
- title: The five longest descriptions
- why: `LENGTH` counts bytes; the request asks for characters, and the DDL uses `utf8mb4`.
- request: Show the five films with the longest descriptions in characters, including their ids, titles and character counts. Break ties by film id.
- sql:

    ```sql
    SELECT film_id, title, CHAR_LENGTH(description) AS characters
    FROM film_text
    ORDER BY characters DESC, film_id
    LIMIT 5
    ```

### fix SAKILA_ACTOR_I_06
- section: ACTOR   tier: Intermediate
- title: Actors with the longest films on average
- why: Ordering by the rounded average can rank a smaller average ahead of a larger one. Round only for display.
- request: Show the five actors whose films have the greatest average known length, with the average rounded to two decimal places. Order by the unrounded average descending, then actor id.
- sql:

    ```sql
    SELECT a.actor_id, a.first_name, a.last_name,
           ROUND(AVG(f.length), 2) AS average_length
    FROM actor a
             JOIN film_actor fa ON fa.actor_id = a.actor_id
             JOIN film f ON f.film_id = fa.film_id
    GROUP BY a.actor_id
    HAVING COUNT(f.length) > 0
    ORDER BY AVG(f.length) DESC, a.actor_id
    LIMIT 5
    ```

### fix SAKILA_FILM_I_03
- section: FILM   tier: Intermediate
- title: Films grouped by running time
- why: A NULL length currently falls into `long`. Give unknown lengths their own group and make the group order explicit.
- request: Count films as short below 60 minutes, medium from 60 through 120, long above 120, or unknown when no length is recorded. Show those groups in that order.
- sql:

    ```sql
    SELECT CASE
               WHEN length IS NULL THEN 'unknown'
               WHEN length < 60 THEN 'short'
               WHEN length <= 120 THEN 'medium'
               ELSE 'long'
           END AS size,
           COUNT(*) AS films
    FROM film
    GROUP BY size
    ORDER BY CASE size
                 WHEN 'short' THEN 1
                 WHEN 'medium' THEN 2
                 WHEN 'long' THEN 3
                 ELSE 4
             END
    ```

### fix SAKILA_FILM_A_01
- section: FILM   tier: Advanced
- title: Films above their rating’s average length
- why: Filtering before grouping omits ratings with zero qualifying films. Ordinary equality also fails to match the nullable rating group.
- request: For every rating represented in the catalog, including an unknown rating, count films longer than that rating’s average known length. Show zero where none qualifies, ordered by rating.
- sql:

    ```sql
    SELECT f1.rating,
           COUNT(CASE
                     WHEN f1.length > (
                         SELECT AVG(f2.length)
                         FROM film f2
                         WHERE f2.rating <=> f1.rating
                     ) THEN 1
                 END) AS films
    FROM film f1
    GROUP BY f1.rating
    ORDER BY f1.rating
    ```

### fix SAKILA_FILM_TEXT_I_01
- section: FILM_TEXT   tier: Intermediate
- title: Check film-text coverage
- why: Equal row counts do not prove that the same film ids occur in both tables; `film_text` has no foreign key to `film`.
- request: Show the row counts of film and film_text, plus the numbers of films missing their text row and text rows without a film.
- sql:

    ```sql
    SELECT (SELECT COUNT(*) FROM film) AS films,
           (SELECT COUNT(*) FROM film_text) AS film_text_rows,
           (SELECT COUNT(*)
            FROM film f
            WHERE NOT EXISTS (
                SELECT 1 FROM film_text ft WHERE ft.film_id = f.film_id
            )) AS missing_text,
           (SELECT COUNT(*)
            FROM film_text ft
            WHERE NOT EXISTS (
                SELECT 1 FROM film f WHERE f.film_id = ft.film_id
            )) AS orphan_text
    ```

### fix SAKILA_ACTOR_INFO_I_03
- section: ACTOR_INFO   tier: Intermediate
- title: Actors grouped by category coverage
- why: The view returns NULL `film_info` for an actor without categorized films. Such actors cover zero categories, rather than an unknown number.
- request: Count how many actors cover each number of categories, treating NULL film_info as zero categories. Order by category count descending.
- sql:

    ```sql
    SELECT COALESCE(CHAR_LENGTH(film_info)
                        - CHAR_LENGTH(REPLACE(film_info, ':', '')), 0) AS categories,
           COUNT(*) AS actors
    FROM actor_info
    GROUP BY categories
    ORDER BY categories DESC
    ```

### fix SAKILA_ACTOR_INFO_A_01
- section: ACTOR_INFO   tier: Advanced
- title: Check category counts against the tables
- why: Comparing NULL with a count produces UNKNOWN, so the current check silently skips actors with NULL `film_info`.
- request: Show actors whose category count parsed from film_info differs from their distinct category count in the tables. Treat NULL film_info as zero categories and order by actor id.
- sql:

    ```sql
    SELECT ai.actor_id, ai.first_name, ai.last_name
    FROM actor_info ai
    WHERE COALESCE(CHAR_LENGTH(ai.film_info)
                       - CHAR_LENGTH(REPLACE(ai.film_info, ':', '')), 0)
              <> (SELECT COUNT(DISTINCT fc.category_id)
                  FROM film_actor fa
                           JOIN film_category fc ON fc.film_id = fa.film_id
                  WHERE fa.actor_id = ai.actor_id)
    ORDER BY ai.actor_id
    ```

### fix SAKILA_ACTOR_INFO_B_01
- section: ACTOR_INFO   tier: Basic
- title: Preview actor 1’s film information
- why: `SELECT *` returns the full string as well as its preview, with two columns named `film_info`. Select the requested columns explicitly.
- request: Show actor 1’s id, first name, last name and the first 80 characters of film_info.
- sql:

    ```sql
    SELECT actor_id, first_name, last_name,
           LEFT(film_info, 80) AS film_info
    FROM actor_info
    WHERE actor_id = 1
    ```

### fix SAKILA_FILM_ACTOR_A_03
- section: FILM_ACTOR   tier: Advanced
- title: Films with identical casts
- why: Starting from shared castings excludes pairs of films whose casts are both empty, although they satisfy the stated definition. Compare the two actor sets directly.
- request: Find pairs of films with exactly the same actors, including pairs with no recorded actors. Show each pair once, its cast size, and order by both film ids.
- sql:

    ```sql
    SELECT f1.film_id AS first_film_id, f2.film_id AS second_film_id,
           (SELECT COUNT(*)
            FROM film_actor fa
            WHERE fa.film_id = f1.film_id) AS actors
    FROM film f1
             JOIN film f2 ON f2.film_id > f1.film_id
    WHERE NOT EXISTS (
              SELECT 1
              FROM film_actor fa1
              WHERE fa1.film_id = f1.film_id
                AND NOT EXISTS (
                    SELECT 1
                    FROM film_actor fa2
                    WHERE fa2.film_id = f2.film_id
                      AND fa2.actor_id = fa1.actor_id
                )
          )
      AND NOT EXISTS (
              SELECT 1
              FROM film_actor fa2
              WHERE fa2.film_id = f2.film_id
                AND NOT EXISTS (
                    SELECT 1
                    FROM film_actor fa1
                    WHERE fa1.film_id = f1.film_id
                      AND fa1.actor_id = fa2.actor_id
                )
          )
    ORDER BY f1.film_id, f2.film_id
    ```

### add SAKILA_FILM_I_05
- section: FILM   tier: Intermediate
- title: Copies available at each store
- why: Existing exercises count inventory and rentals but never distinguish owned copies from copies currently available. This uses nullable `return_date` without multiplying copies by their rental histories.
- request: For film 1, show every store’s total copies and copies available now. A copy is available when it has no rental with a NULL return date; include stores with no copies.
- sql:

    ```sql
    SELECT s.store_id, COUNT(i.inventory_id) AS copies,
           COUNT(CASE
                     WHEN i.inventory_id IS NOT NULL
                         AND NOT EXISTS (
                             SELECT 1
                             FROM rental r
                             WHERE r.inventory_id = i.inventory_id
                               AND r.return_date IS NULL
                         ) THEN 1
                 END) AS available_copies
    FROM store s
             LEFT JOIN inventory i
                       ON i.store_id = s.store_id AND i.film_id = 1
    GROUP BY s.store_id
    ORDER BY s.store_id
    ```

### add SAKILA_FILM_I_06
- section: FILM   tier: Intermediate
- title: Overdue films at a specified time
- why: `rental_duration` and the rental dates are otherwise unused. A fixed reporting time makes the exercise reproducible and allows historically correct return handling.
- request: At midnight on 1 August 2005, which rentals were past their due time and still unreturned? Show the rental, customer, film and due time, earliest due first, breaking ties by rental id.
- sql:

    ```sql
    SELECT r.rental_id, r.customer_id, f.film_id, f.title,
           DATE_ADD(r.rental_date, INTERVAL f.rental_duration DAY) AS due_date
    FROM film f
             JOIN inventory i ON i.film_id = f.film_id
             JOIN rental r ON r.inventory_id = i.inventory_id
    WHERE DATE_ADD(r.rental_date, INTERVAL f.rental_duration DAY)
              < '2005-08-01 00:00:00'
      AND (r.return_date IS NULL
               OR r.return_date > '2005-08-01 00:00:00')
    ORDER BY due_date, r.rental_id
    ```

### add SAKILA_LANGUAGE_A_01
- section: LANGUAGE   tier: Advanced
- title: Leading catalog languages for each original language
- why: The original-language foreign key has only a presence count and an exclusion query. This adds both language roles and populates the currently missing Advanced tier.
- request: For each recorded original language, find the catalog languages used by the most films, including ties. Show both language ids and names and the film count, ordered by original-language id and catalog-language id.
- sql:

    ```sql
    WITH counts AS (
        SELECT original_language_id, language_id, COUNT(*) AS films
        FROM film
        WHERE original_language_id IS NOT NULL
        GROUP BY original_language_id, language_id
    ),
         ranked AS (
             SELECT counts.*,
                    DENSE_RANK() OVER (
                        PARTITION BY original_language_id ORDER BY films DESC
                    ) AS film_rank
             FROM counts
         )
    SELECT ol.language_id AS original_language_id,
           ol.name AS original_language,
           l.language_id, l.name AS language, r.films
    FROM ranked r
             JOIN language ol ON ol.language_id = r.original_language_id
             JOIN language l ON l.language_id = r.language_id
    WHERE r.film_rank = 1
    ORDER BY ol.language_id, l.language_id
    ```

### add SAKILA_FILM_TEXT_I_07
- section: FILM_TEXT   tier: Intermediate
- title: Descriptions out of sync
- why: The existing consistency exercise checks titles alone. The published update trigger uses ordinary inequality, which can miss description changes between NULL and a non-NULL value.
- request: Find films whose film_text description differs from the film description, including differences involving NULL. Show both descriptions, ordered by film id.
- sql:

    ```sql
    SELECT f.film_id, f.title, f.description AS film_description,
           ft.description AS indexed_description
    FROM film f
             JOIN film_text ft ON ft.film_id = f.film_id
    WHERE NOT (ft.description <=> f.description)
    ORDER BY f.film_id
    ```

### add SAKILA_FILM_TEXT_I_06
- section: FILM_TEXT   tier: Intermediate
- title: Validate the title-chain assumptions
- why: The recursive exercise relies on title structure and first-word uniqueness that the DDL does not enforce. Guard those facts once; the first-word check also guards title uniqueness used by title-based ordering elsewhere.
- request: Check the title-chain prerequisites: count titles that do not contain exactly two nonempty words separated by one space, repeated first words, and titles whose final word has no matching first word.
- sql:

    ```sql
    SELECT (SELECT COUNT(*)
            FROM film_text
            WHERE title NOT REGEXP '^[^[:space:]]+ [^[:space:]]+$')
               AS malformed_titles,
           (SELECT COUNT(*)
            FROM (SELECT SUBSTRING_INDEX(title, ' ', 1) AS first_word
                  FROM film_text
                  GROUP BY first_word
                  HAVING COUNT(*) > 1) duplicates)
               AS repeated_first_words,
           (SELECT COUNT(*)
            FROM film_text ft
            WHERE NOT EXISTS (
                SELECT 1
                FROM film_text next_film
                WHERE SUBSTRING_INDEX(next_film.title, ' ', 1)
                          = SUBSTRING_INDEX(ft.title, ' ', -1)
            )) AS unmatched_endings
    ```

### add SAKILA_FILM_B_07
- section: FILM   tier: Basic
- title: Audit catalog metadata
- why: Several exercises rely on populated metadata or all five ratings being represented. A single audit exposes those data assumptions and introduces the otherwise unused nullable `release_year`.
- request: Show the total films, the numbers missing a description, release year, length or rating, and the number of distinct known ratings. Zero missing values and five distinct ratings confirm those sample-data assumptions.
- sql:

    ```sql
    SELECT COUNT(*) AS films,
           COUNT(*) - COUNT(description) AS missing_descriptions,
           COUNT(*) - COUNT(release_year) AS missing_release_years,
           COUNT(*) - COUNT(length) AS missing_lengths,
           COUNT(*) - COUNT(rating) AS missing_ratings,
           COUNT(DISTINCT rating) AS known_ratings
    FROM film
    ```