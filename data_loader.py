# data_loader.py
import pandas as pd
import streamlit as st
import os


def _is_parquet_cache_valid(csv_path, parquet_path):
    if not (os.path.exists(csv_path) and os.path.exists(parquet_path)):
        return False
    return os.path.getmtime(parquet_path) >= os.path.getmtime(csv_path)


def _downcast_numeric(df):
    float_cols = df.select_dtypes(include=['float64']).columns
    int_cols = df.select_dtypes(include=['int64']).columns

    for col in float_cols:
        df[col] = pd.to_numeric(df[col], downcast='float')
    for col in int_cols:
        df[col] = pd.to_numeric(df[col], downcast='integer')

    return df


@st.cache_data
def load_data(files):
    """
    Loads and merges data from two sources:
    1. Logman CSVs (High Frequency: 1s) - Contains 'Global_Usage' in filename
    2. Monitor CSVs (Process Details: 30s) - Contains 'System_Log' in filename (or others)
    """
    import concurrent.futures
    
    logman_dfs = []
    process_dfs = []
    
    # Process files in parallel
    max_workers = min(8, max(1, len(files)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(process_single_file, files)
        
    for res in results:
        if res is None: continue
        rtype, df = res
        
        if rtype == 'logman':
            logman_dfs.append(df)
        elif rtype == 'process':
            process_dfs.append(df)

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

        return _downcast_numeric(merged)
        
    elif master_df is not None:
        return _downcast_numeric(master_df) # Only global data
    elif proc_df is not None:
        return _downcast_numeric(proc_df) # Only process data (fallback to old behavior)
        
    return None

def process_single_file(f):
    try:
        # Check filename if string, or name attribute if UploadedFile
        is_local_file = isinstance(f, str)
        fname = f if is_local_file else f.name
        
        # [Optimization] Parquet Caching for Local Files
        # If we have a local CSV, check if we already have a compiled .parquet version
        if is_local_file:
            parquet_path = f.replace('.csv', '.parquet')
            if _is_parquet_cache_valid(f, parquet_path):
                try:
                    # Load cached parquet - extremely fast
                    df = pd.read_parquet(parquet_path)
                    return ('logman' if "Global_Usage" in fname else 'process', df)
                except:
                    # If parquet load fails (corrupt?), fallback to CSV
                    pass

        # Try using pyarrow engine for speed, fallback to C engine (default) if fails
        # logman files often have mixed types in headers so engine='c' is safer for complex parsing initially
        # But for raw speed on big clean CSVs, pyarrow wins.
        # Let's try standard read first with low_memory=False as baseline optimization
        try:
             # Pyarrow engine is much faster but stricter on types
             # If it fails due to the messy Logman header structure, we fallback
             df = pd.read_csv(f, engine='pyarrow')
        except:
             df = pd.read_csv(f, low_memory=False)
        
        if "Global_Usage" in fname:
            # Check if first column is "(PDH-CSV 4.0)" (case varies)
            if df.columns[0].startswith("(PDH-CSV"):
                pass
            
            # Rename columns from "\Object\Counter" to friendly names
            # Mapping dictionary for EXACT matches
            rename_map = {
                r'Processor(_Total)\% Processor Time': 'CPU(%)',
                r'Memory\Available MBytes': 'AvailableMem(MB)',
                r'Memory\Committed Bytes': 'CommittedBytes',
                # Disk Read/Write Total only
                r'LogicalDisk(_Total)\Disk Read Bytes/sec': 'DiskRead(B/s)',
                r'LogicalDisk(_Total)\Disk Write Bytes/sec': 'DiskWrite(B/s)'
            }
            
            new_cols = []
            import re
            
            for c in df.columns:
                # 1. Check exact map
                found = False
                for key, val in rename_map.items():
                    if key in c:
                        new_cols.append(val)
                        found = True
                        break
                
                if found: continue

                # 2. Check Dynamic Disk Patterns (Regex)
                # Pattern: ...\LogicalDisk(C:)\% Disk Time -> DiskTime_C(%)
                # Pattern: ...\LogicalDisk(C:)\Current Disk Queue Length -> DiskQueue_C
                
                # Disk Time
                match_time = re.search(r'LogicalDisk\((.*)\)\\% Disk Time', c)
                if match_time:
                    drive_letter = match_time.group(1) # e.g. "C:" or "_Total"
                    if drive_letter == "_Total":
                        new_cols.append("DiskTime(%)")
                    else:
                        new_cols.append(f"DiskTime_{drive_letter}(%)")
                    continue
                    
                # Disk Queue
                match_queue = re.search(r'LogicalDisk\((.*)\)\\Current Disk Queue Length', c)
                if match_queue:
                    drive_letter = match_queue.group(1)
                    if drive_letter == "_Total":
                        new_cols.append("DiskQueue")
                    else:
                        new_cols.append(f"DiskQueue_{drive_letter}")
                    continue
                
                # Disk Read Speed
                match_read = re.search(r'LogicalDisk\((.*)\)\\Disk Read Bytes/sec', c)
                if match_read:
                    drive_letter = match_read.group(1)
                    if drive_letter == "_Total":
                        new_cols.append("DiskRead(B/s)")
                    else:
                        new_cols.append(f"DiskRead_{drive_letter}(B/s)")
                    continue

                # Disk Write Speed
                match_write = re.search(r'LogicalDisk\((.*)\)\\Disk Write Bytes/sec', c)
                if match_write:
                    drive_letter = match_write.group(1)
                    if drive_letter == "_Total":
                        new_cols.append("DiskWrite(B/s)")
                    else:
                        new_cols.append(f"DiskWrite_{drive_letter}(B/s)")
                    continue
                    
                if "PDH-CSV" in c:
                    new_cols.append("Timestamp") # First column is timestamp
                else:
                    new_cols.append(c) # Keep original if unknown catch
            
            df.columns = new_cols
            
            # Convert timestamp
            # Logman Format: "MM/DD/YYYY HH:MM:SS.mmm" e.g. "02/06/2026 11:51:16.208"
            # Optimization: Try explicit format first.
            try:
                df['Timestamp'] = pd.to_datetime(df['Timestamp'], format='%m/%d/%Y %H:%M:%S.%f').astype('datetime64[ns]')
            except:
                df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce').astype('datetime64[ns]')
            
            # Enforce numeric conversion for known metric columns
            # Logman CSVs often wrap numbers in quotes, reading them as strings if not careful
            numeric_cols = ['CPU(%)', 'AvailableMem(MB)', 'CommittedBytes']
            
            # Add dynamic disk columns
            for c in df.columns:
                if any(x in c for x in ['DiskTime', 'DiskQueue', 'DiskRead', 'DiskWrite']):
                    numeric_cols.append(c)
            
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            df = _downcast_numeric(df)
            
            # [Optimization] Save to Parquet for next time
            if is_local_file:
                 try:
                     df.to_parquet(parquet_path, index=False)
                 except:
                     pass

            return ('logman', df)
            
        else:
            # Regular Monitor.ps1 CSV
            df.columns = [c.strip() for c in df.columns]
            # Monitor.ps1 usually uses standard ISO-like or locale dependent. errors='coerce' is safe.
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce').astype('datetime64[ns]')
            
            if is_local_file:
                 try:
                     # For process logs, we also cache
                     parquet_path = f.replace('.csv', '.parquet')
                     df.to_parquet(parquet_path, index=False)
                 except:
                     pass

            return ('process', _downcast_numeric(df))
            
    except Exception as e:
        # st.warning(f"Skipping {fname}: {e}")
        return None
