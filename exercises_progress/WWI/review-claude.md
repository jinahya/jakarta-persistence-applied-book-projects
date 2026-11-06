# WWI — Claude's review

### fix WWI_SALES_A_02
- section: SALES   tier: Advanced
- title: The customers whose credit limit changed since a moment, by a native query
- why: `CreditLimit` is `NULL`able (`NULL` means no limit), and `h.CreditLimit <> c.CreditLimit` is unknown when either side is `NULL`. A limit that was added or removed after the moment is a change, but the query drops it. The `INTERSECT` test compares with `NULL`s treated as equal, and works on every version since 2016 (on 2022, `h.CreditLimit IS DISTINCT FROM c.CreditLimit`). The Java native query needs the same change.
- request: Accounts receivable wants the customers whose credit limit is not what it was at a past moment, a limit set or removed since then included, with the limit then and now.
- sql:
    DECLARE @asOf datetime2 = '2015-01-01';
    SELECT c.CustomerID, c.CustomerName, h.CreditLimit AS CreditLimitThen, c.CreditLimit AS CreditLimitNow
    FROM Sales.Customers c
             JOIN Sales.Customers FOR SYSTEM_TIME AS OF @asOf h ON h.CustomerID = c.CustomerID
    WHERE NOT EXISTS (SELECT h.CreditLimit
                      INTERSECT
                      SELECT c.CreditLimit)
    ORDER BY c.CustomerID

### fix WWI_WAREHOUSE_A_01
- section: WAREHOUSE   tier: Advanced
- title: The cold-room readings of a period, from the history
- why: `FOR SYSTEM_TIME FROM @from TO @to` returns every row version that was in force at any point in the period. That includes, for each sensor, the reading recorded before `@from` that was still current at `@from`, and it can also include current rows, not only "former versions". The reading's own time is `RecordedWhen`, so read all versions and filter on it.
- request: Quality control checks the cold rooms over a period: for each sensor, the number of readings recorded in the period and the lowest, highest and average temperature. Each reading is a version of a row of a system-versioned table, so the query reads them all with FOR SYSTEM_TIME ALL, which is SQL only.
- sql:
    DECLARE @from datetime2 = '2016-05-01', @to datetime2 = '2016-05-02';
    SELECT ColdRoomSensorNumber,
           COUNT(*)                                 AS Readings,
           MIN(Temperature)                         AS Lowest,
           MAX(Temperature)                         AS Highest,
           CAST(AVG(Temperature) AS decimal(10, 2)) AS Average
    FROM Warehouse.ColdRoomTemperatures FOR SYSTEM_TIME ALL
    WHERE RecordedWhen >= @from
      AND RecordedWhen < @to
    GROUP BY ColdRoomSensorNumber
    ORDER BY ColdRoomSensorNumber

### fix WWI_SALES_I_04
- section: SALES   tier: Intermediate
- title: The history of a customer's credit limit
- why: `Sales.Customers` gets a new version whenever any column is edited, so "every version of the row" lists many rows where the credit limit did not change. The question asks for the limit's history. `LAG` keeps only the versions where the limit changed, and the comparison treats `NULL` (no limit) as a value.
- request: Accounts receivable wants the history of a customer's credit limit: each limit it has had, from when it was set, the oldest first. FOR SYSTEM_TIME ALL reads the current row and the history together; it is SQL only.
- sql:
    DECLARE @customerId int = 890;
    WITH versions AS (SELECT CustomerID, CreditLimit, ValidFrom,
                             LAG(CreditLimit) OVER (ORDER BY ValidFrom) AS PreviousLimit,
                             ROW_NUMBER() OVER (ORDER BY ValidFrom)     AS Version
                      FROM Sales.Customers FOR SYSTEM_TIME ALL
                      WHERE CustomerID = @customerId)
    SELECT CustomerID, CreditLimit, ValidFrom AS SetFrom
    FROM versions
    WHERE Version = 1
       OR NOT EXISTS (SELECT CreditLimit
                      INTERSECT
                      SELECT PreviousLimit)
    ORDER BY ValidFrom

