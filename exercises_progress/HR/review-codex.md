### fix HR_EMPLOYEES_A_01

- section: EMPLOYEES   tier: Advanced
- title: Top earner of each department
- why: The analytic solution includes unassigned employees, unlike the correlated solution. Exclude that partition and order tied earners consistently.
- request: Show each department’s highest-paid employees, including everyone tied for its highest salary.
- sql:

    ```sql
    SELECT DEPARTMENT_ID, EMPLOYEE_ID, LAST_NAME, SALARY
    FROM (SELECT e.*, RANK() OVER (PARTITION BY DEPARTMENT_ID ORDER BY SALARY DESC) AS RNK
          FROM EMPLOYEES e
          WHERE DEPARTMENT_ID IS NOT NULL)
    WHERE RNK = 1
    ORDER BY DEPARTMENT_ID ASC, EMPLOYEE_ID ASC
    ```

### fix HR_EMPLOYEES_A_02

- section: EMPLOYEES   tier: Advanced
- title: Three highest salary levels per department
- why: Clarify that the request concerns three distinct salary amounts, potentially held by more than three people. The existing ordering leaves employees tied at the same rank unordered.
- request: For each department, show everyone earning one of its three highest distinct salaries, including ties.
- sql:

    ```sql
    SELECT DEPARTMENT_ID, EMPLOYEE_ID, LAST_NAME, SALARY, RNK
    FROM (SELECT e.*, DENSE_RANK() OVER (PARTITION BY DEPARTMENT_ID ORDER BY SALARY DESC) AS RNK
          FROM EMPLOYEES e
          WHERE DEPARTMENT_ID IS NOT NULL)
    WHERE RNK <= 3
    ORDER BY DEPARTMENT_ID ASC, RNK ASC, EMPLOYEE_ID ASC
    ```

### fix HR_EMPLOYEES_B_06

- section: EMPLOYEES   tier: Basic
- title: Hired in a period
- why: Oracle `DATE` includes a time component; the inclusive end date otherwise excludes hires later that day. Employee id resolves ties in hire date.
- request: List employees hired between the supplied calendar dates, both dates included, earliest hires first.
- sql:

    ```sql
    SELECT *
    FROM EMPLOYEES
    WHERE HIRE_DATE >= TRUNC(:fromDate)
      AND HIRE_DATE < TRUNC(:toDate) + 1
    ORDER BY HIRE_DATE ASC, EMPLOYEE_ID ASC
    ```

### fix HR_JOB_HISTORY_B_02

- section: JOB_HISTORY   tier: Basic
- title: Positions closed in a period
- why: The history trigger writes `SYSDATE`, so end dates can contain times even when the sample dates are midnight. Include the whole final day and use the complete history key to resolve ties.
- request: List earlier positions ending between the supplied calendar dates, both dates included, earliest endings first.
- sql:

    ```sql
    SELECT EMPLOYEE_ID, START_DATE, END_DATE, JOB_ID, DEPARTMENT_ID
    FROM JOB_HISTORY
    WHERE END_DATE >= TRUNC(:fromDate)
      AND END_DATE < TRUNC(:toDate) + 1
    ORDER BY END_DATE ASC, EMPLOYEE_ID ASC, START_DATE ASC
    ```

### fix HR_JOBS_I_02

- section: JOBS   tier: Intermediate
- title: The catalogue at a glance
- why: Averaging the two bounds separately can combine different sets of jobs when bounds are missing. Oracle can directly average each complete band’s midpoint.
- request: Show the number of jobs, the lowest recorded minimum, the highest recorded maximum, and the average midpoint of bands with both bounds recorded.
- sql:

    ```sql
    SELECT COUNT(*) AS JOBS, MIN(MIN_SALARY) AS LOWEST, MAX(MAX_SALARY) AS HIGHEST,
           ROUND(AVG((MIN_SALARY + MAX_SALARY) / 2), 2) AS AVERAGE_MIDPOINT
    FROM JOBS
    ```

### fix HR_SCHEMA_I_03

