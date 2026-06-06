# System Overview

Updated On: 2026-06-05
Status: Active

## 시스템 개요

`PC-monitor-Tools`는 Windows 시스템 리소스를 수집하고, 그 결과를 Streamlit 대시보드로 분석하는 도구입니다. 현재 구현은 `psutil` 기반의 파이썬 네이티브 수집기와 `Plotly` 기반 대시보드를 중심으로 구성되어 있습니다.

## 핵심 런타임 경로

1. 수집기 진입: `cli.py` -> `collectors.core.MonitorEngine`
2. 샘플링: `collectors.sampler.Sampler`
3. 집계: `collectors.aggregator.Aggregator`
4. 기록: `collectors.writers.OutputsWriter`
5. 분석 UI: `app.py`
6. 패키징된 단일 진입점: `run_app.py`
7. AOI 로그 파싱 코어: `inspector_logs/core.py`
8. AOI 로그 CLI 요약 / XLSX 내보내기 도구: `aoi_cli.py`
9. 검사 결과 XLSX 메인 화면 패널: `dashboards/inspection_export.py`

## 모듈 책임

| 영역 | 파일 | 역할 |
|---|---|---|
| 대시보드 엔트리 | `app.py` | 로그 선택, 시간 필터, KPI, 탭 라우팅 |
| 수집 CLI | `cli.py` | 수집기 시작 전 Dell 대상 장비의 DCM 부트스트랩과 CPU 온도 센서 진단 파라미터 처리 |
| 수집 루프 | `collectors/core.py` | 1초 샘플링과 5초 집계 주기 제어 |
| DCM 부트스트랩 | `collectors/dell_command_monitor.py` | Dell Precision T5/T7 Tower 계열이면 DCM 설치/준비 상태를 확인하고 필요 시 공식 패키지를 자동 설치 |
| CPU 온도 프로브 | `collectors/cpu_temperature.py` | Dell 대상 장비에서는 DCM WMI를 우선, 일반 PC에서는 `pythonnet + LibreHardwareMonitorLib.dll` 워커가 30초마다 `CPU Core #n` 최고온도를 JSON 상태 파일로 갱신하고 실패 시 OpenHardwareMonitor, PerfRaw Thermal Zone, Thermal Zone 순으로 fallback |
| LHM 브리지 | `collectors/libre_hardware_monitor.py` | EXE에 동봉된 `lhm-bundle/` 또는 로컬 vendor 번들을 우선 찾고, 없을 때만 캐시/다운로드 경로로 내려받아 `pythonnet`으로 `LibreHardwareMonitorLib.dll`을 로드 |
| CPU 온도 워커 | `collectors/cpu_temperature_worker.py` | 일반 PC용 백그라운드 워커로 30초마다 CPU 코어 최고온도를 측정해 로컬 JSON 상태 파일에 기록 |
| CPU 온도 진단 | `collectors/cpu_temperature_diagnostics.py` | 앱 하단 테스트 버튼과 연동되어 현재 워커 상태, provider별 raw 조회 결과, 선택된 센서를 상세 로그로 남김 |
| 샘플링 | `collectors/sampler.py` | CPU, CPU 온도, 실물 메모리, 페이지 파일 기반 가상 메모리, 디스크, 프로세스 정보 수집 |
| WMI 직접 조회 | `collectors/wmi_query.py` | PowerShell 없이 `pythonnet + System.Management`로 WMI provider를 조회해 Dell DCM, Thermal Zone, 물리 메모리, 드라이브 매핑을 유지 |
| subprocess 디코딩 보호 | `collectors/subprocess_utils.py` | Dell 설치기 같은 외부 프로세스 stdout/stderr를 바이트 기준으로 안전 디코딩해 메모리 압박이나 비정상 출력에서도 `UnicodeDecodeError` 없이 수집 경로를 유지 |
| 집계 | `collectors/aggregator.py` | 윈도우 평균/피크 계산, 5초 구간 최고 CPU 온도, 스왑 최고값, Top N 포맷 생성 |
| 기록 | `collectors/writers.py` | 날짜별 CSV와 요약 로그 기록, 새 로그 컬럼 등장 시 헤더 재작성 |
| 데이터 로딩 | `data_loader.py` | `resource_*.csv`와 `process_*.csv` 병합 |
| 상단 시스템 요약 | `dashboards/system_summary.py` | 시간 필터 적용 후 시스템 로그 기준 CPU 사용량/온도와 RAM 사용률 평균/최고 요약 카드 계산 및 렌더 |
| AOI 로그 코어 | `inspector_logs/core.py` | AOI / Inspector 로그 경로 해석, `Model Open` 파싱, 검사 NO 재구성, 시스템 메모리 역매칭, `merge_asof` 전 타임스탬프 정밀도 `datetime64[ns]` 정규화, 시간 필터 기준 검사 결과 뷰와 12시간 샘플 블록 생성 |
| AOI 로그 CLI | `aoi_cli.py` | AOI 로그 요약 확인과 검사 결과 XLSX export Smoke Test |
| 검사 결과 Export UI | `dashboards/inspection_export.py` | 메인 화면에서 현재 시간 필터 기준 모델명, 검사 수, NO 범위, `NO/Frame/Total/메모리 (시스템)/메모리 (인스펙터)` 미리보기와 옵션형 XLSX 다운로드 제공 |
| GUI 자동화 보조 | `tools/playwright-mcp/*` | 로컬 Playwright MCP 실행 래퍼와 WEB GUI 검증 Smoke Test |
| 파싱 | `parsers.py` | Top 5 문자열 컬럼 파싱 |
| 시각화 | `dashboards/*.py` | CPU, Memory, Storage, Custom 화면 렌더 |
| 엑셀 내보내기 | `excel_exporter.py` | 선택 컬럼을 `.xlsx`로 생성 |
| Streamlit 업로드 설정 | `.streamlit/config.toml` | 개발 환경 AOI / 인스펙터 업로드 한도를 1GB로 고정 |
| 기본 경로 설정 | `config.py` | 시스템 로그 경로와 AOI / 인스펙터 기본 경로 `C:\Inspector\shared\operation.txt`를 보관 |

