### fix WWI_SALES_A_02

- section: SALES   tier: Advanced
- title: Credit limits then and now
- why: CreditLimit is nullable, so `<>` misses changes between NULL and a value. Apply the same correction to the accompanying native-query example.
- request: Show customers whose credit limit differs from its value at a past moment, including changes to or from NULL, with the limit then and now.
- sql:

    ```sql
    DECLARE @asOf datetime2 = '2015-01-01';
    SELECT c.CustomerID, c.CustomerName,
           h.CreditLimit AS CreditLimitThen, c.CreditLimit AS CreditLimitNow
    FROM Sales.Customers c
             JOIN Sales.Customers FOR SYSTEM_TIME AS OF @asOf h ON h.CustomerID = c.CustomerID
    WHERE h.CreditLimit <> c.CreditLimit
       OR (h.CreditLimit IS NULL AND c.CreditLimit IS NOT NULL)
       OR (h.CreditLimit IS NOT NULL AND c.CreditLimit IS NULL)
    ORDER BY c.CustomerID
    ```

### fix WWI_SALES_I_03

- section: SALES   tier: Intermediate
- title: Confirmed deliveries since a date
- why: Filtering InvoiceDate includes unconfirmed deliveries and excludes older invoices delivered after the requested date. Use the computed delivery timestamp to answer the delivery question.
- request: Show a customer's deliveries confirmed on or after a date, with the invoice, confirmation time and receiver, earliest confirmation first.
- sql:

    ```sql
    DECLARE @customerId int = 1, @from date = '2016-04-01';
    SELECT InvoiceID, InvoiceDate, ConfirmedDeliveryTime, ConfirmedReceivedBy
    FROM Sales.Invoices
    WHERE CustomerID = @customerId
      AND ConfirmedDeliveryTime >= @from
    ORDER BY ConfirmedDeliveryTime, InvoiceID
    ```

### fix WWI_WAREHOUSE_A_01

- section: WAREHOUSE   tier: Advanced
- title: Cold-room readings recorded in a period
- why: System-time overlap selects when versions were current; RecordedWhen identifies when measurements were taken. Add a sample-data check that `(ColdRoomSensorNumber, RecordedWhen)` is unique across the current and historical versions, guarding the assumption that each version represents a distinct reading.
- request: Summarize each sensor's readings recorded during a period, including historical readings: count, minimum, maximum and average temperature.
- sql:

    ```sql
    DECLARE @from datetime2 = '2016-05-01', @to datetime2 = '2016-05-02';
    SELECT ColdRoomSensorNumber,
           COUNT(*)                                AS Readings,
           MIN(Temperature)                        AS Lowest,
           MAX(Temperature)                        AS Highest,
           CAST(AVG(Temperature) AS decimal(10, 2)) AS Average
    FROM Warehouse.ColdRoomTemperatures FOR SYSTEM_TIME ALL
    WHERE RecordedWhen >= @from
      AND RecordedWhen < @to
    GROUP BY ColdRoomSensorNumber
    ORDER BY ColdRoomSensorNumber
    ```

### fix WWI_APPLICATION_A_01

- section: APPLICATION   tier: Advanced
- title: The five nearest cities
- why: A missing origin location or incompatible spatial reference can produce NULL distances, and equal distances make TOP unstable. Exclude unknown distances and break ties by CityID.
- request: Find the five other cities nearest to a given city, with their state code and distance in kilometres; break equal distances by city identifier.
- sql:

    ```sql
    DECLARE @cityId int = 30378; -- San Francisco
    SELECT TOP (5) c.CityID, c.CityName,
                   sp.StateProvinceCode,
                   CAST(c.Location.STDistance(o.Location) / 1000 AS decimal(10, 1)) AS Kilometres
    FROM Application.Cities c
             JOIN Application.StateProvinces sp ON sp.StateProvinceID = c.StateProvinceID
             JOIN Application.Cities o ON o.CityID = @cityId
    WHERE c.CityID <> o.CityID
      AND c.Location.STDistance(o.Location) IS NOT NULL
    ORDER BY c.Location.STDistance(o.Location), c.CityID
    ```

### fix WWI_SALES_I_01

