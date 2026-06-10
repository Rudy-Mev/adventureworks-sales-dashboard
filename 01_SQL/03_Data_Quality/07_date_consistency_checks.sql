USE AdventureWorksDW2025;
GO

SELECT
    MIN(FullDate) AS MinDate,
    MAX(FullDate) AS MaxDate,
    COUNT(*) AS DateRows
FROM bi.vw_Date;

SELECT *
FROM dbo.DimDate
WHERE CalendarYear IS NULL
   OR MonthNumber IS NULL
   OR MonthYear IS NULL;