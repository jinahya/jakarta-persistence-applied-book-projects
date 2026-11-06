### fix HOG_HEAD_B_10

- section: HEAD   tier: Basic
- title: A country's list, ten terms a page
- why: The DDL does not enforce uniqueness of term_start within a country. Add id to make page boundaries deterministic.
- request: Show the second page of a country's terms, ten per page, earliest first; order terms starting together by id.
- sql:

    ```sql
    SELECT *
    FROM head
    WHERE country = :country
    ORDER BY term_start ASC, id ASC
    LIMIT 10 OFFSET 10
    ```

### fix HOG_HEAD_I_11

- section: HEAD   tier: Advanced
- title: Party share of completed terms, the top three per country
- why: Window functions belong in Advanced, and tied totals currently make the top three unstable. Guard against a zero total, which the DDL permits.
- request: For each country, show up to three parties with the most days in completed terms and their percentage of all completed-term days; break ties by party. Treat each stored party value separately and report an undefined percentage as NULL.
- sql:

    ```sql
    WITH totals AS (SELECT country,
                           party,
                           SUM(julianday(term_end) - julianday(term_start)) AS days
                    FROM head
                    WHERE term_end IS NOT NULL
                    GROUP BY country, party),
         placed AS (SELECT *,
                           ROUND(100.0 * days
                                     / NULLIF(SUM(days) OVER (PARTITION BY country), 0),
                                 1) AS tenure_share,
                           ROW_NUMBER() OVER (PARTITION BY country
                               ORDER BY days DESC, party ASC) AS place
                    FROM totals)
    SELECT country, party, tenure_share
    FROM placed
    WHERE place <= 3
    ORDER BY country ASC, place ASC
    ```

### fix HOG_SCHEMA_I_04

- section: SCHEMA   tier: Intermediate
- title: Living heads per office
- why: The inner join omits offices with no living heads. The request asks for every office.
- request: Show every office with its title and number of living heads, including zero; count a name once within a country.
- sql:

    ```sql
    SELECT g.*, COUNT(DISTINCT h.name) AS living
    FROM office g
             LEFT JOIN head h ON h.country = g.country
        AND h.died IS NULL
    GROUP BY g.country
    ORDER BY g.country ASC
    ```

### fix HOG_SCHEMA_I_05

- section: SCHEMA   tier: Intermediate
- title: Terms per century, side by side
- why: Calendar centuries begin in years ending in 01. The current ranges also incorrectly include every earlier year in the 18th century and every later year in the 21st.
- request: For every office, show its title and counts of terms beginning in the 18th through 21st calendar centuries, with zero where none began.
- sql:

    ```sql
    SELECT g.*,
           SUM(CASE WHEN h.term_start >= '1701-01-01'
                         AND h.term_start < '1801-01-01' THEN 1 ELSE 0 END) AS c18,
           SUM(CASE WHEN h.term_start >= '1801-01-01'
                         AND h.term_start < '1901-01-01' THEN 1 ELSE 0 END) AS c19,
           SUM(CASE WHEN h.term_start >= '1901-01-01'
                         AND h.term_start < '2001-01-01' THEN 1 ELSE 0 END) AS c20,
           SUM(CASE WHEN h.term_start >= '2001-01-01'
                         AND h.term_start < '2101-01-01' THEN 1 ELSE 0 END) AS c21
    FROM office g
             LEFT JOIN head h ON h.country = g.country
    GROUP BY g.country
    ORDER BY g.country ASC
    ```

### fix HOG_SCHEMA_A_06

