import os
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from collectors.subprocess_utils import (
    check_output_text,
    decode_subprocess_text,
    run_text_capture,
)


class TestSubprocessUtils(unittest.TestCase):
    def test_decode_subprocess_text_replaces_invalid_bytes_when_all_codecs_fail(self):
        decoded = decode_subprocess_text(b"\x80CPU")

        self.assertIn("CPU", decoded)
        self.assertIn("\ufffd", decoded)

    @patch("collectors.subprocess_utils.subprocess.run")
    def test_run_text_capture_decodes_invalid_bytes_without_raising(self, run_mock):
        run_mock.return_value = subprocess.CompletedProcess(
            args=["powershell.exe"],
            returncode=0,
            stdout=b"stdout\x80",
            stderr=b"stderr\x80",
        )

        completed = run_text_capture(
            ["powershell.exe", "-Command", "Write-Output test"],
            timeout=1.0,
            creationflags=0,
        )

        self.assertEqual(0, completed.returncode)
        self.assertIn("stdout", completed.stdout)
        self.assertIn("stderr", completed.stderr)
        _, kwargs = run_mock.call_args
        self.assertTrue(kwargs["capture_output"])
        self.assertFalse(kwargs["text"])
        self.assertFalse(kwargs["check"])

    @patch("collectors.subprocess_utils.subprocess.check_output")
    def test_check_output_text_decodes_invalid_bytes_without_raising(self, check_output_mock):
        check_output_mock.return_value = b"partition\x80"

        output = check_output_text(
            'powershell -Command "Get-Partition"',
            shell=True,
            creationflags=0,
        )

        self.assertIn("partition", output)
        _, kwargs = check_output_mock.call_args
        self.assertFalse(kwargs["text"])


if __name__ == "__main__":
    unittest.main()
