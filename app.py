
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import re
from pathlib import Path

st.set_page_config(page_title="Ganga Jamuna — VP Dashboard (Fresh Connection)", layout="wide")

# ======== THEME & STYLES ========
st.markdown(
    """
    <style>
    .title {font-size: 38px; font-weight: 800; margin-bottom: 0rem;}
    .subtitle {font-size: 16px; opacity: 0.85; margin-bottom: 1rem;}
    .callout {padding: 1rem; border-radius: 1rem; border: 1px solid rgba(0,0,0,0.06); background: #f8fafc;}
    .kpi {font-size: 13px; opacity: 0.85;}
    .role-card {padding: 1rem; border-radius: 1rem; border: 1px solid rgba(0,0,0,0.06); background: #ffffff;}
    .role-title {font-weight:700; margin-bottom: .4rem;}
    .muted {opacity:.75}
    </style>
    """,
    unsafe_allow_html=True,
)

# ======== FILES ========
DATA_FILES = ["data/TFC_0_6.xlsx","data/FinanceReport (6).xlsx"]

@st.cache_data(show_spinner=False)
def load_excels(files):
    frames, meta = [], []
    for f in files:
        p = Path(f)
        if not p.exists(): 
            continue
        try:
            xls = pd.ExcelFile(p)
            for s in xls.sheet_names:
                try:
                    df = xls.parse(s)
                    df["__source_file__"] = p.name
                    df["__sheet__"] = s
                    frames.append(df)
                    meta.append({"file": p.name, "sheet": s, "rows": len(df), "cols": list(df.columns)})
                except Exception as e:
                    meta.append({"file": p.name, "sheet": s, "error": str(e)})
        except Exception as e:
            meta.append({"file": p.name, "error": str(e)})
    return frames, meta

frames, meta = load_excels(DATA_FILES)
if len(frames) == 0:
    st.error("No data found. Place Excel files under ./data/. Expected: TFC_0_6.xlsx and FinanceReport (6).xlsx")
    st.stop()

def safe_concat(dfs):
    all_cols=set()
    for d in dfs: all_cols.update(list(d.columns))
    cols=list(all_cols)
    outs=[]
    for d in dfs:
        dd=d.copy()
        for c in cols:
            if c not in dd.columns: dd[c]=np.nan
        outs.append(dd[cols])
    return pd.concat(outs, ignore_index=True)

data_all = safe_concat(frames)

# ======== COLUMN MATCHING ========
def match_col(candidates, patterns, default=None):
    if isinstance(patterns, str): patterns=[patterns]
    for pat in patterns:
        rx=re.compile(pat, flags=re.I)
        for c in candidates:
            if rx.search(str(c)): return c
    return default

def selectbox_map(label, detected, options):
    if detected in options:
        idx = options.index(detected)
    else:
        idx = 0
    return st.selectbox(label, options, index=idx)

cands = list(map(str, data_all.columns))

defaults = {
    "round": match_col(cands, [r"^round$", r"week", r"period", r"cycle", r"game\s*round"]),
    "date": match_col(cands, [r"\bdate\b"]),
    "product": match_col(cands, [r"^product$", r"sku", r"item"]),
    "customer": match_col(cands, [r"^customer", r"account", r"client"]),
    "component": match_col(cands, [r"^component", r"part"]),
    "supplier": match_col(cands, [r"^supplier", r"vendor"]),
    # financial
    "ROI": match_col(cands, [r"\bROI\b", r"return\s*on\s*investment"]),
    "Revenue": match_col(cands, [r"realized\s*revenue", r"\brevenue", r"sales\s*revenue"]),
    "COGS": match_col(cands, [r"\bCOGS\b", r"cost\s*of\s*goods"]),
    "Indirect": match_col(cands, [r"indirect\s*cost", r"overhead"]),
    # sales
    "ShelfLife": match_col(cands, [r"attained\s*shelf\s*life", r"avg.*shelf.*life", r"\bshelf\s*life\b"]),
    "ServiceLevel": match_col(cands, [r"achieved\s*service\s*level", r"service\s*level"]),
    "ForecastError": match_col(cands, [r"forecast(ing)?\s*error", r"MAPE", r"bias"]),
    "ObsolescencePct": match_col(cands, [r"obsolesc(en)?ce\s*%?", r"obsolete\s*%"]),
    # SCM
    "CompAvail": match_col(cands, [r"component\s*availability"]),
    "ProdAvail": match_col(cands, [r"product\s*availability"]),
    # Ops
    "InboundUtil": match_col(cands, [r"inbound\s*warehouse.*cube\s*util", r"inbound.*util"]),
    "OutboundUtil": match_col(cands, [r"outbound\s*warehouse.*cube\s*util", r"outbound.*util"]),
    "PlanAdherence": match_col(cands, [r"production\s*plan\s*adherence", r"\bplan\s*adherence"]),
    # Purchasing
    "DeliveryReliability": match_col(cands, [r"delivery\s*reliab", r"component\s*delivery\s*reliab"]),
    "RejectionPct": match_col(cands, [r"rejection\s*%|reject\s*%"]),
    "ComponentObsoletePct": match_col(cands, [r"component\s*obsolete\s*%|obsolete\s*component\s*%"]),
    "RMCostPct": match_col(cands, [r"raw\s*material\s*cost\s*%|RM\s*cost\s*%"]),
}

