### fix AW_PURCHASING_I_02
- section: PURCHASING   tier: Intermediate
- title: The vendors with the highest rejection shares
- why: Received quantity can be zero, making the division fail. Exclude vendors with no receipts, protect the denominator, and break ties by vendor id.
- request: Show the five vendors with the highest rejected share of received quantity, excluding vendors with no receipts; break ties by vendor id.
- sql:

    ```sql
    SELECT TOP (5) v.Name,
                   SUM(d.ReceivedQty) AS ReceivedQty,
                   SUM(d.RejectedQty) AS RejectedQty,
                   CAST(SUM(d.RejectedQty) * 100.0
                       / NULLIF(SUM(d.ReceivedQty), 0) AS decimal(19, 2)) AS RejectedPercent
    FROM Purchasing.PurchaseOrderDetail d
             JOIN Purchasing.PurchaseOrderHeader h ON h.PurchaseOrderID = d.PurchaseOrderID
             JOIN Purchasing.Vendor v ON v.BusinessEntityID = h.VendorID
    GROUP BY v.BusinessEntityID, v.Name
    HAVING SUM(d.ReceivedQty) > 0
    ORDER BY SUM(d.RejectedQty) / NULLIF(SUM(d.ReceivedQty), 0) DESC, v.BusinessEntityID
    ;
    ```

### fix AW_PRODUCTION_I_01
- section: PRODUCTION   tier: Intermediate
- title: Products below half their safety stock
- why: Starting from inventory omits products with no inventory rows, although their total stock is zero.
- request: Show products whose stock across all locations is less than half their safety stock level, treating missing inventory as zero; show the lowest stock first, then product id.
- sql:

    ```sql
    SELECT p.ProductID, p.Name, p.SafetyStockLevel,
           COALESCE(SUM(i.Quantity), 0) AS Quantity
    FROM Production.Product p
             LEFT JOIN Production.ProductInventory i ON i.ProductID = p.ProductID
    GROUP BY p.ProductID, p.Name, p.SafetyStockLevel
    HAVING COALESCE(SUM(i.Quantity), 0) * 2 < p.SafetyStockLevel
    ORDER BY Quantity, p.ProductID
    ;
    ```

### fix AW_PRODUCTION_B_01
- section: PRODUCTION   tier: Basic
- title: Products on sale in each category
- why: A null sell-end date alone does not establish that selling has started, and it excludes products whose selling period ends in the future. Preserve categories with no qualifying products.
- request: Show every category's number of products on sale now and their lowest and highest list prices, treating the selling endpoints as inclusive; order by category name.
- sql:

    ```sql
    DECLARE @asOf datetime = GETDATE();
    SELECT c.Name AS Category, COUNT(p.ProductID) AS Products,
           MIN(p.ListPrice) AS MinListPrice, MAX(p.ListPrice) AS MaxListPrice
    FROM Production.ProductCategory c
             LEFT JOIN Production.ProductSubcategory s ON s.ProductCategoryID = c.ProductCategoryID
             LEFT JOIN Production.Product p ON p.ProductSubcategoryID = s.ProductSubcategoryID
                 AND p.SellStartDate <= @asOf
                 AND (p.SellEndDate IS NULL OR p.SellEndDate >= @asOf)
    GROUP BY c.ProductCategoryID, c.Name
    ORDER BY c.Name
    ;
    ```

