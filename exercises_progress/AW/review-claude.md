# AW — Claude's review

### fix AW_PRODUCTION_I_01
- section: PRODUCTION   tier: Intermediate
- title: The products whose stock is less than half their safety stock level
- why: The inner join from `ProductInventory` drops every product that has no inventory row at all. Those products have a stock of 0, the most urgent case, and the request asks for them. Start from `Product` and treat a missing stock as 0. If the author wants only products still sold, add `p.SellEndDate IS NULL` and say so in the request.
- request: The warehouse refills the shelves. Show the products whose stock, over every location, is less than half their safety stock level, the lowest stock first.
- sql:
    ```sql
    SELECT p.ProductID, p.Name, p.SafetyStockLevel, COALESCE(SUM(i.Quantity), 0) AS Quantity
    FROM Production.Product p
             LEFT JOIN Production.ProductInventory i ON i.ProductID = p.ProductID
    GROUP BY p.ProductID, p.Name, p.SafetyStockLevel
    HAVING COALESCE(SUM(i.Quantity), 0) * 2 < p.SafetyStockLevel
    ORDER BY Quantity, p.ProductID
    ;
    ```

### fix AW_SALES_A_01
- section: SALES   tier: Advanced
- title: The sales of each sales person, a column per fiscal year
- why: `PIVOT` groups by every column of its source that is not pivoted, and here that is only `LastName`. Two sales persons with the same last name would be merged into one row. Carry `SalesPersonID` through the pivot. `ORDER BY pvt.[2025] DESC` also has no tie-breaker, and persons with no 2025 sales are all NULL and tie.
- request: The sales director compares the sales persons over the years. Show each sales person's sales, a column per fiscal year; Adventure Works' fiscal year starts on the 1st of July.
- sql:
    ```sql
    SELECT pvt.SalesPersonID, pvt.LastName, pvt.[2022], pvt.[2023], pvt.[2024], pvt.[2025]
    FROM (SELECT h.SalesPersonID, p.LastName, h.SubTotal, YEAR(DATEADD(MONTH, 6, h.OrderDate)) AS FiscalYear
          FROM Sales.SalesOrderHeader h
                   JOIN Person.Person p ON p.BusinessEntityID = h.SalesPersonID) AS s
             PIVOT (SUM(s.SubTotal) FOR s.FiscalYear IN ([2022], [2023], [2024], [2025])) AS pvt
    ORDER BY pvt.[2025] DESC, pvt.SalesPersonID
    ;
    ```

### fix AW_SALES_B_02
- section: SALES   tier: Basic
- title: The customers, the persons and the stores among them
- why: The DDL says a customer is a person, a store, or a person who works for a store (both columns set). `COUNT(PersonID)` and `COUNT(StoreID)` each count the store contacts too, so the two counts overlap and do not add up to the total. The request should name the three kinds, and the SQL should count each kind once.
- request: Sales counts its customers. Show how many customers there are, how many of them are persons buying for themselves, how many are stores, and how many are persons buying for a store.
- sql:
    ```sql
    SELECT COUNT(*)                                                                 AS Customers,
           SUM(CASE WHEN c.PersonID IS NOT NULL AND c.StoreID IS NULL THEN 1 ELSE 0 END)     AS Persons,
           SUM(CASE WHEN c.PersonID IS NULL AND c.StoreID IS NOT NULL THEN 1 ELSE 0 END)     AS Stores,
           SUM(CASE WHEN c.PersonID IS NOT NULL AND c.StoreID IS NOT NULL THEN 1 ELSE 0 END) AS StoreContacts
    FROM Sales.Customer c
    ;
    ```

