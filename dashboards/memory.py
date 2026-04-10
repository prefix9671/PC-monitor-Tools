import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import (
    COLOR_INSPECTOR_FRAME,
    COLOR_INSPECTOR_MEM,
    COLOR_INSPECTOR_TOTAL,
    COLOR_MEM,
    COLOR_PROCESS,
    COLOR_SWAP,
)
from inspector_logs.core import INSPECTOR_PROCESS_LABEL


def _get_inspector_insp_df(aoi_df):
    if aoi_df is None or aoi_df.empty:
        return pd.DataFrame(columns=["Timestamp", "Inspector_Frame_Sec", "Inspector_Total_Sec", "Inspector_Total_Frames"])
    return (
        aoi_df.dropna(subset=["Inspector_Frame_Sec", "Inspector_Total_Sec"])
        [["Timestamp", "Inspector_Frame_Sec", "Inspector_Total_Sec", "Inspector_Total_Frames"]]
        .sort_values("Timestamp")
    )


def _get_inspector_mem_df(aoi_df):
    if aoi_df is None or aoi_df.empty:
        return pd.DataFrame(columns=["Timestamp", "Inspector_WorkingSet_KB", "Inspector_WorkingSet_MB", "Inspector_WorkingSet_GB"])
    return (
        aoi_df.dropna(subset=["Inspector_WorkingSet_GB"])
        [["Timestamp", "Inspector_WorkingSet_KB", "Inspector_WorkingSet_MB", "Inspector_WorkingSet_GB"]]
        .sort_values("Timestamp")
    )


def _merge_top_memory_processes(df, parse_process_column, inspector_mem_df):
    frames = []

    if df is not None and not df.empty and "Top5_Memory_MB" in df.columns:
        parsed = parse_process_column(df["Top5_Memory_MB"])
        if not parsed.empty:
            frames.append(parsed)

    if inspector_mem_df is not None and not inspector_mem_df.empty:
        frames.append(
            pd.DataFrame(
                [{"Process": INSPECTOR_PROCESS_LABEL, "Max_Value": float(inspector_mem_df["Inspector_WorkingSet_MB"].max())}]
            )
        )

    if not frames:
        return pd.DataFrame(columns=["Process", "Max_Value"])

    merged = pd.concat(frames, ignore_index=True)
    return (
        merged.groupby("Process", as_index=False)["Max_Value"]
        .max()
        .sort_values("Max_Value", ascending=False)
        .reset_index(drop=True)
    )


def _build_memory_trend_df(df, extract_process_time_series, inspector_mem_df):
    frames = []

    if df is not None and not df.empty and "Top5_Memory_MB" in df.columns:
        process_ts = extract_process_time_series(df, "Top5_Memory_MB")
        if not process_ts.empty:
            frames.append(process_ts)

    if inspector_mem_df is not None and not inspector_mem_df.empty:
        inspector_ts = inspector_mem_df.rename(columns={"Inspector_WorkingSet_MB": "Value"})[
            ["Timestamp", "Value"]
        ].copy()
        inspector_ts["Process"] = INSPECTOR_PROCESS_LABEL
        frames.append(inspector_ts[["Timestamp", "Process", "Value"]])

    if not frames:
        return pd.DataFrame(columns=["Timestamp", "Process", "Value"])

    return pd.concat(frames, ignore_index=True).sort_values("Timestamp")


def _build_external_inspector_df(df, extract_process_time_series):
    if df is None or df.empty or "Top5_Memory_MB" not in df.columns:
        return pd.DataFrame(columns=["Timestamp", "External_Inspector_GB"])

    process_ts = extract_process_time_series(df, "Top5_Memory_MB")
    if process_ts.empty:
        return pd.DataFrame(columns=["Timestamp", "External_Inspector_GB"])

    inspector_ts = process_ts[process_ts["Process"].str.contains("Inspector", case=False, na=False)].copy()
    if inspector_ts.empty:
        return pd.DataFrame(columns=["Timestamp", "External_Inspector_GB"])

    inspector_ts = (
        inspector_ts.groupby("Timestamp", as_index=False)["Value"].sum().rename(columns={"Value": "External_Inspector_MB"})
    )
    inspector_ts["External_Inspector_GB"] = inspector_ts["External_Inspector_MB"] / 1024.0
    return inspector_ts[["Timestamp", "External_Inspector_GB"]]


