import math
from typing import Any, Optional

import pandas as pd


def _numeric_series(df: pd.DataFrame, column_name: str) -> pd.Series:
    if df is None or df.empty or column_name not in df.columns:
        return pd.Series(dtype="float64")
    return pd.to_numeric(df[column_name], errors="coerce").dropna()


def _safe_mean(series: pd.Series) -> Optional[float]:
    if series.empty:
        return None
    return float(series.mean())


def _safe_max(series: pd.Series) -> Optional[float]:
    if series.empty:
        return None
    return float(series.max())


def _format_numeric(value: Optional[float], suffix: str, decimals: int = 2) -> str:
    if value is None or not math.isfinite(value):
        return "N/A"
    return f"{value:.{decimals}f}{suffix}"


def _format_filter_caption(filter_start_time: Any = None, filter_end_time: Any = None) -> str:
    if filter_start_time is None or filter_end_time is None:
        return "현재 표시 중인 시스템 로그 범위 기준입니다."

    start_label = pd.Timestamp(filter_start_time).strftime("%Y-%m-%d %H:%M:%S")
    end_label = pd.Timestamp(filter_end_time).strftime("%Y-%m-%d %H:%M:%S")
    return f"현재 시간 필터 기준: {start_label} -> {end_label}"


def build_system_summary_metrics(df: pd.DataFrame) -> dict[str, Optional[float] | int | str]:
    cpu_avg_series = _numeric_series(df, "CPU_Avg(%)")
    cpu_peak_series = _numeric_series(df, "CPU_Peak(%)")
    if cpu_peak_series.empty:
        cpu_peak_series = cpu_avg_series

    cpu_temp_series = _numeric_series(df, "CPU_Temp(C)")
    ram_usage_series = _numeric_series(df, "Mem_Usage_Avg(%)")

    return {
        "sample_count": 0 if df is None else int(len(df)),
        "cpu_usage_avg_pct": _safe_mean(cpu_avg_series),
        "cpu_usage_peak_pct": _safe_max(cpu_peak_series),
        "cpu_usage_peak_source": "CPU_Peak(%)" if "CPU_Peak(%)" in getattr(df, "columns", []) else "CPU_Avg(%)",
        "cpu_temp_avg_c": _safe_mean(cpu_temp_series),
        "cpu_temp_peak_c": _safe_max(cpu_temp_series),
        "ram_usage_avg_pct": _safe_mean(ram_usage_series),
        "ram_usage_peak_pct": _safe_max(ram_usage_series),
    }


def render_system_summary_cards(st, df: pd.DataFrame, filter_start_time: Any = None, filter_end_time: Any = None) -> None:
    summary = build_system_summary_metrics(df)

    st.markdown("#### 시스템 성능 요약")
    st.caption(_format_filter_caption(filter_start_time, filter_end_time))

    cpu_col, temp_col, ram_col = st.columns(3)
    cpu_col.metric(
        label="CPU 사용량 평균",
        value=_format_numeric(summary["cpu_usage_avg_pct"], "%"),
        delta=f"최고 {_format_numeric(summary['cpu_usage_peak_pct'], '%')}",
    )
    temp_col.metric(
        label="CPU 온도 평균",
        value=_format_numeric(summary["cpu_temp_avg_c"], "°C", decimals=1),
        delta=f"최고 {_format_numeric(summary['cpu_temp_peak_c'], '°C', decimals=1)}",
    )
    ram_col.metric(
        label="RAM 사용량 평균",
        value=_format_numeric(summary["ram_usage_avg_pct"], "%"),
        delta=f"최대 {_format_numeric(summary['ram_usage_peak_pct'], '%')}",
    )

    if summary["cpu_temp_avg_c"] is None:
        st.caption("CPU 온도 컬럼이 없거나 값이 비어 있으면 온도 요약은 N/A로 표시됩니다.")
