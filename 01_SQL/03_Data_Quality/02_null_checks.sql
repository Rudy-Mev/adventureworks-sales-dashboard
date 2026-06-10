-- 02_null_checks.sql

USE AdventureWorksDW2025;
GO

SELECT
    COUNT(*) AS TotalRows,
    SUM(CASE WHEN SalesOrderNumber IS NULL THEN 1 ELSE 0 END) AS Missing_SalesOrderNumber,
    SUM(CASE WHEN ProductKey IS NULL THEN 1 ELSE 0 END) AS Missing_ProductKey,
    SUM(CASE WHEN CustomerKey IS NULL THEN 1 ELSE 0 END) AS Missing_CustomerKey,
    SUM(CASE WHEN OrderDateKey IS NULL THEN 1 ELSE 0 END) AS Missing_OrderDateKey,
    SUM(CASE WHEN SalesTerritoryKey IS NULL THEN 1 ELSE 0 END) AS Missing_TerritoryKey,
    SUM(CASE WHEN SalesAmount IS NULL THEN 1 ELSE 0 END) AS Missing_SalesAmount,
    SUM(CASE WHEN TotalProductCost IS NULL THEN 1 ELSE 0 END) AS Missing_TotalProductCost
FROM bi.vw_Sales;