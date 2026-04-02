import pandas as pd
import plotly.graph_objects as go

from config import COLOR_CPU, COLOR_CPU_TEMP


def render_cpu_dashboard(st, df):
    st.subheader("CPU 성능 및 온도")
    st.caption("현재 표시되는 값은 5초 단위 집계값이며, CPU 온도는 5초 동안 수집된 최고값입니다.")

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

    cpu_temp_series = None
    has_cpu_temp = False
    if "CPU_Temp(C)" in df.columns:
        cpu_temp_series = pd.to_numeric(df["CPU_Temp(C)"], errors="coerce")
        has_cpu_temp = cpu_temp_series.notna().any()
        if has_cpu_temp:
            fig.add_trace(
                go.Scatter(
                    x=df["Timestamp"],
                    y=cpu_temp_series,
                    name="CPU 온도 (°C)",
                    yaxis="y2",
                    line=dict(color=COLOR_CPU_TEMP, dash="dot"),
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

    if has_cpu_temp:
        temp_max = cpu_temp_series.max()
        temp_mean = cpu_temp_series.mean()
        col2.metric("최대 CPU 온도 (5초 최고값)", f"{temp_max:.1f}°C")
        col2.metric("평균 CPU 온도", f"{temp_mean:.1f}°C")

        temp_fig = go.Figure()
        temp_fig.add_trace(
            go.Scatter(
                x=df["Timestamp"],
                y=cpu_temp_series,
                name="CPU 온도 (°C)",
                line=dict(color=COLOR_CPU_TEMP, width=2),
                fill="tozeroy",
                fillcolor="rgba(255, 215, 0, 0.18)",
            )
        )
        temp_fig.update_layout(
            title="CPU 온도 추이",
            yaxis=dict(title="온도 (°C)", range=[0, 120]),
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(temp_fig, width="stretch")
    else:
        col2.info("현재 로그에는 CPU 온도 센서 데이터가 없습니다.")
