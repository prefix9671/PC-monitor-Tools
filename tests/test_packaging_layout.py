import os
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(REPO_ROOT))


class TestPackagingLayout(unittest.TestCase):
    def test_generated_directories_are_not_tracked(self):
        completed = subprocess.run(
            [
                "git",
                "ls-files",
                "build",
                "dist",
                "site",
                "__pycache__",
                "dashboards/__pycache__",
                ".artifacts",
            ],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(0, completed.returncode, completed.stderr)
        tracked = [line for line in completed.stdout.splitlines() if line.strip()]
        self.assertEqual([], tracked, f"Generated artifacts should not be tracked: {tracked}")

    def test_monitor_ps1_is_deprecated_stub(self):
        contents = (REPO_ROOT / "Monitor.ps1").read_text(encoding="utf-8")

        self.assertIn("공식 정리 대상", contents)
        self.assertIn("start_monitor.bat", contents)
        self.assertIn("개발 환경에서는 .\\venv\\Scripts\\python cli.py start", contents)

    def test_build_bat_uses_artifacts_release_bundle(self):
        contents = (REPO_ROOT / "build.bat").read_text(encoding="utf-8")

        self.assertIn(".artifacts", contents)
        self.assertIn("RELEASE_ROOT", contents)
        self.assertNotIn('copy "Monitor.ps1"', contents)
        self.assertNotIn('dist\\Manual.zip', contents)

    def test_monitor_spec_uses_generated_manual_artifact_site(self):
        contents = (REPO_ROOT / "monitor.spec").read_text(encoding="utf-8")

        self.assertIn("manual_site_dir = Path('.artifacts/manual-site')", contents)
        self.assertNotIn("('Monitor.ps1', '.')", contents)

    def test_streamlit_upload_limit_is_pinned_to_one_gigabyte(self):
        config_contents = (REPO_ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
        run_app_contents = (REPO_ROOT / "run_app.py").read_text(encoding="utf-8")

        self.assertIn("maxUploadSize = 1024", config_contents)
        self.assertIn("--server.maxUploadSize=1024", run_app_contents)


if __name__ == "__main__":
    unittest.main()
