import plotly.express as px
import streamlit as st
import pandas as pd
from excel_exporter import generate_excel

def render_custom_dashboard(st, df, parse_process_column):
    st.subheader("🛠️ Custom Visualization")
    
    # 1. 시계열 그래프 섹션
    st.markdown("### 📈 Time Series Multi-Select")
    # 제외할 컬럼 (문자열 등)
    exclude_cols = ['Timestamp', 'IP_Address', 'Top5_Memory_MB', 'Top5_Disk_IO_Global(MB/s)']
    available_cols = [c for c in df.columns if c not in exclude_cols]
    
    # 체크박스/멀티셀렉트로 선택
    selected_cols = st.multiselect("Select Metrics to Plot (Y-Axis)", available_cols, default=['CPU(%)', 'Usage(%)'])
    
    if selected_cols:
        fig_custom = px.line(df, x='Timestamp', y=selected_cols, title="Custom Time Series Analysis")
        fig_custom.update_layout(hovermode="x unified")
        st.plotly_chart(fig_custom, width='stretch')
        
        # 엑셀 내보내기 서브 섹션
        st.markdown("---")
        st.markdown("### 📥 Excel Export Settings")
        
        exp_col1, exp_col2 = st.columns(2)
        with exp_col1:
            export_start = st.selectbox(
                "Export Start Time (Refinement)", 
                options=df['Timestamp'],
                index=0,
                format_func=lambda x: x.strftime('%H:%M:%S')
            )
        
        # 선택한 시작 시간 이후의 데이터만 필터링
        export_df = df[df['Timestamp'] >= export_start]
        
        with exp_col2:
            st.write(" ") # 수직 정렬용
            st.write(" ")
            excel_data = generate_excel(export_df, selected_cols)
            st.download_button(
                label="📁 Download as Excel (.xlsx)",
                data=excel_data,
                file_name=f"resource_export_{export_start.strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        st.info(f"💡 {len(export_df)} rows will be exported starting from {export_start}.")
    else:
        st.info("Please select at least one metric.")

    st.divider()

    # 2. TOP 5 프로세스 분석 섹션
    st.markdown("### 🏆 Top Resource Consuming Processes")
    
    col1, col2 = st.columns(2)

    # (1) TOP 5 Memory Processes
    with col1:
        st.subheader("🧠 Top Memory (MB)")
        if 'Top5_Memory_MB' in df.columns:
            top_mem_df = parse_process_column(df['Top5_Memory_MB']).head(5)
            if not top_mem_df.empty:
                fig_mem_bar = px.bar(top_mem_df, x='Max_Value', y='Process', orientation='h',
                                     title="Peak Memory Usage",
                                     labels={'Max_Value': 'Memory (MB)'}, text_auto='.0f')
                fig_mem_bar.update_layout(yaxis={'categoryorder':'total ascending'})
                fig_mem_bar.update_traces(marker_color='#1f77b4') # Blue
                st.plotly_chart(fig_mem_bar, use_container_width=True)
            else:
                st.info("No memory process data.")
        else:
            st.warning("Memory process column not found.")

    # (2) TOP 5 Disk IO Processes
    with col2:
        st.subheader("💾 Top Disk I/O (MB/s)")
        if 'Top5_Disk_IO_Global(MB/s)' in df.columns:
            top_disk_df = parse_process_column(df['Top5_Disk_IO_Global(MB/s)']).head(5)
            if not top_disk_df.empty:
                fig_disk_bar = px.bar(top_disk_df, x='Max_Value', y='Process', orientation='h',
                                      title="Peak Disk I/O",
                                      labels={'Max_Value': 'I/O Speed (MB/s)'}, text_auto='.1f')
                fig_disk_bar.update_layout(yaxis={'categoryorder':'total ascending'})
                fig_disk_bar.update_traces(marker_color='#333333') # Dark Grey
                st.plotly_chart(fig_disk_bar, use_container_width=True)
            else:
                st.info("No disk I/O process data.")
        else:
            st.warning("Disk I/O process column not found.")
