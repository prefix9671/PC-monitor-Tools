from __future__ import annotations

import re
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from excel_exporter import generate_inspection_excel
from inspector_logs.core import (
    filter_inspection_records_by_time_range,
    format_inspection_preview_dataframe,
    select_inspection_records,
    summarize_inspection_records,
)


GRAPH_TYPE_OPTIONS = {
    "선 + 마커": "line",
    "영역": "area",
    "막대": "bar",
    "점": "scatter",
}

TIME_COLUMNS = ["Frame", "Total"]
MEMORY_COLUMNS = ["메모리 (시스템)", "메모리 (인스펙터)"]

COLOR_PRESET_ITEMS = [
    ("코랄 레드", "#FF6B6B"),
    ("체리 핑크", "#E63973"),
    ("로즈 퍼플", "#B565A7"),
    ("플럼 바이올렛", "#7B2CBF"),
    ("딥 바이올렛", "#5A189A"),
    ("인디고 블루", "#3F37C9"),
    ("코발트 블루", "#4361EE"),
    ("로열 블루", "#3A86FF"),
    ("스카이 블루", "#4CC9F0"),
    ("터쿼이즈", "#2EC4B6"),
    ("민트 그린", "#52B788"),
    ("에메랄드", "#2A9D8F"),
    ("라임 그린", "#8AC926"),
    ("올리브", "#6A994E"),
    ("선플라워", "#FFCA3A"),
    ("앰버", "#F4A261"),
    ("선셋 오렌지", "#FF9F1C"),
    ("탠저린", "#F77F00"),
    ("테라코타", "#E76F51"),
    ("브릭 레드", "#C44536"),
    ("모카 브라운", "#9C6644"),
    ("슬레이트 그레이", "#6C757D"),
    ("스틸 블루", "#577590"),
    ("딥 티얼", "#006D77"),
]

COLOR_PRESET_MAP = dict(COLOR_PRESET_ITEMS)
COLOR_PRESET_LABELS = [label for label, _ in COLOR_PRESET_ITEMS]

DEFAULT_METRIC_COLOR_LABELS = {
    "Frame": "플럼 바이올렛",
    "Total": "선셋 오렌지",
    "메모리 (시스템)": "코발트 블루",
    "메모리 (인스펙터)": "에메랄드",
}

DEFAULT_TABLE_COLOR_LABEL = "스틸 블루"

INSPECTION_EXPORT_RANGE_SCOPE_KEY = "inspection_export_range_scope"
INSPECTION_EXPORT_START_NO_KEY = "inspection_export_selected_start_no"
INSPECTION_EXPORT_END_NO_KEY = "inspection_export_selected_end_no"
INSPECTION_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _sanitize_file_token(value: str | None) -> str:
    token = (value or "").strip()
    if not token:
        return "UnknownModel"
    token = re.sub(r"[\\/:*?\"<>|]+", "_", token)
    token = re.sub(r"\s+", "_", token)
    return token[:60] or "UnknownModel"


def _hex_to_rgba(hex_color: str, opacity: float) -> str:
    normalized = (hex_color or "").strip().lstrip("#")
    if len(normalized) != 6:
        return f"rgba(0, 0, 0, {opacity:.2f})"

    red = int(normalized[0:2], 16)
    green = int(normalized[2:4], 16)
    blue = int(normalized[4:6], 16)
    return f"rgba({red}, {green}, {blue}, {opacity:.2f})"


def _time_scope_token(value) -> str:
    if value is None:
        return "none"
    try:
        return pd.Timestamp(value).isoformat()
    except Exception:
        return str(value)


def _make_inspection_export_scope(
    min_no: int,
    max_no: int,
    row_count: int,
    filter_start_time=None,
    filter_end_time=None,
) -> str:
    return "|".join(
        [
            str(int(min_no)),
            str(int(max_no)),
            str(int(row_count)),
            _time_scope_token(filter_start_time),
            _time_scope_token(filter_end_time),
        ]
    )


