# Data-Quality Checks

Diagnostic SQL run in SSMS **after** building the `bi` schema and the analytical views
(`01_Schemas` → `02_Views`). Each script is a read-only query: most return **rows only when
something is wrong** (an empty result = pass), a few return summary counts to eyeball.

> Database: `AdventureWorksDW2025`. Run the scripts in order; fix any failing check before
> moving on to `04_Business_Validation` and the AI pipeline.

| # | Script | What it checks | Pass condition |
|---|--------|----------------|----------------|
| 01 | `01_row_counts.sql` | Row counts for each `bi.*` view (`vw_Sales`, `vw_Product`, `vw_Customer`, `vw_Date`, `vw_Territory`). | Counts are non-zero and consistent with the source tables. |
| 02 | `02_null_checks.sql` | Missing values in the key and measure columns of `bi.vw_Sales` (keys, `SalesAmount`, `TotalProductCost`). | All `Missing_*` columns return `0`. |
| 03 | `03_dimension_key_uniqueness.sql` | Duplicate primary keys in each dimension (Product, Customer, Date, Territory). | Returns **no rows**. |
| 04 | `04_relationship_checks.sql` | Referential integrity — fact rows with no matching Product, Customer or Date. | Each `Sales_Without_*` count = `0`. |
| 05 | `05_duplicate_sales_check.sql` | Duplicate sales lines on `(SalesOrderNumber, SalesOrderLineNumber)` in `dbo.FactInternetSales`. | Returns **no rows**. |
| 06 | `06_anomaly_checks.sql` | Business anomalies — negative `SalesAmount`/`TotalProductCost` or non-positive `OrderQuantity`. | Returns **no rows**. |
| 07 | `07_date_consistency_checks.sql` | Date range sanity (`MIN`/`MAX`/count on `vw_Date`) and NULLs in `DimDate`. | Date range is plausible; the NULL query returns **no rows**. |
| 08 | `08_grain_check.sql` | Confirms the fact grain is **one row per order line**. | `TotalRows = DistinctOrderLines`. |

## Why this matters

These checks back the KPI guarantees made elsewhere in the project:

- `03`–`05` ensure dimension keys are unique and the fact has no orphan or duplicated lines —
  the precondition for **correct distinct counts** (orders/customers) downstream.
- `08` confirms the grain, which is why orders and customers can be recomputed with
  `COUNT(DISTINCT …)` / `nunique` at any aggregation level without double-counting.
- `02` and `06` catch missing or impossible values before they reach Power BI or the AI report.
