import io
import math
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cli import main
from collectors.aggregator import Aggregator
from collectors.cpu_temperature import (
    _select_max_sensor_temperature,
    _select_max_thermal_zone_temperature,
)
from collectors.models import MetricSample, WindowState
from collectors.writers import OutputsWriter
from dashboards.cpu import render_cpu_dashboard


def _make_sample(timestamp: float, cpu_total: float, cpu_temp_c):
    return MetricSample(
        timestamp=timestamp,
        cpu_total=cpu_total,
        cpu_temp_c=cpu_temp_c,
        mem_used_gb=8.5,
        mem_usage_pct=53.0,
        phys_mem_gb=16.0,
        os_mem_gb=16.0,
        disk_time_by_drive={},
        disk_read_by_drive={},
        disk_write_by_drive={},
        top_cpu_processes=[],
        top_mem_processes=[],
        top_disk_read_processes=[],
        top_disk_write_processes=[],
    )


class FakeColumn:
    def __init__(self):
        self.metrics = []
        self.info_messages = []

    def metric(self, label, value):
        self.metrics.append((label, value))

    def info(self, message):
        self.info_messages.append(message)


class FakeStreamlit:
    def __init__(self):
        self.plotly_figures = []
        self.columns_created = []
        self.subheaders = []
        self.captions = []
        self.errors = []

    def subheader(self, text):
        self.subheaders.append(text)

    def caption(self, text):
        self.captions.append(text)

    def error(self, text):
        self.errors.append(text)

    def plotly_chart(self, fig, width="stretch"):
        self.plotly_figures.append(fig)

    def columns(self, count):
        cols = [FakeColumn() for _ in range(count)]
        self.columns_created.append(cols)
        return cols


class TestCpuTemperatureCore(unittest.TestCase):
    def test_select_max_sensor_temperature_prefers_cpu_related_records(self):
        records = [
            {"Name": "GPU Core", "Value": 71.0, "Identifier": "/gpu-nvidia/0/temperature/0"},
            {"Name": "CPU Package", "Value": 82.4, "Identifier": "/intelcpu/0/temperature/1"},
            {"Name": "CPU Core #1", "Value": 79.1, "Identifier": "/intelcpu/0/temperature/2"},
        ]

        self.assertEqual(82.4, _select_max_sensor_temperature(records))

    def test_select_max_thermal_zone_temperature_converts_to_celsius(self):
        records = [
            {"CurrentTemperature": 3152},
            {"CurrentTemperature": 3282},
        ]

        self.assertAlmostEqual(55.05, _select_max_thermal_zone_temperature(records), places=2)

    def test_aggregator_uses_max_cpu_temperature_over_window(self):
        state = WindowState(window_start=0.0)
        state.update(_make_sample(1.0, 24.0, 55.2))
        state.update(_make_sample(2.0, 42.0, 61.7))
        state.update(_make_sample(3.0, 31.0, None))

        resource_row, _, summary = Aggregator(top_n=5).aggregate(state)

        self.assertEqual(61.7, resource_row["CPU_Temp(C)"])
        self.assertIn("Temp Max:61.7C", summary)

    def test_outputs_writer_rewrites_header_when_new_field_is_added(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            writer = OutputsWriter(temp_dir)

            writer.write_csv(
                "resource",
                {
                    "Timestamp": "2026-04-02 10:00:00",
                    "CPU_Avg(%)": 10.0,
                },
            )
            writer.write_csv(
                "resource",
                {
                    "Timestamp": "2026-04-02 10:00:05",
                    "CPU_Avg(%)": 12.0,
                    "CPU_Temp(C)": 68.5,
                },
            )

            csv_path = next(
                os.path.join(temp_dir, name)
                for name in os.listdir(temp_dir)
                if name.startswith("resource_")
            )
            frame = pd.read_csv(csv_path)

            self.assertIn("CPU_Temp(C)", frame.columns)
            self.assertTrue(math.isnan(frame.iloc[0]["CPU_Temp(C)"]))
            self.assertEqual(68.5, frame.iloc[1]["CPU_Temp(C)"])


class TestCpuDashboard(unittest.TestCase):
    def test_cpu_dashboard_renders_temperature_chart(self):
        st = FakeStreamlit()
        df = pd.DataFrame(
            {
                "Timestamp": pd.to_datetime(["2026-04-02 10:00:00", "2026-04-02 10:00:05"]),
                "CPU_Avg(%)": [25.0, 35.0],
                "CPU_Peak(%)": [40.0, 55.0],
                "CPU_Temp(C)": [61.0, 64.5],
            }
        )

        render_cpu_dashboard(st, df)

        self.assertEqual(2, len(st.plotly_figures))
        self.assertEqual("CPU 사용률과 온도", st.plotly_figures[0].layout.title.text)
        self.assertEqual("CPU 온도 추이", st.plotly_figures[1].layout.title.text)
        self.assertIn(("최대 CPU 온도 (5초 최고값)", "64.5°C"), st.columns_created[0][1].metrics)

    def test_cpu_dashboard_shows_info_when_temperature_is_missing(self):
        st = FakeStreamlit()
        df = pd.DataFrame(
            {
                "Timestamp": pd.to_datetime(["2026-04-02 10:00:00"]),
                "CPU_Avg(%)": [25.0],
                "CPU_Peak(%)": [40.0],
                "CPU_Temp(C)": [None],
            }
        )

        render_cpu_dashboard(st, df)

        self.assertEqual(1, len(st.plotly_figures))
        self.assertEqual(
            ["현재 로그에는 CPU 온도 센서 데이터가 없습니다."],
            st.columns_created[0][1].info_messages,
        )


class TestCpuTemperatureCli(unittest.TestCase):
    @patch("cli.CpuTemperatureProbe")
    def test_probe_temp_command_reports_current_temperature(self, probe_cls):
        probe = probe_cls.return_value
        probe.source_name = "LibreHardwareMonitor"
        probe.read_celsius.return_value = 67.5

        buffer = io.StringIO()
        with patch.object(sys, "argv", ["cli.py", "probe-temp"]), redirect_stdout(buffer):
            main()

        self.assertIn("CPU temperature: 67.5", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
