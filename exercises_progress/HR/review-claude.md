# HR — Claude's review

### fix HR_EMPLOYEES_A_02
- section: EMPLOYEES   tier: Advanced
- title: Three best-paid per department
- why: `SALARY` is nullable and Oracle sorts nulls first in a `DESC` order, so an employee with no salary would get `DENSE_RANK` 1 and be reported as the best-paid. Rows tied on salary also come back in no fixed order.
- request: Ahead of the bonus round, each department head wants their three highest salaries and who earns them.
- sql:
    SELECT DEPARTMENT_ID, EMPLOYEE_ID, LAST_NAME, SALARY, RNK
    FROM (SELECT e.*, DENSE_RANK() OVER (PARTITION BY DEPARTMENT_ID ORDER BY SALARY DESC) AS RNK
          FROM EMPLOYEES e
          WHERE DEPARTMENT_ID IS NOT NULL
            AND SALARY IS NOT NULL)
    WHERE RNK <= 3
    ORDER BY DEPARTMENT_ID ASC, RNK ASC, EMPLOYEE_ID ASC

### fix HR_EMP_DETAILS_VIEW_A_01
- section: EMP_DETAILS_VIEW   tier: Advanced
- title: Best-paid in each region
- why: This has the same null-first problem. The view passes `EMPLOYEES.SALARY` through as nullable, so a null salary would rank 1 in its region. `LAST_NAME` as the last sort key does not break ties between people with the same name.
- request: Each regional director is told who the best-paid people in their region are — the three highest salaries, ties included.
- sql:
    SELECT REGION_NAME, EMPLOYEE_ID, LAST_NAME, JOB_TITLE, SALARY, RNK
    FROM (SELECT v.*, DENSE_RANK() OVER (PARTITION BY REGION_NAME ORDER BY SALARY DESC) AS RNK
          FROM EMP_DETAILS_VIEW v
          WHERE SALARY IS NOT NULL)
    WHERE RNK <= 3
    ORDER BY REGION_NAME ASC, RNK ASC, LAST_NAME ASC, EMPLOYEE_ID ASC

### fix HR_EMPLOYEES_A_01
- section: EMPLOYEES   tier: Advanced
- title: Top earner of each department
- why: The two SQL answers return different rows. The correlated form drops the employee without a department, while the `RANK` form keeps them as a partition of their own and would rank a null salary first. Make them agree by excluding null departments and null salaries, and add a tiebreak, because ties are reported.
- request: Each department head is told who their best-paid employee is; ties are all reported.
- sql:
    SELECT DEPARTMENT_ID, EMPLOYEE_ID, LAST_NAME, SALARY
    FROM (SELECT e.*, RANK() OVER (PARTITION BY DEPARTMENT_ID ORDER BY SALARY DESC) AS RNK
          FROM EMPLOYEES e
          WHERE DEPARTMENT_ID IS NOT NULL
            AND SALARY IS NOT NULL)
    WHERE RNK = 1
    ORDER BY DEPARTMENT_ID ASC, EMPLOYEE_ID ASC

### fix HR_JOB_HISTORY_B_02
- section: JOB_HISTORY   tier: Basic
- title: Positions closed in a period
- why: The schema's own trigger `update_job_history` writes `END_DATE` as `SYSDATE`, which carries a time of day. `BETWEEN :fromDate AND :toDate` therefore misses every position closed after midnight on the last day, even though the request says "both inclusive". A half-open range is correct for any `DATE`.
- request: For an audit, HR wants every earlier position that ended within a given period (from and to dates, both inclusive).
- sql:
    SELECT EMPLOYEE_ID, START_DATE, END_DATE, JOB_ID, DEPARTMENT_ID
    FROM JOB_HISTORY
    WHERE END_DATE >= :fromDate
      AND END_DATE < :toDate + 1
    ORDER BY END_DATE ASC, EMPLOYEE_ID ASC

### fix HR_JOB_HISTORY_I_03
- section: JOB_HISTORY   tier: Intermediate
- title: How long earlier positions lasted
- why: The trigger sets `END_DATE` to `SYSDATE`, so it carries a time of day, and `END_DATE - START_DATE + 1` then becomes a fractional number of days. "In days" needs whole calendar days, which `TRUNC` gives regardless of how a row was written.
- request: Workforce planning wants to know how long people stay in a job before they move on: per job, the number of earlier positions and the shortest, average and longest of them in days, longest average first.
- sql:
    SELECT JOB_ID, COUNT(*) AS POSITIONS,
           MIN(TRUNC(END_DATE) - TRUNC(START_DATE) + 1)        AS SHORTEST_DAYS,
           ROUND(AVG(TRUNC(END_DATE) - TRUNC(START_DATE) + 1)) AS AVERAGE_DAYS,
           MAX(TRUNC(END_DATE) - TRUNC(START_DATE) + 1)        AS LONGEST_DAYS
    FROM JOB_HISTORY
    GROUP BY JOB_ID
    ORDER BY AVERAGE_DAYS DESC, JOB_ID ASC

