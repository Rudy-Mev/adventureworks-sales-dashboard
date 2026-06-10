USE AdventureWorksDW2025;
GO

-- 01_row_counts.sql
SELECT 'vw_Sales' AS TableName, COUNT(*) AS Row_Count FROM bi.vw_Sales
UNION ALL
SELECT 'vw_Product', COUNT(*) FROM bi.vw_Product
UNION ALL
SELECT 'vw_Customer', COUNT(*) FROM bi.vw_Customer
UNION ALL
SELECT 'vw_Date', COUNT(*) FROM bi.vw_Date
UNION ALL
SELECT 'vw_Territory', COUNT(*) FROM bi.vw_Territory;

/* 
Avec UNION ALL, En fait, c’est l’équivalent compact de faire 5 requêtes séparées :
SELECT COUNT(*) FROM bi.vw_Sales;
SELECT COUNT(*) FROM bi.vw_Product;
SELECT COUNT(*) FROM bi.vw_Customer;
SELECT COUNT(*) FROM bi.vw_Date;
SELECT COUNT(*) FROM bi.vw_Territory;
*/