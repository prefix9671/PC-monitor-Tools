import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(REPO_ROOT))

from collectors.sampler import Sampler


class TestSamplerWmiFallbacks(unittest.TestCase):
    @patch("collectors.sampler.CpuTemperatureProbe")
    @patch("collectors.sampler.query_wmi_records")
    def test_physical_memory_uses_wmi_capacity_sum_without_powershell(self, query_mock, _probe_mock):
        def fake_query(spec, *args, **kwargs):
            if spec.class_name == "Win32_LogicalDiskToPartition":
                return []
            if spec.class_name == "Win32_PhysicalMemory":
                return [{"Capacity": str(8 * 1024**3)}, {"Capacity": str(16 * 1024**3)}]
            return []

        query_mock.side_effect = fake_query

        sampler = Sampler()

        self.assertEqual(24.0, sampler.phys_mem_gb)
        queried_classes = [call.args[0].class_name for call in query_mock.call_args_list]
        self.assertIn("Win32_PhysicalMemory", queried_classes)
        self.assertNotIn("Get-CimInstance", str(query_mock.call_args_list))

    @patch("collectors.sampler.CpuTemperatureProbe")
    @patch("collectors.sampler.query_wmi_records")
    def test_drive_mapping_uses_logical_disk_partition_wmi_links(self, query_mock, _probe_mock):
        query_mock.return_value = [
            {
                "Antecedent": r'\\HOST\root\cimv2:Win32_DiskPartition.DeviceID="Disk #0, Partition #1"',
                "Dependent": r'\\HOST\root\cimv2:Win32_LogicalDisk.DeviceID="C:"',
            },
            {
                "Antecedent": r'\\HOST\root\cimv2:Win32_DiskPartition.DeviceID="Disk #0, Partition #2"',
                "Dependent": r'\\HOST\root\cimv2:Win32_LogicalDisk.DeviceID="D:"',
            },
            {
                "Antecedent": r'\\HOST\root\cimv2:Win32_DiskPartition.DeviceID="Disk #1, Partition #1"',
                "Dependent": r'\\HOST\root\cimv2:Win32_LogicalDisk.DeviceID="E:"',
            },
        ]

        sampler = Sampler()

        self.assertEqual("C:,D:", sampler.drive_mapping["PhysicalDrive0"])
        self.assertEqual("E:", sampler.drive_mapping["PhysicalDrive1"])


if __name__ == "__main__":
    unittest.main()
