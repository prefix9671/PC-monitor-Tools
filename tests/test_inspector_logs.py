import tempfile
import unittest
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from inspector_logs.core import (
    load_inspector_log_data,
    load_inspector_log_data_from_uploads,
    resolve_inspector_log_paths,
    summarize_inspector_log_data,
)


class TestInspectorLogs(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name) / "operation_sample"
        self.log_path = self.base_path.with_suffix(".log")
        self.log_path.write_text(
            "\n".join(
                [
                    "20260318_174407 | debug    | (22376) |InspTime|Frame : 1.19 sec|Total : 38.13 sec / 32 frame",
                    "noise line that should be ignored",
                    "20260318_174418 | debug    | (105760) |Memory|Working Set Memory Size | 47487856 KB",
                ]
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_resolve_base_path_without_extension(self):
        resolved = resolve_inspector_log_paths(str(self.base_path))
        self.assertEqual([self.log_path.resolve()], resolved)

    def test_parse_inspector_rows(self):
        df = load_inspector_log_data(str(self.base_path))

        self.assertEqual(2, len(df))
        self.assertIn("Inspector_Frame_Sec", df.columns)
        self.assertIn("Inspector_WorkingSet_GB", df.columns)

        insp_row = df[df["Inspector_Event_Type"] == "insp_time"].iloc[0]
        mem_row = df[df["Inspector_Event_Type"] == "working_set"].iloc[0]

        self.assertAlmostEqual(1.19, float(insp_row["Inspector_Frame_Sec"]), places=2)
        self.assertAlmostEqual(38.13, float(insp_row["Inspector_Total_Sec"]), places=2)
        self.assertEqual(32, int(insp_row["Inspector_Total_Frames"]))
        self.assertAlmostEqual(47487856 / 1024.0, float(mem_row["Inspector_WorkingSet_MB"]), places=2)

    def test_summary_counts(self):
        df = load_inspector_log_data(str(self.base_path))
        summary = summarize_inspector_log_data(df)

        self.assertEqual(2, summary["rows"])
        self.assertEqual(1, summary["insp_rows"])
        self.assertEqual(1, summary["memory_rows"])
        self.assertAlmostEqual(38.13, float(summary["max_total_sec"]), places=2)

    def test_parse_uploaded_log_payload(self):
        uploaded_df = load_inspector_log_data_from_uploads(
            [(self.log_path.name, self.log_path.read_bytes())]
        )

        self.assertEqual(2, len(uploaded_df))
        self.assertIn("Inspector_WorkingSet_MB", uploaded_df.columns)


if __name__ == "__main__":
    unittest.main()
