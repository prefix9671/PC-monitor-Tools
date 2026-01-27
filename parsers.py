# parsers.py
import re
import pandas as pd

def parse_process_column(df_col):
    process_stats = {}

    for row in df_col.dropna():
        # Strip potential literal quotes if the CSV was overly-quoted or has leading/trailing spaces
        row = str(row).strip('"\' ')
        
        # Skip empty or invalid rows
        if not row or row.lower() in ["no_active_io", "nan", "none"]:
            continue

        # Split by pipe. Often Monitor.ps1 uses " | "
        items = [x.strip() for x in row.split('|') if x.strip()]
        
        # Per-row aggregation to handle duplicates like chrome:647MB | chrome:418MB
        row_stats = {}
        items = [x.strip() for x in row.split('|') if x.strip()]
        for item in items:
             if ':' in item:
                try:
                    n, v = item.split(':', 1)
                    n = n.strip()
                    vm = re.search(r"([\d\.]+)", v)
                    if vm:
                        row_stats[n] = row_stats.get(n, 0) + float(vm.group(1))
                except:
                    continue
        
        # Update global max with this row's sums
        for p_name, p_val in row_stats.items():
            process_stats[p_name] = max(process_stats.get(p_name, 0), p_val)

    return (
        pd.DataFrame(list(process_stats.items()), columns=['Process', 'Max_Value'])
        .sort_values('Max_Value', ascending=False)
    )

def extract_process_time_series(df, col_name):
    """
    Extracts time-series data for individual processes from a summary column.
    Returns a long-format DataFrame with ['Timestamp', 'Process', 'Value'].
    """
    rows = []
    if col_name not in df.columns:
        return pd.DataFrame(columns=['Timestamp', 'Process', 'Value'])
        
    for _, row_val in df[['Timestamp', col_name]].dropna().iterrows():
        ts = row_val['Timestamp']
        data_str = str(row_val[col_name]).strip('"\' ')
        
        if not data_str or data_str.lower() in ["no_active_io", "nan", "none"]:
            continue
            
        # Per-timestamp aggregation map
        current_ts_stats = {}
            
        for item in [x.strip() for x in data_str.split('|') if x.strip()]:
            try:
                if ':' in item:
                    name_part, val_part = item.split(':', 1)
                    name = name_part.strip()
                    val_match = re.search(r"([\d\.]+)", val_part)
                    if val_match:
                        val = float(val_match.group(1))
                        # Sum values if process appears multiple times in same timestamp (e.g. chrome)
                        current_ts_stats[name] = current_ts_stats.get(name, 0) + val
            except:
                continue
        
        # Append aggregated results
        for proc_name, total_val in current_ts_stats.items():
            rows.append({'Timestamp': ts, 'Process': proc_name, 'Value': total_val})
                
    return pd.DataFrame(rows)

