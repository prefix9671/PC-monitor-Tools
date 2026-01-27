# dashboards/storage.py
import plotly.express as px
import streamlit as st

def render_storage_dashboard(st, df, parse_process_column):
    st.subheader("💾 Storage Performance Analysis")
    
    # 1. Disk Active Time (Load)
    active_cols = [c for c in df.columns if 'Active(%)' in c]
    if active_cols:
        fig_load = px.line(df, x='Timestamp', y=active_cols, title="Disk Active Time (Load %)")
        fig_load.update_layout(yaxis=dict(range=[0, 100]), hovermode="x unified")
        st.plotly_chart(fig_load, width='stretch')
    else:
        st.info("No Disk Active Time data available.")

    st.divider()

    # 2. I/O Throughput (Read/Write)
    # Find all MB/s columns excluding Top5 global stats
    io_cols = [c for c in df.columns if 'MB/s' in c and 'Top5' not in c]
    
    if io_cols:
        fig_io = px.line(df, x='Timestamp', y=io_cols, title="Drive Read/Write Throughput (MB/s)")
        fig_io.update_layout(hovermode="x unified")
        st.plotly_chart(fig_io, width='stretch')
    else:
        st.error("No Disk I/O data found in log.")
        
    st.divider()
    
    # Top 5 Disk IO Processes
    st.subheader("🔥 Top 5 Disk I/O Consumers")
    if 'Top5_Disk_IO_Global(MB/s)' in df.columns:
        top_disk_df = parse_process_column(df['Top5_Disk_IO_Global(MB/s)'])
        top5_disk = top_disk_df.head(5)
        
        if not top5_disk.empty:
            fig_disk_bar = px.bar(top5_disk, x='Max_Value', y='Process', orientation='h',
                                  title="Peak Disk I/O by Process (MB/s)",
                                  labels={'Max_Value': 'Peak I/O Speed (MB/s)'}, text_auto='.1f')
            # 막대 그래프 순서 반전 (Top이 위로) 및 색상 적용
            fig_disk_bar.update_layout(yaxis={'categoryorder':'total ascending'})
            fig_disk_bar.update_traces(marker_color='#333333') # Dark Grey/Black for Disk
            st.plotly_chart(fig_disk_bar, width='stretch')
        else:
            st.info("No significant disk activity detected.")
