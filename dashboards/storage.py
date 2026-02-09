import re

import pandas as pd
import plotly.express as px

DRIVE_COL_PATTERN = re.compile(r"_[A-Z]:")
DEFAULT_MAX_PLOT_POINTS = 30000


def _downsample_for_plot(df, value_cols, max_points=6000):
    """
    Downsample while preserving local shape.
    Per bucket, keep first/last and local min/max for each metric column.
    """
    if df.empty or len(df) <= max_points:
        return df

    n_rows = len(df)
    points_per_bucket = max(2, 2 + 2 * len(value_cols))
    n_buckets = max(1, max_points // points_per_bucket)
    bucket_size = max(1, (n_rows + n_buckets - 1) // n_buckets)

    keep_idx = {0, n_rows - 1}
    numeric_view = df[value_cols].apply(pd.to_numeric, errors='coerce')

    for start in range(0, n_rows, bucket_size):
        end = min(start + bucket_size, n_rows)
        window = numeric_view.iloc[start:end]
        if window.empty:
            continue

        # Keep bucket boundaries to preserve continuity.
        keep_idx.add(start)
        keep_idx.add(end - 1)

        # Keep local extrema per column to preserve spikes/valleys.
        for col in value_cols:
            if col not in window.columns:
                continue

            series = window[col].dropna()
            if series.empty:
                continue

            keep_idx.add(int(series.idxmax()))
            keep_idx.add(int(series.idxmin()))

    return df.iloc[sorted(keep_idx)].reset_index(drop=True)


def _collect_drive_columns(columns, prefixes):
    return [
        col for col in columns
        if any(col.startswith(prefix) for prefix in prefixes) and DRIVE_COL_PATTERN.search(col)
    ]


def render_storage_dashboard(st, df, parse_process_column):
    st.subheader("Storage Performance Analysis")

    quality_options = {
        "Fast": 12000,
        "Balanced": DEFAULT_MAX_PLOT_POINTS,
        "Detailed": 60000,
        "Original (slow)": None,
    }
    quality = st.selectbox("Chart Quality", list(quality_options.keys()), index=1)
    max_points = quality_options[quality]

    # Use a dedicated plotting copy to avoid mutating original app dataframe.
    plot_df = df.sort_values('Timestamp').reset_index(drop=True).copy()
    if max_points is None and len(plot_df) > 100000:
        st.warning("Original mode can be slow on large datasets.")

    # 1) Disk Active Time
    active_cols = _collect_drive_columns(plot_df.columns, ['DiskTime_'])
    if active_cols:
        for col in active_cols:
            plot_df[col] = pd.to_numeric(plot_df[col], errors='coerce')

        active_plot_df = (
            _downsample_for_plot(plot_df, active_cols, max_points=max_points)
            if max_points is not None
            else plot_df
        )
        fig_load = px.line(
            active_plot_df,
            x='Timestamp',
            y=active_cols,
            title='Disk Active Time (Individual Drives %)',
            render_mode='webgl'
        )
        fig_load.update_layout(yaxis=dict(range=[0, 100]), hovermode='x unified')
        st.plotly_chart(fig_load, width='stretch')

        if len(active_plot_df) < len(plot_df):
            st.caption(f"Rendering optimized: {len(plot_df):,} -> {len(active_plot_df):,} points")
    else:
        st.info('No Disk Drive (C:, D:, etc.) Active Time data available.')

    st.divider()

    # 2) Per-drive I/O throughput
    io_raw_cols = _collect_drive_columns(plot_df.columns, ['DiskRead_', 'DiskWrite_'])
    if io_raw_cols:
        io_display_cols = []
        for col in io_raw_cols:
            new_col = col.replace('(B/s)', '(MB/s)')
            plot_df[new_col] = pd.to_numeric(plot_df[col], errors='coerce') / (1024 * 1024)
            io_display_cols.append(new_col)

        io_plot_df = (
            _downsample_for_plot(plot_df, io_display_cols, max_points=max_points)
            if max_points is not None
            else plot_df
        )
        fig_io = px.line(
            io_plot_df,
            x='Timestamp',
            y=io_display_cols,
            title='Per-Drive Disk I/O Throughput (MB/s)',
            render_mode='webgl'
        )
        fig_io.update_layout(hovermode='x unified')
        st.plotly_chart(fig_io, width='stretch')
        if len(io_plot_df) < len(plot_df):
            st.caption(f"I/O rendering optimized: {len(plot_df):,} -> {len(io_plot_df):,} points")
    else:
        # Fallback to total-only metrics when per-drive metrics are not present.
        io_total_cols = [
            col for col in plot_df.columns
            if ('DiskRead' in col or 'DiskWrite' in col) and '_Total' in col
        ]
        if io_total_cols:
            io_display_total = []
            for col in io_total_cols:
                new_col = (
                    col.replace('(B/s)', '(MB/s)')
                    .replace('DiskRead', 'TotalRead')
                    .replace('DiskWrite', 'TotalWrite')
                )
                plot_df[new_col] = pd.to_numeric(plot_df[col], errors='coerce') / (1024 * 1024)
                io_display_total.append(new_col)

            io_total_plot_df = (
                _downsample_for_plot(plot_df, io_display_total, max_points=max_points)
                if max_points is not None
                else plot_df
            )
            fig_total_io = px.line(
                io_total_plot_df,
                x='Timestamp',
                y=io_display_total,
                title='Total System Disk I/O (MB/s)',
                render_mode='webgl'
            )
            fig_total_io.update_layout(hovermode='x unified')
            st.plotly_chart(fig_total_io, width='stretch')
            if len(io_total_plot_df) < len(plot_df):
                st.caption(f"I/O rendering optimized: {len(plot_df):,} -> {len(io_total_plot_df):,} points")
        else:
            st.error('No Disk I/O data (Read/Write) found in log.')

    st.divider()

    # 3) Top 5 process I/O consumers
    st.subheader('Top 5 Disk I/O Consumers')
    if 'Top5_Disk_IO_Global(MB/s)' in df.columns:
        top_disk_df = parse_process_column(df['Top5_Disk_IO_Global(MB/s)']).head(5)
        if not top_disk_df.empty:
            fig_disk_bar = px.bar(
                top_disk_df,
                x='Max_Value',
                y='Process',
                orientation='h',
                title='Peak Disk I/O by Process (MB/s)',
                labels={'Max_Value': 'Peak I/O Speed (MB/s)'},
                text_auto='.1f'
            )
            fig_disk_bar.update_layout(yaxis={'categoryorder': 'total ascending'})
            fig_disk_bar.update_traces(marker_color='#333333')
            st.plotly_chart(fig_disk_bar, width='stretch')
        else:
            st.info('No significant disk activity detected.')