- section: SCHEMA   tier: Advanced
- title: New heads per century, with a running total
- why: The current century formula assigns boundary years incorrectly. Correct the explanation as well: 1800 belongs to the 18th century.
- request: For each office, show how many people first took office in each represented calendar century and the running total through that century; treat a name as one person within a country.
- sql:

    ```sql
    WITH firsts AS (SELECT country, name, MIN(term_start) AS first_start
                    FROM head
                    GROUP BY country, name),
         per_century AS (SELECT g.country,
                                g.head_title,
                                (CAST(SUBSTR(f.first_start, 1, 4) AS INTEGER) - 1)
                                    / 100 + 1 AS century,
                                COUNT(*) AS new_persons
                         FROM office g
                                  JOIN firsts f ON f.country = g.country
                         GROUP BY g.country, g.head_title, century)
    SELECT country,
           head_title,
           century,
           new_persons,
           SUM(new_persons) OVER (PARTITION BY country
               ORDER BY century ROWS UNBOUNDED PRECEDING) AS persons_so_far
    FROM per_century
    ORDER BY country ASC, century ASC
    ```

### fix HOG_HEAD_B_04

- section: HEAD   tier: Basic
- title: Terms by name
- why: LIKE interprets percent and underscore in the input as wildcards, although the request describes a literal name fragment. Preserve ASCII case folding while treating the fragment literally.
- request: Find every term whose name contains my literal text, ignoring case for ASCII letters; list by country, start date and id.
- sql:

    ```sql
    SELECT *
    FROM head
    WHERE INSTR(LOWER(name), LOWER(:name)) > 0
    ORDER BY country ASC, term_start ASC, id ASC
    ```

### fix HOG_HEAD_I_08

- section: HEAD   tier: Advanced
- title: The first and the latest terms of each country
- why: Window functions belong in Advanced, and the numbering needs an id tie-breaker. The explanation is also wrong at exactly 2 * :n terms, when the sets do not overlap.
- request: For each country, show its first :n and latest :n terms, taking :n as a positive integer. Order simultaneous starts by id; label a term 'first' if it belongs to both sets.
- sql:

    ```sql
    SELECT *,
           CASE WHEN first_rn <= :n THEN 'first' ELSE 'latest' END AS which
    FROM (SELECT h.*,
                 ROW_NUMBER() OVER (PARTITION BY country
                     ORDER BY term_start ASC, id ASC) AS first_rn,
                 ROW_NUMBER() OVER (PARTITION BY country
                     ORDER BY term_start DESC, id DESC) AS latest_rn
          FROM head h)
    WHERE first_rn <= :n
       OR latest_rn <= :n
    ORDER BY country ASC, term_start ASC, id ASC
    ```

### fix HOG_HEAD_A_05

- section: HEAD   tier: Advanced
- title: Predecessor and successor
- why: Ordering windows solely by term_start can assign different neighbors to simultaneous starts. The DDL supplies no chronological ordering between such terms, so state an explicit tie convention.
- request: For an exact name, show every term and the names in the immediately preceding and following recorded terms of that country; order simultaneous starts by id.
- sql:

    ```sql
    SELECT *
    FROM (SELECT h.*,
                 LAG(name) OVER (PARTITION BY country
                     ORDER BY term_start ASC, id ASC) AS predecessor,
                 LEAD(name) OVER (PARTITION BY country
                     ORDER BY term_start ASC, id ASC) AS successor
          FROM head h)
    WHERE name = :name
    ORDER BY country ASC, term_start ASC, id ASC
    ```

### fix HOG_SCHEMA_A_05

- section: SCHEMA   tier: Intermediate
- title: Presidents and the prime ministers of their time
- why: Inner joins omit presidential terms with no overlapping prime minister. Joins and grouped subqueries place this exercise in Intermediate.
- request: Show the ten presidential terms overlapping the most distinct prime ministers, counting a name once per country and including zero matches. Count shared boundary days as overlap, treat open ends as '9999-12-31', and break ties by start date, country and id.
- sql:

    ```sql
    WITH matches AS (SELECT DISTINCT p.id, m.country, m.name
                     FROM head p
                              JOIN office pg ON pg.country = p.country
                         AND pg.head_kind = 'PRESIDENT'
                              JOIN head m
                                   ON m.term_start <= COALESCE(p.term_end, '9999-12-31')
                         AND COALESCE(m.term_end, '9999-12-31') >= p.term_start
                              JOIN office mg ON mg.country = m.country
                         AND mg.head_kind = 'PRIME_MINISTER')
    SELECT p.*, COUNT(m.name) AS prime_ministers
    FROM head p
             JOIN office pg ON pg.country = p.country
        AND pg.head_kind = 'PRESIDENT'
             LEFT JOIN matches m ON m.id = p.id
    GROUP BY p.id
    ORDER BY prime_ministers DESC, p.term_start ASC, p.country ASC, p.id ASC
    LIMIT 10
    ```

