"""
Commercial Cockpit (B8) - Executive / Pricing / Procurement / Retail.

Streamlit front end over the monthly star schema written by
`etl/phase13_commercial_export.py`. The arithmetic and the provenance labelling live in
`dashboard/cockpit_data.py` so they can be tested without a browser; this file is the
drawing.

Two rules shape every chart here:

  * **Provenance is rendered, not remembered.** Every title comes from `label_for()`, which
    derives its suffix from the declared tier - "(simulated)", "(observational estimate)" or
    nothing for real measures. A measure with no declaration raises instead of appearing.
  * **One axis per chart.** Where two measures of different scale belong together (revenue and
    margin %, spend and service level) they get two charts, never two y-scales.

Run:  streamlit run dashboard/commercial_app.py
"""
import os
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cockpit_data as cd  # noqa: E402

# Validated categorical slots 1-3 and the diverging pair (see the project's viz palette).
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
POS, NEG, NEUTRAL = "#2a78d6", "#e34948", "#f0efec"
INK, INK_2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, BASELINE, SURFACE = "#e1e0d9", "#c3c2b7", "#fcfcfb"

LAYOUT = dict(
    paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
    font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif', color=INK_2, size=13),
    margin=dict(l=8, r=8, t=8, b=8), hoverlabel=dict(font_size=12),
)

st.set_page_config(page_title="Commercial Cockpit", layout="wide")


