# Project Structure

Updated On: 2026-04-10  
Status: Active

## 루트 구조

```text
PC-monitor-Tools/
├─ aoi_cli.py
├─ app.py
├─ cli.py
├─ config.py
├─ data_loader.py
├─ excel_exporter.py
├─ inspector_logs/
├─ parsers.py
├─ run_app.py
├─ verify_dashboards.py
├─ collectors/
├─ dashboards/
├─ scripts/
├─ tools/
├─ tests/
├─ docs/
├─ build.bat
├─ start_monitor.bat
├─ Monitor.ps1
├─ monitor.spec
├─ mkdocs.yml
└─ requirements.txt
```

## 핵심 디렉토리

| 경로 | 설명 |
|---|---|
| `collectors/` | CPU 온도 프로브, 실물/가상 메모리 샘플링, 집계, 로그 기록을 담당하는 수집 엔진 |
| `dashboards/` | CPU, Memory, Storage, Custom 화면과 검사 결과 XLSX 내보내기 UI |
| `tools/` | 로컬 Playwright MCP 같은 보조 실행 도구 |
| `scripts/` | CI, 문서 동기화, 대시보드 스모크 자동화 |
| `tests/` | 수집 CLI, CPU 온도, AOI CLI, 시간 필터, Inspector 파싱 기본 검증 |
| `docs/` | 사람과 에이전트를 위한 기준 문서 |

## 주요 파일 역할

| 파일 | 설명 |
|---|---|
| `app.py` | Streamlit 메인 앱 |
| `aoi_cli.py` | AOI / Inspector 로그 요약 및 XLSX export CLI |
| `cli.py` | 수집기 시작과 CPU 온도 센서 진단 CLI |
| `run_app.py` | 패키징된 EXE의 단일 진입점 |
| `data_loader.py` | CSV 로딩, 캐시, exact merge |
| `collectors/dell_command_monitor.py` | Dell Precision T5/T7 Tower 계열의 DCM 감지, 다운로드, 무인 설치, namespace 준비 확인 |
| `collectors/cpu_temperature.py` | Dell DCM 경로와 일반 PC `LibreHardwareMonitorCoreMax` 워커 상태 파일을 오케스트레이션하고, 실패 시 OpenHardwareMonitor/PerfRaw/Thermal Zone fallback 으로 연결 |
| `collectors/libre_hardware_monitor.py` | EXE 동봉 `lhm-bundle/` 우선 탐색, 필요 시 공식 릴리스 다운로드/캐시, `pythonnet` 기반 DLL 로드, `CPU Core #n` 최고온도 추출 |
| `collectors/cpu_temperature_worker.py` | 일반 PC CPU 코어 최고온도를 30초마다 측정해 JSON 상태 파일로 남기는 백그라운드 워커 |
| `collectors/cpu_temperature_diagnostics.py` | 앱 하단 CPU 온도 테스트 버튼용 상세 진단 로그 생성기 |
| `collectors/sampler.py` | `psutil` 기반 1초 실물 메모리/페이지 파일 상태, CPU, 디스크, 프로세스 샘플 수집과 CPU 온도 워커 종료 정리 |
| `collectors/aggregator.py` | 5초 윈도우 기준 CPU/메모리/스왑/디스크 요약 행 생성 |
| `collectors/subprocess_utils.py` | PowerShell/설치기 표준출력의 안전 디코딩과 깨진 바이트 방어 |
| `scripts/doc_sync_rules.toml` | 에이전트와 CI가 공유하는 문서 동기화 규칙 표 |
| `scripts/verify_docs_sync.py` | 코드 변경과 활성 문서 변경의 동기화 검사 |
| `scripts/prepare_lhm_bundle.py` | LibreHardwareMonitor 번들을 `.artifacts/vendor/lhm-bundle/`로 준비 |
| `scripts/run_ci_dashboard_smoke.py` | 샘플 CSV로 대시보드 스모크 테스트 실행 |
| `scripts/verify_playwright_dashboards.js` | Playwright MCP로 실제 Streamlit 대시보드를 열고 스크린샷/콘솔 로그 아티팩트를 생성 |
| `requirements.txt` | 런타임/빌드 의존성 목록. 일반 PC CPU 코어 온도 경로를 위해 `pythonnet` 포함 |
| `dashboards/inspection_export.py` | 메인 화면 AOI 검사 결과 미리보기와 인스펙터 메모리 옵션형 XLSX 다운로드 |
| `inspector_logs/` | AOI / Inspector 로그 경로 해석과 이벤트 파싱 코어 |
| `tools/playwright-mcp/` | Codex용 Playwright MCP 로컬 패키지와 실행/검증 스크립트 |
| `parsers.py` | Top 5 문자열 파싱 |
| `excel_exporter.py` | 엑셀 내보내기 |
| `verify_dashboards.py` | 헤드리스 대시보드 자가 점검 |
| `build.bat` | 문서 사이트와 EXE 빌드 |

## `docs` 구조

```text
docs/
├─ ActiveDocs.md
├─ DocsHub.md
├─ index.md
├─ Architecture/
├─ Best Practices/
├─ Current Phase/
├─ Future/
├─ Wiki/
├─ images/
└─ stylesheets/
```

## 참고 메모

- `build/`, `dist/`, `site/`는 생성 산출물이므로 구조 설명의 기준이 아닙니다.
- `.artifacts/`는 수동 빌드와 CI가 공통으로 사용하는 생성 산출물 경로입니다.
- 현재 문서 탐색 시작점은 `docs/ActiveDocs.md` 입니다.
- 더 상세한 아키텍처 설명은 [../Architecture/SystemOverview.md](../Architecture/SystemOverview.md)를 참고합니다.
