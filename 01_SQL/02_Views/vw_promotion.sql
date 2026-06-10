USE AdventureWorksDW2025;
GO

CREATE OR ALTER VIEW bi.vw_Promotion AS
SELECT
    CAST(PromotionKey AS BIGINT) AS PromotionKey,
    CAST(EnglishPromotionName AS NVARCHAR(255)) AS PromotionName,
    CAST(DiscountPct AS DECIMAL(10,4)) AS DiscountPct,

    StartDate,
    EndDate,

    DATEDIFF(DAY, StartDate, EndDate) AS PromotionDurationDays

FROM dbo.DimPromotion;
GO