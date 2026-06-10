USE AdventureWorksDW2025;
GO

CREATE OR ALTER VIEW bi.vw_Date AS
SELECT
    CAST(DateKey AS BIGINT) AS DateKey,
    CAST(FullDateAlternateKey AS DATE) AS FullDate,

    CAST(CalendarYear AS BIGINT) AS CalendarYear,
    CAST(CalendarSemester AS BIGINT) AS CalendarSemester,
    CAST(CalendarQuarter AS BIGINT) AS CalendarQuarter,

    CONCAT('Q', CalendarQuarter) AS QuarterLabel,

    CAST(MonthNumberOfYear AS BIGINT) AS MonthNumberOfYear,
    EnglishMonthName AS MonthName,

    CONCAT(
        LEFT(EnglishMonthName, 3),
        ' ',
        CalendarYear
    ) AS [Month Year],

    CAST(
        CONCAT(
            CalendarYear,
            RIGHT('0' + CAST(MonthNumberOfYear AS VARCHAR(2)), 2)
        ) AS BIGINT
    ) AS YearMonthNumber,

    CAST(WeekNumberOfYear AS BIGINT) AS WeekNumberOfYear,
    CAST(DayNumberOfYear AS BIGINT) AS DayNumberOfYear,
    CAST(DayNumberOfMonth AS BIGINT) AS DayNumberOfMonth,
    CAST(DayNumberOfWeek AS BIGINT) AS DayNumberOfWeek,

    EnglishDayNameOfWeek AS DayName

FROM dbo.DimDate;
GO