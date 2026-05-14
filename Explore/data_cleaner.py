import pandas as pd
import csv
import re
import streamlit as st

@st.cache_data
def load_data():
    data_rows = []
    # Open the file
    with open('Q1 Press Sum.csv', 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) > 18 and "Sheetfed" in row[18]:
                data_rows.append(row[18:35])
                
    unique_rows = [list(x) for x in set(tuple(x) for x in data_rows)]
    
    columns = ["Machine", "Empty", "OpCode", "Operation", "Events", "Time", "Time_Pct", "Gross", "Gross_Pct", "Net", "Net_Pct", "Waste", "Waste_Pct", "Machine_Total_Time", "Machine_Total_Gross", "Machine_Total_Net", "Machine_Total_Waste"]
    df = pd.DataFrame(unique_rows, columns=columns).drop(columns=["Empty"])
    
    def clean_machine_name(name):
        name = str(name)
        if '  -  ' in name:
            name = name.split('  -  ')[1].strip()
        match = re.search(r'P4-(\d+).*?\s+([A-Za-z]+)', name)
        if match:
            return f"{match.group(1)} {match.group(2)}"
        return name
    
    df['Machine'] = df['Machine'].apply(clean_machine_name)

    # Convert HH:MM:SS into decimal hours
    def time_to_hours(time_str):
        if not isinstance(time_str, str): return 0
        parts = str(time_str).split(':')
        if len(parts) == 3:
            return int(parts[0]) + int(parts[1])/60 + int(parts[2])/3600
        return 0
    
    df['Time_Hours'] = df['Time'].apply(time_to_hours)

    num_cols = ["Events", "Gross", "Net", "Waste"]
    for col in num_cols:
        df[col] = pd.to_numeric(df[col].str.replace(',', ''), errors='coerce')
        
    return df