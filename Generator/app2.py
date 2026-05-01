import sys
import os
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from Project.Project.trading_card_generate_dataset import generate_dataset

# ── PAGE CONFIG ───────────────────────────────────────────────────────────
st.set_page_config(page_title="Print Shop Simulator", layout="wide")

st.title("Print Ops Monitor")
st.set_page_config(page_title="Print Ops Monitor", layout="wide")

st.markdown("""
    <style>
        /* Tighten overall page padding */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
        }

        /* Reduce gap between all stacked elements */
        div[data-testid="stVerticalBlock"] > div {
            gap: 0.2rem !important;
        }

        /* Dividers */
        div[data-testid="stDivider"] {
            margin-top: 4px !important;
            margin-bottom: 4px !important;
            padding-bottom: 0px !important;
        }
        hr {
            margin-top: 0rem !important;
            margin-bottom: 0rem !important;
        }

        /* Title */
        h1 {
            margin-bottom: 0.1rem !important;
            padding-bottom: 0 !important;
        }

        /* Chart subheaders */
        h3 {
            margin-bottom: 0rem !important;
            margin-top: 0.25rem !important;
        }

        /* KPI metrics */
        div[data-testid="stMetric"] {
            padding: 0.2rem 0 !important;
        }

        /* Scenario buttons */
        div[data-testid="stHorizontalBlock"] {
            gap: 0.5rem !important;
        }
    </style>
""", unsafe_allow_html=True)



# ── SCENARIO DEFINITIONS ──────────────────────────────────────────────────
SCENARIOS = {
    "default": {
        "label": "⚙️ Current Fleet",
        "overrides": {},
        "description": "Baseline simulation at current fleet parameters.",
    },
    "waste": {
        "label": "💸 Where Is Money Going to Waste?",
        "overrides": {},  # No overrides — shows waste story in existing data
        "description": "Every job absorbs cost the customer never pays for. Here's where it's going.",
    },
    "foil": {
        "label": "✨ Is Foil Worth It?",
        "overrides": {},  # Handled via two separate runs below
        "description": "Foil commands a premium — but does the operational cost justify it?",
    },
    "throughput": {
        "label": "🔧 What's Slowing Us Down?",
        "overrides": {},
        "description": "As presses age, throughput bleeds away. Here's what deferred maintenance costs in impressions.",
    },
}

# ── SESSION STATE — SCENARIO ──────────────────────────────────────────────
if "active_scenario" not in st.session_state:
    st.session_state.active_scenario = "default"

# ── SCENARIO BUTTONS ──────────────────────────────────────────────────────
st.markdown("### What do you want to know?")
btn_cols = st.columns(4)
scenario_keys = list(SCENARIOS.keys())
for i, key in enumerate(scenario_keys):
    is_active = st.session_state.active_scenario == key
    label = SCENARIOS[key]["label"]
    if is_active:
        btn_cols[i].markdown(
            f"<div style='background:#1F4E79;color:white;padding:10px 8px;"
            f"border-radius:6px;text-align:center;font-weight:700;"
            f"font-size:13px;cursor:default;'>{label}</div>",
            unsafe_allow_html=True
        )
        btn_cols[i].write("")  # spacer so button below aligns
    else:
        if btn_cols[i].button(label, use_container_width=True, key=f"btn_{key}"):
            st.session_state.active_scenario = key
            st.rerun()

active = st.session_state.active_scenario
st.divider()