### fix WWI_SALES_I_01
- section: SALES   tier: Intermediate
- title: The five stock items which earned the most in a year
- why: `TOP (5) ... ORDER BY Revenue DESC` has no tie-break, so two items with the same revenue around fifth place make the result unstable, and the IT asserting the rows can flake. Add the identifier, in the JPQL too.
- request: The sales manager wants the five stock items which earned the most in a year, by the invoiced extended price, with the quantity sold; a tie by the identifier.
- sql:
    DECLARE @from date = '2015-01-01', @to date = '2016-01-01';
    SELECT TOP (5) si.StockItemID, si.StockItemName, SUM(il.Quantity) AS Quantity, SUM(il.ExtendedPrice) AS Revenue
    FROM Sales.InvoiceLines il
             JOIN Sales.Invoices i ON i.InvoiceID = il.InvoiceID
             JOIN Warehouse.StockItems si ON si.StockItemID = il.StockItemID
    WHERE i.InvoiceDate >= @from
      AND i.InvoiceDate < @to
    GROUP BY si.StockItemID, si.StockItemName
    ORDER BY Revenue DESC, si.StockItemID

### fix WWI_SALES_A_01
- section: SALES   tier: Advanced
- title: The top three salespeople of each year
- why: `RANK()` gives equal revenues the same rank, and `ORDER BY r.SalesYear, r.SalesRank` then leaves their order undefined. Add the name as the last key. The request should also say that a tie for third can return more than three rows.
- request: The sales manager ranks the salespeople of each year by the invoiced extended price and wants the top three of each year, all of those tied for a place included, a tie by name. RANK() OVER (...), a window function, is SQL only.
- sql:
    WITH yearly AS (SELECT YEAR(i.InvoiceDate) AS SalesYear, i.SalespersonPersonID, SUM(il.ExtendedPrice) AS Revenue
                    FROM Sales.Invoices i
                             JOIN Sales.InvoiceLines il ON il.InvoiceID = i.InvoiceID
                    GROUP BY YEAR(i.InvoiceDate), i.SalespersonPersonID),
         ranked AS (SELECT y.*, RANK() OVER (PARTITION BY y.SalesYear ORDER BY y.Revenue DESC) AS SalesRank
                    FROM yearly y)
    SELECT r.SalesYear, r.SalesRank, p.FullName, r.Revenue
    FROM ranked r
             JOIN Application.People p ON p.PersonID = r.SalespersonPersonID
    WHERE r.SalesRank <= 3
    ORDER BY r.SalesYear, r.SalesRank, p.FullName

### fix WWI_PURCHASING_B_02
- section: PURCHASING   tier: Basic
- title: What is still owed to each supplier
- why: `ORDER BY Outstanding DESC` has no tie-break. Suppliers with the same balance, such as two with nothing owed on their open transactions, come back in any order. `SupplierName` is unique (`UQ_Purchasing_Suppliers_SupplierName`). The JPQL needs the same key.
- request: Accounts payable wants what is still owed to each supplier: the transactions not finalized, their number and the outstanding balance, the largest first; a tie by name. IsFinalized is a computed column.
- sql:
    SELECT s.SupplierName, COUNT(*) AS Transactions, SUM(st.OutstandingBalance) AS Outstanding
    FROM Purchasing.SupplierTransactions st
             JOIN Purchasing.Suppliers s ON s.SupplierID = st.SupplierID
    WHERE st.IsFinalized = 0
    GROUP BY s.SupplierID, s.SupplierName
    ORDER BY Outstanding DESC, s.SupplierName

### fix WWI_WAREHOUSE_I_02
- section: WAREHOUSE   tier: Intermediate
- title: The stock items by country of manufacture, from the CustomFields JSON
- why: There are only a handful of countries, so equal counts are likely, and `ORDER BY StockItems DESC` leaves them in no defined order. `CustomFields` is `NULL`able, and an item without the key falls into a `NULL` group that the request does not mention.
- request: Compliance counts the stock items by country of manufacture, which is in the CustomFields JSON document, the most first, a tie by country; items with no country recorded are counted as one group. JSON_VALUE is SQL only.
- sql:
    SELECT JSON_VALUE(CustomFields, '$.CountryOfManufacture') AS CountryOfManufacture, COUNT(*) AS StockItems
    FROM Warehouse.StockItems
    GROUP BY JSON_VALUE(CustomFields, '$.CountryOfManufacture')
    ORDER BY StockItems DESC, CountryOfManufacture

