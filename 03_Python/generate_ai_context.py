# -*- coding: utf-8 -*-
"""
generate_ai_context.py — the analytics engine.

Reads the fine-grain sales export, computes KPIs (additive sums + distinct
counts), builds insight-driven charts, and assembles a grounded prompt for an
LLM. It never writes the narrative itself — that is the LLM's job; this script
only produces verified figures and the prompt that frames them.

Input  : 01_Data/Input/ai_sales_raw.csv          (one row per order line, ';' separated)
         falls back to 03_Python/ai_sales_raw_sample.csv when the SQL export is absent
Outputs: 01_Data/Output/ai_context_report.txt     (the prompt)
         01_Data/Output/_charts/*.png             (the figures)

To adapt to another project, edit the CONFIG block below.
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import analytics_extra


# ============================ CONFIG (edit per project) ============================
CLIENT = "AdventureWorks"
COMPANY = "Retail / E-commerce"
SECTOR = "Sales / Distribution"
OBJECTIVE = "Analyze sales performance, profitability, risks and opportunities"
CURRENCY = "€"

# A segment whose previous-year revenue is below this fraction of its current-year
# revenue is treated as a launch ("New in {year}") rather than a misleading YoY %.
NEW_BASE_RATIO = 0.05

# Dimensions analysed in depth (historical mix + YoY: growth / decline / margin / risk / opportunity).
CORE = [
    ("Product category", "ProductCategory"),
    ("Product subcategory", "ProductSubcategory"),
    ("Country", "Country"),
    ("Income group", "IncomeGroup"),
    ("Age group", "AgeGroup"),
]
# Dimensions shown for historical context only (no YoY).
HIST_EXTRA = [("Region", "Region"), ("Territory group", "TerritoryGroup")]

CHART_DIMENSIONS = ["ProductCategory", "Country", "AgeGroup"]
MATRIX_DIMENSION = "ProductCategory"          # dimension used for the Opportunity Matrix
REPORT_MODE = "executive"                     # "full" = complete report | "executive" = tight (~3-4 pages)
ACTIVE_FILTERS = {
    "Country": "All", "ProductCategory": "All", "ProductSubcategory": "All",
    "IncomeGroup": "All", "AgeGroup": "All",
}
PALETTE = {"gold": "#C9B46A", "sage": "#7CA17B", "beige": "#D6D2C8", "char": "#262626"}
# ===================================================================================

# ---- Paths ---------------------------------------------------------------
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV = os.path.join(BASE, "01_Data", "Input", "ai_sales_raw.csv")
if not os.path.exists(CSV):  # demo fallback: use the bundled sample when the SQL export is absent
    _sample = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_sales_raw_sample.csv")
    if os.path.exists(_sample):
        CSV = _sample
        print("[demo] SQL export not found -> using bundled sample:", os.path.basename(CSV))
OUTD = os.path.join(BASE, "01_Data", "Output")
CH = os.path.join(OUTD, "_charts")


# ============================ Pure helpers (unit-tested) ============================
def safe_div(numerator, denominator):
    """Divide, returning None when the denominator is zero/falsy (avoids div-by-zero)."""
    return None if not denominator else numerator / denominator


def yoy(current, previous):
    """Year-over-year change as a ratio; None when there is no comparable prior value."""
    return None if not previous else (current - previous) / previous


def aggregate(data, by=None):
    """Aggregate sales.

    Revenue/Profit/Units are summed (additive); Orders/Customers use nunique
    (distinct counts) so they stay correct at every grain. With `by`, returns a
    per-segment table enriched with MarginPct, AOV, RevPerCustomer and RevenueShare,
    sorted by descending revenue.
    """
    if by is None:
        return dict(
            Revenue=float(data["Revenue"].sum()),
            Profit=float(data["Profit"].sum()),
            UnitsSold=float(data["UnitsSold"].sum()),
            Orders=int(data["SalesOrderNumber"].nunique()),
            Customers=int(data["CustomerKey"].nunique()),
        )
    t = (
        data.groupby(by, dropna=False)
        .agg(
            Revenue=("Revenue", "sum"),
            Profit=("Profit", "sum"),
            UnitsSold=("UnitsSold", "sum"),
            Orders=("SalesOrderNumber", "nunique"),
            Customers=("CustomerKey", "nunique"),
        )
        .reset_index()
    )
    t["MarginPct"] = t["Profit"] / t["Revenue"]
    t["AOV"] = t["Revenue"] / t["Orders"]
    t["RevPerCustomer"] = t["Revenue"] / t["Customers"]
    t["RevenueShare"] = t["Revenue"] / t["Revenue"].sum()
    return t.replace([float("inf"), -float("inf")], pd.NA).sort_values("Revenue", ascending=False)


def growth_status(v):
    """Bucket a YoY revenue ratio into a qualitative growth label."""
    if v is None or pd.isna(v):
        return "No LY Data"
    if v > 0.10:
        return "Strong Growth"
    if v > 0:
        return "Moderate Growth"
    if v > -0.10:
        return "Moderate Decline"
    return "Strong Decline"


def margin_status(v):
    """Bucket a margin ratio into a qualitative margin label."""
    if v is None or pd.isna(v):
        return "Unknown"
    if v >= 0.40:
        return "High Margin"
    if v >= 0.25:
        return "Medium Margin"
    return "Low Margin"


def business_signal(growth, margin):
    """Combine growth and margin into a single decision-oriented signal."""
    if growth is None or pd.isna(growth):
        return "No LY / New"
    if growth > 0 and margin >= 0.30:
        return "Growth Opportunity"
    if growth < 0 and margin >= 0.30:
        return "Recover Priority"
    if growth > 0 and margin < 0.20:
        return "Volume Growth, Low Margin"
    if growth < 0 and margin < 0.20:
        return "High Risk"
    return "Stable"


def comparable_years(df):
    """Return the consecutive pair of *complete* (12-month) years used for YoY.

    Raises if no two consecutive 12-month years exist. Returns (latest, previous).
    """
    months = df.groupby("CalendarYear")["YearMonthNumber"].nunique()
    comp = [y for y in months[months == 12].index if (y - 1) in months[months == 12].index]
    if not comp:
        raise ValueError("No consecutive complete-year pair found -> YoY not possible.")
    latest = int(max(comp))
    return latest, latest - 1


# ============================ Data loading ============================
def load_data(csv_path, active_filters):
    """Load the fine-grain CSV, coerce types, strip BOM, and apply active filters."""
    df = pd.read_csv(csv_path, sep=";")
    df.columns = df.columns.str.strip().str.replace("﻿", "", regex=False)
    for c in ["CalendarYear", "YearMonthNumber", "Revenue", "Profit", "UnitsSold"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["SalesOrderNumber"] = df["SalesOrderNumber"].astype(str)
    df["CustomerKey"] = df["CustomerKey"].astype(str)
    for col, val in active_filters.items():
        if col in df.columns and val != "All":
            df = df[df[col] == val]
    if df.empty:
        raise ValueError("Dataset is empty after applying filters.")
    return df


def segment_latest_vs_previous(col, ldf, pdf, latest):
    """Build a per-segment YoY table for `col`: current vs previous complete year.

    Flags launches (IsNewBase), computes YoY for revenue/profit/orders/customers,
    margin delta, qualitative statuses, and risk/opportunity flags.
    """
    cur = aggregate(ldf, col)
    prev = aggregate(pdf, col)[
        [col, "Revenue", "Profit", "UnitsSold", "Orders", "Customers", "MarginPct"]
    ].rename(columns={
        "Revenue": "RevenueLY", "Profit": "ProfitLY", "UnitsSold": "UnitsSoldLY",
        "Orders": "OrdersLY", "Customers": "CustomersLY", "MarginPct": "MarginPctLY",
    })
    r = cur.merge(prev, on=col, how="left")
    r["IsNewBase"] = r["RevenueLY"].isna() | (r["RevenueLY"] < NEW_BASE_RATIO * r["Revenue"])
    r["RevenueYoY"] = ((r["Revenue"] - r["RevenueLY"]) / r["RevenueLY"]).where(~r["IsNewBase"])
    r["ProfitYoY"] = ((r["Profit"] - r["ProfitLY"]) / r["ProfitLY"]).where(~r["IsNewBase"])
    r["OrdersYoY"] = ((r["Orders"] - r["OrdersLY"]) / r["OrdersLY"]).where(~r["IsNewBase"])
    r["CustomersYoY"] = ((r["Customers"] - r["CustomersLY"]) / r["CustomersLY"]).where(~r["IsNewBase"])
    r["MarginDelta"] = r["MarginPct"] - r["MarginPctLY"]
    r["GrowthStatus"] = r["RevenueYoY"].apply(growth_status)
    r["MarginStatus"] = r["MarginPct"].apply(margin_status)
    r["BusinessSignal"] = [
        ("New in %d" % latest) if nb else business_signal(gw if pd.notna(gw) else None, mg)
        for nb, gw, mg in zip(r["IsNewBase"], r["RevenueYoY"], r["MarginPct"])
    ]
    r["RiskFlag"] = (~r["IsNewBase"]) & (r["RevenueYoY"] < -0.10)
    r["OpportunityFlag"] = (~r["IsNewBase"]) & (r["RevenueYoY"] > 0.10) & (r["MarginPct"] >= 0.30)
    return r.replace([float("inf"), -float("inf")], pd.NA)


# ============================ Charts ============================
def build_charts(ctx):
    """Render the insight-driven charts (titles state the conclusion)."""
    rev_by_year, hist, g = ctx["rev_by_year"], ctx["hist"], ctx["g"]
    LY, PY, is_rebound = ctx["LY"], ctx["PY"], ctx["is_rebound"]
    labels = {col: lab for lab, col in CORE + HIST_EXTRA}
    G, SG, BG, CHc = PALETTE["gold"], PALETTE["sage"], PALETTE["beige"], PALETTE["char"]
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})

    def _title(ax, title):
        ax.set_title(title, fontsize=12.5, color=CHc, fontweight="bold", loc="left", pad=10)

    def bar_share(path, t, col, title, topn=6):
        t = t.head(topn)
        rev = (t["Revenue"] / 1e6).tolist(); lab = t[col].tolist(); sh = (t["RevenueShare"] * 100).tolist()
        fig, ax = plt.subplots(figsize=(6.6, 3.2), dpi=150)
        y = list(range(len(lab)))[::-1]
        b = ax.barh(y, rev, color=[G] + [BG] * (len(lab) - 1), height=0.62)
        ax.set_yticks(y); ax.set_yticklabels(lab, fontsize=10, color=CHc)
        _title(ax, title); ax.spines[["top", "right", "bottom"]].set_visible(False); ax.set_xticks([])
        mx = max(rev)
        for bb, r, sp in zip(b, rev, sh):
            ax.text(bb.get_width() + mx * 0.012, bb.get_y() + bb.get_height() / 2,
                    f"{r:.1f}M{CURRENCY} ({sp:.0f}%)", va="center", fontsize=9, color=CHc, fontweight="bold")
        ax.set_xlim(0, mx * 1.25); plt.tight_layout(); fig.savefig(path, bbox_inches="tight", facecolor="white"); plt.close()

    def year_bars(path, title):
        mxr = max(rev_by_year.values())
        years = [y for y in sorted(rev_by_year) if rev_by_year[y] >= 0.05 * mxr]
        vals = [rev_by_year[y] / 1e6 for y in years]
        fig, ax = plt.subplots(figsize=(6.6, 3.0), dpi=150)
        x = list(range(len(years)))
        b = ax.bar(x, vals, color=[BG] * (len(years) - 1) + [G], width=0.6)
        ax.set_xticks(x); ax.set_xticklabels([str(y) for y in years], fontsize=10, color=CHc)
        _title(ax, title); ax.spines[["top", "right", "left"]].set_visible(False); ax.set_yticks([])
        mx = max(vals)
        for bb, v in zip(b, vals):
            ax.text(bb.get_x() + bb.get_width() / 2, bb.get_height() + mx * 0.02,
                    f"{v:.1f}M{CURRENCY}", ha="center", va="bottom", fontsize=9.5, color=CHc, fontweight="bold")
        ax.set_ylim(0, mx * 1.18); plt.tight_layout(); fig.savefig(path, bbox_inches="tight", facecolor="white"); plt.close()

    def opp_matrix(path, t, col, title, topn=10):
        t = t.dropna(subset=["MarginPct"]).head(topn).copy()
        if len(t) < 2:
            return False
        x = (t["Revenue"] / 1e6).tolist(); y = (t["MarginPct"] * 100).tolist(); lab = t[col].tolist()
        smax = max(t["Revenue"]); sizes = [(r / smax) * 520 + 90 for r in t["Revenue"]]
        xmed = float(pd.Series(x).median()); yavg = g["Profit"] / g["Revenue"] * 100  # global margin = relevant reference
        clrs = [SG if (xi >= xmed and yi >= yavg) else BG for xi, yi in zip(x, y)]
        fig, ax = plt.subplots(figsize=(6.6, 4.2), dpi=150)
        ax.axvline(xmed, color="#c9c4ba", ls="--", lw=0.9); ax.axhline(yavg, color="#c9c4ba", ls="--", lw=0.9)
        ax.scatter(x, y, s=sizes, c=clrs, edgecolor=CHc, linewidth=0.6, alpha=0.92, zorder=3)
        for xi, yi, l in zip(x, y, lab):
            ax.annotate(l, (xi, yi), fontsize=8, color=CHc, xytext=(5, 5), textcoords="offset points")
        _title(ax, title); ax.set_xlabel(f"Revenue (M{CURRENCY})", fontsize=9.5, color=CHc); ax.set_ylabel("Margin %", fontsize=9.5, color=CHc)
        ax.spines[["top", "right"]].set_visible(False); ax.margins(0.18)
        plt.tight_layout(); fig.savefig(path, bbox_inches="tight", facecolor="white"); plt.close()
        return True

    def top_of(col):
        row = hist[col].iloc[0]
        return row[col], row["RevenueShare"] * 100

    # 1) Yearly trajectory (dynamic, insight-stating title)
    ytitle = (f"Revenue rebounded in {LY} to {rev_by_year[LY]/1e6:.1f}M{CURRENCY}" if is_rebound
              else f"Revenue {LY}: {rev_by_year[LY]/1e6:.1f}M{CURRENCY} ({yoy(rev_by_year[LY], rev_by_year[PY]):+.0%} vs {PY})")
    year_bars(f"{CH}/00_Yearly revenue.png", ytitle)
    # 2) Concentration per dimension (title = the conclusion)
    n = 1
    for col in CHART_DIMENSIONS:
        name, share = top_of(col); lb = labels.get(col, col)
        bar_share(f"{CH}/{n:02d}_Revenue by {col}.png", hist[col], col, f"Revenue by {lb}: {name} = {share:.0f}%")
        n += 1
    # 3) Opportunity Matrix (signature visual) on the most readable dimension available
    mcol = MATRIX_DIMENSION if MATRIX_DIMENSION in [c for _, c in CORE] else CHART_DIMENSIONS[0]
    opp_matrix(f"{CH}/{n:02d}_Opportunity matrix.png", hist[mcol], mcol,
               f"Opportunity matrix: revenue vs margin ({labels.get(mcol, mcol)})")


# ============================ Prompt assembly ============================
def build_prompt(ctx):
    """Assemble the grounded LLM prompt from the computed context. Pure string building."""
    g, gl, gp = ctx["g"], ctx["gl"], ctx["gp"]
    hist, ltab = ctx["hist"], ctx["ltab"]
    LY, PY = ctx["LY"], ctx["PY"]
    year_series, rebound_rule, rebound_ground = ctx["year_series"], ctx["rebound_rule"], ctx["rebound_ground"]

    def m(v):
        return "N/A" if v is None or pd.isna(v) else f"{v:,.0f} {CURRENCY}"

    def pc(v):
        return "N/A" if v is None or pd.isna(v) else f"{v:.1%}"

    def nu(v):
        return "N/A" if v is None or pd.isna(v) else f"{v:,.0f}"

    def ttl(t):
        return f"\n\n{'='*80}\n{t}\n{'='*80}\n"

    ai = f"""You are an expert in business analysis, BI analytics, sales performance, profitability and executive reporting.

