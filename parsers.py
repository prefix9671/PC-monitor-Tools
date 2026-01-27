# parsers.py
import re
import pandas as pd

def parse_process_column(df_col):
    process_stats = {}

    for row in df_col.dropna():
        if row == "No_Active_IO" or not isinstance(row, str):
            continue

        for item in row.split('|'):
            try:
                # "sqlservr:120.5MB/s(85%)" or "java:5000MB"
                if ':' in item:
                    name, val_str = item.split(':', 1)
                    val_match = re.search(r"([\d\.]+)", val_str)
                    if val_match:
                        val = float(val_match.group(1))
                        process_stats[name.strip()] = max(
                            process_stats.get(name.strip(), 0),
                            val
                        )
            except:
                continue

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
        data_str = row_val[col_name]
        
        if data_str == "No_Active_IO" or not isinstance(data_str, str):
            continue
            
        for item in data_str.split('|'):
            try:
                if ':' in item:
                    name, val_str = item.split(':', 1)
                    val_match = re.search(r"([\d\.]+)", val_str)
                    if val_match:
                        val = float(val_match.group(1))
                        rows.append({'Timestamp': ts, 'Process': name.strip(), 'Value': val})
            except:
                continue
                
    return pd.DataFrame(rows)

