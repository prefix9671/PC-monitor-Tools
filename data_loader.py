# data_loader.py
import os
import re
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
from inspector_logs.core import (
    load_inspector_log_data as load_inspector_log_data_core,
    load_inspector_log_data_from_uploads as load_inspector_log_data_from_uploads_core,
)

TIME_ONLY_PATTERN = re.compile(r"^\d{1,2}:\d{2}(?::\d{2})?$")
DATE_ONLY_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

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

def collect_available_timestamps(*frames):
    timestamp_series = []

    for frame in frames:
        if frame is None or frame.empty or 'Timestamp' not in frame.columns:
            continue

        parsed = pd.to_datetime(frame['Timestamp'], errors='coerce').dropna()
        if not parsed.empty:
            timestamp_series.append(parsed)

    if not timestamp_series:
        return pd.DatetimeIndex([])

    combined = pd.concat(timestamp_series, ignore_index=True).drop_duplicates().sort_values()
    return pd.DatetimeIndex(combined)

def _parse_time_boundary_input(raw_value, default_date, boundary_name):
    raw_value = (raw_value or '').strip()
    boundary_label = '시작' if boundary_name == 'start' else '종료'
    result = {
        'provided': bool(raw_value),
        'raw': raw_value,
        'parsed': None,
        'error': None,
        'is_time_only': False,
        'is_date_only': False,
    }

    if not raw_value:
        return result

    try:
        if TIME_ONLY_PATTERN.fullmatch(raw_value):
            time_format = '%H:%M:%S' if raw_value.count(':') == 2 else '%H:%M'
            parsed_time = datetime.strptime(raw_value, time_format).time()
            result['parsed'] = pd.Timestamp(datetime.combine(default_date, parsed_time))
            result['is_time_only'] = True
        elif DATE_ONLY_PATTERN.fullmatch(raw_value):
            parsed = pd.Timestamp(raw_value)
            if boundary_name == 'end':
                parsed = parsed + timedelta(days=1) - timedelta(microseconds=1)
            result['parsed'] = parsed
            result['is_date_only'] = True
        else:
            parsed = pd.to_datetime(raw_value, errors='raise')
            parsed = pd.Timestamp(parsed)
            if parsed.tzinfo is not None:
                parsed = parsed.tz_localize(None)
            result['parsed'] = parsed
    except Exception:
        result['error'] = (
            f"{boundary_label} 시간 입력값 '{raw_value}' 형식이 올바르지 않습니다. "
            "YYYY-MM-DD HH:MM[:SS], YYYY-MM-DD, HH:MM[:SS] 형식을 사용하세요."
        )

    return result

def resolve_time_filter_range(available_timestamps, start_input='', end_input=''):
    timestamps = pd.DatetimeIndex(pd.to_datetime(available_timestamps, errors='coerce')).dropna().sort_values()

    if timestamps.empty:
        return {
            'used_manual': False,
            'error': 'No timestamps are available for time filtering.',
            'resolved_start': None,
            'resolved_end': None,
            'requested_start': None,
            'requested_end': None,
            'start_aligned': False,
            'end_aligned': False,
            'notes': [],
            'min_time': None,
            'max_time': None,
        }

    min_time = pd.Timestamp(timestamps[0])
    max_time = pd.Timestamp(timestamps[-1])
    normalized_dates = pd.Index(timestamps.normalize().unique())
    multiple_dates = len(normalized_dates) > 1

    start_boundary = _parse_time_boundary_input(start_input, min_time.date(), 'start')
    end_boundary = _parse_time_boundary_input(end_input, max_time.date(), 'end')

    notes = []
    if start_boundary['error']:
        return {
            'used_manual': True,
            'error': start_boundary['error'],
            'resolved_start': min_time,
            'resolved_end': max_time,
            'requested_start': None,
            'requested_end': None,
            'start_aligned': False,
            'end_aligned': False,
            'notes': notes,
            'min_time': min_time,
            'max_time': max_time,
        }

    if end_boundary['error']:
        return {
            'used_manual': True,
            'error': end_boundary['error'],
            'resolved_start': min_time,
            'resolved_end': max_time,
            'requested_start': start_boundary['parsed'],
            'requested_end': None,
            'start_aligned': False,
            'end_aligned': False,
            'notes': notes,
            'min_time': min_time,
            'max_time': max_time,
        }

    if multiple_dates and (start_boundary['is_time_only'] or end_boundary['is_time_only']):
        notes.append(
            '여러 날짜를 함께 불러온 상태에서 시간만 입력하면 시작은 첫 로드 날짜, 종료는 마지막 로드 날짜를 기준으로 해석합니다. '
            '여러 날짜 범위를 정확히 지정하려면 전체 날짜와 시간을 함께 입력하세요.'
        )

    used_manual = start_boundary['provided'] or end_boundary['provided']
    resolved_start = min_time
    resolved_end = max_time
    start_aligned = False
    end_aligned = False

    if start_boundary['parsed'] is not None:
        start_index = timestamps.searchsorted(start_boundary['parsed'], side='left')
        if start_index >= len(timestamps):
            start_index = len(timestamps) - 1
        resolved_start = pd.Timestamp(timestamps[start_index])
        start_aligned = resolved_start != start_boundary['parsed']

    if end_boundary['parsed'] is not None:
        end_index = timestamps.searchsorted(end_boundary['parsed'], side='right') - 1
        if end_index < 0:
            end_index = 0
        resolved_end = pd.Timestamp(timestamps[end_index])
        end_aligned = resolved_end != end_boundary['parsed']

    error = None
    if resolved_start > resolved_end:
        error = '보정된 시작 시간이 종료 시간보다 늦습니다. 입력 범위를 다시 확인하세요.'

    return {
        'used_manual': used_manual,
        'error': error,
        'resolved_start': resolved_start,
        'resolved_end': resolved_end,
        'requested_start': start_boundary['parsed'],
        'requested_end': end_boundary['parsed'],
        'start_aligned': start_aligned,
        'end_aligned': end_aligned,
        'notes': notes,
        'min_time': min_time,
        'max_time': max_time,
    }