- section: SCHEMA   tier: Intermediate
- title: Departments above a size
- why: An inner join incorrectly excludes empty departments when the threshold is zero. Count employee keys after an outer join and resolve headcount ties.
- request: List departments with at least the supplied nonnegative number of employees, largest first.
- sql:

    ```sql
    SELECT d.DEPARTMENT_ID, d.DEPARTMENT_NAME, COUNT(e.EMPLOYEE_ID) AS HEADCOUNT
    FROM DEPARTMENTS d
             LEFT JOIN EMPLOYEES e ON e.DEPARTMENT_ID = d.DEPARTMENT_ID
    GROUP BY d.DEPARTMENT_ID, d.DEPARTMENT_NAME
    HAVING COUNT(e.EMPLOYEE_ID) >= :minHeadcount
    ORDER BY HEADCOUNT DESC, d.DEPARTMENT_ID ASC
    ```

### fix HR_SCHEMA_I_06

- section: SCHEMA   tier: Intermediate
- title: Due for a promotion conversation
- why: “Top tenth of the band” and “90% of the maximum” describe different thresholds; retain the explicitly stated maximum-based rule. Order by the unrounded ratio, with employee id resolving ties.
- request: List employees paid at least 90% of their job’s maximum salary, highest proportion first.
- sql:

    ```sql
    SELECT e.EMPLOYEE_ID, e.FIRST_NAME, e.LAST_NAME, e.JOB_ID, e.SALARY, j.MAX_SALARY
    FROM EMPLOYEES e
             JOIN JOBS j ON j.JOB_ID = e.JOB_ID
    WHERE e.SALARY >= j.MAX_SALARY * 0.9
    ORDER BY e.SALARY / NULLIF(j.MAX_SALARY, 0) DESC NULLS LAST, e.EMPLOYEE_ID ASC
    ```

### fix HR_SCHEMA_A_05

- section: SCHEMA   tier: Advanced
- title: Department roster in one round trip
- why: Several employees can share a surname within a department. Add first name and employee id so the roster has a stable order.
- request: For one location, show every department and its staff in one query, including empty departments, with staff ordered by surname and first name.
- sql:

    ```sql
    SELECT d.*, e.*
    FROM DEPARTMENTS d
             LEFT JOIN EMPLOYEES e ON e.DEPARTMENT_ID = d.DEPARTMENT_ID
    WHERE d.LOCATION_ID = :locationId
    ORDER BY d.DEPARTMENT_ID ASC, e.LAST_NAME ASC,
             e.FIRST_NAME ASC NULLS FIRST, e.EMPLOYEE_ID ASC
    ```

### add HR_EMPLOYEES_B_09

- section: EMPLOYEES   tier: Basic
- title: Salaries missing from payroll
- why: `CHECK (salary > 0)` permits null salaries. This check guards the existing exercises’ stated assumption that every employee has a salary, including their rankings and quantified comparisons.
- request: Show employees whose salary has not been recorded so payroll can complete their records.
- sql:

    ```sql
    SELECT EMPLOYEE_ID, FIRST_NAME, LAST_NAME, JOB_ID
    FROM EMPLOYEES
    WHERE SALARY IS NULL
    ORDER BY EMPLOYEE_ID ASC
    ```

### add HR_JOBS_B_04

- section: JOBS   tier: Basic
- title: Salary bands needing repair
- why: The DDL enforces neither complete bands nor positive, correctly ordered bounds. This check guards the assumptions used by the ratio and career-ladder exercises.
- request: Find jobs with a missing salary bound, a nonpositive bound, or a minimum greater than the maximum.
- sql:

    ```sql
    SELECT JOB_ID, JOB_TITLE, MIN_SALARY, MAX_SALARY
    FROM JOBS
    WHERE MIN_SALARY IS NULL
       OR MAX_SALARY IS NULL
       OR MIN_SALARY <= 0
       OR MAX_SALARY <= 0
       OR MIN_SALARY > MAX_SALARY
    ORDER BY JOB_ID ASC
    ```

### add HR_SCHEMA_I_11

