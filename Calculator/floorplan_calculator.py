"""
FloorPlan — Core Calculator v3
================================
Math layer only. No UI. Feed it inputs, get outputs.

Two distinct states:
    REALITY  = what actually happened (calibrated from real data)
    CEILING  = what's theoretically possible with zero downtime/makeready

The floor manager operates between reality and ceiling.
Every lever recovers hours from the gap between the two.

Core formulas:
    Reality sheets  = actual_run_hrs × effective_sph
    Ceiling sheets  = available_hrs × cruising_sph × performance × quality
    Lever gain      = hours_recovered × effective_sph
    New sheets      = reality_sheets + lever_gain

OEE = actual_run_hrs / available_hrs × performance × quality
Sheets is the output currency. OEE is the diagnostic currency.
"""

# ── CONSTANTS ─────────────────────────────────────────────────────────────
HOURS_PER_SHIFT = 11       # 12hr shift minus 1hr breaks


# ── DEFAULT PRESS CONFIG ──────────────────────────────────────────────────
# Calibrated from April 2026 Auto-Count + Productivity By Machine report.
#
# actual_run_hrs  = real run hours from productivity report (1020 Run events)
# effective_sph   = net sheets / actual run hrs (blended real speed incl. foil/startup)
# cruising_sph    = median SPH at full speed white stock (lever ceiling reference)
# performance     = effective_sph / cruising_sph
# quality         = net sheets / gross sheets from productivity report
# night_shift     = whether this press runs nights
# days_scheduled  = days scheduled this month (April actuals)
# makeready_mins_per_shift = avg makeready mins consumed per shift (April actuals)

DEFAULT_PRESS_CONFIG = {
    # Calibrated from Q1 2026 (Jan-Mar) monthly average + April 2026
    # actual_run_hrs = avg monthly run hours across 4 months
    # effective_sph  = avg net sheets / avg run hrs (blended real speed)
    # cruising_sph   = median SPH at full speed white stock
    # performance    = effective_sph / cruising_sph
    # quality        = net / gross from productivity reports
    # days_scheduled = April actuals (update monthly)
    "4210": {
        "actual_run_hrs":  199.7,
        "effective_sph":   8965,
        "cruising_sph":    9229,
        "performance":     0.971,
        "quality":         0.981,
        "night_shift":     True,
        "days_scheduled":  22,
        "makeready_mins_per_shift": 170.9,
        "target_makeready_mins_per_shift": 60
    },
    "4180": {
        "actual_run_hrs":  145.5,
        "effective_sph":   5835,
        "cruising_sph":    7615,
        "performance":     0.766,
        "quality":         0.925,
        "night_shift":     True,
        "days_scheduled":  30,
        "makeready_mins_per_shift": 201,
        "target_makeready_mins_per_shift": 60
    },
    "4140": {
        "actual_run_hrs":  176.1,
        "effective_sph":   6293,
        "cruising_sph":    7860,
        "performance":     0.800,
        "quality":         0.962,
        "night_shift":     True,
        "days_scheduled":  29,
        "makeready_mins_per_shift": 74,
        "target_makeready_mins_per_shift": 60
    },
    "4520": {
        "actual_run_hrs":  136.6,
        "effective_sph":   7713,
        "cruising_sph":    8581,
        "performance":     0.899,
        "quality":         0.954,
        "night_shift":     False,
        "days_scheduled":  27,
        "makeready_mins_per_shift": 164,
        "target_makeready_mins_per_shift": 60
    },
    "4360": {
        "actual_run_hrs":   52.9,
        "effective_sph":   5183,
        "cruising_sph":    6353,
        "performance":     0.816,
        "quality":         0.951,
        "night_shift":     False,
        "days_scheduled":  23,
        "makeready_mins_per_shift": 77,
        "target_makeready_mins_per_shift": 60
    },
    "4080": {
        "actual_run_hrs":   35.1,
        "effective_sph":   8438,
        "cruising_sph":    9865,
        "performance":     0.855,
        "quality":         0.889,
        "night_shift":     False,
        "days_scheduled":  27,
        "makeready_mins_per_shift": 143,
        "target_makeready_mins_per_shift": 60
    },
}

# ── DEFAULT DOWNTIME CONFIG ───────────────────────────────────────────────
# Hours per month per press — April 2026 Productivity By Machine report
# Controllable downtime only (No Crew / idle excluded)
# These represent hours lost from the ceiling — they explain why reality < ceiling

