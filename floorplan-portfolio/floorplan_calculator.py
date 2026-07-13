"""
floorplan_calculator.py  --  COMPATIBILITY ADAPTER

The Streamlit UI (floorplan_app.py) was written against the original
proof-of-concept calculator. This adapter keeps the UI's import surface
identical -- same function names, same argument shapes, same return shapes --
but every calculation is now powered by the audited floorplan/ package
running on parsed monthly CSV data.

The UI does not need to change. This file translates between the UI's
expected vocabulary and the new package.

Exposes (matching the old calculator):
    DEFAULT_PRESS_CONFIG     -- dict keyed by press_id
    DEFAULT_DOWNTIME_CONFIG  -- dict keyed by press_id
    fleet_summary()
    rank_opportunities()
    what_would_it_take()
    lever_impact()

Data source: set FLOORPLAN_CSV and FLOORPLAN_MACHINE_LOG below, or the
adapter falls back to the bundled sample files.
"""

import os
import glob
from pathlib import Path
from parsers.productivity_csv import ProductivityCSVParser
from calculations.baseline import (
    running_speed_net, available_hours, ceiling_sheets as _ceiling,
    oee_availability, oee_quality,
)
from calculations.levers import lever_impact as _lever_impact
from calculations.fleet import summarize_fleet

# ---------------------------------------------------------------------------
# Data loading -- parse the CSVs once at import time
# ---------------------------------------------------------------------------

_HERE     = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(_HERE, "data")
MIN_MAKEREADY_MINS = 30

def _average_presses(all_months: list[list]) -> list:
    """
    Take a list of monthly Press lists, return one averaged Press per press.
    Raw fields are summed across months then divided by month count.
    Ratios and derived metrics are never averaged directly.
    """
    from models.press import Press
    
    if not all_months:
        raise ValueError("No monthly data to average.")
    
    n_months = len(all_months)
    
    # Flatten into per-press buckets: 
    by_press = {}
    for month in all_months:
        for press in month:
            by_press.setdefault(press.press_id, []).append(press)
    
    averaged = []
    for press_id, months in by_press.items():
        n = len(months)  # may be < n_months if press was idle some months
        
        # Sum all raw fields
        net_sheets              = sum(p.net_sheets for p in months)
        gross_sheets            = sum(p.gross_sheets for p in months)
        actual_run_hrs          = sum(p.actual_run_hrs for p in months)
        total_logged_hrs        = sum(p.total_logged_hrs for p in months)
        no_crew_hrs             = sum(p.no_crew_hrs for p in months)
        planned_maintenance_hrs = sum(p.planned_maintenance_hrs for p in months)
        total_shifts            = sum(p.total_shifts for p in months)
        job_count               = sum(p.job_count for p in months)

        # Sum downtime_by_lever
        downtime_by_lever = {}
        for p in months:
            for cat, hrs in p.downtime_by_lever.items():
                downtime_by_lever[cat] = downtime_by_lever.get(cat, 0.0) + hrs

        # Sum downtime_by_code
        downtime_by_code = {}
        for p in months:
            for code, d in p.downtime_by_code.items():
                if code not in downtime_by_code:
                    downtime_by_code[code] = {"hours": 0.0, "name": d["name"]}
                downtime_by_code[code]["hours"] += d["hours"]

        # Divide raw fields by number of months this press appeared in
        averaged.append(Press(
            press_id                = press_id,
            period_start            = min(p.period_start for p in months),
            period_end              = max(p.period_end for p in months),
            net_sheets              = round(net_sheets / n),
            gross_sheets            = round(gross_sheets / n),
            actual_run_hrs          = round(actual_run_hrs / n, 2),
            total_logged_hrs        = round(total_logged_hrs / n, 2),
            no_crew_hrs             = round(no_crew_hrs / n, 2),
            planned_maintenance_hrs = round(planned_maintenance_hrs / n, 2),
            total_shifts            = round(total_shifts / n),
            downtime_by_lever       = {k: round(v / n, 2) for k, v in downtime_by_lever.items()},
            downtime_by_code        = {code: {"hours": round(d["hours"] / n, 2), "name": d["name"]}
                                       for code, d in downtime_by_code.items()},
            job_count               = round(job_count/n),
        ))

    return sorted(averaged, key=lambda p: p.press_id)

# ---------------------------------------------------------------------------
# Data loading -- CSV locally, snapshot on Streamlit Cloud
# ---------------------------------------------------------------------------

_USE_SNAPSHOT = not os.path.isdir(_DATA_DIR) or not any(
    f.startswith("productivity_") and f.endswith(".csv")
    for f in os.listdir(_DATA_DIR)
    if os.path.isfile(os.path.join(_DATA_DIR, f))
)
_ALL_MONTHS_BY_PERIOD = {}

