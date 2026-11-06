# HOG — Claude's review (written before reading codex.md)

Inputs: 60 live exercises (HEAD 33, OFFICE 8, SCHEMA 19), 6 retired (HEAD_B_07, HEAD_I_02, HEAD_I_07, SCHEMA_B_02,
SCHEMA_B_04, SCHEMA_A_01), `ddl/schema.sql`. sqlite-jdbc 3.53, so `GROUP_CONCAT(... ORDER BY ...)` (HEAD_A_07,
OFFICE_I_01) is fine.

### fix HOG_HEAD_B_01
- section: HEAD   tier: Basic
- title: Who held office on a day
- why: `term_start <= :date AND term_end >= :date` matches both heads on a handover day (one term's end is the next
  one's start, which the data does; HEAD_I_16 and SCHEMA_A_05 say so), so "each country's head" can give two rows. Same
  question; the request should say what a handover day gives.
- request: A reader gives a date and wants each country's head on that day. A country whose office was vacant is absent;
  on a handover day, the day one term ends and the next begins, both heads show.
- sql: unchanged.

### fix HOG_SCHEMA_A_02
- section: SCHEMA   tier: Advanced
- title: Every office on a day, vacant or not
- why: `g.*, COALESCE(h.name, '(vacant)') AS name, h.*` gives two columns called `name` (and two `country`), the first
  of which the request calls 'vacant' while the SQL writes '(vacant)'. Name the columns; the handover day as in B_01.
- request: A reader gives a date and wants every office with its head on that day, or '(vacant)' where the office was
  empty or the list had not yet begun; on a handover day both heads show.
- sql:
    SELECT g.country, g.head_title, COALESCE(h.name, '(vacant)') AS name, h.number, h.term_start, h.term_end
    FROM office g
             LEFT JOIN head h ON h.country = g.country
        AND h.term_start <= :date
        AND (h.term_end IS NULL OR h.term_end >= :date)
    ORDER BY g.country ASC, h.term_start ASC NULLS FIRST

### fix HOG_SCHEMA_A_03
- section: SCHEMA   tier: Advanced
- title: The incumbents' contemporaries
- why: `i.*, o.*, g.*` repeats every column of head twice (country, name, ...), so the pair cannot be read without
  knowing the column order; name the incumbent's and the other's columns.
- sql:
    SELECT i.country    AS country,
           i.name       AS incumbent,
           i.term_start AS took_office,
           o.country    AS other_country,
           g.head_title AS other_title,
           o.name       AS other_head
    FROM head i
             JOIN head o ON o.country <> i.country
        AND o.term_start <= i.term_start
        AND (o.term_end IS NULL OR o.term_end >= i.term_start)
             JOIN office g ON g.country = o.country
    WHERE i.term_end IS NULL
    ORDER BY i.country ASC, o.country ASC, o.term_start ASC

### fix HOG_HEAD_I_11
- section: HEAD   tier: Intermediate
- title: Party share of completed terms, the top three per country
- why: ROW_NUMBER over the summed days has no tie-break, and neither has the outer ORDER BY; two parties with the same
  days would come in any order, and the third place could change between runs. Add `party ASC` to both.

### fix (format) HOG_HEAD_I_01, HOG_HEAD_I_08, HOG_HEAD_A_01, HOG_HEAD_A_02, HOG_HEAD_A_03, HOG_HEAD_A_05
- why: a formatter left `date ('now')` with a space, and two window columns on one line (`... AS first_rn, ROW_NUMBER()
  ...`), unlike every other exercise. One column per line, `date('now')`. The statements do not change.

### add HOG_HEAD_B_12
- section: HEAD   tier: Basic
- title: Terms that end after the head died
- why: a data check the DDL invites: died is a year and term_end a date, and a term cannot end in a year after its
  head's death. Basic: one table, a filter.
- request: A term cannot outlast its head. List the terms whose end falls in a year after the head's death, by country,
  then in date order; the check passes when nothing comes back.
- sql:
    SELECT *
    FROM head
    WHERE died IS NOT NULL
      AND CAST(SUBSTR(term_end, 1, 4) AS INTEGER) > died
    ORDER BY country ASC, term_start ASC

### add HOG_HEAD_I_18
- section: HEAD   tier: Intermediate
- title: More than one incumbent
- why: OFFICE_I_03 checks an office with no open term; nothing checks the other side, two open terms in one country,
  which would break every "incumbent" exercise. GROUP BY with HAVING.
- request: A country has one head in office now, at most. List the countries with more than one term that has not
  ended, and how many; the check passes when nothing comes back.
- sql:
    SELECT country, COUNT(*) AS open_terms
    FROM head
    WHERE term_end IS NULL
    GROUP BY country
    HAVING COUNT(*) > 1
    ORDER BY country ASC

No removes: HEAD_I_09 (the first two terms) is HEAD_I_08 with :n = 2 and the first half only, but it is the plain
top-n-per-group that I_08 builds on.
