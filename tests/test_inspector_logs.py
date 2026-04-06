import tempfile
import unittest
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from inspector_logs.core import (
    build_inspection_records,
    format_inspection_export_dataframe,
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
                    "20260318_174405 | debug    | (22376) |Model Open : SAMPLE_MODEL_A",
                    "20260318_174406 | debug    | (105760) |Memory|Working Set Memory Size | 47487856 KB",
                    "20260318_174407 | debug    | (22376) |InspTime|Frame : 1.19 sec|Total : 38.13 sec / 32 frame",
                    "noise line that should be ignored",
                    "20260318_174411 | debug    | (105760) |Memory|Working Set Memory Size | 50000000 KB",
                    "20260318_174412 | debug    | (22376) |InspTime|Frame : 1.50 sec|Total : 40.00 sec / 33 frame",
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

        self.assertEqual(5, len(df))
        self.assertIn("Inspector_Frame_Sec", df.columns)
        self.assertIn("Inspector_WorkingSet_GB", df.columns)
        self.assertIn("Inspector_Model_Name", df.columns)

        insp_row = df[df["Inspector_Event_Type"] == "insp_time"].iloc[0]
        mem_row = df[df["Inspector_Event_Type"] == "working_set"].iloc[0]
        model_row = df[df["Inspector_Event_Type"] == "model_open"].iloc[0]

        self.assertAlmostEqual(1.19, float(insp_row["Inspector_Frame_Sec"]), places=2)
        self.assertAlmostEqual(38.13, float(insp_row["Inspector_Total_Sec"]), places=2)
        self.assertEqual(32, int(insp_row["Inspector_Total_Frames"]))
        self.assertAlmostEqual(47487856 / 1024.0, float(mem_row["Inspector_WorkingSet_MB"]), places=2)
        self.assertEqual("SAMPLE_MODEL_A", model_row["Inspector_Model_Name"])

    def test_summary_counts(self):
        df = load_inspector_log_data(str(self.base_path))
        summary = summarize_inspector_log_data(df)

        self.assertEqual(5, summary["rows"])
        self.assertEqual(2, summary["insp_rows"])
        self.assertEqual(2, summary["memory_rows"])
        self.assertEqual(2, summary["inspection_rows"])
        self.assertEqual("SAMPLE_MODEL_A", summary["active_model_name"])
        self.assertAlmostEqual(40.0, float(summary["max_total_sec"]), places=2)

    def test_build_inspection_records_matches_model_memory_and_system_memory(self):
        df = load_inspector_log_data(str(self.base_path))
        system_df = pd.DataFrame(
            {
                "Timestamp": pd.to_datetime(
                    [
                        "2026-03-18 17:44:06",
                        "2026-03-18 17:44:10",
                    ]
                ),
                "Mem_Used(GB)": [28.5, 29.0],
            }
        )

        records = build_inspection_records(df, system_df)
        export_df = format_inspection_export_dataframe(records)

        self.assertEqual(2, len(records))
        self.assertEqual([1, 2], records["Inspection_No"].tolist())
        self.assertTrue((records["Inspector_Model_Name"] == "SAMPLE_MODEL_A").all())
        self.assertAlmostEqual(47487856 / (1024.0 * 1024.0), float(records.iloc[0]["Inspector_WorkingSet_GB"]), places=3)
        self.assertAlmostEqual(50000000 / (1024.0 * 1024.0), float(records.iloc[1]["Inspector_WorkingSet_GB"]), places=3)
        self.assertAlmostEqual(28.5, float(records.iloc[0]["System_Memory_Used_GB"]), places=2)
        self.assertAlmostEqual(29.0, float(records.iloc[1]["System_Memory_Used_GB"]), places=2)
        self.assertEqual(
            ["측정시간", "NO", "Frame", "Total", "Memory (인스펙터)", "Memory (시스템)"],
            export_df.columns.tolist(),
        )

    def test_parse_uploaded_log_payload(self):
        uploaded_df = load_inspector_log_data_from_uploads(
            [(self.log_path.name, self.log_path.read_bytes())]
        )

        self.assertEqual(5, len(uploaded_df))
        self.assertIn("Inspector_WorkingSet_MB", uploaded_df.columns)

    def test_large_single_file_uses_parallel_chunk_executor(self):
        parallel_log_path = Path(self.temp_dir.name) / "parallel_parse.log"
        parallel_log_path.write_text(
            "\n".join(
                [
                    "20260318_174405 | debug    | (22376) |Model Open : SAMPLE_MODEL_A",
                    "20260318_174406 | debug    | (105760) |Memory|Working Set Memory Size | 47487856 KB",
                    "20260318_174407 | debug    | (22376) |InspTime|Frame : 1.19 sec|Total : 38.13 sec / 32 frame",
                    "noise line that should be ignored",
                    "20260318_174411 | debug    | (105760) |Memory|Working Set Memory Size | 50000000 KB",
                    "20260318_174412 | debug    | (22376) |InspTime|Frame : 1.50 sec|Total : 40.00 sec / 33 frame",
                ]
            ),
            encoding="utf-8",
        )

        class RecordingExecutor:
            used = False
            max_workers = None

            def __init__(self, max_workers):
                RecordingExecutor.used = True
                RecordingExecutor.max_workers = max_workers

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def map(self, func, iterable):
                return map(func, iterable)

        with patch("inspector_logs.core.INSPECTOR_PARSE_MIN_LINE_COUNT_FOR_PARALLEL", 4), patch(
            "inspector_logs.core.INSPECTOR_PARSE_CHUNK_LINE_COUNT", 2
        ), patch("inspector_logs.core.concurrent.futures.ThreadPoolExecutor", RecordingExecutor):
            df = load_inspector_log_data(str(parallel_log_path))

        self.assertTrue(RecordingExecutor.used)
        self.assertGreaterEqual(RecordingExecutor.max_workers, 2)
        self.assertEqual(5, len(df))
        self.assertEqual(
            ["model_open", "working_set", "insp_time", "working_set", "insp_time"],
            df["Inspector_Event_Type"].tolist(),
        )


if __name__ == "__main__":
    unittest.main()
