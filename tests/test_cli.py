import os
import sys
import unittest
import tempfile
import pandas as pd
from unittest.mock import patch

# Fix path to import cli and core
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from cli import main

class TestCLI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = self.temp_dir.name
        
    def tearDown(self):
        self.temp_dir.cleanup()

    def test_cli_start_collects_logs(self):
        """
        Verify that calling the CLI with start and specific iterations
        successfully initializes the core and writes actual CSVs safely to a temp dir.
        """
        out_dir = self.output_dir
        
        # Test arguments: 1s sampling, 2s window, 3 iterations (so at least 1 file write occurs)
        test_args = ['cli.py', 'start', '--out-dir', out_dir, '--interval', '1', '--window', '2', '--iterations', '3']
        
        with (
            patch("cli.ensure_dcm_ready") as ensure_dcm_ready,
            patch("collectors.sampler.CpuTemperatureProbe") as probe_cls,
            patch.object(sys, 'argv', test_args),
        ):
            ensure_dcm_ready.return_value.message = ""
            probe_cls.return_value.read_celsius.return_value = 61.2
            main()
            
        # Check if files were created in out_dir
        files = os.listdir(out_dir)
        resource_files = [f for f in files if f.startswith('resource_')]
        process_files = [f for f in files if f.startswith('process_')]
        
        self.assertTrue(len(resource_files) >= 1, "Resource CSV should be created")
        self.assertTrue(len(process_files) >= 1, "Process CSV should be created")
        
        # Verify the contents are valid CSVs
        res_df = pd.read_csv(os.path.join(out_dir, resource_files[0]))
        proc_df = pd.read_csv(os.path.join(out_dir, process_files[0]))
        
        self.assertIn('Timestamp', res_df.columns)
        self.assertIn('CPU_Avg(%)', res_df.columns)
        self.assertIn('CPU_Temp(C)', res_df.columns)
        self.assertIn('Swap_Used(GB)', res_df.columns)
        self.assertIn('Swap_Total(GB)', res_df.columns)
        self.assertIn('Swap_Usage(%)', res_df.columns)
        self.assertIn('Timestamp', proc_df.columns)
        self.assertIn('Top5_CPU(%)', proc_df.columns)
        self.assertTrue(len(res_df) >= 1, "Resource dataframe should have data")

if __name__ == '__main__':
    unittest.main()
