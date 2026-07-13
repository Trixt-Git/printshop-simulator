"""
FloorPlan — Press Room Decision Engine
========================================
Production improvement advisor for the floor manager.
One screen. Three modes. Same math.

Run: streamlit run floorplan_app.py

Requires floorplan_calculator.py in the same directory.
"""

import streamlit as st
import plotly.graph_objects as go
import sys, os, copy
import pandas as pd


sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from floorplan_calculator import (
    DEFAULT_PRESS_CONFIG,
    DEFAULT_DOWNTIME_CONFIG,
    fleet_summary,
    rank_opportunities,
    what_would_it_take,
    lever_impact,
)

# ── CONFIG ────────────────────────────────────────────────────────────────
IMPROVEMENT_PCT   = 0.2
LEVER_LABELS = {
    "maintenance": "Unplanned Maint. & Breakdowns", "jams": "Jams",
    "materials_wait": "Materials Wait", "shift_handoff": "Shift Handoff",
    "quality_approval": "Quality Wait", "manager_approval": "Approval Wait",
    "makeready": "Makeready / Setup",
    "speed":"Running Speed Increase",
}
LEVER_TYPE = {
    "maintenance": "Mechanical", "jams": "Mechanical",
    "materials_wait": "Process", "shift_handoff": "Process",
    "quality_approval": "Process", "manager_approval": "Process",
    "makeready": "Process",
    "speed":"Process",

}
DOWNTIME_CODE_MAP = {
    "maintenance": ["2011 (Unplanned Maint)", "2000 (Breakdown Mech)", "2001 (Breakdown Elec)"],
    "jams": ["2070 (Jam/Trip)", "2085 (Problem: Print Unit)", "2086 (Material Feeder)", "2087 (UV/IR Lamp)", "2097 (Problem: Feeder)"],
    "materials_wait": ["2090 (Wait for Material)", "2095 (Replace Materials)"],
    "shift_handoff": ["2040 (Shift Change/Handoff)"],
    "quality_approval": ["2120 (Quality Wait)", "2123 (Waiting for Quality)"],
    "manager_approval": ["2080 (Wait for Approval)", "2121 (Sales Wait)", "2124 (Waiting for Sales)", "2125 (Waiting for Customer)"],
    "makeready": ["1000 (Make Ready 1)", "1010 (Make Ready 2)", "1060 (Cleanup/Washup)", "2075 (Wash Plates/Blankets)", "2076 (Set-Up Adjustment)","2083 (Plate Change)", "2084 (Anilox Roller Change)"],
}

CODE_HOUR_SPLITS = {
    "4210": {
        "maintenance":      {"2001": 5.67,  "2000": 9.67, "2011": 18.69},
        "jams":             {"2086": 0.48, "2087": 4.68,  "2097": 1.49,  "2070": 2.82,  "2085": 32.26},
        "shift_handoff":    {"2040": 16.18},
        "materials_wait":   {"2095": 0.17, "2090": 1.23},
        "quality_approval": {"2123": 0.26, "2120": 2.22},
        "manager_approval": {"2080": 4.84, "2122": 0,  "2121": 0,  "2124": 0,  "2125": 0},
        "makeready":        {"1010": 52.43,"1000": 10.21, "2075": 34.9,"2076": 13.26,"1060": 15.51,"2083": 21.85,"2082": 5.73, "2084": 0},
    },
    "4180": {
        "maintenance":      {"2001": 5.88, "2000": 20.19, "2011": 10.2},
        "jams":             {"2086": 5.74, "2087": 0.64,  "2097": 6.86,   "2070": 33.04, "2085": 13.76},
        "shift_handoff":    {"2040": 4.46},
        "materials_wait":   {"2095": 0.06, "2090": 9.5},
        "quality_approval": {"2123": 0.15, "2120": 4.13},
        "manager_approval": {"2080": 5.32, "2122": 0.77, "2121": 0.25, "2124": 0,  "2125": 0},
        "makeready":        {"1010": 130.96,"1000": 46.37,"2075": 18.51,"2076": 3.44, "1060": 5.85, "2083": 0.6, "2082": 8.14, "2084": 1.42},
    },
    "4140": {
        "maintenance":      {"2001": 9.78, "2000": 26.66,  "2011": 9.68},
        "jams":             {"2086": 34.29,"2087": 1.38,  "2097": 3.85,  "2070": 21.11, "2085": 17.79},
        "shift_handoff":    {"2040": 4.37},
        "materials_wait":   {"2095": 14.54,"2090": 8},
        "quality_approval": {"2123": 2.41,  "2120": 5.68},
        "manager_approval": {"2080": 1.66, "2122": 0,  "2121": 0,  "2124": 0.02, "2125": 0},
        "makeready":        {"1010": 76.66,"1000": 10.9,  "2075": 51.13, "2076": 8.19, "1060": 17.77,"2083": 5.28, "2082": 17.58,"2084": 1.22},
    },
    "4520": {
        "maintenance":      {"2001": 2.23, "2000": 11.64, "2011": 4.13},
        "jams":             {"2086": 4.47, "2087": 0,   "2097": 8.24,  "2070": 21.76, "2085": 7.48},
        "shift_handoff":    {"2040": 3.52},
        "materials_wait":   {"2095": 1.19, "2090": 5.51},
        "quality_approval": {"2123": 0.03, "2120": 0.47},
        "manager_approval": {"2080": 3.29, "2122": 0.2, "2121": 0,  "2124": 0,  "2125": 0.06},
        "makeready":        {"1010": 34.64,"1000": 9.66, "2075": 26.17,"2076": 4.61, "1060": 16.45,"2083": 0.68, "2082": 2.05, "2084": 0.23},
    },
    "4360": {
        "maintenance":      {"2001": 5.38, "2000": 5.78,  "2011": 1.12},
        "jams":             {"2086": 2.77, "2087": 0,   "2097": 10.62, "2070": 6.94,  "2085": 3.95},
        "shift_handoff":    {"2040": 1.74},
        "materials_wait":   {"2095": 0.69, "2090": 4.15},
        "quality_approval": {"2123": 0.12, "2120": 0.17},
        "manager_approval": {"2080": 0.35, "2122": 0,  "2121": 0,  "2124": 0,  "2125": 0},
        "makeready":        {"1010": 14.7, "1000": 4.5,  "2075": 9.53, "2076": 1.68,  "1060": 6.92, "2083": 0.14, "2082": 1, "2084": 0},
    },
    "4080": {
        "maintenance":      {"2001": 2.42, "2000": 12.95, "2011": 13.62},
        "jams":             {"2086": 3.98, "2087": 14.57, "2097": 2.28,  "2070": 0.42,  "2085": 21.25},
        "shift_handoff":    {"2040": 11.55},
        "materials_wait":   {"2095": 0.49, "2090": 5.96},
        "quality_approval": {"2123": 0,  "2120": 0.06},
        "manager_approval": {"2080": 1.32, "2122": 0,  "2121": 0,  "2124": 0,  "2125": 0},
        "makeready":        {"1010": 49.37,"1000": 6.26,   "2075": 4.63,  "2076": 18.87,"1060": 7.49, "2083": 2.69, "2082": 1.48, "2084": 0},
    },
}


