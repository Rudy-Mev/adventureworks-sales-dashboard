USE AdventureWorksDW2025;
GO

CREATE OR ALTER VIEW bi.vw_Territory AS
SELECT
    CAST(SalesTerritoryKey AS BIGINT) AS SalesTerritoryKey,

    SalesTerritoryGroup AS TerritoryGroup,
    SalesTerritoryCountry AS Country,
    SalesTerritoryRegion AS Region

FROM dbo.DimSalesTerritory;
GO