### fix AW_PURCHASING_I_02
- section: PURCHASING   tier: Intermediate
- title: The five vendors whose goods were rejected the most
- why: The query divides by `SUM(d.ReceivedQty)`, and the DDL allows `ReceivedQty = 0` (for example, an order not received yet). A vendor with nothing received makes the whole query fail with a divide-by-zero error. `Vendor.Name` is not unique, so the tie-breaker also needs the key.
- request: Quality assurance looks for unreliable vendors. Show the five vendors whose received goods were rejected the most, by the share of the quantity received.
- sql:
    ```sql
    SELECT TOP (5) v.Name,
                   SUM(d.ReceivedQty)                                                            AS ReceivedQty,
                   SUM(d.RejectedQty)                                                            AS RejectedQty,
                   CAST(SUM(d.RejectedQty) * 100 / NULLIF(SUM(d.ReceivedQty), 0) AS decimal(5, 2)) AS RejectedPercent
    FROM Purchasing.PurchaseOrderDetail d
             JOIN Purchasing.PurchaseOrderHeader h ON h.PurchaseOrderID = d.PurchaseOrderID
             JOIN Purchasing.Vendor v ON v.BusinessEntityID = h.VendorID
    GROUP BY v.BusinessEntityID, v.Name
    HAVING SUM(d.ReceivedQty) > 0
    ORDER BY SUM(d.RejectedQty) / NULLIF(SUM(d.ReceivedQty), 0) DESC, v.Name, v.BusinessEntityID
    ;
    ```

### fix AW_PURCHASING_I_01
- section: PURCHASING   tier: Intermediate
- title: The five vendors the company spent the most with
- why: `PurchaseOrderHeader.Status` includes 3 = Rejected and 1 = Pending (per the DDL check comment), and money was not spent on either. Only approved (2) and complete (4) orders should count. The `TOP (5)` also has no tie-breaker.
- request: The purchasing manager prepares the vendor reviews. Show the five vendors the company spent the most with, counting approved and complete purchase orders, and how many such orders each one had.
- sql:
    ```sql
    SELECT TOP (5) v.AccountNumber, v.Name, COUNT(*) AS Orders, SUM(h.TotalDue) AS TotalDue
    FROM Purchasing.PurchaseOrderHeader h
             JOIN Purchasing.Vendor v ON v.BusinessEntityID = h.VendorID
    WHERE h.Status IN (2, 4)
    GROUP BY v.BusinessEntityID, v.AccountNumber, v.Name
    ORDER BY TotalDue DESC, v.AccountNumber
    ;
    ```

### fix AW_PRODUCTION_I_02
- section: PRODUCTION   tier: Intermediate
- title: The five scrap reasons with the most scrapped quantity
- why: A `ScrapReasonID` on a work order means part of its quantity was scrapped, not that the order stopped (`StockedQty = OrderQty - ScrappedQty`), so "stopped" misstates the count. `TOP (5)` on the sum alone has no tie-breaker.
- request: The plant manager looks for the costliest failures. Show the five scrap reasons with the most scrapped quantity, and how many work orders scrapped parts for each one.
- sql:
    ```sql
    SELECT TOP (5) r.Name, COUNT(*) AS WorkOrders, SUM(w.ScrappedQty) AS ScrappedQty
    FROM Production.WorkOrder w
             JOIN Production.ScrapReason r ON r.ScrapReasonID = w.ScrapReasonID
    GROUP BY r.ScrapReasonID, r.Name
    ORDER BY ScrappedQty DESC, r.Name
    ;
    ```

### fix AW_PERSON_I_01
- section: PERSON   tier: Intermediate
- title: The five countries with the most addresses
- why: `TOP (5)` ordered only by a count is unstable when the fifth and sixth countries tie. Add the key as a tie-breaker. `AW_SALES_I_02` (`p.ProductID`) and `AW_SALES_I_04` (`sp.BusinessEntityID`) need the same one-line change.
- request: Marketing picks the countries for a mailing. Show the five countries with the most addresses.
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

