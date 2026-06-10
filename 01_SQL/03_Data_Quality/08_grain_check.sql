USE AdventureWorksDW2025;
GO

-- Vérifier le grain de la table de ventes :
-- 1 ligne = 1 ligne produit dans une commande

SELECT
    COUNT(*) AS TotalRows,
    COUNT(DISTINCT CONCAT(SalesOrderNumber, '-', SalesOrderLineNumber)) AS DistinctOrderLines
FROM dbo.FactInternetSales;