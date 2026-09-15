"""
Store Sales Analytics & Forecasting — Streamlit Dashboard
Reads the pre-aggregated star-schema / KPI tables already produced by the
ETL pipeline (etl/phase3_kpi_reporting.py, etl/phase4_forecasting.py,
etl/phase5_powerbi_export.py) — no heavy computation happens here, so the
app starts and reacts fast, which matters for a live demo.

Run:
    pip install streamlit plotly
    streamlit run dashboard/app.py
"""

from pathlib import Path

import json
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------- paths ---
REPO_ROOT = Path(__file__).resolve().parent.parent
DASH_DATA = REPO_ROOT / "dashboard" / "data"
REPORTS = REPO_ROOT / "reports"
PROCESSED = REPO_ROOT / "data" / "processed"

# ------------------------------------------------------------- palette ---
# Validated categorical palette (see dataviz skill / references/palette.md)
BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
SURFACE = "#fcfcfb"
GOOD = "#0ca30c"

PLOTLY_LAYOUT = dict(
    paper_bgcolor=SURFACE,
    plot_bgcolor=SURFACE,
    font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif", color=INK, size=13),
    margin=dict(l=10, r=10, t=40, b=10),
    xaxis=dict(gridcolor=GRID, zerolinecolor=GRID, tickfont=dict(color=INK_MUTED)),
    yaxis=dict(gridcolor=GRID, zerolinecolor=GRID, tickfont=dict(color=INK_MUTED)),
)


# ------------------------------------------------------------- loaders ---
@st.cache_data
def load_kpi_summary():
    df = pd.read_csv(REPORTS / "kpi_summary.csv")
    return dict(zip(df["KPI"], df["Value"]))


@st.cache_data
def load_monthly():
    df = pd.read_csv(PROCESSED / "kpi_monthly.csv", parse_dates=["date"])
    return df.sort_values("date")


@st.cache_data
def load_model_comparison():
    with open(REPORTS / "model_comparison.json") as f:
        d = json.load(f)
    df = pd.DataFrame({"model": list(d.keys()), "rmsle": list(d.values())})
    return df.sort_values("rmsle", ascending=False)  # ascending bars, best on top


@st.cache_data
def load_validation():
    df = pd.read_parquet(PROCESSED / "val_predictions.parquet")
    daily = df.groupby("date", as_index=False).agg(
        actual=("sales", "sum"), forecast=("pred_lightgbm", "sum")
    )
    return daily.sort_values("date")


@st.cache_data
def load_store_kpi():
    return pd.read_csv(PROCESSED / "kpi_store.csv")


@st.cache_data
def load_category_kpi():
    return pd.read_csv(PROCESSED / "kpi_category.csv").sort_values(
        "share_pct", ascending=False
    )


@st.cache_data
def load_feature_importance():
    return pd.read_csv(REPORTS / "feature_importance.csv").sort_values(
        "importance", ascending=True
    )


# ------------------------------------------------------------- page ------
st.set_page_config(
    page_title="Store Sales Analytics & Forecasting",
    page_icon="📈",
    layout="wide",
)

st.markdown(
    f"<h2 style='color:{INK};margin-bottom:0'>Store Sales Analytics & Forecasting</h2>"
    f"<p style='color:{INK_SECONDARY};margin-top:2px'>"
    "Corporación Favorita (Ecuador) · 54 Filialen · 33 Produktkategorien · 2013–2017"
    "</p>",
    unsafe_allow_html=True,
)

kpi = load_kpi_summary()
total_sales = float(kpi["Total Sales (2013-08/2017)"])
weekend_uplift = float(kpi["Weekend vs Weekday Sales Uplift %"])
holiday_uplift = float(kpi["National Holiday Sales Uplift %"])

model_df = load_model_comparison()
best_rmsle = model_df["rmsle"].min()
best_baseline = model_df[model_df["model"] != "LightGBM (engineered features)"]["rmsle"].min()
improvement_pct = (best_baseline - best_rmsle) / best_baseline * 100

c1, c2, c3, c4 = st.columns(4)
c1.metric("Absatzmenge gesamt (2013–2017)", f"{total_sales / 1e9:.2f} Mrd Einheiten")
c2.metric("Bestes Modell: LightGBM", f"RMSLE {best_rmsle:.3f}", f"-{improvement_pct:.1f}% vs. beste Baseline")
c3.metric("Wochenend-Uplift", f"+{weekend_uplift:.1f}%")
c4.metric("Feiertags-Uplift", f"+{holiday_uplift:.1f}%")

st.divider()

# --------------------------------------------------- row: trend + model ---
row1_left, row1_right = st.columns(2)

with row1_left:
    st.subheader("Absatztrend (monatlich)")
    monthly = load_monthly()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly["date"], y=monthly["total_sales"],
        mode="lines", line=dict(color=BLUE, width=2),
        fill="tozeroy", fillcolor="rgba(42,120,214,0.08)",
        hovertemplate="%{x|%b %Y}<br>%{y:,.0f} Einheiten<extra></extra>",
    ))
    fig.update_layout(**PLOTLY_LAYOUT, height=320, showlegend=False)
    fig.update_yaxes(title=None, tickformat=".2s")
    st.plotly_chart(fig, width='stretch')

