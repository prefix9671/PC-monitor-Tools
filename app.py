# app.py
import streamlit as st
import os
import sys
import subprocess
from pathlib import Path
import webbrowser
import pandas as pd
from datetime import datetime, timedelta
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
st.markdown("---")

# 사이드바: 파일 선택
with st.sidebar:
    st.header("🎮 Control Panel")
    
    # Configuration Inputs
    col_conf1, col_conf2 = st.columns(2)
    with col_conf1:
        logman_interval = st.number_input("Global Interval (s)", min_value=1, value=1, help="Logman Interval (CPU/Disk/Mem Peaks)")
    with col_conf2:
        process_interval = st.number_input("Process Interval (s)", min_value=5, value=30, help="PowerShell Interval (Top 5 Process Detail)")
    drives_input = st.text_input("Target Drives (e.g. C:,D:)", value="C:,D:")
    
    if st.button("Start Monitor (Admin)"):
        # Resolve path to start_monitor.bat
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        script_path = os.path.join(base_path, "start_monitor.bat")
        
        try:
            # Arguments must be string, separated by space
            args_str = f"{logman_interval} {process_interval}"
            
            cmd = f"Start-Process -FilePath \"{script_path}\" -ArgumentList \"{args_str}\" -Verb RunAs"
            
            subprocess.Popen(
                ["powershell", "-Command", cmd],
                shell=True
            )
            st.success(f"Started Hybrid Monitor! (Global: {logman_interval}s, Process: {process_interval}s)")
            st.info("A command window will appear. Close it to stop monitoring.")
        except Exception as e:
            st.error(f"Failed: {e}")

    if st.button("Stop Monitor (Logman Only)"):
        try:
            # Stop and Delete Logman Session using PowerShell RunAs Admin
            stop_cmd = "logman stop Global_Peak_Log; logman delete Global_Peak_Log"
            full_cmd = f"Start-Process powershell -ArgumentList '-NoProfile -Command \"{stop_cmd}\"' -Verb RunAs"
            
            subprocess.Popen(
                ["powershell", "-Command", full_cmd],
                shell=True
            )
            st.warning("Sent Stop command to Logman.")
        except Exception as e:
            st.error(f"Failed to stop: {e}")

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
        # 시간 필터링 (데이터가 1개 이상일 때만 슬라이더 표시)
        min_time, max_time = df['Timestamp'].min(), df['Timestamp'].max()
        
        if min_time < max_time:
            time_range = st.slider(
                "Time Range", 
                min_value=min_time.to_pydatetime(), 
                max_value=max_time.to_pydatetime(), 
                value=(min_time.to_pydatetime(), max_time.to_pydatetime())
            )
            # 데이터 필터링 적용
            df = df[(df['Timestamp'] >= pd.to_datetime(time_range[0])) & (df['Timestamp'] <= pd.to_datetime(time_range[1]))]
        else:
            st.info("💡 Only one data point available, time filtering skipped.")
            
        st.divider()
        if st.button("📖 웹 매뉴얼 열기 (MkDocs)", width='stretch'):
            # PyInstaller 환경(`sys.frozen`) 여부 확인
            if getattr(sys, 'frozen', False):
                # exe 실행 시 임시 폴더(_MEIPASS) 내의 site 폴더 참조
                base_path = sys._MEIPASS
            else:
                # 개발 환경에서는 현재 스크립트 위치 기준
                base_path = os.path.dirname(os.path.abspath(__file__))

            manual_path = os.path.join(base_path, "site", "index.html")

            if os.path.exists(manual_path):
                # Windows 경로(\)를 브라우저용 URI(/)로 자동 변환
                webbrowser.open_new_tab(Path(manual_path).as_uri())
            else:
                st.error(f"매뉴얼 사이트를 찾을 수 없습니다: {manual_path}")
        
        # CSV Export
        st.divider()
        st.markdown("### 💾 Export Data")
        if df is not None:
             csv_data = df.to_csv(index=False).encode('utf-8-sig')
             st.download_button(
                 label="Download Merged CSV",
                 data=csv_data,
                 file_name=f"Merged_Log_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                 mime="text/csv"
             )

        st.caption("© 2026 System Resource Monitor - v1.1.0")