### fix AW_PRODUCTION_A_01
- section: PRODUCTION   tier: Advanced
- title: The current parts of an assembly
- why: Both recursive branches ignore start dates and exclude still-effective rows with future end dates. Add fixture checks for BOM cycles and overlapping effective rows for the same assembly/component pair.
- request: Show every part of a product from its bill of materials effective now, down to raw materials, with the quantity its immediate assembly takes and its depth; treat effective endpoints as inclusive.
- sql:

    ```sql
    DECLARE @productId int = 818;
    DECLARE @asOf datetime = GETDATE();
    WITH Parts (AssemblyID, ComponentID, PerAssemblyQty, BomLevel) AS (
        SELECT b.ProductAssemblyID, b.ComponentID, b.PerAssemblyQty, 1
        FROM Production.BillOfMaterials b
        WHERE b.ProductAssemblyID = @productId
          AND b.StartDate <= @asOf
          AND (b.EndDate IS NULL OR b.EndDate >= @asOf)
        UNION ALL
        SELECT b.ProductAssemblyID, b.ComponentID, b.PerAssemblyQty, p.BomLevel + 1
        FROM Production.BillOfMaterials b
                 JOIN Parts p ON p.ComponentID = b.ProductAssemblyID
        WHERE b.StartDate <= @asOf
          AND (b.EndDate IS NULL OR b.EndDate >= @asOf)
    )
    SELECT p.AssemblyID, p.ComponentID, c.Name, p.PerAssemblyQty, p.BomLevel
    FROM Parts p
             JOIN Production.Product c ON c.ProductID = p.ComponentID
    ORDER BY p.BomLevel, p.AssemblyID, p.ComponentID
    ;
    ```

### fix AW_PERSON_A_01
- section: PERSON   tier: Advanced
- title: Answered yearly income bands
- why: Demographics is nullable and YearlyIncome is optional in its XML schema. Missing answers must not count as an answered band.
- request: Show how many individual customers answered each yearly income band in their Demographics survey, excluding missing answers; order by band.
- sql:

    ```sql
    WITH XMLNAMESPACES (DEFAULT 'http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/IndividualSurvey')
    SELECT i.YearlyIncome, COUNT(*) AS Persons
    FROM (SELECT p.Demographics.value('(/IndividualSurvey/YearlyIncome)[1]', 'nvarchar(30)') AS YearlyIncome
          FROM Person.Person p
          WHERE p.PersonType = 'IN'
            AND p.Demographics.exist('/IndividualSurvey/YearlyIncome') = 1) AS i
    GROUP BY i.YearlyIncome
    ORDER BY i.YearlyIncome
    ;
    ```

### fix AW_SALES_A_01
- section: SALES   tier: Advanced
- title: Sales by fiscal year
- why: The request leaves the four hardcoded fiscal years unspecified, and the query omits sales persons without orders and leaves ties unordered. Retain the module's name-based identification, guarded by a fixture check that sales persons have distinct last names.
- request: Show every sales person's order subtotals for fiscal years ending in 2022, 2023, 2024 and 2025, one column per year, with zero for no sales; fiscal years start July 1, and results sort by 2025 sales descending, then last name.
- sql:

    ```sql
    SELECT pvt.LastName,
           COALESCE(pvt.[2022], 0) AS [2022],
           COALESCE(pvt.[2023], 0) AS [2023],
           COALESCE(pvt.[2024], 0) AS [2024],
           COALESCE(pvt.[2025], 0) AS [2025]
    FROM (SELECT p.LastName, h.SubTotal,
                 YEAR(DATEADD(MONTH, 6, h.OrderDate)) AS FiscalYear
          FROM Sales.SalesPerson sp
                   JOIN Person.Person p ON p.BusinessEntityID = sp.BusinessEntityID
                   LEFT JOIN Sales.SalesOrderHeader h ON h.SalesPersonID = sp.BusinessEntityID
                       AND h.OrderDate >= '20210701'
                       AND h.OrderDate < '20250701') AS s
             PIVOT (SUM(s.SubTotal) FOR s.FiscalYear IN ([2022], [2023], [2024], [2025])) AS pvt
    ORDER BY COALESCE(pvt.[2025], 0) DESC, pvt.LastName
    ;
    ```