if _USE_SNAPSHOT:
    from parsers.snapshot_reader import load_snapshot
    print("[INFO] No CSVs found — loading from snapshot.json")
    _ALL_MONTHS_BY_PERIOD = load_snapshot()

else:
    _parser     = ProductivityCSVParser()
    _all_months = []
    for _prod_file in sorted(glob.glob(os.path.join(_DATA_DIR, "productivity_*.csv"))):
        _log_pattern = _prod_file.replace("productivity_", "productionlog_")
        _log_file    = _log_pattern if os.path.exists(_log_pattern) else None
        _all_months.append(_parser.parse(_prod_file, _log_file))

    if not _all_months:
        raise FileNotFoundError(f"No productivity_*.csv files found in {_DATA_DIR}")

    print(f"[INFO] Loaded {len(_all_months)} month(s): "
          + ", ".join(os.path.basename(f) for f in sorted(glob.glob(os.path.join(_DATA_DIR, "productivity_*.csv")))))

    _ALL_MONTHS_BY_PERIOD = {}
    for _month_list in _all_months:
        if _month_list:
            _period = _month_list[0].period_start.strftime("%Y_%m")
            _ALL_MONTHS_BY_PERIOD[_period] = _month_list

_PRESSES     = _average_presses(list(_ALL_MONTHS_BY_PERIOD.values()))
_PRESS_BY_ID = {p.press_id: p for p in _PRESSES}



# ---------------------------------------------------------------------------
# Month range support
# ---------------------------------------------------------------------------


def get_available_months() -> list[str]:
    """Returns sorted list of available month keys e.g. ['2026_01', '2026_04']"""
    return sorted(_ALL_MONTHS_BY_PERIOD.keys())

def load_range(start: str, end: str) -> list:
    """
    Return averaged Press list for months between start and end inclusive.
    start/end are 'YYYY_MM' strings.
    """
    filtered = [
        month_list
        for period, month_list in _ALL_MONTHS_BY_PERIOD.items()
        if start <= period <= end
    ]
    if not filtered:
        raise ValueError(f"No data found between {start} and {end}")
    return _average_presses(filtered)

def load_total(start: str, end: str) -> list:
    """
    Return summed (not averaged) Press list for months between start and end.
    Use for period totals rather than monthly averages.
    """
    from models.press import Press

    filtered = [
        month_list
        for period, month_list in _ALL_MONTHS_BY_PERIOD.items()
        if start <= period <= end
    ]
    if not filtered:
        raise ValueError(f"No data found between {start} and {end}")

    by_press = {}
    for month_list in filtered:
        for press in month_list:
            by_press.setdefault(press.press_id, []).append(press)

    totals = []
    for press_id, months in by_press.items():
        totals.append(Press(
            press_id                = press_id,
            period_start            = min(p.period_start for p in months),
            period_end              = max(p.period_end for p in months),
            net_sheets              = sum(p.net_sheets for p in months),
            gross_sheets            = sum(p.gross_sheets for p in months),
            actual_run_hrs          = round(sum(p.actual_run_hrs for p in months), 2),
            total_logged_hrs        = round(sum(p.total_logged_hrs for p in months), 2),
            no_crew_hrs             = round(sum(p.no_crew_hrs for p in months), 2),
            planned_maintenance_hrs = round(sum(p.planned_maintenance_hrs for p in months), 2),
            total_shifts            = sum(p.total_shifts for p in months),
            job_count               = sum(p.job_count for p in months),
            downtime_by_lever       = {
                k: round(sum(p.downtime_by_lever.get(k, 0) for p in months), 2)
                for k in months[0].downtime_by_lever
            },
            downtime_by_code        = {
                code: {
                    "hours": round(sum(p.downtime_by_code.get(code, {}).get("hours", 0) for p in months), 2),
                    "name": detail["name"]
                }
                for code, detail in months[0].downtime_by_code.items()
            },
        ))

    return sorted(totals, key=lambda p: p.press_id)



# UI lever keys -> new package lever keys.
# The UI uses "quality_approval"/"manager_approval"; the package uses
# "quality_wait"/"approval_wait". "speed" is a UI-only synthetic lever.
_UI_TO_PKG = {
    "maintenance":      "maintenance",
    "jams":             "jams",
    "materials_wait":   "materials_wait",
    "shift_handoff":    "shift_handoff",
    "quality_approval": "quality_wait",
    "manager_approval": "approval_wait",
    "makeready":        "makeready",
}
_PKG_TO_UI = {v: k for k, v in _UI_TO_PKG.items()}

