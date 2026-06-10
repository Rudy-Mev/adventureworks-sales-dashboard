USE AdventureWorksDW2025;
GO

SELECT ProductKey, COUNT(*) AS DuplicateCount
FROM bi.vw_Product
GROUP BY ProductKey
HAVING COUNT(*) > 1;

SELECT CustomerKey, COUNT(*) AS DuplicateCount
FROM bi.vw_Customer
GROUP BY CustomerKey
HAVING COUNT(*) > 1;

SELECT DateKey, COUNT(*) AS DuplicateCount
FROM bi.vw_Date
GROUP BY DateKey
HAVING COUNT(*) > 1;

SELECT SalesTerritoryKey, COUNT(*) AS DuplicateCount
FROM bi.vw_Territory
GROUP BY SalesTerritoryKey
HAVING COUNT(*) > 1;