CLIENT CONTEXT
- Client: {CLIENT} ({COMPANY}, {SECTOR})
- Main objective: {OBJECTIVE}
- Full period analyzed (historical)
- Growth comparison: {LY} vs {PY} (full comparable years only)
- Active filters: {ACTIVE_FILTERS}

IMPORTANT ANALYTICAL RULES
- Revenue/Profit/Units are additive. Orders/Customers are DISTINCT counts (nunique), never summed -> correct at every level.
- Historical segmentations cover the full period and are NOT year-over-year.
- Growth/decline/risk/opportunity use only {LY} vs {PY}; incomplete years are excluded.
- Segments with a negligible {PY} base are flagged "New in {LY}" instead of a misleading YoY %.
- {rebound_rule}

GLOBAL HISTORICAL KPI
- Revenue: {m(g['Revenue'])}
- Profit: {m(g['Profit'])}
- Margin %: {pc(safe_div(g['Profit'],g['Revenue']))}
- Orders: {nu(g['Orders'])}
- Units sold: {nu(g['UnitsSold'])}
- Customers: {nu(g['Customers'])}
- Average order value: {m(safe_div(g['Revenue'],g['Orders']))}
- Revenue per customer: {m(safe_div(g['Revenue'],g['Customers']))}

REVENUE BY YEAR (full series)
{year_series}