## 현재 아키텍처 계약

- 대상 OS는 Windows 10/11 입니다.
- 로그 기본 경로는 `C:\SystemLogs` 입니다.
- 샘플링 주기는 1초, 집계 주기는 5초입니다.
- 리소스 데이터와 프로세스 데이터는 동일한 타임스탬프 경계에서 생성되므로 `data_loader.py`는 exact merge를 전제로 합니다.
- `resource_*.csv`와 `process_*.csv`의 컬럼 스키마는 대시보드와 직접 연결되어 있습니다.
- `resource_*.csv`는 기존 컬럼을 유지한 채 `Swap_Used(GB)`, `Swap_Total(GB)`, `Swap_Usage(%)`를 추가할 수 있으며, 오래된 로그는 이 컬럼이 없어도 계속 로드됩니다.

## 데이터 흐름

```text
LibreHardwareMonitor worker (30s core max) -> JSON state -> CpuTemperatureProbe -> Sampler (1s) -> WindowState accumulate -> Aggregator (5s max temp) -> resource/process CSV
CSV files -> data_loader.load_data() -> merged DataFrame -> dashboards/*.py
AOI log path -> inspector_logs.core.load_inspector_log_data() -> Inspector event DataFrame
Inspector event DataFrame + system monitor DataFrame -> inspector_logs.core.build_inspection_records() -> numbered inspection export rows
numbered inspection export rows + current time filter -> inspector_logs.core.filter/build sample helpers -> Inspection_Results + Inspection_12h_Samples workbook
Inspector event DataFrame -> memory dashboard
```

## 주의해야 할 구조 포인트

