"""
floorplan_calculator.py  --  COMPATIBILITY ADAPTER

The Streamlit UI (floorplan_app.py) was written against the original
proof-of-concept calculator. This adapter keeps the UI's import surface
identical -- same function names, same argument shapes, same return shapes --
but every calculation is now powered by the audited floorplan/ package
running on real CSV data.

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
# Data loading -- parse the real CSVs once at import time
# ---------------------------------------------------------------------------

_HERE     = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(_HERE, "data")


def _find_csv(env_var, pattern):
    """Resolve a CSV path: env var wins; else newest match in data/."""
    # 1. Explicit env var always wins
    env_path = os.environ.get(env_var)
    if env_path:
        if not os.path.exists(env_path):
            raise FileNotFoundError(f"{env_var} set to '{env_path}' but no file there.")
        return env_path
    # 2. Search the data/ folder for the pattern
    matches = sorted(glob.glob(os.path.join(_DATA_DIR, pattern)))
    if matches:
        if len(matches) >1:
            names= ", ".join(os.path.basename(m) for m in matches)
            print(f"[INFO] {len(matches)} files. match '{pattern}: {names}."
                  f"Loading newest only {os.path.basename(matches[-1])}")
        return matches[-1]   # YYYY_MM names sort chronologically -> newest last
    # 3. Nothing found -- fail loud, say exactly where we looked
    raise FileNotFoundError(
        f"No file matching '{pattern}' in {_DATA_DIR}. "
        f"Put your monthly CSV there or set {env_var}."
    )


_CSV         = _find_csv("FLOORPLAN_CSV",         "productivity_*.csv")
_MACHINE_LOG = _find_csv("FLOORPLAN_MACHINE_LOG", "productionlog_*.csv")



_parser  = ProductivityCSVParser()
_PRESSES = _parser.parse(_CSV, _MACHINE_LOG)
_PRESS_BY_ID = {p.press_id: p for p in _PRESSES}

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

def fleet_summary(press_config=None, downtime_config=None,
                  planned_maintenance=None) -> dict:
    """
    Fleet rollup in the shape the UI expects.
    press_config / downtime_config are accepted for signature compatibility
    but the real data comes from the parsed Press objects.
    """
    summary = summarize_fleet(_PRESSES)

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

def lever_impact(press_id, category, reduction_pct,
                 press_config=None, downtime_config=None,
                 hours_already_claimed=0) -> dict:
    """
    Sheet impact of reducing one lever by reduction_pct.
    hours_already_claimed is accepted for signature compatibility but ignored --
    headroom logic was removed (lever hours are self-limiting, decision D7).
    """
    press = _press(press_id)

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
    result = _lever_impact(press, pkg_lever, reduction_pct)

    avail = available_hours(press)
    oee_gained = (
        round((result.hours_recovered / avail) * oee_quality(press) * 100, 2)
        if avail > 0 else 0
    )

    return {
        "press":          press_id,
        "category":       category,
        "type":           "process",
        "reduction_pct":  reduction_pct,
        "hours_saved":    result.hours_recovered,
        "hours_used":     result.hours_recovered,
        "sheets_gained":  result.sheets_gained,
        "oee_pts_gained": oee_gained,
    }


# ---------------------------------------------------------------------------
# rank_opportunities -- matches old return shape
# ---------------------------------------------------------------------------

def rank_opportunities(press_config=None, downtime_config=None,
                       reduction_pct: float = 0.20) -> list:
    """Rank every lever across the fleet by sheets gained, descending."""
    opportunities = []
    for press in _PRESSES:
        for pkg_lever in press.downtime_by_lever:
            if press.downtime_by_lever[pkg_lever] <= 0:
                continue
            ui_cat = _PKG_TO_UI.get(pkg_lever, pkg_lever)
            impact = lever_impact(press.press_id, ui_cat, reduction_pct)
            if impact["sheets_gained"] > 0:
                opportunities.append(impact)
    return sorted(opportunities, key=lambda x: x["sheets_gained"], reverse=True)


# ---------------------------------------------------------------------------
# what_would_it_take -- matches old return shape
# ---------------------------------------------------------------------------

def what_would_it_take(target_sheets: int, press_config=None,
                       downtime_config=None,
                       reduction_pct: float = 0.20) -> dict:
    """Backward engine -- rank levers and show the path to close the gap."""
    fleet   = fleet_summary()
    current = fleet["total_reality"]
    gap     = max(0, target_sheets - current)

    if gap == 0:
        return {"message": "Already at or above target.", "gap": 0, "levers": []}

    opportunities = rank_opportunities(reduction_pct=reduction_pct)
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

def code_breakdown(reduction_pct: float = 1.0) -> list:
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
    for press in _PRESSES:
        speed  = running_speed_net(press)
        shifts = press.total_shifts
        for code, detail in press.downtime_by_code.items():
            from config.op_codes import LEVER_CODE_TO_CATEGORY
            pkg_cat = LEVER_CODE_TO_CATEGORY.get(code)
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


def code_labels_by_category() -> dict:
    """
    {ui_category: ["2070 - Jam / Trip", ...]} built from real parsed data.
    Replaces the UI's hardcoded DOWNTIME_CODE_MAP reference card.
    """
    from config.op_codes import LEVER_CODE_TO_CATEGORY
    out = {}
    seen = set()
    for press in _PRESSES:
        for code, detail in press.downtime_by_code.items():
            if code in seen:
                continue
            seen.add(code)
            pkg_cat = LEVER_CODE_TO_CATEGORY.get(code)
            ui_cat  = _PKG_TO_UI.get(pkg_cat, pkg_cat)
            out.setdefault(ui_cat, []).append(f"{code} - {detail['name']}")
    for cat in out:
        out[cat].sort()
    return out