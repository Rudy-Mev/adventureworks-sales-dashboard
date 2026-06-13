# -*- coding: utf-8 -*-
"""
Unit tests for the analytics guarantees of generate_ai_context.py.

Run from the repo root:  pytest -q
These tests pin the behaviours the project advertises: distinct counts that are
never summed, YoY only on comparable years, launch detection, and the
growth/margin/signal classification thresholds.
"""
import os
import sys
import pandas as pd
import pytest

# Make the engine importable (it lives in 03_Python/).
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "03_Python"))
import generate_ai_context as eng  # noqa: E402

SAMPLE = os.path.join(HERE, "..", "03_Python", "ai_sales_raw_sample.csv")


# ---------- tiny fixtures ----------
def _toy():
    """Two order lines from the SAME order/customer + one other order.

    If orders/customers were summed instead of counted distinct, the totals
    would be inflated — these tests lock the correct behaviour.
    """
    return pd.DataFrame({
        "CalendarYear": [2012, 2012, 2013],
        "YearMonthNumber": [201201, 201201, 201301],
        "Revenue": [100.0, 50.0, 200.0],
        "Profit": [40.0, 20.0, 80.0],
        "UnitsSold": [1, 1, 2],
        "SalesOrderNumber": ["SO1", "SO1", "SO2"],   # SO1 has two lines
        "CustomerKey": ["C1", "C1", "C2"],           # C1 appears twice
        "ProductCategory": ["Bikes", "Bikes", "Bikes"],
    })


# ---------- safe_div / yoy ----------
def test_safe_div_handles_zero():
    assert eng.safe_div(10, 0) is None
    assert eng.safe_div(10, 2) == 5


def test_yoy():
    assert eng.yoy(110, 100) == pytest.approx(0.10)
    assert eng.yoy(50, 100) == pytest.approx(-0.50)
    assert eng.yoy(5, 0) is None


# ---------- distinct counts (the headline guarantee) ----------
def test_orders_and_customers_are_distinct_counts():
    g = eng.aggregate(_toy())
    assert g["Revenue"] == 350.0          # additive
    assert g["Orders"] == 2               # SO1, SO2 — not 3 lines
    assert g["Customers"] == 2            # C1, C2 — not 3 rows


def test_distinct_counts_not_summed_across_segments():
    df = _toy()
    glob = eng.aggregate(df)
    by_year = eng.aggregate(df, "CalendarYear")
    # C1 buys in 2012 only here, so summing per-year customers == global; but the
    # point is the per-segment value uses nunique, never a row count.
    assert by_year["Orders"].tolist() == [1, 1]      # 2013 then 2012 (sorted by revenue desc)
    assert glob["Orders"] == 2


def test_margin_and_share_columns():
    t = eng.aggregate(_toy(), "CalendarYear")
    row2013 = t[t["CalendarYear"] == 2013].iloc[0]
    assert row2013["MarginPct"] == pytest.approx(0.40)
    assert t["RevenueShare"].sum() == pytest.approx(1.0)


# ---------- classification thresholds ----------
@pytest.mark.parametrize("v,expected", [
    (0.20, "Strong Growth"), (0.05, "Moderate Growth"),
    (-0.05, "Moderate Decline"), (-0.20, "Strong Decline"), (None, "No LY Data"),
])
def test_growth_status(v, expected):
    assert eng.growth_status(v) == expected


@pytest.mark.parametrize("v,expected", [
    (0.50, "High Margin"), (0.30, "Medium Margin"), (0.10, "Low Margin"), (None, "Unknown"),
])
def test_margin_status(v, expected):
    assert eng.margin_status(v) == expected


@pytest.mark.parametrize("growth,margin,expected", [
    (0.20, 0.40, "Growth Opportunity"),
    (-0.20, 0.40, "Recover Priority"),
    (0.20, 0.10, "Volume Growth, Low Margin"),
    (-0.20, 0.10, "High Risk"),
    (None, 0.40, "No LY / New"),
])
def test_business_signal(growth, margin, expected):
    assert eng.business_signal(growth, margin) == expected


# ---------- comparable years ----------
def _full_year(year, rev):
    return pd.DataFrame({
        "CalendarYear": [year] * 12,
        "YearMonthNumber": [year * 100 + m for m in range(1, 13)],
        "Revenue": [rev / 12] * 12, "Profit": [rev / 24] * 12, "UnitsSold": [1] * 12,
        "SalesOrderNumber": [f"SO{year}_{m}" for m in range(1, 13)],
        "CustomerKey": [f"C{m}" for m in range(1, 13)],
    })


def test_comparable_years_picks_latest_consecutive_pair():
    df = pd.concat([_full_year(2011, 7e6), _full_year(2012, 5e6), _full_year(2013, 16e6)], ignore_index=True)
    assert eng.comparable_years(df) == (2013, 2012)


def test_comparable_years_raises_without_consecutive_full_years():
    # 2011 full, 2013 full, but 2012 missing -> no consecutive pair
    df = pd.concat([_full_year(2011, 7e6), _full_year(2013, 16e6)], ignore_index=True)
    with pytest.raises(ValueError):
        eng.comparable_years(df)


# ---------- launch ("New in {year}") detection ----------
def test_new_in_year_flagged_when_prior_base_negligible():
    ldf = pd.DataFrame({
        "Revenue": [1000.0], "Profit": [400.0], "UnitsSold": [10],
        "SalesOrderNumber": ["SOa"], "CustomerKey": ["Ca"], "ProductSubcategory": ["Touring Bikes"],
    })
    pdf = pd.DataFrame({
        "Revenue": [1.0], "Profit": [0.4], "UnitsSold": [1],
        "SalesOrderNumber": ["SOb"], "CustomerKey": ["Cb"], "ProductSubcategory": ["Touring Bikes"],
    })
    out = eng.segment_latest_vs_previous("ProductSubcategory", ldf, pdf, latest=2013)
    row = out[out["ProductSubcategory"] == "Touring Bikes"].iloc[0]
    assert bool(row["IsNewBase"]) is True
    assert row["BusinessSignal"] == "New in 2013"
    assert pd.isna(row["RevenueYoY"])           # no misleading YoY % for a launch


# ---------- integration on the bundled sample ----------
@pytest.mark.skipif(not os.path.exists(SAMPLE), reason="sample CSV not present")
def test_sample_loads_and_is_consistent():
    df = eng.load_data(SAMPLE, eng.ACTIVE_FILTERS)
    assert eng.comparable_years(df) == (2013, 2012)
    g = eng.aggregate(df)
    assert g["Revenue"] > 0 and g["Orders"] > 0 and g["Customers"] > 0
    # distinct customers must be <= number of rows (sanity: never inflated)
    assert g["Customers"] <= len(df)
