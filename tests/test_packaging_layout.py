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
        self.assertIn("scripts\\run_prebuild_regression.py", contents)
        self.assertIn("scripts\\prepare_lhm_bundle.py", contents)
        self.assertIn("scripts\\prepare_pawnio_bundle.py", contents)
        self.assertIn("scripts\\publish_release_to_share.ps1", contents)
        self.assertIn("install_pawnio.bat", contents)
        self.assertIn("pawnio-bundle", contents)
        self.assertIn("NETWORK_RELEASE_HOST", contents)
        self.assertIn("NETWORK_RELEASE_SHARE", contents)
        self.assertNotIn('copy "Monitor.ps1"', contents)
        self.assertNotIn('dist\\Manual.zip', contents)

    def test_monitor_spec_uses_generated_manual_artifact_site(self):
        contents = (REPO_ROOT / "monitor.spec").read_text(encoding="utf-8")

        self.assertIn("manual_site_dir = Path('.artifacts/manual-site')", contents)
        self.assertIn("lhm_bundle_dir = Path('.artifacts/vendor/lhm-bundle')", contents)
        self.assertIn("pawnio_bundle_dir = Path('.artifacts/vendor/pawnio-bundle')", contents)
        self.assertIn("('collector_launcher.py', '.')", contents)
        self.assertIn("datas.append((str(lhm_bundle_dir), 'lhm-bundle'))", contents)
        self.assertIn("datas.append((str(pawnio_bundle_dir), 'pawnio-bundle'))", contents)
        self.assertIn("collect_data_files('pythonnet')", contents)
        self.assertIn("'clr'", contents)
        self.assertNotIn("('Monitor.ps1', '.')", contents)

    def test_install_pawnio_script_routes_through_packaged_cli(self):
        contents = (REPO_ROOT / "install_pawnio.bat").read_text(encoding="utf-8")

        self.assertIn("install-pawnio", contents)
        self.assertIn("PawnIO_setup.exe", contents)
        self.assertIn("Start-Process", contents)

    def test_start_monitor_checks_pawnio_before_collector_launch(self):
        contents = (REPO_ROOT / "start_monitor.bat").read_text(encoding="utf-8")

        self.assertIn("install-pawnio --check-only", contents)
        self.assertIn("Install bundled PawnIO now", contents)

    def test_streamlit_upload_limit_is_pinned_to_one_gigabyte(self):
        config_contents = (REPO_ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
        run_app_contents = (REPO_ROOT / "run_app.py").read_text(encoding="utf-8")

        self.assertIn("maxUploadSize = 1024", config_contents)
        self.assertIn("--server.maxUploadSize=1024", run_app_contents)
        self.assertIn('"install-pawnio"', run_app_contents)

    def test_requirements_include_pythonnet(self):
        contents = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")

        self.assertIn("pythonnet", contents)

    def test_prebuild_regression_scripts_exist(self):
        python_runner = (REPO_ROOT / "scripts" / "run_prebuild_regression.py").read_text(encoding="utf-8")
        playwright_runner = (REPO_ROOT / "scripts" / "verify_playwright_prebuild_regression.js").read_text(encoding="utf-8")
        publish_runner = (REPO_ROOT / "scripts" / "publish_release_to_share.ps1").read_text(encoding="utf-8")

        self.assertIn("headless-playwright-regression", python_runner)
        self.assertIn("aoi-inspector-time-filter-fixture-regression", python_runner)
        self.assertIn("inspector_time_filter_range_regression.log", python_runner)
        self.assertIn("inspection-time-filter", playwright_runner)
        self.assertIn("FAILS IF:", playwright_runner)
        self.assertIn("Get-Credential", publish_runner)
        self.assertIn("cmdkey.exe", publish_runner)
        self.assertIn("Get-DefaultTargetFolderName", publish_runner)
        self.assertIn("Archive-PreviousReleases", publish_runner)
        self.assertIn("Join-Path $CopyRoot \"old\"", publish_runner)
        self.assertIn("192.168.1.13", publish_runner)


if __name__ == "__main__":
    unittest.main()
