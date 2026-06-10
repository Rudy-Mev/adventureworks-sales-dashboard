USE AdventureWorksDW2025;
GO

/*
=================================================
 EXPORT — AI SALES RAW (grain fin, OPTION C)
=================================================
 Source :
   bi.vw_AI_Sales_Raw   (cree par Create_ai_sales_raw_view.sql)

 Grain :
   1 ligne = 1 ligne de vente detaillee, avec SalesOrderNumber et CustomerKey.
   -> Python compte les uniques avec nunique() (pas de double comptage).

 Destination :
   04_Python/01_Data/Input/ai_sales_raw.csv

 Export via SSMS :
   Query > Results to > Results to File
   Separateur : point-virgule (;)   |   Inclure les en-tetes : Oui
=================================================
*/

SELECT *
FROM bi.vw_AI_Sales_Raw
ORDER BY
    YearMonthNumber,
    Country,
    ProductCategory;