### fix AW_HUMANRESOURCES_B_01
- section: HUMANRESOURCES   tier: Basic
- title: Current headcount in every department
- why: The inner join omits empty departments. Guard the existing open-assignment convention with a fixture check that grouping history rows with null EndDate by BusinessEntityID never yields COUNT(*) greater than one.
- request: Show every department's current headcount, including zero, using assignments with no end date; show the largest first, then department name.
- sql:

    ```sql
    SELECT d.Name, d.GroupName, COUNT(h.BusinessEntityID) AS Employees
    FROM HumanResources.Department d
             LEFT JOIN HumanResources.EmployeeDepartmentHistory h ON h.DepartmentID = d.DepartmentID
                 AND h.EndDate IS NULL
    GROUP BY d.DepartmentID, d.Name, d.GroupName
    ORDER BY Employees DESC, d.Name
    ;
    ```

### fix AW_PERSON_I_01
- section: PERSON   tier: Intermediate
- title: The five countries with the most addresses
- why: Equal address counts make both the selected five countries and their ordering unstable.
- request: Show the five countries with the most addresses, breaking ties by country code.
- sql:

    ```sql
    SELECT TOP (5) c.CountryRegionCode, c.Name, COUNT(*) AS Addresses
    FROM Person.Address a
             JOIN Person.StateProvince s ON s.StateProvinceID = a.StateProvinceID
             JOIN Person.CountryRegion c ON c.CountryRegionCode = s.CountryRegionCode
    GROUP BY c.CountryRegionCode, c.Name
    ORDER BY Addresses DESC, c.CountryRegionCode
    ;
    ```

### fix AW_PRODUCTION_I_02
- section: PRODUCTION   tier: Intermediate
- title: The five largest scrap totals
- why: A scrap reason does not establish that a work order stopped, and equal scrap totals make TOP unstable.
- request: Show the five scrap reasons with the most scrapped quantity and the number of work orders recording each reason; break ties by scrap reason id.
- sql:

    ```sql
    SELECT TOP (5) r.Name, COUNT(*) AS WorkOrders, SUM(w.ScrappedQty) AS ScrappedQty
    FROM Production.WorkOrder w
             JOIN Production.ScrapReason r ON r.ScrapReasonID = w.ScrapReasonID
    GROUP BY r.ScrapReasonID, r.Name
    ORDER BY ScrappedQty DESC, r.ScrapReasonID
    ;
    ```

### fix AW_PURCHASING_I_01
- section: PURCHASING   tier: Intermediate
- title: The five largest vendor order totals
- why: TotalDue measures order amounts rather than payments, so “spent” needs clarification. Equal totals also need a tie-breaker.
- request: Show the five vendors with the largest total purchase-order amounts, including tax and freight, and their order counts; include all order statuses and break ties by vendor id.
- sql:

    ```sql
    SELECT TOP (5) v.AccountNumber, v.Name, COUNT(*) AS Orders, SUM(h.TotalDue) AS TotalDue
    FROM Purchasing.PurchaseOrderHeader h
             JOIN Purchasing.Vendor v ON v.BusinessEntityID = h.VendorID
    GROUP BY v.BusinessEntityID, v.AccountNumber, v.Name
    ORDER BY TotalDue DESC, v.BusinessEntityID
    ;
    ```

### fix AW_SALES_I_02
- section: SALES   tier: Intermediate
- title: The five products with the most sales revenue
- why: Equal revenue totals make the selected five products unstable.
- request: Show the five products with the largest sales-line totals and their quantities sold, breaking ties by product id.
- sql:

    ```sql
    SELECT TOP (5) p.ProductNumber, p.Name, SUM(d.OrderQty) AS OrderQty, SUM(d.LineTotal) AS LineTotal
    FROM Sales.SalesOrderDetail d
             JOIN Production.Product p ON p.ProductID = d.ProductID
    GROUP BY p.ProductID, p.ProductNumber, p.Name
    ORDER BY LineTotal DESC, p.ProductID
    ;
    ```

