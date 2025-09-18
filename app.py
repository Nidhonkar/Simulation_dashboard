
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import re
from pathlib import Path

st.set_page_config(page_title="Ganga Jamuna — Fresh Connection Dashboard", layout="wide")

# ------------- THEME HEADER -------------
st.markdown(
    """
    <style>
    .title {font-size: 36px; font-weight: 800; margin-bottom: 0.2rem;}
    .subtitle {font-size: 18px; opacity: 0.8; margin-bottom: 1.2rem;}
    .kpi-card {padding: 1rem; border-radius: 1rem; background: rgba(240,240,240,0.35); border: 1px solid rgba(0,0,0,0.05);}
    .fine {font-size: 12px; opacity: 0.7;}
    </style>
    """,
    unsafe_allow_html=True,
)

# --------- FILE LOADING (Schema-flexible) ----------

DATA_FILES = [
    "data/TFC_0_6.xlsx",            # analysis report (functional KPIs by round/product/customer/etc.)
    "data/FinanceReport (6).xlsx",  # financials up to round 6
]

@st.cache_data(show_spinner=False)
def load_excels(files):
    frames = []
    meta = []
    for f in files:
        p = Path(f)
        if not p.exists():
            continue
        try:
            xls = pd.ExcelFile(p)
            for sheet in xls.sheet_names:
                try:
                    df = xls.parse(sheet)
                    df["__source_file__"] = p.name
                    df["__sheet__"] = sheet
                    frames.append(df)
                    meta.append({"file": p.name, "sheet": sheet, "rows": len(df), "cols": list(df.columns)})
                except Exception as e:
                    meta.append({"file": p.name, "sheet": sheet, "error": str(e)})
        except Exception as e:
            meta.append({"file": p.name, "error": str(e)})
    return frames, meta

frames, meta = load_excels(DATA_FILES)

if len(frames) == 0:
    st.error("No data found. Please ensure the Excel files are present under ./data/")
    st.stop()

# Merge all sheets to a long table for filtering convenience (add missing cols)
def safe_concat(dfs):
    # union of columns
    all_cols = set()
    for d in dfs:
        all_cols.update(list(d.columns))
    cols = list(all_cols)
    out = []
    for d in dfs:
        dd = d.copy()
        missing = [c for c in cols if c not in dd.columns]
        for m in missing:
            dd[m] = np.nan
        dd = dd[cols]
        out.append(dd)
    return pd.concat(out, ignore_index=True)

data_all = safe_concat(frames)

# ------------- HELPER: fuzzy column matching -----------------
def match_col(candidates, patterns, default=None):
    """
    Return the first column in candidates that matches any of the regex patterns (case-insensitive).
    patterns: list[str]
    """
    if isinstance(patterns, str):
        patterns = [patterns]
    for pat in patterns:
        rx = re.compile(pat, flags=re.I)
        for c in candidates:
            if rx.search(str(c)):
                return c
    return default

def optional_col(df, pats, default=None):
    return match_col(df.columns, pats, default=default)

# ------------- RECOGNIZE LIKELY KEYS -----------------

round_col = optional_col(data_all, [r"^round$", r"game\s*round", r"period", r"week", r"cycle"])
date_col = optional_col(data_all, [r"date"])  # optional

product_col = optional_col(data_all, [r"^product$", r"sku", r"item"])
customer_col = optional_col(data_all, [r"^customer", r"account", r"client"])
component_col = optional_col(data_all, [r"^component", r"part"])
supplier_col = optional_col(data_all, [r"^supplier", r"vendor"])

# Financial KPIs
roi_col = optional_col(data_all, [r"\bROI\b", r"return\s*on\s*investment"])
revenue_col = optional_col(data_all, [r"realized\s*revenue", r"\brevenue", r"sales\s*revenue"])
cogs_col = optional_col(data_all, [r"\bCOGS\b", r"cost\s*of\s*goods"])
indirect_col = optional_col(data_all, [r"indirect\s*cost", r"overhead"])

# Sales KPIs
shelf_life_col = optional_col(data_all, [r"attained\s*shelf\s*life", r"avg.*shelf.*life", r"\bshelf\s*life\b"])
service_level_col = optional_col(data_all, [r"achieved\s*service\s*level", r"service\s*level"])
forecast_error_col = optional_col(data_all, [r"forecast(ing)?\s*error", r"MAPE", r"bias"])
obsolescence_pct_col = optional_col(data_all, [r"obsolesc(en)?ce\s*%?", r"obsolete\s*%"])

