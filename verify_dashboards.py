import os
import sys
import pandas as pd
from unittest.mock import MagicMock
import argparse

# Path injection if needed
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from data_loader import load_data
from parsers import parse_process_column, extract_process_time_series
from dashboards.cpu import render_cpu_dashboard
from dashboards.memory import render_memory_dashboard
from dashboards.storage import render_storage_dashboard
from dashboards.custom import render_custom_dashboard
from config import DEFAULT_LOG_DIR

def get_latest_log_files():
    if not os.path.exists(DEFAULT_LOG_DIR):
        print(f"Log directory {DEFAULT_LOG_DIR} does not exist.")
        return []
        
    log_groups = set()
    for f in os.listdir(DEFAULT_LOG_DIR):
        if (f.startswith('resource_') or f.startswith('process_')) and f.endswith('.csv'):
            try:
                date_str = f.split('_')[1].split('.')[0]
                log_groups.add(date_str)
            except IndexError:
                pass
                
    if not log_groups:
        return []
        
    latest_date = sorted(list(log_groups))[-1]
    res_file = os.path.join(DEFAULT_LOG_DIR, f"resource_{latest_date}.csv")
    proc_file = os.path.join(DEFAULT_LOG_DIR, f"process_{latest_date}.csv")
    
    files = []
    if os.path.exists(res_file): files.append(res_file)
    if os.path.exists(proc_file): files.append(proc_file)
    return files

def self_test(files=None):
    if not files:
        files = get_latest_log_files()
        
    if not files:
        print("[ERROR] No log files found to test.")
        sys.exit(1)
        
    print(f"Loading data from: {files}")
    df = load_data(files)
    
    if df is None or df.empty:
        print("[ERROR] DataFrame is empty or failed to load.")
        sys.exit(1)
        
    # User requested: top 1 line parsing
    top_df = df.head(1).copy()
    print(f"\n✅ Dataframe loaded. Top 1 row features: {list(top_df.columns)}")
    
    # Create Mock Streamlit API
    st_mock = MagicMock()
    
    # Mock specific return values if necessary
    def mock_selectbox(label, options=None, *args, **kwargs):
        if "Quality" in str(label):
            return "Detailed"
        opts = options if options is not None else kwargs.get("options", [])
        try:
            return opts.iloc[0] if hasattr(opts, 'iloc') else list(opts)[0]
        except:
            return None
            
    st_mock.selectbox.side_effect = mock_selectbox
    st_mock.multiselect.return_value = []
    
    # Enable unpacking for layout elements dynamically
    st_mock.columns.side_effect = lambda n: [MagicMock() for _ in range(n)] if isinstance(n, int) else [MagicMock() for _ in range(len(n))]
    st_mock.tabs.side_effect = lambda labels: [MagicMock() for _ in labels]
    
    print("\n[🏃] Executing CPU Dashboard...")
    try:
        render_cpu_dashboard(st_mock, top_df)
        print(" -> CPU Dashboard SUCCESS.")
    except Exception as e:
        print(f" -> CPU Dashboard FAILED: {e}")
        
    print("\n[🏃] Executing Memory Dashboard...")
    try:
        render_memory_dashboard(st_mock, top_df, parse_process_column, extract_process_time_series, "16")
        print(" -> Memory Dashboard SUCCESS.")
    except Exception as e:
        print(f" -> Memory Dashboard FAILED: {e}")
        
    print("\n[🏃] Executing Storage Dashboard...")
    try:
        render_storage_dashboard(st_mock, top_df, parse_process_column)
        print(" -> Storage Dashboard SUCCESS.")
        
        # Intercept what was plottable
        metric_calls = []
        for call in st_mock.plotly_chart.call_args_list:
            fig = call[0][0]
            metric_calls.append(fig.layout.title.text)
        print(f"    Rendered charts: {metric_calls}")
    except Exception as e:
        print(f" -> Storage Dashboard FAILED: {e}")
        
    print("\n[🏃] Executing Custom Graph Dashboard...")
    try:
        selected_custom_cols_mock = [c for c in top_df.columns if pd.api.types.is_numeric_dtype(top_df[c])]
        if selected_custom_cols_mock:
            st_mock.multiselect.return_value = [selected_custom_cols_mock[0]]
        render_custom_dashboard(st_mock, top_df, parse_process_column)
        print(" -> Custom Graph SUCCESS.")
    except Exception as e:
        print(f" -> Custom Graph FAILED: {e}")

    print("\n🎉 Self-Test Suite Completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", nargs='*', help="Explicit CSV files to test")
    args = parser.parse_args()
    self_test(args.files)