- `data_loader.py`는 `pyarrow` 우선 읽기와 Parquet 캐시를 사용합니다.
- `collectors/wmi_query.py`는 `pythonnet`의 `System.Management`를 통해 WMI를 직접 조회하므로, 현장 PC에서 Windows PowerShell 5.1/7이 실행되지 않아도 수집기의 WMI fallback 경로를 유지합니다.
- `collectors/sampler.py`는 `Win32_LogicalDiskToPartition` WMI 관계를 직접 읽어 `PhysicalDriveX`를 실제 드라이브 문자로 정규화합니다.
- `collectors/sampler.py`는 Windows 10/11에서 `psutil.swap_memory()`를 사용해 페이지 파일 기반 가상 메모리 상태를 읽고, `Swap_Used(GB)`, `Swap_Total(GB)`, `Swap_Usage(%)`로 기록합니다.
- `collectors/subprocess_utils.py`는 Dell 설치기 같은 외부 프로세스 표준출력을 `text=True` 대신 바이트로 받은 뒤 다중 인코딩 후보와 `errors="replace"` fallback으로 디코딩해 `_readerthread`의 `UnicodeDecodeError`를 방지합니다.
- `cli.py start`와 `cli.py probe-temp`는 Dell Precision T5/T7 Tower 계열 장비를 감지하면 `collectors/dell_command_monitor.py`를 통해 DCM 설치/준비를 먼저 시도합니다.
- `collectors/dell_command_monitor.py`는 `Win32_ComputerSystem`과 `root\dcim\sysman` namespace 확인도 PowerShell 없이 WMI 직접 조회로 수행합니다.
- `collectors/cpu_temperature.py`는 Dell 대상 장비에서 `root\dcim\sysman/DCIM_NumericSensor`가 준비된 경우에만 이를 WMI 직접 조회로 사용하고, 일반 PC에서는 `collectors/cpu_temperature_worker.py`가 갱신한 JSON 상태를 우선 읽습니다.
- 일반 PC용 워커는 먼저 EXE 내부 `_MEIPASS\lhm-bundle` 또는 EXE 옆 `lhm-bundle\`을 확인하고, 그 안에 동봉된 LibreHardwareMonitor 번들을 우선 사용합니다.
- 동봉된 번들이 없을 때만 `collectors/libre_hardware_monitor.py`가 LibreHardwareMonitor 최신 공식 릴리스를 `LOCALAPPDATA\PC-monitor-Tools\lhm-cache\`에 캐시하고, `pythonnet`으로 `LibreHardwareMonitorLib.dll`을 로드합니다.
- 일반 PC CPU 온도는 LibreHardwareMonitor `Temperature` 센서 중 `CPU Core #n` 형태의 물리 코어 센서만 대상으로 삼고, `Core Max`, `Core Average`, `Distance to TjMax`, `CPU Package`는 메인 지표에서 제외한 뒤 최고값 하나만 사용합니다.
- 일반 PC 워커 상태가 비어 있거나 실패하면 PowerShell 없이 WMI 직접 조회로 `OpenHardwareMonitor`, `Win32_PerfRawData_Counters_ThermalZoneInformation`, `MSAcpi_ThermalZoneTemperature`를 순차 fallback 합니다.
- `app.py` 하단의 `CPU 온도 테스트 실행 및 로그 저장` 버튼은 현재 worker 상태, local bundle 발견 여부, force refresh 결과, provider별 raw record preview를 `C:\SystemLogs\cpu_temp_diagnostic_*.log`와 `cpu_temp_diagnostic_latest.log`로 저장합니다.
- `app.py` 하단의 `CPU 온도 테스트 실행 및 로그 저장` 버튼은 `collectors/cpu_temperature_diagnostics.py`를 호출해 현재 worker 상태, force refresh 결과, provider별 raw record preview를 `C:\SystemLogs\cpu_temp_diagnostic_*.log`와 `cpu_temp_diagnostic_latest.log`로 저장합니다.
- `Win32_PerfRawData_Counters_ThermalZoneInformation` 경로는 어드벤텍 IPC 같은 산업용 PC에서 노출되는 Kelvin 기반 온도 값을 읽고, `353 -> 79.85°C`, `3530 -> 79.85°C` 규칙으로 섭씨로 환산합니다.
- PerfRaw / Thermal Zone selector 는 `0` 이하 값을 버리고, `_Total` 같은 집계 레코드보다 개별 zone 을 먼저 평가한 뒤 그 안에서 가장 높은 유효 온도를 선택합니다.
- `cli.py probe-temp`는 현재 선택된 provider 이름뿐 아니라 가능할 때 `CPU Core #n` 또는 `Name`/`InstanceName` 기반 센서 식별 문자열도 함께 출력합니다.
- Dell DCM 온도 센서는 `UnitModifier`가 실제 온도 스케일과 어긋나는 경우가 있어, CPU 온도처럼 그럴듯한 직접 읽기값이 있으면 이를 우선 사용하고 스케일 값은 fallback으로만 사용합니다.
- Dell Command Monitor 또는 하드웨어 모니터 계열에서 `CPU Package` 센서가 보이면 이를 메인 지표로 우선 사용하고, 없으면 CPU 관련 온도 센서 중 최고값을 선택합니다.
- `dashboards/storage.py`는 대용량 로그를 위해 차트 품질 모드를 제공합니다.
- `dashboards/cpu.py`는 `CPU_Temp(C)` 컬럼이 있을 때 사용률 복합 차트와 온도 전용 차트를 함께 표시합니다.
- `dashboards/memory.py`는 시스템 메모리와 AOI / Inspector 로그를 함께 보여주는 `Memory AND Inspector` 대시보드로 확장되었고, 스왑 값이 0이면 현재 스왑된 메모리가 없다는 상태 메시지를 함께 표시합니다.
- `dashboards/inspection_export.py`는 메인 화면에서 AOI 검사 결과를 원본 `NO` 유지 기준으로 보여주고, 현재 시간 필터 범위 안에서 미리보기/XLSX를 계산합니다.
- `load_inspector_log_data()`와 `load_inspector_log_data_from_uploads()`는 큰 단일 로그는 청크 단위, 여러 로그는 파일 단위 스레드 병렬화를 사용해 AOI 파싱 시간을 줄입니다.
- Streamlit 대시보드 업로드 경로는 `.streamlit/config.toml`과 `run_app.py --server.maxUploadSize=1024`를 함께 사용해 개발/EXE 모두 1GB 업로드 한도를 유지합니다.
- `app.py`는 사이드바 AOI 구역이 열릴 때 기본 경로 `C:\Inspector\shared\operation.txt`를 자동으로 확인해, 파일이 있으면 업로드 payload와 같은 경로로 자동 업로드 처리하고 없으면 조용히 대기합니다.
- 수동 AOI 경로 입력 UI는 제거되었고, 대신 `인스팩터 로그 다른 이름으로 저장` 버튼이 현재 불러온 원본 TXT / LOG를 그대로 다시 저장하게 합니다.
- `inspector_logs/core.py`는 AOI 이벤트와 시스템 메모리 로그를 `merge_asof` 하기 전에 양쪽 `Timestamp`를 모두 `datetime64[ns]`로 맞춰, Python 3.13 / 최신 pandas 조합에서도 `datetime64[us]` 대 `datetime64[ns]` 타입 충돌 없이 동작하도록 유지합니다.
- 검사 결과 XLSX는 기본 `Inspection_Results` 시트 외에 `Inspection_12h_Samples` 시트를 추가로 만들고, 시간 필터 시작 시각 기준 `+0h, +12h, ... +144h`마다 첫 10개를 블록형으로 적습니다.
- `Inspection_12h_Samples`는 각 기준점 이후 현재 시간 필터 종료 시각 이내에서 찾은 첫 10개를 사용하며, 데이터가 없으면 마지막 데이터 시각 기준 안내 문구 또는 `데이터가 존재하지 않습니다`를 남깁니다.
- `verify_dashboards.py`는 브라우저 없이도 대시보드가 크래시하지 않는지 빠르게 확인하는 헤드리스 점검 스크립트입니다.
- `tools/playwright-mcp/`는 Codex Desktop이 로컬 Playwright MCP 서버를 통해 WEB 기반 GUI 검증을 수행할 수 있게 하는 보조 경로입니다.
- `runtime_patches.py`는 브라우저 종료나 headless 검증 종료 시 Tornado가 남길 수 있는 WebSocket disconnect, static asset flush `CancelledError`, gzip closed-file 종료 노이즈를 런타임에서 흡수합니다.

## 문서 업데이트 트리거

- 샘플링 주기, 로그 스키마, 데이터 흐름, 모듈 경계가 바뀌면 이 문서를 업데이트합니다.
- 패키징 또는 실행 방식이 바뀌면 [RuntimeAndPackaging.md](RuntimeAndPackaging.md)도 같이 업데이트합니다.