### add AW_PURCHASING_A_01
- section: PURCHASING   tier: Advanced
- title: The yearly spend with each vendor, against the year before
- why: Purchasing is the only section with no Advanced exercise. A window function (`LAG`) over a yearly aggregate fits the level that the other sections' Advanced exercises set (SQL only).
- request: The purchasing manager watches how the spend with each vendor moves. Show, for each vendor and year, what was spent on its approved and complete purchase orders, the spend of the vendor's previous year with orders, and the change.
- sql:
    ```sql
    WITH Yearly (VendorID, OrderYear, TotalDue) AS (
        SELECT h.VendorID, YEAR(h.OrderDate), SUM(h.TotalDue)
        FROM Purchasing.PurchaseOrderHeader h
        WHERE h.Status IN (2, 4)
        GROUP BY h.VendorID, YEAR(h.OrderDate)
    )
    SELECT v.Name, y.OrderYear, y.TotalDue,
           LAG(y.TotalDue) OVER (PARTITION BY y.VendorID ORDER BY y.OrderYear)              AS PreviousTotalDue,
           y.TotalDue - LAG(y.TotalDue) OVER (PARTITION BY y.VendorID ORDER BY y.OrderYear) AS Change
    FROM Yearly y
             JOIN Purchasing.Vendor v ON v.BusinessEntityID = y.VendorID
    ORDER BY v.Name, y.VendorID, y.OrderYear
    ;
    ```

### add AW_SALES_I_05
- section: SALES   tier: Intermediate
- title: The orders and their amounts in each currency
- why: `SalesOrderHeader.CurrencyRateID` is a nullable foreign key, and nothing yet uses `CurrencyRate` or the outer-join-plus-`COALESCE` pattern it calls for. It assumes every rate converts from USD and that an order with no rate is in USD; add a check that guards this (`CurrencyRate.FromCurrencyCode = 'USD'` for every referenced rate).
- request: Finance reports sales by currency. Show, for each currency the orders were paid in, how many orders there were, their total in US dollars, and their total in that currency.
- sql:
    ```sql
    SELECT COALESCE(r.ToCurrencyCode, N'USD')            AS CurrencyCode,
           COUNT(*)                                      AS Orders,
           SUM(h.TotalDue)                               AS TotalDueUsd,
           SUM(h.TotalDue * COALESCE(r.AverageRate, 1))  AS TotalDueInCurrency
    FROM Sales.SalesOrderHeader h
             LEFT JOIN Sales.CurrencyRate r ON r.CurrencyRateID = h.CurrencyRateID
    GROUP BY COALESCE(r.ToCurrencyCode, N'USD')
    ORDER BY Orders DESC, CurrencyCode
    ;
    ```

### add AW_SALES_B_03
- section: SALES   tier: Basic
- title: The orders that gave each sales reason
- why: The many-to-many `SalesOrderHeaderSalesReason` link table, a classic `@ManyToMany`/link-entity case, is never read. A `LEFT JOIN` from `SalesReason` also keeps reasons no order gave.
- request: Marketing asks why customers buy. Show, for each sales reason and its type, how many orders gave it, the most first.
- sql:
    ```sql
    SELECT r.ReasonType, r.Name, COUNT(hr.SalesOrderID) AS Orders
    FROM Sales.SalesReason r
             LEFT JOIN Sales.SalesOrderHeaderSalesReason hr ON hr.SalesReasonID = r.SalesReasonID
    GROUP BY r.SalesReasonID, r.ReasonType, r.Name
    ORDER BY Orders DESC, r.Name
    ;
    ```

### add AW_HUMANRESOURCES_I_03
- section: HUMANRESOURCES   tier: Intermediate
- title: The employees who worked in more than one department
- why: `EmployeeDepartmentHistory` is used only for current rows (`EndDate IS NULL`). Its history, a dated composite key, is what makes the table interesting, and no exercise reads it.
- request: HR looks at internal mobility. Show the employees who have worked in more than one department, with how many departments each one worked in.
- sql:
    ```sql
    SELECT p.FirstName, p.LastName, COUNT(DISTINCT h.DepartmentID) AS Departments
    FROM HumanResources.EmployeeDepartmentHistory h
             JOIN Person.Person p ON p.BusinessEntityID = h.BusinessEntityID
    GROUP BY h.BusinessEntityID, p.FirstName, p.LastName
    HAVING COUNT(DISTINCT h.DepartmentID) > 1
    ORDER BY p.LastName, p.FirstName, h.BusinessEntityID
    ;
    ```