### add WWI_PURCHASING_A_01
- section: PURCHASING   tier: Advanced
- title: The suppliers' late deliveries
- why: Purchasing has no Advanced exercise, and no exercise uses the delivery dates of purchase orders (`ExpectedDeliveryDate`, `LastReceiptDate`), which are both `NULL`able. The query works from a derived table, uses `HAVING` to keep only fully received orders, a conditional count and `DATEDIFF`.
- request: The buyer rates the suppliers on delivery: for each supplier, the finalized purchase orders received in full, how many of them arrived after the expected delivery date, and the average days late; the most late orders first, a tie by name.
- sql:
    WITH received AS (SELECT po.PurchaseOrderID, po.SupplierID, po.ExpectedDeliveryDate,
                             MAX(pol.LastReceiptDate) AS ReceivedDate
                      FROM Purchasing.PurchaseOrders po
                               JOIN Purchasing.PurchaseOrderLines pol ON pol.PurchaseOrderID = po.PurchaseOrderID
                      WHERE po.IsOrderFinalized = 1
                        AND po.ExpectedDeliveryDate IS NOT NULL
                      GROUP BY po.PurchaseOrderID, po.SupplierID, po.ExpectedDeliveryDate
                      HAVING COUNT(pol.LastReceiptDate) = COUNT(*))
    SELECT s.SupplierName,
           COUNT(*)                                                             AS Orders,
           SUM(CASE WHEN r.ReceivedDate > r.ExpectedDeliveryDate THEN 1 ELSE 0 END) AS Late,
           CAST(AVG(CAST(DATEDIFF(day, r.ExpectedDeliveryDate, r.ReceivedDate) AS decimal(10, 1)))
               AS decimal(10, 1))                                               AS AverageDaysLate
    FROM received r
             JOIN Purchasing.Suppliers s ON s.SupplierID = r.SupplierID
    GROUP BY s.SupplierID, s.SupplierName
    ORDER BY Late DESC, s.SupplierName

### add WWI_SALES_I_05
- section: SALES   tier: Intermediate
- title: The special deals in force on a date
- why: `Sales.SpecialDeals` is not used by any exercise. It has five `NULL`able foreign keys (stock item, stock group, customer, buying group, customer category), and CHECK constraints allow exactly one pricing option. That makes it a good LEFT JOIN exercise on optional associations and a date range.
- request: The sales desk wants the special deals in force on a date: each deal, what it applies to (stock item or stock group, customer, buying group or customer category) and its discount or price, by deal.
- sql:
    DECLARE @on date = '2016-01-01';
    SELECT d.SpecialDealID, d.DealDescription, d.StartDate, d.EndDate,
           si.StockItemName, sg.StockGroupName, c.CustomerName, bg.BuyingGroupName, cc.CustomerCategoryName,
           d.DiscountAmount, d.DiscountPercentage, d.UnitPrice
    FROM Sales.SpecialDeals d
             LEFT JOIN Warehouse.StockItems si ON si.StockItemID = d.StockItemID
             LEFT JOIN Warehouse.StockGroups sg ON sg.StockGroupID = d.StockGroupID
             LEFT JOIN Sales.Customers c ON c.CustomerID = d.CustomerID
             LEFT JOIN Sales.BuyingGroups bg ON bg.BuyingGroupID = d.BuyingGroupID
             LEFT JOIN Sales.CustomerCategories cc ON cc.CustomerCategoryID = d.CustomerCategoryID
    WHERE d.StartDate <= @on
      AND d.EndDate >= @on
    ORDER BY d.SpecialDealID