# Supply chain
comp_avail_col = optional_col(data_all, [r"component\s*availability"])
prod_avail_col = optional_col(data_all, [r"product\s*availability"])

# Operations
inb_util_col = optional_col(data_all, [r"inbound\s*warehouse.*cube\s*util", r"inbound.*util"])
outb_util_col = optional_col(data_all, [r"outbound\s*warehouse.*cube\s*util", r"outbound.*util"])
plan_adherence_col = optional_col(data_all, [r"production\s*plan\s*adherence", r"\bplan\s*adherence"])

# Purchasing
deliv_rel_col = optional_col(data_all, [r"delivery\s*reliab", r"component\s*delivery\s*reliab"])
rej_pct_col = optional_col(data_all, [r"rejection\s*%|reject\s*%"])
comp_obsol_pct_col = optional_col(data_all, [r"component\s*obsolete\s*%|obsolete\s*component\s*%"])
rm_cost_pct_col = optional_col(data_all, [r"raw\s*material\s*cost\s*%|RM\s*cost\s*%"])

# ------------- SIDEBAR FILTERS -----------------
with st.sidebar:
    st.markdown("### Filters")
    st.caption("Use filters to drill down by Round, Product, Customer, Supplier, etc.")
    # Build options from existing columns
    def make_filter(col, label):
        if col and col in data_all.columns:
            vals = sorted([v for v in pd.Series(data_all[col]).dropna().unique()])
            return st.multiselect(label, options=vals, default=[])
        return []

    rounds = make_filter(round_col, "Round / Week")
    products = make_filter(product_col, "Product")
    customers = make_filter(customer_col, "Customer")
    components = make_filter(component_col, "Component")
    suppliers = make_filter(supplier_col, "Supplier")

def apply_filters(df):
    d = df.copy()
    def apply(col, vals):
        if col and len(vals) > 0 and col in d.columns:
            return d[d[col].isin(vals)]
        return d
    d = apply(d, rounds) if False else d  # placeholder
    if round_col and len(rounds) > 0:
        d = d[d[round_col].isin(rounds)]
    if product_col and len(products) > 0:
        d = d[d[product_col].isin(products)]
    if customer_col and len(customers) > 0:
        d = d[d[customer_col].isin(customers)]
    if component_col and len(components) > 0:
        d = d[d[component_col].isin(components)]
    if supplier_col and len(suppliers) > 0:
        d = d[d[supplier_col].isin(suppliers)]
    return d

filtered = apply_filters(data_all)

# ------------- HEADER -----------------
st.markdown('<div class="title">Ganga Jamuna — Interactive Simulation Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">The Fresh Connection • Round-wise performance & KPI-to-Financial impact</div>', unsafe_allow_html=True)

# ------------- TABS -----------------
tab_fin, tab_sales, tab_scm, tab_ops, tab_purch = st.tabs(
    ["🏦 Financials", "🛒 Sales", "🔗 Supply Chain", "🏭 Operations", "📦 Purchasing"]
)

# --------- COMMON HELPERS FOR CHARTS ----------
def kpi_row(metrics):
    cols = st.columns(len(metrics))
    for (label, value, help_text) in metrics:
        with cols[metrics.index((label, value, help_text))]:
            with st.container(border=True):
                st.markdown(f"**{label}**")
                if value is None or (isinstance(value, float) and np.isnan(value)):
                    st.metric(label="", value="—")
                else:
                    if isinstance(value, (float, int)):
                        st.metric(label="", value=f"{value:,.2f}")
                    else:
                        st.metric(label="", value=str(value))
                if help_text:
                    st.caption(help_text)

def line_or_bar(df, x, y, title, kind="line"):
    if not x or not y or x not in df.columns or y not in df.columns:
        st.info(f"Column not found for chart: {title}")
        return
    d = df[[x, y]].dropna()
    if len(d) == 0:
        st.info(f"No data for chart: {title}")
        return
    d = d.sort_values(by=x)
    if kind == "bar":
        fig = px.bar(d, x=x, y=y, title=title)
    else:
        fig = px.line(d, x=x, y=y, markers=True, title=title)
    st.plotly_chart(fig, use_container_width=True)

