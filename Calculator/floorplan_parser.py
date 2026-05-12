"""
FloorPlan — Auto-Count CSV Parser
===================================
Reads raw Auto-Count production log CSVs and outputs a clean,
structured DataFrame with one row per operation event.

Two row types in the raw data:
  - Job rows:      col[8] == "Date" — contains press, job, operation, sheets, speed
  - Downtime rows: col[42] has a downtime code — contains press, elapsed, downtime type

Output columns:
    date, press, press_id, job_id, operation, operation_type,
    elapsed_hrs, speed_sph, gross_sheets, net_sheets, waste_sheets
"""

import csv
import glob
import os
import re
import pandas as pd
from datetime import datetime, timedelta

# ── PRESS MAPPING ─────────────────────────────────────────────────────────
PRESS_MAP = {
    "P4-30201": "2060",
    "P4-30202": "2190",
    "P4-30203": "2160",
    "P4-30204": "2500",
    "P4-30206": "2330",
    "P4-30207": "2150",
}

# ── OPERATION TYPE MAPPING ────────────────────────────────────────────────
# Maps raw operation codes to clean calculator categories

OPERATION_MAP = {
    # Production
    "1000 Make Ready":          "makeready",
    "1010 Make Ready 2":        "makeready",
    "1020 Run":                 "run",
    "1030 Over Running":        "run",
    "1050 Auto-Restart":        "run",
    "1060 Cleanup/Washup/Teardown": "cleanup",

    # Downtime — Mechanical
    "2000 Breakdown (mechanical)": "jams",
    "2001 Breakdown (electrical)": "jams",
    "2070 Jam / Trip Up / etc":    "jams",
    "2097 Problem: Feeder":        "jams",
    "2085 Problem: Print Unit":    "jams",
    "2086 Material feeder trouble":"jams",
    "2087 UV or IR lamp trouble":  "jams",

    # Downtime — Maintenance
    "2010 Maintenance (planned)":   "maintenance",
    "2011 Maintenance (unplanned)": "maintenance",
    "2075 Wash Plates/Blankets":    "maintenance",
    "2082 Blanket Change":          "maintenance",
    "2083 Plate Change":            "maintenance",
    "2088 Ink Roller Maintenance":  "maintenance",
    "2021 UV/Convential Ink Convert": "maintenance",

    # Downtime — Approval waits
    "2080 Wait for Approval":          "manager_approval",
    "2081 Waiting for Color Match":    "manager_approval",
    "2121 Wait for Sales Approval":    "manager_approval",
    "2122 Wait for Customer Approval": "manager_approval",
    "2120 Wait for Quality Approval":  "quality_approval",
    "2123 Waiting for Quality Approval": "quality_approval",
    "2076 Set-Up Adjustment":          "quality_approval",
    "2098 Camera adjustment":          "quality_approval",
    "2099 Camera issues":              "quality_approval",

    # Downtime — Materials
    "2090 Wait for Material":          "materials_wait",
    "2095 Replace Materials":          "materials_wait",
    "2096 Raw Materials Non-conformance": "materials_wait",

    # Downtime — Shift
    "2040 Shift Change / Hand Off":    "shift_handoff",
    "2041 Waiting for Crew":           "shift_handoff",
    "2060 Downtime/No Crew":           "shift_handoff",
    "2089 One-Person Crew":            "shift_handoff",

    # Downtime — Breaks (excluded from productive time calc — already in 11hr shift)
    "2030 Break/Lunch":                "break",

    # Downtime — Other/Training
    "2050 Training / Meeting / etc":   "other",
    "2118 Training / Meetings / etc":  "other",
    "2109 Adjusting foil":             "other",
    "2110 Waiting for temperature":    "other",
    "2079 Waste Removal":              "other",
    "2114 Baler Down":                 "other",
}


def parse_elapsed(elapsed_str: str) -> float:
    """Convert H:MM:SS or HH:MM:SS string to decimal hours."""
    if not elapsed_str or not elapsed_str.strip():
        return 0.0
    try:
        parts = elapsed_str.strip().split(":")
        if len(parts) == 3:
            h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
            return h + m / 60 + s / 3600
        elif len(parts) == 2:
            h, m = int(parts[0]), int(parts[1])
            return h + m / 60
    except:
        return 0.0
    return 0.0


def clean_int(val: str) -> int:
    """Strip commas and convert to int."""
    try:
        return int(str(val).replace(",", "").strip())
    except:
        return 0