# ── SIDEBAR — CUSTOMIZE ───────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Customize Parameters")
    st.caption("Adjust any value to explore scenarios beyond the presets.")

    set_baseline = st.button("📊 Set as Baseline", use_container_width=True)
    if st.session_state.get("baseline_set"):
        st.caption("✅ Baseline active — deltas shown against this state")
    st.divider()

    with st.expander("Financial Rates", expanded=False):
        st.markdown("**Press Rates ($/hr)**")
        sf_cost_rate = st.slider("Sheetfed Cost Rate",   200, 500, 240, step=10)
        pf_cost_rate = st.slider("Perfecting Cost Rate", 200, 500, 250, step=10)
        sf_bill_rate = st.slider("Sheetfed Bill Rate",   300, 500, 350, step=10)
        pf_bill_rate = st.slider("Perfecting Bill Rate", 300, 500, 385, step=10)
        st.markdown("---")
        st.markdown("**Stock Costs**")
        stock_white = st.slider("White Stock ($/MSF)",  20, 150,  55, step=5)
        stock_foil  = st.slider("Foil Stock ($/MSF)",  100, 600, 320, step=10)
        ink_cost    = st.slider("Ink Cost ($/lb)",        5,  50,  20, step=1)

    with st.expander("Product Mix", expanded=False):
        avg_run_size = st.slider("Avg Run Size (sheets)", 5000, 100000, 10000, step=5000)
        st.markdown("---")
        st.markdown("**Layout Mix** — relative weights")
        mix_121_plain = st.slider("121-up White", 0.0, 1.0, 0.40, step=0.05)
        mix_121_holo  = st.slider("121-up Foil",  0.0, 1.0, 0.25, step=0.05)
        mix_100_plain = st.slider("100-up White", 0.0, 1.0, 0.15, step=0.05)
        mix_100_holo  = st.slider("100-up Foil",  0.0, 1.0, 0.20, step=0.05)
        st.markdown("---")
        st.markdown("**Material**")
        foil_waste = st.slider("Foil Waste Factor", 1.0, 2.0, 1.25, step=0.05)
        jam_rate   = st.slider("Jam Rate (per 10K sheets)", 0.0, 0.15, 0.03, step=0.01)

    with st.expander("Customer Markup", expanded=False):
        markup_a    = st.slider("CUST-A Markup",           1.0, 2.0, 1.25, step=0.05)
        markup_b    = st.slider("CUST-B Markup",           1.0, 2.0, 1.40, step=0.05)
        markup_spot = st.slider("SPOT Markup",             1.0, 2.5, 1.55, step=0.05)
        foil_prem   = st.slider("Foil Complexity Premium", 0.0, 0.5, 0.15, step=0.05)
        st.markdown("---")
        st.markdown("**Customer Mix** — relative weights")
        share_a    = st.slider("CUST-A Share", 0.0, 1.0, 0.70, step=0.05)
        share_b    = st.slider("CUST-B Share", 0.0, 1.0, 0.20, step=0.05)
        share_spot = st.slider("SPOT Share",   0.0, 1.0, 0.10, step=0.05)

    with st.expander("Press Controls", expanded=False):
        st.markdown("**Base Speeds (sph)**")
        speed_white_sf = st.slider("White — Sheetfed",   5000, 15000, 10500, step=500)
        speed_white_pf = st.slider("White — Perfecting", 5000, 15000,  9500, step=500)
        speed_foil_sf  = st.slider("Foil — Sheetfed",    3000, 12000,  7500, step=500)
        speed_foil_pf  = st.slider("Foil — Perfecting",  3000, 12000,  6500, step=500)
        speed_noise    = st.slider("Speed Noise Std Dev",    0,   800,   400, step=50)
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
        age_2190 = st.slider("2190 KBA106",   1.0, 2.0, 1.15, step=0.05)
        age_2500 = st.slider("2500 Komori",   1.0, 2.0, 1.20, step=0.05)
        age_2330 = st.slider("2330 Komori",   1.0, 2.0, 1.20, step=0.05)
        age_2150 = st.slider("2150 Komori",   1.0, 2.0, 1.25, step=0.05)
        age_2160 = st.slider("2160 840",      1.0, 2.0, 1.30, step=0.05)
        age_2060 = st.slider("2060 KBA105",   1.0, 2.0, 1.50, step=0.05,
                             help="Most unreliable press in fleet")

    with st.expander("Quality Control", expanded=False):
        st.markdown("**Rejection Thresholds**")
        delta_e_reject    = st.slider("Color Delta E Reject",      1.0, 6.0, 3.5, step=0.1)
        register_reject   = st.slider("Register Error Reject",     0.5, 4.0, 2.0, step=0.1)
        dot_gain_reject   = st.slider("Dot Gain Reject (%)",      20.0,40.0,30.0, step=1.0)
        cut_dev_reject    = st.slider("Cut Deviation Reject (mm)", 0.1, 1.5, 0.5, step=0.05)
        foil_adhesion_fail= st.slider("Foil Adhesion Fail",       40,  90,   70,  step=5)
        st.markdown("---")
        st.markdown("**QC Scrap & Downtime**")
        defect_sheets    = st.slider("Sheets Tossed on QC Hit", 10, 200,  50, step=10)
        qc_readjust_mins = st.slider("Readjust Time (min)",       5,  60,  15, step=5)

    with st.expander("Night Shift", expanded=False):
        night_waste   = st.slider("Night Waste Factor",   1.0, 1.5, 1.15, step=0.05)
        night_quality = st.slider("Night Quality Factor", 1.0, 1.5, 1.15, step=0.05)

    st.subheader("Volume")
    num_jobs = st.slider("Number of Jobs", 500, 5000, 1000, step=500)