def scatter_rel(df, x, y, color=None, size=None, title=""):
    cols = [c for c in [x, y, color, size] if c and c in df.columns]
    if not x or not y or x not in df.columns or y not in df.columns:
        st.info(f"Columns not found for scatter: {title}")
        return
    d = df[cols].dropna()
    if len(d) == 0:
        st.info(f"No data for scatter: {title}")
        return
    fig = px.scatter(d, x=x, y=y, color=color if color in d.columns else None,
                     size=size if size in d.columns else None,
                     trendline="ols", title=title)
    st.plotly_chart(fig, use_container_width=True)

def agg_mean(df, by_col, val_col):
    if not by_col or not val_col or by_col not in df.columns or val_col not in df.columns:
        return pd.DataFrame()
    d = df[[by_col, val_col]].dropna().groupby(by_col, as_index=False).mean()
    return d

# ============== FINANCIALS TAB ==================
with tab_fin:
    st.subheader("Financial KPIs")
    fin_kpis = []
    if roi_col in filtered.columns:
        fin_kpis.append(("ROI", filtered[roi_col].dropna().mean(), "Average ROI over selection"))
    if revenue_col in filtered.columns:
        fin_kpis.append(("Realized Revenues", filtered[revenue_col].dropna().sum(), "Total Revenues over selection"))
    if cogs_col in filtered.columns:
        fin_kpis.append(("COGS", filtered[cogs_col].dropna().sum(), "Total COGS over selection"))
    if indirect_col in filtered.columns:
        fin_kpis.append(("Indirect Cost", filtered[indirect_col].dropna().sum(), "Total Indirect Costs over selection"))
    if len(fin_kpis) == 0:
        st.warning("No financial KPI columns were detected. Please verify your column names.")
    else:
        kpi_row(fin_kpis)

    st.markdown("#### Trends by Round")
    line_or_bar(filtered, round_col if round_col else date_col, roi_col, "ROI by Round", kind="line")
    line_or_bar(filtered, round_col if round_col else date_col, revenue_col, "Realized Revenues by Round", kind="bar")
    line_or_bar(filtered, round_col if round_col else date_col, cogs_col, "COGS by Round", kind="bar")
    line_or_bar(filtered, round_col if round_col else date_col, indirect_col, "Indirect Cost by Round", kind="bar")

    st.markdown("#### KPI Relationships")
    scatter_rel(filtered, revenue_col, roi_col, color=product_col or customer_col, size=None, title="Revenues vs ROI")
    scatter_rel(filtered, cogs_col, roi_col, color=product_col or supplier_col, size=None, title="COGS vs ROI")
    if indirect_col:
        scatter_rel(filtered, indirect_col, roi_col, color=customer_col or supplier_col, title="Indirect Cost vs ROI")

# ============== SALES TAB ==================
with tab_sales:
    st.subheader("Sales KPIs → Financial Impact")
    # KPI cards
    cards = []
    if service_level_col in filtered.columns:
        cards.append(("Avg Service Level", filtered[service_level_col].dropna().mean(), None))
    if shelf_life_col in filtered.columns:
        cards.append(("Avg Attained Shelf Life", filtered[shelf_life_col].dropna().mean(), None))
    if forecast_error_col in filtered.columns:
        cards.append(("Forecasting Error (Avg)", filtered[forecast_error_col].dropna().mean(), None))
    if obsolescence_pct_col in filtered.columns:
        cards.append(("Obsolescence % (Avg)", filtered[obsolescence_pct_col].dropna().mean(), None))
    if len(cards) > 0:
        kpi_row(cards)

    # Customer prioritization by ROI/Revenue
    if customer_col and (roi_col or revenue_col):
        st.markdown("#### Customer Prioritization: Impact on ROI & Revenues")
        cols_to_use = [customer_col]
        if roi_col: cols_to_use.append(roi_col)
        if revenue_col: cols_to_use.append(revenue_col)
        d = filtered[cols_to_use].dropna()
        if len(d) > 0:
            agg = d.groupby(customer_col, as_index=False).agg({(roi_col if roi_col else customer_col):"mean", (revenue_col if revenue_col else customer_col):"sum"})
            # Fix columns
            if roi_col and revenue_col:
                agg.columns = [customer_col, "Avg ROI", "Total Revenue"]
            elif roi_col:
                agg.columns = [customer_col, "Avg ROI"]
            elif revenue_col:
                agg.columns = [customer_col, "Total Revenue"]
            st.dataframe(agg.sort_values(agg.columns[-1], ascending=False))
            # Bubble chart
            if roi_col and revenue_col:
                fig = px.scatter(agg, x="Total Revenue", y="Avg ROI", size="Total Revenue", hover_name=customer_col,
                                 title="Customers — Contribution (ROI vs Revenue)")
                st.plotly_chart(fig, use_container_width=True)

    # KPI → ROI relationships
    scatter_rel(filtered, service_level_col, roi_col, color=customer_col, title="Service Level vs ROI (by Customer)")
    scatter_rel(filtered, shelf_life_col, revenue_col, color=product_col, title="Shelf Life vs Revenues (by Product)")
    scatter_rel(filtered, forecast_error_col, roi_col, color=customer_col, title="Forecast Error vs ROI")
    scatter_rel(filtered, obsolescence_pct_col, revenue_col, color=product_col, title="Obsolescence % vs Revenue")