- section: SALES   tier: Intermediate
- title: The five highest-revenue stock items
- why: Equal revenue makes the selected five unstable. Keep TOP (5), adding the stock-item identifier as the tie-breaker.
- request: Show the five stock items with the greatest invoiced extended price in a year, with quantity sold; break equal revenue by stock-item identifier.
- sql:

    ```sql
    DECLARE @from date = '2015-01-01', @to date = '2016-01-01';
    SELECT TOP (5) si.StockItemID, si.StockItemName,
                   SUM(il.Quantity) AS Quantity, SUM(il.ExtendedPrice) AS Revenue
    FROM Sales.InvoiceLines il
             JOIN Sales.Invoices i ON i.InvoiceID = il.InvoiceID
             JOIN Warehouse.StockItems si ON si.StockItemID = il.StockItemID
    WHERE i.InvoiceDate >= @from
      AND i.InvoiceDate < @to
    GROUP BY si.StockItemID, si.StockItemName
    ORDER BY Revenue DESC, si.StockItemID
    ```

### fix WWI_PURCHASING_I_01

- section: PURCHASING   tier: Intermediate
- title: Annual purchase orders and expected amount
- why: The calculation assumes every relevant order has lines and every line has an expected price, although the DDL guarantees neither. Add fixture checks rejecting orders without lines and lines with NULL ExpectedUnitPricePerOuter; also make equal amounts deterministic.
- request: For each supplier with purchase orders placed in a year, show the order count and total amount at expected prices, largest amount first; break ties by supplier identifier.
- sql:

    ```sql
    DECLARE @from date = '2015-01-01', @to date = '2016-01-01';
    SELECT s.SupplierName,
           COUNT(DISTINCT po.PurchaseOrderID)                     AS Orders,
           SUM(pol.OrderedOuters * pol.ExpectedUnitPricePerOuter) AS Amount
    FROM Purchasing.PurchaseOrders po
             JOIN Purchasing.PurchaseOrderLines pol ON pol.PurchaseOrderID = po.PurchaseOrderID
             JOIN Purchasing.Suppliers s ON s.SupplierID = po.SupplierID
    WHERE po.OrderDate >= @from
      AND po.OrderDate < @to
    GROUP BY s.SupplierID, s.SupplierName
    ORDER BY Amount DESC, s.SupplierID
    ```

### fix WWI_SALES_B_01

- section: SALES   tier: Basic
- title: Customer counts for every buying group
- why: Starting from Customers omits buying groups with no customers. Count from BuyingGroups and append the ungrouped customers separately.
- request: Count customers in every buying group, including empty groups, and show a separate NULL group for customers belonging to none; order by count descending, then group name.
- sql:

    ```sql
    SELECT bg.BuyingGroupName, COUNT(c.CustomerID) AS Customers
    FROM Sales.BuyingGroups bg
             LEFT JOIN Sales.Customers c ON c.BuyingGroupID = bg.BuyingGroupID
    GROUP BY bg.BuyingGroupID, bg.BuyingGroupName
    UNION ALL
    SELECT CAST(NULL AS nvarchar(50)) AS BuyingGroupName, COUNT(*) AS Customers
    FROM Sales.Customers
    WHERE BuyingGroupID IS NULL
    ORDER BY Customers DESC, BuyingGroupName
    ```

### fix WWI_WAREHOUSE_I_01

- section: WAREHOUSE   tier: Intermediate
- title: Stock-item counts for every stock group
- why: The inner join omits empty stock groups. The bridge's unique group/item constraint makes counting its non-NULL identifier sufficient.
- request: Count the stock items in every stock group, including empty groups, largest count first; break ties by group name.
- sql:

    ```sql
    SELECT sg.StockGroupName, COUNT(sisg.StockItemStockGroupID) AS StockItems
    FROM Warehouse.StockGroups sg
             LEFT JOIN Warehouse.StockItemStockGroups sisg ON sisg.StockGroupID = sg.StockGroupID
    GROUP BY sg.StockGroupID, sg.StockGroupName
    ORDER BY StockItems DESC, sg.StockGroupName
    ```

### fix WWI_SALES_A_01

