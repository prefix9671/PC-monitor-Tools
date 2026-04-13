# app.py
import json
import os
import subprocess
import sys
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from collectors.cpu_temperature_diagnostics import write_cpu_temperature_diagnostic_log
from config import DEFAULT_LOG_DIR, MANUAL_SITE_DIR
from dashboards.cpu import render_cpu_dashboard
from dashboards.custom import render_custom_dashboard
from dashboards.inspection_export import render_inspection_export_panel
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
from inspector_logs.core import build_inspection_records, resolve_inspector_log_paths
from parsers import extract_process_time_series, parse_process_column
from runtime_patches import apply_streamlit_runtime_patches


apply_streamlit_runtime_patches()
st.set_page_config(page_title="시스템 자원 모니터", page_icon="📊", layout="wide")

st.title("시스템 자원 대시보드")
st.markdown("---")

df = None
aoi_df = None
system_df_full = None
aoi_df_full = None
inspection_records_df = None
system_target_files = []
resolved_aoi_paths = []
loaded_aoi_sources = []
inspection_filter_start = None
inspection_filter_end = None
inspection_filter_end_user_specified = False
st.session_state.setdefault("cpu_temp_diagnostic_result", None)


with st.sidebar:
    st.header("제어판")
    st.info("Python Collector는 1초 샘플링 / 5초 집계 기준으로 동작합니다.")

    if st.button("모니터링 시작"):
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
            st.success("Python 모니터를 시작했습니다.")
            st.info("명령 프롬프트 창이 열리며, 창을 닫으면 모니터링이 종료됩니다.")
        except Exception as exc:
            st.error(f"실행 실패: {exc}")

    st.divider()
    if st.button("로그 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.header("로그 파일 선택")

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
    uploaded_files = st.file_uploader("시스템 모니터 CSV 업로드", type=["csv"], accept_multiple_files=True)

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

    selected_dates = st.multiselect(f"{DEFAULT_LOG_DIR}에서 기록 날짜 선택", log_groups, default=default_dates)

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
            st.success(f"시스템 모니터 행 {len(df)}개를 불러왔습니다.")

    st.divider()
    st.header("AOI / 인스펙터 로그")
    uploaded_aoi_files = st.file_uploader(
        "AOI / 인스펙터 로그 업로드",
        type=["log", "txt"],
        accept_multiple_files=True,
        help="파일 탐색기에서 AOI / 인스펙터 TXT 또는 LOG 파일을 직접 선택합니다.",
    )
    st.caption("권장: Browse files로 AOI / 인스펙터 TXT 또는 LOG 파일을 직접 선택하세요. 업로드 제한은 1GB입니다.")

    aoi_frames = []
    if uploaded_aoi_files:
        try:
            uploaded_payloads = tuple((uploaded_file.name, uploaded_file.getvalue()) for uploaded_file in uploaded_aoi_files)
            uploaded_aoi_df = load_inspector_uploaded_data(uploaded_payloads)
            if uploaded_aoi_df is not None and not uploaded_aoi_df.empty:
                aoi_frames.append(uploaded_aoi_df)
                loaded_aoi_sources.extend(uploaded_file.name for uploaded_file in uploaded_aoi_files)
                st.success(
                    f"업로드한 파일 {len(uploaded_aoi_files)}개에서 인스펙터 이벤트 {len(uploaded_aoi_df)}행을 불러왔습니다."
                )
            else:
                st.warning("파일은 읽었지만 InspTime / Working Set 라인을 찾지 못했습니다.")
        except Exception as exc:
            st.error(f"업로드한 AOI 로그를 불러오지 못했습니다: {exc}")

    with st.expander("고급: 경로로 AOI / 인스펙터 로그 불러오기", expanded=False):
        aoi_path_input = st.text_area(
            "AOI 로그 파일 또는 폴더 경로",
            value="",
            height=90,
            placeholder=r"C:\Inspector\shared\operation_0319_north side grab",
        )
        st.caption("파일 경로, 폴더 경로, 확장자 없는 기본 경로를 지원합니다. 한 줄에 하나씩 입력하세요.")

        if aoi_path_input.strip():
            try:
                resolved_aoi_paths = resolve_inspector_log_paths(aoi_path_input)
                if resolved_aoi_paths:
                    path_aoi_df = load_inspector_data(aoi_path_input)
                    if path_aoi_df is not None and not path_aoi_df.empty:
                        aoi_frames.append(path_aoi_df)
                        loaded_aoi_sources.extend(path.name for path in resolved_aoi_paths)
                        st.success(
                            f"경로에서 찾은 파일 {len(resolved_aoi_paths)}개에서 인스펙터 이벤트 {len(path_aoi_df)}행을 불러왔습니다."
                        )
                    else:
                        st.warning("경로는 찾았지만 InspTime / Working Set 라인을 찾지 못했습니다.")
                else:
                    st.warning("입력한 경로와 일치하는 AOI 로그가 없습니다. 기본 경로만 넣으면 `.log`, `.txt`를 자동으로 확인합니다.")
            except Exception as exc:
                st.error(f"AOI 로그 경로를 불러오지 못했습니다: {exc}")

    if aoi_frames:
        aoi_df = (
            pd.concat(aoi_frames, ignore_index=True)
            .drop_duplicates()
            .sort_values("Timestamp")
            .reset_index(drop=True)
        )
        if loaded_aoi_sources:
            st.caption(f"AOI 원본: {', '.join(dict.fromkeys(loaded_aoi_sources))}")

    has_system_data = df is not None and not df.empty
    has_inspector_data = aoi_df is not None and not aoi_df.empty
    system_df_full = df
    aoi_df_full = aoi_df
    inspection_records_df = build_inspection_records(aoi_df_full, system_df_full) if has_inspector_data else None

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
                    "시간 범위",
                    min_value=min_time.to_pydatetime(),
                    max_value=max_time.to_pydatetime(),
                    key=slider_key,
                )

                input_col1, input_col2 = st.columns(2)
                with input_col1:
                    st.text_input(
                        "시작 시간",
                        key="time_range_start_input",
                        placeholder="YYYY-MM-DD HH:MM:SS 또는 HH:MM[:SS]",
                    )
                with input_col2:
                    st.text_input(
                        "종료 시간",
                        key="time_range_end_input",
                        placeholder="YYYY-MM-DD HH:MM:SS 또는 HH:MM[:SS]",
                    )

                st.caption(
                    "수동 입력은 선택 사항입니다. 둘 다 비우면 슬라이더 기준으로 동작합니다. "
                    "시작만 입력하면 마지막 샘플까지, 종료만 입력하면 첫 샘플부터 표시합니다."
                )

                if manual_range["used_manual"]:
                    if manual_range["error"]:
                        st.warning(manual_range["error"])
                        start_time = pd.to_datetime(time_range[0])
                        end_time = pd.to_datetime(time_range[1])
                        inspection_filter_end_user_specified = False
                    else:
                        start_time = manual_range["resolved_start"]
                        end_time = manual_range["resolved_end"]
                        inspection_filter_end_user_specified = manual_range["requested_end"] is not None
                        st.caption(
                            "적용된 수동 범위: "
                            f"{start_time.strftime('%Y-%m-%d %H:%M:%S')} -> "
                            f"{end_time.strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        if manual_range["requested_start"] is not None and manual_range["start_aligned"]:
                            st.caption(
                                "시작 시간을 가장 가까운 사용 가능 샘플로 보정했습니다: "
                                f"{manual_range['requested_start'].strftime('%Y-%m-%d %H:%M:%S')} -> "
                                f"{start_time.strftime('%Y-%m-%d %H:%M:%S')}"
                            )
                        if manual_range["requested_end"] is not None and manual_range["end_aligned"]:
                            st.caption(
                                "종료 시간을 가장 가까운 사용 가능 샘플로 보정했습니다: "
                                f"{manual_range['requested_end'].strftime('%Y-%m-%d %H:%M:%S')} -> "
                                f"{end_time.strftime('%Y-%m-%d %H:%M:%S')}"
                            )
                        for note in manual_range["notes"]:
                            st.caption(note)
                        st.caption("다시 슬라이더로 제어하려면 시작 시간과 종료 시간을 비우세요.")
                else:
                    start_time = pd.to_datetime(time_range[0])
                    end_time = pd.to_datetime(time_range[1])
                    inspection_filter_end_user_specified = False

                inspection_filter_start = start_time
                inspection_filter_end = end_time

                if has_system_data:
                    df = filter_dataframe_by_time_range(df, start_time, end_time)
                if has_inspector_data:
                    aoi_df = filter_dataframe_by_time_range(aoi_df, start_time, end_time)
            else:
                inspection_filter_start = min_time
                inspection_filter_end = max_time
                inspection_filter_end_user_specified = False
                st.info("데이터가 1개뿐이라 시간 필터를 건너뜁니다.")

        st.divider()
        if st.button("매뉴얼 열기 (MkDocs)", width="stretch"):
            if getattr(sys, "frozen", False):
                manual_candidates = [os.path.join(sys._MEIPASS, "site", "index.html")]
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
                manual_candidates = [
                    os.path.join(base_path, MANUAL_SITE_DIR, "index.html"),
                    os.path.join(base_path, "site", "index.html"),
                ]

            manual_path = next((path for path in manual_candidates if os.path.exists(path)), None)

            if manual_path:
                webbrowser.open_new_tab(Path(manual_path).as_uri())
            else:
                st.error("매뉴얼 페이지를 찾을 수 없습니다. 먼저 `python -m mkdocs build`를 실행해 주세요.")

        st.divider()
        st.markdown("### 데이터 내보내기")
        if has_system_data:
            csv_data = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="병합 CSV 다운로드",
                data=csv_data,
                file_name=f"Merged_Log_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
            )

        if has_inspector_data:
            inspector_csv = aoi_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="파싱된 인스펙터 로그 CSV 다운로드",
                data=inspector_csv,
                file_name=f"Inspector_Log_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
            )

        st.caption("2026 시스템 자원 모니터 - v1.2.0")


