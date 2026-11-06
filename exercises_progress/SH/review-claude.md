# SH — Claude's review

### fix SH_CAL_MONTH_SALES_MV_A_01
- section: CAL_MONTH_SALES_MV   tier: Advanced
- title: Running total of monthly revenue
- why: The request asks for a year-to-date total, but the window runs over the whole range. When `:fromMonth`..`:toMonth` crosses a year boundary, the total carries over into the next year instead of starting again in January.
- request: Finance wants each month's revenue between `:fromMonth` and `:toMonth`, with the year-to-date running total next to it.
- sql:
    SELECT CALENDAR_MONTH_DESC,
           DOLLARS,
           SUM(DOLLARS) OVER (PARTITION BY SUBSTR(CALENDAR_MONTH_DESC, 1, 4)
                              ORDER BY CALENDAR_MONTH_DESC) AS RUNNING_TOTAL
    FROM CAL_MONTH_SALES_MV
    WHERE CALENDAR_MONTH_DESC BETWEEN :fromMonth AND :toMonth
    ORDER BY CALENDAR_MONTH_DESC

### fix SH_PROFITS_I_01
- section: PROFITS   tier: Intermediate
- title: Thinnest margins
- why: The top-10 cut is ordered by a ratio alone, so ties at tenth place make the result unstable. The division also fails when a product's revenue in the period sums to zero.
- request: Finance wants the ten products with the lowest margin ratio between `:fromDay` and `:toDay`, with the revenue and margin behind it.
- sql:
    SELECT PROD_ID,
           SUM(AMOUNT_SOLD)                                         AS REVENUE,
           SUM(AMOUNT_SOLD - TOTAL_COST)                            AS MARGIN,
           SUM(AMOUNT_SOLD - TOTAL_COST) / NULLIF(SUM(AMOUNT_SOLD), 0) AS MARGIN_RATIO
    FROM PROFITS
    WHERE TIME_ID BETWEEN :fromDay AND :toDay
    GROUP BY PROD_ID
    ORDER BY MARGIN_RATIO NULLS LAST, PROD_ID
    FETCH FIRST 10 ROWS ONLY

### fix SH_SALES_I_01
- section: SALES   tier: Intermediate
- title: Top spenders of a period
- why: `ORDER BY SPENT DESC` with `FETCH FIRST 10` has no tie-breaker, so which customer gets the tenth row is left to the database. The JPQL has the same problem with `setMaxResults(10)`; add `s.customer.custId` there as well.
- request: The loyalty programme wants the ten customers who spent the most between `:fromDay` and `:toDay`, with the number of sales lines and units behind it.
- sql:
    SELECT CUST_ID, COUNT(*) AS LINES, SUM(QUANTITY_SOLD) AS UNITS, SUM(AMOUNT_SOLD) AS SPENT
    FROM SALES
    WHERE TIME_ID BETWEEN :fromDay AND :toDay
    GROUP BY CUST_ID
    ORDER BY SPENT DESC, CUST_ID
    FETCH FIRST 10 ROWS ONLY

### fix SH_SCHEMA_I_02
- section: SCHEMA   tier: Intermediate
- title: Ten best sellers
- why: The note admits that ties at tenth place are "cut arbitrarily". A top-N exercise should be deterministic, so add `PROD_ID` as a tie-breaker (and `p.prodId` in the JPQL). Keep `WITH TIES` as the alternative named in the note.
- request: Merchandising wants the ten products that sold the most units in `:year`, with the revenue they brought in.
- sql:
    SELECT p.PROD_ID, p.PROD_NAME, SUM(s.QUANTITY_SOLD) AS UNITS, SUM(s.AMOUNT_SOLD) AS REVENUE
    FROM SALES s
             JOIN PRODUCTS p ON p.PROD_ID = s.PROD_ID
             JOIN TIMES t ON t.TIME_ID = s.TIME_ID
    WHERE t.CALENDAR_YEAR = :year
    GROUP BY p.PROD_ID, p.PROD_NAME
    ORDER BY UNITS DESC, p.PROD_ID
    FETCH FIRST 10 ROWS ONLY

### fix SH_CUSTOMERS_B_04
- section: CUSTOMERS   tier: Basic
- title: Income bands, unknowns last
- why: `CUST_CREDIT_LIMIT` is nullable, and Oracle sorts `NULL` first under `DESC`, so customers with no limit come before the highest limit in each band. That is the same "unknowns at the start" problem the exercise is about. The order also has no unique tie-breaker.
- request: The credit team wants the customers of `:city` ordered by income band, highest credit limit first within a band, and the customers whose income band is unknown at the end of the list rather than the start.
- sql:
    SELECT CUST_ID, CUST_LAST_NAME, CUST_INCOME_LEVEL, CUST_CREDIT_LIMIT
    FROM CUSTOMERS
    WHERE CUST_CITY = :city
    ORDER BY CUST_INCOME_LEVEL ASC NULLS LAST, CUST_CREDIT_LIMIT DESC NULLS LAST, CUST_ID