with st.sidebar:
    st.markdown("### Filters")
    st.caption("Slice the dashboard for presentation")
    with st.expander("KPI Mapper (advanced)"):
        options = ["—"] + cands
        mapper = {}
        for k, v in defaults.items():
            mapper[k] = selectbox_map(k, v if v else "—", options)
            if mapper[k] == "—": mapper[k] = None

    round_col = mapper["round"]; date_col = mapper["date"]
    product_col = mapper["product"]; customer_col = mapper["customer"]
    component_col = mapper["component"]; supplier_col = mapper["supplier"]
    roi_col = mapper["ROI"]; revenue_col = mapper["Revenue"]
    cogs_col = mapper["COGS"]; indirect_col = mapper["Indirect"]
    shelf_life_col = mapper["ShelfLife"]; service_level_col = mapper["ServiceLevel"]
    forecast_error_col = mapper["ForecastError"]; obsolescence_pct_col = mapper["ObsolescencePct"]
    comp_avail_col = mapper["CompAvail"]; prod_avail_col = mapper["ProdAvail"]
    inb_util_col = mapper["InboundUtil"]; outb_util_col = mapper["OutboundUtil"]; plan_adherence_col = mapper["PlanAdherence"]
    deliv_rel_col = mapper["DeliveryReliability"]; rej_pct_col = mapper["RejectionPct"]
    comp_obsol_pct_col = mapper["ComponentObsoletePct"]; rm_cost_pct_col = mapper["RMCostPct"]

    def make_filter(col, label):
        if col and col in data_all.columns:
            vals = sorted(pd.Series(data_all[col]).dropna().unique().tolist())
            return st.multiselect(label, vals, [])
        return []

    rounds = make_filter(round_col, "Round / Week")
    products = make_filter(product_col, "Product")
    customers = make_filter(customer_col, "Customer")
    components = make_filter(component_col, "Component")
    suppliers = make_filter(supplier_col, "Supplier")

def apply_filters(df):
    d = df.copy()
    def filt(c, vals):
        nonlocal d
        if c and c in d.columns and len(vals)>0:
            d = d[d[c].isin(vals)]
    filt(round_col, rounds); filt(product_col, products); filt(customer_col, customers)
    filt(component_col, components); filt(supplier_col, suppliers)
    return d

filtered = apply_filters(data_all)

# ======== HEADER / OVERVIEW ========
st.markdown('<div class="title">Ganga Jamuna — Executive VP Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Fresh Connection • Rounds 0–6 • Dynamic link between Functional and Financial KPIs</div>', unsafe_allow_html=True)

with st.container(border=True):
    c1, c2 = st.columns([2,1])
    with c1:
        st.markdown("**Functional KPIs**")
        st.markdown("- **Purchase** — Delivery Reliability, Rejection %, Component Obsolete %, Raw Material Cost %")
        st.markdown("- **Sales** — Attained Shelf Life, Achieved Service Level, Forecasting Error, Obsolescence %")
        st.markdown("- **Supply Chain** — Component availability, Product availability")
        st.markdown("- **Operations** — Inbound & Outbound Warehouse Cube Utilization, Production Plan Adherence %")
    with c2:
        st.markdown("**Financial KPIs**")
        st.markdown("1. ROI  \n2. Realized Revenues  \n3. Cost of Goods Sold (COGS)  \n4. Indirect Cost")