### fix HR_EMPLOYEES_I_03
- section: EMPLOYEES   tier: Intermediate
- title: Headcount per pay grade
- why: `SALARY` is nullable, and the `ELSE` branch counts an employee with no salary as 'High'. There is also no `ORDER BY`, so the grades come back in any order.
- request: HR reports headcount in three pay grades: under 5,000, 5,000 up to 10,000, and 10,000 or more.
- sql:
    SELECT CASE
               WHEN SALARY < 5000 THEN 'Low'
               WHEN SALARY < 10000 THEN 'Medium'
               ELSE 'High'
               END  AS GRADE,
           COUNT(*) AS HEADCOUNT
    FROM EMPLOYEES
    WHERE SALARY IS NOT NULL
    GROUP BY CASE
                 WHEN SALARY < 5000 THEN 'Low'
                 WHEN SALARY < 10000 THEN 'Medium'
                 ELSE 'High'
                 END
    ORDER BY MIN(SALARY) ASC

### fix HR_SCHEMA_A_02
- section: SCHEMA   tier: Advanced
- title: Career timeline of one employee
- why: `ORDER BY 1` alone is ambiguous here. The trigger writes the first history row with `START_DATE = HIRE_DATE`, and the current-position row also starts on `HIRE_DATE`, so the current job can sort before an earlier one. The open-ended current row (null `END_DATE`) should sort last on a tie.
- request: An employee asks HR for their record: every position they have held, the current one included, in date order.
- sql:
    SELECT h.START_DATE, h.END_DATE, h.JOB_ID, j.JOB_TITLE, h.DEPARTMENT_ID
    FROM JOB_HISTORY h
             JOIN JOBS j ON j.JOB_ID = h.JOB_ID
    WHERE h.EMPLOYEE_ID = :employeeId
    UNION ALL
    SELECT e.HIRE_DATE, NULL, e.JOB_ID, j.JOB_TITLE, e.DEPARTMENT_ID
    FROM EMPLOYEES e
             JOIN JOBS j ON j.JOB_ID = e.JOB_ID
    WHERE e.EMPLOYEE_ID = :employeeId
    ORDER BY 1 ASC, 2 ASC NULLS LAST

### fix HR_SCHEMA_A_05
- section: SCHEMA   tier: Advanced
- title: Department roster in one round trip
- why: `SELECT d.*, e.*` returns `DEPARTMENT_ID` and `MANAGER_ID` twice under the same names, which is ambiguous to any reader of the result set. Ties on `LAST_NAME` within a department are also unordered.
- request: The intranet's site page shows, for one location, each department and its staff. Loading departments and then each department's employees one by one is the N+1 problem; the page needs a single query.
- sql:
    SELECT d.DEPARTMENT_ID, d.DEPARTMENT_NAME, e.EMPLOYEE_ID, e.FIRST_NAME, e.LAST_NAME, e.JOB_ID
    FROM DEPARTMENTS d
             LEFT JOIN EMPLOYEES e ON e.DEPARTMENT_ID = d.DEPARTMENT_ID
    WHERE d.LOCATION_ID = :locationId
    ORDER BY d.DEPARTMENT_ID ASC, e.LAST_NAME ASC, e.EMPLOYEE_ID ASC

### fix HR_EMPLOYEES_B_06
- section: EMPLOYEES   tier: Basic
- title: Hired in a period
- why: `HIRE_DATE` is a `DATE`, and `BETWEEN` misses a hire on `:toDate` that carries a time of day; the note admits this rather than fixing it. Sorting by `HIRE_DATE` alone is also unstable for people hired on the same day.
- request: HR is preparing the probation review for everyone hired in a given period (from and to dates, both inclusive).
- sql:
    SELECT *
    FROM EMPLOYEES
    WHERE HIRE_DATE >= :fromDate
      AND HIRE_DATE < :toDate + 1
    ORDER BY HIRE_DATE ASC, EMPLOYEE_ID ASC

### fix HR_EMPLOYEES_I_01
- section: EMPLOYEES   tier: Intermediate
- title: Above the company average
- why: Salaries repeat in the data (two vice presidents earn the same, for one), so `ORDER BY SALARY DESC` alone gives an unstable order and a test of the output could flake. Add the key as a tiebreak.
- request: The board asks who earns more than the company-wide average salary.
- sql:
    SELECT EMPLOYEE_ID, FIRST_NAME, LAST_NAME, SALARY
    FROM EMPLOYEES
    WHERE SALARY > (SELECT AVG(SALARY) FROM EMPLOYEES)
    ORDER BY SALARY DESC, EMPLOYEE_ID ASC

