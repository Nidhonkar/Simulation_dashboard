
# Ganga Jamuna — VP Dashboard (Fresh Connection)

A presentation-grade, **role-based** Streamlit app linking **Functional KPIs** to **Financial KPIs** for *The Fresh Connection* (Rounds 0–6).

## Folder Tree
```
tfc_dashboard_full/
├─ app.py
├─ requirements.txt
├─ .streamlit/
│  └─ config.toml
├─ data/
│  ├─ TFC_0_6.xlsx
│  └─ FinanceReport (6).xlsx
└─ README.md
```

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```
## Deploy (Streamlit Cloud)
- Push this folder to GitHub
- Set **Main file** to `app.py`
- Keep `data/` in the repo or adapt the loader