# ── BASE OVERRIDES FROM SLIDERS ───────────────────────────────────────────
base_overrides = {
    "AGE_FACTOR_2190":             age_2190,
    "AGE_FACTOR_2160":             age_2160,
    "AGE_FACTOR_2150":             age_2150,
    "AGE_FACTOR_2500":             age_2500,
    "AGE_FACTOR_2330":             age_2330,
    "AGE_FACTOR_2060":             age_2060,
    "SHARE_2190":                  share_2190,
    "SHARE_2160":                  share_2160,
    "SHARE_2150":                  share_2150,
    "SHARE_2500":                  share_2500,
    "SHARE_2330":                  share_2330,
    "SHARE_2060":                  share_2060,
    "BASE_SPEED_WHITE_SHEETFED":   speed_white_sf,
    "BASE_SPEED_WHITE_PERFECTING": speed_white_pf,
    "BASE_SPEED_FOIL_SHEETFED":    speed_foil_sf,
    "BASE_SPEED_FOIL_PERFECTING":  speed_foil_pf,
    "SPEED_NOISE_STD":             speed_noise,
    "MIX_121_PLAIN":               mix_121_plain,
    "MIX_121_HOLO":                mix_121_holo,
    "MIX_100_PLAIN":               mix_100_plain,
    "MIX_100_HOLO":                mix_100_holo,
    "AVG_RUN_SIZE":                avg_run_size,
    "FOIL_WASTE_FACTOR":           foil_waste,
    "JAM_RATE_PER_10K_SHEETS":     jam_rate,
    "CUST_A_MARKUP":               markup_a,
    "CUST_B_MARKUP":               markup_b,
    "SPOT_MARKUP_PREMIUM":         markup_spot,
    "COMPLEXITY_PREMIUM_FOIL":     foil_prem,
    "CUST_A_SHARE":                share_a,
    "CUST_B_SHARE":                share_b,
    "SPOT_JOB_SHARE":              share_spot,
    "SHEETFED_RATE_HR":            sf_cost_rate,
    "PERFECTING_RATE_HR":          pf_cost_rate,
    "SHEETFED_BILL_RATE_HR":       sf_bill_rate,
    "PERFECTING_BILL_RATE_HR":     pf_bill_rate,
    "BURDEN_RATE_HR":              0,
    "STOCK_COST_WHITE":            stock_white,
    "STOCK_COST_FOIL":             stock_foil,
    "INK_COST_PER_LB":             ink_cost,
    "DELTA_E_REJECT":              delta_e_reject,
    "REGISTER_REJECT":             register_reject,
    "DOT_GAIN_REJECT":             dot_gain_reject,
    "CUT_DEVIATION_REJECT":        cut_dev_reject,
    "FOIL_ADHESION_FAIL":          foil_adhesion_fail,
    "DEFECT_WINDOW_SHEETS":        defect_sheets,
    "QC_READJUST_MINUTES":         qc_readjust_mins,
    "NIGHT_WASTE_FACTOR":          night_waste,
    "NIGHT_QUALITY_FACTOR":        night_quality,
    "NUM_JOBS":                    num_jobs,
}

# Merge scenario overrides on top of slider values
scenario_overrides = {**base_overrides, **SCENARIOS[active]["overrides"]}
# ── RUN SIMULATION ────────────────────────────────────────────────────────
@st.cache_data
def run_sim(overrides_tuple):
    return generate_dataset(dict(overrides_tuple))

with st.spinner("Running simulation..."):
    df = run_sim(tuple(sorted(scenario_overrides.items())))

# ── BASELINE ──────────────────────────────────────────────────────────────
if "baseline_df" not in st.session_state:
    st.session_state.baseline_df = df.copy()
    st.session_state.baseline_set = False

if set_baseline:
    st.session_state.baseline_df = df.copy()
    st.session_state.baseline_set = True

baseline = st.session_state.baseline_df

# ── SHARED HELPERS ────────────────────────────────────────────────────────
def waste_dollars(d):
    mat = (d["paper_cost"] * ((d["sheets_run"] - d["qty_ordered"]) / d["sheets_run"])).sum()
    time_ = ((d["jam_time_hrs"] + d["qc_downtime_hrs"]) * d["labor_rate"]).sum()
    return mat + time_

def throughput(d):
    return (d["qty_ordered"] * d["passes"]).sum() / d["total_press_time"].sum()

MUTED  = "#A8C4D4"
ACCENT = "#FF4455"
PRIMARY = "#4A90A4"

def worst(series, highest=False):
    return series.idxmax() if highest else series.idxmin()

def bar_colors(index, worst_press):
    return [ACCENT if p == worst_press else MUTED for p in index]

def clean_layout(fig, x_title=None, y_title=None, y_prefix="", y_suffix="", y_format=""):
    fig.update_layout(
        showlegend=False,
        xaxis_title=x_title,
        yaxis_title=y_title,
        xaxis_type="category",
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="#EEEEEE",
                   tickprefix=y_prefix,
                   ticksuffix=y_suffix,
                   tickformat=y_format),
        margin=dict(t=10, b=10),
    )
    return fig

# ── KPI STRIP ─────────────────────────────────────────────────────────────
cur_profit     = df["gross_profit"].sum()
cur_waste      = waste_dollars(df)
cur_waste_pct  = cur_waste / df["revenue"].sum() * 100
cur_through    = throughput(df)

base_profit    = baseline["gross_profit"].sum()
base_waste     = waste_dollars(baseline)
base_through   = throughput(baseline)

profit_diff    = cur_profit - base_profit
waste_diff     = cur_waste - base_waste
through_diff   = cur_through - base_through

k1, k2, k3 = st.columns(3)

k1.metric("Total Profit:",
          f"${cur_profit:,.0f}",
          delta=f"{'-' if profit_diff < 0 else ''}${abs(profit_diff):,.0f}",
          delta_color="normal")