- section: SCHEMA   tier: Intermediate
- title: Department managers assigned elsewhere
- why: The department’s manager foreign key and the employee’s department foreign key are independent. No existing exercise checks whether the designated manager belongs to the department they manage.
- request: Show departments whose designated manager is assigned to another department or has no department assignment.
- sql:

    ```sql
    SELECT d.DEPARTMENT_ID, d.DEPARTMENT_NAME,
           m.EMPLOYEE_ID AS MANAGER_ID, m.FIRST_NAME, m.LAST_NAME,
           m.DEPARTMENT_ID AS MANAGER_DEPARTMENT
    FROM DEPARTMENTS d
             JOIN EMPLOYEES m ON m.EMPLOYEE_ID = d.MANAGER_ID
    WHERE m.DEPARTMENT_ID <> d.DEPARTMENT_ID
       OR m.DEPARTMENT_ID IS NULL
    ORDER BY d.DEPARTMENT_ID ASC
    ```

### add HR_SCHEMA_I_12

- section: SCHEMA   tier: Intermediate
- title: Countries without company sites
- why: Existing country and location counts omit countries with no sites. This adds the missing country-to-location anti-join.
- request: Which countries in our catalogue have no company site?
- sql:

    ```sql
    SELECT c.COUNTRY_ID, c.COUNTRY_NAME
    FROM COUNTRIES c
    WHERE NOT EXISTS (SELECT 1
                      FROM LOCATIONS l
                      WHERE l.COUNTRY_ID = c.COUNTRY_ID)
    ORDER BY c.COUNTRY_NAME ASC, c.COUNTRY_ID ASC
    ```

### add HR_EMPLOYEES_I_07

- section: EMPLOYEES   tier: Intermediate
- title: Highest-paid employees for review
- why: No exercise covers a bounded first-page result. Oracle’s `FETCH FIRST` provides it directly without an unnecessary offset, and employee id makes the selection deterministic.
- request: Show the first ten employees for a salary review, ordered by highest salary and then employee id; exclude missing salaries.
- sql:

    ```sql
    SELECT EMPLOYEE_ID, FIRST_NAME, LAST_NAME, SALARY
    FROM EMPLOYEES
    WHERE SALARY IS NOT NULL
    ORDER BY SALARY DESC, EMPLOYEE_ID ASC
    FETCH FIRST 10 ROWS ONLY
    ```

### add HR_SCHEMA_A_07

- section: SCHEMA   tier: Advanced
- title: Recorded career information
- why: Replace the unanswerable timeline with an explicit distinction between recorded history dates and the employee’s hire date. The current assignment’s actual start date is not reliably available.
- request: Show one employee’s recorded earlier positions in date order, followed by their current assignment; show their hire date separately and leave the current assignment’s start date unknown.
- sql:

    ```sql
    SELECT POSITION_TYPE, START_DATE, END_DATE, HIRE_DATE,
           JOB_ID, JOB_TITLE, DEPARTMENT_ID
    FROM (SELECT 'Earlier' AS POSITION_TYPE,
                 h.START_DATE, h.END_DATE, e.HIRE_DATE,
                 h.JOB_ID, j.JOB_TITLE, h.DEPARTMENT_ID,
                 0 AS CURRENT_POSITION
          FROM JOB_HISTORY h
                   JOIN EMPLOYEES e ON e.EMPLOYEE_ID = h.EMPLOYEE_ID
                   JOIN JOBS j ON j.JOB_ID = h.JOB_ID
          WHERE h.EMPLOYEE_ID = :employeeId
          UNION ALL
          SELECT 'Current', CAST(NULL AS DATE), CAST(NULL AS DATE), e.HIRE_DATE,
                 e.JOB_ID, j.JOB_TITLE, e.DEPARTMENT_ID, 1
          FROM EMPLOYEES e
                   JOIN JOBS j ON j.JOB_ID = e.JOB_ID
          WHERE e.EMPLOYEE_ID = :employeeId)
    ORDER BY CURRENT_POSITION ASC, START_DATE ASC
    ```

### remove HR_SCHEMA_A_02

- section: SCHEMA   tier: Advanced
- title: Career timeline of one employee
- why: The exercise itself acknowledges that `HIRE_DATE` remains unchanged after role changes, yet presents it as the current position’s start date. A complete dated career timeline cannot be reconstructed reliably; retire this id and replace it with HR_SCHEMA_A_07.