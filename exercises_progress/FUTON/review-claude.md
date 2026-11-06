# FUTON — Claude's review

### fix FUTON_DBO_A_03
- section: DBO   tier: Advanced
- title: how many of each futon the components in stock can build
- why: The `INNER JOIN Inventory` drops every component that has no stock row in WH-MAIN, so a futon whose component is missing there still shows a buildable count taken from its other components. The answer should be 0. Join the warehouse first, then `LEFT JOIN` the stock and count a missing row as 0. The JPQL needs the same `LEFT JOIN DboInventory v ON v.item = b.componentItem AND v.warehouse = w`.
- request: How many of each finished futon the components available in WH-MAIN can build: for each component, how many times its quantity is available (none if WH-MAIN does not stock it), and the smallest of those.
- sql:
    SELECT p.ItemCode, p.ItemName, MIN(FLOOR(COALESCE(v.QuantityAvailable, 0) / b.Quantity)) AS Buildable
    FROM BillOfMaterials b
             JOIN Items p ON p.ItemID = b.ParentItemID
             JOIN ItemType t ON t.ItemTypeID = p.ItemTypeID
             JOIN Warehouse w ON w.WarehouseCode = 'WH-MAIN'
             LEFT JOIN Inventory v ON v.ItemID = b.ComponentItemID AND v.WarehouseID = w.WarehouseID
    WHERE t.TypeCode = 'FG'
      AND b.IsActive = 1
    GROUP BY p.ItemID, p.ItemCode, p.ItemName
    ORDER BY Buildable DESC, p.ItemCode
    ;

### fix FUTON_DBO_B_05
- section: DBO   tier: Basic
- title: the orders not delivered yet
- why: `Status <> 'Delivered'` also returns Cancelled orders, which will never be delivered. `RequestedDeliveryDate` is nullable, and SQL Server sorts NULL first, so orders with no date come before the earliest real date. The JPQL becomes `so.status NOT IN :statuses ... ORDER BY so.requestedDeliveryDate NULLS LAST`.
- request: The orders not delivered yet and not cancelled, the earliest requested delivery date first, the orders without one last.
- sql:
    SELECT so.OrderNumber, c.CustomerName, so.Status, so.RequestedDeliveryDate, so.NetAmount
    FROM SalesOrder so
             JOIN Customer c ON c.CustomerID = so.CustomerID
    WHERE so.Status NOT IN ('Delivered', 'Cancelled')
    ORDER BY CASE WHEN so.RequestedDeliveryDate IS NULL THEN 1 ELSE 0 END, so.RequestedDeliveryDate, so.OrderNumber
    ;

### fix FUTON_DBO_I_06
- section: DBO   tier: Intermediate
- title: the three futons sold the most
- why: The query counts every item on an order line, not just futons, and it counts the lines of cancelled orders. Restrict it to finished goods (`TypeCode = 'FG'`) and leave out Cancelled orders.
- request: The three futons sold the most, by quantity, on orders not cancelled, with the net amount of their lines.
- sql:
    SELECT TOP (3) i.ItemCode, i.ItemName, SUM(d.Quantity) AS Quantity, SUM(d.NetAmount) AS NetAmount
    FROM SalesOrderDetail d
             JOIN SalesOrder so ON so.SalesOrderID = d.SalesOrderID
             JOIN Items i ON i.ItemID = d.ItemID
             JOIN ItemType t ON t.ItemTypeID = i.ItemTypeID
    WHERE t.TypeCode = 'FG'
      AND so.Status <> 'Cancelled'
    GROUP BY i.ItemID, i.ItemCode, i.ItemName
    ORDER BY Quantity DESC, i.ItemCode
    ;