### fix HOG_OFFICE_I_03

- section: SCHEMA   tier: Intermediate
- title: Offices without an incumbent
- why: This exercise reads both tables, so the conventions place it in SCHEMA. Describe the recorded open terms without assuming the snapshot establishes who holds office today.
- request: List offices with no recorded term whose end is NULL, by country code.
- sql:

    ```sql
    SELECT g.*
    FROM office g
    WHERE NOT EXISTS (SELECT 1
                      FROM head h
                      WHERE h.country = g.country
                        AND h.term_end IS NULL)
    ORDER BY g.country ASC
    ```

### fix HOG_OFFICE_A_01

- section: OFFICE   tier: Intermediate
- title: What number counts, in a phrase
- why: This uses a derived-table subquery, not an Advanced feature. Keep its id when moving it to Intermediate, and describe the extraction without assuming particular stored sentences.
- request: Show each office with the part of its numbering description before the first comma or semicolon, or the whole description if neither occurs.
- sql:

    ```sql
    SELECT *,
           CASE
               WHEN comma > 0 AND (semicolon = 0 OR comma < semicolon)
                   THEN SUBSTR(numbering, 1, comma - 1)
               WHEN semicolon > 0 THEN SUBSTR(numbering, 1, semicolon - 1)
               ELSE numbering
               END AS counts
    FROM (SELECT *,
                 INSTR(numbering, ',') AS comma,
                 INSTR(numbering, ';') AS semicolon
          FROM office)
    ORDER BY country ASC
    ```

### add HOG_HEAD_I_18

- section: HEAD   tier: Intermediate
- title: Repeated term starts
- why: The DDL explicitly leaves the intended `(country, term_start)` identity unconstrained. This audit exposes records that undermine chronological exercises.
- request: Find country and start-date combinations recorded more than once, with their row counts, by country and date.
- sql:

    ```sql
    SELECT country, term_start, COUNT(*) AS terms
    FROM head
    GROUP BY country, term_start
    HAVING COUNT(*) > 1
    ORDER BY country ASC, term_start ASC
    ```

### add HOG_HEAD_B_12

- section: HEAD   tier: Basic
- title: Look up an official number
- why: No existing exercise retrieves terms by number. Returning every match teaches why the indexed `(country, number)` pair is not a unique key.
- request: Show every term carrying a given number in a given country, earliest first.
- sql:

    ```sql
    SELECT *
    FROM head
    WHERE country = :country
      AND number = :number
    ORDER BY term_start ASC, id ASC
    ```

### add HOG_OFFICE_A_02

- section: OFFICE   tier: Advanced
- title: Rank titles by character count
- why: This supplies a genuine window-function exercise for OFFICE after moving its current Advanced exercise. Character counts are useful when reviewing localized labels.
- request: Rank office titles from most characters to fewest, giving equal lengths the same rank; list tied offices by country.
- sql:

    ```sql
    SELECT country,
           head_title,
           LENGTH(head_title) AS characters,
           DENSE_RANK() OVER (ORDER BY LENGTH(head_title) DESC) AS place
    FROM office
    ORDER BY place ASC, country ASC
    ```

### remove HOG_HEAD_I_09

- section: HEAD   tier: Intermediate
- title: The first two terms of each country
- why: This repeats the first-term selection already covered by HOG_HEAD_I_08 with :n = 2. Retire the id and retain the more general exercise.