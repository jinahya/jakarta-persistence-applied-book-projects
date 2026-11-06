### fix SH_CAL_MONTH_SALES_MV_A_01

- section: CAL_MONTH_SALES_MV   tier: Advanced
- title: Year-to-date monthly revenue
- why: The current total starts at `:fromMonth` and continues across year boundaries. Calculate within each calendar year before filtering the displayed months.
- request: Show each month's revenue between `:fromMonth` and `:toMonth`, with its calendar-year-to-date revenue.
- sql:

    ```sql
    SELECT CALENDAR_MONTH_DESC, DOLLARS, RUNNING_TOTAL
    FROM (SELECT CALENDAR_MONTH_DESC,
                 DOLLARS,
                 SUM(DOLLARS) OVER (
                     PARTITION BY SUBSTR(CALENDAR_MONTH_DESC, 1, 4)
                     ORDER BY CALENDAR_MONTH_DESC) AS RUNNING_TOTAL
          FROM CAL_MONTH_SALES_MV)
    WHERE CALENDAR_MONTH_DESC BETWEEN :fromMonth AND :toMonth
    ORDER BY CALENDAR_MONTH_DESC
    ```

### fix SH_SCHEMA_A_05

- section: SCHEMA   tier: Advanced
- title: Gross margin with cost coverage
- why: The inner join silently excludes sales without costs; the accompanying suggestion to substitute zero overstates margin. Preserve revenue, expose missing costs, and leave complete cost and margin unknown when coverage is incomplete.
- request: Show revenue, cost, gross margin and margin ratio by category for `:year`, identifying sales lines without matching costs; leave cost and margin unknown for incomplete categories.
- sql:

    ```sql
    SELECT p.PROD_CATEGORY,
           SUM(s.AMOUNT_SOLD) AS REVENUE,
           COUNT(*) - COUNT(c.UNIT_COST) AS UNCosted_LINES,
           CASE WHEN COUNT(*) = COUNT(c.UNIT_COST)
                THEN SUM(s.QUANTITY_SOLD * c.UNIT_COST) END AS COST,
           CASE WHEN COUNT(*) = COUNT(c.UNIT_COST)
                THEN SUM(s.AMOUNT_SOLD - s.QUANTITY_SOLD * c.UNIT_COST)
                END AS MARGIN,
           CASE WHEN COUNT(*) = COUNT(c.UNIT_COST)
                THEN SUM(s.AMOUNT_SOLD - s.QUANTITY_SOLD * c.UNIT_COST)
                     / NULLIF(SUM(s.AMOUNT_SOLD), 0)
                END AS MARGIN_RATIO
    FROM SALES s
             JOIN PRODUCTS p ON p.PROD_ID = s.PROD_ID
             JOIN TIMES t ON t.TIME_ID = s.TIME_ID
             LEFT JOIN COSTS c ON c.PROD_ID = s.PROD_ID
        AND c.TIME_ID = s.TIME_ID
        AND c.CHANNEL_ID = s.CHANNEL_ID
        AND c.PROMO_ID = s.PROMO_ID
    WHERE t.CALENDAR_YEAR = :year
    GROUP BY p.PROD_CATEGORY
    ORDER BY MARGIN DESC NULLS LAST, p.PROD_CATEGORY
    ```

### fix SH_PROFITS_I_01

- section: PROFITS   tier: Intermediate
- title: Ten thinnest product margins
- why: Zero total revenue causes division by zero, and tied ratios make the selected ten unstable. State the view's cost-coverage limitation explicitly.
- request: Using sales represented in `PROFITS`, show the ten products with the lowest defined margin ratios between `:fromDay` and `:toDay`, breaking ties by product id.
- sql:

    ```sql
    SELECT PROD_ID,
           SUM(AMOUNT_SOLD) AS REVENUE,
           SUM(AMOUNT_SOLD - TOTAL_COST) AS MARGIN,
           SUM(AMOUNT_SOLD - TOTAL_COST)
               / NULLIF(SUM(AMOUNT_SOLD), 0) AS MARGIN_RATIO
    FROM PROFITS
    WHERE TIME_ID BETWEEN :fromDay AND :toDay
    GROUP BY PROD_ID
    HAVING SUM(AMOUNT_SOLD) <> 0
    ORDER BY MARGIN_RATIO, PROD_ID
    FETCH FIRST 10 ROWS ONLY
    ```

