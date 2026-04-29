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

# ── BASELINE BUTTON ───────────────────────────────────────────────────────
set_baseline = st.sidebar.button("📊 Set as Baseline", use_container_width=True)
if st.session_state.get("baseline_set"):
    st.sidebar.caption("✅ Baseline set — move sliders to compare")

st.sidebar.divider()

# ── FINANCIAL RATES ───────────────────────────────────────────────────────
with st.sidebar.expander("Financial Rates", expanded=False):
    st.markdown("**Press Rates ($/hr)**")
    sf_cost_rate  = st.slider("Sheetfed Cost Rate",    50,  300, 140, step=10)
    pf_cost_rate  = st.slider("Perfecting Cost Rate",  50,  300, 150, step=10)
    sf_bill_rate  = st.slider("Sheetfed Bill Rate",   100,  500, 250, step=10)
    pf_bill_rate  = st.slider("Perfecting Bill Rate", 100,  500, 285, step=10)
    st.markdown("---")
    st.markdown("**Stock Costs**")
    stock_white = st.slider("White Stock ($/MSF)",  20, 150,  55, step=5)
    stock_foil  = st.slider("Foil Stock ($/MSF)",  100, 600, 320, step=10)
    ink_cost    = st.slider("Ink Cost ($/lb)",        5,  50,  20, step=1)

# ── PRODUCT MIX ───────────────────────────────────────────────────────────
with st.sidebar.expander("Product Mix", expanded=False):
    avg_run_size = st.slider("Avg Run Size (sheets)", 15000, 100000, 40000, step=5000,
                             help="Global average job size. Per-press run size variation to be added in a future update.")
    st.markdown("---")
    st.markdown("**Layout Mix** — relative weights")
    mix_121_plain = st.slider("121-up White", 0.0, 1.0, 0.40, step=0.05)
    mix_121_holo  = st.slider("121-up Foil",  0.0, 1.0, 0.25, step=0.05)
    mix_100_plain = st.slider("100-up White", 0.0, 1.0, 0.15, step=0.05)
    mix_100_holo  = st.slider("100-up Foil",  0.0, 1.0, 0.20, step=0.05)
    st.markdown("---")
    st.markdown("**Material**")
    foil_waste = st.slider("Foil Waste Factor", 1.0, 2.0, 1.25, step=0.05,
                           help="Multiplier applied to waste rate and jam rate for foil stock jobs. 1.25 = foil generates 25% more waste than white stock.")
    jam_rate   = st.slider("Jam Rate (per 10K sheets)", 0.0, 0.15, 0.03, step=0.01)

# ── CUSTOMER MARKUP ───────────────────────────────────────────────────────
with st.sidebar.expander("Customer Markup", expanded=False):
    markup_a    = st.slider("CUST-A Markup",           1.0, 2.0, 1.25, step=0.05)
    markup_b    = st.slider("CUST-B Markup",           1.0, 2.0, 1.40, step=0.05)
    markup_spot = st.slider("SPOT Markup",             1.0, 2.5, 1.55, step=0.05)
    foil_prem   = st.slider("Foil Complexity Premium", 0.0, 0.5, 0.15, step=0.05,
                            help="Additional markup added on top of the customer's base rate for foil jobs. 0.15 = 15 extra points of markup on any foil job.")
    st.markdown("---")
    st.markdown("**Customer Mix** — relative weights")
    share_a    = st.slider("CUST-A Share", 0.0, 1.0, 0.70, step=0.05)
    share_b    = st.slider("CUST-B Share", 0.0, 1.0, 0.20, step=0.05)
    share_spot = st.slider("SPOT Share",   0.0, 1.0, 0.10, step=0.05)

# ── PRESS CONTROLS ────────────────────────────────────────────────────────
with st.sidebar.expander("Press Controls", expanded=False):
    st.markdown("**Base Speeds (sph)**")
    speed_white_sf = st.slider("White — Sheetfed",   5000, 15000, 10500, step=500)
    speed_white_pf = st.slider("White — Perfecting", 5000, 15000,  9500, step=500)
    speed_foil_sf  = st.slider("Foil — Sheetfed",    3000, 12000,  7500, step=500)
    speed_foil_pf  = st.slider("Foil — Perfecting",  3000, 12000,  6500, step=500)
    speed_noise    = st.slider("Speed Noise Std Dev",    0,   800,   400, step=50,
                               help="Controls how much actual press speed varies around the baseline. Higher = more job-to-job variability in run times.")
    st.markdown("---")
    st.markdown("**Job Shares** — relative weights")
    share_2190 = st.slider("2190 Share", 0.0, 1.0, 0.30, step=0.01)
    share_2160 = st.slider("2160 Share", 0.0, 1.0, 0.21, step=0.01)
    share_2150 = st.slider("2150 Share", 0.0, 1.0, 0.19, step=0.01)
    share_2500 = st.slider("2500 Share", 0.0, 1.0, 0.16, step=0.01)
    share_2330 = st.slider("2330 Share", 0.0, 1.0, 0.08, step=0.01)
    share_2060 = st.slider("2060 Share", 0.0, 1.0, 0.06, step=0.01)
    st.markdown("---")
    st.markdown("**Age Factors**")
    st.caption("1.15 = best maintained → 1.50 = most unreliable")
    age_2190 = st.slider("2190 KBA106 — Perfecting",   1.0, 2.0, 1.15, step=0.05)
    age_2500 = st.slider("2500 640 Komori — Sheetfed", 1.0, 2.0, 1.20, step=0.05)
    age_2330 = st.slider("2330 640 Komori — Sheetfed", 1.0, 2.0, 1.20, step=0.05)
    age_2150 = st.slider("2150 640 Komori — Sheetfed", 1.0, 2.0, 1.25, step=0.05)
    age_2160 = st.slider("2160 840 Komori — Sheetfed", 1.0, 2.0, 1.30, step=0.05)
    age_2060 = st.slider("2060 KBA105 — Perfecting",   1.0, 2.0, 1.50, step=0.05,
                         help="Most unreliable press in fleet")

