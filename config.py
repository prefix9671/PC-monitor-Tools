# config.py

COLOR_CPU = '#FF4B4B'
COLOR_MEM = '#0068C9'
COLOR_SWAP = '#FFA500'
COLOR_PROCESS = '#800080'
COLOR_ANOMALY = 'rgba(255, 0, 0, 0.1)'

DEFAULT_LOG_DIR = r"C:\SystemLogs"

LAST_BUILD = "~0,4datetime:~4,2datetime:~6,2datetime:~8,2datetime:~10,2" # Updated by build.bat

# Collector Settings
SAMPLE_INTERVAL_SEC = 1
AGGREGATION_WINDOW_SEC = 5
TOP_N = 5
OUTPUT_DIR = DEFAULT_LOG_DIR
ENABLE_SUMMARY_LOG = True
CSV_ENCODING = 'utf-8-sig'