### fix SH_SUPPLEMENTARY_DEMOGRAPHICS_A_01
- section: SUPPLEMENTARY_DEMOGRAPHICS   tier: Advanced
- title: Occupations ahead of the overall take-up
- why: `OCCUPATION` is nullable, so customers with no recorded occupation show up as an "occupation" of their own. `AVG(AFFINITY_CARD)` also counts only non-null cards while `COUNT(*)` counts every customer. Keep `AVG`, and guard the 0/1, never-null assumption with a check (`SELECT COUNT(*) FROM SUPPLEMENTARY_DEMOGRAPHICS WHERE AFFINITY_CARD IS NULL OR AFFINITY_CARD NOT IN (0, 1)`, expected 0). The order also needs a tie-breaker.
- request: The loyalty programme wants the occupations whose affinity-card take-up rate is above the rate across all customers, highest first.
- sql:
    SELECT OCCUPATION, COUNT(*) AS CUSTOMERS, AVG(AFFINITY_CARD) AS TAKE_UP
    FROM SUPPLEMENTARY_DEMOGRAPHICS
    WHERE OCCUPATION IS NOT NULL
    GROUP BY OCCUPATION
    HAVING AVG(AFFINITY_CARD) > (SELECT AVG(AFFINITY_CARD) FROM SUPPLEMENTARY_DEMOGRAPHICS)
    ORDER BY TAKE_UP DESC, OCCUPATION

### fix SH_SALES_B_01
- section: SALES   tier: Basic
- title: A day's takings through one channel
- why: A sales line is identified by all five foreign keys. With the day and channel fixed, `PROD_ID, CUST_ID` still leaves rows that differ only by `PROMO_ID` in an undefined order. The JPQL orders by `amountSold` alone; give it the same keys.
- request: Finance is checking the takings of `:day` through channel `:channelId`: every sales line, biggest amount first.
- sql:
    SELECT PROD_ID, CUST_ID, PROMO_ID, QUANTITY_SOLD, AMOUNT_SOLD
    FROM SALES
    WHERE TIME_ID = :day
      AND CHANNEL_ID = :channelId
    ORDER BY AMOUNT_SOLD DESC, PROD_ID, CUST_ID, PROMO_ID

### fix SH_COSTS_B_01
- section: COSTS   tier: Basic
- title: Prices below cost
- why: A `COSTS` record is keyed by product, day, channel and promotion. Ordering by `TIME_ID, PROD_ID` leaves the channel and promotion rows of one product and day in an undefined order.
- request: Finance wants every cost record between `:fromDay` and `:toDay` whose unit price is below its unit cost: a product priced at a loss on that day, through that channel, under that promotion.
- sql:
    SELECT TIME_ID, PROD_ID, CHANNEL_ID, PROMO_ID, UNIT_COST, UNIT_PRICE
    FROM COSTS
    WHERE TIME_ID BETWEEN :fromDay AND :toDay
      AND UNIT_PRICE < UNIT_COST
    ORDER BY TIME_ID, PROD_ID, CHANNEL_ID, PROMO_ID

### fix SH_PROFITS_B_01
- section: PROFITS   tier: Basic
- title: Loss-making sales
- why: A row of the view is one sales line, which is identified by all five keys. `TIME_ID, PROD_ID, CUST_ID` leaves the channel and promotion of the same customer, product and day unordered.
- request: Finance wants the sales between `:fromDay` and `:toDay` whose invoiced amount was below what the goods cost.
- sql:
    SELECT TIME_ID, PROD_ID, CUST_ID, CHANNEL_ID, PROMO_ID, QUANTITY_SOLD, AMOUNT_SOLD, TOTAL_COST
    FROM PROFITS
    WHERE TIME_ID BETWEEN :fromDay AND :toDay
      AND AMOUNT_SOLD < TOTAL_COST
    ORDER BY TIME_ID, PROD_ID, CUST_ID, CHANNEL_ID, PROMO_ID

### fix SH_CUSTOMERS_B_02
- section: CUSTOMERS   tier: Basic
- title: Customers in selected income bands
- why: For a mail drop the order `CUST_INCOME_LEVEL, CUST_LAST_NAME` is unstable within a surname, unlike the module's other customer lists (`..., CUST_FIRST_NAME, CUST_ID`). The JPQL needs the same tie-breakers.
- request: Marketing is planning a mail drop in `:city` (e.g. `Los Angeles`) aimed at the lower income bands, `:levels` (e.g. `A: Below 30,000`, `B: 30,000 - 49,999`).
- sql:
    SELECT CUST_ID, CUST_FIRST_NAME, CUST_LAST_NAME, CUST_STREET_ADDRESS, CUST_POSTAL_CODE, CUST_INCOME_LEVEL
    FROM CUSTOMERS
    WHERE CUST_CITY = :city
      AND CUST_INCOME_LEVEL IN ('A: Below 30,000', 'B: 30,000 - 49,999')
    ORDER BY CUST_INCOME_LEVEL, CUST_LAST_NAME, CUST_FIRST_NAME, CUST_ID

