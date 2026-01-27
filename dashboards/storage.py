# dashboards/storage.py
import plotly.express as px
import streamlit as st

def render_storage_dashboard(st, df, parse_process_column):
    st.subheader("D: Drive I/O Analysis (NVMe/Data)")
    
    # D드라이브 읽기/쓰기 라인 차트
    # 컬럼명이 정확한지 확인 (공백 처리됨)
    d_cols = [c for c in df.columns if c.startswith('D_') and 'MB/s' in c]
    
    if d_cols:
        fig_io = px.line(df, x='Timestamp', y=d_cols, title="D: Drive Read/Write Throughput (MB/s)")
        st.plotly_chart(fig_io, width='stretch')
    else:
        st.error("D: drive columns not found in log.")
        
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