- section: SALES   tier: Advanced
- title: The top three sales ranks of each year
- why: RANK can return more than three people and skips ranks after ties; clarify that policy. Preserve revenue-only ranking and make the final ordering deterministic.
- request: Rank each year's salespeople by invoiced extended price using competition ranking, and show everyone ranked first, second or third, including ties; order tied people by identifier.
- sql:

    ```sql
    WITH yearly AS (SELECT YEAR(i.InvoiceDate) AS SalesYear,
                             i.SalespersonPersonID, SUM(il.ExtendedPrice) AS Revenue
                    FROM Sales.Invoices i
                             JOIN Sales.InvoiceLines il ON il.InvoiceID = i.InvoiceID
                    GROUP BY YEAR(i.InvoiceDate), i.SalespersonPersonID),
         ranked AS (SELECT y.*,
                           RANK() OVER (PARTITION BY y.SalesYear ORDER BY y.Revenue DESC) AS SalesRank
                    FROM yearly y)
    SELECT r.SalesYear, r.SalesRank, p.PersonID, p.FullName, r.Revenue
    FROM ranked r
             JOIN Application.People p ON p.PersonID = r.SalespersonPersonID
    WHERE r.SalesRank <= 3
    ORDER BY r.SalesYear, r.SalesRank, p.PersonID
    ```

### fix WWI_PURCHASING_B_02

- section: PURCHASING   tier: Basic
- title: Outstanding supplier balances
- why: Equal outstanding balances have no defined order. SupplierID supplies a stable tie-breaker.
- request: Show suppliers with unfinalized transactions, their transaction count and outstanding balance, largest balance first; break ties by supplier identifier.
- sql:

    ```sql
    SELECT s.SupplierName, COUNT(*) AS Transactions, SUM(st.OutstandingBalance) AS Outstanding
    FROM Purchasing.SupplierTransactions st
             JOIN Purchasing.Suppliers s ON s.SupplierID = st.SupplierID
    WHERE st.IsFinalized = 0
    GROUP BY s.SupplierID, s.SupplierName
    ORDER BY Outstanding DESC, s.SupplierID
    ```

### fix WWI_APPLICATION_B_01

- section: APPLICATION   tier: Basic
- title: Salespeople in name order
- why: FullName has no uniqueness constraint. Add PersonID to make equal names consistently ordered.
- request: List salespeople with their phone number and email address, ordered by name and then identifier.
- sql:

    ```sql
    SELECT PersonID, FullName, PhoneNumber, EmailAddress
    FROM Application.People
    WHERE IsSalesperson = 1
    ORDER BY FullName, PersonID
    ```

### add WWI_PURCHASING_A_01

- section: PURCHASING   tier: Advanced
- title: Each supplier's three most overdue purchase orders
- why: Purchasing currently has no Advanced exercise. This adds operational use of expected delivery dates, receipt quantities and finalization flags, with ranking at the module's established Advanced level.
- request: For each supplier, show up to three currently unfinalized purchase orders whose expected delivery date is before a cutoff and which have an unfinalized, short-received line; take the earliest expected dates first, breaking ties by order identifier.
- sql:

    ```sql
    DECLARE @asOf date = '2016-06-01';
    WITH overdue AS (SELECT po.PurchaseOrderID, po.SupplierID, po.ExpectedDeliveryDate,
                            ROW_NUMBER() OVER (
                                PARTITION BY po.SupplierID
                                ORDER BY po.ExpectedDeliveryDate, po.PurchaseOrderID
                            ) AS Position
                     FROM Purchasing.PurchaseOrders po
                     WHERE po.IsOrderFinalized = 0
                       AND po.ExpectedDeliveryDate < @asOf
                       AND EXISTS (SELECT 1
                                   FROM Purchasing.PurchaseOrderLines pol
                                   WHERE pol.PurchaseOrderID = po.PurchaseOrderID
                                     AND pol.IsOrderLineFinalized = 0
                                     AND pol.ReceivedOuters < pol.OrderedOuters))
    SELECT s.SupplierID, s.SupplierName, o.PurchaseOrderID, o.ExpectedDeliveryDate
    FROM overdue o
             JOIN Purchasing.Suppliers s ON s.SupplierID = o.SupplierID
    WHERE o.Position <= 3
    ORDER BY s.SupplierName, o.Position
    ```

