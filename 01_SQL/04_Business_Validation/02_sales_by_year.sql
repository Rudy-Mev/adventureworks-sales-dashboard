USE AdventureWorksDW2025;
GO

SELECT
    d.CalendarYear,
    SUM(s.SalesAmount) AS Revenue,
    SUM(s.SalesAmount - s.TotalProductCost) AS Profit,
    SUM(SalesAmount - TotalProductCost) / NULLIF(SUM(SalesAmount), 0) AS MarginRate
FROM bi.vw_Sales s
LEFT JOIN bi.vw_Date d
    ON s.OrderDateKey = d.DateKey
GROUP BY d.CalendarYear
ORDER BY d.CalendarYear;