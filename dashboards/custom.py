import pandas as pd
import plotly.express as px

from excel_exporter import generate_excel


def render_custom_dashboard(st, df, parse_process_column):
    st.subheader("사용자 정의 시각화")
    st.caption("사용자 정의 차트의 기본 데이터는 5초 단위 집계값(평균/피크) 기준입니다.")

    st.markdown("### 시계열 지표 선택")
    exclude_cols = [
        "Timestamp",
        "IP_Address",
        "Top5_Memory_MB",
        "Top5_Disk_IO_Global(MB/s)",
        "Top5_CPU(%)",
        "Top5_Disk_Read_MBs",
        "Top5_Disk_Write_MBs",
    ]
    available_cols = [c for c in df.columns if c not in exclude_cols]

    default_cols = [c for c in ["CPU_Avg(%)", "Mem_Usage_Avg(%)"] if c in available_cols]
    selected_cols = st.multiselect("차트에 표시할 지표 선택 (Y축)", available_cols, default=default_cols)

    if selected_cols:
        fig_custom = px.line(df, x="Timestamp", y=selected_cols, title="사용자 정의 시계열 분석")
        fig_custom.update_layout(hovermode="x unified")
        st.plotly_chart(fig_custom, width="stretch")

        st.markdown("---")
        st.markdown("### 엑셀 내보내기 설정")

        exp_col1, exp_col2 = st.columns(2)
        with exp_col1:
            export_start = st.selectbox(
                "내보내기 시작 시각",
                options=df["Timestamp"],
                index=0,
                format_func=lambda x: x.strftime("%H:%M:%S"),
            )

        export_df = df[df["Timestamp"] >= export_start]

        with exp_col2:
            st.write(" ")
            st.write(" ")
            excel_data = generate_excel(export_df, selected_cols)
            st.download_button(
                label="엑셀(.xlsx) 다운로드",
                data=excel_data,
                file_name=f"resource_export_{export_start.strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        st.info(f"{len(export_df)}개 행이 {export_start}부터 내보내집니다.")
    else:
        st.info("지표를 하나 이상 선택해 주세요.")

    st.divider()

    st.markdown("### 상위 자원 사용 프로세스")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("상위 메모리 사용량 (MB)")
        if "Top5_Memory_MB" in df.columns:
            top_mem_df = parse_process_column(df["Top5_Memory_MB"]).head(5)
            if not top_mem_df.empty:
                fig_mem_bar = px.bar(
                    top_mem_df,
                    x="Max_Value",
                    y="Process",
                    orientation="h",
                    title="최대 메모리 사용량",
                    labels={"Max_Value": "메모리 (MB)"},
                    text_auto=".0f",
                )
                fig_mem_bar.update_layout(yaxis={"categoryorder": "total ascending"})
                fig_mem_bar.update_traces(marker_color="#1f77b4")
                st.plotly_chart(fig_mem_bar, width="stretch")
            else:
                st.info("메모리 프로세스 데이터가 없습니다.")
        else:
            st.warning("메모리 프로세스 컬럼이 없습니다.")

    with col2:
        st.subheader("상위 디스크 I/O (MB/s)")
        if "Top5_Disk_IO_Global(MB/s)" in df.columns:
            top_disk_df = parse_process_column(df["Top5_Disk_IO_Global(MB/s)"]).head(5)
            if not top_disk_df.empty:
                fig_disk_bar = px.bar(
                    top_disk_df,
                    x="Max_Value",
                    y="Process",
                    orientation="h",
                    title="최대 디스크 I/O",
                    labels={"Max_Value": "I/O 속도 (MB/s)"},
                    text_auto=".1f",
                )
                fig_disk_bar.update_layout(yaxis={"categoryorder": "total ascending"})
                fig_disk_bar.update_traces(marker_color="#333333")
                st.plotly_chart(fig_disk_bar, use_container_width=True)
            else:
                st.info("디스크 I/O 프로세스 데이터가 없습니다.")
        else:
            st.warning("디스크 I/O 프로세스 컬럼이 없습니다.")
