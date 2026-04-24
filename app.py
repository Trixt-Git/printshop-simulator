import streamlit as st
import plotly.express as px
import pandas as pd
from trading_card_generate_dataset import generate_dataset

# ── PAGE CONFIG ───────────────────────────────────────────────────────────
st.set_page_config(page_title="Print Shop Simulator", layout="wide")

st.title("Trading Card Print Shop — Live Simulator")
st.caption("Move any slider to rerun the simulation and see the system respond.")

# ── SIDEBAR CONTROLS ──────────────────────────────────────────────────────
st.sidebar.header("Simulation Controls")

st.sidebar.subheader("Press Age Factors")
st.sidebar.caption("Fleet baseline: 1.15 (best) → 1.50 (worst). No press in this fleet is at 1.0.")
age_2190 = st.sidebar.slider("2190 KBA106 — Perfecting",  1.0, 2.0, 1.15, step=0.05)
age_2160 = st.sidebar.slider("2160 840 Komori — Sheetfed", 1.0, 2.0, 1.30, step=0.05)
age_2150 = st.sidebar.slider("2150 640 Komori — Sheetfed", 1.0, 2.0, 1.25, step=0.05)
age_2500 = st.sidebar.slider("2500 640 Komori — Sheetfed", 1.0, 2.0, 1.20, step=0.05)
age_2330 = st.sidebar.slider("2330 640 Komori — Sheetfed", 1.0, 2.0, 1.20, step=0.05)
age_2060 = st.sidebar.slider("2060 KBA105 — Perfecting",  1.0, 2.0, 1.50, step=0.05,
                              help="Most unreliable press in fleet")

st.sidebar.subheader("Night Shift")
night_waste   = st.sidebar.slider("Night Waste Factor",   1.0, 1.5, 1.15, step=0.05)
night_quality = st.sidebar.slider("Night Quality Factor", 1.0, 1.5, 1.15, step=0.05)

st.sidebar.subheader("Stock & Material")
foil_waste = st.sidebar.slider("Foil Waste Factor",          1.0, 2.0, 1.25, step=0.05)
jam_rate   = st.sidebar.slider("Jam Rate (per 10K sheets)",  0.0, 0.15, 0.03, step=0.01)

st.sidebar.subheader("Volume")
num_jobs = st.sidebar.slider("Number of Jobs", 500, 5000, 1000, step=500)

# ── RUN SIMULATION ────────────────────────────────────────────────────────
@st.cache_data
def run_sim(overrides_tuple):
    return generate_dataset(dict(overrides_tuple))

overrides = {
    "AGE_FACTOR_2190":         age_2190,
    "AGE_FACTOR_2160":         age_2160,
    "AGE_FACTOR_2150":         age_2150,
    "AGE_FACTOR_2500":         age_2500,
    "AGE_FACTOR_2330":         age_2330,
    "AGE_FACTOR_2060":         age_2060,
    "NIGHT_WASTE_FACTOR":      night_waste,
    "NIGHT_QUALITY_FACTOR":    night_quality,
    "FOIL_WASTE_FACTOR":       foil_waste,
    "JAM_RATE_PER_10K_SHEETS": jam_rate,
    "NUM_JOBS":                num_jobs,
}

with st.spinner("Running simulation..."):
    df = run_sim(tuple(sorted(overrides.items())))

# ── KPI STRIP ─────────────────────────────────────────────────────────────
st.subheader("Top Line")
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Profit",  f"${df['gross_profit'].sum():,.0f}")
k2.metric("Avg Margin",    f"{df['gross_margin_pct'].mean():.1f}%")
k3.metric("Late Rate",     f"{(df['delivery_status']=='LATE').mean():.1%}")
k4.metric("Avg Waste",     f"{df['waste_pct'].mean():.1f}%")
k5.metric("QC Fail Rate",  f"{(df['quality_pass']==0).mean():.1%}")

st.divider()

# ── ROW 1: PROFIT BY PRESS + MARGIN BY CUSTOMER ───────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("Total Gross Profit by Press")
    st.caption("Which presses are generating the most value — and which are dragging.")
    profit_by_press = df.groupby("press")["gross_profit"].sum().reset_index()
    profit_by_press.columns = ["press", "total_profit"]
    profit_by_press["press"] = profit_by_press["press"].astype(str)
    profit_by_press = profit_by_press.sort_values("total_profit", ascending=False)
    worst_press = profit_by_press.iloc[-1]["press"]
    bar_colors = ["#FF4455" if p == worst_press else "#4A90A4"
                  for p in profit_by_press["press"]]
    fig = px.bar(profit_by_press, x="press", y="total_profit",
                 category_orders={"press": profit_by_press["press"].tolist()})
    fig.update_traces(marker_color=bar_colors)
    fig.update_layout(showlegend=False, xaxis_title="Press",
                      yaxis_title="Total Gross Profit",
                      yaxis_tickprefix="$", yaxis_tickformat=",",
                      xaxis_type="category")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Margin by Customer")
    st.caption("SPOT jobs yield the highest margin. CUST-A is the volume anchor but lowest return.")
    margin_by_cust = df.groupby("customer")["gross_margin_pct"].mean().reset_index()
    margin_by_cust.columns = ["customer", "avg_margin"]
    margin_by_cust = margin_by_cust.sort_values("avg_margin", ascending=False)
    worst_cust = margin_by_cust.iloc[-1]["customer"]
    cust_colors = ["#FF4455" if c == worst_cust else "#4A90A4"
                   for c in margin_by_cust["customer"]]
    fig = px.bar(margin_by_cust, x="customer", y="avg_margin",
                 category_orders={"customer": margin_by_cust["customer"].tolist()})
    fig.update_traces(marker_color=cust_colors)
    fig.update_layout(showlegend=False, xaxis_title="Customer",
                      yaxis_title="Avg Gross Margin %",
                      yaxis_ticksuffix="%",
                      xaxis_type="category")
    st.plotly_chart(fig, use_container_width=True)

