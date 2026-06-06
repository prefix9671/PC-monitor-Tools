import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from collectors.dell_command_monitor import DcmBootstrapResult
from collectors.libre_hardware_monitor import LhmCpuCoreTemperatureSample
from collectors.wmi_query import WmiQuerySpec
from collectors.cpu_temperature_diagnostics import (
    collect_cpu_temperature_diagnostics,
    write_cpu_temperature_diagnostic_log,
)


class FakeProbe:
    def __init__(self, *args, **kwargs):
        self.enable_dell_command_monitor = False
        self._state_path = Path(tempfile.gettempdir()) / "fake-cpu-temp-state.json"
        self._providers = [
            (
                "OpenHardwareMonitor",
                WmiQuerySpec(
                    namespace="root\\OpenHardwareMonitor",
                    class_name="Sensor",
                    properties=("Name", "SensorType", "Value", "Identifier", "Parent"),
                ),
                lambda records: SimpleNamespace(value_c=50.0, detail="CPU Package | fake"),
            )
        ]
        self.source_name = None
        self.source_detail = None

    def _query_wmi_provider_records(self, query_spec):
        return [{"Name": "CPU Package", "Value": 50.0, "Identifier": "/intelcpu/0/temperature/1"}]

    def read_celsius(self, force_refresh: bool = False):
        self.source_name = "LibreHardwareMonitorCoreMax"
        self.source_detail = "Intel Xeon | CPU Core #4 | /intelcpu/0/temperature/4"
        return 77.4

    def close(self):
        return None


class TestCpuTemperatureDiagnostics(unittest.TestCase):
    @patch("collectors.cpu_temperature_diagnostics.collect_cpu_temperature_diagnostics")
    def test_write_cpu_temperature_diagnostic_log_creates_log_and_latest_alias(self, collect_mock):
        collect_mock.return_value = {
            "generated_at": "2026-04-10T18:00:00",
            "force_refresh_probe": {"value_c": 73.4, "source_name": "LibreHardwareMonitorCoreMax"},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            diagnostics, log_path, latest_path = write_cpu_temperature_diagnostic_log(temp_dir)

            self.assertEqual("2026-04-10T18:00:00", diagnostics["generated_at"])
            self.assertTrue(log_path.exists())
            self.assertTrue(latest_path.exists())
            self.assertIn("LibreHardwareMonitorCoreMax", log_path.read_text(encoding="utf-8"))
            self.assertEqual(log_path.read_text(encoding="utf-8"), latest_path.read_text(encoding="utf-8"))

    @patch("collectors.cpu_temperature_diagnostics.CpuTemperatureProbe", FakeProbe)
    @patch("collectors.cpu_temperature_diagnostics.get_system_identity", return_value=("Advantech", "IPC-BOX"))
    @patch("collectors.cpu_temperature_diagnostics.resolve_dcm_package", return_value=None)
    @patch(
        "collectors.cpu_temperature_diagnostics.ensure_dcm_ready",
        return_value=DcmBootstrapResult(
            manufacturer="Advantech",
            model="IPC-BOX",
            supported_model=False,
            package_name=None,
            installed_version=None,
            namespace_available=False,
            attempted_install=False,
            reboot_required=False,
            installer_path=None,
            message="DCM bootstrap skipped",
        ),
    )
    @patch(
        "collectors.cpu_temperature_diagnostics.load_state_payload",
        return_value={"status": "ok", "provider_name": "LibreHardwareMonitorCoreMax", "value_c": 77.4},
    )
    @patch("collectors.cpu_temperature_diagnostics.capture_and_write_state", return_value=True)
    @patch("collectors.cpu_temperature_diagnostics.read_lhm_bundle_manifest", return_value={"version": "v0.9.6"})
    @patch("collectors.cpu_temperature_diagnostics.ensure_lhm_bundle_dir", return_value=Path("C:/temp/lhm-cache/v0.9.6"))
    @patch(
        "collectors.cpu_temperature_diagnostics.read_cpu_core_max_temperature_sample",
        return_value=LhmCpuCoreTemperatureSample(
            value_c=77.4,
            detail="Intel Xeon | CPU Core #4 | /intelcpu/0/temperature/4",
            sensor_name="CPU Core #4",
            hardware_name="Intel Xeon",
        ),
    )
    def test_collect_cpu_temperature_diagnostics_includes_worker_and_provider_results(self, *_mocks):
        diagnostics = collect_cpu_temperature_diagnostics()

        self.assertEqual("Advantech", diagnostics["system_identity"]["manufacturer"])
        self.assertEqual(77.4, diagnostics["force_refresh_probe"]["value_c"])
        self.assertEqual("LibreHardwareMonitorCoreMax", diagnostics["force_refresh_probe"]["source_name"])
        self.assertEqual("v0.9.6", diagnostics["lhm_worker"]["manifest"]["version"])
        self.assertEqual("OpenHardwareMonitor", diagnostics["provider_diagnostics"][0]["provider_name"])
        self.assertEqual(50.0, diagnostics["provider_diagnostics"][0]["selected_value_c"])


if __name__ == "__main__":
    unittest.main()
