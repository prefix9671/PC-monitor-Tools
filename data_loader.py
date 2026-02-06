# data_loader.py
import pandas as pd
import streamlit as st
import os

@st.cache_data
def load_data(files):
    """
    Loads and merges data from two sources:
    1. Logman CSVs (High Frequency: 1s) - Contains 'Global_Usage' in filename
    2. Monitor CSVs (Process Details: 30s) - Contains 'System_Log' in filename (or others)
    """
    logman_dfs = []
    process_dfs = []

    for f in files:
        try:
            # Check filename if string, or name attribute if UploadedFile
            fname = f if isinstance(f, str) else f.name
            
            if "Global_Usage" in fname:
                # Logman CSV (PDH-CSV) usually has a header in 2nd line or strict format
                # PDH-CSV often has a first line like "(PDH-CSV 4.0)...." which pandas might treat as header if not skipped
                # However, default pd.read_csv might just handle it if we are careful.
                # Let's peek first line or assume standard Logman CSV
                
                # Reading with header=0 usually works for standard CSV, but Logman puts blank line or ID sometimes?
                # Standard Logman CSV:
                # "(PDH-CSV 4.0)","\\COMP\Processor...","..."
                # "02/06/2026 10:00:00.000","12.5",...
                
                df = pd.read_csv(f)
                
                # Check if first column is "(PDH-CSV 4.0)" (case varies)
                if df.columns[0].startswith("(PDH-CSV"):
                    # The actual data is here, but headers are messy paths
                    pass
                
                # Rename columns from "\Object\Counter" to friendly names
                # Mapping dictionary
                rename_map = {
                    r'Processor(_Total)\% Processor Time': 'CPU(%)',
                    r'Memory\Available MBytes': 'AvailableMem(MB)',
                    r'Memory\Committed Bytes': 'CommittedBytes',
                    r'LogicalDisk(_Total)\% Disk Time': 'DiskTime(%)',
                    r'LogicalDisk(_Total)\Current Disk Queue Length': 'DiskQueue',
                    r'LogicalDisk(_Total)\Disk Read Bytes/sec': 'DiskRead(B/s)',
                    r'LogicalDisk(_Total)\Disk Write Bytes/sec': 'DiskWrite(B/s)'
                }
                
                new_cols = []
                for c in df.columns:
                    found = False
                    for key, val in rename_map.items():
                        if key in c:
                            new_cols.append(val)
                            found = True
                            break
                    if not found:
                        if "PDH-CSV" in c:
                            new_cols.append("Timestamp") # First column is timestamp
                        else:
                            new_cols.append(c) # Keep original if unknown catch
                
                df.columns = new_cols
                
                # Convert timestamp
                # Logman Format: "MM/DD/YYYY HH:MM:SS.mmm"
                df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
                logman_dfs.append(df)
                
            else:
                # Regular Monitor.ps1 CSV
                df = pd.read_csv(f)
                df.columns = [c.strip() for c in df.columns]
                df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
                process_dfs.append(df)
                
        except Exception as e:
            # st.warning(f"Skipping {fname}: {e}")
            continue

    # 1. Combine Logman Data (Master Timeline)
    master_df = None
    if logman_dfs:
        master_df = pd.concat(logman_dfs, ignore_index=True).sort_values('Timestamp')
        
    # 2. Combine Process Data
    proc_df = None
    if process_dfs:
        proc_df = pd.concat(process_dfs, ignore_index=True).sort_values('Timestamp')

    # 3. Merge Strategies
    if master_df is not None and proc_df is not None:
        # Merge Process Data onto Master Timeline using nearest backward match (tolerate 30s lag)
        master_df = master_df.sort_values('Timestamp')
        proc_df = proc_df.sort_values('Timestamp')
        
        merged = pd.merge_asof(
            master_df, 
            proc_df, 
            on='Timestamp', 
            direction='backward',
            tolerance=pd.Timedelta(seconds=35) # Allow 30s + buffer
        )
        # Fill strictly static info (IP, Total Mem) if missing due to start time diff
        # Actually forward fill might leave NaNs at the very start if proc started later
        merged[['PhysicalMem(GB)', 'OSTotalMem(GB)']] = merged[['PhysicalMem(GB)', 'OSTotalMem(GB)']].bfill().ffill()
        
        # Calculate derived columns common to old app.py logic
        # Logman gives AvailableMem, we need Used(GB), Usage(%)
        # But we need TotalMem for that. Use 'OSTotalMem(GB)' from proc_df
        
        if 'AvailableMem(MB)' in merged.columns and 'OSTotalMem(GB)' in merged.columns:
             merged['Used(GB)'] = (merged['OSTotalMem(GB)'] * 1024 - merged['AvailableMem(MB)']) / 1024
             merged['Usage(%)'] = (merged['Used(GB)'] / merged['OSTotalMem(GB)']) * 100
             
        return merged
        
    elif master_df is not None:
        return master_df # Only global data
    elif proc_df is not None:
        return proc_df # Only process data (fallback to old behavior)
        
    return None
