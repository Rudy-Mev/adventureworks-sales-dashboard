USE AdventureWorksDW2025;
GO

CREATE OR ALTER VIEW bi.vw_Customer AS
SELECT
    CAST(c.CustomerKey AS BIGINT) AS CustomerKey,

    CONCAT(
        LTRIM(RTRIM(c.FirstName)),
        ' ',
        LTRIM(RTRIM(c.LastName))
    ) AS CustomerName,

    CAST(LTRIM(RTRIM(c.FirstName)) AS NVARCHAR(100)) AS FirstName,
    CAST(LTRIM(RTRIM(c.LastName)) AS NVARCHAR(100)) AS LastName,

    CAST(c.Gender AS NVARCHAR(10)) AS Gender,
    CAST(c.MaritalStatus AS NVARCHAR(10)) AS MaritalStatus,
    CAST(c.BirthDate AS DATE) AS BirthDate,

    CASE
        WHEN DATEDIFF(YEAR, c.BirthDate, GETDATE()) < 26 THEN '18-25'
        WHEN DATEDIFF(YEAR, c.BirthDate, GETDATE()) < 36 THEN '26-35'
        WHEN DATEDIFF(YEAR, c.BirthDate, GETDATE()) < 46 THEN '36-45'
        WHEN DATEDIFF(YEAR, c.BirthDate, GETDATE()) < 56 THEN '46-55'
        ELSE '55+'
    END AS AgeGroup,

    CASE
        WHEN DATEDIFF(YEAR, c.BirthDate, GETDATE()) < 26 THEN 1
        WHEN DATEDIFF(YEAR, c.BirthDate, GETDATE()) < 36 THEN 2
        WHEN DATEDIFF(YEAR, c.BirthDate, GETDATE()) < 46 THEN 3
        WHEN DATEDIFF(YEAR, c.BirthDate, GETDATE()) < 56 THEN 4
        ELSE 5
    END AS AgeGroupSort,

    CAST(c.EnglishEducation AS NVARCHAR(100)) AS Education,
    CAST(c.EnglishOccupation AS NVARCHAR(100)) AS Occupation,

    CAST(c.YearlyIncome AS DECIMAL(18,2)) AS YearlyIncome,

    CASE
        WHEN c.YearlyIncome < 40000 THEN 'Low Income'
        WHEN c.YearlyIncome < 80000 THEN 'Middle Income'
        ELSE 'High Income'
    END AS IncomeGroup,

    CASE
        WHEN c.YearlyIncome < 40000 THEN 1
        WHEN c.YearlyIncome < 80000 THEN 2
        ELSE 3
    END AS IncomeGroupSort,

    CAST(c.TotalChildren AS BIGINT) AS TotalChildren,
    CAST(c.NumberChildrenAtHome AS BIGINT) AS NumberChildrenAtHome,

    CASE
        WHEN c.HouseOwnerFlag = '1' THEN 'Home Owner'
        WHEN c.HouseOwnerFlag = '0' THEN 'Non Home Owner'
        ELSE 'Unknown'
    END AS HouseOwnerFlag,

    CAST(c.NumberCarsOwned AS BIGINT) AS NumberCarsOwned,
    CAST(c.CommuteDistance AS NVARCHAR(50)) AS CommuteDistance,
    CAST(c.DateFirstPurchase AS DATE) AS DateFirstPurchase,

    CAST(g.City AS NVARCHAR(100)) AS City,
    CAST(g.StateProvinceName AS NVARCHAR(100)) AS StateProvinceName,
    CAST(g.EnglishCountryRegionName AS NVARCHAR(100)) AS Country,
    CAST(g.PostalCode AS NVARCHAR(50)) AS PostalCode

FROM dbo.DimCustomer c
LEFT JOIN dbo.DimGeography g
    ON c.GeographyKey = g.GeographyKey;
GO