# ── QUALITY CONTROL ───────────────────────────────────────────────────────
with st.sidebar.expander("Quality Control", expanded=False):
    st.markdown("**Rejection Thresholds**")
    delta_e_reject    = st.slider("Color Delta E Reject",    1.0, 6.0, 3.5, step=0.1)
    register_reject   = st.slider("Register Error Reject",   0.5, 4.0, 2.0, step=0.1)
    dot_gain_reject   = st.slider("Dot Gain Reject (%)",    20.0,40.0,30.0, step=1.0)
    cut_dev_reject    = st.slider("Cut Deviation Reject (mm)",0.1, 1.5, 0.5, step=0.05)
    foil_adhesion_fail= st.slider("Foil Adhesion Fail",     40,  90,   70,  step=5)
    st.markdown("---")
    st.markdown("**QC Scrap & Downtime**")
    defect_sheets     = st.slider("Sheets Tossed on QC Hit",  10, 200,  50, step=10)
    qc_readjust_mins  = st.slider("Readjust Time (min)",        5,  60,  15, step=5)

# ── NIGHT SHIFT ───────────────────────────────────────────────────────────
with st.sidebar.expander("Night Shift", expanded=False):
    night_waste   = st.slider("Night Waste Factor",   1.0, 1.5, 1.15, step=0.05)
    night_quality = st.slider("Night Quality Factor", 1.0, 1.5, 1.15, step=0.05)

# ── VOLUME ────────────────────────────────────────────────────────────────
st.sidebar.subheader("Volume")
num_jobs = st.sidebar.slider("Number of Jobs", 500, 5000, 1000, step=500)

# ── RUN SIMULATION ────────────────────────────────────────────────────────
@st.cache_data
def run_sim(overrides_tuple):
    return generate_dataset(dict(overrides_tuple))

overrides = {
    # Press age
    "AGE_FACTOR_2190":            age_2190,
    "AGE_FACTOR_2160":            age_2160,
    "AGE_FACTOR_2150":            age_2150,
    "AGE_FACTOR_2500":            age_2500,
    "AGE_FACTOR_2330":            age_2330,
    "AGE_FACTOR_2060":            age_2060,
    # Press shares
    "SHARE_2190":                 share_2190,
    "SHARE_2160":                 share_2160,
    "SHARE_2150":                 share_2150,
    "SHARE_2500":                 share_2500,
    "SHARE_2330":                 share_2330,
    "SHARE_2060":                 share_2060,
    # Speeds
    "BASE_SPEED_WHITE_SHEETFED":  speed_white_sf,
    "BASE_SPEED_WHITE_PERFECTING":speed_white_pf,
    "BASE_SPEED_FOIL_SHEETFED":   speed_foil_sf,
    "BASE_SPEED_FOIL_PERFECTING": speed_foil_pf,
    "SPEED_NOISE_STD":            speed_noise,
    # Product mix
    "MIX_121_PLAIN":              mix_121_plain,
    "MIX_121_HOLO":               mix_121_holo,
    "MIX_100_PLAIN":              mix_100_plain,
    "MIX_100_HOLO":               mix_100_holo,
    "AVG_RUN_SIZE":               avg_run_size,
    "FOIL_WASTE_FACTOR":          foil_waste,
    "JAM_RATE_PER_10K_SHEETS":    jam_rate,
    # Customer markup
    "CUST_A_MARKUP":              markup_a,
    "CUST_B_MARKUP":              markup_b,
    "SPOT_MARKUP_PREMIUM":        markup_spot,
    "COMPLEXITY_PREMIUM_FOIL":    foil_prem,
    "CUST_A_SHARE":               share_a,
    "CUST_B_SHARE":               share_b,
    "SPOT_JOB_SHARE":             share_spot,
    # Financial rates
    "SHEETFED_RATE_HR":           sf_cost_rate,
    "PERFECTING_RATE_HR":         pf_cost_rate,
    "SHEETFED_BILL_RATE_HR":      sf_bill_rate,
    "PERFECTING_BILL_RATE_HR":    pf_bill_rate,
    "BURDEN_RATE_HR":             0,
    "STOCK_COST_WHITE":           stock_white,
    "STOCK_COST_FOIL":            stock_foil,
    "INK_COST_PER_LB":            ink_cost,
    # Quality control
    "DELTA_E_REJECT":             delta_e_reject,
    "REGISTER_REJECT":            register_reject,
    "DOT_GAIN_REJECT":            dot_gain_reject,
    "CUT_DEVIATION_REJECT":       cut_dev_reject,
    "FOIL_ADHESION_FAIL":         foil_adhesion_fail,
    "DEFECT_WINDOW_SHEETS":       defect_sheets,
    "QC_READJUST_MINUTES":        qc_readjust_mins,
    # Night shift
    "NIGHT_WASTE_FACTOR":         night_waste,
    "NIGHT_QUALITY_FACTOR":       night_quality,
    # Volume
    "NUM_JOBS":                   num_jobs,
}