# ── ROW 2: QC FAIL BY PRESS + MARGIN TREND ────────────────────────────────
col3, col4 = st.columns(2)

with col3:
    st.subheader("QC Failure Rate by Press")
    st.caption("Operational risk. High failure rate = waste, delays, and margin compression.")
    qc_by_press = df.groupby("press")["quality_pass"].apply(
        lambda x: (1 - x.mean()) * 100
    ).reset_index()
    qc_by_press.columns = ["press", "fail_rate"]
    qc_by_press["press"] = qc_by_press["press"].astype(str)
    qc_by_press = qc_by_press.sort_values("fail_rate", ascending=False)
    worst_qc = qc_by_press.iloc[0]["press"]
    qc_colors = ["#FF4455" if p == worst_qc else "#4A90A4"
                 for p in qc_by_press["press"]]
    fig = px.bar(qc_by_press, x="press", y="fail_rate",
                 category_orders={"press": qc_by_press["press"].tolist()})
    fig.update_traces(marker_color=qc_colors)
    fig.update_layout(showlegend=False, xaxis_title="Press",
                      yaxis_title="QC Failure Rate %",
                      yaxis_ticksuffix="%",
                      xaxis_type="category")
    st.plotly_chart(fig, use_container_width=True)

with col4:
    st.subheader("Margin Trend Over Time")
    st.caption("Is margin improving or declining? Rolling 30-day average by customer.")
    df["job_date"] = pd.to_datetime(df["job_date"])
    trend = (df.groupby(["job_date", "customer"])["gross_margin_pct"]
             .mean()
             .reset_index()
             .sort_values("job_date"))
    trend = trend.set_index("job_date")
    smoothed = (trend.groupby("customer")["gross_margin_pct"]
                .transform(lambda x: x.rolling(30, min_periods=1).mean()))
    trend["smoothed"] = smoothed.values
    trend = trend.reset_index()
    fig = px.line(trend, x="job_date", y="smoothed", color="customer",
                  color_discrete_sequence=["#4A90A4", "#F5A623", "#00C875"])
    fig.update_layout(xaxis_title="Date", yaxis_title="Avg Gross Margin %",
                      yaxis_ticksuffix="%", legend_title="Customer")
    st.plotly_chart(fig, use_container_width=True)

# ── PRESS SUMMARY TABLE ────────────────────────────────────────────────────
col5, _ = st.columns([3, 1])
with col5:
    st.subheader("Press Performance Summary")
    press_summary = df.groupby("press").agg(
        qc_pass_rate=("quality_pass", "mean"),
        avg_waste=("waste_pct", "mean"),
        avg_margin=("gross_margin_pct", "mean"),
        avg_revenue=("revenue", "mean"),
        avg_cost=("total_cost", "mean"),
        avg_jams=("jam_count", "mean"),
    ).round(2)
    press_summary = press_summary.reindex(["2190","2500","2330","2150","2160","2060"])
    press_summary.index.name = "Press"
    press_summary_display = pd.DataFrame({
        "QC Pass Rate": press_summary["qc_pass_rate"].map("{:.1%}".format),
        "Avg Waste %":  press_summary["avg_waste"].map("{:.1f}%".format),
        "Avg Margin %": press_summary["avg_margin"].map("{:.1f}%".format),
        "Avg Revenue":  press_summary["avg_revenue"].map("${:,.0f}".format),
        "Avg Cost":     press_summary["avg_cost"].map("${:,.0f}".format),
        "Avg Jams":     press_summary["avg_jams"].map("{:.2f}".format),
    }, index=press_summary.index)
    st.dataframe(press_summary_display, use_container_width=True)

# ── DIAGNOSTIC CHECKS (uncomment to use) ──────────────────────────────────
# st.dataframe(df[['color_delta_e','register_error','dot_gain_pct','cut_deviation_mm']].describe().round(3))
# st.write("QC failure breakdown")
# st.dataframe(pd.DataFrame({
#     "delta_e_fails":       (df["color_delta_e"]    > 3.5).mean(),
#     "register_fails":      (df["register_error"]   > 2.0).mean(),
#     "dot_gain_fails":      (df["dot_gain_pct"]     > 30.0).mean(),
#     "cut_dev_fails":       (df["cut_deviation_mm"] > 0.5).mean(),
#     "foil_adhesion_fails": (df["foil_adhesion"]    < 70).mean(),
# }, index=["fail_rate"]).T.round(3))
# st.dataframe(df.groupby(["press","shift"])["quality_pass"].mean().unstack().round(3))

# ── RAW DATA ──────────────────────────────────────────────────────────────
with st.expander("Show raw data sample"):
    st.dataframe(df.head(50))