### add WWI_SALES_I_05

- section: SALES   tier: Intermediate
- title: Special deals applicable to a customer and item
- why: SpecialDeals is uncovered despite its nullable targeting keys and exactly-one-pricing-option constraint. Listing applicable deals avoids inventing a precedence rule the DDL does not establish.
- request: List all special deals applicable to a given customer and stock item on a date, treating NULL targeting keys as unrestricted and both date endpoints as inclusive; show the three pricing-option columns without choosing a winning deal.
- sql:

    ```sql
    DECLARE @customerId int = 1, @stockItemId int = 1, @on date = '2016-05-01';
    SELECT sd.SpecialDealID, sd.DealDescription, sd.StartDate, sd.EndDate,
           sd.DiscountAmount, sd.DiscountPercentage, sd.UnitPrice
    FROM Sales.SpecialDeals sd
             JOIN Sales.Customers c ON c.CustomerID = @customerId
             JOIN Warehouse.StockItems si ON si.StockItemID = @stockItemId
    WHERE sd.StartDate <= @on
      AND sd.EndDate >= @on
      AND (sd.CustomerID IS NULL OR sd.CustomerID = c.CustomerID)
      AND (sd.BuyingGroupID IS NULL OR sd.BuyingGroupID = c.BuyingGroupID)
      AND (sd.CustomerCategoryID IS NULL OR sd.CustomerCategoryID = c.CustomerCategoryID)
      AND (sd.StockItemID IS NULL OR sd.StockItemID = si.StockItemID)
      AND (sd.StockGroupID IS NULL
           OR EXISTS (SELECT 1
                      FROM Warehouse.StockItemStockGroups sisg
                      WHERE sisg.StockItemID = si.StockItemID
                        AND sisg.StockGroupID = sd.StockGroupID))
    ORDER BY sd.SpecialDealID
    ```

### add WWI_APPLICATION_B_02

- section: APPLICATION   tier: Basic
- title: Cities in a country's states and provinces
- why: No exercise follows the Cities–StateProvinces–Countries foreign-key path. This adds a useful geographical lookup without relying on city-name uniqueness.
- request: List a country's cities with their state or province names and latest recorded populations, ordered by state or province, city name and city identifier.
- sql:

    ```sql
    DECLARE @countryId int = 230;
    SELECT c.CityID, c.CityName, sp.StateProvinceName, co.CountryName,
           c.LatestRecordedPopulation
    FROM Application.Cities c
             JOIN Application.StateProvinces sp ON sp.StateProvinceID = c.StateProvinceID
             JOIN Application.Countries co ON co.CountryID = sp.CountryID
    WHERE co.CountryID = @countryId
    ORDER BY sp.StateProvinceName, c.CityName, c.CityID
    ```

### add WWI_WAREHOUSE_I_03

- section: WAREHOUSE   tier: Intermediate
- title: Incoming and outgoing stock movements
- why: StockItemTransactions is uncovered, including its decimal quantities and documented positive-incoming, negative-outgoing convention. Conditional aggregation adds a useful stock-flow report.
- request: For each stock item with movements during a period, show incoming quantity, outgoing quantity as a positive amount, and net movement, ordered by item name.
- sql:

    ```sql
    DECLARE @from datetime2 = '2016-05-01', @to datetime2 = '2016-06-01';
    SELECT si.StockItemID, si.StockItemName,
           SUM(CASE WHEN st.Quantity > 0 THEN st.Quantity ELSE 0 END)  AS Incoming,
           SUM(CASE WHEN st.Quantity < 0 THEN -st.Quantity ELSE 0 END) AS Outgoing,
           SUM(st.Quantity)                                          AS NetMovement
    FROM Warehouse.StockItemTransactions st
             JOIN Warehouse.StockItems si ON si.StockItemID = st.StockItemID
    WHERE st.TransactionOccurredWhen >= @from
      AND st.TransactionOccurredWhen < @to
    GROUP BY si.StockItemID, si.StockItemName
    ORDER BY si.StockItemName
    ```