### fix SH_SCHEMA_I_09

- section: SCHEMA   tier: Intermediate
- title: Realised price against list price
- why: Neither quantities nor list prices have positivity constraints. Protect both divisions and place undefined ratios last with a stable tie-breaker.
- request: Compare each selling product's average realised unit price in `:year` with its list price, showing undefined prices or ratios as NULL.
- sql:

    ```sql
    SELECT p.PROD_ID, p.PROD_NAME, p.PROD_LIST_PRICE,
           SUM(s.AMOUNT_SOLD)
               / NULLIF(SUM(s.QUANTITY_SOLD), 0) AS REALISED_PRICE,
           SUM(s.AMOUNT_SOLD)
               / NULLIF(SUM(s.QUANTITY_SOLD), 0)
               / NULLIF(p.PROD_LIST_PRICE, 0) AS REALISED_RATIO
    FROM SALES s
             JOIN PRODUCTS p ON p.PROD_ID = s.PROD_ID
             JOIN TIMES t ON t.TIME_ID = s.TIME_ID
    WHERE t.CALENDAR_YEAR = :year
    GROUP BY p.PROD_ID, p.PROD_NAME, p.PROD_LIST_PRICE
    ORDER BY REALISED_RATIO NULLS LAST, p.PROD_ID
    ```

### fix SH_SCHEMA_A_04

- section: SCHEMA   tier: Advanced
- title: Three leading products per category
- why: `RANK() <= 3` can return more than three products. Use a deterministic row number to answer the stated request.
- request: Show up to three selling products per category with the highest revenue in `:year`, breaking revenue ties by product id.
- sql:

    ```sql
    SELECT PROD_CATEGORY, PROD_ID, PROD_NAME, REVENUE, RNK
    FROM (SELECT p.PROD_CATEGORY,
                 p.PROD_ID,
                 p.PROD_NAME,
                 SUM(s.AMOUNT_SOLD) AS REVENUE,
                 ROW_NUMBER() OVER (
                     PARTITION BY p.PROD_CATEGORY
                     ORDER BY SUM(s.AMOUNT_SOLD) DESC, p.PROD_ID) AS RNK
          FROM SALES s
                   JOIN PRODUCTS p ON p.PROD_ID = s.PROD_ID
                   JOIN TIMES t ON t.TIME_ID = s.TIME_ID
          WHERE t.CALENDAR_YEAR = :year
          GROUP BY p.PROD_CATEGORY, p.PROD_ID, p.PROD_NAME)
    WHERE RNK <= 3
    ORDER BY PROD_CATEGORY, RNK
    ```

### fix SH_SCHEMA_A_10

- section: SCHEMA   tier: Advanced
- title: Three-month moving revenue average
- why: Filtering to `:year` before calculating the window excludes the preceding November and December; months without sales also disappear. Include calendar months before calculating, then filter the output.
- request: Show every month of `:year`, its revenue, and its average revenue over that month and the preceding two months, counting months without sales as zero; return NULL when the calendar lacks a full three-month window.
- sql:

    ```sql
    WITH BOUNDS AS (
        SELECT TO_DATE(:year || '-01-01', 'YYYY-MM-DD') AS YEAR_START
        FROM DUAL
    ),
    MONTHLY AS (
        SELECT TRUNC(t.TIME_ID, 'MM') AS MONTH_START,
               COALESCE(SUM(s.AMOUNT_SOLD), 0) AS REVENUE
        FROM TIMES t
                 CROSS JOIN BOUNDS b
                 LEFT JOIN SALES s ON s.TIME_ID = t.TIME_ID
        WHERE t.TIME_ID >= ADD_MONTHS(b.YEAR_START, -2)
          AND t.TIME_ID < ADD_MONTHS(b.YEAR_START, 12)
        GROUP BY TRUNC(t.TIME_ID, 'MM')
    ),
    AVERAGED AS (
        SELECT MONTH_START, REVENUE,
               CASE WHEN COUNT(*) OVER (
                             ORDER BY MONTH_START
                             ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) = 3
                    THEN ROUND(AVG(REVENUE) OVER (
                             ORDER BY MONTH_START
                             ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2)
                    END AS MOVING_AVERAGE
        FROM MONTHLY
    )
    SELECT TO_CHAR(a.MONTH_START, 'YYYY-MM') AS CALENDAR_MONTH_DESC,
           a.REVENUE, a.MOVING_AVERAGE
    FROM AVERAGED a
             CROSS JOIN BOUNDS b
    WHERE a.MONTH_START >= b.YEAR_START
    ORDER BY a.MONTH_START
    ```