C_DARK, C_MID, C_MUTED, C_WHITE = "#111827", "#374151", "#6B7280", "#FFFFFF"
C_ACCENT, C_ALERT, C_OK = "#2563EB", "#DC2626", "#16A34A"

def fmt_k(n):
    if abs(n) >= 1_000_000: return f"{n/1_000_000:.2f}M"
    if abs(n) >= 1_000: return f"{n/1_000:.0f}K"
    return str(n)

def fmt_hrs(h): return f"{h:.1f} hrs"

# ── PAGE SETUP & STYLING ──────────────────────────────────────────────────
st.set_page_config(page_title="FloorPlan", layout="wide", initial_sidebar_state="collapsed")

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');

    [data-testid="stHeader"] {{ display: none !important; }}
    [data-testid="stAppViewBlockContainer"] {{ padding-top: 0rem !important; margin-top: -4rem !important; }}
    .stAppViewMain .block-container {{ padding: 1rem 2.5rem 0rem 2.5rem !important; max-width: 1200px; }}

    html, body, [class*="css"] {{ font-family: 'IBM Plex Sans', sans-serif; background-color: {C_DARK}; color: {C_WHITE}; }}

/* 3. KPI tiles - Centered & Tightened */
    .kpi-block {{
        background: {C_MID};
        border-radius: 4px;
        padding: 0.7rem 1rem;
        border-left: 3px solid {C_ACCENT};
        text-align: center;
        min-height: 90px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }}
    .kpi-block.alert {{ border-left-color: {C_ALERT}; }}
    .kpi-block.ok {{ border-left-color: {C_OK}; }}
    
    .kpi-label {{
        font-size: 0.72rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: {C_MUTED};
        font-weight: 600;
        margin-bottom: 0.2rem;
    }}
    .kpi-value {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1.8rem;
        font-weight: 600;
        color: {C_WHITE};
        line-height: 1.1;
    }}
    .kpi-sub {{
        font-size: 0.75rem;
        color: {C_MUTED};
        margin-top: 0.2rem;
    }}

    .section-label {{ font-size: 0.68rem; letter-spacing: 0.15em; text-transform: uppercase; color: {C_MUTED}; font-weight: 600; margin-bottom: 0.8rem; margin-top: 1.5rem; }}

    div[data-testid="stButton"] > button {{ background: {C_MID}; color: {C_WHITE}; border: 1px solid #4B5563; border-radius: 4px; width: 100%; font-weight: 600; }}
    div[data-testid="stButton"] > button:hover {{ background: {C_ACCENT}; border-color: {C_ACCENT}; }}

    .lever-card {{ background: {C_MID}; border-radius: 4px; padding: 1rem 1.2rem; margin-bottom: 0.6rem; border-left: 3px solid {C_ACCENT}; display: flex; justify-content: space-between; align-items: center; }}
    .lever-card.top {{ border-left-color: {C_OK}; background: #1a2e1a; }}
    .lever-gain {{ font-family: 'IBM Plex Mono', monospace; font-size: 1.1rem; font-weight: 600; color: {C_OK}; }}

    .result-callout {{ background: #1e3a5f; border: 1px solid {C_ACCENT}; border-radius: 4px; padding: 1rem 1.5rem; text-align: center; }}
    .result-callout.success {{ background: #14290f; border-color: {C_OK}; }}
    
    hr {{ border-color: #374151 !important; margin: 1.2rem 0 !important; }}
    div[data-testid="stNumberInput"] button {{ display: flex !important; }}
    div[data-testid="stPopoverBody"] {{ padding: 0.5rem !important; }}
    footer {{ visibility: hidden; }}
</style>
""", unsafe_allow_html=True)

# ── SESSION STATE (CLEANED) ───────────────────────────────────────────────
if "question" not in st.session_state: st.session_state.question = "losses"
if "fwd_press" not in st.session_state: st.session_state.fwd_press = "All"
if "fwd_cat" not in st.session_state: st.session_state.fwd_cat = "jams"
if "fwd_pct" not in st.session_state: st.session_state.fwd_pct = 0
if "target_pct" not in st.session_state: st.session_state.target_pct = 10
if "plan_moves" not in st.session_state: st.session_state.plan_moves = []
if "group_fleet_losses" not in st.session_state:
    st.session_state.group_fleet_losses = False
if "dd_group_mode" not in st.session_state:
    st.session_state.dd_group_mode = "detailed"


# press_config lives in session state so settings panel edits flow into all calculations.
# It starts as a deep copy of the defaults — user changes never touch the source of truth.
if "press_config" not in st.session_state:
    st.session_state.press_config = copy.deepcopy(DEFAULT_PRESS_CONFIG)

# ── HELPER: MINUTES PER SHIFT ─────────────────────────────────────────────
def mins_per_shift(hours: float, cfg: dict) -> float:
    """Convert total monthly hours to average minutes lost per shift.

    Learning note: we compute total_shifts from the config rather than
    accepting it as a parameter — keeps the function self-contained and
    avoids the caller needing to know the shift math.
    """
    shifts_per_day = 2 if cfg["night_shift"] else 1
    total_shifts = cfg["days_scheduled"] * shifts_per_day
    if total_shifts == 0:
        return 0.0
    return round((hours * 60) / total_shifts, 1)

def fmt_mps(hours: float, cfg: dict) -> str:
    """Format mins-per-shift as a short readable string."""
    mps = mins_per_shift(hours, cfg)
    return f"{mps:.0f} min/shift"

# ── HEADER ────────────────────────────────────────────────────────────────
col_head, col_targ = st.columns([6, 1])
fleet      = fleet_summary(st.session_state.press_config, DEFAULT_DOWNTIME_CONFIG)
current    = fleet["total_reality"]
with col_head:
    st.markdown(f"""
        <div style="font-size: 2rem; font-weight: 700; margin-bottom: 0rem; line-height: 1.2;">FloorPlan</div>
        <div style="color:{C_MUTED}; font-size: 0.8rem; margin-top: 0.1rem; margin-bottom: 1rem;">Press Room Decision Engine · Calibrated Q1–Apr 2026</div>
    """, unsafe_allow_html=True)

with col_targ:
    st.markdown("<div style='margin-top:0.8rem;'></div>", unsafe_allow_html=True)
    with st.popover("+/- Target", use_container_width=True):

        # Toggle mode
        if "target_mode" not in st.session_state:
            st.session_state.target_mode = "pct"

        if st.session_state.target_mode == "pct":
            st.number_input(
                "Growth Goal (%)",
                min_value=1,
                max_value=200,
                value=int(st.session_state.target_pct),
                step=1,
                format="%d",
                label_visibility="collapsed",
                key="target_pct",
            )
        else:
            new_sheets = st.number_input(
                "Target Sheets",
                min_value=int(current * 1.01),
                max_value=int(current * 3),
                value=int(current * (1 + st.session_state.target_pct / 100)),
                step=10000,
                label_visibility="collapsed",
                key="input_target_sheets",
            )
            # Convert sheets → pct so the rest of the app stays unchanged
            st.session_state.target_pct = round((new_sheets / current - 1) * 100, 1)

        # Toggle button
        mode_label = "Switch to Sheets" if st.session_state.target_mode == "pct" else "Switch to %"
        if st.button(mode_label, key="btn_target_mode", use_container_width=True):
            st.session_state.target_mode = "sheets" if st.session_state.target_mode == "pct" else "pct"
            st.rerun()


# ── COMPUTE BASELINE (Only happens once here, after the input) ───────────
TARGET_GROWTH_PCT = st.session_state.target_pct / 100
ui_target_pct = st.session_state.target_pct


target     = round(current * (1 + TARGET_GROWTH_PCT))
gap        = target - current
all_levers = rank_opportunities(st.session_state.press_config, DEFAULT_DOWNTIME_CONFIG, IMPROVEMENT_PCT)

# ── KPI STRIP ─────────────────────────────────────────────────────────────
k1, k2, k3 = st.columns(3)
with k1:
    st.markdown(f'<div class="kpi-block"><div class="kpi-label">Monthly Output</div><div class="kpi-value">{fmt_k(current)}</div><div class="kpi-sub">sheets produced</div></div>', unsafe_allow_html=True)
with k2:
    st.markdown(f'<div class="kpi-block alert"><div class="kpi-label">Gap to Target</div><div class="kpi-value" style="color:{C_ALERT};">-{fmt_k(gap)}</div><div class="kpi-sub">+{ui_target_pct}% growth goal · target {fmt_k(target)}</div></div>', unsafe_allow_html=True)
with k3:
    goal_sheets = fmt_k(target)
    goal_pct    = ui_target_pct
    sheets_left = fmt_k(gap)
    st.markdown(f"""
    <div class="kpi-block">
        <div class="kpi-label">Goal</div>
        <div class="kpi-value">{goal_sheets}</div>
        <div class="kpi-sub">+{goal_pct}% target · {sheets_left} to go</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)



# ── QUESTION BUTTONS ──────────────────────────────────────────────────────
q1, q2, q3, q4, spacer, q5 = st.columns([3,3,3,3,6,2])
if q1.button("📊 Biggest losses", key="btn_loss",use_container_width=True): st.session_state.question = "losses"; st.rerun()
if q2.button("🎯 Path to target", key="btn_bwd",use_container_width=True): st.session_state.question = "backward"; st.rerun()
if q3.button("🔧 Build a plan", key="btn_plan",use_container_width=True): st.session_state.question = "plan"; st.rerun()
if q4.button("Deep Dive 🔍", use_container_width=True): st.session_state.question = "deep_dive";st.rerun()
if q5.button("Reset", key="btn_reset",use_container_width=True): 
    st.session_state.question = "losses"; st.session_state.fwd_pct = 0
    st.session_state.plan_moves = []; st.rerun()

#Order was switched, Losses is now default view.

# ══════════════════════════════════════════════════════════════════════════
# BACKWARD — What do we need to hit target?
# ══════════════════════════════════════════════════════════════════════════
elif st.session_state.question == "backward":
    st.markdown("<hr>", unsafe_allow_html=True)

    plan = what_would_it_take(target, st.session_state.press_config, DEFAULT_DOWNTIME_CONFIG, IMPROVEMENT_PCT)

    _, col_status, _ = st.columns([1, 4, 1])

    # ── LEVER GRID ───────────────────────────────────────────────────────
    st.markdown(
            """
            <div style="margin-top: -2rem; margin-bottom: 1rem; font-size: 0.9rem; color: #9CA3AF; text-align: left;">
                <i>All items show 20% improvement to hit +10% target</i>
            </div>
            """, 
            unsafe_allow_html=True
        )


    card_cols = st.columns(2)
    cum_closed = 0
    
    for i, lev in enumerate(plan["levers"]):
        cum_closed += lev["pct_of_gap"]
        label      = LEVER_LABELS.get(lev["category"], lev["category"])
        ltype      = LEVER_TYPE.get(lev["category"], "")
        p_cfg      = st.session_state.press_config[lev["press"]]
        
        cfg = p_cfg
        shifts_per_day = 2 if cfg["night_shift"] else 1
        total_shifts = cfg["days_scheduled"] * shifts_per_day
        
        if lev["category"] == "makeready":
            baseline = round(total_shifts * (cfg["makeready_mins_per_shift"] / 60), 1)
        else:
            baseline = DEFAULT_DOWNTIME_CONFIG[lev["press"]].get(lev["category"], 0)
            
        target_hrs = round(baseline - lev["hours_saved"], 1)
        mps_str    = fmt_mps(baseline, p_cfg)
        is_top     = (i == 0)
        card_class = "lever-card top" if is_top else "lever-card"

        reduction_display = int(lev['reduction_pct'] * 100)
        hrs = lev.get('hours_saved', 0)
        
        with card_cols[i % 2]:
            border_color = C_OK if i == 0 else C_ACCENT
            # Calculate current mins per shift and the new target
            current_mps_val = (baseline * 60) / total_shifts
            target_mps_val  = current_mps_val * (1 - lev['reduction_pct'])
            
            # Format for display
            current_mps_str = f"{int(current_mps_val)}m"
            target_mps_str  = f"{int(target_mps_val)}m"
            card_html = (
                f'<div style="padding: 0.75rem 1rem; border-radius: 8px; border: 1px solid #2D3748; '
                f'border-left: 4px solid {border_color}; background: #1E293B; margin-bottom: 0.75rem; '
                f'display: flex; align-items: center; justify-content: center; text-align: center;">'
                
                # LEFT: Press Identity + The Action (Now on its own line)
                f'<div style="flex: 1; min-width: 0;">'
                f'<div style="font-size: 0.8rem; font-weight: 600; color: #9CA3AF;">#{i+1}: Press {lev["press"]}</div>'
                f'<div style="font-size: 0.95rem; font-weight: 700; color: #FFFFFF; text-transform: uppercase;">{label}</div>'
                f'</div>'
                
                # CENTER: Current to Goal Transition
                f'<div style="flex: 1.5; display: flex; flex-direction: column; justify-content: center; '
                f'border-left: 1px solid #334155; border-right: 1px solid #334155; margin: 0 0.5rem; padding: 0 0.5rem;">'
                f'<div style="font-size: 0.85rem; font-weight: 700; color: #FFFFFF;">'
                f'<span style="color: #9CA3AF; font-weight: 400; font-size: 0.85rem;">SHIFT GOAL:</span> {target_mps_str}'
                f'</div>'
                f'<div style="font-size: 0.8rem; color: #EF4444; margin-top: 0.1rem;">'
                f'<span style="font-size: 0.7rem;">▼</span> Current: {current_mps_str}'
                f'</div>'
                f'</div>'
                
                # RIGHT: The Output
                f'<div style="flex: 1;">'
                f'<div style="font-size: 1.5rem; font-weight: 800; color: {border_color}; line-height: 1;">'
                f'+{fmt_k(lev["closes_sheets"])}'
                f'</div>'
                f'<div style="font-size: 0.7rem; font-weight: 600; color: #9CA3AF; text-transform: uppercase; margin-top: 0.2rem;">Sheets</div>'
                f'</div>'
                
                f'</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    # ── WATERFALL CHART ──────────────────────────────────────────────────
    if plan["levers"]:

        labels   = ["Now"]
        measures = ["absolute"]
        values   = [current]
        texts    = [f"Now<br><b>{fmt_k(current)} sheets</b>"]
        positions = ["inside"]


        for i, lev in enumerate(plan["levers"]):
            label     = LEVER_LABELS.get(lev["category"], lev["category"])
            short     = f"#{i+1} {lev['press']}<br>{label}"
            labels.append(short)
            measures.append("relative")
            values.append(lev["closes_sheets"])
            texts.append(f"{short}<br><b>+{fmt_k(lev['closes_sheets'])}</b>")
            positions.append("auto")

        if not plan["fully_closeable"] and plan["gap_remaining"] > 0:
            labels.append("Shortfall")
            measures.append("relative")
            values.append(plan["gap_remaining"])
            texts.append(f"-{fmt_k(plan['gap_remaining'])}")
            positions.append("auto")

        labels.append("Target")
        measures.append("total")
        values.append(target)
        texts.append(f"Target<br><b>{fmt_k(target)}</b>")
        positions.append("inside")

        y_min = current * .97
        y_max = target  * 1.02

        fig_wf = go.Figure(go.Waterfall(
            orientation = "v",
            measure     = measures,
            x           = labels,
            y           = values,
            text        = texts,
            textposition= positions,
            textfont    = dict(family="IBM Plex Sans", size=11, color=C_WHITE),
            connector   = dict(line=dict(color="#4B5563", width=1, dash="dot")),
            increasing  = dict(marker_color=C_ACCENT),
            decreasing  = dict(marker_color=C_ALERT),
            totals      = dict(marker_color=C_MID),
        ))


        fig_wf.update_layout(
            height          = 350,
            margin          = dict(l=0, r=20, t=40, b=0),
            paper_bgcolor   = "rgba(0,0,0,0)",
            plot_bgcolor    = "rgba(0,0,0,0)",
            showlegend      = False,
            xaxis           = dict(visible=False),
            yaxis           = dict(
                visible     = False,  
                range       = [y_min, y_max],
            ),
            waterfallgap    = 0.3,
        )

        st.plotly_chart(fig_wf, use_container_width=True, config={"displayModeBar": False})
        
# ══════════════════════════════════════════════════════════════════════════
# LOSSES — What are our biggest issues?
# ══════════════════════════════════════════════════════════════════════════
elif st.session_state.question == "losses":
    
    # Ensure state exists
    if "group_fleet_losses" not in st.session_state:
        st.session_state.group_fleet_losses = False

    # ── HEADER ROW WITH BUTTON ──────────────────────────────────────────
    col_title, col_btn = st.columns([4, 1], vertical_alignment="bottom")
    
    with col_title:
        st.markdown('<div class="section-label" style="margin-top:0.5rem; margin-bottom: 0.5rem;">Top Sheet Losses Per Month</div>', unsafe_allow_html=True)
        
    with col_btn:
        btn_text = "Ungroup Presses" if st.session_state.group_fleet_losses else "Group All Presses"
        if st.button(btn_text, key="btn_group_all", use_container_width=True):
            st.session_state.group_fleet_losses = not st.session_state.group_fleet_losses
            st.rerun()

    # ── DATA PREPARATION ────────────────────────────────────────────────
    levers_raw = rank_opportunities(st.session_state.press_config, DEFAULT_DOWNTIME_CONFIG, reduction_pct=1.0)
    levers_full = [l for l in levers_raw if l["category"] != "speed"]
    
    # Apply Grouping Logic if toggle is active
    if st.session_state.group_fleet_losses:
        grouped_levers = {}
        for l in levers_full:
            cat = l["category"]
            if cat not in grouped_levers:
                grouped_levers[cat] = {
                    "category": cat,
                    "press": "All",
                    "sheets_gained": 0,
                    "hours_saved": 0
                }
            grouped_levers[cat]["sheets_gained"] += l["sheets_gained"]
            grouped_levers[cat]["hours_saved"] += l["hours_saved"]
        
        # Convert dictionary back to list and sort by sheets_gained descending
        levers_to_process = list(grouped_levers.values())
        levers_to_process.sort(key=lambda x: x["sheets_gained"], reverse=True)
    else:
        levers_to_process = levers_full
    
    if 'show_all_losses' not in st.session_state:
        st.session_state.show_all_losses = False  
        
    top_n  = len(levers_to_process) if st.session_state.show_all_losses else min(10, len(levers_to_process))
    levers = levers_to_process[:top_n]

    # ── CHART FORMATTING ────────────────────────────────────────────────
    bar_labels = []
    bar_text = []
    bar_mps = []
    
    for l in levers:
        cat_label = LEVER_LABELS.get(l['category'], l['category'])
        v = l["sheets_gained"]
        
        if l['press'] == "All":
            bar_labels.append(f" ~ {cat_label}")
            bar_text.append(f" ~ {cat_label}    ({fmt_k(v)})")
            
            # Calc fleet-wide average MPS
            total_shifts = 0
            for p_id, p_cfg in st.session_state.press_config.items():
                total_shifts += p_cfg["days_scheduled"] * (2 if p_cfg["night_shift"] else 1)
            mps_val = (l["hours_saved"] * 60) / total_shifts if total_shifts > 0 else 0
            bar_mps.append(f"{int(mps_val)} min/shift (fleet avg)")
        else:
            bar_labels.append(f"Press {l['press']} · {cat_label}")
            bar_text.append(f"  Press {l['press']} · {cat_label}    ({fmt_k(v)})")
            bar_mps.append(fmt_mps(l["hours_saved"], st.session_state.press_config[l["press"]]))

    bar_vals   = [l["sheets_gained"] for l in levers]
    bar_hrs    = [l["hours_saved"] for l in levers]
    bar_colors = [C_OK if i == 0 else C_ACCENT if i <= 2 else C_MID for i in range(top_n)]

    dynamic_height = top_n * 35
    fig = go.Figure(go.Bar(
        x=bar_vals,
        y=bar_labels,  # Keep this for the hover popup
        orientation="h",
        marker_color=bar_colors,
        text=bar_text,
        textposition="auto",
        insidetextanchor="start",  # Anchors text to the left side of the bar
        textfont=dict(family="IBM Plex Sans", size=13, color=C_WHITE),
        hovertemplate="<b>%{y}</b><br>+%{x:,.0f} sheets (100% recovery)<br>%{customdata[0]:.1f} hrs/month · <b>%{customdata[1]}</b><extra></extra>",
        customdata=list(zip(bar_hrs, bar_mps)),
    ))

    fig.update_layout(
        height=dynamic_height,
        margin=dict(l=0, r=0, t=10, b=0),  # Removed left/right margins to maximize bar width
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(
            visible=False, 
            autorange="reversed",
        ),
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    
    col_btn_show, _ = st.columns([1, 2])
    with col_btn_show:
        if not st.session_state.show_all_losses:
            if st.button("Show all↓"):
                st.session_state.show_all_losses = True
                st.rerun()
        else:
            if st.button("Show less ↑"):
                st.session_state.show_all_losses = False
                st.rerun()
                
    st.markdown(f"<div style='color:{C_MUTED};font-size:0.72rem;margin-top:-0.5rem;text-align:center;'>Green = highest impact · shows 100% theoretical recovery · hover for hrs/month and min/shift · calibrated to real Apr 2026 data</div>", unsafe_allow_html=True)
# ══════════════════════════════════════════════════════════════════════════
# PLAN — Build a cumulative improvement plan
# ══════════════════════════════════════════════════════════════════════════
elif st.session_state.question == "plan":
    st.markdown("<hr>", unsafe_allow_html=True)

    # ── 1. CUMULATIVE IMPACT CALCULATION ─────────────────────────────────
    claimed = {}
    results = []

    for move in st.session_state.plan_moves:
        p_list = list(st.session_state.press_config.keys()) if move["press"] == "All" else [move["press"]]
        m_gain, m_used, m_saved = 0, 0, 0
        for p in p_list:
            already = claimed.get(p, 0)
            impact = lever_impact(p, move["category"], move["pct"] / 100, st.session_state.press_config, DEFAULT_DOWNTIME_CONFIG, hours_already_claimed=already)
            claimed[p] = already + impact["hours_used"]
            m_gain += impact["sheets_gained"]; m_used += impact["hours_used"]; m_saved += impact["hours_saved"]
            
        results.append({"press": move["press"], "category": move["category"], "pct": move["pct"], "sheets_gained": m_gain, "hours_used": m_used, "hours_saved": m_saved})

    total_gained = sum(r["sheets_gained"] for r in results)
    total_hrs = sum(r["hours_used"] for r in results)
    new_total = current + total_gained
    gap_closed = round(total_gained / gap * 100, 1) if gap > 0 else 100
    
    # ── 2. PLAN SUMMARY CALLOUT ──────────────────────────────────────────
    bar_color = C_OK if gap_closed >= 100 else C_ACCENT
    callout_cls = "result-callout success" if gap_closed >= 100 else "result-callout"
    st.markdown(f'<div class="{callout_cls}" style="padding:0.6rem 1rem;display:flex;justify-content:space-between;align-items:center;margin-bottom:1.5rem;"><div style="display:flex;align-items:baseline;gap:0.8rem;"><span style="font-size:1rem;letter-spacing:0.12em;text-transform:uppercase;color:{C_MUTED};">Plan total</span><span style="font-family:\'IBM Plex Mono\',monospace;font-size:1.5rem;font-weight:700;color:{bar_color};">+{fmt_k(total_gained)}</span></div><div style="font-size:1rem;color:{C_MUTED};">New total: <span style="color:{C_WHITE};">{fmt_k(new_total)}</span> &nbsp;·&nbsp; Gap closed: <span style="color:{C_WHITE};">{gap_closed:.0f}%</span> &nbsp;·&nbsp; <span style="color:{C_WHITE};">{fmt_hrs(total_hrs)}</span> recovered</div></div>', unsafe_allow_html=True)

    # ── 3. INPUT ROW ─────────────────────────────────────────────────────
    col_p, col_c, col_pct, col_prev, col_add = st.columns([1.5, 2.5, 1.5, 2.5, 1.2])
    with col_p: add_press = st.selectbox("Press", options=["All"] + list(st.session_state.press_config.keys()), key="plan_press")
    with col_c: add_cat = st.selectbox("What to improve", options=list(LEVER_LABELS.keys()), format_func=lambda x: LEVER_LABELS[x], key="plan_cat")
    with col_pct: add_pct = st.slider("By how much?", 0, 100, 0, step=5, format="%d%%", key="plan_pct")

    # Preview Calc
    p_list_prev = list(st.session_state.press_config.keys()) if add_press == "All" else [add_press]
    p_gain, p_hrs, p_save = 0, 0, 0
    for p in p_list_prev:
        impact = lever_impact(p, add_cat, add_pct/100, st.session_state.press_config, DEFAULT_DOWNTIME_CONFIG, hours_already_claimed=claimed.get(p, 0))
        p_gain += impact["sheets_gained"]; p_hrs += impact["hours_used"]; p_save += impact["hours_saved"]
    
    with col_prev:
        warn_msg = f"<span style='color:{C_ALERT};font-size:0.85rem;margin-left:0.4rem;' title='Clipped'>⚠</span>" if p_hrs < p_save and add_cat != "speed" else ""
        st.markdown(f'<div style="margin-top:1.73rem;background:{C_MID};border:1px solid #4B5563;border-radius:4px;padding:0.65rem 0.5rem;display:flex;justify-content:center;align-items:center;line-height:1.2;"><span style="font-size:0.85rem;color:{C_MUTED};text-transform:uppercase;letter-spacing:0.05em;margin-right:0.6rem;">Sheets:</span><span style="font-family:\'IBM Plex Mono\',monospace;color:{C_OK};font-size:1.05rem;font-weight:700;">+{fmt_k(p_gain)}</span>{warn_msg}</div>', unsafe_allow_html=True)

    with col_add:
        st.markdown("<div style='margin-top:1.73rem;'></div>", unsafe_allow_html=True)
        if st.button("＋ Add", key="btn_add_move", use_container_width=True):
            st.session_state.plan_moves.append({"press": add_press, "category": add_cat, "pct": add_pct})
            st.rerun()

    # ── 4. THE MASTER STACKED BAR ────────────────────────────────────────
    st.markdown('<div class="section-label" style="margin-top:1.5rem;margin-bottom:0.5rem;">Visualized Plan Growth</div>', unsafe_allow_html=True)
    bar_colors_list = [C_OK, C_ACCENT, "#F59E0B", "#06B6D4", "#8B5CF6", "#EC4899", "#14B8A6"]
    
    committed_slices_html = ""
    for i, r in enumerate(results):
        w = (r["sheets_gained"] / gap * 100) if gap > 0 else 0
        label = LEVER_LABELS.get(r["category"], r["category"])
        display_press = "Fleet Wide" if r['press'] == "All" else f"Press {r['press']}"
        bg_color = bar_colors_list[i % len(bar_colors_list)]
        p_ids = list(st.session_state.press_config.keys()) if r['press'] == "All" else [r['press']]
        
        if r["category"] == "speed":
            avg_sph = sum(st.session_state.press_config[p].get("effective_sph", 0) for p in p_ids) / len(p_ids)
            detail_str = f"{int(avg_sph):,} -> {int(avg_sph*(1+r['pct']/100)):,} SPH"
        else:
            b_hrs, b_shifts = 0, 0
            for p in p_ids:
                p_cfg = st.session_state.press_config[p]
                n_s = p_cfg["days_scheduled"] * (2 if p_cfg["night_shift"] else 1)
                b_shifts += n_s; b_hrs += n_s * (p_cfg["makeready_mins_per_shift"] / 60) if r["category"] == "makeready" else DEFAULT_DOWNTIME_CONFIG[p].get(r["category"], 0)
            detail_str = f"{int((b_hrs*60)/b_shifts)}m -> {int(((b_hrs-r['hours_used'])*60)/b_shifts)}m" if b_shifts > 0 else "0m"

        full_info = f"{display_press} | {label} | +{fmt_k(r['sheets_gained'])} | {detail_str}"
        short_p = "All" if r['press'] == "All" else f"P{r['press']}"
        if w >= 25: inner = f'<span style="padding-left:0.6rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{display_press} · {label} &nbsp;&nbsp;<b>+{fmt_k(r["sheets_gained"])}</b></span>'
        elif w >= 12: inner = f'<span style="padding-left:0.6rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{display_press} &nbsp;&nbsp;<b>+{fmt_k(r["sheets_gained"])}</b></span>'
        elif w >= 5: inner = f'<span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{short_p} <b>+{fmt_k(r["sheets_gained"])}</b></span>'
        else: inner = ""
        committed_slices_html += f'<div title="{full_info}" style="width:{w}%;background:{bg_color};height:100%;display:flex;align-items:center;justify-content:center;border-right:1px solid {C_DARK};overflow:hidden;font-size:0.85rem;color:white;">{inner}</div>'

    # ── RESTORED GHOST BAR (PREVIEW) LOGIC ──
    ghost_html = ""
    preview_gap_closed = gap_closed
    if add_pct > 0:
        g_w = (p_gain / gap * 100) if gap > 0 else 0
        g_color = bar_colors_list[len(results) % len(bar_colors_list)]
        g_label = LEVER_LABELS.get(add_cat, add_cat)
        preview_gap_closed = round((total_gained + p_gain) / gap * 100, 1) if gap > 0 else 100
        pre_p = "Fleet Wide" if add_press == "All" else f"Press {add_press}"
        short_pre_p = "All" if add_press == "All" else f"{add_press}"
        if g_w >= 25: inner_g = f'<span style="padding-left:0.6rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{pre_p} · {g_label} &nbsp;&nbsp;<b>+{fmt_k(p_gain)}</b></span>'
        elif g_w >= 12: inner_g = f'<span style="padding-left:0.6rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{pre_p} &nbsp;&nbsp;<b>+{fmt_k(p_gain)}</b></span>'
        elif g_w >= 5: inner_g = f'<span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{short_pre_p} <b>+{fmt_k(p_gain)}</b></span>'
        else: inner_g = ""
        ghost_html = f'<div title="PREVIEW: +{fmt_k(p_gain)}" style="width:{g_w}%;background:{g_color};opacity:0.6;height:100%;display:flex;align-items:center;justify-content:center;border:1px dashed white;overflow:hidden;font-size:0.85rem;color:white;">{inner_g}</div>'

    st.markdown(f'<div style="background:{C_MID};border-radius:6px;height:50px;width:100%;display:flex;overflow:hidden;border:2px solid {C_MID};">{committed_slices_html}{ghost_html}</div><div style="display:flex;justify-content:space-between;font-size:0.75rem;color:{C_MUTED};margin-top:0.4rem;"><span>Current: {fmt_k(current)}</span><span style="color:{C_WHITE};font-weight:600;">{preview_gap_closed:.0f}% of Gap Closed {"(Preview)" if add_pct > 0 else ""}</span><span>Target: {fmt_k(target)}</span></div>', unsafe_allow_html=True)

    # ── 5. ACTIVE LEVERS LIST ────────────────────────────────────────────
    if results:
        st.markdown('<div class="section-label" style="margin-top:1.5rem;margin-bottom:0.5rem;">Active Levers</div>', unsafe_allow_html=True)
        to_remove = None
        for i, r in enumerate(results):
            label = LEVER_LABELS.get(r["category"], r["category"]); display_p = "Fleet Wide" if r['press'] == "All" else f"Press {r['press']}"
            p_ids = list(st.session_state.press_config.keys()) if r['press'] == "All" else [r['press']]
            if r["category"] == "speed":
                avg_sph = sum(st.session_state.press_config[p].get("effective_sph", 0) for p in p_ids) / len(p_ids)
                m_str = f"{int(avg_sph):,} -> {int(avg_sph*(1+r['pct']/100)):,} SPH"
            else:
                b_hrs, b_shifts = 0, 0
                for p in p_ids:
                    p_cfg = st.session_state.press_config[p]
                    n_s = p_cfg["days_scheduled"] * (2 if p_cfg["night_shift"] else 1)
                    b_shifts += n_s; b_hrs += n_s * (p_cfg["makeready_mins_per_shift"] / 60) if r["category"] == "makeready" else DEFAULT_DOWNTIME_CONFIG[p].get(r["category"], 0)
                m_str = f"{int((b_hrs*60)/b_shifts)}m -> {int(((b_hrs-r['hours_used'])*60)/b_shifts)}m" if b_shifts > 0 else "0m"

            col_txt, col_del = st.columns([15, 1])
            with col_txt: st.markdown(f'<div style="font-size:0.85rem;color:{C_MUTED};display:flex;align-items:center;gap:10px;padding-top:0.3rem;"><div style="width:10px;height:10px;background:{bar_colors_list[i % len(bar_colors_list)]};border-radius:2px;"></div><span style="color:{C_WHITE};font-weight:600;">{display_p}</span><span>{label}</span><span style="margin-left:auto;font-family:\'IBM Plex Mono\';color:{C_OK};font-weight:600;">+{fmt_k(r["sheets_gained"])}</span><span style="opacity:0.7;font-size:0.8rem;margin-left:10px;">({m_str})</span></div>', unsafe_allow_html=True)
            with col_del: 
                if st.button("✕", key=f"del_{i}"): to_remove = i
        if to_remove is not None: st.session_state.plan_moves.pop(to_remove); st.rerun()

# ══════════════════════════════════════════════════════════════════════════
# DEEP DIVE — Code-Level Detailed Audit
# ══════════════════════════════════════════════════════════════════════════


elif st.session_state.question == "deep_dive":
    if "dd_filter_press" not in st.session_state:
        st.session_state.dd_filter_press = "All"

    st.markdown("<hr>", unsafe_allow_html=True)
    
    # ── 1. COMPACT PRESS FILTER BAR ──────────────────────────────────────
    press_list = list(st.session_state.press_config.keys())
    filter_options = ["All"] + press_list
    cols = st.columns(len(filter_options))
    
    for i, opt in enumerate(filter_options):
        label = f"[{opt}]" if st.session_state.dd_filter_press == opt else str(opt)
        if cols[i].button(label, key=f"dd_filter_{opt}", use_container_width=True):
            st.session_state.dd_filter_press = opt
            if opt != "All":
                st.session_state.dd_group_mode = "detailed"
            st.rerun()

    # ── 2. CODE-SPECIFIC DATA TABLE (FILTERED) ───────────────────────────
    raw_levers = rank_opportunities(st.session_state.press_config, DEFAULT_DOWNTIME_CONFIG, reduction_pct=1.0)
    
    df_rows = []
    active_press = st.session_state.dd_filter_press
    levers_to_render = [l for l in raw_levers if active_press == "All" or l["press"] == active_press]
    col_label, col_btn = st.columns([4, 1], vertical_alignment="bottom")
    with col_label:
        st.markdown('<div class="section-label" style="margin-top:1.5rem; margin-bottom:1rem;">Full Audit: Press & Code Breakdown</div>', unsafe_allow_html=True)
    with col_btn:
        if st.session_state.dd_filter_press == "All":
            mode_labels = {"detailed": "Group by Press", "by_press": "Group by Code", "by_code": "Show Detail"}
            if st.button(mode_labels[st.session_state.dd_group_mode], use_container_width=True):
                cycle = {"detailed": "by_press", "by_press": "by_code", "by_code": "detailed"}
                st.session_state.dd_group_mode = cycle[st.session_state.dd_group_mode]
                st.rerun()

    for l in levers_to_render:
        if l["category"] == "speed": continue
        
        specific_codes = DOWNTIME_CODE_MAP.get(l["category"], [LEVER_LABELS.get(l["category"], l["category"])])
        num_codes = len(specific_codes)
        
        p_cfg = st.session_state.press_config[l["press"]]
        n_s = p_cfg["days_scheduled"] * (2 if p_cfg["night_shift"] else 1)
        
        press_splits = CODE_HOUR_SPLITS.get(l["press"], {}).get(l["category"], {})
        total_split_hrs = sum(press_splits.values()) if press_splits else 0
        
        for code_desc in specific_codes:
            code_num = code_desc.split(" ")[0]
            if total_split_hrs > 0 and code_num in press_splits:
                proportion = press_splits[code_num] / total_split_hrs
            else:
                proportion = 1 / num_codes
            code_sheets = l["sheets_gained"] * proportion
            code_hours = l["hours_saved"] * proportion 
            
            code_mps = (code_hours * 60) / n_s if n_s > 0 else 0
            
            df_rows.append({
                "Press": f"Press {l['press']}",
                "Reason": code_desc,
                "Overall": LEVER_LABELS.get(l["category"], l["category"]),
                "Sheets Lost": int(code_sheets),
                "Hours Lost": code_hours,
                "Mins/Shift": int(code_mps)
            })

    if st.session_state.dd_group_mode == "by_press":
        grouped = {}
        for r in df_rows:
            p = r["Press"]
            if p not in grouped:
                p_id = p.replace("Press ", "")
                p_cfg = st.session_state.press_config[p_id]
                n_s = p_cfg["days_scheduled"] * (2 if p_cfg["night_shift"] else 1)
                grouped[p] = {"Press": p, "Reason": "All categories", "Overall": "—", 
                            "Sheets Lost": 0, "Hours Lost": 0.0, "_shifts": n_s}
            grouped[p]["Sheets Lost"] += r["Sheets Lost"]
            grouped[p]["Hours Lost"] += r["Hours Lost"]
        
        df_rows = []
        for row in grouped.values():
            row["Mins/Shift"] = int((row["Hours Lost"] * 60) / row["_shifts"]) if row["_shifts"] > 0 else 0
            del row["_shifts"]
            df_rows.append(row)
        df_rows.sort(key=lambda x: x["Sheets Lost"], reverse=True)


    elif st.session_state.dd_group_mode == "by_code":
        total_fleet_shifts = sum(
            cfg["days_scheduled"] * (2 if cfg["night_shift"] else 1)
            for cfg in st.session_state.press_config.values()
        )
        grouped = {}
        for r in df_rows:
            key = r["Reason"]
            if key not in grouped:
                grouped[key] = {"Press": "All", "Reason": r["Reason"], "Overall": r["Overall"],
                            "Sheets Lost": 0, "Hours Lost": 0.0}
            grouped[key]["Sheets Lost"] += r["Sheets Lost"]
            grouped[key]["Hours Lost"] += r["Hours Lost"]
        
        df_rows = []
        for row in grouped.values():
            row["Mins/Shift"] = int((row["Hours Lost"] * 60) / total_fleet_shifts) if total_fleet_shifts > 0 else 0
            df_rows.append(row)
        df_rows.sort(key=lambda x: x["Sheets Lost"], reverse=True)



    st.dataframe(
        pd.DataFrame(df_rows).sort_values(by="Sheets Lost", ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Press": st.column_config.TextColumn("Press",width="small"),
            "Overall": st.column_config.TextColumn("Category",width="small"),
            "Reason": st.column_config.TextColumn("Code",width="small"),
            "Sheets Lost": st.column_config.ProgressColumn(
                "Sheet Loss",
                format="%,.0f",
                min_value=0,
                max_value=max([r["Sheets Lost"] for r in df_rows]) if df_rows else 1,
                width="large"
            ),
            "Hours Lost": st.column_config.NumberColumn("Hrs/Mo", format="%.1f hrs",),
            "Mins/Shift": st.column_config.NumberColumn("Min/Shift", format="%d min"),
        }
    )

    # ── 3. CODE MAPPING GRID (REFERENCE CARDS) ───────────────────────────  
    with st.expander("Downtime Reason Code Reference", expanded=False):
        map_cols = st.columns(4)
        for i, (cat_key, codes) in enumerate(DOWNTIME_CODE_MAP.items()):
            with map_cols[i % 4]:
                st.markdown(f"""
                    <div style="background:{C_MID}; padding:0.8rem; border-radius:4px; border-left:3px solid {C_ACCENT}; margin-bottom:0.8rem; min-height:85px;">
                        <div style="font-size:0.65rem; color:{"#9CA3AF"}; text-transform:uppercase; letter-spacing:0.1em; font-weight:700;">{LEVER_LABELS.get(cat_key, cat_key)}</div>
                        <div style="font-family:'IBM Plex Mono', monospace; font-size:0.82rem; color:{C_WHITE}; margin-top:0.4rem; line-height:1.4;">
                            {"<br>".join(codes)}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

# ── FOOTER ────────────────────────────────────────────────────────────────
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(f"<div style='color:{C_MUTED};font-size:0.7rem;'>FloorPlan v1.0 · Press Room · Calibrated Q1–Apr 2026 · Fleet accuracy -2.0% vs actual</div>", unsafe_allow_html=True)