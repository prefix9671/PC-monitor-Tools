# dashboards/cpu.py
import plotly.graph_objects as go
import pandas as pd
from config import COLOR_CPU

def render_cpu_dashboard(st, df):
    st.subheader("CPU Performance & Thermal")
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Timestamp'], y=df['CPU(%)'], name='CPU Usage (%)', line=dict(color=COLOR_CPU, width=2)))
    
    if 'CPU_Temp(C)' in df.columns:
        # 온도는 N/A일 수 있으므로 숫자형 변환 시도
        df['CPU_Temp(C)'] = pd.to_numeric(df['CPU_Temp(C)'], errors='coerce')
        fig.add_trace(go.Scatter(x=df['Timestamp'], y=df['CPU_Temp(C)'], name='CPU Temp (°C)', yaxis='y2', line=dict(color='#FFD700', dash='dot'))) # 노랑/골드

    fig.update_layout(
        yaxis=dict(title="Usage (%)", range=[0, 100]),
        yaxis2=dict(title="Temperature (°C)", overlaying='y', side='right', range=[0, 120]),
        title="CPU Usage (Red) vs Temperature (Yellow)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, width='stretch')
    
    # 통계 지표
    col1, col2 = st.columns(2)
    col1.metric("Max CPU Usage", f"{df['CPU(%)'].max()}%")
    col1.metric("Avg CPU Usage", f"{round(df['CPU(%)'].mean(), 2)}%")
    if 'CPU_Temp(C)' in df.columns:
        col2.metric("Max CPU Temp", f"{df['CPU_Temp(C)'].max()}°C")