# ============== SUPPLY CHAIN TAB ==================
with tab_scm:
    st.subheader("Supply Chain KPIs → Financial Impact")
    if comp_avail_col:
        line_or_bar(filtered, round_col if round_col else date_col, comp_avail_col, "Component Availability by Round")
    if prod_avail_col:
        line_or_bar(filtered, round_col if round_col else date_col, prod_avail_col, "Product Availability by Round")

    # Prioritize components/products by ROI impact
    if component_col and (roi_col or revenue_col):
        st.markdown("#### Components — Prioritize by ROI/Revenue impact")
        cols = [component_col]
        if roi_col: cols.append(roi_col)
        if revenue_col: cols.append(revenue_col)
        dd = filtered[cols].dropna()
        if len(dd) > 0:
            agg = dd.groupby(component_col, as_index=False).agg({(roi_col if roi_col else cols[0]):"mean", (revenue_col if revenue_col else cols[0]):"sum"}) if (roi_col and revenue_col) else dd.groupby(component_col, as_index=False).mean()
            if roi_col and revenue_col:
                agg.columns = [component_col, "Avg ROI", "Total Revenue"]
            st.dataframe(agg.sort_values(agg.columns[-1], ascending=False))
            if roi_col and revenue_col:
                fig = px.scatter(agg, x="Total Revenue", y="Avg ROI", size="Total Revenue", hover_name=component_col,
                                 title="Components — Contribution (ROI vs Revenue)")
                st.plotly_chart(fig, use_container_width=True)

    if product_col and (roi_col or revenue_col):
        st.markdown("#### Products — Prioritize by ROI/Revenue impact")
        cols = [product_col]
        if roi_col: cols.append(roi_col)
        if revenue_col: cols.append(revenue_col)
        dd = filtered[cols].dropna()
        if len(dd) > 0:
            agg = dd.groupby(product_col, as_index=False).agg({(roi_col if roi_col else cols[0]):"mean", (revenue_col if revenue_col else cols[0]):"sum"}) if (roi_col and revenue_col) else dd.groupby(product_col, as_index=False).mean()
            if roi_col and revenue_col:
                agg.columns = [product_col, "Avg ROI", "Total Revenue"]
            st.dataframe(agg.sort_values(agg.columns[-1], ascending=False))
            if roi_col and revenue_col:
                fig = px.scatter(agg, x="Total Revenue", y="Avg ROI", size="Total Revenue", hover_name=product_col,
                                 title="Products — Contribution (ROI vs Revenue)")
                st.plotly_chart(fig, use_container_width=True)

# ============== OPERATIONS TAB ==================
with tab_ops:
    st.subheader("Operations KPIs → Financial Impact")
    # KPI cards
    ops_cards = []
    if inb_util_col in filtered.columns:
        ops_cards.append(("Inbound WH Cube Util (Avg)", filtered[inb_util_col].dropna().mean(), None))
    if outb_util_col in filtered.columns:
        ops_cards.append(("Outbound WH Cube Util (Avg)", filtered[outb_util_col].dropna().mean(), None))
    if plan_adherence_col in filtered.columns:
        ops_cards.append(("Production Plan Adherence (Avg)", filtered[plan_adherence_col].dropna().mean(), None))
    if len(ops_cards) > 0:
        kpi_row(ops_cards)

    # Relationships to COGS/ROI
    scatter_rel(filtered, inb_util_col, cogs_col, title="Inbound Warehouse Utilization vs COGS")
    scatter_rel(filtered, outb_util_col, cogs_col, title="Outbound Warehouse Utilization vs COGS")
    scatter_rel(filtered, plan_adherence_col, roi_col, title="Production Plan Adherence vs ROI")