k2.metric("Waste Cost:",
          f"${cur_waste:,.0f} ({cur_waste_pct:.1f}%)",
          delta=f"{'-' if waste_diff < 0 else ''}${abs(waste_diff):,.0f}",
          delta_color="inverse")

k3.metric("Throughput:",
          f"{cur_through:,.0f} imp/hr",
          delta=f"{through_diff:+.0f} imp/hr",
          delta_color="normal")

st.divider()

# ── CHART SECTION ─────────────────────────────────────────────────────────
placeholder = st.empty()
col1, col2, col3= st.columns(3)

# ═══════════════════════════════════════════════════════════════════════════
# DEFAULT VIEW
# ═══════════════════════════════════════════════════════════════════════════
if active == "default":

    with col1:
        profit_by_press = df.groupby("press")["gross_profit"].sum().sort_values()
        wp = profit_by_press.idxmin()
        
        # 1. Combine Title and Value using HTML breaks (<b> tags for emphasis)
        labels_profit = [f"<b>{p}</b><br>${val:,.0f}" for p, val in zip(profit_by_press.index, profit_by_press.values)]
        
        # 2. Dynamic text color for contrast (White on Red, Dark Blue on Light Blue)
        font_colors_1 = ["white" if p == wp else "#1F4E79" for p in profit_by_press.index]

        st.subheader(f"Press {wp} Is Dragging Profit")
        st.caption("Total gross profit by press — worst performer highlighted.")
        
        fig1 = px.bar(profit_by_press.reset_index(),
                     x="press", y="gross_profit",
                     category_orders={"press": profit_by_press.index.tolist()})
        
        fig1.update_traces(
            text=labels_profit,
            textposition="inside", 
            insidetextanchor="middle",
            textfont=dict(color=font_colors_1, size=14),
            marker_color=bar_colors(profit_by_press.index, wp)
        )
        
        clean_layout(fig1)
        # 3. Completely obliterate both axes
        fig1.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False), margin=dict(t=10, b=0)) 
        st.plotly_chart(fig1, use_container_width=True,height=350)

    with col2:
        # LEFT UNTOUCHED: Box plots require an x-axis to anchor the distribution spread
        avg_margin = df.groupby("press")["gross_margin_pct"].mean().sort_values()
        wp2 = avg_margin.idxmin()
        st.subheader(f"Press {wp2} Has the Weakest Margin")
        st.caption("Distribution of margin % per press — spread shows consistency.")
        cmap = {p: ACCENT if p == wp2 else MUTED for p in df["press"].unique()}
        
        fig2 = px.box(df, x="press", y="gross_margin_pct",
                     color="press", color_discrete_map=cmap,
                     category_orders={"press": avg_margin.index.tolist()})
        
        fig2.update_layout(showlegend=False, xaxis_type="category",
                          xaxis=dict(showgrid=False),
                          yaxis=dict(gridcolor="#EEEEEE", ticksuffix="%"),
                          margin=dict(t=10, b=10))
        st.plotly_chart(fig2, use_container_width=True,height=350)

    with col3:
        qc = df.groupby("press")["quality_pass"].apply(lambda x: (1 - x.mean()) * 100).sort_values(ascending=False)
        wq = qc.idxmax()
        
        labels_qc = [f"<b>{p}</b><br>{val:.1f}%" for p, val in zip(qc.index, qc.values)]
        font_colors_3 = ["white" if p == wq else "#1F4E79" for p in qc.index]

        st.subheader(f"Press {wq} Fails QC Most Often")
        st.caption("QC failure rate by press — failures add waste cost and downtime.")
        
        fig3 = px.bar(qc.reset_index(),
                     x="press", y="quality_pass",
                     category_orders={"press": qc.index.tolist()})
        
        fig3.update_traces(
            text=labels_qc,
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(color=font_colors_3, size=14),
            marker_color=[ACCENT if p == wq else MUTED for p in qc.index]
        )
        
        clean_layout(fig3)
        fig3.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False), margin=dict(t=10, b=0))
        st.plotly_chart(fig3, use_container_width=True,height=350)

    # SHIFT COMPARISONS
    # with col4:
    #     rev_shift = df.groupby("shift")["revenue"].sum().sort_values(ascending=False)
    #     ls = rev_shift.idxmin()
        
    #     labels_rev = [f"<b>{s}</b><br>${val:,.0f}" for s, val in zip(rev_shift.index, rev_shift.values)]
    #     font_colors_4 = ["white" if s == ls else "#1F4E79" for s in rev_shift.index]

    #     st.subheader(f"{ls} Generates the Least Revenue")
    #     st.caption("Total revenue by shift.")
        
    #     fig4 = px.bar(rev_shift.reset_index(),
    #                  x="shift", y="revenue",
    #                  category_orders={"shift": rev_shift.index.tolist()})
        
    #     fig4.update_traces(
    #         text=labels_rev,
    #         textposition="inside",
    #         insidetextanchor="middle",
    #         textfont=dict(color=font_colors_4, size=14),
    #         marker_color=[ACCENT if s == ls else MUTED for s in rev_shift.index]
    #     )
        
    #     clean_layout(fig4)
    #     fig4.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False), margin=dict(t=10, b=0))
    #     st.plotly_chart(fig4, use_container_width=True)