def _coerce_int(value, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(fallback)


def _clamp_no_range(start_no: int, end_no: int, min_no: int, max_no: int) -> tuple[int, int]:
    start_no = min(max(int(start_no), int(min_no)), int(max_no))
    end_no = min(max(int(end_no), start_no), int(max_no))
    return start_no, end_no


def _resolve_inspection_no_range_state(
    session_state,
    min_no: int,
    max_no: int,
    row_count: int,
    filter_start_time=None,
    filter_end_time=None,
) -> tuple[int, int]:
    scope = _make_inspection_export_scope(
        min_no=min_no,
        max_no=max_no,
        row_count=row_count,
        filter_start_time=filter_start_time,
        filter_end_time=filter_end_time,
    )

    if session_state.get(INSPECTION_EXPORT_RANGE_SCOPE_KEY) != scope:
        session_state[INSPECTION_EXPORT_RANGE_SCOPE_KEY] = scope
        session_state[INSPECTION_EXPORT_START_NO_KEY] = int(min_no)
        session_state[INSPECTION_EXPORT_END_NO_KEY] = int(max_no)
        return int(min_no), int(max_no)

    start_no = _coerce_int(session_state.get(INSPECTION_EXPORT_START_NO_KEY), min_no)
    end_no = _coerce_int(session_state.get(INSPECTION_EXPORT_END_NO_KEY), max_no)
    start_no, end_no = _clamp_no_range(start_no, end_no, min_no, max_no)
    session_state[INSPECTION_EXPORT_START_NO_KEY] = start_no
    session_state[INSPECTION_EXPORT_END_NO_KEY] = end_no
    return start_no, end_no


def _format_time_filter_caption(filter_start_time, filter_end_time) -> str:
    if filter_start_time is None or filter_end_time is None:
        return "현재 로드된 AOI/SPI 로그 전체 범위를 기준으로 표시합니다."

    start_label = pd.Timestamp(filter_start_time).strftime("%Y-%m-%d %H:%M:%S")
    end_label = pd.Timestamp(filter_end_time).strftime("%Y-%m-%d %H:%M:%S")
    return f"현재 시간 필터 기준: {start_label} -> {end_label}"


def _style_preview_table(preview_df: pd.DataFrame, accent_color: str, opacity: float):
    if preview_df.empty:
        return preview_df.style

    base_fill = _hex_to_rgba(accent_color, max(opacity * 0.45, 0.05))
    alt_fill = _hex_to_rgba(accent_color, max(opacity * 0.18, 0.02))
    no_fill = _hex_to_rgba(accent_color, min(opacity + 0.18, 0.95))
    header_fill = _hex_to_rgba(accent_color, min(opacity + 0.28, 1.0))

    def stripe_row(row):
        row_fill = base_fill if row.name % 2 == 0 else alt_fill
        styles = []
        for column_name in preview_df.columns:
            if column_name == "NO":
                styles.append(f"background-color: {no_fill}; font-weight: 700;")
            else:
                styles.append(f"background-color: {row_fill};")
        return styles

    return (
        preview_df.style.format(
            {
                "Frame": "{:.2f}",
                "Total": "{:.2f}",
                "메모리 (시스템)": "{:.3f}",
                "메모리 (인스펙터)": "{:.3f}",
            },
            na_rep="",
        )
        .apply(stripe_row, axis=1)
        .set_table_styles(
            [
                {"selector": "th", "props": [("background-color", header_fill), ("color", "#111111")]},
                {"selector": "td", "props": [("border-bottom", "1px solid rgba(255,255,255,0.08)")]},
            ]
        )
    )


def _build_preview_chart(
    preview_df: pd.DataFrame,
    chart_type: str,
    selected_metrics: list[str],
    metric_colors: dict[str, str],
    opacity: float,
):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    chart_key = GRAPH_TYPE_OPTIONS.get(chart_type, "line")

    def add_trace(metric_name: str, secondary_y: bool, color: str):
        if metric_name not in preview_df.columns:
            return

        trace_name = metric_name
        x_values = preview_df["NO"]
        y_values = preview_df[metric_name]

        if chart_key == "bar":
            fig.add_trace(
                go.Bar(
                    x=x_values,
                    y=y_values,
                    name=trace_name,
                    marker_color=_hex_to_rgba(color, opacity),
                    opacity=opacity,
                ),
                secondary_y=secondary_y,
            )
            return

        mode = "markers" if chart_key == "scatter" else "lines+markers"
        fill = "tozeroy" if chart_key == "area" else None
        fill_color = _hex_to_rgba(color, max(opacity * 0.65, 0.08)) if chart_key == "area" else None
        fig.add_trace(
            go.Scatter(
                x=x_values,
                y=y_values,
                name=trace_name,
                mode=mode,
                line=dict(color=color, width=3),
                marker=dict(color=color, size=9, opacity=max(opacity, 0.35)),
                opacity=max(opacity, 0.35),
                fill=fill,
                fillcolor=fill_color,
            ),
            secondary_y=secondary_y,
        )

    for metric_name in selected_metrics:
        if metric_name in TIME_COLUMNS:
            add_trace(metric_name, secondary_y=False, color=metric_colors.get(metric_name, "#3A86FF"))
        elif metric_name in MEMORY_COLUMNS:
            add_trace(metric_name, secondary_y=True, color=metric_colors.get(metric_name, "#2A9D8F"))

    fig.update_layout(
        title="검사 결과 미리보기 그래프",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        bargap=0.22,
    )
    fig.update_xaxes(title_text="NO")
    fig.update_yaxes(title_text="검사 시간 (sec)", secondary_y=False)
    fig.update_yaxes(title_text="메모리 (GB)", secondary_y=True)
    return fig


def _render_color_badges(st, metric_color_labels: dict[str, str], table_color_label: str):
    badge_parts = []
    combined = list(metric_color_labels.items()) + [("표 강조", table_color_label)]

    for metric_name, color_label in combined:
        color_hex = COLOR_PRESET_MAP[color_label]
        badge_parts.append(
            "<span style='display:inline-flex;align-items:center;margin:0 10px 8px 0;"
            "padding:6px 10px;border-radius:999px;background:rgba(255,255,255,0.06);'>"
            f"<span style='display:inline-block;width:12px;height:12px;border-radius:50%;"
            f"background:{color_hex};margin-right:8px;border:1px solid rgba(0,0,0,0.15);'></span>"
            f"{metric_name}: {color_label}</span>"
        )

    st.markdown("".join(badge_parts), unsafe_allow_html=True)


def _build_inspection_xlsx_download_payload(
    selected_records,
    selected_model: str | None,
    start_no: int,
    end_no: int,
    include_inspector_memory: bool,
    sample_records=None,
    sample_start_time=None,
    sample_end_time=None,
    end_time_user_specified=False,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    generated_at = generated_at or datetime.now()
    file_model_token = _sanitize_file_token(selected_model)
    file_name = (
        f"Inspection_Results_{file_model_token}_NO{start_no:04d}-{end_no:04d}_"
        f"{generated_at.strftime('%Y%m%d_%H%M%S')}.xlsx"
    )

    return {
        "data": generate_inspection_excel(
            selected_records,
            include_inspector_memory=include_inspector_memory,
            sample_records=sample_records,
            sample_start_time=sample_start_time,
            sample_end_time=sample_end_time,
            end_time_user_specified=end_time_user_specified,
        ),
        "file_name": file_name,
        "mime": INSPECTION_XLSX_MIME,
    }


def _build_inspection_xlsx_download_key(
    start_no: int,
    end_no: int,
    selected_row_count: int,
    filtered_row_count: int,
    include_inspector_memory: bool,
) -> str:
    memory_token = "with-inspector-memory" if include_inspector_memory else "without-inspector-memory"
    return (
        "inspection-xlsx-download-"
        f"{int(start_no)}-{int(end_no)}-"
        f"{int(selected_row_count)}-{int(filtered_row_count)}-"
        f"{memory_token}"
    )


def render_inspection_export_panel(
    st,
    inspection_records,
    filter_start_time=None,
    filter_end_time=None,
    filter_end_user_specified=False,
):
    st.subheader("검사 결과 XLSX 내보내기")

    filtered_records = filter_inspection_records_by_time_range(
        inspection_records,
        start_time=filter_start_time,
        end_time=filter_end_time,
    )

    summary = summarize_inspection_records(filtered_records)
    if summary["rows"] == 0 or summary["no_range"] is None:
        if filter_start_time is not None or filter_end_time is not None:
            st.info("현재 시간 필터 범위에는 번호화할 검사 결과가 없습니다.")
        else:
            st.info("현재 불러온 AOI / SPI / 인스펙터 로그에는 번호화할 검사 결과가 없습니다.")
        return

    min_no, max_no = summary["no_range"]
    start_default, end_default = _resolve_inspection_no_range_state(
        st.session_state,
        min_no=min_no,
        max_no=max_no,
        row_count=summary["rows"],
        filter_start_time=filter_start_time,
        filter_end_time=filter_end_time,
    )

    selected_model = summary["primary_model_name"] or "미확인"
    source_label = ", ".join(summary.get("source_types") or []) or "미확인"
    system_match_count = summary["system_memory_matches"]

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric("모델/장비", selected_model)
    metric_col2.metric("총 검사 수", f"{summary['rows']}건")
    metric_col3.metric("시스템 메모리 매칭", f"{system_match_count}건")

    st.caption(f"감지된 로그 형식: {source_label}")
    if len(summary["model_names"]) > 1:
        st.caption(f"감지된 모델명: {', '.join(summary['model_names'])}")

    st.caption(_format_time_filter_caption(filter_start_time, filter_end_time))
    st.caption("NO는 원본 AOI/SPI 로그 기준 번호를 유지하며, 현재 시간 필터에 포함된 검사 결과만 표시합니다.")

    range_col1, range_col2 = st.columns(2)
    with range_col1:
        start_no = int(
            range_col1.number_input(
                "시작 NO",
                min_value=min_no,
                max_value=max_no,
                value=start_default,
                step=1,
            )
        )
    if int(st.session_state.get(INSPECTION_EXPORT_END_NO_KEY, max_no)) < start_no:
        st.session_state[INSPECTION_EXPORT_END_NO_KEY] = start_no
    end_default = min(max(int(st.session_state.get(INSPECTION_EXPORT_END_NO_KEY, end_default)), start_no), max_no)
    with range_col2:
        end_no = int(
            range_col2.number_input(
                "종료 NO",
                min_value=start_no,
                max_value=max_no,
                value=end_default,
                step=1,
            )
        )

    st.session_state[INSPECTION_EXPORT_START_NO_KEY] = start_no
    st.session_state[INSPECTION_EXPORT_END_NO_KEY] = end_no

    selected_records = select_inspection_records(filtered_records, start_no=start_no, end_no=end_no)
    preview_df = format_inspection_preview_dataframe(selected_records)

    st.caption(f"선택 범위: NO {start_no} -> {end_no} / {len(preview_df)}건")

    if len(preview_df) != len(selected_records):
        st.warning("미리보기 생성 중 일부 행이 제외되었습니다.")

    if selected_records["System_Memory_Used_GB"].isna().any():
        st.warning("일부 검사 결과는 직전 시스템 메모리 샘플을 찾지 못해 `메모리 (시스템)` 값이 비어 있습니다.")
    if selected_records["Inspector_WorkingSet_GB"].isna().any():
        st.warning("일부 검사 결과는 AOI/SPI 로그 Working Set 정보를 찾지 못해 `메모리 (인스펙터)` 값이 비어 있습니다.")

    st.markdown("#### 표현 설정")
    style_col1, style_col2, style_col3 = st.columns(3)
    with style_col1:
        chart_type = st.selectbox("그래프 형식", list(GRAPH_TYPE_OPTIONS.keys()), index=0)
        chart_opacity = st.slider("그래프 투명도", min_value=0.2, max_value=1.0, value=0.85, step=0.05)
    with style_col2:
        table_color_label = st.selectbox(
            "표 강조 색상",
            COLOR_PRESET_LABELS,
            index=COLOR_PRESET_LABELS.index(DEFAULT_TABLE_COLOR_LABEL),
        )
    with style_col3:
        table_opacity = st.slider("표 강조 투명도", min_value=0.05, max_value=0.7, value=0.28, step=0.05)

    metric_options = TIME_COLUMNS + MEMORY_COLUMNS
    default_metrics = [metric for metric in metric_options if metric in preview_df.columns]
    selected_metrics = st.multiselect(
        "미리보기 그래프 항목",
        metric_options,
        default=default_metrics,
        help="Frame, Total, 시스템 메모리 지표를 함께 비교할 수 있습니다.",
    )

    st.caption("항목별 색상은 이름으로 고르고, 화면 아래 배지에서 현재 선택을 바로 확인할 수 있습니다.")
    color_columns = st.columns(len(metric_options))
    metric_color_labels: dict[str, str] = {}
    for index, metric_name in enumerate(metric_options):
        default_label = DEFAULT_METRIC_COLOR_LABELS[metric_name]
        metric_color_labels[metric_name] = color_columns[index].selectbox(
            f"{metric_name} 색상",
            COLOR_PRESET_LABELS,
            index=COLOR_PRESET_LABELS.index(default_label),
            key=f"inspection_metric_color_{metric_name}",
        )

    _render_color_badges(st, metric_color_labels=metric_color_labels, table_color_label=table_color_label)
    metric_colors = {metric_name: COLOR_PRESET_MAP[color_label] for metric_name, color_label in metric_color_labels.items()}
    table_color = COLOR_PRESET_MAP[table_color_label]

    if selected_metrics and not preview_df.empty:
        chart_figure = _build_preview_chart(
            preview_df=preview_df,
            chart_type=chart_type,
            selected_metrics=selected_metrics,
            metric_colors=metric_colors,
            opacity=chart_opacity,
        )
        st.plotly_chart(chart_figure, width="stretch")
    elif preview_df.empty:
        st.info("선택한 NO 범위에 표시할 검사 결과가 없습니다.")
    else:
        st.info("미리보기 그래프에 표시할 항목을 하나 이상 선택해 주세요.")

    styled_preview = _style_preview_table(preview_df, accent_color=table_color, opacity=table_opacity)
    st.dataframe(styled_preview, hide_index=True, width="stretch")

    include_inspector_memory_in_xlsx = st.checkbox(
        "XLSX에 인스펙터 메모리 포함",
        value=False,
        help="체크하면 `메모리 (시스템)` 오른쪽에 `메모리 (인스펙터)` 컬럼을 추가합니다.",
    )

    xlsx_payload = _build_inspection_xlsx_download_payload(
        selected_records=selected_records,
        selected_model=selected_model,
        start_no=start_no,
        end_no=end_no,
        include_inspector_memory=include_inspector_memory_in_xlsx,
        sample_records=filtered_records,
        sample_start_time=filter_start_time,
        sample_end_time=filter_end_time,
        end_time_user_specified=filter_end_user_specified,
    )

    st.download_button(
        label="검사 결과 XLSX 다운로드",
        data=xlsx_payload["data"],
        file_name=xlsx_payload["file_name"],
        mime=xlsx_payload["mime"],
        key=_build_inspection_xlsx_download_key(
            start_no=start_no,
            end_no=end_no,
            selected_row_count=len(selected_records),
            filtered_row_count=len(filtered_records),
            include_inspector_memory=include_inspector_memory_in_xlsx,
        ),
        on_click="ignore",
    )
