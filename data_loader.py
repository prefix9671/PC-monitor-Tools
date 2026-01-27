# data_loader.py
import pandas as pd
import streamlit as st

@st.cache_data
def load_data(files):
    dfs = []
    # files can be a list of file paths (str) or UploadedFile objects
    for f in files:
        try:
            df = pd.read_csv(f)
            df.columns = [c.strip() for c in df.columns]
            dfs.append(df)
        except Exception as e:
            # st.error(f"Error loading {f}: {e}") # Optional: show error for specific files
            continue
            
    if dfs:
        try:
            full_df = pd.concat(dfs, ignore_index=True)
            full_df['Timestamp'] = pd.to_datetime(full_df['Timestamp'])
            return full_df.sort_values('Timestamp')
        except Exception as e:
            return None
    return None
