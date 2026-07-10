"""
Ross Stores - Agentic Procurement Advisor (Streamlit UI)

Run:  streamlit run app.py
Requires GEMINI_API_KEY in .env
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from agents import load_data, run_pipeline

# ----------------------------------------------------------- viz tokens
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
SERIES = ["#2a78d6", "#1baf7a", "#eda100", "#008300"]  # categorical slots 1-4
BLUE_LIGHT = "#9ec5f4"  # sequential step 200 (de-emphasized bars)
BLUE_MAIN = "#2a78d6"
STATUS = {"good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b"}

FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def base_layout(fig: go.Figure, title: str, height: int = 300) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color=INK, family=FONT)),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font=dict(family=FONT, size=12, color=INK_2),
        height=height, margin=dict(l=10, r=10, t=44, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0,
                    font=dict(size=11, color=INK_2), bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor="#ffffff", font=dict(family=FONT, size=12, color=INK)),
    )
    fig.update_xaxes(showgrid=False, linecolor=BASELINE, tickfont=dict(color=MUTED, size=11),
                     title_font=dict(color=MUTED, size=11), zeroline=False)
    fig.update_yaxes(gridcolor=GRID, gridwidth=1, linecolor="rgba(0,0,0,0)",
                     tickfont=dict(color=MUTED, size=11),
                     title_font=dict(color=MUTED, size=11), zeroline=False)
    return fig


# ----------------------------------------------------------- page setup
st.set_page_config(page_title="Ross Procurement Advisor", page_icon="🛒", layout="wide")

st.markdown(
    """
    <style>
      .block-container {padding-top: 2.2rem;}
      div[data-testid="stMetricValue"] {font-size: 1.6rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

data = load_data()
brands = data["brands"]

st.title("🛒 Ross Stores — Agentic Procurement Advisor")
st.caption(
    "Five AI agents evaluate tariffs, geopolitics, demand trends and unit economics "
    "to answer: **should we buy, how much, and when?**"
)

# ----------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Buy request")
    category = st.selectbox("Category", sorted(brands["category"].unique()))
    cat_brands = brands[brands["category"] == category]
    brand_name = st.selectbox("Brand / supplier", cat_brands["brand"].tolist())
    brand_row = cat_brands[cat_brands["brand"] == brand_name].iloc[0]

    st.markdown(
        f"**Origin:** {brand_row['country']}  \n"
        f"**FOB cost:** ${brand_row['fob_unit_cost_usd']:.2f}/unit  \n"
        f"**MOQ:** {brand_row['moq_units']:,} units  \n"
        f"**Lead time:** {brand_row['lead_time_days']} days  \n"
        f"**Quality:** {brand_row['quality_score']}/10"
    )
    st.divider()
    requested_qty = st.number_input("Requested quantity (units)", min_value=1000,
                                    max_value=500_000, value=20_000, step=1000)
    target_margin = st.slider("Target gross margin (%)", 25, 60, 45)
    run = st.button("▶ Run agentic analysis", type="primary", width='stretch')

# ----------------------------------------------------------- context charts
tariff_cat = data["tariffs"][data["tariffs"]["category"] == category].sort_values(
    "current_tariff_pct", ascending=True)
trend_cat = data["trends"][data["trends"]["category"] == category].tail(12)

c1, c2 = st.columns(2)

with c1:
    colors = [BLUE_MAIN if c == brand_row["country"] else BLUE_LIGHT
              for c in tariff_cat["country"]]
    fig = go.Figure(go.Bar(
        x=tariff_cat["current_tariff_pct"], y=tariff_cat["country"],
        orientation="h", marker=dict(color=colors, cornerradius=4),
        width=0.55,
        text=[f"{v:.1f}%" for v in tariff_cat["current_tariff_pct"]],
        textposition="outside", textfont=dict(size=11, color=INK_2),
        hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
    ))
    fig = base_layout(fig, f"Current US tariff on {category} by origin — "
                           f"{brand_row['country']} highlighted", 320)
    fig.update_xaxes(title="tariff %", range=[0, tariff_cat["current_tariff_pct"].max() * 1.18])
    st.plotly_chart(fig, width='stretch')

with c2:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=trend_cat["month"], y=trend_cat["demand_index"],
                             mode="lines", name="Demand index",
                             line=dict(color=SERIES[0], width=2),
                             hovertemplate="%{x} · demand %{y:.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=trend_cat["month"], y=trend_cat["social_buzz_score"],
                             mode="lines", name="Social buzz",
                             line=dict(color=SERIES[1], width=2),
                             hovertemplate="%{x} · buzz %{y:.0f}<extra></extra>"))
    fig = base_layout(fig, f"{category}: demand & social buzz, last 12 months", 320)
    fig.update_xaxes(tickangle=-35)
    st.plotly_chart(fig, width='stretch')

# ----------------------------------------------------------- run pipeline
if run:
    status = st.status("Running the agent team...", expanded=True)

    def progress(msg: str):
        status.write(msg)

    try:
        result = run_pipeline(data, brand_name, int(requested_qty),
                              float(target_margin), progress_cb=progress)
        status.update(label="Analysis complete", state="complete", expanded=False)
    except Exception as e:
        status.update(label="Analysis failed", state="error")
        st.error(f"Pipeline error: {e}")
        st.stop()

    st.session_state["result"] = result

