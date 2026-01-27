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
