import pandas as pd
import sys
import os
import time

# ── 1. DYNAMIC PATH RESOLUTION ───────────────────────────────────────────────
script_dir = os.path.dirname(os.path.abspath(__file__))
excel_path = os.path.join(script_dir, "simulation_inputs.xlsx")

print(f"Targeting: {excel_path}\n")

if not os.path.exists(excel_path):
    print(f"❌ Critical Error: 'simulation_inputs.xlsx' not found at {excel_path}")
    sys.exit(1)

# Short delay to ensure OS file handles are released if just generated
time.sleep(0.3)

try:
    # ── 2. DATA INGESTION ──────────────────────────────────────────────────────
    df_front = pd.read_excel(excel_path, sheet_name="Main Control Panel", header=None)
    df_back = pd.read_excel(excel_path, sheet_name="Backend Engine", header=None)
    df_all = pd.concat([df_front, df_back])

    # The Master Knob List (Expanded to include all 54 variables)
    target_variables = [
        "SCENARIO_NAME", "MAKEREADY_ATTEMPTS", "SHEETS_PER_ATTEMPT", "DEFECT_WINDOW_SHEETS",
        "MIX_121_PLAIN", "MIX_121_HOLO", "MIX_100_PLAIN", "MIX_100_HOLO",
        "SHIFT_MIX_RED_DAY", "SHIFT_MIX_RED_NIGHT", "SHIFT_MIX_BLACK_DAY", "SHIFT_MIX_BLACK_NIGHT",
        "NIGHT_WASTE_FACTOR", "NIGHT_QUALITY_FACTOR", "FOIL_WASTE_FACTOR", "FOIL_MAKEREADY_FACTOR", "FOIL_SPEED_PENALTY",
        "SHARE_SF1", "SHARE_SF2", "SHARE_SF3", "SHARE_SF4", "SHARE_PF1", "SHARE_PF2",
        "AGE_FACTOR_SF3", "AGE_FACTOR_PF2", "SHEETFED_RATE_HR", "PERFECTING_RATE_HR",
        "STOCK_COST_WHITE", "STOCK_COST_FOIL", "INK_COST_PER_LB", "MARKUP_MIN", "MARKUP_MAX",
        "NUM_JOBS", "DATE_RANGE_DAYS",
        "PERFECTING_MAKEREADY_BONUS", "BASE_SPEED_WHITE_SHEETFED", "BASE_SPEED_WHITE_PERFECTING", 
        "BASE_SPEED_FOIL_SHEETFED", "BASE_SPEED_FOIL_PERFECTING",
        "DELTA_E_REJECT", "REGISTER_REJECT", "DOT_GAIN_REJECT", "CUT_DEVIATION_REJECT", "FOIL_ADHESION_FAIL",
        "MAKEREADY_NOISE_STD", "SPEED_NOISE_STD", "LEAD_TIME_MEAN_DAYS", "LEAD_TIME_STD_DAYS",
        "ACTUAL_TIME_MEAN", "ACTUAL_TIME_STD", "RANDOM_SEED", "START_DATE", "NUM_CUSTOMERS",
        "INK_COVERAGE_MIN", "INK_COVERAGE_MAX"
    ]

    xl_conf = {}

    # ── 3. SMART VARIABLE EXTRACTION ───────────────────────────────────────────
    for index, row in df_all.iterrows():
        param_name = str(row[0]).strip()
        
        if param_name in target_variables:
            raw_val = row[1]
            # Try to convert to float, if it fails, keep as original (string/date)
            try:
                xl_conf[param_name] = float(raw_val)
            except (ValueError, TypeError):
                xl_conf[param_name] = raw_val

    if len(xl_conf) < 1:
        print("❌ Error: No variables found. Check if Column A has the correct names.")
        sys.exit(1)

    print(f"✅ Success! Found {len(xl_conf)} variables.")
    print("-" * 60)
    # Sort them alphabetically for easier verification
    for key in sorted(xl_conf.keys()):
        print(f"{key:.<45} {xl_conf[key]}")

except Exception as e:
    print(f"❌ Critical Error during import: {e}")
    sys.exit(1)