# ======== IMPACT MATRIX ========
def build_impact_matrix(df):
    cols_map = {
        "ROI": roi_col, "Revenues": revenue_col, "COGS": cogs_col, "Indirect": indirect_col,
        "Service Level": service_level_col, "Shelf Life": shelf_life_col,
        "Forecast Error": forecast_error_col, "Obsolescence %": obsolescence_pct_col,
        "Component Avail": comp_avail_col, "Product Avail": prod_avail_col,
        "Inbound Util": inb_util_col, "Outbound Util": outb_util_col, "Plan Adherence %": plan_adherence_col,
        "Delivery Reliability": deliv_rel_col, "Rejection %": rej_pct_col,
        "Component Obsolete %": comp_obsol_pct_col, "RM Cost %": rm_cost_pct_col
    }
    use = {k:v for k,v in cols_map.items() if v and v in df.columns}
    if len(use) < 2: return None, use
    num = df[list(use.values())].apply(pd.to_numeric, errors="coerce")
    corr = num.corr()
    corr.index = [k for k,v in use.items()]; corr.columns = [k for k,v in use.items()]
    return corr, use

corr, used_cols = build_impact_matrix(filtered)
st.markdown("### Impact Matrix — Functional ↔ Financial KPIs (correlation)")
if corr is None:
    st.info("Not enough numeric columns detected to build impact matrix. Map KPI columns in the sidebar if needed.")
else:
    fig = px.imshow(corr.round(2), text_auto=True, aspect="auto",
                    title="Correlation heatmap (higher absolute values = stronger linear relationship)")
    st.plotly_chart(fig, use_container_width=True)

# ======== TABS ========
tab_fin, tab_sales, tab_scm, tab_ops, tab_purch = st.tabs(
    ["🏦 Financials", "🛒 Sales", "🔗 Supply Chain", "🏭 Operations", "📦 Purchasing"]
)

def kpi_row(metrics):
    cols = st.columns(len(metrics))
    for i, (label, value, hint) in enumerate(metrics):
        with cols[i]:
            with st.container(border=True):
                st.caption(label)
                if value is None or (isinstance(value, float) and np.isnan(value)):
                    st.metric(label="", value="—")
                else:
                    st.metric(label="", value=f"{value:,.2f}" if isinstance(value, (int,float)) else str(value))
                if hint: st.caption(f":gray[{hint}]")

def line_or_bar(df, x, y, title, kind="line"):
    if not x or not y or x not in df.columns or y not in df.columns: 
        st.info(f"Missing data for: {title}"); return
    d = df[[x,y]].apply(pd.to_numeric, errors="ignore").dropna()
    if len(d)==0: st.info(f"No rows for: {title}"); return
    d = d.sort_values(by=x)
    fig = px.line(d, x=x, y=y, markers=True, title=title) if kind=="line" else px.bar(d, x=x, y=y, title=title)
    st.plotly_chart(fig, use_container_width=True)

def scatter_rel(df, x, y, color=None, size=None, title=""):
    if not x or not y or x not in df.columns or y not in df.columns: 
        st.info(f"Missing data for: {title}"); return
    cols = [x,y] + [c for c in [color,size] if c and c in df.columns]
    d = df[cols].dropna()
    if len(d)==0: st.info(f"No rows for: {title}"); return
    fig = px.scatter(d, x=x, y=y, color=color if color in d.columns else None,
                     size=size if size in d.columns else None, trendline="ols", title=title)
    st.plotly_chart(fig, use_container_width=True)

# FINANCIALS
with tab_fin:
    st.subheader("Financial KPIs")
    fin = []
    if roi_col: fin.append(("ROI (avg)", filtered[roi_col].astype(float).dropna().mean() if roi_col in filtered.columns else None, "Average"))
    if revenue_col: fin.append(("Realized Revenues (sum)", filtered[revenue_col].astype(float).dropna().sum() if revenue_col in filtered.columns else None, "Total"))
    if cogs_col: fin.append(("COGS (sum)", filtered[cogs_col].astype(float).dropna().sum() if cogs_col in filtered.columns else None, "Total"))
    if indirect_col: fin.append(("Indirect Cost (sum)", filtered[indirect_col].astype(float).dropna().sum() if indirect_col in filtered.columns else None, "Total"))
    if len(fin)>0: kpi_row(fin)
    xaxis = round_col if round_col else date_col
    st.markdown("#### Trends by Round")
    line_or_bar(filtered, xaxis, roi_col, "ROI by Round", kind="line")
    line_or_bar(filtered, xaxis, revenue_col, "Realized Revenues by Round", kind="bar")
    line_or_bar(filtered, xaxis, cogs_col, "COGS by Round", kind="bar")
    line_or_bar(filtered, xaxis, indirect_col, "Indirect Cost by Round", kind="bar")
    st.markdown("#### Relationships")
    scatter_rel(filtered, revenue_col, roi_col, color=product_col or customer_col, title="Revenue vs ROI")
    scatter_rel(filtered, cogs_col, roi_col, color=supplier_col or product_col, title="COGS vs ROI")
    if indirect_col: scatter_rel(filtered, indirect_col, roi_col, color=customer_col, title="Indirect Cost vs ROI")