# ═══════════════════════════════════════════════════════════════════════════
# SCENARIO 1 — WHERE IS MONEY GOING TO WASTE?
# ═══════════════════════════════════════════════════════════════════════════
elif active == "waste":

    # Waste cost per press
    def press_waste_cost(d):
        mat = d["paper_cost"] * ((d["sheets_run"] - d["qty_ordered"]) / d["sheets_run"])
        time_ = (d["jam_time_hrs"] + d["qc_downtime_hrs"]) * d["labor_rate"]
        return (mat + time_).groupby(d["press"]).sum()

    wc = press_waste_cost(df).sort_values(ascending=False)
    wp = wc.idxmax()

    with col1:
        labels_wc = [f"<b>{p}</b><br>${val:,.0f}" for p, val in zip(wc.index, wc.values)]
        font_colors_1 = ["white" if p == wp else "#1F4E79" for p in wc.index]

        st.subheader(f"Press {wp} Costs the Most in Waste")
        st.caption("Combined material scrap + lost press time per press.")
        
        fig1 = px.bar(wc.reset_index(),
                     x="press", y=0,
                     category_orders={"press": wc.index.tolist()})
        
        fig1.update_traces(
            text=labels_wc,
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(color=font_colors_1, size=14),
            marker_color=[ACCENT if p == wp else MUTED for p in wc.index]
        )
        
        clean_layout(fig1)
        fig1.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False,range=[0, wc.max() * 1.15]), margin=dict(t=10, b=0))
        st.plotly_chart(fig1, use_container_width=True,height=350)

    with col2:
        gap = df.groupby("press").apply(
            lambda d: (d["sheets_run"] - d["qty_ordered"]).sum()
        ).sort_values(ascending=False)
        wg = gap.idxmax()
        
        labels_gap = [f"<b>{p}</b><br>{val:,.0f}" for p, val in zip(gap.index, gap.values)]
        font_colors_2 = ["white" if p == wg else "#1F4E79" for p in gap.index]

        st.subheader(f"Press {wg} Runs the Most Unrecovered Sheets")
        st.caption("Sheets run beyond what the customer ordered — every one is absorbed cost.")
        
        fig2 = px.bar(gap.reset_index(),
                     x="press", y=0,
                     category_orders={"press": gap.index.tolist()})
        
        fig2.update_traces(
            text=labels_gap,
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(color=font_colors_2, size=14),
            marker_color=[ACCENT if p == wg else MUTED for p in gap.index]
        )
        
        clean_layout(fig2)
        fig2.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False), margin=dict(t=10, b=0))
        st.plotly_chart(fig2, use_container_width=True,height=350)

    with col3:
        waste_shift = df.groupby("shift")["waste_pct"].mean().sort_values(ascending=False)
        ws = waste_shift.idxmax()
        
        labels_shift = [f"<b>{s}</b><br>{val:.1f}%" for s, val in zip(waste_shift.index, waste_shift.values)]
        font_colors_3 = ["white" if s == ws else "#1F4E79" for s in waste_shift.index]

        st.subheader(f"{ws} Has the Highest Waste Rate")
        st.caption("Average waste % by shift — night penalty visible here.")
        
        fig3 = px.bar(waste_shift.reset_index(),
                     x="shift", y="waste_pct",
                     category_orders={"shift": waste_shift.index.tolist()})
        
        fig3.update_traces(
            text=labels_shift,
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(color=font_colors_3, size=14),
            marker_color=[ACCENT if s == ws else MUTED for s in waste_shift.index]
        )
        
        clean_layout(fig3)
        fig3.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False), margin=dict(t=10, b=0))
        st.plotly_chart(fig3, use_container_width=True,height=350)

    # WASTE TRENDS
    # with col4:
    #     # Waste cost trend over time
    #     df["job_date"] = pd.to_datetime(df["job_date"])
    #     df["waste_cost_job"] = (
    #         df["paper_cost"] * ((df["sheets_run"] - df["qty_ordered"]) / df["sheets_run"])
    #         + (df["jam_time_hrs"] + df["qc_downtime_hrs"]) * df["labor_rate"]
    #     )
    #     wt = (df.groupby("job_date")["waste_cost_job"]
    #           .sum()
    #           .rolling(30, min_periods=1)
    #           .mean()
    #           .reset_index())
        
    #     st.subheader("Waste Cost Trend")
    #     st.caption("30-day rolling avg daily waste. Dashed line is the period mean.")
        
    #     fig4 = px.line(wt, x="job_date", y="waste_cost_job",
    #                   color_discrete_sequence=[ACCENT])
        
    #     # Add Tufte Reference Line (Context) - Let Plotly auto-color the text for Dark Mode
    #     overall_avg = wt["waste_cost_job"].mean()
    #     fig4.add_hline(y=overall_avg, line_dash="dash", line_color=MUTED,
    #                    annotation_text=f"Avg: ${overall_avg:,.0f}", 
    #                    annotation_position="bottom right",
    #                    annotation_font=dict(size=12))

    #     # Direct label the final point
    #     last_date = wt["job_date"].iloc[-1]
    #     last_val = wt["waste_cost_job"].iloc[-1]
    #     fig4.add_annotation(x=last_date, y=last_val,
    #                         text=f"<b>${last_val:,.0f}</b>",
    #                         showarrow=True, arrowhead=0, ax=35, ay=0,
    #                         font=dict(color=ACCENT, size=14))
                            
    #     # Label the starting date for X-axis context
    #     first_date = wt["job_date"].iloc[0]
    #     fig4.add_annotation(x=first_date, y=wt["waste_cost_job"].iloc[0],
    #                         text=f"{first_date.strftime('%b %d')}",
    #                         showarrow=False, yshift=-15,
    #                         font=dict(size=12))

    #     clean_layout(fig4)
        
    #     # Erase BOTH axes entirely to kill rogue lines and formatting issues 
    #     fig4.update_layout(
    #         yaxis=dict(visible=False), 
    #         xaxis=dict(visible=False),
    #         margin=dict(t=10, b=10, r=50) # Right margin prevents the end label from clipping
    #     )
    #     st.plotly_chart(fig4, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════