DEFAULT_DOWNTIME_CONFIG = {
    # Monthly averages: Q1 2026 (Jan-Mar) monthly avg + April 2026, averaged equally
    # Controllable downtime only (No Crew / idle excluded)
    "4210": {"manager_approval":  1.37, "quality_approval":  2.47, "materials_wait":  1.37,
             "shift_handoff": 15.55, "maintenance": 34.03, "jams": 41.71},
    "4180": {"manager_approval":  9.67, "quality_approval":  6.34, "materials_wait":  9.87,
             "shift_handoff":  7.79, "maintenance": 36.27, "jams": 60.07},
    "4140": {"manager_approval":  1.98, "quality_approval":  10.64, "materials_wait": 30.5,
             "shift_handoff":  4.17, "maintenance": 46.09, "jams": 78.46},
    "4520": {"manager_approval":  3.25, "quality_approval":  3.63, "materials_wait":  7.93,
             "shift_handoff":  4.01, "maintenance": 17.95, "jams": 41.92},
    "4360": {"manager_approval":  0.42, "quality_approval":  0.84, "materials_wait":  5.46,
             "shift_handoff":  2.83, "maintenance":  12.28, "jams": 24.25},
    "4080": {"manager_approval":  0.87, "quality_approval": 20.24, "materials_wait":  7.61,
             "shift_handoff": 9.73, "maintenance": 29, "jams": 42.49},
}

# ── PLANNED MAINTENANCE (fixed input, not a lever) ────────────────────────
DEFAULT_PLANNED_MAINTENANCE = {
    "4210": 0, "4180": 0, "4140": 0,
    "4520": 0, "4360": 0, "4080": 0,
}


# ── CORE FUNCTIONS ────────────────────────────────────────────────────────

def available_hours(cfg: dict) -> float:
    """Theoretical ceiling — days scheduled × shifts × 11 hrs."""
    shifts_per_day = 2 if cfg["night_shift"] else 1
    return cfg["days_scheduled"] * shifts_per_day * HOURS_PER_SHIFT


def makeready_hours(cfg: dict) -> float:
    """Total makeready hours consumed per month."""
    shifts_per_day = 2 if cfg["night_shift"] else 1
    total_shifts = cfg["days_scheduled"] * shifts_per_day
    return total_shifts * (cfg["makeready_mins_per_shift"] / 60)


def reality_sheets(cfg: dict) -> int:
    """Baseline: what actually happened. actual_run_hrs × effective_sph."""
    return round(cfg["actual_run_hrs"] * cfg["effective_sph"])


def ceiling_sheets(cfg: dict, planned_maintenance: float = 0) -> int:
    """
    Theoretical max: available hours × cruising SPH × performance × quality.
    Reduced by planned maintenance (fixed, not a lever).
    """
    avail = available_hours(cfg) - planned_maintenance
    return round(avail * cfg["effective_sph"] * cfg["performance"] * cfg["quality"])


def oee_actual(cfg: dict) -> dict:
    """OEE based on actual April run hours."""
    avail        = available_hours(cfg)
    availability = cfg["actual_run_hrs"] / avail if avail > 0 else 0
    oee_total    = availability * cfg["performance"] * cfg["quality"]
    return {
        "available_hrs":  round(avail, 1),
        "actual_run_hrs": round(cfg["actual_run_hrs"], 1),
        "availability":   round(availability, 4),
        "performance":    round(cfg["performance"], 4),
        "quality":        round(cfg["quality"], 4),
        "oee_pct":        round(oee_total * 100, 1),
    }


def press_summary(press_id: str, press_config: dict, downtime_config: dict,
                  planned_maintenance: dict = None) -> dict:
    """Full summary for a single press."""
    cfg = press_config[press_id]
    dt  = downtime_config[press_id]
    pm  = (planned_maintenance or DEFAULT_PLANNED_MAINTENANCE)[press_id]
    o   = oee_actual(cfg)

    return {
        "press":             press_id,
        "available_hrs":     o["available_hrs"],
        "actual_run_hrs":    o["actual_run_hrs"],
        "availability_pct":  round(o["availability"] * 100, 1),
        "performance_pct":   round(o["performance"] * 100, 1),
        "quality_pct":       round(o["quality"] * 100, 1),
        "oee_pct":           o["oee_pct"],
        "reality_sheets":    reality_sheets(cfg),
        "ceiling_sheets":    ceiling_sheets(cfg, pm),
        "opportunity_sheets": ceiling_sheets(cfg, pm) - reality_sheets(cfg),
        "ranked_downtime":   sorted(dt.items(), key=lambda x: x[1], reverse=True),
    }


