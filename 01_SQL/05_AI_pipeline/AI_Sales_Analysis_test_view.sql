USE AdventureWorksDW2025;
GO

SELECT TOP 100 *
FROM bi.vw_AI_Sales_Analysis
ORDER BY YearMonthNumber, Country, ProductCategory;