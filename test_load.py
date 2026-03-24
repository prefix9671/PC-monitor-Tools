# test_load.py
import os
import sys
from data_loader import load_data

log_dir = "./logs"
files = [os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.endswith('.csv')]
print(f"Loading {len(files)} files...")
df = load_data(files)
if df is not None:
    print(df.head())
    print("\nColumns:")
    print(df.columns)
    print("\nSuccess! Data parsed and merged correctly.")
else:
    print("Failed to load or merge data.")
