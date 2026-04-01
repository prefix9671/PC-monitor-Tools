import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from aoi_cli import main


class TestAoiCli(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        self.aoi_log_path = self.temp_path / "inspection_session.log"
        self.aoi_log_path.write_text(
            "\n".join(
                [
                    "20260318_174405 | debug    | (22376) |Model Open : SAMPLE_MODEL_A",
                    "20260318_174406 | debug    | (105760) |Memory|Working Set Memory Size | 47487856 KB",
                    "20260318_174407 | debug    | (22376) |InspTime|Frame : 1.19 sec|Total : 38.13 sec / 32 frame",
                    "20260318_174411 | debug    | (105760) |Memory|Working Set Memory Size | 50000000 KB",
                    "20260318_174412 | debug    | (22376) |InspTime|Frame : 1.50 sec|Total : 40.00 sec / 33 frame",
                ]
            ),
            encoding="utf-8",
        )

        self.resource_csv_path = self.temp_path / "resource_20260318.csv"
        pd.DataFrame(
            {
                "Timestamp": ["2026-03-18 17:44:06", "2026-03-18 17:44:10"],
                "CPU_Avg(%)": [10.0, 12.0],
                "Mem_Used(GB)": [28.5, 29.0],
                "Mem_Usage_Avg(%)": [50.0, 51.0],
            }
        ).to_csv(self.resource_csv_path, index=False, encoding="utf-8-sig")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_export_command_generates_xlsx_with_numbered_rows(self):
        output_path = self.temp_path / "inspection_export.xlsx"
        test_args = [
            "aoi_cli.py",
            "export",
            "--path",
            str(self.aoi_log_path),
            "--system-path",
            str(self.resource_csv_path),
            "--start-no",
            "1",
            "--end-no",
            "2",
            "--out",
            str(output_path),
        ]

        with patch.object(sys, "argv", test_args):
            exit_code = main()

        self.assertEqual(0, exit_code)
        self.assertTrue(output_path.exists())

        export_df = pd.read_excel(output_path)
        self.assertEqual(
            ["측정시간", "NO", "Frame", "Total", "Memory (인스펙터)", "Memory (시스템)"],
            export_df.columns.tolist(),
        )
        self.assertEqual([1, 2], export_df["NO"].tolist())
        self.assertAlmostEqual(28.5, float(export_df.iloc[0]["Memory (시스템)"]), places=2)
        self.assertAlmostEqual(29.0, float(export_df.iloc[1]["Memory (시스템)"]), places=2)


if __name__ == "__main__":
    unittest.main()