# ==========================================
# 2. 메인 대시보드 UI
# ==========================================

if df is not None:
    # ---------------------------------------------------------
    # (A) 상단 요약 카드 (Executive Summary)
    # ---------------------------------------------------------
    st.markdown("---")
    
    # CSV에서 메모리 정보 가져오기
    # Ensure values are float before formatting
    try:
        if 'PhysicalMem(GB)' in df.columns and pd.notna(df['PhysicalMem(GB)'].iloc[0]):
            physical_mem_gb = f"{float(df['PhysicalMem(GB)'].iloc[0]):.2f}"
        else: 
            physical_mem_gb = "N/A"
            
        if 'OSTotalMem(GB)' in df.columns and pd.notna(df['OSTotalMem(GB)'].iloc[0]):
            os_total_mem_gb = f"{float(df['OSTotalMem(GB)'].iloc[0]):.2f}"
        else:
            os_total_mem_gb = "N/A"
    except:
        physical_mem_gb = "N/A"
        os_total_mem_gb = "N/A"
    
    st.markdown(f"#### 🖥️ 시스템 사양 정보")
    st.write(f"- **물리 장착 메모리**: {physical_mem_gb} GB")
    st.write(f"- **OS 사용 가능 메모리**: {os_total_mem_gb} GB")
    st.write("※ 실제 사용 가능 메모리 %로 계산하였습니다.")
    
    total_mem_gb = os_total_mem_gb
    st.markdown("---")

    max_mem_gb = f"{df['Used(GB)'].max():.2f}" if 'Used(GB)' in df.columns else "0.00"
    max_mem_pct = f"{df['Usage(%)'].max():.2f}" if 'Usage(%)' in df.columns else "0.00"

    # 2. 지속 증가 시간 (단순화: Min -> Max 도달 시간)
    trend_str = "- Stable or Fluctuating"
    
    if 'Used(GB)' in df.columns and df['Used(GB)'].notna().any():
        try:
            min_mem_idx = df['Used(GB)'].idxmin()
            max_mem_idx = df['Used(GB)'].idxmax()
            
            # idxmin can return NaN if all are NaN, but we checked notna().any()
            # However, if idxmin/max returns an index that is not in df (unlikely)
            if pd.notna(min_mem_idx) and pd.notna(max_mem_idx):
                t_min = df.loc[min_mem_idx, 'Timestamp']
                t_max = df.loc[max_mem_idx, 'Timestamp']
                if t_max > t_min:
                    duration = t_max - t_min
                    trend_str = f"↗ {str(duration).split('.')[0]} duration"
        except Exception:
            pass

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
        delta=f"{top_offender_val:.2f} GB Max",
        delta_color="inverse"
    )
    st.markdown("---")

    # 탭 메뉴 구성
    tab_list = ["📊 CPU Dashboard", "🧠 Memory Dashboard", "💾 Storage (D:)", "📈 Custom Graph"]
    menu = st.selectbox("Select Dashboard View", tab_list)

    if menu == "📊 CPU Dashboard":
        render_cpu_dashboard(st, df)
    elif menu == "🧠 Memory Dashboard":
        render_memory_dashboard(st, df, parse_process_column, extract_process_time_series, total_mem_gb)
    elif menu == "💾 Storage (D:)":
        render_storage_dashboard(st, df, parse_process_column)
    elif menu == "📈 Custom Graph":
        render_custom_dashboard(st, df, parse_process_column)

else:
    st.info(f"👈 Please upload a log file or ensure files exist in {DEFAULT_LOG_DIR}")
