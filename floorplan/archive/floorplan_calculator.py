"""
FloorPlan — Core Calculator v3
================================
Math layer only. No UI. Feed it inputs, get outputs.
"""

# ── CONSTANTS ─────────────────────────────────────────────────────────────
HOURS_PER_SHIFT = 11       # 12hr shift minus 1hr breaks


# ── DEFAULT PRESS CONFIG ──────────────────────────────────────────────────
DEFAULT_PRESS_CONFIG = {
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

DEFAULT_DOWNTIME_CONFIG = {
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

DEFAULT_PLANNED_MAINTENANCE = {
    "4210": 0, "4180": 0, "4140": 0,
    "4520": 0, "4360": 0, "4080": 0,
}


def available_hours(cfg: dict) -> float:
    shifts_per_day = 2 if cfg["night_shift"] else 1
    return float(cfg["days_scheduled"] * shifts_per_day * HOURS_PER_SHIFT)


def makeready_hours(cfg: dict) -> float:
    shifts_per_day = 2 if cfg["night_shift"] else 1
    total_shifts = cfg["days_scheduled"] * shifts_per_day
    return float(total_shifts * (cfg["makeready_mins_per_shift"] / 60))


def reality_sheets(cfg: dict) -> int:
    return round(cfg["actual_run_hrs"] * cfg["effective_sph"])


def ceiling_sheets(cfg: dict, planned_maintenance: float = 0) -> int:
    avail = available_hours(cfg) - planned_maintenance
    return round(avail * cfg["effective_sph"] * cfg["performance"] * cfg["quality"])


def oee_actual(cfg: dict) -> dict:
    avail = available_hours(cfg)
    availability = cfg["actual_run_hrs"] / avail if avail > 0 else 0
    oee_total = availability * cfg["performance"] * cfg["quality"]
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
    summaries = {p: press_summary(p, press_config, downtime_config, planned_maintenance)
                 for p in press_config}
    total_reality = sum(s["reality_sheets"] for s in summaries.values())
    total_ceiling = sum(s["ceiling_sheets"] for s in summaries.values())
    total_avail   = sum(s["available_hrs"] for s in summaries.values())
    total_run     = sum(s["actual_run_hrs"] for s in summaries.values())
    fleet_oee     = round(total_run / total_avail * 100, 1) if total_avail > 0 else 0

    return {
        "by_press":          summaries,
        "total_reality":     total_reality,
        "total_ceiling":     total_ceiling,
        "total_opportunity": total_ceiling - total_reality,
        "total_avail_hrs":   total_avail,
        "total_run_hrs":     total_run,
        "fleet_oee_pct":     fleet_oee,
    }


def lever_impact(press_id: str, category: str, reduction_pct: float,
                 press_config: dict, downtime_config: dict, hours_already_claimed=0) -> dict:
    cfg = press_config[press_id]
    avail = available_hours(cfg)
    
    if category == "speed":
        hours_saved = 0
        hours_used = 0 
        sheets_gained = round(cfg["actual_run_hrs"] * (cfg["effective_sph"] * reduction_pct))
        oee_gained = round(((cfg["actual_run_hrs"] / avail) * cfg["performance"] * cfg["quality"] * reduction_pct * 100), 2) if avail > 0 else 0
        lever_type = "process"
        
    elif category == "makeready":
        shifts_per_day = 2 if cfg["night_shift"] else 1
        total_shifts = cfg["days_scheduled"] * shifts_per_day
        excess_mins = max(0, cfg["makeready_mins_per_shift"] - cfg["target_makeready_mins_per_shift"])
        hours_lost = total_shifts * (excess_mins / 60)
        
        hours_saved = round(hours_lost * reduction_pct, 1)
        lost_time = max(0, avail - cfg["actual_run_hrs"] - hours_already_claimed)
        hours_used = min(hours_saved, lost_time)
        sheets_gained = round(hours_used * cfg["effective_sph"])
        oee_gained = round((hours_used / avail) * cfg["performance"] * cfg["quality"] * 100, 2) if avail > 0 else 0
        lever_type = "process"
        
    else:
        hours_lost = downtime_config[press_id].get(category, 0)
        hours_saved = round(hours_lost * reduction_pct, 1)
        lost_time = max(0, avail - cfg["actual_run_hrs"] - hours_already_claimed)
        hours_used = min(hours_saved, lost_time)
        sheets_gained = round(hours_used * cfg["effective_sph"])
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


def rank_opportunities(press_config: dict, downtime_config: dict, reduction_pct: float = 0.20) -> list:
    opportunities = []
    for press in press_config:
        categories_to_check = list(downtime_config[press].keys())
        categories_to_check.append("makeready")
        for category in categories_to_check:
            impact = lever_impact(press, category, reduction_pct, press_config, downtime_config)
            if impact["sheets_gained"] > 0:
                opportunities.append(impact)
    return sorted(opportunities, key=lambda x: x["sheets_gained"], reverse=True)


def what_would_it_take(target_sheets: int, press_config: dict, downtime_config: dict, reduction_pct: float = 0.20) -> dict:
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