# SALES
with tab_sales:
    st.subheader("VP Sales — KPI to Financial impact")
    cards=[]
    if service_level_col: cards.append(("Service Level (avg)", filtered[service_level_col].astype(float).dropna().mean(), None))
    if shelf_life_col: cards.append(("Attained Shelf Life (avg)", filtered[shelf_life_col].astype(float).dropna().mean(), None))
    if forecast_error_col: cards.append(("Forecast Error (avg)", filtered[forecast_error_col].astype(float).dropna().mean(), None))
    if obsolescence_pct_col: cards.append(("Obsolescence % (avg)", filtered[obsolescence_pct_col].astype(float).dropna().mean(), None))
    if len(cards)>0: kpi_row(cards)
    if customer_col and (roi_col or revenue_col):
        st.markdown("#### Customer Prioritization (Contribution)")
        cols = [customer_col] + [c for c in [roi_col, revenue_col] if c]
        d = filtered[cols].dropna()
        if len(d)>0 and (roi_col and revenue_col):
            agg = d.groupby(customer_col, as_index=False).agg({roi_col:"mean", revenue_col:"sum"})
            agg.columns=[customer_col, "Avg ROI", "Total Revenue"]
            st.dataframe(agg.sort_values("Total Revenue", ascending=False))
            fig = px.scatter(agg, x="Total Revenue", y="Avg ROI", size="Total Revenue", hover_name=customer_col,
                             title="Customers — ROI vs Revenue")
            st.plotly_chart(fig, use_container_width=True)
    scatter_rel(filtered, service_level_col, roi_col, color=customer_col, title="Service Level vs ROI (by Customer)")
    scatter_rel(filtered, shelf_life_col, revenue_col, color=product_col, title="Shelf Life vs Revenue (by Product)")
    scatter_rel(filtered, forecast_error_col, roi_col, color=customer_col, title="Forecast Error vs ROI")
    scatter_rel(filtered, obsolescence_pct_col, revenue_col, color=product_col, title="Obsolescence % vs Revenue")

# SUPPLY CHAIN
with tab_scm:
    st.subheader("VP Supply Chain — Availability & Financials")
    xaxis = round_col if round_col else date_col
    if comp_avail_col: line_or_bar(filtered, xaxis, comp_avail_col, "Component Availability by Round")
    if prod_avail_col: line_or_bar(filtered, xaxis, prod_avail_col, "Product Availability by Round")
    if component_col and (roi_col or revenue_col):
        st.markdown("#### Components — Prioritize by ROI / Revenue")
        cols=[component_col] + [c for c in [roi_col, revenue_col] if c]
        d = filtered[cols].dropna()
        if len(d)>0 and (roi_col and revenue_col):
            agg = d.groupby(component_col, as_index=False).agg({roi_col:"mean", revenue_col:"sum"})
            agg.columns=[component_col, "Avg ROI", "Total Revenue"]
            st.dataframe(agg.sort_values("Total Revenue", ascending=False))
            fig = px.scatter(agg, x="Total Revenue", y="Avg ROI", size="Total Revenue", hover_name=component_col,
                             title="Components — ROI vs Revenue")
            st.plotly_chart(fig, use_container_width=True)
    if product_col and (roi_col or revenue_col):
        st.markdown("#### Products — Prioritize by ROI / Revenue")
        cols=[product_col] + [c for c in [roi_col, revenue_col] if c]
        d = filtered[cols].dropna()
        if len(d)>0 and (roi_col and revenue_col):
            agg = d.groupby(product_col, as_index=False).agg({roi_col:"mean", revenue_col:"sum"})
            agg.columns=[product_col, "Avg ROI", "Total Revenue"]
            st.dataframe(agg.sort_values("Total Revenue", ascending=False))
            fig = px.scatter(agg, x="Total Revenue", y="Avg ROI", size="Total Revenue", hover_name=product_col,
                             title="Products — ROI vs Revenue")
            st.plotly_chart(fig, use_container_width=True)