has_system_data = df is not None and not df.empty
has_inspector_data = aoi_df is not None and not aoi_df.empty

if has_system_data or has_inspector_data:
    total_mem_gb = "N/A"

    if has_system_data:
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

        st.markdown("#### 시스템 사양 정보")
        st.write(f"- **물리 메모리**: {physical_mem_gb} GB")
        st.write(f"- **OS 사용 가능 메모리**: {os_total_mem_gb} GB")
        st.write("- 실제 대시보드 계산은 OS 사용 가능 메모리를 기준으로 합니다.")

        total_mem_gb = os_total_mem_gb
        st.markdown("---")

        max_mem_gb = f"{df['Mem_Used(GB)'].max():.2f}" if "Mem_Used(GB)" in df.columns else "0.00"
        max_mem_pct = f"{df['Mem_Usage_Avg(%)'].max():.2f}" if "Mem_Usage_Avg(%)" in df.columns else "0.00"

        trend_str = "안정적 또는 변동형"
        if "Mem_Used(GB)" in df.columns and df["Mem_Used(GB)"].notna().any():
            try:
                min_mem_idx = df["Mem_Used(GB)"].idxmin()
                max_mem_idx = df["Mem_Used(GB)"].idxmax()
                if pd.notna(min_mem_idx) and pd.notna(max_mem_idx):
                    min_time = df.loc[min_mem_idx, "Timestamp"]
                    max_time = df.loc[max_mem_idx, "Timestamp"]
                    if max_time > min_time:
                        duration = max_time - min_time
                        trend_str = f"{str(duration).split('.')[0]} 동안 증가"
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
            label="최대 메모리 사용량",
            value=f"{max_mem_gb} GB",
            delta=f"전체 {total_mem_gb}GB 중 {max_mem_pct}%",
            delta_color="inverse",
        )
        kpi2.metric(
            label="메모리 상승 구간",
            value=trend_str,
            help="선택한 구간에서 메모리 최소값부터 최대값까지 걸린 시간입니다.",
        )
        kpi3.metric(
            label="최상위 메모리 프로세스",
            value=top_offender,
            delta=f"최대 {top_offender_val:.2f} GB",
            delta_color="inverse",
        )
        st.markdown("---")
    else:
        st.info("시스템 모니터 CSV가 없어 인스펙터 로그 지표만 표시합니다.")

    tab_list = []
    if has_system_data:
        tab_list.append("CPU 대시보드")
    tab_list.append("메모리 + 인스펙터 대시보드")
    if has_system_data:
        tab_list.append("스토리지 대시보드")
        tab_list.append("사용자 정의 그래프")

    menu = st.selectbox("대시보드 보기 선택", tab_list)

    if menu == "CPU 대시보드":
        render_cpu_dashboard(st, df)
    elif menu == "메모리 + 인스펙터 대시보드":
        render_memory_dashboard(
            st,
            df,
            parse_process_column,
            extract_process_time_series,
            total_mem_gb,
            aoi_df=aoi_df,
        )
    elif menu == "스토리지 대시보드":
        render_storage_dashboard(st, df, parse_process_column)
    elif menu == "사용자 정의 그래프":
        render_custom_dashboard(st, df, parse_process_column)

    if inspection_records_df is not None:
        st.markdown("---")
        render_inspection_export_panel(
            st,
            inspection_records_df,
            filter_start_time=inspection_filter_start,
            filter_end_time=inspection_filter_end,
            filter_end_user_specified=inspection_filter_end_user_specified,
        )