# SCENARIO 2 — IS FOIL WORTH IT?
# ═══════════════════════════════════════════════════════════════════════════
elif active == "foil":

    df_white = df[df["stock_type"] == "White"]
    df_foil  = df[df["stock_type"] == "Foil"]

    # Compute comparison metrics
    metrics = {
        "Avg Profit / Job": (
            df_white["gross_profit"].mean(),
            df_foil["gross_profit"].mean()
        ),
        "Avg Margin %": (
            df_white["gross_margin_pct"].mean(),
            df_foil["gross_margin_pct"].mean()
        ),
        "Waste Cost / Job": (
            waste_dollars(df_white) / len(df_white),
            waste_dollars(df_foil)  / len(df_foil)
        ),
        "Throughput (imp/hr)": (
            throughput(df_white),
            throughput(df_foil)
        ),
    }

    metric_labels = list(metrics.keys())
    white_vals = [metrics[m][0] for m in metric_labels]
    foil_vals  = [metrics[m][1] for m in metric_labels]

    comparison_df = pd.DataFrame({
        "Metric": metric_labels * 2,
        "Value":  white_vals + foil_vals,
        "Stock":  ["White"] * 4 + ["Foil"] * 4,
    })
    # Duarte callout
    margin_diff = foil_vals[1] - white_vals[1]
    waste_diff_foil = foil_vals[2] - white_vals[2]
    direction = "higher" if margin_diff > 0 else "lower"
    with placeholder:
            message = (
                f"<strong>Bottom line:</strong> Foil jobs have {abs(margin_diff):.1f} margin points {direction} than white, "
                f"but cost ${abs(waste_diff_foil):,.0f} more per job in waste. "
                f"{'The premium is covering it.' if margin_diff > 0 else 'The premium is not covering the operational cost.'}"
        )
        
        # Wrap it in a div that mimics Streamlit's st.info box but adds 'text-align: center'
            centered_html = f"""
                    <div style="background-color: rgba(28, 131, 225, 0.1); 
                                padding: 16px; 
                                border-radius: 8px; 
                                text-align: center; 
                                color: inherit; 
                                border: 1px solid rgba(28, 131, 225, 0.2);">
                        {message}
                    </div>
                    """
            
            # Render it using st.markdown with HTML enabled
            st.markdown(centered_html, unsafe_allow_html=True)
    with col1:
        data = comparison_df[comparison_df["Metric"] == "Avg Profit / Job"].copy()
        winner = "Foil" if foil_vals[0] > white_vals[0] else "White"
        
        # Define labels to force onto the traces
        labels = [f"<b>{row['Stock']}</b><br>${row['Value']:,.0f}" for _, row in data.iterrows()]

        st.subheader(f"{winner} Generates More Profit Per Job")
        st.caption("Average gross profit per job.")
        
        fig1 = px.bar(data, x="Stock", y="Value",
                     color="Stock",
                     color_discrete_map={"White": MUTED, "Foil": PRIMARY})
                     
        # Explicitly force the labels back into the traces
        for i, trace in enumerate(fig1.data):
            trace.text = [labels[i]]
            
        fig1.update_traces(
            textposition="inside", 
            insidetextanchor="middle",
            textfont=dict(size=18)
        )
        
        clean_layout(fig1)
        fig1.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False), margin=dict(t=10, b=0))
        st.plotly_chart(fig1, use_container_width=True,height=350)
        
    with col2:
        data = comparison_df[comparison_df["Metric"] == "Avg Margin %"].copy()
        winner = "Foil" if foil_vals[1] > white_vals[1] else "White"
        
        # Define labels to force onto the traces
        labels = [f"<b>{row['Stock']}</b><br>{row['Value']:.1f}%" for _, row in data.iterrows()]
        
        # Adding back the missing subheader and caption!
        st.subheader(f"{winner} Has Higher Margins")
        st.caption("Average gross margin percentage.")

        fig2 = px.bar(data, x="Stock", y="Value",
                     color="Stock",
                     color_discrete_map={"White": MUTED, "Foil": PRIMARY})
                     
        # Explicitly force the labels back into the traces
        for i, trace in enumerate(fig2.data):
            trace.text = [labels[i]]
            
        fig2.update_traces(
            textposition="inside", 
            insidetextanchor="middle",
            textfont=dict(size=18)
        )
        
        clean_layout(fig2)
        fig2.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False), margin=dict(t=10, b=0))
        st.plotly_chart(fig2, use_container_width=True,height=350)

    with col3:
        data = comparison_df[comparison_df["Metric"] == "Waste Cost / Job"].copy()
        winner = "White" if white_vals[2] < foil_vals[2] else "Foil"
        
        # Define labels to force onto the traces
        labels = [f"<b>{row['Stock']}</b><br>${row['Value']:,.0f}" for _, row in data.iterrows()]

        st.subheader(f"{winner} Wastes Less Per Job")
        st.caption("Average waste cost per job — material scrap + lost press time.")
        
        fig3 = px.bar(data, x="Stock", y="Value",
                     color="Stock",
                     color_discrete_map={"White": MUTED, "Foil": ACCENT})
                     
        # Explicitly force the labels back into the traces
        for i, trace in enumerate(fig3.data):
            trace.text = [labels[i]]
            
        fig3.update_traces(
            textposition="inside", 
            insidetextanchor="middle",
            textfont=dict(size=18)
        )
        
        clean_layout(fig3)
        fig3.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False), margin=dict(t=10, b=0))
        st.plotly_chart(fig3, use_container_width=True,height=350)

    # WHICH RUNS FASTER?
    # with col4:
    #     data = comparison_df[comparison_df["Metric"] == "Throughput (imp/hr)"]
    #     winner = "White" if white_vals[3] > foil_vals[3] else "Foil"
        
    #     labels = [f"<b>{row['Stock']}</b><br>{row['Value']:,.0f}" for _, row in data.iterrows()]

    #     st.subheader(f"{winner} Runs Faster")
    #     st.caption("Impressions per hour — foil runs slower by design.")
        
    #     fig4 = px.bar(data, x="Stock", y="Value",
    #                  color="Stock",
    #                  color_discrete_map={"White": PRIMARY, "Foil": MUTED})
                     
    #     fig4.update_traces(
    #         text=labels, 
    #         textposition="inside", 
    #         insidetextanchor="middle",
    #         textfont=dict(size=18)
    #     )
        
    #     clean_layout(fig4)
    #     fig4.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False), margin=dict(t=10, b=0))
    #     st.plotly_chart(fig4, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
