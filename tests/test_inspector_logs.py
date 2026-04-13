import tempfile
import unittest
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from inspector_logs.core import (
    build_inspection_sample_sections,
    build_inspection_records,
    filter_inspection_records_by_time_range,
    format_inspection_export_dataframe,
    format_inspection_preview_dataframe,
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
        preview_df = format_inspection_preview_dataframe(records)
        export_df = format_inspection_export_dataframe(records)
        export_with_inspector_df = format_inspection_export_dataframe(records, include_inspector_memory=True)

        self.assertEqual(2, len(records))
        self.assertEqual([1, 2], records["Inspection_No"].tolist())
        self.assertTrue((records["Inspector_Model_Name"] == "SAMPLE_MODEL_A").all())
        self.assertAlmostEqual(47487856 / (1024.0 * 1024.0), float(records.iloc[0]["Inspector_WorkingSet_GB"]), places=3)
        self.assertAlmostEqual(50000000 / (1024.0 * 1024.0), float(records.iloc[1]["Inspector_WorkingSet_GB"]), places=3)
        self.assertAlmostEqual(28.5, float(records.iloc[0]["System_Memory_Used_GB"]), places=2)
        self.assertAlmostEqual(29.0, float(records.iloc[1]["System_Memory_Used_GB"]), places=2)
        self.assertEqual(
            ["NO", "Frame", "Total", "메모리 (인스펙터)", "메모리 (시스템)"],
            preview_df.columns.tolist(),
        )
        self.assertEqual(
            ["NO", "Frame", "Total", "메모리 (시스템)"],
            export_df.columns.tolist(),
        )
        self.assertEqual(
            ["NO", "Frame", "Total", "메모리 (시스템)", "메모리 (인스펙터)"],
            export_with_inspector_df.columns.tolist(),
        )

    def test_parse_uploaded_log_payload(self):
        uploaded_df = load_inspector_log_data_from_uploads(
            [(self.log_path.name, self.log_path.read_bytes())]
        )

        self.assertEqual(5, len(uploaded_df))
        self.assertIn("Inspector_WorkingSet_MB", uploaded_df.columns)

    def test_filter_inspection_records_by_time_range_keeps_original_no(self):
        inspection_records = pd.DataFrame(
            {
                "Timestamp": pd.to_datetime(
                    [
                        "2026-03-18 00:00:05",
                        "2026-03-18 12:00:05",
                        "2026-03-19 00:00:05",
                    ]
                ),
                "SourceFile": ["sample.log"] * 3,
                "Inspection_No": [101, 205, 309],
                "Inspector_Model_Name": ["SAMPLE_MODEL_A"] * 3,
                "Inspector_Frame_Sec": [1.0, 1.1, 1.2],
                "Inspector_Total_Sec": [10.0, 11.0, 12.0],
                "Inspector_Total_Frames": [10, 11, 12],
                "Inspector_WorkingSet_KB": [1000.0, 1100.0, 1200.0],
                "Inspector_WorkingSet_MB": [1.0, 1.1, 1.2],
                "Inspector_WorkingSet_GB": [0.001, 0.0011, 0.0012],
                "System_Memory_Used_GB": [20.0, 21.0, 22.0],
                "System_Memory_Timestamp": pd.to_datetime(
                    [
                        "2026-03-18 00:00:00",
                        "2026-03-18 12:00:00",
                        "2026-03-19 00:00:00",
                    ]
                ),
            }
        )

        filtered = filter_inspection_records_by_time_range(
            inspection_records,
            start_time="2026-03-18 12:00:00",
            end_time="2026-03-19 00:10:00",
        )

        self.assertEqual([205, 309], filtered["Inspection_No"].tolist())

    def test_build_inspection_sample_sections_uses_anchor_and_first_10_after_it(self):
        inspection_records = pd.DataFrame(
            {
                "Timestamp": pd.to_datetime(
                    [
                        "2026-03-18 00:00:05",
                        "2026-03-18 00:00:10",
                        "2026-03-18 12:00:01",
                        "2026-03-18 12:00:05",
                        "2026-03-19 00:00:03",
                        "2026-03-19 00:05:00",
                    ]
                ),
                "SourceFile": ["sample.log"] * 6,
                "Inspection_No": [1, 2, 11, 12, 21, 22],
                "Inspector_Model_Name": ["SAMPLE_MODEL_A"] * 6,
                "Inspector_Frame_Sec": [1.0, 1.1, 1.2, 1.3, 1.4, 1.5],
                "Inspector_Total_Sec": [10.0, 10.1, 10.2, 10.3, 10.4, 10.5],
                "Inspector_Total_Frames": [10, 10, 10, 10, 10, 10],
                "Inspector_WorkingSet_KB": [1000.0] * 6,
                "Inspector_WorkingSet_MB": [1.0] * 6,
                "Inspector_WorkingSet_GB": [0.001, 0.0011, 0.0012, 0.0013, 0.0014, 0.0015],
                "System_Memory_Used_GB": [20.0, 20.1, 20.2, 20.3, 20.4, 20.5],
                "System_Memory_Timestamp": pd.to_datetime(
                    [
                        "2026-03-18 00:00:00",
                        "2026-03-18 00:00:05",
                        "2026-03-18 12:00:00",
                        "2026-03-18 12:00:05",
                        "2026-03-19 00:00:00",
                        "2026-03-19 00:05:00",
                    ]
                ),
            }
        )

        sample_sections = build_inspection_sample_sections(
            inspection_records,
            start_time="2026-03-18 00:00:00",
            end_time="2026-03-19 12:10:00",
            include_inspector_memory=True,
        )

        self.assertEqual([0, 12, 24, 36], [section["anchor_hours"] for section in sample_sections["sections"]])
        self.assertEqual("rows", sample_sections["sections"][0]["status"])
        self.assertEqual(1, int(sample_sections["sections"][0]["dataframe"].iloc[0]["NO"]))
        self.assertEqual(11, int(sample_sections["sections"][1]["dataframe"].iloc[0]["NO"]))
        self.assertEqual(21, int(sample_sections["sections"][2]["dataframe"].iloc[0]["NO"]))
        self.assertEqual("메모리 (인스펙터)", sample_sections["sections"][0]["dataframe"].columns[-1])
        self.assertEqual("message", sample_sections["sections"][3]["status"])
        self.assertIn("마지막 데이터는", sample_sections["sections"][3]["message"])

    def test_build_inspection_sample_sections_reports_no_data_when_filtered_range_is_empty(self):
        inspection_records = pd.DataFrame(
            {
                "Timestamp": pd.to_datetime(["2026-03-18 00:00:05"]),
                "SourceFile": ["sample.log"],
                "Inspection_No": [1],
                "Inspector_Model_Name": ["SAMPLE_MODEL_A"],
                "Inspector_Frame_Sec": [1.0],
                "Inspector_Total_Sec": [10.0],
                "Inspector_Total_Frames": [10],
                "Inspector_WorkingSet_KB": [1000.0],
                "Inspector_WorkingSet_MB": [1.0],
                "Inspector_WorkingSet_GB": [0.001],
                "System_Memory_Used_GB": [20.0],
                "System_Memory_Timestamp": pd.to_datetime(["2026-03-18 00:00:00"]),
            }
        )

        sample_sections = build_inspection_sample_sections(
            inspection_records,
            start_time="2026-03-19 00:00:00",
            end_time="2026-03-19 12:00:00",
        )

        self.assertEqual("message", sample_sections["sections"][0]["status"])
        self.assertEqual("데이터가 존재하지 않습니다.", sample_sections["sections"][0]["message"])


if __name__ == "__main__":
    unittest.main()