def _get_numeric_series(df, column_name):
    if df is None or df.empty or column_name not in df.columns:
        return pd.Series(dtype="float64")
    return pd.to_numeric(df[column_name], errors="coerce").dropna()


def _summarize_swap_usage(df):
    usage_series = _get_numeric_series(df, "Swap_Usage(%)")
    used_series = _get_numeric_series(df, "Swap_Used(GB)")
    total_series = _get_numeric_series(df, "Swap_Total(GB)")

    if usage_series.empty and used_series.empty and total_series.empty:
        return {
            "available": False,
            "latest_used_gb": 0.0,
            "peak_used_gb": 0.0,
            "latest_usage_pct": 0.0,
            "peak_usage_pct": 0.0,
            "total_gb": 0.0,
            "status_label": "로그 없음",
            "message": "현재 로그에는 페이지 파일 사용량 컬럼이 없어 가상 메모리 상태를 표시할 수 없습니다.",
            "message_level": "info",
        }

    latest_used_gb = float(used_series.iloc[-1]) if not used_series.empty else 0.0
    peak_used_gb = float(used_series.max()) if not used_series.empty else latest_used_gb
    latest_usage_pct = float(usage_series.iloc[-1]) if not usage_series.empty else 0.0
    peak_usage_pct = float(usage_series.max()) if not usage_series.empty else latest_usage_pct
    total_gb = float(total_series.iloc[-1]) if not total_series.empty else 0.0

    if total_gb <= 0:
        status_label = "페이지 파일 꺼짐"
        message = "이 로그 구간에서는 페이지 파일 크기가 0GB로 보고되어 스왑 메모리를 사용할 수 없는 상태입니다."
        message_level = "warning"
    elif latest_used_gb <= 0 and latest_usage_pct <= 0:
        status_label = "스왑 없음"
        message = "현재 스왑된 메모리가 없습니다."
        message_level = "info"
    else:
        status_label = "스왑 사용 중"
        message = (
            f"현재 페이지 파일에서 {latest_used_gb:.2f} GB "
            f"({latest_usage_pct:.1f}%)를 사용 중이며, 이 구간 최대값은 "
            f"{peak_used_gb:.2f} GB ({peak_usage_pct:.1f}%)입니다."
        )
        message_level = "warning"

    return {
        "available": True,
        "latest_used_gb": latest_used_gb,
        "peak_used_gb": peak_used_gb,
        "latest_usage_pct": latest_usage_pct,
        "peak_usage_pct": peak_usage_pct,
        "total_gb": total_gb,
        "status_label": status_label,
        "message": message,
        "message_level": message_level,
    }


