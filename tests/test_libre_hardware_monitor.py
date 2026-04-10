import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from collectors.libre_hardware_monitor import ensure_lhm_bundle_dir


class TestLibreHardwareMonitorBundleResolution(unittest.TestCase):
    def test_ensure_lhm_bundle_dir_prefers_local_bundle_without_network(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_dir = Path(temp_dir) / "lhm-bundle"
            bundle_dir.mkdir(parents=True, exist_ok=True)
            (bundle_dir / "LibreHardwareMonitorLib.dll").write_bytes(b"fake-dll")

            with patch(
                "collectors.libre_hardware_monitor._local_bundle_dir_candidates",
                return_value=[bundle_dir],
            ), patch(
                "collectors.libre_hardware_monitor._request_json",
                side_effect=AssertionError("Network access should not be attempted when local bundle exists."),
            ):
                resolved = ensure_lhm_bundle_dir()

            self.assertEqual(bundle_dir, resolved)


if __name__ == "__main__":
    unittest.main()