### fix SH_SALES_I_01

- section: SALES   tier: Intermediate
- title: Ten highest-spending customers
- why: Equal spending totals make the selected ten arbitrary. Customer id gives a deterministic boundary without unnecessary paging clauses.
- request: Show the ten customers who spent most between `:fromDay` and `:toDay`, with sales-line and unit counts; break spending ties by customer id.
- sql:

    ```sql
    SELECT CUST_ID, COUNT(*) AS LINES,
           SUM(QUANTITY_SOLD) AS UNITS, SUM(AMOUNT_SOLD) AS SPENT
    FROM SALES
    WHERE TIME_ID BETWEEN :fromDay AND :toDay
    GROUP BY CUST_ID
    ORDER BY SPENT DESC, CUST_ID
    FETCH FIRST 10 ROWS ONLY
    ```

### fix SH_SCHEMA_I_02

- section: SCHEMA   tier: Intermediate
- title: Ten best sellers
- why: Equal unit totals make the top-ten selection unstable. Add the product key as the final ordering term.
- request: Show the ten products selling most units in `:year`, with their revenue, breaking unit-total ties by product id.
- sql:

    ```sql
    SELECT p.PROD_ID, p.PROD_NAME,
           SUM(s.QUANTITY_SOLD) AS UNITS,
           SUM(s.AMOUNT_SOLD) AS REVENUE
    FROM SALES s
             JOIN PRODUCTS p ON p.PROD_ID = s.PROD_ID
             JOIN TIMES t ON t.TIME_ID = s.TIME_ID
    WHERE t.CALENDAR_YEAR = :year
    GROUP BY p.PROD_ID, p.PROD_NAME
    ORDER BY UNITS DESC, p.PROD_ID
    FETCH FIRST 10 ROWS ONLY
    ```

### fix SH_SCHEMA_A_11

- section: SCHEMA   tier: Advanced
- title: Every country's regional revenue share
- why: The current inner joins omit countries without sales despite requesting every country. Preserve those countries and handle a zero regional total.
- request: Show every country's revenue in `:year` and its percentage of regional revenue, including countries without sales at zero; show NULL shares when regional revenue is zero.
- sql:

    ```sql
    WITH COUNTRY_REVENUE AS (
        SELECT cu.COUNTRY_ID, SUM(s.AMOUNT_SOLD) AS REVENUE
        FROM SALES s
                 JOIN CUSTOMERS cu ON cu.CUST_ID = s.CUST_ID
                 JOIN TIMES t ON t.TIME_ID = s.TIME_ID
        WHERE t.CALENDAR_YEAR = :year
        GROUP BY cu.COUNTRY_ID
    ),
    SHARES AS (
        SELECT co.COUNTRY_REGION, co.COUNTRY_REGION_ID,
               co.COUNTRY_ID, co.COUNTRY_NAME,
               COALESCE(r.REVENUE, 0) AS REVENUE,
               100 * COALESCE(r.REVENUE, 0)
                   / NULLIF(SUM(COALESCE(r.REVENUE, 0)) OVER (
                       PARTITION BY co.COUNTRY_REGION_ID), 0) AS SHARE_PCT
        FROM COUNTRIES co
                 LEFT JOIN COUNTRY_REVENUE r ON r.COUNTRY_ID = co.COUNTRY_ID
    )
    SELECT COUNTRY_REGION, COUNTRY_NAME, REVENUE,
           ROUND(SHARE_PCT, 2) AS SHARE_PCT
    FROM SHARES
    ORDER BY COUNTRY_REGION, COUNTRY_REGION_ID,
             SHARES.SHARE_PCT DESC NULLS LAST, COUNTRY_ID
    ```

### fix SH_CUSTOMERS_B_04

- section: CUSTOMERS   tier: Basic
- title: Income bands and known credit limits
- why: Oracle's descending order puts NULL credit limits first, ahead of the highest known limits. Specify their placement and resolve equal limits by customer id.
- request: List customers of `:city` by income band, unknown bands last, with highest known credit limits first within each band and unknown limits last.
- sql:

    ```sql
    SELECT CUST_ID, CUST_LAST_NAME, CUST_INCOME_LEVEL, CUST_CREDIT_LIMIT
    FROM CUSTOMERS
    WHERE CUST_CITY = :city
    ORDER BY CUST_INCOME_LEVEL ASC NULLS LAST,
             CUST_CREDIT_LIMIT DESC NULLS LAST, CUST_ID
    ```

