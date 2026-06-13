# -*- coding: utf-8 -*-
"""
analytics_extra.py — optional analytical depth for the AI context.

Two grounded, decision-oriented add-ons consumed by generate_ai_context.py:

1. Accessories cross-sell ("attach") — how often Bike orders also contain
   Accessories, and the addressable revenue/profit if currently-unattached bike
   orders each added an average accessory basket. (One stated assumption; not a forecast.)
2. Revenue outlook — a deliberately cautious next-year projection (linear trend
   vs CAGR) presented as a range, with an explicit volatility caveat.

Everything is computed from the data; the only modelling assumption (the attach
basket) is labelled as such, in keeping with the project's "no invented numbers" rule.
"""

import numpy as np


# ============================ Pure computations ============================
def attach_analysis(df, anchor="Bikes", attach="Accessories"):
    """Cross-sell metrics between an anchor category and an attach category.

    Works at order grain: an order "contains" a category if any of its lines
    belong to it. Returns counts, attach rate, the unattached base, the average
    accessory basket, the accessory margin, and the addressable revenue/profit.
    """
    cats_per_order = df.groupby("SalesOrderNumber")["ProductCategory"].agg(set)
    anchor_orders = cats_per_order[cats_per_order.apply(lambda s: anchor in s)]
    n_anchor = int(len(anchor_orders))
    n_attached = int(anchor_orders.apply(lambda s: attach in s).sum())
    gap_orders = n_anchor - n_attached
    attach_rate = (n_attached / n_anchor) if n_anchor else None

    acc = df[df["ProductCategory"] == attach]
    acc_orders = int(acc["SalesOrderNumber"].nunique())
    acc_rev = float(acc["Revenue"].sum())
    acc_profit = float(acc["Profit"].sum())
    avg_basket = (acc_rev / acc_orders) if acc_orders else None
    acc_margin = (acc_profit / acc_rev) if acc_rev else None

    addressable_rev = (gap_orders * avg_basket) if avg_basket is not None else None
    addressable_profit = (addressable_rev * acc_margin) if (addressable_rev is not None and acc_margin is not None) else None

    return dict(
        anchor=anchor, attach=attach, anchor_orders=n_anchor, attached=n_attached,
        gap_orders=gap_orders, attach_rate=attach_rate, acc_orders=acc_orders,
        avg_basket=avg_basket, acc_margin=acc_margin,
        addressable_rev=addressable_rev, addressable_profit=addressable_profit,
    )


def revenue_forecast(rev_by_year):
    """Cautious next-year revenue projection from a {year: revenue} dict.

    Returns both a linear-trend and a CAGR-based projection (as a range), plus a
    `volatile` flag set when revenue dipped in any year (point forecasts then
    unreliable). Returns None if fewer than two years are available.
    """
    years = sorted(rev_by_year)
    if len(years) < 2:
        return None
    rev = [rev_by_year[y] for y in years]
    span = years[-1] - years[0]
    cagr = ((rev[-1] / rev[0]) ** (1 / span) - 1) if (rev[0] > 0 and span > 0) else None

    slope, intercept = np.polyfit(years, rev, 1)
    lin_next = float(slope * (years[-1] + 1) + intercept)
    cagr_next = float(rev[-1] * (1 + cagr)) if cagr is not None else None

    volatile = any(rev[i] < rev[i - 1] for i in range(1, len(rev)))
    candidates = [v for v in (lin_next, cagr_next) if v is not None]
    return dict(
        years=years, cagr=cagr, lin_next=lin_next, cagr_next=cagr_next,
        next_year=years[-1] + 1, low=min(candidates), high=max(candidates), volatile=volatile,
    )


# ============================ Prompt formatting ============================
def build_extra_sections(df, rev_by_year, currency="€"):
    """Render the two add-on sections as a prompt text block (same style as the engine)."""
    def money(v):
        return "N/A" if v is None else f"{v:,.0f} {currency}"

    def pct(v):
        return "N/A" if v is None else f"{v:.1%}"

    def ttl(t):
        return f"\n\n{'='*80}\n{t}\n{'='*80}\n"

    a = attach_analysis(df)
    s = ttl(f"ACCESSORIES CROSS-SELL (ATTACH) — full period")
    s += f"- Orders containing {a['anchor']}: {a['anchor_orders']:,}\n"
    s += f"- Of those, orders that ALSO contain {a['attach']}: {a['attached']:,} -> attach rate {pct(a['attach_rate'])}\n"
    s += f"- {a['anchor']} orders WITHOUT any {a['attach'].lower()}: {a['gap_orders']:,} (the addressable base)\n"
    s += f"- Average {a['attach'].lower()} revenue per {a['attach'].lower()} order: {money(a['avg_basket'])}\n"
    s += f"- {a['attach']} margin: {pct(a['acc_margin'])}\n"
    s += (f"- Addressable cross-sell (illustrative): {a['gap_orders']:,} unattached {a['anchor'].lower()} orders "
          f"x {money(a['avg_basket'])} average basket = {money(a['addressable_rev'])} potential revenue, "
          f"~{money(a['addressable_profit'])} profit at the {a['attach'].lower()} margin.\n")
    s += (f"  ASSUMPTION: one average {a['attach'].lower()} basket added per currently-unattached "
          f"{a['anchor'].lower()} order. This is a sizing of the opportunity, NOT a forecast.\n")

    f = revenue_forecast(rev_by_year)
    s += ttl("REVENUE OUTLOOK (cautious — complete years only)")
    if not f:
        s += "Not enough complete years to project.\n"
        return s
    s += f"- CAGR ({f['years'][0]}->{f['years'][-1]}): {pct(f['cagr'])}\n"
    s += f"- Naive {f['next_year']} projection: linear trend {money(f['lin_next'])} | CAGR-based {money(f['cagr_next'])}\n"
    s += f"- Directional range for {f['next_year']}: {money(f['low'])} to {money(f['high'])}\n"
    if f["volatile"]:
        s += ("- CAUTION: revenue dipped within the series (see REVENUE BY YEAR), so the recent jump is partly a "
              "rebound. Treat the projection as a wide directional range, not a committed number.\n")
    return s