LATEST COMPLETE YEAR — {LY} vs {PY}
- Revenue: {m(gl['Revenue'])} vs {m(gp['Revenue'])} -> YoY {pc(yoy(gl['Revenue'],gp['Revenue']))}
- Profit: {m(gl['Profit'])} vs {m(gp['Profit'])} -> YoY {pc(yoy(gl['Profit'],gp['Profit']))}
- Margin: {pc(safe_div(gl['Profit'],gl['Revenue']))} vs {pc(safe_div(gp['Profit'],gp['Revenue']))}
- Orders: {nu(gl['Orders'])} vs {nu(gp['Orders'])} -> YoY {pc(yoy(gl['Orders'],gp['Orders']))}
- Units: {nu(gl['UnitsSold'])} vs {nu(gp['UnitsSold'])} -> YoY {pc(yoy(gl['UnitsSold'],gp['UnitsSold']))}
- Customers: {nu(gl['Customers'])} vs {nu(gp['Customers'])} -> YoY {pc(yoy(gl['Customers'],gp['Customers']))}
"""
    for label, col in CORE + HIST_EXTRA:
        t = hist[col].head(8)
        ai += ttl(f"HISTORICAL SEGMENTATION BY {label.upper()}")
        for _, r in t.iterrows():
            ai += (f"- {r[col]}: Revenue {m(r['Revenue'])} (share {pc(r['RevenueShare'])}), Profit {m(r['Profit'])}, "
                   f"Margin {pc(r['MarginPct'])}, Orders {nu(r['Orders'])}, Units {nu(r['UnitsSold'])}, "
                   f"Customers {nu(r['Customers'])}, AOV {m(r['AOV'])}, Rev/Customer {m(r['RevPerCustomer'])}\n")

    def fmt_segment_line(r, col):
        return (f"- {r[col]}: Revenue {m(r['Revenue'])} (share {pc(r['RevenueShare'])}), Revenue YoY {pc(r['RevenueYoY'])}, "
                f"Profit YoY {pc(r['ProfitYoY'])}, Margin {pc(r['MarginPct'])} (delta {pc(r['MarginDelta'])}), "
                f"Orders YoY {pc(r['OrdersYoY'])}, Customers YoY {pc(r['CustomersYoY'])} | Signal: {r['BusinessSignal']}\n")

    def block(name, col, rows):
        s = ttl(f"{name} — {LY} vs {PY}")
        if rows.empty:
            return s + "No segment in this category.\n"
        for _, r in rows.iterrows():
            s += fmt_segment_line(r, col)
        return s

    for label, col in CORE:
        t = ltab[col]
        ct = t[~t["IsNewBase"]]
        ai += block(f"TOP GROWTH {label.upper()}", col, ct.dropna(subset=["RevenueYoY"]).sort_values("RevenueYoY", ascending=False).head(5))
        ai += block(f"DECLINING {label.upper()}", col, ct.dropna(subset=["RevenueYoY"]).sort_values("RevenueYoY").head(5))
        ai += block(f"HIGHEST MARGIN {label.upper()}", col, t.dropna(subset=["MarginPct"]).sort_values("MarginPct", ascending=False).head(5))
        ai += block(f"LOWEST MARGIN {label.upper()}", col, t.dropna(subset=["MarginPct"]).sort_values("MarginPct").head(5))
        ai += block(f"TOP RISK {label.upper()}", col, t[t["RiskFlag"]].sort_values("Revenue", ascending=False).head(5))
        ai += block(f"TOP OPPORTUNITY {label.upper()}", col, t[t["OpportunityFlag"]].sort_values("Revenue", ascending=False).head(5))
        nb = t[t["IsNewBase"]].sort_values("Revenue", ascending=False).head(8)
        if not nb.empty:
            ai += ttl(f"NEW IN {LY} (negligible {PY} base) — {label.upper()}")
            for _, r in nb.iterrows():
                ai += f"- {r[col]}: Revenue {m(r['Revenue'])} (share {pc(r['RevenueShare'])}), Margin {pc(r['MarginPct'])}\n"

    allseg = pd.concat([ltab[c] for _, c in CORE], ignore_index=True)
    ai += ttl(f"BUSINESS SIGNAL DISTRIBUTION — {LY} vs {PY}")
    for c in ["BusinessSignal", "GrowthStatus", "MarginStatus"]:
        ai += f"\n{c}:\n"
        for v, k in allseg[c].value_counts(dropna=False).items():
            ai += f"- {v}: {k} segments\n"
    ai += f"\nRiskFlag = Yes: {int(allseg['RiskFlag'].sum())} | OpportunityFlag = Yes: {int(allseg['OpportunityFlag'].sum())}\n"
    ai += analytics_extra.build_extra_sections(ctx["df"], ctx["rev_by_year"], CURRENCY)

    if REPORT_MODE == "executive":
        output_structure = ("EXPECTED OUTPUT STRUCTURE (return as plain Markdown text — do NOT build a PDF, the PDF is generated separately) - EXECUTIVE, concise (~3-4 pages)\n\n"
          "# PAGE 1 - EXECUTIVE SUMMARY\n- Global performance, %d vs %d headline, main issue, main opportunity, top 3 actions\n\n"
          "# PAGE 2 - KEY FINDINGS\n- Product, geography, customer: the essentials only (no exhaustive tables)\n\n"
          "# PAGE 3 - RECOMMENDATIONS\n- Table: Action | Expected impact | Priority (High/Medium/Low)\n\n"
          "No appendix. Be concise and decision-oriented.") % (LY, PY)
    else:
        output_structure = ("EXPECTED OUTPUT STRUCTURE (return as plain Markdown text — do NOT build a PDF, the PDF is generated separately))\n\n"
          "# PAGE 1 - EXECUTIVE SUMMARY\n- Global performance / Latest complete year performance / Main issue / Main opportunity / 3 priority actions\n\n"
          "# PAGE 2 - GLOBAL PERFORMANCE\n- Revenue / Profit / Margin %% / Orders / Customers / Historical business mix / Key comments\n\n"
          "# PAGE 3 - DETAILED ANALYSIS\n- Product performance / Geographic performance / Customer segment performance / Risks and anomalies\n\n"
          "# PAGE 4 - RECOMMENDATIONS\n- Table: Action | Expected business impact | Priority level (High / Medium / Low)\n\n"
          "# PAGE 5 - APPENDIX (non-redundant)\n- Include ONLY a %d vs %d KPI recap table and a short methodology note.\n- Do NOT repeat tables already shown in the body (country, segment, subcategory breakdowns).") % (LY, PY)

    ai += f"""

