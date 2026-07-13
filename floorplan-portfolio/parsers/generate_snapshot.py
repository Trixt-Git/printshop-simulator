"""
generate_snapshot.py

Run locally whenever you have new monthly data.
Outputs data/snapshot.json for Streamlit Cloud to read.

Usage: python generate_snapshot.py
"""

import json
import os
import sys

# Script lives in parsers/ — step up to project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from floorplan_calculator import _ALL_MONTHS_BY_PERIOD
from calculations.baseline import running_speed_net, available_hours, oee_quality


def press_to_dict(press) -> dict:
    return {
        "press_id":               press.press_id,
        "period_start":           press.period_start.isoformat(),
        "period_end":             press.period_end.isoformat(),
        "net_sheets":             press.net_sheets,
        "gross_sheets":           press.gross_sheets,
        "actual_run_hrs":         press.actual_run_hrs,
        "total_logged_hrs":       press.total_logged_hrs,
        "no_crew_hrs":            press.no_crew_hrs,
        "planned_maintenance_hrs":press.planned_maintenance_hrs,
        "total_shifts":           press.total_shifts,
        "downtime_by_lever":      press.downtime_by_lever,
        "downtime_by_code":       press.downtime_by_code,
        "job_count":              press.job_count,  
    }

snapshot = {}
for period, month_list in _ALL_MONTHS_BY_PERIOD.items():
    snapshot[period] = [press_to_dict(p) for p in month_list]

out_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "snapshot.json"
)

with open(out_path, "w") as f:
    json.dump(snapshot, f, indent=2)

print(f"Snapshot written to {out_path}")
print(f"Periods: {sorted(snapshot.keys())}")
for period, presses in snapshot.items():
    print(f"  {period}: {len(presses)} presses")

