import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dashboards.memory import _summarize_swap_usage, render_memory_dashboard
from parsers import extract_process_time_series, parse_process_column


class FakeColumn:
    def __init__(self):
        self.metrics = []

    def metric(self, label, value, delta=None):
        self.metrics.append((label, value, delta))


class FakeStreamlit:
    def __init__(self):
        self.subheaders = []
        self.captions = []
        self.info_messages = []
        self.warning_messages = []
        self.errors = []
        self.plotly_figures = []
        self.columns_created = []

    def subheader(self, text):
        self.subheaders.append(text)

    def caption(self, text):
        self.captions.append(text)

    def info(self, text):
        self.info_messages.append(text)

    def warning(self, text):
        self.warning_messages.append(text)

    def error(self, text):
        self.errors.append(text)

    def plotly_chart(self, fig, width="stretch"):
        self.plotly_figures.append(fig)

    def columns(self, count):
        cols = [FakeColumn() for _ in range(count)]
        self.columns_created.append(cols)
        return cols

    def divider(self):
        return None


class TestSwapMonitoring(unittest.TestCase):
    def test_summarize_swap_usage_reports_no_swap_when_usage_is_zero(self):
        df = pd.DataFrame(
            {
                "Swap_Used(GB)": [0.0, 0.0],
                "Swap_Total(GB)": [8.0, 8.0],
                "Swap_Usage(%)": [0.0, 0.0],
            }
        )

        summary = _summarize_swap_usage(df)

        self.assertTrue(summary["available"])
        self.assertEqual("스왑 없음", summary["status_label"])
        self.assertIn("현재 스왑된 메모리가 없습니다.", summary["message"])

    def test_summarize_swap_usage_reports_active_swap_when_usage_is_positive(self):
        df = pd.DataFrame(
            {
                "Swap_Used(GB)": [0.0, 0.5],
                "Swap_Total(GB)": [8.0, 8.0],
                "Swap_Usage(%)": [0.0, 6.25],
            }
        )

        summary = _summarize_swap_usage(df)

        self.assertTrue(summary["available"])
        self.assertEqual("스왑 사용 중", summary["status_label"])
        self.assertIn("0.50 GB", summary["message"])
        self.assertAlmostEqual(6.25, summary["latest_usage_pct"], places=2)

    def test_render_memory_dashboard_shows_no_swap_message(self):
        st = FakeStreamlit()
        df = pd.DataFrame(
            {
                "Timestamp": pd.to_datetime(["2026-04-10 09:00:00", "2026-04-10 09:00:05"]),
                "Mem_Used(GB)": [8.1, 8.2],
                "Mem_Usage_Avg(%)": [50.5, 51.0],
                "Swap_Used(GB)": [0.0, 0.0],
                "Swap_Total(GB)": [8.0, 8.0],
                "Swap_Usage(%)": [0.0, 0.0],
            }
        )

        render_memory_dashboard(st, df, parse_process_column, extract_process_time_series, total_mem="16")

        self.assertEqual("메모리 및 AOI/SPI 분석", st.subheaders[0])
        self.assertTrue(any("현재 스왑된 메모리가 없습니다." in message for message in st.info_messages))
        self.assertEqual(1, len(st.plotly_figures))

    def test_render_memory_dashboard_marks_swap_start_without_timestamp_axis_error(self):
        st = FakeStreamlit()
        df = pd.DataFrame(
            {
                "Timestamp": pd.to_datetime(
                    ["2026-04-10 09:00:00", "2026-04-10 09:00:05", "2026-04-10 09:00:10"]
                ),
                "Mem_Used(GB)": [8.1, 8.4, 8.6],
                "Mem_Usage_Avg(%)": [50.5, 52.0, 53.0],
                "Swap_Used(GB)": [0.0, 0.2, 0.3],
                "Swap_Total(GB)": [8.0, 8.0, 8.0],
                "Swap_Usage(%)": [0.0, 2.5, 3.4],
            }
        )

        render_memory_dashboard(st, df, parse_process_column, extract_process_time_series, total_mem="16")

        self.assertEqual(1, len(st.plotly_figures))
        self.assertTrue(st.warning_messages)
        memory_fig = st.plotly_figures[0]
        self.assertGreaterEqual(len(memory_fig.layout.shapes), 2)
        self.assertTrue(memory_fig.layout.annotations)


if __name__ == "__main__":
    unittest.main()
