import streamlit as st
import sys
import os

# --- IMPORT FIX ---
# This looks one level up from "Explore" to the "Project" folder
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import the logic and cleaner
# Ensure floorplan_calculator.py and data_cleaner.py are in the Project folder
from floorplan_calculator import DEFAULT_PRESS_CONFIG
from data_cleaner import load_data

st.set_page_config(layout="wide")
st.title("Calibration: Makeready Metrics")

# 1. Load the data
df_clean = load_data()

# 2. Define Makeready operations
target_ops = [
    'Blanket Change', 
    'Make Ready', 
    'Make Ready 2', 
    'Plate Change', 
    'Wash Plates/Blankets'
]

# 3. Filter for setup time only
mr_data = df_clean[df_clean['Operation'].isin(target_ops)]

# 4. Group by press and get Monthly Avg (Total / 4 months)
# CSV covers Jan 1 - Apr 30
mr_monthly_avg_hrs = mr_data.groupby('Machine')['Time_Hours'].sum() / 4

st.write("### Calculated Actuals (Mins per Shift)")
st.write("Use these values to update your `DEFAULT_PRESS_CONFIG`.")

# 5. Calculate Mins per Shift
for machine_name, monthly_hrs in mr_monthly_avg_hrs.items():
    # Extract ID (e.g., '2190') from cleaned machine name
    press_id = str(machine_name).split()[0]
    
    if press_id in DEFAULT_PRESS_CONFIG:
        cfg = DEFAULT_PRESS_CONFIG[press_id]
        
        # Calculate scheduled shifts per month
        shifts_per_day = 2 if cfg["night_shift"] else 1
        total_monthly_shifts = cfg["days_scheduled"] * shifts_per_day
        
        # Math: (Hours * 60 mins) / Total Shifts
        mins_per_shift = (monthly_hrs * 60) / total_monthly_shifts
        
        st.metric(label=f"Press {press_id}", value=f"{mins_per_shift:.1f} mins/shift")
        st.caption(f"Based on {monthly_hrs:.1f} avg monthly hours over {total_monthly_shifts} shifts.")