def floored_makeready_hrs(press) -> float:
    """Makeready hours after subtracting the per-job floor. Single source of truth."""
    raw = press.downtime_by_lever.get("makeready", 0)
    if press.job_count > 0:
        floor_hrs = (press.job_count * MIN_MAKEREADY_MINS) / 60
        return max(0, raw - floor_hrs)
    return raw


# Standard Makeready Mins




# ---------------------------------------------------------------------------
# DEFAULT_PRESS_CONFIG -- shaped like the old config, filled from real data
# ---------------------------------------------------------------------------

def _build_press_config() -> dict:
    cfg = {}
    for p in _PRESSES:
        cfg[p.press_id] = {
            "actual_run_hrs":  p.actual_run_hrs,
            "effective_sph":   round(running_speed_net(p), 1),
            "available_hrs":   round(available_hours(p), 1),
            "total_shifts":    p.total_shifts,
            "quality":         round(oee_quality(p), 4),
            "net_sheets":      p.net_sheets,
            "gross_sheets":    p.gross_sheets,
        }
    return cfg


def _build_downtime_config() -> dict:
    """Downtime hours per press, keyed by UI lever names."""
    dt = {}
    for p in _PRESSES:
        row = {}
        for pkg_lever, hours in p.downtime_by_lever.items():
            ui_key = _PKG_TO_UI.get(pkg_lever)
            if ui_key:
                row[ui_key] = round(hours, 1)
        dt[p.press_id] = row
    return dt


DEFAULT_PRESS_CONFIG    = _build_press_config()
DEFAULT_DOWNTIME_CONFIG = _build_downtime_config()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _press(press_id):
    """Get the Press object for an id. Raises if unknown."""
    if press_id not in _PRESS_BY_ID:
        raise KeyError(f"Unknown press id: {press_id}")
    return _PRESS_BY_ID[press_id]


# ---------------------------------------------------------------------------
# fleet_summary -- matches old return shape
# ---------------------------------------------------------------------------

def fleet_summary(presses,press_config=None, downtime_config=None,
                  planned_maintenance=None) -> dict:
    """
    Fleet rollup in the shape the UI expects.
    press_config / downtime_config are accepted for signature compatibility
    but the real data comes from the parsed Press objects.
    """
    summary = summarize_fleet(presses)

    by_press = {}
    for s in summary.by_press:
        by_press[s.press_id] = {
            "press":              s.press_id,
            "available_hrs":      s.available_hrs,
            "actual_run_hrs":     s.actual_run_hrs,
            "availability_pct":   round(s.availability * 100, 1),
            "quality_pct":        round(s.quality * 100, 1),
            "oee_pct":            round(s.availability * 100, 1),
            "reality_sheets":     s.net_sheets,
            "ceiling_sheets":     s.ceiling_sheets,
            "opportunity_sheets": s.opportunity_sheets,
        }

    return {
        "by_press":          by_press,
        "total_reality":     summary.fleet_net_sheets,
        "total_ceiling":     summary.fleet_ceiling,
        "total_opportunity": summary.fleet_opportunity,
        "total_avail_hrs":   summary.fleet_available_hrs,
        "total_run_hrs":     summary.fleet_run_hrs,
        "fleet_oee_pct":     round(summary.fleet_availability * 100, 1),
    }


# ---------------------------------------------------------------------------
# lever_impact -- matches old return shape
# ---------------------------------------------------------------------------

def lever_impact(presses, press_id, category, reduction_pct,
               press_config=None, downtime_config=None,
               hours_already_claimed=0) -> dict:
    press_by_id = {p.press_id: p for p in presses}
    if press_id not in press_by_id:
        raise KeyError(f"Unknown press id: {press_id}")
    press = press_by_id[press_id]

    # SPEED -- synthetic UI lever. Increases yield of existing run hours.
    if category == "speed":
        speed = running_speed_net(press)
        sheets_gained = round(press.actual_run_hrs * speed * reduction_pct)
        return {
            "press":          press_id,
            "category":       "speed",
            "type":           "process",
            "reduction_pct":  reduction_pct,
            "hours_saved":    0,
            "hours_used":     0,
            "sheets_gained":  sheets_gained,
            "oee_pts_gained": 0,
        }

    # Standard levers -- route through the audited package
    pkg_lever = _UI_TO_PKG.get(category, category)

    # Makeready floor -- we can't reduce below MIN_MAKEREADY_MINS per job
    if pkg_lever == "makeready":
        import dataclasses
        press = dataclasses.replace(
            press,
            downtime_by_lever={
                **press.downtime_by_lever,
                "makeready": floored_makeready_hrs(press)
            }
        )


    result = _lever_impact(press, pkg_lever, reduction_pct)

    return {
        "press":          press_id,
        "category":       category,
        "type":           "process",
        "reduction_pct":  reduction_pct,
        "hours_saved":    result.hours_recovered,
        "hours_used":     result.hours_recovered,
        "sheets_gained":  result.sheets_gained,
        
    }


