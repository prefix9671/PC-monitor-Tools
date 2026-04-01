import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dashboards.inspection_export import COLOR_PRESET_MAP, _build_preview_chart, _hex_to_rgba


class TestInspectionExportPanel(unittest.TestCase):
    def setUp(self):
        self.preview_df = pd.DataFrame(
            {
                "측정시간": pd.to_datetime(["2026-03-18 17:44:07", "2026-03-18 17:44:12"]),
                "NO": [1, 2],
                "Frame": [1.19, 1.50],
                "Total": [38.13, 40.00],
                "Memory (인스펙터)": [45.288, 47.684],
                "Memory (시스템)": [28.5, 29.0],
            }
        )

    def test_hex_to_rgba(self):
        self.assertEqual("rgba(58, 134, 255, 0.28)", _hex_to_rgba("#3A86FF", 0.28))

    def test_named_palette_count_stays_within_requested_range(self):
        self.assertLessEqual(len(COLOR_PRESET_MAP), 36)

    def test_build_preview_chart_line_mode(self):
        fig = _build_preview_chart(
            preview_df=self.preview_df,
            chart_type="선 + 마커",
            selected_metrics=["Frame", "Total", "Memory (인스펙터)", "Memory (시스템)"],
            metric_colors={
                "Frame": COLOR_PRESET_MAP["플럼 바이올렛"],
                "Total": COLOR_PRESET_MAP["선셋 오렌지"],
                "Memory (인스펙터)": COLOR_PRESET_MAP["에메랄드"],
                "Memory (시스템)": COLOR_PRESET_MAP["코발트 블루"],
            },
            opacity=0.85,
        )

        self.assertEqual(4, len(fig.data))
        self.assertTrue(all(trace.type == "scatter" for trace in fig.data))
        self.assertEqual("검사 시간 (sec)", fig.layout.yaxis.title.text)
        self.assertEqual("메모리 (GB)", fig.layout.yaxis2.title.text)

    def test_build_preview_chart_bar_mode(self):
        fig = _build_preview_chart(
            preview_df=self.preview_df,
            chart_type="막대",
            selected_metrics=["Frame", "Memory (시스템)"],
            metric_colors={
                "Frame": COLOR_PRESET_MAP["플럼 바이올렛"],
                "Memory (시스템)": COLOR_PRESET_MAP["코발트 블루"],
            },
            opacity=0.55,
        )

        self.assertEqual(2, len(fig.data))
        self.assertTrue(all(trace.type == "bar" for trace in fig.data))


if __name__ == "__main__":
    unittest.main()