### fix FUTON_DBO_I_03
- section: DBO   tier: Intermediate
- title: the five stocks nearest to their reorder points
- why: A row is one item in one warehouse, but the warehouse is neither shown nor in the ORDER BY. The same item in two warehouses gives two rows the reader cannot tell apart, and they tie on `(ratio, ItemCode)`, so the TOP (5) cut is unstable.
- request: The five stocks, an item in a warehouse, nearest to their reorder points: the ratio of the quantity available to the reorder point, the smallest first.
- sql:
    SELECT TOP (5) i.ItemCode,
                   i.ItemName,
                   w.WarehouseCode,
                   v.QuantityAvailable,
                   i.ReorderPoint,
                   CAST(v.QuantityAvailable / i.ReorderPoint AS DECIMAL(9, 2)) AS Ratio
    FROM Inventory v
             JOIN Items i ON i.ItemID = v.ItemID
             JOIN Warehouse w ON w.WarehouseID = v.WarehouseID
    WHERE i.ReorderPoint > 0
    ORDER BY v.QuantityAvailable / i.ReorderPoint, i.ItemCode, w.WarehouseCode
    ;

### fix FUTON_DBO_I_05
- section: DBO   tier: Intermediate
- title: the orders and the net amount of each sales channel
- why: Cancelled orders are counted as sales. The ORDER BY on `NetAmount` alone has no tie-breaker. `SalesOrder.SalesChannelID` is nullable, so orders without a channel quietly drop out of the inner join. That fits the request, but the exercise's text should say so.
- request: The number of orders not cancelled and their net amount, for each sales channel, the largest first.
- sql:
    SELECT ch.ChannelCode, ch.ChannelName, COUNT(*) AS Orders, SUM(so.NetAmount) AS NetAmount
    FROM SalesOrder so
             JOIN SalesChannel ch ON ch.SalesChannelID = so.SalesChannelID
    WHERE so.Status <> 'Cancelled'
    GROUP BY ch.SalesChannelID, ch.ChannelCode, ch.ChannelName
    ORDER BY NetAmount DESC, ch.ChannelCode
    ;

### fix FUTON_DBO_A_04
- section: DBO   tier: Advanced
- title: the running total of each wholesale customer
- why: The running total adds the net amount of cancelled orders. Also, the caption of the native query names `FUTON_SALES_A_01_Test`, and A_02's names `FUTON_BOM_A_02_Test`. Both are stale ids: the registry has `FUTON_DBO_A_04_Test` and `FUTON_DBO_A_02_Test`.
- request: The orders of the wholesale customers, cancelled ones left out, each with the running total of its customer's net amount, in the order of their dates.
- sql:
    SELECT c.CustomerCode,
           so.OrderNumber,
           so.OrderDate,
           so.NetAmount,
           SUM(so.NetAmount) OVER (PARTITION BY so.CustomerID
                                   ORDER BY so.OrderDate, so.SalesOrderID
                                   ROWS UNBOUNDED PRECEDING) AS RunningTotal
    FROM SalesOrder so
             JOIN Customer c ON c.CustomerID = so.CustomerID
    WHERE c.CustomerType = 'Wholesale'
      AND so.Status <> 'Cancelled'
    ORDER BY c.CustomerCode, so.OrderDate, so.SalesOrderID
    ;

### fix FUTON_DBO_I_04
- section: DBO   tier: Intermediate
- title: the share rejected on receipt, for each supplier
- why: "On receipt" is `InspectionType = 'Incoming'` in the DDL, but the query does not filter on it. The percentage also divides by a sum that can be 0. Guard it with `NULLIF`.
- request: The share of what was inspected on receipt that was rejected, for each supplier, the worst first; an inspection names its purchase order by number, not by a foreign key.
- sql:
    SELECT s.SupplierCode,
           s.SupplierName,
           SUM(q.QuantityInspected) AS Inspected,
           SUM(q.QuantityRejected) AS Rejected,
           CAST(SUM(q.QuantityRejected) * 100 / NULLIF(SUM(q.QuantityInspected), 0) AS DECIMAL(5, 2)) AS RejectedPercent
    FROM PurchaseOrder po
             JOIN Supplier s ON s.SupplierID = po.SupplierID
             JOIN QualityInspection q ON q.ReferenceType = 'PO' AND q.ReferenceNumber = po.PONumber
    WHERE q.InspectionType = 'Incoming'
    GROUP BY s.SupplierID, s.SupplierCode, s.SupplierName
    ORDER BY RejectedPercent DESC, s.SupplierCode
    ;