else:
    st.info(
        f"시스템 모니터 CSV를 업로드하거나 {DEFAULT_LOG_DIR}에 로그가 있는지 확인하세요. "
        "또는 AOI / 인스펙터 로그를 업로드해 주세요."
    )

st.markdown("---")
st.subheader("CPU 온도 진단")
st.caption(
    "일반 PC는 LibreHardwareMonitor 코어 온도 워커 상태와 fallback provider 결과를 함께 점검하고, "
    f"로그는 {DEFAULT_LOG_DIR}에 저장합니다."
)

if st.button("CPU 온도 테스트 실행 및 로그 저장", key="cpu_temp_diagnostic_button"):
    with st.spinner("CPU 온도 진단 로그를 수집하는 중입니다..."):
        try:
            diagnostics, log_path, latest_path = write_cpu_temperature_diagnostic_log(DEFAULT_LOG_DIR)
            st.session_state["cpu_temp_diagnostic_result"] = {
                "diagnostics": diagnostics,
                "log_path": str(log_path),
                "latest_path": str(latest_path),
            }
            st.success(f"CPU 온도 진단 로그를 저장했습니다: {log_path}")
        except Exception as exc:
            st.session_state["cpu_temp_diagnostic_result"] = {
                "error": str(exc),
            }
            st.error(f"CPU 온도 진단에 실패했습니다: {exc}")

