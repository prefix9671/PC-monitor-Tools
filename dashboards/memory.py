# dashboards/memory.py
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


def render_memory_dashboard(st, df, parse_process_column, extract_process_time_series, total_mem, aoi_df=None):
    has_system_data = df is not None and not df.empty
    insp_df = _get_inspector_insp_df(aoi_df)
    inspector_mem_df = _get_inspector_mem_df(aoi_df)

    st.subheader("Memory AND Inspector Analysis")

    if has_system_data and not insp_df.empty:
        st.caption(
            "ℹ️ OS 메모리 트렌드는 5초 집계값이고, Inspector 값은 AOI 로그에서 추출한 이벤트 시점 데이터입니다."
        )
    elif has_system_data:
        st.caption("ℹ️ 현재 표시되는 메모리 트렌드 및 프로세스 사용량은 5초 단위 집계값(Avg/Peak)입니다.")
    elif not insp_df.empty or not inspector_mem_df.empty:
        st.caption("ℹ️ System monitor CSV 없이 AOI / Inspector 로그 정보만 표시 중입니다.")

    if not insp_df.empty or not inspector_mem_df.empty:
        metric_cols = st.columns(3)

        if not insp_df.empty:
            metric_cols[0].metric(
                "🧪 Latest Frame Inspect Time",
                f"{insp_df['Inspector_Frame_Sec'].iloc[-1]:.2f} sec",
                delta=f"Peak {insp_df['Inspector_Frame_Sec'].max():.2f} sec",
            )
            metric_cols[1].metric(
                "🧩 Latest Total Inspect Time",
                f"{insp_df['Inspector_Total_Sec'].iloc[-1]:.2f} sec",
                delta=f"{int(insp_df['Inspector_Total_Frames'].iloc[-1])} frame",
            )
        else:
            metric_cols[0].metric("🧪 Latest Frame Inspect Time", "N/A")
            metric_cols[1].metric("🧩 Latest Total Inspect Time", "N/A")

        if not inspector_mem_df.empty:
            metric_cols[2].metric(
                "🧠 Inspector Working Set",
                f"{inspector_mem_df['Inspector_WorkingSet_GB'].iloc[-1]:.2f} GB",
                delta=f"Peak {inspector_mem_df['Inspector_WorkingSet_GB'].max():.2f} GB",
            )
        else:
            metric_cols[2].metric("🧠 Inspector Working Set", "N/A")

        st.divider()

    # 1. OS Memory Graph
    if has_system_data:
        fig_mem = go.Figure()

        if "Mem_Usage_Avg(%)" not in df.columns:
            st.error(f"❌ Memory data not found. Available columns: {list(df.columns)}")
            return

        fig_mem.add_trace(
            go.Scatter(
                x=df["Timestamp"],
                y=df["Mem_Usage_Avg(%)"],
                name="Physical Memory Avg (%)",
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
                    name="Swap Usage (%)",
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
                    annotation_text="Swap Started",
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
                        text="Start",
                        showarrow=True,
                        arrowhead=1,
                    )
                    fig_mem.add_annotation(
                        x=df.loc[max_mem_idx, "Timestamp"],
                        y=df.loc[max_mem_idx, "Mem_Usage_Avg(%)"],
                        text="Peak",
                        showarrow=True,
                        arrowhead=1,
                    )
            except Exception:
                pass

        fig_mem.update_layout(
            title=f"Physical Memory Usage (System Capacity: {total_mem} GB)",
            yaxis=dict(title="Usage (%)", range=[0, 100]),
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_mem, width="stretch")
        st.divider()

    # 2. Inspector inspect speed graph
    if not insp_df.empty:
        fig_insp = make_subplots(specs=[[{"secondary_y": True}]])
        fig_insp.add_trace(
            go.Scatter(
                x=insp_df["Timestamp"],
                y=insp_df["Inspector_Total_Sec"],
                name="Total Inspect Time (sec)",
                mode="lines+markers",
                line=dict(color=COLOR_INSPECTOR_TOTAL, width=2),
                customdata=insp_df[["Inspector_Total_Frames"]],
                hovertemplate=(
                    "Timestamp=%{x}<br>Total=%{y:.2f} sec<br>Frames=%{customdata[0]}<extra></extra>"
                ),
            ),
            secondary_y=False,
        )
        fig_insp.add_trace(
            go.Scatter(
                x=insp_df["Timestamp"],
                y=insp_df["Inspector_Frame_Sec"],
                name="Frame Inspect Time (sec/frame)",
                mode="lines+markers",
                line=dict(color=COLOR_INSPECTOR_FRAME, width=2),
                hovertemplate="Timestamp=%{x}<br>Frame=%{y:.2f} sec/frame<extra></extra>",
            ),
            secondary_y=True,
        )
        fig_insp.update_layout(
            title="Inspector Inspect Speed Timeline",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        fig_insp.update_yaxes(title_text="Total Inspect Time (sec)", secondary_y=False)
        fig_insp.update_yaxes(title_text="Frame Inspect Time (sec/frame)", secondary_y=True)
        st.plotly_chart(fig_insp, width="stretch")
        st.divider()

    # 3. Inspector memory graph
    if not inspector_mem_df.empty:
        fig_inspector_mem = go.Figure()
        fig_inspector_mem.add_trace(
            go.Scatter(
                x=inspector_mem_df["Timestamp"],
                y=inspector_mem_df["Inspector_WorkingSet_GB"],
                name="Inspector Working Set (log, KB -> GB)",
                mode="lines+markers",
                line=dict(color=COLOR_INSPECTOR_MEM, width=2),
                hovertemplate=(
                    "Timestamp=%{x}<br>Working Set=%{y:.2f} GB"
                    "<br>Raw=%{customdata[0]:,.0f} KB<extra></extra>"
                ),
                customdata=inspector_mem_df[["Inspector_WorkingSet_KB"]],
            )
        )
        fig_inspector_mem.update_layout(
            title="Inspector Working Set Memory From AOI Log",
            yaxis=dict(title="Working Set (GB)"),
            hovermode="x unified",
        )
        st.plotly_chart(fig_inspector_mem, width="stretch")
        st.divider()

    # 4. External vs log memory comparison
    if has_system_data and not inspector_mem_df.empty:
        external_inspector_df = _build_external_inspector_df(df, extract_process_time_series)
        if not external_inspector_df.empty:
            fig_compare = go.Figure()
            fig_compare.add_trace(
                go.Scatter(
                    x=external_inspector_df["Timestamp"],
                    y=external_inspector_df["External_Inspector_GB"],
                    name="Inspector Process (system monitor, GB)",
                    mode="lines",
                    line=dict(color=COLOR_PROCESS, width=2),
                )
            )
            fig_compare.add_trace(
                go.Scatter(
                    x=inspector_mem_df["Timestamp"],
                    y=inspector_mem_df["Inspector_WorkingSet_GB"],
                    name="Inspector APP (log, KB -> GB)",
                    mode="lines+markers",
                    line=dict(color=COLOR_INSPECTOR_MEM, width=2),
                )
            )
            fig_compare.update_layout(
                title="External Inspector Memory vs Inspector Log Working Set",
                yaxis=dict(title="Memory (GB)"),
                hovermode="x unified",
            )
            st.plotly_chart(fig_compare, width="stretch")
            st.divider()

    # 5. Top Memory Processes + Inspector log memory
    top_mem_df = _merge_top_memory_processes(df, parse_process_column, inspector_mem_df)
    if not top_mem_df.empty:
        st.subheader("🏆 Top 5 Heavy Memory Processes + Inspector APP (log)")
        top_display_df = top_mem_df.head(5)
        fig_bar = px.bar(
            top_display_df,
            x="Process",
            y="Max_Value",
            title="Peak Memory Usage by Process / Inspector Log (MB)",
            labels={"Max_Value": "Peak Memory (MB)"},
            text_auto=".0f",
        )
        fig_bar.update_traces(marker_color=COLOR_PROCESS)
        st.plotly_chart(fig_bar, width="stretch")

        st.divider()

        st.subheader("📈 Process Memory Trends (Top 5 + Inspector APP)")
        selectable_names = top_display_df["Process"].tolist()
        selected_procs = []
        if selectable_names:
            st.write("Select processes to view their memory usage over time:")
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
                        title="Memory Usage Over Time (MB)",
                        labels={"Value": "Memory (MB)"},
                    )
                    fig_trend.update_layout(hovermode="x unified")
                    st.plotly_chart(fig_trend, width="stretch")
                else:
                    st.info("No time-series data found for selected processes.")
            else:
                st.info("No process memory trend data available.")

        with st.expander("See Top 10 Details"):
            st.dataframe(top_mem_df.head(10))
    elif has_system_data:
        st.warning("No process memory data available.")
        if "Top5_Memory_MB" in df.columns:
            with st.expander("💀 Debug: Raw Data Inspection"):
                st.write("First 10 rows of 'Top5_Memory_MB':")
                st.write(df["Top5_Memory_MB"].head(10))
                st.write("Column Type:", df["Top5_Memory_MB"].dtype)
    else:
        st.info("No memory process comparison data is available yet.")
