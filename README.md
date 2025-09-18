
# Ganga Jamuna — Fresh Connection Dashboard

An interactive Streamlit dashboard for **The Fresh Connection** simulation (Rounds 0–6), covering:

- **Financials**: ROI, Realized Revenues, COGS, Indirect Cost  
- **Sales**: Shelf life, Service level, Forecasting error, Obsolescence %  
- **Supply Chain**: Component availability, Product availability  
- **Operations**: Inbound/Outbound Warehouse Cube Utilization, Production Plan Adherence %  
- **Purchasing**: Delivery Reliability, Rejection %, Component Obsolete %, Raw Material Cost %  

## 🚀 Quick Start (Local)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Put your data files under `./data/` (the app expects these names by default):
- `TFC_0_6.xlsx`
- `FinanceReport (6).xlsx`

## 🌐 Deploy to Streamlit Cloud

1. Push this folder to a GitHub repo.
2. In Streamlit Cloud, set **Main file path** to `app.py`.
3. Make sure your `data/` folder and Excel files are included (or use an external data URL with your own loader).

## 🧠 Notes

- The app **auto-detects column names** using regex, so small naming differences are okay.
- Use the **sidebar filters** to slice by Round, Product, Customer, Component, Supplier.
- Relationship charts include **trendlines** to visualize KPI → Financial impact.