def parse_machine(cell: str) -> str:
    """Extract P4-XXXXX code from machine cell."""
    match = re.match(r"(P4-\d+)", cell.strip())
    return match.group(1) if match else ""


def parse_job_id(cell: str) -> str:
    """Extract numeric job ID from '540828  -  620049 - ...' format."""
    match = re.match(r"(\d+)", cell.strip())
    return match.group(1) if match else ""


def parse_file(filepath: str) -> list:
    """Parse one Auto-Count CSV file. Returns list of event dicts."""
    events = []
    current_machine = ""
    current_date = ""
    current_job = ""

    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 43:
                continue

            # Track current machine (always in col 7)
            if row[7].strip().startswith("P4-"):
                current_machine = parse_machine(row[7])

            # Skip rows not from our 6 presses
            if current_machine not in PRESS_MAP:
                continue

            press_id = PRESS_MAP[current_machine]

            # ── JOB ROW (col 8 == "Date") ──────────────────────────────
            if row[8].strip() == "Date":
                current_date = row[9].strip()
                current_job  = parse_job_id(row[13])
                operation    = row[33].strip()
                elapsed_hrs  = parse_elapsed(row[31])
                speed        = clean_int(row[32])
                gross        = clean_int(row[34])
                net          = clean_int(row[36])
                waste        = clean_int(row[38])

                if not operation:
                    continue

                op_type = OPERATION_MAP.get(operation, "other")

                events.append({
                    "date":           current_date,
                    "press":          current_machine,
                    "press_id":       press_id,
                    "job_id":         current_job,
                    "operation":      operation,
                    "operation_type": op_type,
                    "elapsed_hrs":    round(elapsed_hrs, 4),
                    "speed_sph":      speed,
                    "gross_sheets":   gross,
                    "net_sheets":     net,
                    "waste_sheets":   waste,
                })

            # ── DOWNTIME ROW (col 42 has downtime code) ─────────────────
            elif row[42].strip() and row[42].strip() in OPERATION_MAP:
                operation   = row[42].strip()
                elapsed_hrs = parse_elapsed(row[41])
                op_type     = OPERATION_MAP.get(operation, "other")

                events.append({
                    "date":           current_date,
                    "press":          current_machine,
                    "press_id":       press_id,
                    "job_id":         current_job,
                    "operation":      operation,
                    "operation_type": op_type,
                    "elapsed_hrs":    round(elapsed_hrs, 4),
                    "speed_sph":      0,
                    "gross_sheets":   0,
                    "net_sheets":     0,
                    "waste_sheets":   0,
                })

    return events


def parse_all(data_dir: str = ".") -> pd.DataFrame:
    """Parse all CSV files in a directory and return combined DataFrame."""
    all_events = []
    files = glob.glob(os.path.join(data_dir, "*.csv"))

    for f in files:
        print(f"Parsing {os.path.basename(f)}...")
        events = parse_file(f)
        all_events.extend(events)
        print(f"  → {len(events)} events")

    df = pd.DataFrame(all_events)

    if df.empty:
        print("No events parsed.")
        return df

    # Clean up
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df = df.sort_values(["date", "press_id"]).reset_index(drop=True)

    return df


# ── QUICK TEST ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    df = parse_all("/mnt/user-data/uploads")

    print(f"\n=== PARSE SUMMARY ===")
    print(f"Total events:  {len(df):,}")
    print(f"Date range:    {df['date'].min().date()} → {df['date'].max().date()}")
    print(f"\nEvents by press:")
    print(df.groupby("press_id")["elapsed_hrs"].agg(["count", "sum"]).rename(
        columns={"count": "events", "sum": "total_hrs"}).round(1))

    print(f"\nEvents by operation type:")
    print(df.groupby("operation_type").agg(
        events=("elapsed_hrs", "count"),
        total_hrs=("elapsed_hrs", "sum"),
        total_gross=("gross_sheets", "sum")
    ).round(1).sort_values("total_hrs", ascending=False))

    print(f"\nDowntime hours by press and category:")
    dt = df[df["operation_type"].isin([
        "jams", "maintenance", "manager_approval",
        "quality_approval", "materials_wait", "shift_handoff"
    ])]
    print(dt.groupby(["press_id", "operation_type"])["elapsed_hrs"].sum().round(2).unstack(fill_value=0))