# ----------------------------------------------------------- results
if "result" in st.session_state:
    r = st.session_state["result"]
    dec = r["decision"]

    DECISION_STYLE = {
        "YES":         (STATUS["good"],     "✅", "PROCURE"),
        "PARTIAL_YES": (STATUS["warning"],  "🟡", "PARTIAL BUY"),
        "NO":          (STATUS["critical"], "🛑", "DO NOT PROCURE"),
    }
    color, icon, label = DECISION_STYLE.get(dec.get("decision", "NO"),
                                            DECISION_STYLE["NO"])

    st.markdown(
        f"""
        <div style="border-left:6px solid {color}; background:{SURFACE};
                    border:1px solid rgba(11,11,11,0.10); border-left:6px solid {color};
                    border-radius:8px; padding:16px 20px; margin:8px 0 16px 0;">
          <div style="font-size:1.25rem; font-weight:700; color:{INK};">
            {icon} {label} — {r['brand_row']['brand']} ({r['brand_row']['country']})</div>
          <div style="color:{INK_2}; margin-top:6px;">{dec.get('rationale', '')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Recommended quantity", f"{dec.get('recommended_qty', 0):,} units",
              f"requested {requested_qty:,}", delta_color="off")
    m2.metric("Gross margin", f"{r['finance']['gross_margin_pct']}%",
              f"target {target_margin}%", delta_color="off")
    m3.metric("Geopolitical risk", f"{r['geopolitics'].get('risk_score', '—')}/10",
              r["geopolitics"].get("deal_status", ""), delta_color="off")
    m4.metric("Confidence", str(dec.get("confidence", "—")).title(),
              dec.get("order_timing", ""), delta_color="off")

    lc = r["tariff"]["landed_cost"]
    cc1, cc2 = st.columns(2)

    with cc1:
        parts = [("FOB cost", lc["fob"]), ("Import duty", lc["duty"]),
                 ("Freight", lc["freight"]), ("Handling", lc["handling"])]
        fig = go.Figure()
        for (name, val), col in zip(parts, SERIES):
            fig.add_trace(go.Bar(
                y=["Landed cost"], x=[val], name=name, orientation="h",
                marker=dict(color=col, line=dict(color=SURFACE, width=2)),
                width=0.45,
                hovertemplate=f"{name}: $%{{x:.2f}}<extra></extra>",
            ))
        fig.update_layout(barmode="stack")
        fig = base_layout(fig, f"Landed cost per unit: ${lc['landed']:.2f} "
                               f"(retail ${r['finance']['retail_price']:.2f})", 220)
        fig.update_xaxes(title="USD per unit")
        st.plotly_chart(fig, width='stretch')

    with cc2:
        t = r["tariff"]
        fig = go.Figure(go.Bar(
            x=["Base tariff", "Current tariff"],
            y=[t["base_tariff_pct"], t["current_tariff_pct"]],
            marker=dict(color=[BLUE_LIGHT, BLUE_MAIN], cornerradius=4), width=0.4,
            text=[f"{t['base_tariff_pct']:.1f}%", f"{t['current_tariff_pct']:.1f}%"],
            textposition="outside", textfont=dict(size=12, color=INK_2),
            hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
        ))
        fig = base_layout(fig, f"Tariff shift for {r['brand_row']['country']} "
                               f"{category} (base → current)", 220)
        fig.update_yaxes(range=[0, max(t["current_tariff_pct"], 1) * 1.25], title="tariff %")
        st.plotly_chart(fig, width='stretch')

    st.subheader("Agent reports")
    a1, a2 = st.columns(2)
    with a1:
        with st.expander("🧾 Tariff Agent", expanded=True):
            t = r["tariff"]
            st.markdown(f"**Risk: {str(t.get('tariff_risk', '')).upper()}** · duty is "
                        f"{t.get('duty_share_of_cost_pct', '—')}% of landed cost")
            st.write(t.get("summary", ""))
            for w in t.get("watch_items", []):
                st.markdown(f"- {w}")
        with st.expander("🌍 Geopolitics Agent", expanded=True):
            g = r["geopolitics"]
            st.markdown(f"**Risk score: {g.get('risk_score', '—')}/10** · deal status: "
                        f"{g.get('deal_status', '—')}")
            st.write(g.get("summary", ""))
            st.markdown(f"*6-month outlook:* {g.get('outlook_6_months', '')}")
    with a2:
        with st.expander("📈 Trend Agent", expanded=True):
            tr = r["trend"]
            st.markdown(f"**Demand: {str(tr.get('demand_outlook', '')).upper()}** · trend "
                        f"{tr.get('trend_direction', '—')} · next-quarter category forecast "
                        f"{tr.get('next_quarter_forecast_units', 0):,} units")
            st.write(tr.get("summary", ""))
            st.markdown(f"*Seasonality:* {tr.get('seasonal_note', '')}")
        with st.expander("💰 Finance Agent", expanded=True):
            f = r["finance"]
            st.markdown(f"**{str(f.get('viability', '')).upper()}** · landed "
                        f"${f['landed_cost_per_unit']:.2f} · margin {f['gross_margin_pct']}% "
                        f"· breakeven retail for 45%: ${f['breakeven_retail_for_45pct']:.2f}")
            st.write(f.get("summary", ""))
            for lever in f.get("levers", []):
                st.markdown(f"- {lever}")

    with st.expander("🧠 Chief Decision Agent — conditions & triggers", expanded=True):
        st.markdown(f"**Order timing:** {dec.get('order_timing', '—')}")
        for c in dec.get("conditions", []):
            st.markdown(f"- {c}")
else:
    st.info("Configure a buy request in the sidebar and click **Run agentic analysis**.")
