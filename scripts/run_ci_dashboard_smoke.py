import sys
import tempfile
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from verify_dashboards import self_test


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        resource_path = temp_path / "resource_20260402.csv"
        process_path = temp_path / "process_20260402.csv"

        resource_df = pd.DataFrame(
            [
                {
                    "Timestamp": "2026-04-02 10:00:00",
                    "CPU_Avg(%)": 24.5,
                    "CPU_Peak(%)": 48.0,
                    "CPU_Temp(C)": 61.5,
                    "Mem_Used(GB)": 8.2,
                    "Mem_Usage_Avg(%)": 51.4,
                    "PhysicalMem(GB)": 16.0,
                    "OSTotalMem(GB)": 16.0,
                    "DiskTime_C:(%)": 31.0,
                    "DiskRead_C:(B/s)": 1048576.0,
                    "DiskWrite_C:(B/s)": 524288.0,
                }
            ]
        )
        process_df = pd.DataFrame(
            [
                {
                    "Timestamp": "2026-04-02 10:00:00",
                    "Top5_CPU(%)": "Inspector.exe:24.5 | python.exe:5.1",
                    "Top5_Memory_MB": "Inspector.exe:1536.0 | python.exe:512.0",
                    "Top5_Disk_Read_MBs": "Inspector.exe:12.5 | python.exe:2.0",
                    "Top5_Disk_Write_MBs": "Inspector.exe:5.0 | python.exe:1.0",
                    "Top5_Disk_IO_Global(MB/s)": "Inspector.exe:17.5 | python.exe:3.0",
                }
            ]
        )

        resource_df.to_csv(resource_path, index=False, encoding="utf-8-sig")
        process_df.to_csv(process_path, index=False, encoding="utf-8-sig")

        self_test([str(resource_path), str(process_path)])

    return 0


if __name__ == "__main__":
    sys.exit(main())
