USE AdventureWorksDW2025;
GO

SELECT
    SalesOrderNumber,
    SalesOrderLineNumber,
    COUNT(*) AS DuplicateCount
FROM dbo.FactInternetSales
GROUP BY
    SalesOrderNumber,
    SalesOrderLineNumber
HAVING COUNT(*) > 1;