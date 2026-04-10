import io
import json
import math
import os
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cli import main
from collectors.aggregator import Aggregator
from collectors.dell_command_monitor import (
    LEGACY_PRECISION_PACKAGE,
    MODERN_PRECISION_PACKAGE,
    resolve_dcm_package,
)
from collectors.cpu_temperature import (
    CpuTemperatureProbe,
    _convert_numeric_sensor_to_celsius,
    _convert_perf_raw_thermal_zone_to_celsius,
    _select_dell_command_monitor_temperature,
    _select_perf_raw_thermal_zone_temperature,
    _select_max_sensor_temperature,
    _select_max_thermal_zone_temperature,
)
from collectors.libre_hardware_monitor import (
    LIBRE_HARDWARE_MONITOR_CORE_MAX_PROVIDER,
    _is_cpu_core_sensor_name,
    _select_hottest_cpu_core_candidate,
)
from collectors.models import MetricSample, WindowState
from collectors.writers import OutputsWriter
from dashboards.cpu import render_cpu_dashboard


def _make_sample(timestamp: float, cpu_total: float, cpu_temp_c, swap_used_gb=0.0, swap_total_gb=0.0, swap_usage_pct=0.0):
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
        swap_used_gb=swap_used_gb,
        swap_total_gb=swap_total_gb,
        swap_usage_pct=swap_usage_pct,
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
    def test_resolve_dcm_package_distinguishes_legacy_and_modern_precision_towers(self):
        legacy = resolve_dcm_package("Dell Inc.", "Precision 5820 Tower")
        modern = resolve_dcm_package("Dell Inc.", "Precision 5860 Tower")
        non_target = resolve_dcm_package("ASUS", "ROG STRIX")

        self.assertEqual(LEGACY_PRECISION_PACKAGE, legacy)
        self.assertEqual(MODERN_PRECISION_PACKAGE, modern)
        self.assertIsNone(non_target)

    def test_select_max_sensor_temperature_prefers_cpu_package_when_available(self):
        records = [
            {"Name": "GPU Core", "Value": 71.0, "Identifier": "/gpu-nvidia/0/temperature/0"},
            {"Name": "CPU Package", "Value": 78.4, "Identifier": "/intelcpu/0/temperature/1"},
            {"Name": "CPU Core #1", "Value": 81.1, "Identifier": "/intelcpu/0/temperature/2"},
        ]

        self.assertEqual(78.4, _select_max_sensor_temperature(records))

    def test_convert_numeric_sensor_to_celsius_prefers_raw_temperature_when_scaled_value_is_implausible(self):
        record = {
            "CurrentReading": 58,
            "UnitModifier": -1,
            "BaseUnits": 2,
            "ElementName": "CPU Package Temperature Sensor",
        }

        self.assertEqual(58.0, _convert_numeric_sensor_to_celsius(record))

    def test_select_dell_command_monitor_temperature_prefers_cpu_package(self):
        records = [
            {"ElementName": "System Board Temperature Sensor", "DeviceID": "SYS_TEMP", "CurrentReading": 39, "BaseUnits": 2},
            {"ElementName": "CPU Package Temperature Sensor", "DeviceID": "CPU_PACKAGE", "CurrentReading": 74, "BaseUnits": 2},
            {"ElementName": "CPU Core 0 Temperature Sensor", "DeviceID": "CPU_CORE_0", "CurrentReading": 81, "BaseUnits": 2},
        ]

        self.assertEqual(74.0, _select_dell_command_monitor_temperature(records))

    def test_select_max_thermal_zone_temperature_converts_to_celsius(self):
        records = [
            {"CurrentTemperature": 3152},
            {"CurrentTemperature": 3282},
        ]

        self.assertAlmostEqual(55.05, _select_max_thermal_zone_temperature(records), places=2)

    def test_convert_perf_raw_thermal_zone_to_celsius_from_kelvin(self):
        record = {"Name": "CPU Thermal Zone", "Temperature": 353}

        self.assertAlmostEqual(79.85, _convert_perf_raw_thermal_zone_to_celsius(record), places=2)

    def test_convert_perf_raw_thermal_zone_to_celsius_from_tenths_kelvin(self):
        record = {"Name": "CPU Thermal Zone", "Temperature": 3530}

        self.assertAlmostEqual(79.85, _convert_perf_raw_thermal_zone_to_celsius(record), places=2)

    def test_convert_perf_raw_thermal_zone_to_celsius_ignores_non_positive_and_implausible_values(self):
        self.assertIsNone(_convert_perf_raw_thermal_zone_to_celsius({"Temperature": 0}))
        self.assertIsNone(_convert_perf_raw_thermal_zone_to_celsius({"Temperature": -1}))
        self.assertIsNone(_convert_perf_raw_thermal_zone_to_celsius({"Temperature": 20000}))

    def test_select_perf_raw_thermal_zone_temperature_prefers_cpu_keyword_records(self):
        records = [
            {"Name": "Mainboard Thermal Zone", "Temperature": 360},
            {"Name": "CPU Thermal Zone", "Temperature": 353},
        ]

        self.assertAlmostEqual(79.85, _select_perf_raw_thermal_zone_temperature(records), places=2)

    def test_select_perf_raw_thermal_zone_temperature_prefers_specific_zone_over_total_aggregate(self):
        records = [
            {"Name": "Processor Information", "InstanceName": "_Total", "Temperature": 331},
            {"Name": "Thermal Zone CPU0", "InstanceName": "TZ00", "Temperature": 356},
        ]

        self.assertAlmostEqual(82.85, _select_perf_raw_thermal_zone_temperature(records), places=2)

    def test_select_perf_raw_thermal_zone_temperature_falls_back_to_max_valid_value(self):
        records = [
            {"Name": "Thermal Zone A", "Temperature": 340},
            {"Name": "Thermal Zone B", "Temperature": 353},
        ]

        self.assertAlmostEqual(79.85, _select_perf_raw_thermal_zone_temperature(records), places=2)

    def test_lhm_core_sensor_name_matches_only_numbered_core_sensors(self):
        self.assertTrue(_is_cpu_core_sensor_name("CPU Core #1"))
        self.assertTrue(_is_cpu_core_sensor_name("Core 7"))
        self.assertFalse(_is_cpu_core_sensor_name("CPU Package"))
        self.assertFalse(_is_cpu_core_sensor_name("Core Max"))
        self.assertFalse(_is_cpu_core_sensor_name("CPU Core #1 Distance to TjMax"))

    def test_select_hottest_cpu_core_candidate_uses_max_core_value(self):
        selected = _select_hottest_cpu_core_candidate(
            [
                {"value_c": 71.1, "sensor_name": "CPU Core #1"},
                {"value_c": 82.4, "sensor_name": "CPU Core #4"},
                {"value_c": 79.8, "sensor_name": "CPU Core #2"},
            ]
        )

        self.assertEqual("CPU Core #4", selected["sensor_name"])
        self.assertEqual(82.4, selected["value_c"])

    def test_probe_provider_order_for_non_dell_uses_openhardwaremonitor_then_thermal_zone_fallbacks(self):
        probe = CpuTemperatureProbe(
            enable_dell_command_monitor=False,
            system_identity=("Advantech", "ARK-3534"),
        )

        self.assertEqual(
            [
                "OpenHardwareMonitor",
                "PerfRawThermalZone",
                "MSAcpiThermalZone",
            ],
            [provider_name for provider_name, *_ in probe._providers],
        )

    def test_probe_provider_order_for_dell_keeps_legacy_fallbacks(self):
        probe = CpuTemperatureProbe(
            enable_dell_command_monitor=False,
            system_identity=("Dell Inc.", "Precision 5820 Tower"),
        )

        self.assertEqual(
            [
                "LibreHardwareMonitor",
                "OpenHardwareMonitor",
                "PerfRawThermalZone",
                "MSAcpiThermalZone",
            ],
            [provider_name for provider_name, *_ in probe._providers],
        )

    def test_non_dell_probe_reads_worker_state_before_fallbacks(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "cpu-core-temp-state.json"
            state_path.write_text(
                json.dumps(
                    {
                        "status": "ok",
                        "provider_name": LIBRE_HARDWARE_MONITOR_CORE_MAX_PROVIDER,
                        "value_c": 73.4,
                        "detail": "Intel Xeon | CPU Core #4 | /intelcpu/0/temperature/4",
                        "sampled_at_epoch": time.time(),
                    }
                ),
                encoding="utf-8",
            )
            probe = CpuTemperatureProbe(
                enable_dell_command_monitor=False,
                system_identity=("Advantech", "ARK-3534"),
                state_path=state_path,
            )

            value = probe.read_celsius()

            self.assertEqual(73.4, value)
            self.assertEqual(LIBRE_HARDWARE_MONITOR_CORE_MAX_PROVIDER, probe.source_name)
            self.assertEqual("Intel Xeon | CPU Core #4 | /intelcpu/0/temperature/4", probe.source_detail)

    def test_aggregator_uses_max_cpu_temperature_over_window(self):
        state = WindowState(window_start=0.0)
        state.update(_make_sample(1.0, 24.0, 55.2))
        state.update(_make_sample(2.0, 42.0, 61.7))
        state.update(_make_sample(3.0, 31.0, None))

        resource_row, _, summary = Aggregator(top_n=5).aggregate(state)

        self.assertEqual(61.7, resource_row["CPU_Temp(C)"])
        self.assertIn("Temp Max:61.7C", summary)

    def test_aggregator_tracks_peak_swap_usage_over_window(self):
        state = WindowState(window_start=0.0)
        state.update(_make_sample(1.0, 24.0, 55.2, swap_used_gb=0.0, swap_total_gb=8.0, swap_usage_pct=0.0))
        state.update(_make_sample(2.0, 42.0, 61.7, swap_used_gb=0.35, swap_total_gb=8.0, swap_usage_pct=4.4))
        state.update(_make_sample(3.0, 31.0, None, swap_used_gb=0.12, swap_total_gb=8.0, swap_usage_pct=1.5))

        resource_row, _, summary = Aggregator(top_n=5).aggregate(state)

        self.assertEqual(0.35, resource_row["Swap_Used(GB)"])
        self.assertEqual(8.0, resource_row["Swap_Total(GB)"])
        self.assertEqual(4.4, resource_row["Swap_Usage(%)"])
        self.assertIn("Swap Max:0.35GB ( 4.4%)", summary)

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
    @patch("cli.ensure_dcm_ready")
    def test_probe_temp_command_reports_current_temperature(self, _ensure_dcm_ready, probe_cls):
        _ensure_dcm_ready.return_value.message = ""
        probe = probe_cls.return_value
        probe.source_name = "LibreHardwareMonitor"
        probe.source_detail = "CPU Package"
        probe.read_celsius.return_value = 67.5

        buffer = io.StringIO()
        with patch.object(sys, "argv", ["cli.py", "probe-temp"]), redirect_stdout(buffer):
            main()

        self.assertIn("CPU temperature: 67.5", buffer.getvalue())
        self.assertIn("Source: LibreHardwareMonitor", buffer.getvalue())
        self.assertIn("Sensor: CPU Package", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
