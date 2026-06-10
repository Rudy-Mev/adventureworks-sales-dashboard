USE AdventureWorksDW2025;
GO

SELECT
    SUM(SalesAmount) AS Revenue,
    SUM(SalesAmount - TotalProductCost) AS Profit,
    SUM(SalesAmount - TotalProductCost) / NULLIF(SUM(SalesAmount), 0) AS MarginRate,
    COUNT(DISTINCT SalesOrderNumber) AS Orders
FROM bi.vw_Sales;