### fix FUTON_DBO_B_04
- section: DBO   tier: Basic
- title: the items a supplier supplies, its price beside the standard cost
- why: `SupplierItem` has no unique key on `(SupplierID, ItemID)`, and it keeps dated rows (`EffectiveDate`/`EndDate`). An item can therefore come back twice, once with an ended price, and the ORDER BY `ItemCode` then ties. Keep the open-ended offers only, as "its price" means. Then propose a check that one supplier has at most one open offer per item.
- request: The items a supplier, SUP-002, supplies now (offers not ended), with its price beside the item's standard cost.
- sql:
    SELECT i.ItemCode, i.ItemName, si.UnitPrice, i.StandardCost, si.MinimumOrderQuantity, si.LeadTimeDays
    FROM SupplierItem si
             JOIN Supplier s ON s.SupplierID = si.SupplierID
             JOIN Items i ON i.ItemID = si.ItemID
    WHERE s.SupplierCode = 'SUP-002'
      AND si.EndDate IS NULL
    ORDER BY i.ItemCode
    ;

### add FUTON_DBO_B_06
- section: DBO   tier: Basic
- title: the production orders completed late
- why: No exercise covers production (`ProductionOrder`, `WorkCenter`, `ProductionCompletion`, `ProductionOrderMaterial`). This one opens a new "Production" heading. It compares two dates and uses `LEFT JOIN` on the nullable `WorkCenterID`.
- request: The production orders completed after their planned completion date, with the item and the work center, if any, the earliest planned first.
- sql:
    SELECT po.WorkOrderNumber, i.ItemCode, wc.WorkCenterCode, po.PlannedCompletionDate, po.ActualCompletionDate
    FROM ProductionOrder po
             JOIN Items i ON i.ItemID = po.ItemID
             LEFT JOIN WorkCenter wc ON wc.WorkCenterID = po.WorkCenterID
    WHERE po.Status = 'Completed'
      AND po.ActualCompletionDate > po.PlannedCompletionDate
    ORDER BY po.PlannedCompletionDate, po.WorkOrderNumber
    ;

### add FUTON_DBO_I_07
- section: DBO   tier: Intermediate
- title: the scrap rate of each work center
- why: This is the Intermediate exercise for Production. A completion may name its own work center (nullable), or fall back to its order's. The exercise uses COALESCE in a join, NULL-safe sums and a guarded percentage.
- request: For each work center, what its completions made and scrapped, and the share scrapped, the worst first; a completion without a work center counts for its production order's.
- sql:
    SELECT wc.WorkCenterCode,
           wc.WorkCenterName,
           SUM(pc.QuantityCompleted) AS Completed,
           SUM(COALESCE(pc.QuantityScrapped, 0)) AS Scrapped,
           CAST(SUM(COALESCE(pc.QuantityScrapped, 0)) * 100
                / NULLIF(SUM(pc.QuantityCompleted + COALESCE(pc.QuantityScrapped, 0)), 0) AS DECIMAL(5, 2)) AS ScrapPercent
    FROM ProductionCompletion pc
             JOIN ProductionOrder po ON po.ProductionOrderID = pc.ProductionOrderID
             JOIN WorkCenter wc ON wc.WorkCenterID = COALESCE(pc.WorkCenterID, po.WorkCenterID)
    GROUP BY wc.WorkCenterID, wc.WorkCenterCode, wc.WorkCenterName
    ORDER BY ScrapPercent DESC, wc.WorkCenterCode
    ;

