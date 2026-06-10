SELECT
    COUNT(*) AS Row_Count,
    MIN(CalendarYear) AS MinYear,
    MAX(CalendarYear) AS MaxYear,
    SUM(Revenue) AS TotalRevenue,
    SUM(Profit) AS TotalProfit
FROM bi.vw_AI_Sales_Analysis;