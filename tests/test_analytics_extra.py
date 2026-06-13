# -*- coding: utf-8 -*-
"""Unit tests for analytics_extra (attach cross-sell + revenue forecast)."""
import os
import sys
import pandas as pd
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "03_Python"))
import analytics_extra as ax  # noqa: E402


def _toy_orders():
    # SO1: Bike + Accessory | SO2: Bike only | SO3: Accessory only
    return pd.DataFrame({
        "SalesOrderNumber": ["SO1", "SO1", "SO2", "SO3"],
        "ProductCategory": ["Bikes", "Accessories", "Bikes", "Accessories"],
        "Revenue": [200.0, 50.0, 300.0, 30.0],
        "Profit":  [80.0,  31.0, 120.0, 18.0],
    })


def test_attach_counts_and_rate():
    a = ax.attach_analysis(_toy_orders())
    assert a["anchor_orders"] == 2          # SO1, SO2 contain Bikes
    assert a["attached"] == 1               # only SO1 also has Accessories
    assert a["gap_orders"] == 1             # SO2 is the unattached base
    assert a["attach_rate"] == pytest.approx(0.5)


def test_attach_basket_and_addressable():
    a = ax.attach_analysis(_toy_orders())
    assert a["acc_orders"] == 2             # SO1, SO3 contain Accessories
    assert a["avg_basket"] == pytest.approx(40.0)     # (50+30)/2
    assert a["acc_margin"] == pytest.approx(49.0 / 80.0)
    assert a["addressable_rev"] == pytest.approx(40.0)        # gap(1) * 40
    assert a["addressable_profit"] == pytest.approx(40.0 * 49.0 / 80.0)


def test_forecast_range_and_volatility():
    f = ax.revenue_forecast({2011: 100.0, 2012: 80.0, 2013: 160.0})
    assert f["next_year"] == 2014
    assert f["cagr"] == pytest.approx((160 / 100) ** 0.5 - 1)
    assert f["lin_next"] == pytest.approx(173.333, rel=1e-3)
    assert f["cagr_next"] == pytest.approx(160 * (1 + f["cagr"]))
    assert f["low"] <= f["high"]
    assert f["volatile"] is True            # 2012 < 2011


def test_forecast_needs_two_years():
    assert ax.revenue_forecast({2013: 100.0}) is None


def test_no_invented_numbers_when_attach_absent():
    # anchor present, attach category absent -> zero attach, no crash
    df = pd.DataFrame({
        "SalesOrderNumber": ["SO1", "SO2"],
        "ProductCategory": ["Bikes", "Bikes"],
        "Revenue": [100.0, 200.0], "Profit": [40.0, 80.0],
    })
    a = ax.attach_analysis(df)
    assert a["attached"] == 0
    assert a["attach_rate"] == pytest.approx(0.0)
    assert a["avg_basket"] is None          # no accessory orders -> None, not a made-up value
    assert a["addressable_rev"] is None
