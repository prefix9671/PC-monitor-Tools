# dashboards/cpu.py
import plotly.graph_objects as go
import pandas as pd
from config import COLOR_CPU

def render_cpu_dashboard(st, df):
    st.subheader("CPU Performance & Thermal")
    st.caption("ℹ️ 현재 표시되는 값은 5초 단위 집계값(Avg/Peak)입니다.")
    
    if 'CPU_Avg(%)' not in df.columns:
        st.error(f"❌ CPU Data not found. Available columns: {list(df.columns)}")
        return

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Timestamp'], y=df['CPU_Avg(%)'], name='CPU Avg (%)', line=dict(color=COLOR_CPU, width=2)))
    
    if 'CPU_Peak(%)' in df.columns:
        fig.add_trace(go.Scatter(x=df['Timestamp'], y=df['CPU_Peak(%)'], name='CPU Peak (%)', line=dict(color='rgba(255, 0, 0, 0.3)', width=1, dash='dot')))
    
    if 'CPU_Temp(C)' in df.columns:
        # 온도는 N/A일 수 있으므로 숫자형 변환 시도
        df['CPU_Temp(C)'] = pd.to_numeric(df['CPU_Temp(C)'], errors='coerce')
        fig.add_trace(go.Scatter(x=df['Timestamp'], y=df['CPU_Temp(C)'], name='CPU Temp (°C)', yaxis='y2', line=dict(color='#FFD700', dash='dot'))) # 노랑/골드

    fig.update_layout(
        yaxis=dict(title="Usage (%)", range=[0, 100]),
        yaxis2=dict(title="Temperature (°C)", overlaying='y', side='right', range=[0, 120]),
        title="CPU Usage vs Temperature",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, width='stretch')
    
    # 통계 지표
    col1, col2 = st.columns(2)
    
    cpu_max = df['CPU_Peak(%)'].max() if 'CPU_Peak(%)' in df.columns else df['CPU_Avg(%)'].max()
    cpu_mean = df['CPU_Avg(%)'].mean()
    
    col1.metric("Max CPU Usage (5s Peak)", f"{cpu_max:.2f}%")
    col1.metric("Avg CPU Usage", f"{cpu_mean:.2f}%")
    
    if 'CPU_Temp(C)' in df.columns and df['CPU_Temp(C)'].notna().any():
        temp_max = df['CPU_Temp(C)'].max()
        col2.metric("Max CPU Temp", f"{temp_max:.1f}°C")
