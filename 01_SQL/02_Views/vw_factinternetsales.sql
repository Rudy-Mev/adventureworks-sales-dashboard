USE AdventureWorksDW2025;
GO

CREATE OR ALTER VIEW bi.vw_Sales AS
SELECT
    SalesOrderNumber,
    -- SalesOrderLineNumber,
    CAST(OrderDateKey AS BIGINT) AS OrderDateKey,
    CAST(ProductKey AS BIGINT) AS ProductKey,
    CAST(CustomerKey AS BIGINT) AS CustomerKey,
    CAST(PromotionKey AS BIGINT) AS PromotionKey,
    CAST(SalesTerritoryKey AS BIGINT) AS SalesTerritoryKey,

    CAST(OrderQuantity AS INT) AS OrderQuantity,

    CAST(UnitPrice AS DECIMAL(18,2)) AS UnitPrice,
    CAST(SalesAmount AS DECIMAL(18,2)) AS SalesAmount,
    CAST(TotalProductCost AS DECIMAL(18,2)) AS TotalProductCost

FROM dbo.FactInternetSales;
GO