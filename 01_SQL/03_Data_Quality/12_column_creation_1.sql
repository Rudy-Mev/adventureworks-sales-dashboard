CONCAT(CalendarYear, '-', RIGHT('0' + CAST(MonthNumber AS varchar(2)), 2))
AS MonthYear,

CalendarYear * 100 + MonthNumber
AS YearMonthNumber