### add SH_SCHEMA_I_11
- section: SCHEMA   tier: Intermediate
- title: Promotions that never sold
- why: The DDL documents `PROMOTIONS` as the dimension that exists "to show outer join functionality", and the notes say only four promotions ever sold. Yet no exercise uses a `LEFT JOIN` that keeps the zero rows with their counts. `SH_SCHEMA_A_01` only covers `NOT EXISTS`.
- request: The promotions team wants every promotion it has run, with the number of sales lines and the revenue booked against it, including those that sold nothing, the least productive first.
- sql:
    SELECT pr.PROMO_ID, pr.PROMO_NAME, pr.PROMO_CATEGORY, pr.PROMO_COST,
           COUNT(s.PROMO_ID)             AS SALES_LINES,
           COALESCE(SUM(s.AMOUNT_SOLD), 0) AS REVENUE
    FROM PROMOTIONS pr
             LEFT JOIN SALES s ON s.PROMO_ID = pr.PROMO_ID
    WHERE pr.PROMO_CATEGORY <> 'NO PROMOTION'
    GROUP BY pr.PROMO_ID, pr.PROMO_NAME, pr.PROMO_CATEGORY, pr.PROMO_COST
    ORDER BY REVENUE, pr.PROMO_COST DESC, pr.PROMO_ID

### add SH_CUSTOMERS_B_05
- section: CUSTOMERS   tier: Basic
- title: Customer records in effect on a day
- why: The nullable effective-date columns `CUST_EFF_FROM` / `CUST_EFF_TO` (a slowly changing dimension) are never read. Filtering on an open-ended date range with `NULL` meaning "no bound" is a NULL-handling question at Basic level.
- request: The account-management team wants the customer records of `:city` that were in effect on `:day`; a missing start or end date means the record has no bound on that side.
- sql:
    SELECT CUST_ID, CUST_FIRST_NAME, CUST_LAST_NAME, CUST_EFF_FROM, CUST_EFF_TO, CUST_VALID
    FROM CUSTOMERS
    WHERE CUST_CITY = :city
      AND (CUST_EFF_FROM IS NULL OR CUST_EFF_FROM <= :day)
      AND (CUST_EFF_TO IS NULL OR CUST_EFF_TO >= :day)
    ORDER BY CUST_LAST_NAME, CUST_FIRST_NAME, CUST_ID

### add SH_PRODUCTS_I_02
- section: PRODUCTS   tier: Intermediate
- title: Discount headroom per subcategory
- why: `PROD_MIN_PRICE` and the subcategory hierarchy (`PROD_SUBCATEGORY_ID` under `PROD_CATEGORY`) are not used by any aggregate, and the only Intermediate products exercise is a plain scalar subquery. Grouping by the hierarchy's id is also safer than grouping by its name.
- request: Pricing wants, for each product subcategory, how many products it has and how far, on average and at most, their list price can be cut before reaching the minimum price, largest average headroom first.
- sql:
    SELECT PROD_CATEGORY, PROD_SUBCATEGORY_ID, PROD_SUBCATEGORY,
           COUNT(*)                                                              AS PRODUCTS,
           ROUND(100 * AVG((PROD_LIST_PRICE - PROD_MIN_PRICE)
                           / NULLIF(PROD_LIST_PRICE, 0)), 2)                     AS AVG_HEADROOM_PCT,
           MAX(PROD_LIST_PRICE - PROD_MIN_PRICE)                                 AS MAX_HEADROOM
    FROM PRODUCTS
    GROUP BY PROD_CATEGORY, PROD_SUBCATEGORY_ID, PROD_SUBCATEGORY
    ORDER BY AVG_HEADROOM_PCT DESC NULLS LAST, PROD_SUBCATEGORY_ID

### add SH_CUSTOMERS_I_02
- section: CUSTOMERS   tier: Intermediate
- title: Customers by decade of birth
- why: `CUST_YEAR_OF_BIRTH` and `CUST_GENDER` (both `NOT NULL`) are never aggregated. Bucketing by an expression with conditional counts is a natural Intermediate question that the only Intermediate customers exercise does not cover.
- request: Marketing wants the customer base by decade of birth, with the number of women and men in each decade, oldest decade first.
- sql:
    SELECT FLOOR(CUST_YEAR_OF_BIRTH / 10) * 10                 AS DECADE,
           COUNT(*)                                            AS CUSTOMERS,
           SUM(CASE WHEN CUST_GENDER = 'F' THEN 1 ELSE 0 END)  AS WOMEN,
           SUM(CASE WHEN CUST_GENDER = 'M' THEN 1 ELSE 0 END)  AS MEN
    FROM CUSTOMERS
    GROUP BY FLOOR(CUST_YEAR_OF_BIRTH / 10) * 10
    ORDER BY DECADE