# OPERATIONS
with tab_ops:
    st.subheader("VP Operations — Warehouses & Production")
    cards=[]
    if inb_util_col: cards.append(("Inbound WH Util (avg)", filtered[inb_util_col].astype(float).dropna().mean(), None))
    if outb_util_col: cards.append(("Outbound WH Util (avg)", filtered[outb_util_col].astype(float).dropna().mean(), None))
    if plan_adherence_col: cards.append(("Plan Adherence % (avg)", filtered[plan_adherence_col].astype(float).dropna().mean(), None))
    if len(cards)>0: kpi_row(cards)
    scatter_rel(filtered, inb_util_col, cogs_col, color=None, title="Inbound WH Util vs COGS")
    scatter_rel(filtered, outb_util_col, cogs_col, color=None, title="Outbound WH Util vs COGS")
    scatter_rel(filtered, plan_adherence_col, roi_col, color=None, title="Production Plan Adherence vs ROI")

# PURCHASING
with tab_purch:
    st.subheader("VP Purchasing — Supplier Performance & Financials")
    cards=[]
    if deliv_rel_col: cards.append(("Delivery Reliability (avg)", filtered[deliv_rel_col].astype(float).dropna().mean(), None))
    if rej_pct_col: cards.append(("Rejection % (avg)", filtered[rej_pct_col].astype(float).dropna().mean(), None))
    if comp_obsol_pct_col: cards.append(("Component Obsolete % (avg)", filtered[comp_obsol_pct_col].astype(float).dropna().mean(), None))
    if rm_cost_pct_col: cards.append(("Raw Material Cost % (avg)", filtered[rm_cost_pct_col].astype(float).dropna().mean(), None))
    if len(cards)>0: kpi_row(cards)
    if supplier_col and (roi_col or cogs_col or revenue_col):
        st.markdown("#### Supplier Impact Summary")
        cols=[supplier_col] + [c for c in [roi_col, cogs_col, revenue_col] if c]
        d = filtered[cols].dropna(how="all")
        if len(d)>0:
            agg_map={}
            if roi_col: agg_map[roi_col]="mean"
            if cogs_col: agg_map[cogs_col]="sum"
            if revenue_col: agg_map[revenue_col]="sum"
            agg = d.groupby(supplier_col, as_index=False).agg(agg_map)
            rename={}
            if roi_col: rename[roi_col]="Avg ROI"
            if cogs_col: rename[cogs_col]="Total COGS"
            if revenue_col: rename[revenue_col]="Total Revenue"
            agg = agg.rename(columns=rename)
            st.dataframe(agg.sort_values(list(agg.columns)[-1], ascending=False))
            x = "Total COGS" if "Total COGS" in agg.columns else ("Total Revenue" if "Total Revenue" in agg.columns else None)
            y = "Avg ROI" if "Avg ROI" in agg.columns else None
            if x and y:
                fig = px.scatter(agg, x=x, y=y, size=x, hover_name=supplier_col, title="Suppliers — Financial Impact")
                st.plotly_chart(fig, use_container_width=True)
    scatter_rel(filtered, deliv_rel_col, roi_col, color=supplier_col, title="Delivery Reliability vs ROI (by Supplier)")
    scatter_rel(filtered, rej_pct_col, roi_col, color=supplier_col, title="Rejection % vs ROI (by Supplier)")
    scatter_rel(filtered, rm_cost_pct_col, roi_col, color=supplier_col, title="RM Cost % vs ROI (by Supplier)")

# META
with st.expander("📄 Data sources & column mapping"):
    st.write(pd.DataFrame(meta))
    st.json({k: v for k,v in defaults.items()})
    st.markdown("**Current mapping (after overrides):**")
    st.json({
        "round": round_col, "date": date_col, "product": product_col, "customer": customer_col,
        "component": component_col, "supplier": supplier_col, "ROI": roi_col, "Revenue": revenue_col,
        "COGS": cogs_col, "Indirect": indirect_col, "ShelfLife": shelf_life_col, "ServiceLevel": service_level_col,
        "ForecastError": forecast_error_col, "Obsolescence%": obsolescence_pct_col, "ComponentAvail": comp_avail_col,
        "ProductAvail": prod_avail_col, "InboundUtil": inb_util_col, "OutboundUtil": outb_util_col,
        "PlanAdherence%": plan_adherence_col, "DeliveryReliability": deliv_rel_col, "Rejection%": rej_pct_col,
        "ComponentObsolete%": comp_obsol_pct_col, "RMCost%": rm_cost_pct_col
    })
