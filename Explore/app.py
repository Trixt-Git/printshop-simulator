import streamlit as st
import sys
import os

# --- 1. DIRECTORY FIX ---
# Path to app.py (.../Project/Explore)
explore_dir = os.path.dirname(os.path.abspath(__file__))

# Path to the Root Project folder (.../Project)
project_root = os.path.dirname(explore_dir)

# Path to the Calculator folder (.../Project/Calculator)
calculator_dir = os.path.join(project_root, 'Calculator')

# Add the Calculator folder to Python's search list
if calculator_dir not in sys.path:
    sys.path.append(calculator_dir)
# Also add the Project root just in case data_cleaner is there
if project_root not in sys.path:
    sys.path.append(project_root)

# --- 2. IMPORTS ---
try:
    from floorplan_calculator import DEFAULT_PRESS_CONFIG
    from data_cleaner import load_data
except ImportError as e:
    st.error(f"Still can't find the files. Error: {e}")
    st.stop()

# --- 3. THE CALCULATION ---
st.title("Makeready Calibration Report")
df_clean = load_data()

# Operations included in "Makeready"
target_ops = [
    'Blanket Change', 
    'Make Ready', 
    'Make Ready 2', 
    'Plate Change', 
    'Wash Plates/Blankets'
]

# Filter and aggregate the total hours over the 4-month data period
mr_data = df_clean[df_clean['Operation'].isin(target_ops)]
# Divide by 4 to get the average monthly hours (Jan-Apr)
mr_monthly_avg_hrs = mr_data.groupby('Machine')['Time_Hours'].sum() / 4

# Loop through each press to calculate the shift ratio
for machine_name, monthly_hrs in mr_monthly_avg_hrs.items():
    # Extracts the ID like '2190' from names like '2190 KBA'
    press_id = str(machine_name).split()[0]
    
    if press_id in DEFAULT_PRESS_CONFIG:
        cfg = DEFAULT_PRESS_CONFIG[press_id]
        
        # Calculate shifts per month from your configuration
        shifts_per_day = 2 if cfg.get("night_shift", False) else 1
        total_monthly_shifts = cfg["days_scheduled"] * shifts_per_day
        
        # Math: (Avg Monthly Hours * 60 minutes) / Monthly Shifts
        mins_per_shift = (monthly_hrs * 60) / total_monthly_shifts
        
        st.write(f"**Press {press_id}:** {mins_per_shift:.1f} mins/shift")