### add SH_SCHEMA_A_12

- section: SCHEMA   tier: Advanced
- title: Check the assumed composite keys
- why: The DDL enforces neither the five-column sales key nor the four-column costs key assumed by the exercises and mappings. This check guards those assumptions, including against cost joins multiplying revenue.
- request: Before trusting the reports, list duplicate sales-key and cost-key combinations; a clean result should contain no rows.
- sql:

    ```sql
    SELECT 'SALES' AS SOURCE_TABLE,
           PROD_ID, TIME_ID, CHANNEL_ID, PROMO_ID, CUST_ID,
           COUNT(*) AS RECORDS
    FROM SALES
    GROUP BY PROD_ID, TIME_ID, CHANNEL_ID, PROMO_ID, CUST_ID
    HAVING COUNT(*) > 1
    UNION ALL
    SELECT 'COSTS' AS SOURCE_TABLE,
           PROD_ID, TIME_ID, CHANNEL_ID, PROMO_ID, NULL AS CUST_ID,
           COUNT(*) AS RECORDS
    FROM COSTS
    GROUP BY PROD_ID, TIME_ID, CHANNEL_ID, PROMO_ID
    HAVING COUNT(*) > 1
    ORDER BY SOURCE_TABLE, PROD_ID, TIME_ID, CHANNEL_ID, PROMO_ID, CUST_ID
    ```

### add SH_SUPPLEMENTARY_DEMOGRAPHICS_I_02

- section: SUPPLEMENTARY_DEMOGRAPHICS   tier: Intermediate
- title: Validate affinity-card indicators
- why: Existing sums and averages assume every indicator is zero or one, but the nullable `NUMBER(10)` column has no such constraint. Guard that fact once instead of rewriting each report.
- request: Count records whose affinity-card indicator is missing or is neither zero nor one; both counts should be zero before calculating take-up.
- sql:

    ```sql
    SELECT COUNT(CASE WHEN AFFINITY_CARD IS NULL THEN 1 END) AS MISSING_FLAGS,
           COUNT(CASE WHEN AFFINITY_CARD NOT IN (0, 1) THEN 1 END) AS INVALID_FLAGS
    FROM SUPPLEMENTARY_DEMOGRAPHICS
    ```

### add SH_PRODUCTS_I_02

- section: PRODUCTS   tier: Intermediate
- title: Supplier coverage of the catalogue
- why: `SUPPLIER_ID` is currently unused and supports a useful purchasing question without inventing a supplier table.
- request: For each supplier id, show its product count, number of categories supplied, and lowest and highest list prices, largest catalogue first.
- sql:

    ```sql
    SELECT SUPPLIER_ID,
           COUNT(*) AS PRODUCTS,
           COUNT(DISTINCT PROD_CATEGORY_ID) AS CATEGORIES,
           MIN(PROD_LIST_PRICE) AS LOWEST_PRICE,
           MAX(PROD_LIST_PRICE) AS HIGHEST_PRICE
    FROM PRODUCTS
    GROUP BY SUPPLIER_ID
    ORDER BY PRODUCTS DESC, SUPPLIER_ID
    ```

### add SH_CUSTOMERS_B_05

- section: CUSTOMERS   tier: Basic
- title: Customer records effective at an instant
- why: The nullable effective dates are not covered. An explicit interval rule makes this useful without assuming undocumented meanings for `CUST_VALID`.
- request: Show customer records effective at `:asOf`, treating NULL bounds as open-ended and each interval as including its start and excluding its end.
- sql:

    ```sql
    SELECT CUST_ID, CUST_FIRST_NAME, CUST_LAST_NAME,
           CUST_SRC_ID, CUST_EFF_FROM, CUST_EFF_TO
    FROM CUSTOMERS
    WHERE (CUST_EFF_FROM IS NULL OR CUST_EFF_FROM <= :asOf)
      AND (CUST_EFF_TO IS NULL OR :asOf < CUST_EFF_TO)
    ORDER BY CUST_LAST_NAME, CUST_FIRST_NAME, CUST_ID
    ```