### fix AW_SALES_I_04
- section: SALES   tier: Intermediate
- title: The five highest recorded year-to-date sales
- why: Equal SalesYTD values make TOP unstable; “this year” should identify the stored year-to-date measure rather than imply a calculation for the execution year.
- request: Show the five sales persons with the highest recorded SalesYTD, with their names and territories, breaking ties by sales person id.
- sql:

    ```sql
    SELECT TOP (5) p.FirstName, p.LastName, t.Name AS Territory, sp.SalesYTD
    FROM Sales.SalesPerson sp
             JOIN HumanResources.Employee e ON e.BusinessEntityID = sp.BusinessEntityID
             JOIN Person.Person p ON p.BusinessEntityID = e.BusinessEntityID
             LEFT JOIN Sales.SalesTerritory t ON t.TerritoryID = sp.TerritoryID
    ORDER BY sp.SalesYTD DESC, sp.BusinessEntityID
    ;
    ```

### add AW_PURCHASING_A_01
- section: PURCHASING   tier: Advanced
- title: Monthly vendor totals and running totals
- why: Purchasing lacks an Advanced exercise. Monthly aggregation followed by a running total adds a useful date analysis and window frame.
- request: For 2025, show each vendor's purchase-order total in every month with orders and its running total through that month, including all order statuses.
- sql:

    ```sql
    DECLARE @year int = 2025;
    WITH Monthly AS (
        SELECT h.VendorID, MONTH(h.OrderDate) AS OrderMonth,
               SUM(h.TotalDue) AS TotalDue
        FROM Purchasing.PurchaseOrderHeader h
        WHERE h.OrderDate >= DATEFROMPARTS(@year, 1, 1)
          AND h.OrderDate < DATEFROMPARTS(@year + 1, 1, 1)
        GROUP BY h.VendorID, MONTH(h.OrderDate)
    )
    SELECT v.AccountNumber, v.Name, m.OrderMonth, m.TotalDue,
           SUM(m.TotalDue) OVER (
               PARTITION BY m.VendorID
               ORDER BY m.OrderMonth
               ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
           ) AS RunningTotalDue
    FROM Monthly m
             JOIN Purchasing.Vendor v ON v.BusinessEntityID = m.VendorID
    ORDER BY v.AccountNumber, m.OrderMonth
    ;
    ```

### add AW_PERSON_B_02
- section: PERSON   tier: Basic
- title: An organization's contacts and their roles
- why: No exercise covers BusinessEntityContact or its contact-role join; these answer a practical directory question.
- request: Show the contact persons and their roles for a business entity, ordered by last name, first name, person id and role id.
- sql:

    ```sql
    DECLARE @businessEntityId int = 1492;
    SELECT p.BusinessEntityID AS PersonID, p.FirstName, p.LastName,
           t.Name AS ContactType
    FROM Person.BusinessEntityContact c
             JOIN Person.Person p ON p.BusinessEntityID = c.PersonID
             JOIN Person.ContactType t ON t.ContactTypeID = c.ContactTypeID
    WHERE c.BusinessEntityID = @businessEntityId
    ORDER BY p.LastName, p.FirstName, p.BusinessEntityID, t.ContactTypeID
    ;
    ```

### add AW_HUMANRESOURCES_I_03
- section: HUMANRESOURCES   tier: Intermediate
- title: Shift lengths across midnight
- why: Shift and its time columns are uncovered. Calculating duration introduces useful time arithmetic with explicit overnight handling.
- request: Show each shift's start, end and duration in minutes, treating an end time at or before the start as occurring the following day; order by shift id.
- sql:

    ```sql
    SELECT s.ShiftID, s.Name, s.StartTime, s.EndTime,
           DATEDIFF(MINUTE, s.StartTime, s.EndTime)
               + CASE WHEN s.EndTime <= s.StartTime THEN 1440 ELSE 0 END AS DurationMinutes
    FROM HumanResources.Shift s
    ORDER BY s.ShiftID
    ;
    ```