# SCENARIO 3 — WHAT'S SLOWING US DOWN?
# ═══════════════════════════════════════════════════════════════════════════
elif active == "throughput":

    press_through = df.groupby("press").apply(
        lambda d: (d["qty_ordered"] * d["passes"]).sum() / d["total_press_time"].sum()
    ).sort_values()
    slowest = press_through.idxmin()

    with col1:
        labels_pt = [f"<b>{p}</b><br>{val:,.0f}/hr" for p, val in zip(press_through.index, press_through.values)]

        st.subheader(f"Press {slowest} Has the Lowest Throughput")
        st.caption("Impressions per hour by press — age degrades output directly.")
        
        fig1 = px.bar(press_through.reset_index(),
                     x="press", y=0,
                     category_orders={"press": press_through.index.tolist()})
                     
        fig1.update_traces(
            text=labels_pt,
            textposition="auto",
            textfont=dict(size=14),
            marker_color=[ACCENT if p == slowest else MUTED for p in press_through.index]
        )
        
        clean_layout(fig1)
        fig1.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False), margin=dict(t=10, b=0))
        st.plotly_chart(fig1, use_container_width=True,height=350)

    with col2:
        lost = df.groupby("press").apply(
            lambda d: pd.Series({
                "Jams":       d["jam_time_hrs"].sum(),
                "QC Stops":   d["qc_downtime_hrs"].sum(),
            })
        ).reset_index().melt(id_vars="press", var_name="Type", value_name="Hours")
        
        most_lost = df.groupby("press").apply(
            lambda d: d["jam_time_hrs"].sum() + d["qc_downtime_hrs"].sum()
        ).idxmax()
        
        st.subheader(f"Press {most_lost} Loses the Most Time")
        st.caption("Hours lost to jams and QC stops.")
        
        fig2 = px.bar(lost, x="press", y="Hours", color="Type",
                     color_discrete_map={"Jams": ACCENT, "QC Stops": "#F5A623"},
                     category_orders={"press": press_through.index.tolist()},
                     barmode="stack")
                     
        # Use texttemplate to format the segment values automatically
        fig2.update_traces(texttemplate='<b>%{y:.1f}h</b>', textposition='inside')

        # Press name in QC Stops segment (bigger, sits on top)
        for trace in fig2.data:
            if trace.name == "QC Stops":
                trace.text = [f"<b>{p}</b><br>{h:.1f}h" for p, h in zip(trace.x, trace.y)]
                trace.texttemplate = None
                trace.textposition = "inside"
                trace.insidetextanchor = "middle"

        
        clean_layout(fig2)
        # Keep X-axis for category names, drop Y-axis entirely, move legend to top
        fig2.update_layout(
            yaxis=dict(visible=False, range=[0, lost.groupby("press")["Hours"].sum().max() * 1.15]),
            xaxis=dict(visible = False, showgrid=False, title=None, tickfont=dict(size=14)),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=None),
            margin=dict(t=10, b=0)
        )
        st.plotly_chart(fig2, use_container_width=True,height=350)

    # PRESS THROUGHPUT ON WARE LEVELS
    # with col3:
    #     # 1. Calculate throughput per press safely (fixes the KeyError)
    #     age_through = df.groupby("press").apply(
    #         lambda d: (d["qty_ordered"] * d["passes"]).sum() / d["total_press_time"].sum()
    #     ).reset_index(name="throughput")

    #     # 2. Map the age factors safely
    #     age_through["age_factor"] = age_through["press"].apply(
    #         lambda p: scenario_overrides.get(f"AGE_FACTOR_{p}", base_overrides.get(f"AGE_FACTOR_{p}", 1.2))
    #     )
        
    #     # 3. Identify the worst performer to highlight
    #     worst_press = age_through.loc[age_through['throughput'].idxmin(), 'press']
    #     worst_throughput = age_through['throughput'].min()
    #     worst_age = age_through.loc[age_through['throughput'].idxmin(), 'age_factor']

    #     st.subheader("Worse Condition = Lower Output")
    #     st.caption("Press throughput based on wear level.")
        
    #     fig3 = px.scatter(age_through, x="age_factor", y="throughput")
        
    #     # Emphasize the worst press with color and size; keep others standard
    #     fig3.update_traces(
    #         marker=dict(
    #             size=[16 if p == worst_press else 10 for p in age_through['press']],
    #             color=[ACCENT if p == worst_press else PRIMARY for p in age_through['press']]
    #         )
    #     )
        
    #     # Direct Annotation ONLY for the worst press
    #     fig3.add_annotation(
    #         x=worst_age, y=worst_throughput,
    #         text=f"<b>Press {worst_press}</b><br>{worst_throughput:,.0f}/hr",
    #         showarrow=False,
    #         yshift=-25, 
    #         font=dict(color=ACCENT, size=13)
    #     )
        
    #     clean_layout(fig3)
        
    #     # THE FIX: Reverse the X-axis. 
    #     # This puts the best presses in the "top right" and the worst in the "bottom left".
    #     fig3.update_layout(
    #         yaxis=dict(title="Impressions / hr", showgrid=True, gridcolor="#EEEEEE", zeroline=False, tickformat=","),
    #         xaxis=dict(title="← Worse Condition | Better Condition →", showgrid=False, zeroline=False, autorange="reversed"),
    #         margin=dict(t=10, b=10)
    #     )
        
    #     st.plotly_chart(fig3, use_container_width=True)
    with col3:
        qc = df.groupby("press")["quality_pass"].apply(
            lambda x: (1 - x.mean()) * 100
        ).sort_values(ascending=False)
        wq = qc.idxmax()
        fleet_avg_qc = qc.mean()
        
        labels_qc = [f"<b>{p}</b><br>{val:.1f}%" for p, val in zip(qc.index, qc.values)]

        st.subheader(f"Press {wq} Fails QC at {qc[wq]:.1f}%")
        st.caption(f"QC failures stop the press. Fleet average is {fleet_avg_qc:.1f}%.")
        
        fig4 = px.bar(qc.reset_index(),
                     x="press", y="quality_pass",
                     category_orders={"press": qc.index.tolist()})
                     
        fig4.update_traces(
            text=labels_qc,
            textposition="auto",
            textfont=dict(size=14),
            marker_color=[ACCENT if p == wq else MUTED for p in qc.index]
        )
        
        # Add Tufte Reference Line
        fig4.add_hline(y=fleet_avg_qc, line_dash="dash", line_color="#888888",
                      annotation_text=f"Avg: {fleet_avg_qc:.1f}%",
                      annotation_position="top right")
                      
        clean_layout(fig4)
        fig4.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False), margin=dict(t=10, b=0))
        st.plotly_chart(fig4, use_container_width=True,height=350)


# ── RAW DATA ──────────────────────────────────────────────────────────────
with st.expander("Show raw data sample"):
    st.dataframe(df.head(50))