def filter_dataframe_by_time_range(df, start_time, end_time):
    if df is None or df.empty or 'Timestamp' not in df.columns:
        return df
    return df[(df['Timestamp'] >= start_time) & (df['Timestamp'] <= end_time)].copy()

@st.cache_data
def load_data(files):
    """
    Loads data using the new format generated by the Python collector.
    Performs an exact merge on 'Timestamp' between resource and process datasets.
    """
    import concurrent.futures
    
    resource_dfs = []
    process_dfs = []
    
    max_workers = min(8, max(1, len(files)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(process_single_file, files)
        
    for res in results:
        if res is None: continue
        rtype, df = res
        
        if rtype == 'resource':
            resource_dfs.append(df)
        elif rtype == 'process':
            process_dfs.append(df)

    res_df = None
    if resource_dfs:
        res_df = pd.concat(resource_dfs, ignore_index=True)
        res_df = res_df.dropna(subset=['Timestamp']).sort_values('Timestamp')
        
    proc_df = None
    if process_dfs:
        proc_df = pd.concat(process_dfs, ignore_index=True)
        proc_df = proc_df.dropna(subset=['Timestamp']).sort_values('Timestamp')

    if res_df is not None and proc_df is not None:
        # Exact merge since both are generated on the exact same 5s boundary
        merged = pd.merge(res_df, proc_df, on='Timestamp', how='outer', suffixes=('', '_proc'))
        return _downcast_numeric(merged)
    elif res_df is not None:
        return _downcast_numeric(res_df)
    elif proc_df is not None:
        return _downcast_numeric(proc_df)
        
    return None

def _clean_column_names(df):
    import re
    def _clean(c):
        if not isinstance(c, str): return c
        c = c.replace('\x00', '')
        m = re.search(r'_(.*?)([A-Z]:(?:,[A-Z]:)*|PhysicalDrive\d+)(.*?)\(', c)
        if m and ('DiskTime_' in c or 'DiskRead_' in c or 'DiskWrite_' in c) and '(' in c:
            base = c.split('_')[0]
            unit = '(' + c.split('(')[1]
            drive = m.group(2)
            return f"{base}_{drive}{unit}"
        return c
    df.columns = [_clean(c) for c in df.columns]
    return df

def _calibrate_disk_metrics(df):
    """
    Auto-calibrates DiskTime(%) columns. 
    If all values in a column are extremely low (max < 2.0), 
    we treat them as legacy fractional-percent values and scale by 100x 
    to match the user's expected 0-100% scale.
    """
    for col in df.columns:
        if 'DiskTime_' in col and '(%)' in col:
            # If the max value is low, it's likely the old scale (e.g. 0.32 instead of 32.0)
            # We only scale if there's actually some data (max > 0)
            col_max = df[col].max()
            if 0 < col_max < 2.0:
                df[col] = df[col] * 100.0
                
    # Impute missing memory capacity columns for older Python collector logs
    if 'Mem_Used(GB)' in df.columns and 'Mem_Usage_Avg(%)' in df.columns:
        if 'OSTotalMem(GB)' not in df.columns or df['OSTotalMem(GB)'].isna().all():
            # Derived Total = Used / (Usage% / 100)
            valid = df[df['Mem_Usage_Avg(%)'] > 0]
            if not valid.empty:
                total = (valid['Mem_Used(GB)'].iloc[0] / valid['Mem_Usage_Avg(%)'].iloc[0]) * 100
                df['OSTotalMem(GB)'] = total
                if 'PhysicalMem(GB)' not in df.columns:
                    df['PhysicalMem(GB)'] = total
    return df

def process_single_file(f):
    try:
        is_local_file = isinstance(f, str)
        fname = f if is_local_file else f.name
        
        if is_local_file:
            # We append a version suffix to parquet cache if we change the parsing logic
            # to force invalidation of old cached data.
            parquet_path = f.replace('.csv', '.v3.parquet')
            if _is_parquet_cache_valid(f, parquet_path):
                try:
                    df = pd.read_parquet(parquet_path)
                    rtype = 'resource' if 'CPU_Avg(%)' in df.columns else 'process'
                    return (rtype, _clean_column_names(df))
                except:
                    pass

        try:
            df = pd.read_csv(f, engine='pyarrow')
        except:
            df = pd.read_csv(f, low_memory=False)
            
        # Parse Timestamp
        if 'Timestamp' in df.columns:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce').astype('datetime64[ns]')
            
        # Determine format structurally
        if 'CPU_Avg(%)' in df.columns:
            rtype = 'resource'
            # Legacy dashboards may look for 'CPU(%)', 'Used(GB)', 'Usage(%)'
            # Mapping canonical names to what old dashboard logic expects if possible,
            # or we just update the dashboard. Updating dashboard is better.
        elif 'Top5_CPU(%)' in df.columns:
            rtype = 'process'
        else:
            return None
            
        df = _downcast_numeric(df)
        df = _clean_column_names(df)
        
        if is_local_file:
            try:
                df.to_parquet(parquet_path, index=False)
            except:
                pass

        return (rtype, df)
        
    except Exception as e:
        return None

@st.cache_data
def load_inspector_data(path_input):
    return load_inspector_log_data_core(path_input)

@st.cache_data
def load_inspector_uploaded_data(file_payloads):
    return load_inspector_log_data_from_uploads_core(file_payloads)
