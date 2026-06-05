import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(REPO_ROOT))

import collector_launcher


class TestCollectorLauncher(unittest.TestCase):
    def test_app_monitor_start_does_not_call_powershell_start_process(self):
        app_contents = (REPO_ROOT / "app.py").read_text(encoding="utf-8")

        self.assertIn("launch_collector_from_current_process", app_contents)
        self.assertNotIn("Start-Process", app_contents)
        self.assertNotIn("[\"powershell\"", app_contents)

    def test_resolve_dev_spec_targets_cli_start(self):
        with patch.object(sys, "frozen", False, create=True):
            spec = collector_launcher.resolve_collector_launch_spec()

        self.assertEqual(sys.executable, spec.executable)
        self.assertEqual((str(REPO_ROOT / "cli.py"), "start"), spec.arguments)
        self.assertEqual(str(REPO_ROOT), spec.cwd)

    def test_launch_elevated_uses_shell_execute_runas_without_powershell(self):
        calls = []

        def fake_shell_execute(hwnd, verb, executable, parameters, cwd, show_cmd):
            calls.append((hwnd, verb, executable, parameters, cwd, show_cmd))
            return 42

        result = collector_launcher.launch_collector_from_current_process(
            admin_checker=lambda: False,
            shell_execute=fake_shell_execute,
        )

        self.assertTrue(result.ok)
        self.assertTrue(result.used_elevation)
        self.assertEqual("runas", calls[0][1])
        self.assertNotIn("powershell", calls[0][2].lower())
        self.assertIn("start", calls[0][3])

    def test_launch_elevated_reports_access_denied(self):
        result = collector_launcher.launch_collector_from_current_process(
            admin_checker=lambda: False,
            shell_execute=lambda *args: 5,
        )

        self.assertFalse(result.ok)
        self.assertIn("차단", result.message)
        self.assertIn("액세스가 거부", result.detail)

    def test_launch_direct_when_already_admin_uses_popen(self):
        calls = []

        def fake_popen(args, **kwargs):
            calls.append((args, kwargs))
            return object()

        result = collector_launcher.launch_collector_from_current_process(
            admin_checker=lambda: True,
            popen=fake_popen,
        )

        self.assertTrue(result.ok)
        self.assertFalse(result.used_elevation)
        self.assertEqual(sys.executable, calls[0][0][0])
        self.assertIn("start", calls[0][0])
        self.assertEqual(str(REPO_ROOT), calls[0][1]["cwd"])
        self.assertEqual(getattr(subprocess, "CREATE_NEW_CONSOLE", 0), calls[0][1]["creationflags"])


if __name__ == "__main__":
    unittest.main()
