# System Overview

Updated On: 2026-04-02  
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
| CPU 온도 프로브 | `collectors/cpu_temperature.py` | Dell 대상 장비에서는 DCM WMI를 우선, 일반 PC에서는 LibreHardwareMonitor, OpenHardwareMonitor, Thermal Zone 순으로 CPU 온도 센서 조회 |
| 샘플링 | `collectors/sampler.py` | CPU, CPU 온도, 메모리, 디스크, 프로세스 정보 수집 |
| 집계 | `collectors/aggregator.py` | 윈도우 평균/피크 계산, 5초 구간 최고 CPU 온도, Top N 포맷 생성 |
| 기록 | `collectors/writers.py` | 날짜별 CSV와 요약 로그 기록, 새 로그 컬럼 등장 시 헤더 재작성 |
| 데이터 로딩 | `data_loader.py` | `resource_*.csv`와 `process_*.csv` 병합 |
| AOI 로그 코어 | `inspector_logs/core.py` | AOI / Inspector 로그 경로 해석, `Model Open` 파싱, 검사 NO 재구성, 시스템 메모리 역매칭 |
| AOI 로그 CLI | `aoi_cli.py` | AOI 로그 요약 확인과 검사 결과 XLSX export Smoke Test |
| 검사 결과 Export UI | `dashboards/inspection_export.py` | 메인 화면에서 모델명, 검사 수, NO 범위, 미리보기, XLSX 다운로드 제공 |
| GUI 자동화 보조 | `tools/playwright-mcp/*` | 로컬 Playwright MCP 실행 래퍼와 WEB GUI 검증 Smoke Test |
| 파싱 | `parsers.py` | Top 5 문자열 컬럼 파싱 |
| 시각화 | `dashboards/*.py` | CPU, Memory, Storage, Custom 화면 렌더 |
| 엑셀 내보내기 | `excel_exporter.py` | 선택 컬럼을 `.xlsx`로 생성 |

## 현재 아키텍처 계약

- 대상 OS는 Windows 10/11 입니다.
- 로그 기본 경로는 `C:\SystemLogs` 입니다.
- 샘플링 주기는 1초, 집계 주기는 5초입니다.
- 리소스 데이터와 프로세스 데이터는 동일한 타임스탬프 경계에서 생성되므로 `data_loader.py`는 exact merge를 전제로 합니다.
- `resource_*.csv`와 `process_*.csv`의 컬럼 스키마는 대시보드와 직접 연결되어 있습니다.

## 데이터 흐름

```text
CpuTemperatureProbe -> Sampler (1s) -> WindowState accumulate -> Aggregator (5s max temp) -> resource/process CSV
CSV files -> data_loader.load_data() -> merged DataFrame -> dashboards/*.py
AOI log path -> inspector_logs.core.load_inspector_log_data() -> Inspector event DataFrame
Inspector event DataFrame + system monitor DataFrame -> inspector_logs.core.build_inspection_records() -> numbered inspection export rows
Inspector event DataFrame -> memory dashboard
```

## 주의해야 할 구조 포인트

- `data_loader.py`는 `pyarrow` 우선 읽기와 Parquet 캐시를 사용합니다.
- `collectors/sampler.py`는 PowerShell `Get-Partition` 결과를 파싱해 `PhysicalDriveX`를 실제 드라이브 문자로 정규화합니다.
- `cli.py start`와 `cli.py probe-temp`는 Dell Precision T5/T7 Tower 계열 장비를 감지하면 `collectors/dell_command_monitor.py`를 통해 DCM 설치/준비를 먼저 시도합니다.
- `collectors/cpu_temperature.py`는 Dell 대상 장비에서 `root\dcim\sysman/DCIM_NumericSensor`가 준비된 경우에만 이를 사용하고, 일반 PC나 DCM 미준비 상태에서는 `LibreHardwareMonitor`, `OpenHardwareMonitor`, `MSAcpi_ThermalZoneTemperature`를 순차 탐색합니다.
- Dell DCM 온도 센서는 `UnitModifier`가 실제 온도 스케일과 어긋나는 경우가 있어, CPU 온도처럼 그럴듯한 직접 읽기값이 있으면 이를 우선 사용하고 스케일 값은 fallback으로만 사용합니다.
- Dell Command Monitor 또는 하드웨어 모니터 계열에서 `CPU Package` 센서가 보이면 이를 메인 지표로 우선 사용하고, 없으면 CPU 관련 온도 센서 중 최고값을 선택합니다.
- `dashboards/storage.py`는 대용량 로그를 위해 차트 품질 모드를 제공합니다.
- `dashboards/cpu.py`는 `CPU_Temp(C)` 컬럼이 있을 때 사용률 복합 차트와 온도 전용 차트를 함께 표시합니다.
- `dashboards/memory.py`는 시스템 메모리와 AOI / Inspector 로그를 함께 보여주는 `Memory AND Inspector` 대시보드로 확장되었습니다.
- `dashboards/inspection_export.py`는 메인 화면에서 AOI 검사 결과를 `NO=1`부터 번호화해 XLSX로 내보냅니다.
- `verify_dashboards.py`는 브라우저 없이도 대시보드가 크래시하지 않는지 빠르게 확인하는 헤드리스 점검 스크립트입니다.
- `tools/playwright-mcp/`는 Codex Desktop이 로컬 Playwright MCP 서버를 통해 WEB 기반 GUI 검증을 수행할 수 있게 하는 보조 경로입니다.

## 문서 업데이트 트리거

- 샘플링 주기, 로그 스키마, 데이터 흐름, 모듈 경계가 바뀌면 이 문서를 업데이트합니다.
- 패키징 또는 실행 방식이 바뀌면 [RuntimeAndPackaging.md](RuntimeAndPackaging.md)도 같이 업데이트합니다.
