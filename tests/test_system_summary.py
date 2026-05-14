import os
import sys
import unittest

import pandas as pd


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dashboards.system_summary import build_system_summary_metrics, render_system_summary_cards


class FakeColumn:
    def __init__(self):
        self.metrics = []

    def metric(self, label, value, delta=None, **kwargs):
        self.metrics.append({"label": label, "value": value, "delta": delta, **kwargs})


class FakeStreamlit:
    def __init__(self):
        self.markdowns = []
        self.captions = []
        self.columns_created = []

    def markdown(self, text):
        self.markdowns.append(text)

    def caption(self, text):
        self.captions.append(text)

    def columns(self, count):
        columns = [FakeColumn() for _ in range(count)]
        self.columns_created.append(columns)
        return columns


class TestSystemSummary(unittest.TestCase):
    def test_build_system_summary_uses_filtered_dataframe_values(self):
        df = pd.DataFrame(
            {
                "CPU_Avg(%)": [10.0, 30.0],
                "CPU_Peak(%)": [40.0, 90.0],
                "CPU_Temp(C)": [55.0, 75.0],
                "Mem_Usage_Avg(%)": [60.0, 80.0],
            }
        )

        summary = build_system_summary_metrics(df)

        self.assertEqual(2, summary["sample_count"])
        self.assertEqual(20.0, summary["cpu_usage_avg_pct"])
        self.assertEqual(90.0, summary["cpu_usage_peak_pct"])
        self.assertEqual(65.0, summary["cpu_temp_avg_c"])
        self.assertEqual(75.0, summary["cpu_temp_peak_c"])
        self.assertEqual(70.0, summary["ram_usage_avg_pct"])
        self.assertEqual(80.0, summary["ram_usage_peak_pct"])

    def test_build_system_summary_falls_back_to_cpu_average_when_peak_is_missing(self):
        df = pd.DataFrame(
            {
                "CPU_Avg(%)": [15.0, 25.0],
                "Mem_Usage_Avg(%)": [45.0, 55.0],
            }
        )

        summary = build_system_summary_metrics(df)

        self.assertEqual(25.0, summary["cpu_usage_peak_pct"])
        self.assertIsNone(summary["cpu_temp_avg_c"])
        self.assertIsNone(summary["cpu_temp_peak_c"])

    def test_render_system_summary_cards_outputs_cpu_temperature_and_ram_metrics(self):
        df = pd.DataFrame(
            {
                "Timestamp": pd.to_datetime(["2026-04-10 10:00:00", "2026-04-10 10:05:00"]),
                "CPU_Avg(%)": [10.0, 30.0],
                "CPU_Peak(%)": [40.0, 90.0],
                "CPU_Temp(C)": [55.0, 75.0],
                "Mem_Usage_Avg(%)": [60.0, 80.0],
            }
        )
        st = FakeStreamlit()

        render_system_summary_cards(
            st,
            df,
            filter_start_time=pd.Timestamp("2026-04-10 10:00:00"),
            filter_end_time=pd.Timestamp("2026-04-10 10:05:00"),
        )

        metrics = [metric for column in st.columns_created[0] for metric in column.metrics]
        labels = [metric["label"] for metric in metrics]
        self.assertEqual(["CPU 사용량 평균", "CPU 온도 평균", "RAM 사용량 평균"], labels)
        self.assertEqual("20.00%", metrics[0]["value"])
        self.assertEqual("최고 90.00%", metrics[0]["delta"])
        self.assertEqual("65.0°C", metrics[1]["value"])
        self.assertEqual("최고 75.0°C", metrics[1]["delta"])
        self.assertEqual("70.00%", metrics[2]["value"])
        self.assertEqual("최대 80.00%", metrics[2]["delta"])
        self.assertIn("현재 시간 필터 기준", st.captions[0])


if __name__ == "__main__":
    unittest.main()
