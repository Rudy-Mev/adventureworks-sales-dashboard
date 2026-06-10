USE AdventureWorksDW2025;
GO

CREATE OR ALTER VIEW bi.vw_Product AS
SELECT
    CAST(ProductKey AS BIGINT) AS ProductKey,

    CAST(EnglishProductName AS NVARCHAR(255)) AS ProductName,

    COALESCE(EnglishProductSubcategoryName, 'Unknown') AS ProductSubcategory,

    COALESCE(EnglishProductCategoryName, 'Unknown') AS ProductCategory,

    COALESCE(ProductLine, 'Other') AS ProductLine,

    Color,
    Size,

    COALESCE(Status, 'No Model') AS Status,

    COALESCE(ModelName, 'No Model') AS ModelName,

    CAST(ListPrice AS DECIMAL(18,2)) AS ListPrice

FROM dbo.DimProduct;
GO