def fleet_summary(press_config: dict, downtime_config: dict,
                  planned_maintenance: dict = None) -> dict:
    """Fleet-wide rollup."""
    summaries       = {p: press_summary(p, press_config, downtime_config, planned_maintenance)
                       for p in press_config}
    total_reality   = sum(s["reality_sheets"]    for s in summaries.values())
    total_ceiling   = sum(s["ceiling_sheets"]    for s in summaries.values())
    total_avail     = sum(s["available_hrs"]     for s in summaries.values())
    total_run       = sum(s["actual_run_hrs"]    for s in summaries.values())
    fleet_oee       = round(total_run / total_avail * 100, 1) if total_avail > 0 else 0

    return {
        "by_press":          summaries,
        "total_reality":     total_reality,
        "total_ceiling":     total_ceiling,
        "total_opportunity": total_ceiling - total_reality,
        "total_avail_hrs":   total_avail,
        "total_run_hrs":     total_run,
        "fleet_oee_pct":     fleet_oee,
    }


# ── BACKWARD ENGINE ───────────────────────────────────────────────────────

def lever_impact(press_id: str, category: str, reduction_pct: float,
                 press_config: dict, downtime_config: dict, hours_already_claimed=0) -> dict:
    """
    What sheets are gained if we reduce one downtime category by reduction_pct?
    Or, what sheets are gained if we increase run speed by reduction_pct?
    """
    cfg = press_config[press_id]
    avail = available_hours(cfg)
    
    # 1. SPEED LEVER: Increases yield of existing run hours, does not recover lost time.
    if category == "speed":
        hours_saved = 0
        hours_used = 0 
        sheets_gained = round(cfg["actual_run_hrs"] * (cfg["effective_sph"] * reduction_pct))
        
        # OEE Math: Speed increases the Performance multiplier directly, scaling the whole OEE.
        if avail > 0:
            base_oee= (cfg["actual_run_hrs"] / avail) * cfg["performance"] * cfg["quality"]
            oee_gained = round(base_oee * reduction_pct * 100, 2)
        else:
            oee_gained = 0
            
        lever_type = "process"
        
    # 2. MAKEREADY LEVER: Recovers time based on a realistic dynamic floor.
    elif category == "makeready":
        shifts_per_day = 2 if cfg["night_shift"] else 1
        total_shifts = cfg["days_scheduled"] * shifts_per_day
        excess_mins = max(0, cfg["makeready_mins_per_shift"] - cfg["target_makeready_mins_per_shift"])
        hours_lost = total_shifts * (excess_mins / 60)
        
        hours_saved = round(hours_lost * reduction_pct, 1)
        lost_time = avail - cfg["actual_run_hrs"] - hours_already_claimed
        hours_used = min(hours_saved, lost_time)
        sheets_gained = round(hours_used * cfg["effective_sph"])
        
        # OEE Math: Recovered hours increase Availability.
        oee_gained = round((hours_used / avail) * cfg["performance"] * cfg["quality"] * 100, 2) if avail > 0 else 0
        lever_type = "process"
        
    # 3. STANDARD DOWNTIME LEVERS: Recovers hours directly from the config dictionary.
    else:
        hours_lost = downtime_config[press_id].get(category, 0)
        hours_saved = round(hours_lost * reduction_pct, 1)
        lost_time = avail - cfg["actual_run_hrs"] - hours_already_claimed
        hours_used = min(hours_saved, lost_time)
        sheets_gained = round(hours_used * cfg["effective_sph"])
        
        # OEE Math: Recovered hours increase Availability.
        oee_gained = round((hours_used / avail) * cfg["performance"] * cfg["quality"] * 100, 2) if avail > 0 else 0
        
        process_cats = ["manager_approval", "quality_approval", "materials_wait", "shift_handoff"]
        lever_type = "process" if category in process_cats else "mechanical"

    return {
        "press":          press_id,
        "category":       category,
        "type":           lever_type,
        "reduction_pct":  reduction_pct,
        "hours_saved":    hours_saved,
        "hours_used":     hours_used,
        "sheets_gained":  sheets_gained,
        "oee_pts_gained": oee_gained,
    }