def style(fig, height=320, showlegend=False):
    fig.update_layout(**LAYOUT, height=height, showlegend=showlegend,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    fig.update_xaxes(gridcolor=GRID, linecolor=BASELINE, zerolinecolor=BASELINE,
                     tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, linecolor=BASELINE, zerolinecolor=BASELINE,
                     tickfont=dict(color=MUTED))
    return fig


def line(x, y, color, hover):
    fig = go.Figure(go.Scatter(x=x, y=y, mode="lines", line=dict(color=color, width=2),
                               hovertemplate=hover + "<extra></extra>"))
    return style(fig)


def bar(y_labels, values, color, hover, text=None, height=380):
    fig = go.Figure(go.Bar(x=values, y=y_labels, orientation="h", marker_color=color,
                           text=text, textposition="outside",
                           textfont=dict(color=INK_2),
                           hovertemplate=hover + "<extra></extra>"))
    return style(fig, height=height)


@st.cache_data
def load():
    return cd.load_model()


fact, proc, families, suppliers, provenance = load()
L = lambda m, t: cd.label_for(m, t, provenance)   # noqa: E731

st.title("Commercial Cockpit")
st.caption("Corporación Favorita sales history with a documented commercial simulation layer. "
           "Quantities and promotion occurrence are real; every monetary figure is simulated — "
           "each title below says which. See docs/19 and docs/26.")

months = sorted(fact["month"].unique())
c1, c2 = st.columns([2, 3])
period = c1.select_slider("Period", options=months, value=(months[0], months[-1]),
                          format_func=lambda d: pd.Timestamp(d).strftime("%Y-%m"))
groups = ["All"] + sorted(families["sourcing_group"].dropna().unique().tolist())
group = c2.selectbox("Sourcing group", groups)

mask = (fact["month"] >= period[0]) & (fact["month"] <= period[1])
pmask = (proc["month"] >= period[0]) & (proc["month"] <= period[1])
if group != "All":
    keep = set(families.loc[families["sourcing_group"] == group, "family"])
    mask &= fact["family"].isin(keep)
    pmask &= proc["family"].isin(keep)
f, p = fact[mask], proc[pmask]

executive, pricing, procurement, retail = st.tabs(
    ["Executive", "Pricing", "Procurement", "Retail"])

# ------------------------------------------------------------------ Executive --
with executive:
    k = cd.executive_kpis(f, p)
    cols = st.columns(6)
    cols[0].metric(L("revenue_sim", "Revenue"), f"{k['revenue_sim']/1e9:.2f}bn USD")
    cols[1].metric(L("gross_margin_sim", "Gross margin"), f"{k['gross_margin_pct']:.1f}%")
    cols[2].metric(L("markdown_value_sim", "Markdown"), f"{k['markdown_pct']:.1f}% of list")
    cols[3].metric(L("po_value_sim", "Procurement spend"), f"{k['po_value_sim']/1e9:.2f}bn USD")
    cols[4].metric(L("fulfilled_units_sim", "Demand fulfilment"), f"{k['fulfillment_pct']:.1f}%")
    cols[5].metric(L("stockout_days_sim", "OOS day rate"), f"{k['oos_day_rate_pct']:.2f}%")

    m = cd.by_month(f)
    left, right = st.columns(2)
    with left:
        st.subheader(L("revenue_sim", "Monthly revenue"))
        st.plotly_chart(line(m["month"], m["revenue_sim"], SERIES[0],
                             "%{x|%b %Y}<br>%{y:,.0f} USD"), use_container_width=True)
    with right:
        # a second chart rather than a second y-axis
        st.subheader(L("gross_margin_sim", "Monthly gross margin %"))
        st.plotly_chart(line(m["month"], m["gross_margin_pct"], SERIES[1],
                             "%{x|%b %Y}<br>%{y:.1f}%"), use_container_width=True)

    fam = cd.by_family(f, families).nlargest(10, "revenue_sim").sort_values("revenue_sim")
    st.subheader(L("revenue_sim", "Top 10 families by revenue"))
    st.plotly_chart(bar(fam["family"], fam["revenue_sim"], SERIES[0],
                        "%{y}<br>%{x:,.0f} USD",
                        text=[f"{v/1e6:.0f}M" for v in fam["revenue_sim"]]),
                    use_container_width=True)

# -------------------------------------------------------------------- Pricing --
with pricing:
    fam = cd.by_family(f, families)
    st.subheader(L("gross_margin_sim", "Gross margin % by family"))
    d = fam.sort_values("gross_margin_pct")
    st.plotly_chart(bar(d["family"], d["gross_margin_pct"], SERIES[0],
                        "%{y}<br>%{x:.1f}%", height=640), use_container_width=True)

    left, right = st.columns(2)
    with left:
        st.subheader("Markdown against margin")
        fig = go.Figure(go.Scatter(
            x=fam["markdown_pct"], y=fam["gross_margin_pct"], mode="markers",
            marker=dict(size=10, color=SERIES[0], line=dict(width=2, color=SURFACE)),
            text=fam["family"],
            hovertemplate="%{text}<br>markdown %{x:.1f}%<br>margin %{y:.1f}%<extra></extra>"))
        fig.update_xaxes(title=dict(text="Markdown % of list (simulated)",
                                    font=dict(color=MUTED)))
        fig.update_yaxes(title=dict(text="Gross margin % (simulated)", font=dict(color=MUTED)))
        st.plotly_chart(style(fig, height=380), use_container_width=True)
    with right:
        st.subheader("Promotion uplift against its break-even requirement")
        g = fam.dropna(subset=["break_even_uplift_pct_sim"]).copy()
        g["gap"] = (g["estimated_observational_uplift_pct"] - g["break_even_uplift_pct_sim"])
        g = g.sort_values("gap")
        st.plotly_chart(bar(g["family"], g["gap"],
                            [POS if v > 0 else NEG for v in g["gap"]],
                            "%{y}<br>%{x:+.1f} pp vs break-even", height=380),
                        use_container_width=True)
        st.caption("Positive means the observed uplift exceeded the scenario break-even "
                   "requirement — not that the promotion was profitable (docs/24 §5).")

# ---------------------------------------------------------------- Procurement --
with procurement:
    sup = cd.by_supplier(p, suppliers)
    left, right = st.columns(2)
    with left:
        st.subheader(L("po_value_sim", "Spend by supplier"))
        d = sup.sort_values("po_value_sim")
        st.plotly_chart(bar(d["supplier_id"], d["po_value_sim"], SERIES[0],
                            "%{y}<br>%{x:,.0f} USD", height=420), use_container_width=True)
    with right:
        st.subheader(L("on_time_lines_sim", "Service level by supplier"))
        d = sup.sort_values("on_time_pct")
        fig = go.Figure()
        fig.add_bar(y=d["supplier_id"], x=d["on_time_pct"], orientation="h", name="On time",
                    marker_color=SERIES[0], hovertemplate="%{y}<br>on time %{x:.1f}%<extra></extra>")
        fig.add_bar(y=d["supplier_id"], x=d["in_full_pct"], orientation="h", name="In full",
                    marker_color=SERIES[1], hovertemplate="%{y}<br>in full %{x:.1f}%<extra></extra>")
        fig.update_layout(barmode="group", bargap=0.25)
        st.plotly_chart(style(fig, height=420, showlegend=True), use_container_width=True)

    st.subheader("The sourcing trade-off: price against reliability")
    fig = go.Figure(go.Scatter(
        x=sup["price_factor"], y=100 * sup["late_rate"], mode="markers+text",
        marker=dict(size=11, color=SERIES[0], line=dict(width=2, color=SURFACE)),
        text=sup["supplier_id"], textposition="top center", textfont=dict(color=MUTED, size=11),
        customdata=sup["supplier_name"],
        hovertemplate="%{customdata}<br>price factor %{x:.3f}<br>late %{y:.0f}%<extra></extra>"))
    fig.update_xaxes(title=dict(text="Purchase price factor vs standard cost (simulated)",
                                font=dict(color=MUTED)))
    fig.update_yaxes(title=dict(text="Late deliveries % (simulated)", font=dict(color=MUTED)))
    st.plotly_chart(style(fig, height=380), use_container_width=True)
    st.caption("The scenario was built with this tension in it: cheaper vendors are the less "
               "reliable ones (docs/20 §4).")

# --------------------------------------------------------------------- Retail --
with retail:
    fam = cd.by_family(f, families)
    left, right = st.columns(2)
    with left:
        st.subheader(L("stockout_days_sim", "Highest OOS day rate"))
        d = fam.nlargest(10, "oos_day_rate_pct").sort_values("oos_day_rate_pct")
        st.plotly_chart(bar(d["family"], d["oos_day_rate_pct"], SERIES[0],
                            "%{y}<br>%{x:.2f}% of days"), use_container_width=True)
    with right:
        st.subheader(L("fulfilled_units_sim", "Lowest demand fulfilment"))
        d = fam.nsmallest(10, "fulfillment_pct").sort_values("fulfillment_pct",
                                                             ascending=False)
        st.plotly_chart(bar(d["family"], d["fulfillment_pct"], SERIES[0],
                            "%{y}<br>%{x:.2f}%"), use_container_width=True)

    m = cd.by_month(f)
    st.subheader(L("avg_inventory_value_sim", "Monthly average inventory value"))
    st.plotly_chart(line(m["month"], m["avg_inventory_value_sim"], SERIES[0],
                         "%{x|%b %Y}<br>%{y:,.0f} USD"), use_container_width=True)

# ----------------------------------------------------------------- provenance --
with st.expander("Model & provenance — what every measure rests on"):
    st.dataframe(provenance, use_container_width=True, hide_index=True)
    st.caption("Titles on this page are generated from this table. A measure with no entry "
               "raises rather than being displayed (rule P-06, docs/19 §2).")
