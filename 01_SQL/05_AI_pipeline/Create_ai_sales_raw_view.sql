USE AdventureWorksDW2025;
GO

/*
=====================================================================
 VUE : bi.vw_AI_Sales_Raw      (OPTION C — export au GRAIN FIN)
=====================================================================
 BUT
   Exposer les ventes au grain LIGNE (1 ligne = 1 vente detaillee),
   en GARDANT les identifiants SalesOrderNumber et CustomerKey.

 POURQUOI
   Orders et Customers sont des COMPTES DISTINCTS : on ne peut pas les
   additionner (un client/une commande apparait sur plusieurs lignes).
   En gardant les identifiants bruts, Python pourra les recompter
   correctement avec nunique() -> a TOUT grain, sans double comptage.

 CE QUE CA REMPLACE
   - l'ancien export pre-agrege (ai_sales_analysis_sql_export.csv)
   - le fichier ai_global_kpi.csv  (devient inutile)
   -> un seul fichier source : ai_sales_raw.csv

 NOTE
   C'est ta CTE "EnrichedRows" transformee en vue reutilisable.
=====================================================================
*/

CREATE OR ALTER VIEW bi.vw_AI_Sales_Raw AS
SELECT
    -- ===================== Dimensions TEMPS =====================
    d.CalendarYear,
    CAST(d.CalendarYear * 100 + d.MonthNumberOfYear AS INT)  AS YearMonthNumber,
    CONCAT('Q', d.CalendarQuarter)                           AS QuarterLabel,
    CONCAT(LEFT(d.MonthName, 3), ' ', d.CalendarYear)        AS MonthYear,

    -- ===================== Dimensions GEO =======================
    t.TerritoryGroup,
    t.Country,
    t.Region,

    -- ===================== Dimensions PRODUIT ===================
    p.ProductCategory,
    p.ProductSubcategory,

    -- ===================== Dimensions CLIENT ====================
    CASE
        WHEN c.YearlyIncome < 40000 THEN 'Low Income'
        WHEN c.YearlyIncome < 80000 THEN 'Middle Income'
        ELSE 'High Income'
    END AS IncomeGroup,
    CASE
        WHEN DATEDIFF(YEAR, c.BirthDate, GETDATE()) < 26 THEN '18-25'
        WHEN DATEDIFF(YEAR, c.BirthDate, GETDATE()) < 36 THEN '26-35'
        WHEN DATEDIFF(YEAR, c.BirthDate, GETDATE()) < 46 THEN '36-45'
        WHEN DATEDIFF(YEAR, c.BirthDate, GETDATE()) < 56 THEN '46-55'
        ELSE '55+'
    END AS AgeGroup,
    c.Gender,
    c.Occupation,
    c.HouseOwnerFlag,

    -- ============ MESURES ADDITIVES (valeurs d'UNE ligne) =======
    -- Ici PAS de SUM : une ligne = une vente. C'est Python qui sommera.
    s.SalesAmount                       AS Revenue,
    s.SalesAmount - s.TotalProductCost  AS Profit,
    s.OrderQuantity                     AS UnitsSold,

    -- ============ IDENTIFIANTS (le coeur de l'option C) =========
    -- On NE les agrege PAS. On les garde bruts pour que Python
    -- fasse nunique() = compter les uniques, sans double comptage.
    s.SalesOrderNumber,
    s.CustomerKey

FROM bi.vw_Sales s
LEFT JOIN bi.vw_Date      d ON s.OrderDateKey      = d.DateKey
LEFT JOIN bi.vw_Product   p ON s.ProductKey        = p.ProductKey
LEFT JOIN bi.vw_Customer  c ON s.CustomerKey       = c.CustomerKey
LEFT JOIN bi.vw_Territory t ON s.SalesTerritoryKey = t.SalesTerritoryKey;
GO

-- Ce fichier CREE seulement la vue.
-- Pour exporter le CSV, utiliser : Export_ai_sales_raw.sql
