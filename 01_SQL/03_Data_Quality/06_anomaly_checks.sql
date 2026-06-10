USE AdventureWorksDW2025;
GO

SELECT *
FROM bi.vw_Sales
WHERE SalesAmount < 0
   OR TotalProductCost < 0
   OR OrderQuantity <= 0;