### add AW_PRODUCTION_B_02
- section: PRODUCTION   tier: Basic
- title: The list price of a product on a date
- why: The dated history tables (`ProductListPriceHistory`, `ProductCostHistory`), with an `EndDate` that is NULL for the current row, are never queried, and a date-range lookup is a basic, common question. Rows of one product are taken not to overlap and `EndDate` is taken as the last day of the period; add a check that guards both. The test's `@onDate` must fall inside the loaded data.
- request: A customer disputes an old invoice. Show the list price a product had on a given date.
- sql:
    ```sql
    DECLARE @productId int = 707;
    DECLARE @onDate date = '2024-01-01';
    SELECT h.ProductID, h.ListPrice, CAST(h.StartDate AS date) AS StartDate, CAST(h.EndDate AS date) AS EndDate
    FROM Production.ProductListPriceHistory h
    WHERE h.ProductID = @productId
      AND h.StartDate <= @onDate
      AND (h.EndDate IS NULL OR h.EndDate >= @onDate)
    ;
    ```

### add AW_PRODUCTION_I_03
- section: PRODUCTION   tier: Intermediate
- title: The ten products whose work orders finish late the most
- why: `WorkOrder` is read only for scrap. Its nullable `EndDate` against `DueDate` gives a natural date-arithmetic question. Average with a decimal, because `AVG` of the integer that `DATEDIFF` returns truncates.
- request: The plant manager looks for late production. Show the ten products with the most work orders finished after their due date, and by how many days they were late on average.
- sql:
    ```sql
    SELECT TOP (10) p.ProductID, p.Name, COUNT(*) AS LateWorkOrders,
                    AVG(1.0 * DATEDIFF(DAY, w.DueDate, w.EndDate)) AS AverageDaysLate
    FROM Production.WorkOrder w
             JOIN Production.Product p ON p.ProductID = w.ProductID
    WHERE w.EndDate > w.DueDate
    GROUP BY p.ProductID, p.Name
    ORDER BY LateWorkOrders DESC, p.ProductID
    ;
    ```

### add AW_PERSON_B_02
- section: PERSON   tier: Basic
- title: The addresses of each address type
- why: Person has a single Basic exercise. `BusinessEntityAddress` (a three-way link table with a composite key) and `AddressType` are never used, even though they are how every person, store and vendor reaches an address.
- request: The data steward checks how the addresses are used. Show how many addresses are held for each address type, the most first.
- sql:
    ```sql
    SELECT t.Name, COUNT(*) AS Addresses
    FROM Person.BusinessEntityAddress bea
             JOIN Person.AddressType t ON t.AddressTypeID = bea.AddressTypeID
    GROUP BY t.AddressTypeID, t.Name
    ORDER BY Addresses DESC, t.Name
    ;
    ```

### add AW_PURCHASING_B_02
- section: PURCHASING   tier: Basic
- title: The purchase orders of each status
- why: Purchasing has a single Basic exercise, and the coded `Status` column (1 to 4, documented only in the DDL's check comment) is a common case for a `CASE` label, and for an enum mapping in Jakarta Persistence.
- request: The purchasing manager checks the pipeline. Show, for each status of the purchase orders, how many orders there are and what they come to.
- sql:
    ```sql
    SELECT h.Status,
           CASE h.Status
               WHEN 1 THEN 'Pending'
               WHEN 2 THEN 'Approved'
               WHEN 3 THEN 'Rejected'
               WHEN 4 THEN 'Complete'
               END         AS StatusName,
           COUNT(*)        AS Orders,
           SUM(h.TotalDue) AS TotalDue
    FROM Purchasing.PurchaseOrderHeader h
    GROUP BY h.Status
    ORDER BY h.Status
    ;
    ```