### add FUTON_DBO_I_08
- section: DBO   tier: Intermediate
- title: the share of each futon returned
- why: Returns (`SalesReturn`, `SalesReturnDetail`) are untouched, as is the FK from a return line to the order line it returns (`SODetailID`). The exercise sums the returns per order line before it joins them, so a line with several returns is not counted more than once.
- request: For each item sold on orders not cancelled, the quantity sold, the quantity returned (denied returns left out), and the share returned, the highest first.
- sql:
    SELECT i.ItemCode,
           i.ItemName,
           SUM(d.Quantity) AS Sold,
           SUM(COALESCE(r.Returned, 0)) AS Returned,
           CAST(SUM(COALESCE(r.Returned, 0)) * 100 / SUM(d.Quantity) AS DECIMAL(5, 2)) AS ReturnedPercent
    FROM SalesOrderDetail d
             JOIN SalesOrder so ON so.SalesOrderID = d.SalesOrderID
             JOIN Items i ON i.ItemID = d.ItemID
             LEFT JOIN (SELECT rd.SODetailID, SUM(rd.QuantityReturned) AS Returned
                        FROM SalesReturnDetail rd
                                 JOIN SalesReturn sr ON sr.ReturnID = rd.ReturnID
                        WHERE sr.Status <> 'Denied'
                        GROUP BY rd.SODetailID) r ON r.SODetailID = d.SODetailID
    WHERE so.Status <> 'Cancelled'
    GROUP BY i.ItemID, i.ItemCode, i.ItemName
    ORDER BY ReturnedPercent DESC, i.ItemCode
    ;

### add FUTON_DBO_B_07
- section: DBO   tier: Basic
- title: the accepted quotes not turned into orders
- why: Quotes (`SalesQuote`) are not covered. The nullable FK `ConvertedToOrderID` makes this a natural Basic `IS NULL` question for the Sales heading.
- request: The quotes a customer accepted that have not become an order yet, the oldest first.
- sql:
    SELECT q.QuoteNumber, c.CustomerName, q.QuoteDate, q.ExpirationDate, q.TotalAmount
    FROM SalesQuote q
             JOIN Customer c ON c.CustomerID = q.CustomerID
    WHERE q.Status = 'Accepted'
      AND q.ConvertedToOrderID IS NULL
    ORDER BY q.QuoteDate, q.QuoteNumber
    ;

### add FUTON_DBO_B_08
- section: DBO   tier: Basic
- title: the purchase-order lines still to receive
- why: Purchasing never reads `PurchaseOrderDetail`. `QuantityReceived` is nullable, which brings in NULL handling at the Basic level.
- request: The lines of the submitted, confirmed or shipped purchase orders that have received less than they ordered, the earliest expected delivery first.
- sql:
    SELECT po.PONumber, d.LineNumber, i.ItemCode, d.Quantity, COALESCE(d.QuantityReceived, 0) AS QuantityReceived,
           po.ExpectedDeliveryDate
    FROM PurchaseOrderDetail d
             JOIN PurchaseOrder po ON po.PurchaseOrderID = d.PurchaseOrderID
             JOIN Items i ON i.ItemID = d.ItemID
    WHERE po.Status IN ('Submitted', 'Confirmed', 'Shipped')
      AND COALESCE(d.QuantityReceived, 0) < d.Quantity
    ORDER BY po.ExpectedDeliveryDate, po.PONumber, d.LineNumber
    ;

### add FUTON_DBO_A_05
- section: DBO   tier: Advanced
- title: the last movement of each item in the main warehouse
- why: `InventoryTransaction` and `TransactionType` are never read. A greatest-row-per-group with `ROW_NUMBER` fits the Inventory heading at the Advanced level. `TransactionDate` is nullable, and a DESC sort puts NULLs last, so dated rows win. `TransactionID` breaks ties.
- request: For each item in WH-MAIN, its last inventory transaction: the type, the quantity, what it refers to, and when.
- sql:
    WITH Ranked AS (SELECT t.ItemID,
                           t.TransactionTypeID,
                           t.Quantity,
                           t.ReferenceType,
                           t.ReferenceNumber,
                           t.TransactionDate,
                           ROW_NUMBER() OVER (PARTITION BY t.ItemID
                                              ORDER BY t.TransactionDate DESC, t.TransactionID DESC) AS Rn
                    FROM InventoryTransaction t
                             JOIN Warehouse w ON w.WarehouseID = t.WarehouseID
                    WHERE w.WarehouseCode = 'WH-MAIN')
    SELECT i.ItemCode, i.ItemName, tt.TypeCode, r.Quantity, r.ReferenceType, r.ReferenceNumber, r.TransactionDate
    FROM Ranked r
             JOIN Items i ON i.ItemID = r.ItemID
             JOIN TransactionType tt ON tt.TransactionTypeID = r.TransactionTypeID
    WHERE r.Rn = 1
    ORDER BY i.ItemCode
    ;
