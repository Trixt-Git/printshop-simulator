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
import sys, os

# ── DOCS (Assigned to variable so it doesn't render as a gap) ─────────────
_docs = """
FloorPlan — Press Room Decision Engine
========================================
Production improvement advisor for the floor manager.
"""

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
IMPROVEMENT_PCT   = 1
LEVER_LABELS = {
    "maintenance": "Unplanned Maintenance & Breakdowns", "jams": "Jams",
    "materials_wait": "Materials Wait", "shift_handoff": "Shift Handoff",
    "quality_approval": "Quality Wait", "manager_approval": "Approval Wait",
    "makeready": "Makeready / Setup",
}
LEVER_TYPE = {
    "maintenance": "Mechanical", "jams": "Mechanical",
    "materials_wait": "Process", "shift_handoff": "Process",
    "quality_approval": "Process", "manager_approval": "Process",
    "makeready": "Process",
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

# ── HEADER ────────────────────────────────────────────────────────────────
col_head, col_targ = st.columns([6, 1])
fleet      = fleet_summary(DEFAULT_PRESS_CONFIG, DEFAULT_DOWNTIME_CONFIG)
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
all_levers = rank_opportunities(DEFAULT_PRESS_CONFIG, DEFAULT_DOWNTIME_CONFIG, IMPROVEMENT_PCT)

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
if q3.button("📈 What if we improve?", key="btn_fwd",use_container_width=True): st.session_state.question = "forward"; st.rerun()
if q4.button("🔧 Build a plan", key="btn_plan",use_container_width=True): st.session_state.question = "plan"; st.rerun()
if q5.button("Reset", key="btn_reset",use_container_width=True): 
    st.session_state.question = "forward"; st.session_state.fwd_pct = 0
    st.session_state.plan_moves = []; st.rerun()

#Order was switched, Losses is now default view.

# ══════════════════════════════════════════════════════════════════════════
# FORWARD — What if we improve something?
# ══════════════════════════════════════════════════════════════════════════
if st.session_state.question == "forward":
    st.markdown("<hr>", unsafe_allow_html=True)
    
    # 1. Inputs across the top
    col_press, col_cat, col_pct = st.columns(3)

    with col_press:
        press_options = ["All"] + list(DEFAULT_PRESS_CONFIG.keys())
        press = st.selectbox(
            "Press",
            options=press_options,
            index=press_options.index(st.session_state.fwd_press) if st.session_state.fwd_press in press_options else 0,
            key="sel_press",
        )
        st.session_state.fwd_press = press

    with col_cat:
        cat = st.selectbox(
            "What are you improving?",
            options=list(LEVER_LABELS.keys()),
            format_func=lambda x: LEVER_LABELS[x],
            index=list(LEVER_LABELS.keys()).index(st.session_state.fwd_cat),
            key="sel_cat",
        )
        st.session_state.fwd_cat = cat

    with col_pct:
        pct = st.slider(
            "By how much?",
            min_value=0,
            max_value=100,
            value=st.session_state.fwd_pct,
            step=5,
            format="%d%%",
            key="sl_pct",
        )
        st.session_state.fwd_pct = pct

    st.markdown("<div style='margin-bottom:1.5rem;'></div>", unsafe_allow_html=True)

    # 2. Results underneath
    gained       = 0
    hrs_saved    = 0
    hrs_used     = 0
    baseline_hrs = 0
    
    presses_to_calc = list(DEFAULT_PRESS_CONFIG.keys()) if press == "All" else [press]
    
    for p in presses_to_calc:
        result = lever_impact(p, cat, pct / 100, DEFAULT_PRESS_CONFIG, DEFAULT_DOWNTIME_CONFIG)
        gained    += result["sheets_gained"]
        hrs_saved += result["hours_saved"]
        hrs_used  += result["hours_used"]
        
        if cat == "makeready":
            cfg = DEFAULT_PRESS_CONFIG[p]
            shifts_per_day = 2 if cfg["night_shift"] else 1
            total_shifts = cfg["days_scheduled"] * shifts_per_day
            baseline_hrs += round(total_shifts * (cfg["makeready_mins_per_shift"] / 60), 1)
        else:
            baseline_hrs += DEFAULT_DOWNTIME_CONFIG[p].get(cat, 0)
            
    new_hrs      = round(baseline_hrs - hrs_used, 1)
    gap_closed   = round(gained / gap * 100, 1) if gap > 0 else 100
    new_total    = current + gained
    
    display_name = "Fleet Wide" if press == "All" else f"Press {press}"
    callout_class = "result-callout success" if gap_closed >= 100 else "result-callout"
    
    # Place the boxes side-by-side
    col_res_left, col_res_right = st.columns(2)
    
    with col_res_left:
        st.markdown(f"""
        <div class="{callout_class}" style="margin-bottom:0; height:100%; display:flex; flex-direction:column; justify-content:center;">
            <div style="font-size:0.7rem;letter-spacing:0.12em;text-transform:uppercase;color:{C_MUTED};margin-bottom:0.4rem;">Sheets gained</div>
            <div style="font-family:'IBM Plex Mono',monospace;font-size:2.2rem;font-weight:700;color:{C_OK};">+{fmt_k(gained)}</div>
            <div style="font-size:0.85rem;color:{C_MUTED};margin-top:0.3rem;">New fleet total: {fmt_k(new_total)} &nbsp;·&nbsp; Gap closed: {gap_closed:.0f}%</div>
        </div>
        """, unsafe_allow_html=True)

    with col_res_right:
        st.markdown(f"""
        <div class="lever-card" style="margin-bottom:0; height:100%;">
            <div>
                <div class="lever-press">{display_name} · {LEVER_LABELS[cat]}</div>
                <div class="lever-name" style="font-size:1.1rem; margin-top:0.3rem;">{round(baseline_hrs, 1)} → {new_hrs} hrs/mo</div>
            </div>
            <div>
                <div class="lever-gain" style="font-size:1.8rem;">{fmt_hrs(hrs_used)}</div>
                <div class="lever-hrs">recovered</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Warnings and progress bar span the full width underneath
    if hrs_used < hrs_saved:
        st.markdown(f"<div style='color:{C_MUTED};font-size:0.78rem;text-align:center;margin-top:1rem;'>⚠ {display_name} only has {fmt_hrs(hrs_used)} of headroom — {fmt_hrs(hrs_saved - hrs_used)} saved but at capacity.</div>", unsafe_allow_html=True)

    progress_pct   = min(gap_closed / 100, 1.0)
    bar_fill_color = C_OK if gap_closed >= 100 else C_ACCENT

    st.markdown(f"""
    <div style="margin-top:1.5rem;">
        <div style="font-size:0.7rem;letter-spacing:0.1em;text-transform:uppercase;color:{C_MUTED};margin-bottom:0.4rem;text-align:center;">Progress to target</div>
        <div style="background:{C_MID};border-radius:3px;height:10px;width:100%;">
            <div style="background:{bar_fill_color};border-radius:3px;height:10px;width:{progress_pct*100:.0f}%;"></div>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:0.72rem;color:{C_MUTED};margin-top:0.4rem;">
            <span>{fmt_k(current)}</span><span>Target: {fmt_k(target)}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# BACKWARD — What do we need to hit target?
# ══════════════════════════════════════════════════════════════════════════
elif st.session_state.question == "backward":
    st.markdown("<hr>", unsafe_allow_html=True)

    plan = what_would_it_take(target, DEFAULT_PRESS_CONFIG, DEFAULT_DOWNTIME_CONFIG, IMPROVEMENT_PCT)

    _, col_status, _ = st.columns([1, 4, 1])

    # ── LEVER GRID ───────────────────────────────────────────────────────
    st.markdown(f'<div class="section-label" style="margin-top:0rem;">Recommended Action Plan (To hit +{ui_target_pct}% Target)</div>', unsafe_allow_html=True)

    card_cols = st.columns(2)
    cum_closed = 0
    
    for i, lev in enumerate(plan["levers"]):
        cum_closed += lev["pct_of_gap"]
        label      = LEVER_LABELS.get(lev["category"], lev["category"])
        ltype      = LEVER_TYPE.get(lev["category"], "")
        
        if lev["category"] == "makeready":
            cfg = DEFAULT_PRESS_CONFIG[lev["press"]]
            shifts_per_day = 2 if cfg["night_shift"] else 1
            total_shifts = cfg["days_scheduled"] * shifts_per_day
            baseline = round(total_shifts * (cfg["makeready_mins_per_shift"] / 60), 1)
        else:
            baseline = DEFAULT_DOWNTIME_CONFIG[lev["press"]].get(lev["category"], 0)
            
        target_hrs = round(baseline - lev["hours_saved"], 1)
        is_top     = (i == 0)
        card_class = "lever-card top" if is_top else "lever-card"

        # "Deal" the cards left and right using modulo
        with card_cols[i % 2]:
            st.markdown(f"""
            <div class="{card_class}">
                <div>
                    <div class="lever-press">#{i+1} · Press {lev['press']} · {ltype}</div>
                    <div class="lever-name">{label}</div>
                    <div style="font-size:0.78rem;color:{C_MUTED};margin-top:0.2rem;">{baseline} → {target_hrs} hrs/month &nbsp;(save {lev['hours_saved']} hrs)</div>
                </div>
                <div style="text-align:right;min-width:90px;">
                    <div class="lever-gain">+{fmt_k(lev['sheets_gained'])}</div>
                    <div class="lever-hrs">closes {lev['pct_of_gap']:.0f}% of gap</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ── WATERFALL CHART ──────────────────────────────────────────────────
    if plan["levers"]:
        st.markdown('<div class="section-label" style="margin-top:1.5rem;">Projected Target Build-Up</div>', unsafe_allow_html=True)

        labels   = ["Now"]
        measures = ["absolute"]
        values   = [current]
        texts    = [fmt_k(current)]

        for i, lev in enumerate(plan["levers"]):
            label     = LEVER_LABELS.get(lev["category"], lev["category"])
            short     = f"#{i+1} {lev['press']}<br>{label}"
            labels.append(short)
            measures.append("relative")
            values.append(lev["closes_sheets"])
            texts.append(f"+{fmt_k(lev['closes_sheets'])}")

        if not plan["fully_closeable"] and plan["gap_remaining"] > 0:
            labels.append("Shortfall")
            measures.append("relative")
            values.append(plan["gap_remaining"])
            texts.append(f"-{fmt_k(plan['gap_remaining'])}")

        labels.append("Target")
        measures.append("total")
        values.append(target)
        texts.append(fmt_k(target))

        y_min = current * 0.97
        y_max = target  * 1.02

        fig_wf = go.Figure(go.Waterfall(
            orientation = "v",
            measure     = measures,
            x           = labels,
            y           = values,
            text        = texts,
            textposition= "outside",
            textfont    = dict(family="IBM Plex Mono", size=12, color=C_WHITE),
            connector   = dict(line=dict(color="#4B5563", width=1, dash="dot")),
            increasing  = dict(marker_color=C_ACCENT),
            decreasing  = dict(marker_color=C_ALERT),
            totals      = dict(marker_color=C_MID),
        ))

        fig_wf.add_hline(
            y=target,
            line_width=2, line_dash="dash", line_color=C_WHITE,
            annotation_text="TARGET",
            annotation_position="top right",
            annotation_font=dict(color=C_WHITE, size=11),
        )

        fig_wf.update_layout(
            height          = 300,
            margin          = dict(l=0, r=20, t=40, b=0),
            paper_bgcolor   = "rgba(0,0,0,0)",
            plot_bgcolor    = "rgba(0,0,0,0)",
            showlegend      = False,
            xaxis           = dict(
                showgrid    = False,
                tickfont    = dict(family="IBM Plex Sans", size=11, color=C_WHITE),
            ),
            yaxis           = dict(
                showgrid    = True,
                gridcolor   = "#1F2937",
                range       = [y_min, y_max],
                tickformat  = ",.0f",
                tickfont    = dict(family="IBM Plex Mono", size=10, color=C_MUTED),
            ),
            waterfallgap    = 0.4,
        )

        st.plotly_chart(fig_wf, use_container_width=True, config={"displayModeBar": False})
# ══════════════════════════════════════════════════════════════════════════
# LOSSES — What are our biggest issues?
# ══════════════════════════════════════════════════════════════════════════
elif st.session_state.question == "losses":
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<div class="section-label" style="margin-top:0rem;">Historical Constraints — Top Fleet Losses (April)</div>', unsafe_allow_html=True)

    top_n  = min(10, len(all_levers))
    levers = all_levers[:top_n]

    bar_labels = [f"Press {l['press']} · {LEVER_LABELS.get(l['category'], l['category'])}" for l in levers]
    bar_vals   = [l["sheets_gained"] for l in levers]
    bar_hrs    = [l["hours_saved"] for l in levers]
    bar_colors = [C_OK if i == 0 else C_ACCENT if i <= 2 else C_MID for i in range(top_n)]
    
    # Combine the title and the value into one string for the inside of the bar
    bar_text   = [f"  Press {l['press']} · {LEVER_LABELS.get(l['category'], l['category'])}    (+{fmt_k(v)})" for l, v in zip(levers, bar_vals)]

    fig = go.Figure(go.Bar(
        x=bar_vals,
        y=bar_labels,  # Keep this for the hover popup
        orientation="h",
        marker_color=bar_colors,
        text=bar_text,
        textposition="inside",
        insidetextanchor="start",  # Anchors text to the left side of the bar
        textfont=dict(family="IBM Plex Sans", size=13, color=C_WHITE),
        hovertemplate="<b>%{y}</b><br>+%{x:,.0f} sheets at 20% reduction<br>Save %{customdata} hrs/month<extra></extra>",
        customdata=bar_hrs,
    ))

    fig.update_layout(
        height=350,
        margin=dict(l=0, r=0, t=10, b=0),  # Removed left/right margins to maximize bar width
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(
            visible=False,  # Hides the external y-axis titles entirely
            autorange="reversed",
        ),
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown(f"<div style='color:{C_MUTED};font-size:0.72rem;margin-top:-0.5rem;text-align:center;'>Green = highest impact · assumes 20% reduction per lever · calibrated to real Apr 2026 data</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# PLAN — Build a cumulative improvement plan
# ══════════════════════════════════════════════════════════════════════════
elif st.session_state.question == "plan":
    st.markdown("<hr>", unsafe_allow_html=True)

    # ── CALCULATE CUMULATIVE IMPACT (Moved up for preview math) ───────────
    claimed = {}
    results = []

    for move in st.session_state.plan_moves:
        presses_to_calc = list(DEFAULT_PRESS_CONFIG.keys()) if move["press"] == "All" else [move["press"]]
        
        m_gain, m_used, m_saved = 0, 0, 0
        
        for p in presses_to_calc:
            already = claimed.get(p, 0)
            impact  = lever_impact(
                p, move["category"], move["pct"] / 100,
                DEFAULT_PRESS_CONFIG, DEFAULT_DOWNTIME_CONFIG,
                hours_already_claimed=already,
            )
            claimed[p] = already + impact["hours_used"]
            m_gain  += impact["sheets_gained"]
            m_used  += impact["hours_used"]
            m_saved += impact["hours_saved"]
            
        results.append({
            "press": move["press"],
            "category": move["category"],
            "pct": move["pct"],
            "sheets_gained": m_gain,
            "hours_used": m_used,
            "hours_saved": m_saved
        })

    total_gained  = sum(r["sheets_gained"] for r in results)
    total_hrs     = sum(r["hours_used"]    for r in results)
    new_total     = current + total_gained
    gap_closed    = round(total_gained / gap * 100, 1) if gap > 0 else 100
    

    
# ── PLAN SUMMARY BAR ───────────────────────────────
    bar_color   = C_OK if gap_closed >= 100 else C_ACCENT
    callout_cls = "result-callout success" if gap_closed >= 100 else "result-callout"
    
    st.markdown(f"""
    <div class="{callout_cls}" style="padding: 0.6rem 1rem; display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
        <div style="display: flex; align-items: baseline; gap: 0.8rem;">
            <span style="font-size:1rem;letter-spacing:0.12em;text-transform:uppercase;color:{C_MUTED};">Plan total</span>
            <span style="font-family:'IBM Plex Mono',monospace;font-size:1.5rem;font-weight:700;color:{bar_color};">+{fmt_k(total_gained)}</span>
        </div>
        <div style="font-size:1rem;color:{C_MUTED};">
            New total: <span style="color:{C_WHITE};">{fmt_k(new_total)}</span> &nbsp;·&nbsp; Gap closed: <span style="color:{C_WHITE};">{gap_closed:.0f}%</span> &nbsp;·&nbsp; <span style="color:{C_WHITE};">{fmt_hrs(total_hrs)}</span> recovered
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── INPUT ROW ─────────────────────────────────────────────────────────
    col_p, col_c, col_pct, col_prev, col_add = st.columns([1.5, 2.5, 1.5, 2.5, 1.2])

    with col_p:
        press_options = ["All"] + list(DEFAULT_PRESS_CONFIG.keys())
        add_press = st.selectbox("Press", options=press_options, key="plan_press")

    with col_c:
        add_cat = st.selectbox(
            "What to improve",
            options=list(LEVER_LABELS.keys()),
            format_func=lambda x: LEVER_LABELS[x],
            key="plan_cat",
        )

    with col_pct:
        add_pct = st.slider("By how much?", 0, 100, 0, step=5, format="%d%%", key="plan_pct")

    # ── PREVIEW CALCULATION ───────────────────────────────────────────────
    presses_to_calc_prev = list(DEFAULT_PRESS_CONFIG.keys()) if add_press == "All" else [add_press]
    p_gain, p_hrs, p_save = 0, 0, 0
    
    for p in presses_to_calc_prev:
        preview_already = claimed.get(p, 0)
        preview_impact = lever_impact(
            p, add_cat, add_pct / 100,
            DEFAULT_PRESS_CONFIG, DEFAULT_DOWNTIME_CONFIG,
            hours_already_claimed=preview_already
        )
        p_gain += preview_impact["sheets_gained"]
        p_hrs  += preview_impact["hours_used"]
        p_save += preview_impact["hours_saved"]
    
    with col_prev:
        warn_msg = f"<span style='color:{C_ALERT}; font-size:0.85rem; margin-left:0.4rem;' title='Clipped (only {fmt_hrs(p_hrs)} left)'>⚠</span>" if p_hrs < p_save else ""
        
        st.markdown(f"""
        <div style="margin-top:1.73rem; background:{C_MID}; border:1px solid #4B5563; border-radius:4px; padding:0.65rem 0.5rem; display:flex; justify-content:center; align-items:center; line-height:1.2;">
            <span style="font-size:0.85rem; color:{C_MUTED}; text-transform:uppercase; letter-spacing:0.05em; margin-right:0.6rem;">Sheets:</span>
            <span style="font-family:'IBM Plex Mono',monospace; color:{C_OK}; font-size:1.05rem; font-weight:700;">+{fmt_k(p_gain)}</span>
            {warn_msg}
        </div>
        """, unsafe_allow_html=True)

    with col_add:
        st.markdown("<div style='margin-top:1.73rem;'></div>", unsafe_allow_html=True)
        if st.button("＋ Add", key="btn_add_move", use_container_width=True):
            st.session_state.plan_moves.append({
                "press": add_press,
                "category": add_cat,
                "pct": add_pct,
            })
            st.rerun()

    st.markdown("<div style='margin-bottom:1.5rem;'></div>", unsafe_allow_html=True)



    # ── MOVE LIST ─────────────────────────────────────────────────────────
    if results:
        bar_colors = [C_OK, C_ACCENT, "#F59E0B", "#06B6D4", "#8B5CF6", "#EC4899", "#14B8A6"]
        assigned_colors = [bar_colors[i % len(bar_colors)] for i, _ in enumerate(results)]

        st.markdown('<div class="section-label" style="margin-top:1.5rem; margin-bottom: 0.5rem;">Your plan</div>', unsafe_allow_html=True)

        cum_gained = 0
        to_remove  = None
        
        max_gain = max(r["sheets_gained"] for r in results) if results else 1

        for i, r in enumerate(results):
            cum_gained  += r["sheets_gained"]
            cum_pct      = round(cum_gained / gap * 100, 1) if gap > 0 else 100
            label        = LEVER_LABELS.get(r["category"], r["category"])
            ltype        = LEVER_TYPE.get(r["category"], "Process")
            headroom_warn = r["hours_used"] < r["hours_saved"]
            
            width_pct = (r["sheets_gained"] / max_gain) * 100
            bar_color = assigned_colors[i]

            display_press = "Fleet Wide" if r['press'] == "All" else f"Press {r['press']}"

            col_bar, col_del = st.columns([15, 1])
            with col_bar:
                warn_html = ""
                if headroom_warn:
                    clipped = r["hours_saved"] - r["hours_used"]
                    warn_html = f"<span style='color:{C_ALERT}; margin-left:1rem; font-size:0.75rem;'>⚠ {fmt_hrs(clipped)} clipped</span>"
                
                st.markdown(f"""
                <div style="width:100%; background: linear-gradient(to right, {bar_color} {width_pct}%, transparent {width_pct}%); min-height:36px; display:flex; align-items:center; border-radius:2px; margin-top:0.1rem;">
                    <span style="font-family:'IBM Plex Sans', sans-serif; font-size:0.9rem; color:{C_WHITE}; padding-left:0.6rem; white-space:nowrap;">
                        {display_press} · {label} &nbsp;&nbsp;<b>+{fmt_k(r['sheets_gained'])}</b>
                    </span>
                    {warn_html}
                </div>
                """, unsafe_allow_html=True)

            with col_del:
                if st.button("✕", key=f"del_{i}", help="Remove this lever"):
                    to_remove = i

        if to_remove is not None:
            st.session_state.plan_moves.pop(to_remove)
            st.rerun()

# ── STACKED PROGRESS BAR ──────────────────────────────────────────────
    st.markdown(f"""
    <div style="margin-top:1.5rem;">
        <div style="font-size:0.7rem;letter-spacing:0.1em;text-transform:uppercase;
                    color:{C_MUTED};margin-bottom:0.4rem;text-align:center;">
            Progress to target
        </div>
        <div style="background:{C_MID};border-radius:3px;height:14px;width:100%;display:flex;overflow:hidden;">
            {"".join([
                f'<div title="{LEVER_LABELS.get(r["category"])} · +{fmt_k(r["sheets_gained"])}" '
                f'style="width:{min(r["sheets_gained"]/gap*100, 100):.2f}%;'
                f'background:{assigned_colors[i]};'
                f'height:100%;"></div>'
                for i, r in enumerate(results)
            ])}
        </div>
        <div style="display:flex;justify-content:space-between;font-size:0.72rem;
                    color:{C_MUTED};margin-top:0.4rem;">
            <span>{fmt_k(current)}</span>
            <span style="color:{C_OK if gap_closed >= 100 else C_WHITE};">
                {gap_closed:.0f}% closed
            </span>
            <span>Target: {fmt_k(target)}</span>
        </div>
        <div style="display:flex;flex-wrap:wrap;gap:0.5rem;margin-top:0.8rem;">
            {"".join([
                f'<div style="display:flex;align-items:center;gap:0.4rem;">'
                f'<div style="width:10px;height:10px;border-radius:2px;'
                f'background:{bar_colors[i % len(bar_colors)]};flex-shrink:0;"></div>'
                f'<span style="font-size:0.72rem;color:{C_MUTED};">#{i+1} {r["press"]} · '
                f'{LEVER_LABELS.get(r["category"])}</span></div>'
                for i, r in enumerate(results)
            ])}
        </div>
    </div>
    """, unsafe_allow_html=True)



# ── FOOTER ────────────────────────────────────────────────────────────────
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(f"<div style='color:{C_MUTED};font-size:0.7rem;'>FloorPlan v1.0 · RRD Press Room · Calibrated Q1–Apr 2026 · Fleet accuracy -2.1% vs actual</div>", unsafe_allow_html=True)