# ============== PURCHASING TAB ==================
with tab_purch:
    st.subheader("Purchasing KPIs → Financial Impact")
    purch_cards = []
    if deliv_rel_col in filtered.columns:
        purch_cards.append(("Delivery Reliability (Avg)", filtered[deliv_rel_col].dropna().mean(), None))
    if rej_pct_col in filtered.columns:
        purch_cards.append(("Rejection % (Avg)", filtered[rej_pct_col].dropna().mean(), None))
    if comp_obsol_pct_col in filtered.columns:
        purch_cards.append(("Component Obsolete % (Avg)", filtered[comp_obsol_pct_col].dropna().mean(), None))
    if rm_cost_pct_col in filtered.columns:
        purch_cards.append(("Raw Material Cost % (Avg)", filtered[rm_cost_pct_col].dropna().mean(), None))
    if len(purch_cards) > 0:
        kpi_row(purch_cards)

    # Supplier analysis for ROI & financials
    if supplier_col:
        st.markdown("#### Supplier Impact on Financials")
        if roi_col or cogs_col or revenue_col:
            cols = [supplier_col]
            agg_map = {}
            if roi_col: agg_map[roi_col] = "mean"
            if cogs_col: agg_map[cogs_col] = "sum"
            if revenue_col: agg_map[revenue_col] = "sum"
            dd = filtered[[c for c in [supplier_col, roi_col, cogs_col, revenue_col] if c]].dropna(how="all")
            if len(dd) > 0:
                agg = dd.groupby(supplier_col, as_index=False).agg(agg_map)
                # Rename for display
                rename_map = {}
                if roi_col and roi_col in agg.columns: rename_map[roi_col] = "Avg ROI"
                if cogs_col and cogs_col in agg.columns: rename_map[cogs_col] = "Total COGS"
                if revenue_col and revenue_col in agg.columns: rename_map[revenue_col] = "Total Revenue"
                agg = agg.rename(columns=rename_map)
                st.dataframe(agg.sort_values(list(agg.columns)[-1], ascending=False))
                # Bubble chart when possible
                x = "Total COGS" if "Total COGS" in agg.columns else ( "Total Revenue" if "Total Revenue" in agg.columns else None )
                y = "Avg ROI" if "Avg ROI" in agg.columns else None
                if x and y:
                    fig = px.scatter(agg, x=x, y=y, size=x, hover_name=supplier_col, title="Suppliers — Financial Impact")
                    st.plotly_chart(fig, use_container_width=True)

    # KPI → ROI relationships
    scatter_rel(filtered, deliv_rel_col, roi_col, color=supplier_col, title="Delivery Reliability vs ROI (by Supplier)")
    scatter_rel(filtered, rej_pct_col, roi_col, color=supplier_col, title="Rejection % vs ROI (by Supplier)")
    scatter_rel(filtered, rm_cost_pct_col, roi_col, color=supplier_col, title="Raw Material Cost % vs ROI (by Supplier)")

# ------------- META / DEBUG -------------
with st.expander("ℹ️ Data Sources & Detected Columns"):
    st.write(pd.DataFrame(meta))
    st.write("Detected keys:", {
        "round_col": round_col, "date_col": date_col, "product_col": product_col,
        "customer_col": customer_col, "component_col": component_col, "supplier_col": supplier_col
    })
    st.write("Detected financials:", {"ROI": roi_col, "Revenue": revenue_col, "COGS": cogs_col, "Indirect": indirect_col})
    st.write("Sales KPIs:", {"ShelfLife": shelf_life_col, "ServiceLevel": service_level_col,
                             "ForecastError": forecast_error_col, "Obsolescence%": obsolescence_pct_col})
    st.write("SCM KPIs:", {"ComponentAvailability": comp_avail_col, "ProductAvailability": prod_avail_col})
    st.write("Ops KPIs:", {"InboundUtil": inb_util_col, "OutboundUtil": outb_util_col, "PlanAdherence": plan_adherence_col})
    st.write("Purch KPIs:", {"DeliveryReliability": deliv_rel_col, "Rejection%": rej_pct_col,
                             "ComponentObsolete%": comp_obsol_pct_col, "RM Cost%": rm_cost_pct_col})
