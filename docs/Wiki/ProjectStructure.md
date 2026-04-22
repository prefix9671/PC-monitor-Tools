# Project Structure

Updated On: 2026-04-21  
Status: Active

## 루트 구조

```text
PC-monitor-Tools/
├─ .streamlit/
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
| `tests/` | 수집 CLI, CPU 온도, AOI CLI, 시간 필터, Inspector 파싱과 12시간 샘플 XLSX 기본 검증 |
| `docs/` | 사람과 에이전트를 위한 기준 문서 |

## 주요 파일 역할

| 파일 | 설명 |
|---|---|
| `.streamlit/config.toml` | 개발 환경 Streamlit 업로드 한도 설정. AOI / 인스펙터 로그 1GB 제한 유지 |
| `app.py` | Streamlit 메인 앱 |
| `config.py` | 시스템 로그 경로, AOI 자동 로드 기본 경로 `C:\Inspector\shared\operation.txt`, 공용 색상/런타임 상수 |
| `aoi_cli.py` | AOI / Inspector 로그 요약 및 XLSX export CLI. 기본 결과 시트와 12시간 샘플 시트를 함께 생성 |
| `cli.py` | 수집기 시작과 CPU 온도 센서 진단 CLI |
| `run_app.py` | 패키징된 EXE의 단일 진입점. Streamlit 업로드 한도 1GB를 함께 고정 |
| `runtime_patches.py` | Streamlit/Tornado의 WebSocket disconnect, static asset flush `CancelledError`, gzip closed-file 종료 노이즈를 완화하는 런타임 패치 |
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
| `scripts/verify_docs_sync.py` | 코드 변경과 활성 문서 변경의 동기화 검사. Playwright 회귀 자체를 실행하지는 않지만, 관련 자동화 스크립트 변경 시 필요한 문서 갱신을 강제 |
| `scripts/prepare_lhm_bundle.py` | LibreHardwareMonitor 번들을 `.artifacts/vendor/lhm-bundle/`로 준비 |
| `scripts/check_git_cl.ps1` | 현재 저장소의 `git cl` 오류가 GitHub 원격 기준 비필수 상황인지, 실제 `git-cl` 실행 파일 누락인지 진단 |
| `scripts/publish_release_to_share.ps1` | 로컬 release bundle 을 QA 공유 폴더 `\\192.168.1.13\sqa\113_테스트 툴`에 복사하고, 현재 빌드를 제외한 이전 버전 폴더는 `old/`로 이동 |
| `scripts/capture_user_manual_assets.js` | headless Playwright로 유저 매뉴얼용 진입점/모니터링, 대시보드, AOI 업로드, XLSX 내보내기 스크린샷을 raw/approved 단계로 캡처 |
| `scripts/run_prebuild_regression.py` | 빌드 전 회귀 러너. 단위 테스트, AOI CLI, 대시보드 스모크, 문서 동기화, MkDocs, headless Playwright를 순차 실행 |
| `scripts/run_ci_dashboard_smoke.py` | 샘플 CSV로 대시보드 스모크 테스트 실행 |
| `scripts/verify_playwright_dashboards.js` | Playwright MCP로 실제 Streamlit 대시보드를 열고 스크린샷/콘솔 로그 아티팩트를 생성 |
| `scripts/verify_playwright_prebuild_regression.js` | repo-local bug 입력 파일을 업로드해 AOI 패널/시간 필터까지 포함한 headless Playwright 회귀를 수행 |
| `requirements.txt` | 런타임/빌드 의존성 목록. 일반 PC CPU 코어 온도 경로를 위해 `pythonnet` 포함 |
| `dashboards/inspection_export.py` | 메인 화면 AOI 검사 결과 미리보기와 인스펙터 메모리 옵션형 XLSX 다운로드. 현재 시간 필터 범위를 그대로 반영 |
| `inspector_logs/` | AOI / Inspector 로그 경로 해석, 이벤트 파싱, 원본 로그 재저장 payload / ZIP 생성, 원본 NO 유지형 시간 필터링, `merge_asof`용 `datetime64[ns]` 정밀도 정규화, 12시간 샘플 블록 생성 코어 |
| `tools/playwright-mcp/` | Codex용 Playwright MCP 로컬 패키지와 실행/검증 스크립트 |
| `parsers.py` | Top 5 문자열 파싱 |
| `excel_exporter.py` | 엑셀 내보내기 |
| `verify_dashboards.py` | 헤드리스 대시보드 자가 점검 |
| `build.bat` | 문서 사이트와 EXE 빌드, QA 공유 폴더 최신본 동기화 |

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
- `.artifacts/manual-assets/entry-monitoring/`과 `.artifacts/manual-assets/dashboards-inspector/`은 유저 매뉴얼용 실UI 캡처의 raw, approved, summary 산출물 경로입니다.
- `bug/` 아래의 로그는 수동 재현과 실데이터 검증용 입력으로 사용하며, 이번 AOI 12시간 샘플 검증 기준 로그는 `bug/operation_0319_north side grab.log` 입니다.
- `tests/test_inspector_logs.py`에는 AOI 이벤트 `datetime64[us]`와 시스템 메모리 `datetime64[ns]`가 섞여도 검사 결과 역매칭이 깨지지 않는 회귀 테스트가 포함됩니다.
- `scripts/verify_docs_sync.py`는 `bug/`, `tests/*.log`, `tools/playwright-mcp/*.png`, `tools/playwright-mcp/*-snapshot.md`, `tools/playwright-mcp/*.txt` 같은 로컬 검증 입력/산출물은 문서 동기화 대상 변경으로 취급하지 않습니다.
- `docs/images/manual/`에는 검수 완료 후 매뉴얼 본문에 실제로 포함되는 승인 스크린샷만 둡니다.
- 현재 문서 탐색 시작점은 `docs/ActiveDocs.md` 입니다.
- 더 상세한 아키텍처 설명은 [../Architecture/SystemOverview.md](../Architecture/SystemOverview.md)를 참고합니다.
