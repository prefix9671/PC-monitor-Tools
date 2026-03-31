# app.py
import os
import subprocess
import sys
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from config import DEFAULT_LOG_DIR
from dashboards.cpu import render_cpu_dashboard
from dashboards.custom import render_custom_dashboard
from dashboards.memory import render_memory_dashboard
from dashboards.storage import render_storage_dashboard
from data_loader import (
    collect_available_timestamps,
    filter_dataframe_by_time_range,
    load_data,
    load_inspector_data,
    load_inspector_uploaded_data,
    resolve_time_filter_range,
)
from inspector_logs.core import resolve_inspector_log_paths
from parsers import extract_process_time_series, parse_process_column

# ==========================================
# 1. 설정 및 데이터 로딩
# ==========================================
st.set_page_config(page_title="System Resource Monitor", page_icon="🖥️", layout="wide")

st.title("🖥️ System Resource Dashboard")
st.markdown("---")

df = None
aoi_df = None
system_target_files = []
resolved_aoi_paths = []
loaded_aoi_sources = []

# 사이드바: 파일 선택
with st.sidebar:
    st.header("🎮 Control Panel")

    # Configuration Inputs
    st.info("💡 Python Collector runs with a fixed 1s Sampling / 5s Aggregation interval.")

    if st.button("Start Monitor"):
        if getattr(sys, "frozen", False):
            exe_path = sys.executable
            cmd = f"Start-Process -FilePath '{exe_path}' -ArgumentList 'start' -Verb RunAs"
        else:
            exe_path = sys.executable
            cli_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cli.py")
            cmd = f"Start-Process -FilePath '{exe_path}' -ArgumentList '{cli_path}', 'start' -Verb RunAs"

        try:
            subprocess.Popen(
                ["powershell", "-Command", cmd],
                shell=True,
            )
            st.success("Started Python Monitor (5s Peak/Avg)!")
            st.info("A command window will appear. Close it to stop monitoring.")
        except Exception as exc:
            st.error(f"Failed: {exc}")

    st.divider()
    if st.button("Refresh Log Data 🔄", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.header("📂 Log File Selection")

    # 1. 기본 경로 탐색
    log_groups = set()
    if os.path.exists(DEFAULT_LOG_DIR):
        for file_name in os.listdir(DEFAULT_LOG_DIR):
            if (file_name.startswith("resource_") or file_name.startswith("process_")) and file_name.endswith(".csv"):
                try:
                    date_str = file_name.split("_")[1].split(".")[0]
                    log_groups.add(date_str)
                except IndexError:
                    pass

    log_groups = sorted(list(log_groups), reverse=True)

    uploaded_files = st.file_uploader("Upload Log CSV(s)", type=["csv"], accept_multiple_files=True)

    # 기본값으로 오늘 기준 최근 1주일(7일) 이내의 로그 자동 선택
    default_dates = []
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)

    for date_str in log_groups:
        try:
            date_value = datetime.strptime(date_str, "%Y%m%d").date()
            if week_ago <= date_value <= today:
                default_dates.append(date_str)
        except ValueError:
            pass

    if not default_dates and log_groups:
        default_dates = [log_groups[0]]

    selected_dates = st.multiselect(f"Select Record Date from {DEFAULT_LOG_DIR}", log_groups, default=default_dates)

    if uploaded_files:
        system_target_files.extend(uploaded_files)

    if selected_dates:
        for date_str in selected_dates:
            res_file = os.path.join(DEFAULT_LOG_DIR, f"resource_{date_str}.csv")
            proc_file = os.path.join(DEFAULT_LOG_DIR, f"process_{date_str}.csv")
            if os.path.exists(res_file):
                system_target_files.append(res_file)
            if os.path.exists(proc_file):
                system_target_files.append(proc_file)

    if system_target_files:
        df = load_data(system_target_files)
        if df is not None and not df.empty:
            st.success(f"Loaded system monitor rows: {len(df)}")

    st.divider()
    st.header("🧪 AOI / Inspector Log")
    uploaded_aoi_files = st.file_uploader(
        "Upload AOI / Inspector Log(s)",
        type=["log", "txt"],
        accept_multiple_files=True,
        help="Use Browse files to select AOI / Inspector TXT or LOG files directly.",
    )
    st.caption("권장: Browse files로 AOI / Inspector TXT 또는 LOG 파일을 직접 선택하세요.")

    aoi_frames = []
    if uploaded_aoi_files:
        try:
            uploaded_payloads = tuple((uploaded_file.name, uploaded_file.getvalue()) for uploaded_file in uploaded_aoi_files)
            uploaded_aoi_df = load_inspector_uploaded_data(uploaded_payloads)
            if uploaded_aoi_df is not None and not uploaded_aoi_df.empty:
                aoi_frames.append(uploaded_aoi_df)
                loaded_aoi_sources.extend(uploaded_file.name for uploaded_file in uploaded_aoi_files)
                st.success(
                    f"Loaded Inspector events: {len(uploaded_aoi_df)} rows from {len(uploaded_aoi_files)} uploaded file(s)"
                )
            else:
                st.warning("Uploaded AOI / Inspector files were read, but no InspTime / Working Set lines were parsed.")
        except Exception as exc:
            st.error(f"Failed to load uploaded AOI log files: {exc}")

    with st.expander("Advanced: Load AOI / Inspector Log by Path", expanded=False):
        aoi_path_input = st.text_area(
            "AOI Log File or Folder Path(s)",
            value="",
            height=90,
            placeholder=r"C:\Inspector\shared\operation_0319_north side grab",
        )
        st.caption("Supports file paths, folder paths, or a base path without extension. Use one path per line.")

        if aoi_path_input.strip():
            try:
                resolved_aoi_paths = resolve_inspector_log_paths(aoi_path_input)
                if resolved_aoi_paths:
                    path_aoi_df = load_inspector_data(aoi_path_input)
                    if path_aoi_df is not None and not path_aoi_df.empty:
                        aoi_frames.append(path_aoi_df)
                        loaded_aoi_sources.extend(path.name for path in resolved_aoi_paths)
                        st.success(
                            f"Loaded Inspector events: {len(path_aoi_df)} rows from {len(resolved_aoi_paths)} path file(s)"
                        )
                    else:
                        st.warning("AOI log paths were resolved, but no InspTime / Working Set lines were parsed.")
                else:
                    st.warning("No AOI log files matched the given path. If you entered a base path, `.log` or `.txt` will be tried automatically.")
            except Exception as exc:
                st.error(f"Failed to load AOI log path: {exc}")

    if aoi_frames:
        aoi_df = (
            pd.concat(aoi_frames, ignore_index=True)
            .drop_duplicates()
            .sort_values("Timestamp")
            .reset_index(drop=True)
        )
        if loaded_aoi_sources:
            st.caption(f"AOI sources: {', '.join(dict.fromkeys(loaded_aoi_sources))}")

    has_system_data = df is not None and not df.empty
    has_inspector_data = aoi_df is not None and not aoi_df.empty

    if has_system_data or has_inspector_data:
        available_timestamps = collect_available_timestamps(df, aoi_df)

        if not available_timestamps.empty:
            min_time = pd.Timestamp(available_timestamps.min())
            max_time = pd.Timestamp(available_timestamps.max())

            st.session_state.setdefault("time_range_start_input", "")
            st.session_state.setdefault("time_range_end_input", "")

            manual_range = resolve_time_filter_range(
                available_timestamps,
                start_input=st.session_state["time_range_start_input"],
                end_input=st.session_state["time_range_end_input"],
            )

            slider_key = "time_range_slider"
            slider_bounds_key = "time_range_slider_bounds"
            current_bounds = (min_time.isoformat(), max_time.isoformat())

            if slider_key not in st.session_state or st.session_state.get(slider_bounds_key) != current_bounds:
                st.session_state[slider_key] = (min_time.to_pydatetime(), max_time.to_pydatetime())
                st.session_state[slider_bounds_key] = current_bounds

            if manual_range["used_manual"] and not manual_range["error"]:
                st.session_state[slider_key] = (
                    manual_range["resolved_start"].to_pydatetime(),
                    manual_range["resolved_end"].to_pydatetime(),
                )

            if min_time < max_time:
                time_range = st.slider(
                    "Time Range",
                    min_value=min_time.to_pydatetime(),
                    max_value=max_time.to_pydatetime(),
                    key=slider_key,
                )

                input_col1, input_col2 = st.columns(2)
                with input_col1:
                    st.text_input(
                        "Start Time",
                        key="time_range_start_input",
                        placeholder="YYYY-MM-DD HH:MM:SS or HH:MM[:SS]",
                    )
                with input_col2:
                    st.text_input(
                        "End Time",
                        key="time_range_end_input",
                        placeholder="YYYY-MM-DD HH:MM:SS or HH:MM[:SS]",
                    )

                st.caption(
                    "Optional manual override: leave both blank to use the slider. "
                    "If only Start is set, the range runs to the last sample. "
                    "If only End is set, the range starts at the first sample."
                )

                if manual_range["used_manual"]:
                    if manual_range["error"]:
                        st.warning(manual_range["error"])
                        start_time = pd.to_datetime(time_range[0])
                        end_time = pd.to_datetime(time_range[1])
                    else:
                        start_time = manual_range["resolved_start"]
                        end_time = manual_range["resolved_end"]
                        st.caption(
                            "Applied manual range: "
                            f"{start_time.strftime('%Y-%m-%d %H:%M:%S')} -> "
                            f"{end_time.strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        if manual_range["requested_start"] is not None and manual_range["start_aligned"]:
                            st.caption(
                                "Start aligned to nearest available sample: "
                                f"{manual_range['requested_start'].strftime('%Y-%m-%d %H:%M:%S')} -> "
                                f"{start_time.strftime('%Y-%m-%d %H:%M:%S')}"
                            )
                        if manual_range["requested_end"] is not None and manual_range["end_aligned"]:
                            st.caption(
                                "End aligned to nearest available sample: "
                                f"{manual_range['requested_end'].strftime('%Y-%m-%d %H:%M:%S')} -> "
                                f"{end_time.strftime('%Y-%m-%d %H:%M:%S')}"
                            )
                        for note in manual_range["notes"]:
                            st.caption(note)
                        st.caption("Clear Start Time and End Time to use the slider directly again.")
                else:
                    start_time = pd.to_datetime(time_range[0])
                    end_time = pd.to_datetime(time_range[1])

                if has_system_data:
                    df = filter_dataframe_by_time_range(df, start_time, end_time)
                if has_inspector_data:
                    aoi_df = filter_dataframe_by_time_range(aoi_df, start_time, end_time)
            else:
                st.info("💡 Only one data point available, time filtering skipped.")

        st.divider()
        if st.button("📖 웹 매뉴얼 열기 (MkDocs)", width="stretch"):
            if getattr(sys, "frozen", False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))

            manual_path = os.path.join(base_path, "site", "index.html")

            if os.path.exists(manual_path):
                webbrowser.open_new_tab(Path(manual_path).as_uri())
            else:
                st.error(f"매뉴얼 사이트를 찾을 수 없습니다: {manual_path}")

        st.divider()
        st.markdown("### 💾 Export Data")
        if has_system_data:
            csv_data = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="Download Merged CSV",
                data=csv_data,
                file_name=f"Merged_Log_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
            )

        if has_inspector_data:
            inspector_csv = aoi_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="Download Parsed Inspector Log CSV",
                data=inspector_csv,
                file_name=f"Inspector_Log_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
            )

        st.caption("© 2026 System Resource Monitor - v1.2.0")

