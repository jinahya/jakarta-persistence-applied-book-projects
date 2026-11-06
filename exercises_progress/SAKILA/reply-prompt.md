You reviewed the Sakila exercises blind, in four batches (1/review-codex.md .. 4/review-codex.md). Claude reviewed the
same batches (1/review-claude.md .. 4/review-claude.md). Below is where the decisions differ from your proposals. For
each point answer in one or two sentences: `agree` (you accept the decision) or `hold` (you keep yours, and why). Do
not run anything; read only this directory. Markdown, nothing else, numbered as below.

1. FILM_A_01 (count films above their rating's average, for every rating incl. NULL): rejected. No rating is NULL in
   the data, and a new check, SAKILA_FILM_B_07, counts the NULLs of every optional film column.
2. FILM_ACTOR_A_03 (pairs of films with identical casts, empty casts included): rejected. Two empty casts being
   "identical" is not what a reader asks, and the double NOT EXISTS over all film pairs is a million-pair query.
3. LANGUAGE_A_01: Claude's version (each language's films as language and as original language) taken over yours,
   since original_language_id is NULL for every film in the data, so yours returns no row.
4. FILM_I_06 (overdue at a fixed time) and SCHEMA_I_14 (available copies per store and film), SCHEMA_I_15 (language
   roles), SCHEMA_I_16 (film_text reconciliation): rejected as duplicates of what this round adds elsewhere
   (INVENTORY_A_03, FILM_I_05, LANGUAGE_I_03, FILM_TEXT_I_01/I_03/I_06).
5. INVENTORY_I_03 (count copies, not open rentals): rejected; INVENTORY_I_06, a check that a copy has one open rental
   at most, guards the equality.
6. CUSTOMER_A_02 (zero-payment customers, stores with none above average): rejected; CUSTOMER_I_06, a check for
   customers with no payment, guards the assumption.
7. CUSTOMER_B_02, CUSTOMER_LIST_B_02, PAYMENT_B_01 (drop the join to store or staff, return bare ids): rejected; the
   module returns whole entity rows (`st.*`) on purpose, as its JPQL answers map entities.
8. CUSTOMER_B_07 (customers registered in February 2006): rejected; every customer has the same create_date in the
   data, so it returns all of them.
9. FILM_LIST_A_02: Claude's (most actors per category, from the view's actors string) over your three cheapest per
   category. FILM_LIST_B_05 (descriptions mentioning dinosaurs): rejected, a LIKE search the module has.
10. SCHEMA_I_07 (COUNT(DISTINCT rental_id)): rejected; PAYMENT_B_06, a check that a rental has one payment at most,
    guards COUNT(*). SCHEMA_I_09 takes your NULL-length point, with an 'unknown' group as FILM_I_03.
11. Removes by Claude you did not propose: ADDRESS_A_01 (ADDRESS_I_03's 'none' class counts the same addresses) and
    SCHEMA_A_03 (a running total over payment alone, as PAYMENT_A_01).
12. COUNTRY: your duplicate-name check is taken as COUNTRY_I_05 (Intermediate, as the other GROUP BY ... HAVING checks),
    not COUNTRY_B_04; CITY_B_04 likewise as CITY_I_06.
