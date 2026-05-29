"""
parsers/snapshot_reader.py

Reads data/snapshot.json instead of raw CSVs.
Used by Streamlit Cloud where CSV files are not available.
"""

import json
import os
from datetime import date
from models.press import Press


def load_snapshot(snapshot_path: str = None) -> dict:
    """
    Load snapshot.json and return {period: [Press, ...]} 
    matching the shape of _ALL_MONTHS_BY_PERIOD.
    """
    if snapshot_path is None:
        snapshot_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "snapshot.json"
        )

    with open(snapshot_path) as f:
        raw = json.load(f)

    result = {}
    for period, press_list in raw.items():
        presses = []
        for d in press_list:
            presses.append(Press(
                press_id                = d["press_id"],
                period_start            = date.fromisoformat(d["period_start"]),
                period_end              = date.fromisoformat(d["period_end"]),
                net_sheets              = d["net_sheets"],
                gross_sheets            = d["gross_sheets"],
                actual_run_hrs          = d["actual_run_hrs"],
                total_logged_hrs        = d["total_logged_hrs"],
                no_crew_hrs             = d["no_crew_hrs"],
                planned_maintenance_hrs = d["planned_maintenance_hrs"],
                total_shifts            = d["total_shifts"],
                downtime_by_lever       = d["downtime_by_lever"],
                downtime_by_code        = d["downtime_by_code"],
                job_count               = d.get("job_count",0),
            ))
        result[period] = presses

    return result