### add WWI_SALES_I_06
- section: SALES   tier: Intermediate
- title: The ten customers using the most of their credit limit
- why: `Sales.CustomerTransactions` (the receivables ledger, with the computed `IsFinalized`) and `Customers.CreditLimit` are never compared. A `NULL` limit means no limit, so those customers must be left out rather than divided by. This mirrors PURCHASING_B_02 on the sales side.
- request: Accounts receivable wants the ten customers with a credit limit whose outstanding balance uses the most of it: the limit, the balance of the transactions not finalized, and the share of the limit used; a tie by the identifier.
- sql:
    SELECT TOP (10) c.CustomerID, c.CustomerName, c.CreditLimit,
                    SUM(ct.OutstandingBalance)                                          AS Outstanding,
                    CAST(SUM(ct.OutstandingBalance) * 100 / c.CreditLimit AS decimal(10, 1)) AS PercentUsed
    FROM Sales.CustomerTransactions ct
             JOIN Sales.Customers c ON c.CustomerID = ct.CustomerID
    WHERE ct.IsFinalized = 0
      AND c.CreditLimit > 0
    GROUP BY c.CustomerID, c.CustomerName, c.CreditLimit
    ORDER BY PercentUsed DESC, c.CustomerID

### add WWI_WAREHOUSE_I_03
- section: WAREHOUSE   tier: Intermediate
- title: The movements of a stock item in a year, by transaction type
- why: `Warehouse.StockItemTransactions`, the stock ledger, and `Application.TransactionTypes` are not used anywhere. A stock-keeper's first question is what went in and out of an item over a period.
- request: The warehouse manager wants the movements of a stock item in a year: for each transaction type, the number of transactions and the net quantity, by type name.
- sql:
    DECLARE @stockItemId int = 1, @from datetime2 = '2015-01-01', @to datetime2 = '2016-01-01';
    SELECT tt.TransactionTypeName, COUNT(*) AS Transactions, SUM(sit.Quantity) AS Quantity
    FROM Warehouse.StockItemTransactions sit
             JOIN Application.TransactionTypes tt ON tt.TransactionTypeID = sit.TransactionTypeID
    WHERE sit.StockItemID = @stockItemId
      AND sit.TransactionOccurredWhen >= @from
      AND sit.TransactionOccurredWhen < @to
    GROUP BY tt.TransactionTypeID, tt.TransactionTypeName
    ORDER BY tt.TransactionTypeName

### add WWI_APPLICATION_B_02
- section: APPLICATION   tier: Basic
- title: The sales territories of a country
- why: Application has only one Basic exercise, and the Country → StateProvince hierarchy (with the indexed `SalesTerritory`) is never used. The country is taken by its unique name, not a magic id.
- request: The sales manager sizes the sales territories of a country: for each territory, the number of states or provinces and their total population, the most populous first; a tie by territory.
- sql:
    DECLARE @countryName nvarchar(60) = N'United States';
    SELECT sp.SalesTerritory, COUNT(*) AS StateProvinces, SUM(sp.LatestRecordedPopulation) AS Population
    FROM Application.StateProvinces sp
             JOIN Application.Countries c ON c.CountryID = sp.CountryID
    WHERE c.CountryName = @countryName
    GROUP BY sp.SalesTerritory
    ORDER BY Population DESC, sp.SalesTerritory

### add WWI_WAREHOUSE_B_03
- section: WAREHOUSE   tier: Basic
- title: The latest vehicle temperature readings, from the Website.VehicleTemperatures view
- why: The Website.VehicleTemperatures view is not used. It decompresses `CompressedSensorData` so that the full sensor data reads as text. It is a natural read-only entity over a memory-optimized table, as SALES_B_03 is for Website.Customers.
- request: The transport team wants the ten latest chiller readings of the delivery vehicles, from the Website.VehicleTemperatures view, with the vehicle, sensor, temperature and full sensor data; a tie by the identifier.
- sql:
    SELECT TOP (10) VehicleTemperatureID, VehicleRegistration, ChillerSensorNumber, RecordedWhen, Temperature, FullSensorData
    FROM Website.VehicleTemperatures
    ORDER BY RecordedWhen DESC, VehicleTemperatureID DESC