with st.spinner("Running simulation..."):
    df = run_sim(tuple(sorted(overrides.items())))

# ── BASELINE ──────────────────────────────────────────────────────────────
if "baseline_df" not in st.session_state:
    st.session_state.baseline_df = df.copy()
    st.session_state.baseline_set = False

if set_baseline:
    st.session_state.baseline_df = df.copy()
    st.session_state.baseline_set = True

baseline = st.session_state.baseline_df

# ── KPI STRIP ─────────────────────────────────────────────────────────────
st.subheader("Top Line")
k1, k2, k3, k4, k5 = st.columns(5)

cur_profit  = df["gross_profit"].sum()
cur_margin  = df["gross_margin_pct"].mean()
cur_late    = (df["delivery_status"] == "LATE").mean() * 100
cur_waste   = df["waste_pct"].mean()
cur_qc_fail = (df["quality_pass"] == 0).mean() * 100

base_profit  = baseline["gross_profit"].sum()
base_margin  = baseline["gross_margin_pct"].mean()
base_late    = (baseline["delivery_status"] == "LATE").mean() * 100
base_waste   = baseline["waste_pct"].mean()
base_qc_fail = (baseline["quality_pass"] == 0).mean() * 100
profit_diff = cur_profit - base_profit

k1.metric("Total Profit",      f"${cur_profit:,.0f}",
          delta=f"{'-' if profit_diff < 0 else ''}${abs(profit_diff):,.0f}",
          delta_color="normal")  

k2.metric("Avg Margin",    f"{cur_margin:.1f}%",
          delta=f"{cur_margin - base_margin:.1f}%")
k3.metric("Late Rate",     f"{cur_late:.1f}%",
          delta=f"{cur_late - base_late:.1f}%",
          delta_color="inverse")
k4.metric("Avg Waste",     f"{cur_waste:.1f}%",
          delta=f"{cur_waste - base_waste:.1f}%",
          delta_color="inverse")
k5.metric("QC Fail Rate",  f"{cur_qc_fail:.1f}%",
          delta=f"{cur_qc_fail - base_qc_fail:.1f}%",
          delta_color="inverse")

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
    st.subheader("Revenue Trend Over Time")
    st.caption("Cumulative revenue by customer across the simulation period.")
    df["job_date"] = pd.to_datetime(df["job_date"])
    trend = (df.groupby(["job_date", "customer"])["revenue"]
             .sum()
             .reset_index()
             .sort_values("job_date"))
    trend = trend.set_index("job_date")
    smoothed = (trend.groupby("customer")["revenue"]
                .transform(lambda x: x.rolling(30, min_periods=1).mean()))
    trend["smoothed"] = smoothed.values
    trend = trend.reset_index()
    fig = px.line(trend, x="job_date", y="smoothed", color="customer",
                  color_discrete_sequence=["#4A90A4", "#F5A623", "#00C875"])
    fig.update_layout(xaxis_title="Date", yaxis_title="Avg Daily Revenue",
                      yaxis_tickprefix="$", yaxis_tickformat=",",
                      legend_title="Customer")
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
    st.subheader("Revenue by Shift")
    st.caption("Which shifts are generating the most value.")
    rev_by_shift = df.groupby("shift")["revenue"].sum().reset_index()
    rev_by_shift.columns = ["shift", "total_revenue"]
    rev_by_shift = rev_by_shift.sort_values("total_revenue", ascending=False)
    lowest_shift = rev_by_shift.iloc[-1]["shift"]
    shift_colors = ["#FF4455" if s == lowest_shift else "#4A90A4"
                    for s in rev_by_shift["shift"]]
    fig = px.bar(rev_by_shift, x="shift", y="total_revenue",
                 category_orders={"shift": rev_by_shift["shift"].tolist()})
    fig.update_traces(marker_color=shift_colors)
    fig.update_layout(showlegend=False, xaxis_title="Shift",
                      yaxis_title="Total Revenue",
                      yaxis_tickprefix="$", yaxis_tickformat=",",
                      xaxis_type="category")
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