cpu_temp_diagnostic_result = st.session_state.get("cpu_temp_diagnostic_result")
if cpu_temp_diagnostic_result:
    if cpu_temp_diagnostic_result.get("error"):
        st.error(f"최근 CPU 온도 진단 실패: {cpu_temp_diagnostic_result['error']}")
    else:
        diagnostics = cpu_temp_diagnostic_result["diagnostics"]
        force_refresh_probe = diagnostics.get("force_refresh_probe") or {}
        st.write(f"- 마지막 진단 시각: **{diagnostics.get('generated_at', 'N/A')}**")
        st.write(f"- 진단 로그: **{cpu_temp_diagnostic_result['log_path']}**")
        st.write(f"- 최신 로그 별칭: **{cpu_temp_diagnostic_result['latest_path']}**")
        st.write(f"- 강제 새로고침 값: **{force_refresh_probe.get('value_c', 'N/A')}°C**")
        st.write(f"- 선택 source: **{force_refresh_probe.get('source_name', 'Unavailable')}**")
        st.write(f"- 선택 sensor: **{force_refresh_probe.get('source_detail', 'N/A')}**")
        with st.expander("CPU 온도 진단 JSON 보기", expanded=False):
            st.code(
                json.dumps(cpu_temp_diagnostic_result["diagnostics"], ensure_ascii=False, indent=2),
                language="json",
            )