# ---------------------------------------------------------------------------
# rank_opportunities -- matches old return shape
# ---------------------------------------------------------------------------

def rank_opportunities(presses,press_config=None, downtime_config=None,
                       reduction_pct: float = 0.20) -> list:
    """Rank every lever across the fleet by sheets gained, descending."""
    opportunities = []
    for press in presses:
        for pkg_lever in press.downtime_by_lever:
            if press.downtime_by_lever[pkg_lever] <= 0:
                continue
            ui_cat = _PKG_TO_UI.get(pkg_lever, pkg_lever)
            impact = lever_impact(presses,press.press_id,ui_cat,reduction_pct)
            if impact["sheets_gained"] > 0:
                opportunities.append(impact)
    return sorted(opportunities, key=lambda x: x["sheets_gained"], reverse=True)


# ---------------------------------------------------------------------------
# what_would_it_take -- matches old return shape
# ---------------------------------------------------------------------------

def what_would_it_take(presses,
                       target_sheets: int, press_config=None,
                       downtime_config=None,
                       reduction_pct: float = 0.20) -> dict:
    """Backward engine -- rank levers and show the path to close the gap."""
    fleet   = fleet_summary(presses)
    current = fleet["total_reality"]
    gap     = max(0, target_sheets - current)

    if gap == 0:
        return {"message": "Already at or above target.", "gap": 0, "levers": []}

    opportunities = rank_opportunities(presses, reduction_pct=reduction_pct)
    levers    = []
    remaining = gap

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


# ---------------------------------------------------------------------------
# code_breakdown -- real per-op-code detail for the Deep Dive view
# ---------------------------------------------------------------------------

def code_breakdown(presses,reduction_pct: float = 1.0) -> list:
    """
    Per-op-code loss breakdown across the fleet, built from real parsed data.
    Replaces the UI's hardcoded CODE_HOUR_SPLITS / DOWNTIME_CODE_MAP.

    Each row:
        press        -- press id
        category     -- UI lever key (e.g. "jams")
        code         -- op code string (e.g. "2070")
        code_label   -- "2070 - Jam / Trip Up / etc" (name from Auto-Count)
        hours_lost   -- hours in this code at the given reduction_pct
        sheets_lost  -- hours_lost x running_speed_net
        mins_shift   -- hours_lost converted to minutes per shift

    reduction_pct 1.0 = full theoretical recovery (matches Deep Dive default).
    """
    rows = []
    for press in presses:
        speed  = running_speed_net(press)
        shifts = press.total_shifts
        for code, detail in press.downtime_by_code.items():
            from config.op_codes import LEVER_CODE_TO_CATEGORY
            pkg_cat = LEVER_CODE_TO_CATEGORY.get(code) or "unknown"
            ui_cat  = _PKG_TO_UI.get(pkg_cat, pkg_cat)

            hours_lost  = detail["hours"] * reduction_pct
            sheets_lost = round(hours_lost * speed)
            mins_shift  = round((hours_lost * 60) / shifts) if shifts > 0 else 0

            rows.append({
                "press":       press.press_id,
                "category":    ui_cat,
                "code":        code,
                "code_label":  f"{code} - {detail['name']}",
                "hours_lost":  round(hours_lost, 2),
                "sheets_lost": sheets_lost,
                "mins_shift":  mins_shift,
            })
    return sorted(rows, key=lambda r: r["sheets_lost"], reverse=True)


def code_labels_by_category(presses,) -> dict:
    """
    {ui_category: ["2070 - Jam / Trip", ...]} built from real parsed data.
    Replaces the UI's hardcoded DOWNTIME_CODE_MAP reference card.
    """
    from config.op_codes import LEVER_CODE_TO_CATEGORY
    out = {}
    seen = set()
    for press in presses:
        for code, detail in press.downtime_by_code.items():
            if code in seen:
                continue
            seen.add(code)
            pkg_cat = LEVER_CODE_TO_CATEGORY.get(code) or "unknown"
            ui_cat  = _PKG_TO_UI.get(pkg_cat, pkg_cat)
            out.setdefault(ui_cat, []).append(f"{code} - {detail['name']}")
    for cat in out:
        out[cat].sort()
    return out