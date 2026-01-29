# System Resource Monitor (Windows 11)

A comprehensive system resource monitoring tool for Windows 11 workstations, featuring a high-performance PowerShell data collector and an interactive Streamlit dashboard.

## Features

- **Hybrid GPU Monitoring**: Simultaneously monitors NVIDIA Discrete GPUs (via `nvidia-smi`) and Intel/AMD Integrated GPUs (via Performance Counters).
- **Comprehensive Metrics**:
    - **CPU**: Usage (%) and Temperature (°C).
    - **Memory**: Physical Usage, Swap Usage, and Top Consumer Processes.
    - **Storage**: Disk I/O (Read/Write) and Usage for multiple drives.
- **Interactive Dashboard**:
    - Built with [Streamlit](https://streamlit.io/) and [Plotly](https://plotly.com/).
    - Modular design for easy extensibility.
    - Multi-file and folder log loading support.
    - **Advanced Memory Analysis**: TOP 3 peak usage tracking and selectable TOP 5 process trend analysis over time.
    - **Dynamic Sizing**: Automatically calculates system-wide total memory from log data.
- **Admin Execution**: Built-in support to launch the PowerShell collector with Administrator privileges directly from the UI.
- **Configurable**: Adjustable monitoring interval (down to 2s) and target drives (e.g., C:, D:, E:).

## Project Structure

```
sys_resource_monitor/
├── app.py                  # Main Streamlit Application
├── Monitor.ps1             # PowerShell Data Collector Script
├── config.py               # Configuration constants
├── data_loader.py          # CSV Data Loading & Caching
├── parsers.py              # Log Parsing Utilities
├── run_app.py              # PyInstaller Entry Point
├── monitor.spec            # PyInstaller Build Specification
├── requirements.txt        # Python Dependencies
└── dashboards/             # Dashboard Modules
    ├── cpu.py
    ├── memory.py
    ├── storage.py
    └── custom.py
```

자세한 프로젝트 구조 및 설명은 [docs/project_structure.md](docs/project_structure.md) 파일을 참고하세요.

## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/YOUR_USERNAME/sys_resource_monitor.git
    cd sys_resource_monitor
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### Running the Dashboard
```bash
python -m streamlit run app.py
```

1.  The dashboard will open in your default browser.
2.  Use the **Control Panel** in the sidebar to configure monitoring settings (Interval, Drives).
3.  Click **"Start Monitor (Admin)"** to launch the PowerShell collector.
4.  Logs will be saved to `C:\SystemLogs` and can be loaded via the **Log File Selection** menu.

### Building Executable (EXE)
To bundle the application into a single executable file:

```bash
pyinstaller monitor.spec
```
The output file will be located in the `dist` folder.

## Requirements
- Windows 10/11
- Python 3.8+
- Administrator privileges (for full hardware monitoring access)
