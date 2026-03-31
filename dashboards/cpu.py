import pandas as pd
import plotly.graph_objects as go

from config import COLOR_CPU


def render_cpu_dashboard(st, df):
    st.subheader("CPU 성능 및 온도")
    st.caption("현재 표시되는 값은 5초 단위 집계값(평균/피크)입니다.")

    if "CPU_Avg(%)" not in df.columns:
        st.error(f"CPU 데이터가 없습니다. 현재 컬럼: {list(df.columns)}")
        return

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["Timestamp"],
            y=df["CPU_Avg(%)"],
            name="CPU 평균 사용률 (%)",
            line=dict(color=COLOR_CPU, width=2),
        )
    )

    if "CPU_Peak(%)" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["Timestamp"],
                y=df["CPU_Peak(%)"],
                name="CPU 피크 사용률 (%)",
                line=dict(color="rgba(255, 0, 0, 0.3)", width=1, dash="dot"),
            )
        )

    if "CPU_Temp(C)" in df.columns:
        df["CPU_Temp(C)"] = pd.to_numeric(df["CPU_Temp(C)"], errors="coerce")
        fig.add_trace(
            go.Scatter(
                x=df["Timestamp"],
                y=df["CPU_Temp(C)"],
                name="CPU 온도 (°C)",
                yaxis="y2",
                line=dict(color="#FFD700", dash="dot"),
            )
        )

    fig.update_layout(
        yaxis=dict(title="사용률 (%)", range=[0, 100]),
        yaxis2=dict(title="온도 (°C)", overlaying="y", side="right", range=[0, 120]),
        title="CPU 사용률과 온도",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, width="stretch")

    col1, col2 = st.columns(2)

    cpu_max = df["CPU_Peak(%)"].max() if "CPU_Peak(%)" in df.columns else df["CPU_Avg(%)"].max()
    cpu_mean = df["CPU_Avg(%)"].mean()

    col1.metric("최대 CPU 사용률 (5초 피크)", f"{cpu_max:.2f}%")
    col1.metric("평균 CPU 사용률", f"{cpu_mean:.2f}%")

    if "CPU_Temp(C)" in df.columns and df["CPU_Temp(C)"].notna().any():
        temp_max = df["CPU_Temp(C)"].max()
        col2.metric("최대 CPU 온도", f"{temp_max:.1f}°C")
