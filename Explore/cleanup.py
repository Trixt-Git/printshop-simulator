import pandas as pd
import numpy as np
import streamlit as st
import csv
import re

st.set_page_config(layout="wide")
st.title("Machine Productivity & Waste Dashboard")

# 2. Create a function to load and clean our specific CSV format
# The @st.cache_data line is a Streamlit "decorator". 
# It memorizes the data so the app doesn't have to re-read the file every time you click a button!
@st.cache_data
def load_data():
    data_rows = []
    # Open the file (make sure the name matches your file exactly!)
    with open('Q1 Press Sum.csv', 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            # Find the rows that contain our actual machine data
            if len(row) > 18 and "Sheetfed" in row[18]:
                data_rows.append(row[18:35])
                
    # Remove any duplicate rows
    unique_rows = [list(x) for x in set(tuple(x) for x in data_rows)]
    
    # Assign our column names
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
    


    # Convert text with commas (like "1,500") into real numbers so we can do math on them
    num_cols = ["Events", "Gross", "Net", "Waste"]
    for col in num_cols:
        df[col] = pd.to_numeric(df[col].str.replace(',', ''), errors='coerce')
        
    return df

# 3. Execute the function to load the data into a variable
df_clean = load_data()

st.sidebar.header("Please Filter Here:")

all_machines = df_clean['Machine'].unique()
all_operations = df_clean['Operation'].unique()

selected_machines = st.sidebar.multiselect(
    "Select Machines:",
    options=all_machines,
    default=all_machines
)

selected_operations = st.sidebar.multiselect(
    "Select Operations:",
    options=all_operations,
    default=all_operations
)

filtered_df = df_clean[
    (df_clean['Machine'].isin(selected_machines)) &
    (df_clean['Operation'].isin(selected_operations))
    ]

st.write('### Filtered Data Preview')
st.write(f"Showing {len(filtered_df)} Matching records")

st.dataframe(filtered_df)