def render_memory_dashboard(st, df, parse_process_column, extract_process_time_series, total_mem, aoi_df=None):
    has_system_data = df is not None and not df.empty
    insp_df = _get_inspector_insp_df(aoi_df)
    inspector_mem_df = _get_inspector_mem_df(aoi_df)
    swap_summary = _summarize_swap_usage(df) if has_system_data else None

    st.subheader("메모리 및 인스펙터 분석")

    if has_system_data and not insp_df.empty:
        st.caption("OS 메모리 그래프는 5초 집계 기준이며, 인스펙터 지표는 AOI 로그에서 추출한 이벤트 시점 데이터입니다.")
    elif has_system_data:
        st.caption("현재 표시되는 메모리 그래프와 프로세스 사용량은 5초 단위 집계값(평균/피크)입니다.")
    elif not insp_df.empty or not inspector_mem_df.empty:
        st.caption("시스템 모니터 CSV 없이 AOI / 인스펙터 로그 정보만 표시 중입니다.")

    if not insp_df.empty or not inspector_mem_df.empty:
        metric_cols = st.columns(3)

        if not insp_df.empty:
            metric_cols[0].metric(
                "최근 프레임 검사 시간",
                f"{insp_df['Inspector_Frame_Sec'].iloc[-1]:.2f}초",
                delta=f"최대 {insp_df['Inspector_Frame_Sec'].max():.2f}초",
            )
            metric_cols[1].metric(
                "최근 전체 검사 시간",
                f"{insp_df['Inspector_Total_Sec'].iloc[-1]:.2f}초",
                delta=f"{int(insp_df['Inspector_Total_Frames'].iloc[-1])}프레임",
            )
        else:
            metric_cols[0].metric("최근 프레임 검사 시간", "N/A")
            metric_cols[1].metric("최근 전체 검사 시간", "N/A")

        if not inspector_mem_df.empty:
            metric_cols[2].metric(
                "인스펙터 Working Set",
                f"{inspector_mem_df['Inspector_WorkingSet_GB'].iloc[-1]:.2f} GB",
                delta=f"최대 {inspector_mem_df['Inspector_WorkingSet_GB'].max():.2f} GB",
            )
        else:
            metric_cols[2].metric("인스펙터 Working Set", "N/A")

        st.divider()

        if not insp_df.empty or not inspector_mem_df.empty:
            st.caption("검사 시간/인스펙터 메모리 상세 시계열은 화면 아래 `검사 결과 XLSX 내보내기` 패널에서 확인할 수 있습니다.")

    if has_system_data:
        fig_mem = go.Figure()

        if "Mem_Usage_Avg(%)" not in df.columns:
            st.error(f"메모리 데이터가 없습니다. 현재 컬럼: {list(df.columns)}")
            return

        fig_mem.add_trace(
            go.Scatter(
                x=df["Timestamp"],
                y=df["Mem_Usage_Avg(%)"],
                name="실물 메모리 평균 사용률 (%)",
                mode="lines",
                line=dict(color=COLOR_MEM, width=2),
                fill="tozeroy",
            )
        )

        if "Swap_Usage(%)" in df.columns:
            fig_mem.add_trace(
                go.Scatter(
                    x=df["Timestamp"],
                    y=df["Swap_Usage(%)"],
                    name="스왑 사용률 (%)",
                    mode="lines",
                    line=dict(color=COLOR_SWAP, width=2),
                )
            )

            swap_start = df[df["Swap_Usage(%)"] > 1]["Timestamp"].min()
            if pd.notnull(swap_start):
                fig_mem.add_vline(
                    x=swap_start,
                    line_width=2,
                    line_dash="dash",
                    line_color="red",
                    annotation_text="스왑 시작",
                )
                fig_mem.add_vrect(
                    x0=swap_start,
                    x1=df["Timestamp"].max(),
                    fillcolor="red",
                    opacity=0.1,
                    layer="below",
                    line_width=0,
                )

        if "Mem_Used(GB)" in df.columns and df["Mem_Used(GB)"].notna().any():
            try:
                min_mem_idx = df["Mem_Used(GB)"].idxmin()
                max_mem_idx = df["Mem_Used(GB)"].idxmax()
                if pd.notna(min_mem_idx) and pd.notna(max_mem_idx) and max_mem_idx > min_mem_idx:
                    fig_mem.add_annotation(
                        x=df.loc[min_mem_idx, "Timestamp"],
                        y=df.loc[min_mem_idx, "Mem_Usage_Avg(%)"],
                        text="시작",
                        showarrow=True,
                        arrowhead=1,
                    )
                    fig_mem.add_annotation(
                        x=df.loc[max_mem_idx, "Timestamp"],
                        y=df.loc[max_mem_idx, "Mem_Usage_Avg(%)"],
                        text="최대",
                        showarrow=True,
                        arrowhead=1,
                    )
            except Exception:
                pass

        fig_mem.update_layout(
            title=f"실물 메모리 사용량 (시스템 메모리: {total_mem} GB)",
            yaxis=dict(title="사용률 (%)", range=[0, 100]),
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_mem, width="stretch")
        if swap_summary and swap_summary["available"]:
            swap_cols = st.columns(3)
            swap_cols[0].metric(
                "현재 페이지 파일 사용량",
                f"{swap_summary['latest_used_gb']:.2f} GB",
                delta=f"최대 {swap_summary['peak_used_gb']:.2f} GB",
            )
            swap_cols[1].metric(
                "현재 스왑 사용률",
                f"{swap_summary['latest_usage_pct']:.1f}%",
                delta=f"최대 {swap_summary['peak_usage_pct']:.1f}%",
            )
            swap_cols[2].metric(
                "가상 메모리 상태",
                swap_summary["status_label"],
                delta=f"총 페이지 파일 {swap_summary['total_gb']:.2f} GB",
            )
            if swap_summary["message_level"] == "warning":
                st.warning(swap_summary["message"])
            else:
                st.info(swap_summary["message"])
        st.caption("짙은 파란 선: 5초 평균 기준 실물 메모리 사용률입니다.")
        st.caption("옅은 파란 영역: 위 실물 메모리 사용률을 면적으로 강조한 표시이며, 별도의 다른 지표는 아닙니다.")
        if "Swap_Usage(%)" in df.columns:
            st.caption("주황색 선: 디스크 스왑(페이지 파일) 사용률입니다. RAM에 있던 일부 메모리가 디스크로 밀려난 비율을 뜻합니다.")
            swap_peak = pd.to_numeric(df["Swap_Usage(%)"], errors="coerce").fillna(0).max()
            if swap_peak <= 0:
                st.caption("이번 선택 구간에서는 현재 스왑된 메모리가 없어 주황색 선이 보이지 않거나 바닥에 붙어 있을 수 있습니다.")
        else:
            st.caption("현재 로그에는 스왑 사용률 컬럼이 없어 디스크 스왑 메모리 선은 표시되지 않습니다.")
        st.divider()

    # NOTE:
    # The dedicated "검사 결과 XLSX 내보내기" panel now owns the detailed
    # inspector-only charts below. We are intentionally hiding them here to
    # avoid duplicated dashboard content, but keeping the old code commented
    # out until follow-up verification is complete and explicit deletion is requested.
    #
    # if not insp_df.empty:
    #     fig_insp = make_subplots(specs=[[{"secondary_y": True}]])
    #     fig_insp.add_trace(
    #         go.Scatter(
    #             x=insp_df["Timestamp"],
    #             y=insp_df["Inspector_Total_Sec"],
    #             name="전체 검사 시간 (초)",
    #             mode="lines+markers",
    #             line=dict(color=COLOR_INSPECTOR_TOTAL, width=2),
    #             customdata=insp_df[["Inspector_Total_Frames"]],
    #             hovertemplate="시각=%{x}<br>전체=%{y:.2f}초<br>프레임=%{customdata[0]}<extra></extra>",
    #         ),
    #         secondary_y=False,
    #     )
    #     fig_insp.add_trace(
    #         go.Scatter(
    #             x=insp_df["Timestamp"],
    #             y=insp_df["Inspector_Frame_Sec"],
    #             name="프레임 검사 시간 (초/프레임)",
    #             mode="lines+markers",
    #             line=dict(color=COLOR_INSPECTOR_FRAME, width=2),
    #             hovertemplate="시각=%{x}<br>프레임=%{y:.2f}초/프레임<extra></extra>",
    #         ),
    #         secondary_y=True,
    #     )
    #     fig_insp.update_layout(
    #         title="인스펙터 검사 속도 시계열",
    #         hovermode="x unified",
    #         legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    #     )
    #     fig_insp.update_yaxes(title_text="전체 검사 시간 (초)", secondary_y=False)
    #     fig_insp.update_yaxes(title_text="프레임 검사 시간 (초/프레임)", secondary_y=True)
    #     st.plotly_chart(fig_insp, width="stretch")
    #     st.divider()
    #
    # if not inspector_mem_df.empty:
    #     fig_inspector_mem = go.Figure()
    #     fig_inspector_mem.add_trace(
    #         go.Scatter(
    #             x=inspector_mem_df["Timestamp"],
    #             y=inspector_mem_df["Inspector_WorkingSet_GB"],
    #             name="인스펙터 Working Set (로그, KB -> GB)",
    #             mode="lines+markers",
    #             line=dict(color=COLOR_INSPECTOR_MEM, width=2),
    #             hovertemplate="시각=%{x}<br>Working Set=%{y:.2f} GB<br>원본=%{customdata[0]:,.0f} KB<extra></extra>",
    #             customdata=inspector_mem_df[["Inspector_WorkingSet_KB"]],
    #         )
    #     )
    #     fig_inspector_mem.update_layout(
    #         title="AOI 로그 기준 인스펙터 Working Set 메모리",
    #         yaxis=dict(title="Working Set (GB)"),
    #         hovermode="x unified",
    #     )
    #     st.plotly_chart(fig_inspector_mem, width="stretch")
    #     st.divider()

    if has_system_data and not inspector_mem_df.empty:
        external_inspector_df = _build_external_inspector_df(df, extract_process_time_series)
        if not external_inspector_df.empty:
            fig_compare = go.Figure()
            fig_compare.add_trace(
                go.Scatter(
                    x=external_inspector_df["Timestamp"],
                    y=external_inspector_df["External_Inspector_GB"],
                    name="인스펙터 프로세스 (시스템 모니터, GB)",
                    mode="lines",
                    line=dict(color=COLOR_PROCESS, width=2),
                )
            )
            fig_compare.add_trace(
                go.Scatter(
                    x=inspector_mem_df["Timestamp"],
                    y=inspector_mem_df["Inspector_WorkingSet_GB"],
                    name="인스펙터 앱 (로그, KB -> GB)",
                    mode="lines+markers",
                    line=dict(color=COLOR_INSPECTOR_MEM, width=2),
                )
            )
            fig_compare.update_layout(
                title="외부 인스펙터 메모리와 로그 Working Set 비교",
                yaxis=dict(title="메모리 (GB)"),
                hovermode="x unified",
            )
            st.plotly_chart(fig_compare, width="stretch")
            st.divider()

    top_mem_df = _merge_top_memory_processes(df, parse_process_column, inspector_mem_df)
    if not top_mem_df.empty:
        st.subheader("상위 5개 메모리 프로세스 + 인스펙터 앱 (로그)")
        top_display_df = top_mem_df.head(5)
        fig_bar = px.bar(
            top_display_df,
            x="Process",
            y="Max_Value",
            title="프로세스 / 인스펙터 로그 최대 메모리 사용량 (MB)",
            labels={"Max_Value": "최대 메모리 (MB)"},
            text_auto=".0f",
        )
        fig_bar.update_traces(marker_color=COLOR_PROCESS)
        st.plotly_chart(fig_bar, width="stretch")

        st.divider()

        st.subheader("프로세스 메모리 추세 (상위 5개 + 인스펙터 앱)")
        selectable_names = top_display_df["Process"].tolist()
        selected_procs = []
        if selectable_names:
            st.write("시계열로 볼 프로세스를 선택하세요:")
            cols = st.columns(len(selectable_names))
            for idx, name in enumerate(selectable_names):
                default_selected = idx == 0 or name == INSPECTOR_PROCESS_LABEL
                if cols[idx].checkbox(f"{name}", value=default_selected):
                    selected_procs.append(name)

        if selected_procs:
            trend_df = _build_memory_trend_df(df, extract_process_time_series, inspector_mem_df)
            if not trend_df.empty:
                filtered_trend_df = trend_df[trend_df["Process"].isin(selected_procs)]
                if not filtered_trend_df.empty:
                    fig_trend = px.line(
                        filtered_trend_df,
                        x="Timestamp",
                        y="Value",
                        color="Process",
                        title="시간대별 메모리 사용량 (MB)",
                        labels={"Value": "메모리 (MB)"},
                    )
                    fig_trend.update_layout(hovermode="x unified")
                    st.plotly_chart(fig_trend, width="stretch")
                else:
                    st.info("선택한 프로세스의 시계열 데이터가 없습니다.")
            else:
                st.info("프로세스 메모리 추세 데이터가 없습니다.")

        with st.expander("상위 10개 상세 보기"):
            st.dataframe(top_mem_df.head(10))
    elif has_system_data:
        st.warning("프로세스 메모리 데이터가 없습니다.")
        if "Top5_Memory_MB" in df.columns:
            with st.expander("디버그: 원본 데이터 보기"):
                st.write("'Top5_Memory_MB' 상위 10개 행:")
                st.write(df["Top5_Memory_MB"].head(10))
                st.write("컬럼 타입:", df["Top5_Memory_MB"].dtype)
    else:
        st.info("메모리 프로세스 비교 데이터가 아직 없습니다.")
