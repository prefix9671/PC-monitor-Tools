import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data_loader import (
    collect_available_timestamps,
    filter_dataframe_by_time_range,
    resolve_time_filter_range,
)


class TestTimeFiltering(unittest.TestCase):
    def setUp(self):
        self.single_day_df = pd.DataFrame(
            {
                "Timestamp": pd.to_datetime(
                    [
                        "2026-03-18 17:44:07",
                        "2026-03-18 17:44:18",
                        "2026-03-18 17:44:28",
                    ]
                ),
                "Value": [1, 2, 3],
            }
        )
        self.multi_day_df = pd.DataFrame(
            {
                "Timestamp": pd.to_datetime(
                    [
                        "2026-03-18 17:44:07",
                        "2026-03-18 17:44:18",
                        "2026-03-19 09:00:00",
                    ]
                )
            }
        )

    def test_collect_available_timestamps_merges_and_sorts(self):
        merged = collect_available_timestamps(
            self.single_day_df.iloc[[2, 0]],
            self.single_day_df.iloc[[1]],
        )

        self.assertEqual(
            [
                pd.Timestamp("2026-03-18 17:44:07"),
                pd.Timestamp("2026-03-18 17:44:18"),
                pd.Timestamp("2026-03-18 17:44:28"),
            ],
            list(merged),
        )

    def test_start_only_uses_next_available_sample_and_runs_to_end(self):
        resolved = resolve_time_filter_range(
            collect_available_timestamps(self.single_day_df),
            start_input="2026-03-18 17:44:08",
        )

        self.assertTrue(resolved["used_manual"])
        self.assertEqual(pd.Timestamp("2026-03-18 17:44:18"), resolved["resolved_start"])
        self.assertEqual(pd.Timestamp("2026-03-18 17:44:28"), resolved["resolved_end"])
        self.assertTrue(resolved["start_aligned"])

    def test_end_only_uses_previous_available_sample_and_runs_from_start(self):
        resolved = resolve_time_filter_range(
            collect_available_timestamps(self.single_day_df),
            end_input="2026-03-18 17:44:20",
        )

        self.assertTrue(resolved["used_manual"])
        self.assertEqual(pd.Timestamp("2026-03-18 17:44:07"), resolved["resolved_start"])
        self.assertEqual(pd.Timestamp("2026-03-18 17:44:18"), resolved["resolved_end"])
        self.assertTrue(resolved["end_aligned"])

    def test_time_only_input_works_for_single_day_logs(self):
        resolved = resolve_time_filter_range(
            collect_available_timestamps(self.single_day_df),
            start_input="17:44:18",
            end_input="17:44:28",
        )

        self.assertIsNone(resolved["error"])
        self.assertEqual(pd.Timestamp("2026-03-18 17:44:18"), resolved["resolved_start"])
        self.assertEqual(pd.Timestamp("2026-03-18 17:44:28"), resolved["resolved_end"])

    def test_time_only_multi_day_input_adds_note(self):
        resolved = resolve_time_filter_range(
            collect_available_timestamps(self.multi_day_df),
            start_input="17:44:18",
        )

        self.assertTrue(resolved["notes"])
        self.assertIn("first loaded date", resolved["notes"][0])

    def test_reversed_manual_range_returns_error(self):
        resolved = resolve_time_filter_range(
            collect_available_timestamps(self.single_day_df),
            start_input="2026-03-18 17:44:28",
            end_input="2026-03-18 17:44:07",
        )

        self.assertIsNotNone(resolved["error"])

    def test_filter_dataframe_by_time_range_returns_expected_rows(self):
        filtered = filter_dataframe_by_time_range(
            self.single_day_df,
            pd.Timestamp("2026-03-18 17:44:18"),
            pd.Timestamp("2026-03-18 17:44:28"),
        )

        self.assertEqual(2, len(filtered))
        self.assertEqual([2, 3], filtered["Value"].tolist())


if __name__ == "__main__":
    unittest.main()