MISSION
Analyze the dataset and produce decision-oriented business insights for the C-level decision-makers of {CLIENT}.

You must:
1. Summarize global historical performance.
2. Explain latest complete year performance: {LY} vs {PY}.
3. Identify the 3 main business issues.
4. Explain probable causes using product, geography and customer segments.
5. Identify the strongest growth drivers.
6. Identify the highest-risk segments.
7. Identify the strongest opportunities.
8. Give 5 actionable recommendations.
9. Prioritize recommendations by business impact.
10. Finish with a clear executive summary for a decision-maker.

GROUNDING RULES
- Use ONLY the figures above. Never invent a number. Back every insight with a figure.
- If the data does not support a conclusion, say so.
- {rebound_ground} Treat "New in {LY}" segments as product launches, not growth %.

{output_structure}

STYLE REQUIREMENTS
- Professional consulting tone. Clear and concise. Decision-oriented. Avoid generic comments.
- Base every insight on the provided data. Mention uncertainty when data is insufficient.
- Do not confuse historical segmentation with YoY analysis.
"""
    return ai


# ============================ Orchestration ============================
def main():
    os.makedirs(CH, exist_ok=True)
    for f in os.listdir(CH):
        if f.endswith(".png"):
            os.remove(os.path.join(CH, f))

    df = load_data(CSV, ACTIVE_FILTERS)
    LY, PY = comparable_years(df)
    ldf, pdf = df[df["CalendarYear"] == LY], df[df["CalendarYear"] == PY]
    g, gl, gp = aggregate(df), aggregate(ldf), aggregate(pdf)

    rev_by_year = {int(k): float(v) for k, v in df.groupby("CalendarYear")["Revenue"].sum().items()}
    year_series = " | ".join(f"{y}: {rev_by_year[y]/1e6:.2f} M" + CURRENCY for y in sorted(rev_by_year))
    is_rebound = ((PY - 1) in rev_by_year) and (rev_by_year[PY] < rev_by_year[PY - 1])
    rebound_rule = (f"The {LY} vs {PY} jump is amplified by a REBOUND: {PY} was below {PY-1} (see REVENUE BY YEAR). Do not read it as organic tripling."
                    if is_rebound else
                    f"Interpret the {LY} vs {PY} change using the REVENUE BY YEAR trend; do not assume organic growth or a rebound without checking.")
    rebound_ground = (f"Treat the {LY} jump as a rebound from a low base." if is_rebound
                      else f"Judge the {LY} change from the REVENUE BY YEAR series; do not assume it is a rebound.")

    hist = {col: aggregate(df, col).head(10) for _, col in CORE + HIST_EXTRA}
    ltab = {col: segment_latest_vs_previous(col, ldf, pdf, LY) for _, col in CORE}

    ctx = dict(df=df, LY=LY, PY=PY, g=g, gl=gl, gp=gp, hist=hist, ltab=ltab,
               rev_by_year=rev_by_year, year_series=year_series, is_rebound=is_rebound,
               rebound_rule=rebound_rule, rebound_ground=rebound_ground)

    build_charts(ctx)
    ai = build_prompt(ctx)
    with open(os.path.join(OUTD, "ai_context_report.txt"), "w", encoding="utf-8") as fh:
        fh.write(ai)
    print(f"OK -> full prompt ({len(ai)} chars) + charts ({LY} vs {PY})")


if __name__ == "__main__":
    main()