def rank_opportunities(press_config: dict, downtime_config: dict,
                       reduction_pct: float = 0.20) -> list:
    """Rank all levers by sheets gained at a given % reduction."""
    opportunities = []
    for press in press_config:
        categories_to_check = list(downtime_config[press].keys())
        categories_to_check.append("makeready")
        for category in categories_to_check:
            impact = lever_impact(press, category, reduction_pct, press_config, downtime_config)
            if impact["sheets_gained"] > 0:
                opportunities.append(impact)
    return sorted(opportunities, key=lambda x: x["sheets_gained"], reverse=True)


def what_would_it_take(target_sheets: int, press_config: dict,
                       downtime_config: dict,
                       reduction_pct: float = 0.20) -> dict:
    """
    Backward engine.
    Given a target, rank levers and show the path to close the gap.
    """
    fleet   = fleet_summary(press_config, downtime_config)
    current = fleet["total_reality"]
    gap     = max(0, target_sheets - current)

    if gap == 0:
        return {"message": "Already at or above target.", "gap": 0, "levers": []}

    opportunities = rank_opportunities(press_config, downtime_config, reduction_pct)
    levers        = []
    remaining     = gap

    for opp in opportunities[:10]:
        if remaining <= 0:
            break
        closes     = min(opp["sheets_gained"], remaining)
        pct_of_gap = round(closes / gap * 100, 1)
        remaining -= closes
        levers.append({**opp, "closes_sheets": closes, "pct_of_gap": pct_of_gap})

    return {
        "current_sheets":  current,
        "fleet_oee_pct":   fleet["fleet_oee_pct"],
        "target_sheets":   target_sheets,
        "gap":             gap,
        "levers":          levers,
        "gap_remaining":   max(0, remaining),
        "fully_closeable": remaining <= 0,
    }


# ── QUICK TEST ────────────────────────────────────────────────────────────
if __name__ == "__main__":

    REAL_NET = {
        "4210": 1608266, "4140": 1282891, "4180": 902697,
        "4520": 1102054, "4360":  367025, "4080": 215840,
    }
    total_real = sum(REAL_NET.values())

    fleet = fleet_summary(DEFAULT_PRESS_CONFIG, DEFAULT_DOWNTIME_CONFIG)

    print("=== FLEET SUMMARY ===")
    print(f"Reality (calc):  {fleet['total_reality']:,}")
    print(f"Reality (actual):{total_real:,}")
    print(f"Difference:      {fleet['total_reality'] - total_real:+,} ({(fleet['total_reality']-total_real)/total_real*100:+.1f}%)")
    print(f"Ceiling:         {fleet['total_ceiling']:,}")
    print(f"Opportunity:     {fleet['total_opportunity']:,} sheets between reality and ceiling")
    print(f"Fleet OEE:       {fleet['fleet_oee_pct']}%")

    print()
    print("=== PER PRESS ===")
    print(f"{'Press':<6} {'OEE%':>6} {'Reality':>10} {'Real Actual':>12} {'Ceiling':>10} {'Opportunity':>12}")
    for press, s in fleet["by_press"].items():
        real = REAL_NET[press]
        print(f"{press:<6} {s['oee_pct']:>6.1f}% {s['reality_sheets']:>10,} {real:>12,} {s['ceiling_sheets']:>10,} {s['opportunity_sheets']:>12,}")

    print()
    print("=== BACKWARD ENGINE: +10% TARGET (20% lever reduction) ===")
    target = round(total_real * 1.10)
    result = what_would_it_take(target, DEFAULT_PRESS_CONFIG, DEFAULT_DOWNTIME_CONFIG)
    print(f"Current: {result['current_sheets']:,} | Target: {result['target_sheets']:,} | Gap: {result['gap']:,}")
    print(f"Fleet OEE: {result['fleet_oee_pct']}%")
    print()
    print("Top levers (at 20% reduction each):")
    for l in result["levers"]:
        print(f"  [{l['type'][:4]}] {l['press']} — {l['category']}: "
              f"save {l['hours_saved']}hrs → +{l['sheets_gained']:,} sheets "
              f"(+{l['oee_pts_gained']} OEE pts) — closes {l['pct_of_gap']}% of gap")
    print()
    if result["fully_closeable"]:
        print("✅ Gap fully closeable with these levers.")
    else:
        print(f"⚠️  Gap remaining: {result['gap_remaining']:,} sheets")
