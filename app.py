# app.py
import streamlit as st
import os
import sys
import subprocess
import pandas as pd
from config import DEFAULT_LOG_DIR
from data_loader import load_data
from parsers import parse_process_column, extract_process_time_series
from dashboards.cpu import render_cpu_dashboard
from dashboards.memory import render_memory_dashboard
from dashboards.storage import render_storage_dashboard
from dashboards.custom import render_custom_dashboard

# ==========================================
# 1. 설정 및 데이터 로딩
# ==========================================
st.set_page_config(page_title="System Resource Monitor", page_icon="🖥️", layout="wide")

st.title("🖥️ System Resource Dashboard")
st.markdown(f"##### 🚀 Executive Summary (Last Build: `{LAST_BUILD}`)")

# 사이드바: 파일 선택
with st.sidebar:
    st.header("🎮 Control Panel")
    
    # Configuration Inputs
    interval_sec = st.number_input("Interval (Seconds)", min_value=2, value=5, help="Minimum 2s (1s for CPU sampling)")
    drives_input = st.text_input("Target Drives (e.g. C:,D:)", value="C:,D:")
    
    if st.button("Start Monitor (Admin)"):
        # Resolve path to Monitor.ps1
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        script_path = os.path.join(base_path, "Monitor.ps1")
        
        # Parse drives for PowerShell array format: "C:","D:"
        drives_list = [d.strip() for d in drives_input.split(',')]
        drives_arg = ",".join([f'"{d}"' for d in drives_list])
        
        try:
            # Use PowerShell Start-Process to run as admin
            # Powershell argument syntax: -TargetDrives "C:","D:"
            args = f"-IntervalSeconds {interval_sec} -TargetDrives {drives_arg}"
            cmd = f"Start-Process powershell -ArgumentList '-ExecutionPolicy Bypass -File \"{script_path}\" {args}' -Verb RunAs"
            
            subprocess.Popen(
                ["powershell", "-Command", cmd],
                shell=True
            )
            st.success(f"Started! ({interval_sec}s, {drives_input})")
        except Exception as e:
            st.error(f"Failed: {e}")

    st.divider()
    st.header("📂 Log File Selection")
    
    # 1. 기본 경로 탐색
    log_files = []
    if os.path.exists(DEFAULT_LOG_DIR):
        log_files = [f for f in os.listdir(DEFAULT_LOG_DIR) if f.endswith('.csv')]
        log_files.sort(reverse=True) # 최신순 정렬
    
    uploaded_files = st.file_uploader("Upload Log CSV(s)", type=['csv'], accept_multiple_files=True)
    selected_files = st.multiselect(f"Select from {DEFAULT_LOG_DIR}", log_files)

    # 데이터 로드
    df = None
    target_files = []
    
    if uploaded_files:
        target_files.extend(uploaded_files)
    
    if selected_files:
        target_files.extend([os.path.join(DEFAULT_LOG_DIR, f) for f in selected_files])
        
    if target_files:
        df = load_data(target_files)
    
    if df is not None:
        st.success(f"Loaded: {len(df)} rows")
        # 시간 필터링
        min_time, max_time = df['Timestamp'].min(), df['Timestamp'].max()
        time_range = st.slider("Time Range", min_value=min_time.to_pydatetime(), max_value=max_time.to_pydatetime(), value=(min_time.to_pydatetime(), max_time.to_pydatetime()))
        
        # 데이터 필터링 적용
        df = df[(df['Timestamp'] >= pd.to_datetime(time_range[0])) & (df['Timestamp'] <= pd.to_datetime(time_range[1]))]

# ==========================================
# 2. 메인 대시보드 UI
# ==========================================

if df is not None:
    # ---------------------------------------------------------
    # (A) 상단 요약 카드 (Executive Summary)
    # ---------------------------------------------------------
    st.markdown("---")
    
    # 1. Max Memory 계산
    max_mem_gb = df['Used(GB)'].max()
    max_mem_pct = df['Usage(%)'].max()
    
    # Calculate Total Memory (Inverse of Usage calculation)
    # Total = Used / (Usage/100)
    # Use the max usage point for best accuracy (avoid div by zero or small number errors)
    try:
        valid_rows = df[df['Usage(%)'] > 0]
        if not valid_rows.empty:
            # Calculate for all rows and take median to smooth out rounding errors
            total_mem_series = valid_rows['Used(GB)'] / (valid_rows['Usage(%)'] / 100)
            total_mem_gb = round(total_mem_series.median())
        else:
            total_mem_gb = 0
    except:
        total_mem_gb = 512 # Fallback if calc fails

    # 2. 지속 증가 시간 (단순화: Min -> Max 도달 시간)
    min_mem_idx = df['Used(GB)'].idxmin()
    max_mem_idx = df['Used(GB)'].idxmax()
    if max_mem_idx > min_mem_idx:
        duration = df.loc[max_mem_idx, 'Timestamp'] - df.loc[min_mem_idx, 'Timestamp']
        trend_str = f"↗ {str(duration).split('.')[0]} duration"
    else:
        trend_str = "- Stable or Fluctuating"

    # 3. Top Offender Process
    top_offender = "N/A"
    top_offender_val = 0
    if 'Top5_Memory_MB' in df.columns:
        top_proc_df = parse_process_column(df['Top5_Memory_MB'])
        if not top_proc_df.empty:
            top_offender = top_proc_df.iloc[0]['Process']
            top_offender_val = top_proc_df.iloc[0]['Max_Value'] / 1024 # MB -> GB 변환

    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric(
        label="📈 Peak Memory Usage",
        value=f"{max_mem_gb} GB",
        delta=f"{max_mem_pct}% of {total_mem_gb}GB",
        delta_color="inverse"
    )
    kpi2.metric(
        label="⏱ Memory Ramp-up Duration",
        value=trend_str,
        help="Time taken from minimum to maximum memory usage in selected range."
    )
    kpi3.metric(
        label="🔥 Top Offender Process",
        value=top_offender,
        delta=f"{top_offender_val:.1f} GB Max",
        delta_color="inverse"
    )
    st.markdown("---")

    # 탭 메뉴 구성
    tab_list = ["📊 CPU Dashboard", "🧠 Memory Dashboard", "💾 Storage (D:)", "📈 Custom Graph"]
    menu = st.selectbox("Select Dashboard View", tab_list)

    if menu == "📊 CPU Dashboard":
        render_cpu_dashboard(st, df)
    elif menu == "🧠 Memory Dashboard":
        render_memory_dashboard(st, df, parse_process_column, extract_process_time_series)
    elif menu == "💾 Storage (D:)":
        render_storage_dashboard(st, df, parse_process_column)
    elif menu == "📈 Custom Graph":
        render_custom_dashboard(st, df)

else:
    st.info(f"👈 Please upload a log file or ensure files exist in {DEFAULT_LOG_DIR}")