# ==========================================
# 2. 메인 대시보드 UI
# ==========================================

has_system_data = df is not None and not df.empty
has_inspector_data = aoi_df is not None and not aoi_df.empty

if has_system_data or has_inspector_data:
    total_mem_gb = "N/A"

    if has_system_data:
        st.markdown("---")

        try:
            if "PhysicalMem(GB)" in df.columns and pd.notna(df["PhysicalMem(GB)"].iloc[0]):
                physical_mem_gb = f"{float(df['PhysicalMem(GB)'].iloc[0]):.2f}"
            else:
                physical_mem_gb = "N/A"

            if "OSTotalMem(GB)" in df.columns and pd.notna(df["OSTotalMem(GB)"].iloc[0]):
                os_total_mem_gb = f"{float(df['OSTotalMem(GB)'].iloc[0]):.2f}"
            else:
                os_total_mem_gb = "N/A"
        except Exception:
            physical_mem_gb = "N/A"
            os_total_mem_gb = "N/A"

        st.markdown("#### 🖥️ 시스템 사양 정보")
        st.write(f"- **물리 장착 메모리**: {physical_mem_gb} GB")
        st.write(f"- **OS 사용 가능 메모리**: {os_total_mem_gb} GB")
        st.write("※ 실제 사용 가능 메모리 %로 계산하였습니다.")

        total_mem_gb = os_total_mem_gb
        st.markdown("---")

        max_mem_gb = f"{df['Mem_Used(GB)'].max():.2f}" if "Mem_Used(GB)" in df.columns else "0.00"
        max_mem_pct = f"{df['Mem_Usage_Avg(%)'].max():.2f}" if "Mem_Usage_Avg(%)" in df.columns else "0.00"

        trend_str = "- Stable or Fluctuating"
        if "Mem_Used(GB)" in df.columns and df["Mem_Used(GB)"].notna().any():
            try:
                min_mem_idx = df["Mem_Used(GB)"].idxmin()
                max_mem_idx = df["Mem_Used(GB)"].idxmax()
                if pd.notna(min_mem_idx) and pd.notna(max_mem_idx):
                    min_time = df.loc[min_mem_idx, "Timestamp"]
                    max_time = df.loc[max_mem_idx, "Timestamp"]
                    if max_time > min_time:
                        duration = max_time - min_time
                        trend_str = f"↗ {str(duration).split('.')[0]} duration"
            except Exception:
                pass

        top_offender = "N/A"
        top_offender_val = 0.0
        if "Top5_Memory_MB" in df.columns:
            top_proc_df = parse_process_column(df["Top5_Memory_MB"])
            if not top_proc_df.empty:
                top_offender = top_proc_df.iloc[0]["Process"]
                top_offender_val = top_proc_df.iloc[0]["Max_Value"] / 1024.0

        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric(
            label="📈 Peak Memory Usage",
            value=f"{max_mem_gb} GB",
            delta=f"{max_mem_pct}% of {total_mem_gb}GB",
            delta_color="inverse",
        )
        kpi2.metric(
            label="⏱ Memory Ramp-up Duration",
            value=trend_str,
            help="Time taken from minimum to maximum memory usage in selected range.",
        )
        kpi3.metric(
            label="🔥 Top Offender Process",
            value=top_offender,
            delta=f"{top_offender_val:.2f} GB Max",
            delta_color="inverse",
        )
        st.markdown("---")
    else:
        st.info("System monitor CSV is not loaded. Showing Inspector log metrics only.")

    tab_list = []
    if has_system_data:
        tab_list.append("📊 CPU Dashboard")
    tab_list.append("🧠 Memory AND Inspector Dashboard")
    if has_system_data:
        tab_list.append("💾 Storage Dashboard")
        tab_list.append("📈 Custom Graph")

    menu = st.selectbox("Select Dashboard View", tab_list)

    if menu == "📊 CPU Dashboard":
        render_cpu_dashboard(st, df)
    elif menu == "🧠 Memory AND Inspector Dashboard":
        render_memory_dashboard(
            st,
            df,
            parse_process_column,
            extract_process_time_series,
            total_mem_gb,
            aoi_df=aoi_df,
        )
    elif menu == "💾 Storage Dashboard":
        render_storage_dashboard(st, df, parse_process_column)
    elif menu == "📈 Custom Graph":
        render_custom_dashboard(st, df, parse_process_column)

else:
    st.info(
        f"👈 Please upload a system monitor CSV, ensure files exist in {DEFAULT_LOG_DIR}, "
        "or upload an AOI / Inspector log file."
    )
