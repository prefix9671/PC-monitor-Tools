# dashboards/custom.py
import plotly.express as px
import streamlit as st

def render_custom_dashboard(st, df):
    st.subheader("🛠️ Custom Visualization")
    
    # 제외할 컬럼 (문자열 등)
    exclude_cols = ['Timestamp', 'IP_Address', 'Top5_Memory_MB', 'Top5_Disk_IO_Global(MB/s)']
    available_cols = [c for c in df.columns if c not in exclude_cols]
    
    # 체크박스/멀티셀렉트로 선택
    selected_cols = st.multiselect("Select Metrics to Plot (Y-Axis)", available_cols, default=['CPU(%)', 'Usage(%)'])
    
    if selected_cols:
        fig_custom = px.line(df, x='Timestamp', y=selected_cols, title="Custom Time Series Analysis")
        fig_custom.update_layout(hovermode="x unified")
        st.plotly_chart(fig_custom, width='stretch')
    else:
        st.info("Please select at least one metric.")
