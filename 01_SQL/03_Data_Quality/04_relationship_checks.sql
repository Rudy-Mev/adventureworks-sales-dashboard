-- 03_relationship_checks.sql
SELECT COUNT(*) AS Sales_Without_Product
FROM bi.vw_Sales s
LEFT JOIN bi.vw_Product p
    ON s.ProductKey = p.ProductKey
WHERE p.ProductKey IS NULL;

SELECT COUNT(*) AS Sales_Without_Customer
FROM bi.vw_Sales s
LEFT JOIN bi.vw_Customer c
    ON s.CustomerKey = c.CustomerKey
WHERE c.CustomerKey IS NULL;

SELECT COUNT(*) AS Sales_Without_Date
FROM bi.vw_Sales s
LEFT JOIN bi.vw_Date d
    ON s.OrderDateKey = d.DateKey
WHERE d.DateKey IS NULL;