### fix HR_SCHEMA_A_04
- section: SCHEMA   tier: Advanced
- title: Offices with no department
- why: The query has no `ORDER BY`. `MINUS` happens to sort on many Oracle plans, but nothing guarantees it, so the result order is undefined.
- request: Facilities is reviewing the property list: which locations host no department at all?
- sql:
    SELECT LOCATION_ID
    FROM LOCATIONS
    MINUS
    SELECT LOCATION_ID
    FROM DEPARTMENTS
    ORDER BY 1 ASC

### add HR_EMPLOYEES_B_09
- section: EMPLOYEES   tier: Basic
- title: The newest hires
- why: No exercise takes only the top n rows, so Oracle's row-limiting clause (`FETCH FIRST n ROWS ONLY`, the optimal form here, with no `OFFSET` for the first page) is never shown. The JPQL counterpart would be `setMaxResults(n)`.
- request: The onboarding team wants the n most recently hired employees, newest first.
- sql:
    SELECT EMPLOYEE_ID, FIRST_NAME, LAST_NAME, JOB_ID, HIRE_DATE
    FROM EMPLOYEES
    ORDER BY HIRE_DATE DESC, EMPLOYEE_ID DESC
    FETCH FIRST :n ROWS ONLY

### add HR_SCHEMA_I_11
- section: SCHEMA   tier: Intermediate
- title: Managers outside their department
- why: The DDL has two independent manager links: `DEPARTMENTS.MANAGER_ID` and the manager's own `EMPLOYEES.DEPARTMENT_ID`. Nothing ties them together, and no exercise checks whether a department's manager actually belongs to it, including a manager with no department.
- request: An auditor wants every department whose manager on record is not a member of that department, with the department the manager does belong to.
- sql:
    SELECT d.DEPARTMENT_ID, d.DEPARTMENT_NAME, m.EMPLOYEE_ID, m.LAST_NAME,
           m.DEPARTMENT_ID AS MANAGER_DEPARTMENT_ID
    FROM DEPARTMENTS d
             JOIN EMPLOYEES m ON m.EMPLOYEE_ID = d.MANAGER_ID
    WHERE m.DEPARTMENT_ID IS NULL
       OR m.DEPARTMENT_ID <> d.DEPARTMENT_ID
    ORDER BY d.DEPARTMENT_ID ASC

### add HR_SCHEMA_A_07
- section: SCHEMA   tier: Advanced
- title: Each department's staff on one line
- why: String aggregation (`LISTAGG ... WITHIN GROUP`) is missing from the set. Users of this data commonly ask for a department's staff on one line for a report.
- request: The intranet's department index shows each department with its headcount and its staff's last names on one line, alphabetically.
- sql:
    SELECT d.DEPARTMENT_ID, d.DEPARTMENT_NAME, COUNT(*) AS HEADCOUNT,
           LISTAGG(e.LAST_NAME, ', ') WITHIN GROUP (ORDER BY e.LAST_NAME, e.EMPLOYEE_ID) AS STAFF
    FROM DEPARTMENTS d
             JOIN EMPLOYEES e ON e.DEPARTMENT_ID = d.DEPARTMENT_ID
    GROUP BY d.DEPARTMENT_ID, d.DEPARTMENT_NAME
    ORDER BY d.DEPARTMENT_ID ASC

### add HR_EMP_DETAILS_VIEW_A_02
- section: EMP_DETAILS_VIEW   tier: Advanced
- title: Payroll with subtotals
- why: Finance's per-country payroll (`_I_01`) has no subtotals, and `GROUP BY ROLLUP` / `GROUPING` appear nowhere in the set. The view's region-to-country hierarchy is the natural place for them.
- request: Finance wants the monthly salary cost per country, with a subtotal for each region and a grand total.
- sql:
    SELECT REGION_NAME, COUNTRY_NAME, COUNT(*) AS HEADCOUNT, SUM(SALARY) AS MONTHLY_COST,
           GROUPING_ID(REGION_NAME, COUNTRY_NAME) AS SUBTOTAL_LEVEL
    FROM EMP_DETAILS_VIEW
    GROUP BY ROLLUP (REGION_NAME, COUNTRY_NAME)
    ORDER BY GROUPING(REGION_NAME) ASC, REGION_NAME ASC, GROUPING(COUNTRY_NAME) ASC, COUNTRY_NAME ASC