with row1_right:
    st.subheader("Modellvergleich (RMSLE, niedriger = besser)")
    colors = [GOOD if m.startswith("LightGBM") else BLUE for m in model_df["model"]]
    labels = [f"{v:.3f}" + ("  ✓ gewählt" if m.startswith("LightGBM") else "") for m, v in zip(model_df["model"], model_df["rmsle"])]
    fig = go.Figure(go.Bar(
        x=model_df["rmsle"], y=model_df["model"], orientation="h",
        marker_color=colors, text=labels, textposition="outside",
        hovertemplate="%{y}: %{x:.3f}<extra></extra>",
    ))
    fig.update_layout(**PLOTLY_LAYOUT, height=320, showlegend=False)
    fig.update_xaxes(title="RMSLE", range=[0, model_df["rmsle"].max() * 1.25])
    fig.update_yaxes(title=None)
    st.plotly_chart(fig, width='stretch')

# --------------------------------------------- row: validation + stores ---
row2_left, row2_right = st.columns(2)

with row2_left:
    st.subheader("Ist vs. Prognose (Validierungsfenster, 16 Tage)")
    val = load_validation()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=val["date"], y=val["actual"], mode="lines+markers",
                              name="Tatsächlich", line=dict(color=BLUE, width=2)))
    fig.add_trace(go.Scatter(x=val["date"], y=val["forecast"], mode="lines+markers",
                              name="Prognose (LightGBM)", line=dict(color=ORANGE, width=2, dash="dash")))
    fig.update_layout(**PLOTLY_LAYOUT, height=320,
                       legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    fig.update_yaxes(title=None, tickformat=".2s")
    st.plotly_chart(fig, width='stretch')

with row2_right:
    st.subheader("Filialen-Ranking (Top 10 nach Absatzmenge)")
    stores = load_store_kpi()
    store_types = ["Alle"] + sorted(stores["type"].dropna().unique().tolist())
    selected_type = st.selectbox("Filialtyp", store_types, key="store_type_filter")
    filtered = stores if selected_type == "Alle" else stores[stores["type"] == selected_type]
    top10 = filtered.nlargest(10, "total_sales").sort_values("total_sales")
    top10_labels = top10["store_nbr"].astype(str) + " · " + top10["city"]
    fig = go.Figure(go.Bar(
        x=top10["total_sales"], y=top10_labels, orientation="h",
        marker_color=BLUE, text=[f"{v/1e6:.1f} Mio." for v in top10["total_sales"]],
        textposition="outside",
        hovertemplate="Filiale %{y}<br>%{x:,.0f} Einheiten<extra></extra>",
    ))
    fig.update_layout(**PLOTLY_LAYOUT, height=320, showlegend=False)
    fig.update_xaxes(title=None, tickformat=".2s")
    fig.update_yaxes(title=None)
    st.plotly_chart(fig, width='stretch')

st.divider()

# --------------------------------------------------------- category share --
st.subheader("Absatzanteil nach Produktkategorie")
cat = load_category_kpi()
top_n = 8
top_cats = cat.head(top_n).copy()
other_share = cat["share_pct"].iloc[top_n:].sum()
if other_share > 0:
    top_cats = pd.concat([
        top_cats,
        pd.DataFrame([{"family": "ANDERE (25 Kategorien)", "share_pct": other_share}]),
    ])
top_cats = top_cats.sort_values("share_pct")
fig = go.Figure(go.Bar(
    x=top_cats["share_pct"], y=top_cats["family"], orientation="h",
    marker_color=BLUE, text=[f"{v:.1f}%" for v in top_cats["share_pct"]],
    textposition="outside",
    hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
))
fig.update_layout(**PLOTLY_LAYOUT, height=340, showlegend=False)
fig.update_xaxes(title="Anteil an der Gesamtabsatzmenge (%)", range=[0, top_cats["share_pct"].max() * 1.2])
fig.update_yaxes(title=None)
st.plotly_chart(fig, width='stretch')

with st.expander("Details: wichtigste Merkmale für das Prognosemodell"):
    fi = load_feature_importance().tail(10)
    fig = go.Figure(go.Bar(
        x=fi["importance"], y=fi["feature"], orientation="h",
        marker_color=BLUE,
        hovertemplate="%{y}: %{x}<extra></extra>",
    ))
    fig.update_layout(**PLOTLY_LAYOUT, height=340, showlegend=False)
    fig.update_xaxes(title="Wichtigkeit (LightGBM)")
    fig.update_yaxes(title=None)
    st.plotly_chart(fig, width='stretch')

st.caption(
    "Datenquelle: Kaggle „Store Sales – Time Series Forecasting\" · "
    "ETL-Pipeline: pandas, LightGBM · Star-Schema exportiert für BI-Tools · "
    "Quality-Checks: pytest (siehe tests/test_data_quality.py)"
)
