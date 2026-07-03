# Changelog

Updated On: 2026-07-03
Status: Active

## [2026-07-03] - PawnIO 설치기 동봉과 설치 경로 추가

### 변경 사항

- LibreHardwareMonitor 0.9.6 계열에서 CPU 코어 온도 수집에 필요한 PawnIO 설치기를 `pawnio-bundle/PawnIO_setup.exe`로 배포본에 함께 포함하도록 했습니다.
- `collectors/pawnio_package.py`와 `scripts/prepare_pawnio_bundle.py`를 추가해 공식 PawnIO 릴리스 설치기를 다운로드/해시 검증하고 `.artifacts/vendor/pawnio-bundle/`로 준비합니다.
- `SystemResourceMonitor*.exe install-pawnio` CLI와 `install_pawnio.bat`를 추가해 릴리스 폴더에서 관리자 권한 설치를 실행할 수 있게 했습니다.
- `start_monitor.bat`는 수집기 실행 전 PawnIO 설치 여부를 확인하고, 미설치 상태면 사용자에게 동봉 설치기를 실행할지 묻습니다.
- PawnIO 미설치 안내에 `install_pawnio.bat`, `SystemResourceMonitor*.exe install-pawnio`, `pawnio-bundle/PawnIO_setup.exe` 경로를 함께 표시해 현장에서 수동 설치 파일을 바로 찾을 수 있게 했습니다.
- CPU 온도 진단 로그에 PawnIO 설치 상태, 동봉 설치기 경로, manifest 정보를 남기도록 보강했습니다.

## [2026-06-05] - 모니터링 시작 버튼 PowerShell 의존성 제거

### 변경 사항

- Streamlit `모니터링 시작` 버튼이 PowerShell `Start-Process -Verb RunAs`를 호출하지 않고, `collector_launcher.py`의 Windows ShellExecute `runas` 경로로 관리자 권한 수집기 실행을 요청하도록 바꿨습니다.
- 이미 관리자 권한으로 앱이 실행 중이면 새 콘솔에서 수집기를 직접 시작하고, 일반 권한이면 UAC 권한 상승 요청을 보내도록 분기했습니다.
- PowerShell이 손상된 현장 PC에서도 버튼 경로가 셸 런타임에 묶이지 않도록 했고, 실패 시 `액세스 거부`, 파일 차단, 보안 정책, 권한 문제를 UI에 더 명확히 표시하도록 정리했습니다.
- `collectors/wmi_query.py`를 추가해 Dell DCM, OpenHardwareMonitor, PerfRaw Thermal Zone, MSAcpi Thermal Zone, 물리 메모리, 드라이브 문자 매핑을 PowerShell `Get-CimInstance` / `Get-Partition` 없이 WMI 직접 조회로 수행하도록 바꿨습니다.
- 빌드 전 문서 동기화 검사가 로컬 Playwright MCP 실행 산출물(`.playwright-mcp/**`, `console-errors.md`)을 코드 변경으로 오인하지 않도록 ignore 규칙을 보강했습니다.

## [2026-05-14] - AOI 시간 필터 NO 범위 재설정 보강

### 변경 사항

- `검사 결과 XLSX 내보내기` 패널에서 시간 필터가 바뀌면 `시작 NO` / `종료 NO`가 새 필터에 포함된 전체 검사 범위로 자동 재설정되도록 보강했습니다.
- 같은 시간 필터 안에서 사용자가 직접 줄인 NO 범위는 유지하되, 새 시간 조건에서는 이전 선택값 때문에 1건만 미리보기/다운로드되는 혼선을 막았습니다.
- prebuild 회귀에 최소 fixture `tests\fixtures\inspector_time_filter_range_regression.log` 기준 `2026-05-13 15:00:00 -> 16:44:59`, `NO 2 -> 4`, 3건 검증 단계를 추가해 같은 문제가 다시 들어오면 빌드 전 단계에서 실패하도록 했습니다.

## [2026-05-14] - GitHub Actions CI 의존성 보강

### 변경 사항

- `runtime_patches.py` 테스트가 직접 import 하는 `tornado`를 `requirements.txt`에 명시해, GitHub Actions의 깨끗한 Python 3.13 runner 에서도 unit test discovery 가 실패하지 않도록 보강했습니다.
- `actions/checkout`과 `actions/setup-python`을 Node.js 24 런타임 기반 major 버전으로 올려 Node.js 20 deprecation 경고를 제거할 수 있게 정리했습니다.

## [2026-05-14] - 상단 시스템 성능 요약 카드 개선

### 변경 사항

- 기존 상단 메모리 중심 KPI를 시스템 로그 기준 `CPU 사용량 평균/최고`, `CPU 온도 평균/최고`, `RAM 사용량 평균/최대` 카드로 교체했습니다.
- 시스템 로그만 있어도 새 요약 카드를 표시하고, 인스펙터 로그가 함께 로드된 경우에도 같은 시스템 로그 범위를 기준으로 계산합니다.
- 시간 필터가 적용되면 필터로 줄어든 `df` 기준으로 평균/최고/최대값을 다시 계산하도록 정리했습니다.

## [2026-04-21] - AOI 기본 경로 자동 로드와 원본 재저장 버튼 추가

### 변경 사항

- AOI / 인스펙터 로그는 사이드바 렌더링 시 기본 경로 `C:\Inspector\shared\operation.txt`를 자동으로 먼저 확인하고, 파일이 있으면 사용자가 업로드한 것과 같은 payload 경로로 자동 업로드 처리하며, 파일이 없으면 경고 없이 조용히 대기하도록 바꿨습니다.
- 기존 `고급: 경로로 AOI / 인스펙터 로그 불러오기` UI는 제거하고, 대신 현재 불러온 원본 TXT / LOG를 그대로 다시 저장하는 `인스팩터 로그 다른 이름으로 저장` 버튼을 추가했습니다.
- 원본 로그 저장은 한 파일이면 원래 파일명 그대로, 여러 파일이면 ZIP 묶음으로 저장되도록 정리했습니다.
- 추가로 `runtime_patches.py`가 브라우저 종료 시 `WebSocketClosedError`뿐 아니라 static asset flush `CancelledError`와 `gzip ... I/O operation on closed file` 종료 노이즈도 함께 흡수하도록 보강했습니다.

## [2026-04-14] - AOI 1GB 업로드 브랜치 main 반영

### 변경 사항

- 별도 브랜치에 남아 있던 AOI / 인스펙터 1GB 업로드 설정을 `main`에 반영해, 개발 환경은 `.streamlit/config.toml`, EXE 경로는 `run_app.py --server.maxUploadSize=1024`로 같은 한도를 유지하도록 정리했습니다.
- `inspector_logs/core.py`는 큰 단일 로그에 청크 단위 스레드 병렬화, 여러 로그 입력에 파일 단위 스레드 병렬화를 사용하도록 복원해 장시간 운전 로그 파싱 경로를 `main`으로 통합했습니다.
- 관련 회귀 테스트와 운영 문서를 함께 갱신하고, 병합 전 `main` 기준 회귀 검증으로 동작 여부를 다시 확인했습니다.

## [2026-04-13] - 빌드 산출물 QA 공유 폴더 동시 배포

### 변경 사항

- `build.bat`가 로컬 `.artifacts/releases/<빌드명>/` 생성 뒤 `scripts/publish_release_to_share.ps1`를 호출해 QA 공유 폴더 `\\192.168.1.13\sqa\113_테스트 툴\<빌드명>\`에도 같은 release bundle 을 복사하도록 확장했습니다.
- QA 공유 폴더 경로는 스크립트 기본값으로 고정하고, 자격증명은 환경 변수 대신 Windows Credential Manager 또는 현재 Windows 세션 자격증명을 우선 사용하도록 정리했습니다.
- direct copy 가 실패하면 한 번만 사용자에게 자격증명을 묻고, 이를 Windows Credential Manager에 저장한 뒤 재시도하도록 보강했습니다.
- 새 릴리스 복사가 끝나면 QA 공유 폴더 루트에는 최신 빌드만 남기고, 이전 버전 폴더는 `old/` 아래로 이동하도록 정리했습니다.
- packaging 테스트는 새 네트워크 배포 스크립트 존재와 `build.bat` 연결을 함께 확인하도록 보강했습니다.

## [2026-04-13] - 문서 동기화 검증기의 Playwright 회귀 매핑 보강

### 변경 사항

- `scripts/verify_docs_sync.py`가 headless Playwright 회귀를 직접 실행하는 도구는 아니라는 점을 문서에 명확히 적고, 실제 실행기는 계속 `scripts/run_prebuild_regression.py`임을 정리했습니다.
- `scripts/doc_sync_rules.toml`에 Playwright 회귀 스크립트와 MCP 런처를 별도 추적 대상으로 추가해, 이 자동화가 바뀌면 `RuntimeAndPackaging`, `VerificationChecklist`, `ReliabilityReport` 문서를 함께 갱신하도록 보강했습니다.
- `bug/`, `tests/*.log`, `tools/playwright-mcp/*.png`, `*-snapshot.md`, `*.txt` 같은 로컬 검증 입력/산출물은 문서 동기화 기준 변경으로 오인하지 않도록 제외 규칙을 추가했습니다.

## [2026-04-13] - GitHub 원격 기준 git cl 진단 스크립트 추가

### 변경 사항

- `scripts/check_git_cl.ps1`를 추가해 현재 저장소에서 `git cl` 오류가 depot_tools 미설치 같은 실제 환경 문제인지, 아니면 GitHub 원격이라 애초에 `git cl`이 필요 없는 상황인지 바로 판별할 수 있게 했습니다.
- 이 저장소는 GitHub pull request 흐름을 기본 게시 경로로 유지하므로, `git cl`이 없더라도 GitHub 원격에서는 `not-required`로 안내하고 `git push` 및 PR 비교 URL을 함께 출력하도록 정리했습니다.

## [2026-04-13] - AOI 12시간 샘플 XLSX와 build 전 headless Playwright 회귀

### 변경 사항

- AOI 검사 결과 XLSX에 `Inspection_12h_Samples` 시트를 추가하고, 현재 시간 필터 시작 시각 기준 `+0h, +12h, ... +144h` 블록별 첫 10개 샘플을 함께 내보내도록 확장했습니다.
- AOI 검사 결과 미리보기, 그래프, XLSX 다운로드가 현재 시간 필터 범위를 그대로 따르되 원본 `NO`는 유지하도록 정리했습니다.
- `scripts/run_prebuild_regression.py`와 `scripts/verify_playwright_prebuild_regression.js`를 추가해, build 전 회귀 절차에 AOI 업로드/시간 필터까지 포함한 headless Playwright 검증을 정식 편입했습니다.
- 새 prebuild regression은 각 step의 실패 조건과 STDOUT을 `.artifacts/prebuild-regression/` 및 `.artifacts/playwright-prebuild-regression/`에 남기고, `build.bat`가 이를 선행 게이트로 실행합니다.

## [2026-04-10] - 일반 PC CPU 코어 최고온도 워커 전환

### 변경 사항

- 일반 PC와 어드벤텍 IPC 계열의 CPU 온도 경로를 `pythonnet + LibreHardwareMonitorLib.dll` 기반 백그라운드 워커로 전환했습니다.
- 워커는 EXE에 동봉된 `lhm-bundle`을 우선 사용하고, 없을 때만 LibreHardwareMonitor 최신 공식 릴리스를 로컬 캐시에 내려받아 `CPU Core #n` 온도 센서만 대상으로 읽고, 30초마다 최고 코어 온도 하나를 JSON 상태 파일로 갱신합니다.
- Dell Precision T5/T7 Tower 계열은 기존 Dell Command Monitor 우선 경로를 그대로 유지합니다.
- 일반 PC에서 워커가 실패하거나 코어 센서를 만들지 못하면 OpenHardwareMonitor, PerfRaw Thermal Zone, MSAcpi Thermal Zone 순으로 fallback 합니다.
- `run_app.py`, `monitor.spec`, `requirements.txt`를 갱신해 EXE 환경에서도 `cpu-temp-worker` 분기와 `pythonnet` 런타임 파일이 함께 포함되도록 정리했습니다.
- 앱 본문 맨 아래에 `CPU 온도 테스트 실행 및 로그 저장` 버튼을 추가해, 현장 PC에서 상세 진단 로그를 `C:\SystemLogs\cpu_temp_diagnostic_*.log`로 바로 남길 수 있게 했습니다.
- 추가로 `scripts/prepare_lhm_bundle.py`와 `monitor.spec`를 연결해 LibreHardwareMonitor 번들을 EXE와 함께 동봉하도록 바꿨고, 런타임은 동봉 번들을 먼저 사용해 SSL 인증서 이슈가 있는 현장 PC에서도 오프라인으로 동작할 수 있게 했습니다.

## [2026-04-08] - 검사 결과 XLSX 컬럼 단순화

### 변경 사항

- AOI / Inspector 검사 결과 XLSX와 메인 화면 미리보기 컬럼을 `NO`, `Frame`, `Total`, `메모리 (시스템)`만 남기도록 단순화했습니다.
- `측정시간`과 `Memory (인스펙터)`는 검사 결과 XLSX와 미리보기 표에서 제외했습니다.
- 미리보기 그래프의 X축은 `측정시간` 대신 `NO`를 사용하도록 조정했습니다.

## [2026-04-09] - 어드벤텍 IPC Kelvin CPU 온도 fallback 추가

### 변경 사항

- `collectors/cpu_temperature.py`에 `Win32_PerfRawData_Counters_ThermalZoneInformation` 기반 `PerfRawThermalZone` 공급자를 추가했습니다.
- 일반 PC fallback 순서를 `LibreHardwareMonitor -> OpenHardwareMonitor -> PerfRawThermalZone -> MSAcpiThermalZone`로 확장했습니다.
- `Temperature` raw 값은 `<=0` 무시, `>=2000`이면 1/10 Kelvin, 그 외 양수는 Kelvin 으로 해석해 섭씨로 변환하도록 고정했습니다.
- 어드벤텍 IPC처럼 `353`, `3530` 형식의 Thermal Zone 값을 노출하는 장비에서 `probe-temp`와 수집 로그의 CPU 온도 인식률을 개선했습니다.

## [2026-04-09] - PyInstaller optional import 경고와 Playwright MCP stdio 정리

### 변경 사항

- `monitor.spec`에서 Streamlit 서브모듈 수집 시 `streamlit.external.langchain`을 제외해 optional LangChain import 경고를 제거할 수 있게 정리했습니다.
- Playwright MCP 로컬 런처는 stdout 대신 stderr로 진단 로그를 보내도록 조정했습니다.
- Codex용 `playwright` MCP 구성은 PowerShell 래퍼 대신 `node.exe + @playwright/mcp cli.js` direct stdio 연결을 기준으로 재정렬했습니다.
- `launch-playwright-mcp.ps1`는 계속 포트/SSE 기동 확인용 래퍼로 유지하고, 실제 MCP 도구 연결은 direct stdio 기준으로 검증합니다.

## [2026-04-08] - 인스펙터 메모리 미리보기 복원과 XLSX 옵션화

### 변경 사항

- 검사 결과 미리보기 표와 그래프에는 `메모리 (인스펙터)`를 다시 표시하도록 복원했습니다.
- XLSX 내보내기는 기본적으로 `NO`, `Frame`, `Total`, `메모리 (시스템)`만 내보내고, `XLSX에 인스펙터 메모리 포함` 옵션을 켰을 때만 `메모리 (인스펙터)`를 `메모리 (시스템)` 오른쪽에 추가하도록 조정했습니다.
- AOI CLI `export`에도 동일 동작을 맞추기 위해 `--include-inspector-memory` 옵션을 추가했습니다.

## [2026-04-02] - Dell Command Monitor CPU 온도 우선 수집

### 변경 사항

- `collectors/dell_command_monitor.py`를 추가해 Dell Precision T5/T7 Tower 계열 장비에서는 Dell Command | Monitor를 자동 감지하고, 필요하면 공식 Dell 패키지를 내려받아 무인 설치하도록 연결했습니다.
- `collectors/cpu_temperature.py`는 Dell 대상 장비에서만 `root\dcim\sysman/DCIM_NumericSensor`를 사용하고, 일반 PC는 LibreHardwareMonitor, OpenHardwareMonitor, Thermal Zone 경로로 바로 fallback 하도록 분기했습니다.
- Dell Command Monitor 또는 하드웨어 모니터 계열 센서가 여러 개일 때는 `CPU Package`를 메인 지표로 우선 선택하고, 없으면 CPU 관련 센서 중 최고값으로 fallback 하도록 정리했습니다.
- Dell Precision 일부 장비에서 `UnitModifier=-1` 때문에 `5.x°C`처럼 비현실적인 온도가 기록되던 문제를 보정해, 그럴듯한 직접 온도 읽기값을 우선 사용하도록 수정했습니다.
- `cli.py start`, `cli.py probe-temp`, 관련 검증/사용자 문서를 Dell 제어 PC 운영 기준에 맞춰 갱신했습니다.

## [2026-04-02] - 문서 동기화 규칙 단일 소스화

### 변경 사항

- `docs/Best Practices/DocumentationWorkflow.md`를 문서-코드 매핑의 기준 문서로 올리고, `AGENTS.md`는 문서 트리와 진입 규칙만 남기도록 정리했습니다.
- `scripts/doc_sync_rules.toml`을 추가해 `scripts/verify_docs_sync.py`와 CI가 같은 문서 동기화 규칙 소스를 공유하도록 바꿨습니다.
- 비사소한 코드 변경의 기본 문서는 `docs/Current Phase/VerificationChecklist.md`, 리스크/우선순위/운영 기준 변경의 필수 문서는 `docs/Current Phase/CurrentPhase.md`로 역할을 분리했습니다.
- `docs/Wiki/ReliabilityReport.md`는 런타임, 패키징, CI 변경에서만 자동 요구 대상으로 유지하고, 일반 기능 작업에서는 선택 검토로 낮췄습니다.

## [2026-04-02] - CPU 온도 수집 복원과 전용 대시보드 추가

### 변경 사항

- `collectors/cpu_temperature.py`를 추가하고 Windows에서 `LibreHardwareMonitor`, `OpenHardwareMonitor`, `MSAcpi_ThermalZoneTemperature` 순으로 CPU 온도 센서를 조회하도록 확장했습니다.
- `collectors/sampler.py`와 `collectors/aggregator.py`에서 1초 단위 온도를 수집하고, 각 5초 집계 구간의 최고 온도를 `CPU_Temp(C)` 컬럼으로 기록하도록 연결했습니다.
- `dashboards/cpu.py`에 기존 사용률 복합 차트와 함께 `CPU 온도 추이` 전용 차트를 추가하고, KPI에 최고/평균 온도를 표시하도록 보강했습니다.
- `cli.py`에 `probe-temp` 명령을 추가해 현재 PC에서 CPU 온도 센서가 잡히는지 바로 확인할 수 있게 했습니다.
- `collectors/writers.py`는 기존 날짜 CSV에 새 컬럼이 추가되더라도 헤더를 재작성해 로그 파일이 깨지지 않도록 보강했습니다.

## [2026-04-02] - 패키징 산출물 정리와 CI 문서 동기화 추가

### 변경 사항

- `Monitor.ps1`를 공식 정리 대상으로 명시하고, 신규 실행 기준이 아닌 호환성 스텁으로 단순화했습니다.
- `build.bat`, `mkdocs.yml`, `monitor.spec`를 조정해 문서 사이트, PyInstaller 작업 디렉토리, 릴리스 산출물이 모두 `.artifacts/` 아래로 생성되도록 정리했습니다.
- `.github/workflows/windows-ci.yml`을 추가하고, 단위 테스트, 샘플 로그 기반 대시보드 스모크, 문서 동기화 검사, MkDocs 빌드를 자동 검증에 포함했습니다.
- `scripts/verify_docs_sync.py`를 추가해 코드 변경과 활성 문서 변경이 함께 이뤄졌는지 CI와 로컬에서 확인할 수 있게 했습니다.
- PowerShell에서 한글 문서를 읽을 때 `Get-Content -Encoding UTF8`를 사용해야 한다는 규칙을 활성 문서와 에이전트 기준에 반영했습니다.
- `AGENTS.md`와 문서 워크플로에 작업 마감 문서 게이트를 추가해 `docs/Current Phase/*` 문서가 기능 변경 뒤에 빠지지 않도록 보강했습니다.

## [2026-04-01] - Playwright MCP 로컬 세팅 추가

### 변경 사항

- `tools/playwright-mcp/`에 로컬 Playwright MCP 패키지, 실행 래퍼, Smoke Test 스크립트를 추가했습니다.
- Windows 환경에 Node.js LTS를 설치하고, Codex Desktop 로컬 설정 `C:\Users\Win11_SPC_General\.codex\config.toml`에 `playwright` MCP 서버 엔트리를 등록했습니다.
- 이후 WEB 기반 GUI 검증은 저장소 로컬 래퍼 `tools/playwright-mcp/launch-playwright-mcp.ps1`를 기준 경로로 사용하도록 정리했습니다.

## [2026-04-01] - AOI 검사 결과 번호화와 XLSX 내보내기

### 변경 사항

- `inspector_logs/core.py`에서 `Model Open : ...` 라인을 파싱하고, `InspTime` 기준 검사 결과를 `NO=1`부터 재구성하도록 확장했습니다.
- 검사 결과별 `Memory (인스펙터)`는 AOI 로그의 최신 `Working Set` 값을, `Memory (시스템)`은 해당 검사 시각 직전의 `Mem_Used(GB)` 값을 매칭하도록 추가했습니다.
- `aoi_cli.py`에 `export` 명령을 추가해 검사 결과 XLSX를 CLI로도 내보낼 수 있게 했습니다.
- 메인 화면 대시보드 아래쪽에 `검사 결과 XLSX 내보내기` 영역을 두고, 모델명, 총 검사 수, 시작/종료 NO, 미리보기, XLSX 다운로드를 바로 사용할 수 있게 했습니다.
- 검사 결과 미리보기에서 그래프 형식, 항목별 이름 기반 색상 팔레트, 투명도, 표 강조 색상을 사용자가 직접 바꿀 수 있게 했습니다.
- 메모리 대시보드에서는 새 검사 결과 패널과 겹치는 인스펙터 상세 시계열 차트를 숨기고, 관련 코드는 주석으로 보존했습니다.
- `verify_dashboards.py`의 Windows 콘솔 인코딩 문제를 피하도록 ASCII 출력으로 정리했습니다.

## [2026-03-31] - Time Range 직접 입력 추가와 한글 UI 정리

### 변경 사항

- `Time Range` 슬라이더와 함께 `시작 시간`, `종료 시간` 직접 입력 UI를 추가했습니다.
- 시작만 입력하면 해당 시각부터 로그 끝까지, 종료만 입력하면 로그 처음부터 해당 시각까지 보이도록 확장했습니다.
- 입력한 시각과 정확히 일치하는 데이터가 없을 때 시작은 다음 샘플, 종료는 이전 샘플로 자동 보정하도록 정리했습니다.
- 사이드바, KPI, 대시보드 선택 메뉴, 차트 제목과 안내 문구를 한국어 중심 UI로 정리했습니다.
- `인스펙터 앱 (로그)` 명칭을 화면과 차트에 일관되게 반영했습니다.
- 사용자 메뉴얼을 한국어 UI 명칭 기준으로 다시 정리했습니다.
- 메모리 대시보드에 짙은 파란 선, 옅은 파란 영역, 디스크 스왑 메모리(주황색 선) 의미 설명을 추가했습니다.

## [2026-03-30] - Docs 구조 정리와 AOI / Inspector 연동

### 변경 사항

- `docs`를 `Architecture`, `Best Practices`, `Wiki`, `Future`, `Current Phase` 구조로 재편했습니다.
- `docs/ActiveDocs.md`를 추가해 활성 문서 인덱스를 만들었습니다.
- `AGENTS.md`에 문서 확인 규칙과 구현 후 문서 업데이트 규칙을 추가했습니다.
- 기존 루트 문서들은 호환성 stub로 남기고 활성 문서는 새 경로로 이동했습니다.

### AOI / Inspector 로그

- 사용자가 AOI / Inspector 로그 파일 경로를 직접 입력할 수 있도록 Streamlit UI를 확장했습니다.
- `inspector_logs/core.py`와 `aoi_cli.py`를 추가해 AOI 로그 파싱 코어와 CLI Smoke Test 경로를 분리했습니다.
- 메모리 탭을 `Memory AND Inspector Dashboard`로 확장하고 `Frame`, `Total`, `Working Set`, `Inspector APP (log)` 비교를 추가했습니다.
- AOI / Inspector 로그는 `Browse files` 업로드를 기본 경로로 지원하고, 경로 입력은 고급 옵션으로 유지했습니다.
- `monitor.spec`에 `inspector_logs/`를 포함해 빌드된 EXE에서 import가 누락되지 않도록 수정했습니다.

## [2026-03-25] - 포터블 배포 안정화와 수집기 보정

### 해결한 문제

- 포터블 실행 시 경로 인식 오류를 줄이기 위해 EXE 진입 흐름을 정리했습니다.
- PyInstaller 임시 경로와 원본 EXE 경로 사이 이동 문제를 완화했습니다.

### 기능 개선

- `run_app.py` 기반 단일 진입점 구조를 도입했습니다.
- 피크 시간 계산과 사용자 가시성 관련 표시를 보정했습니다.

## [2026-03-24] - 타임드라이브 수집기로 마이그레이션

### 주요 변경 사항

- 기존 수집 방식을 `psutil` 기반 드라이브 수집기로 전환했습니다.
- `data_loader.py`를 exact merge 기반 로딩 구조로 단순화했습니다.
- 대시보드가 5초 집계 컬럼을 직접 참조하도록 정리했습니다.
- `verify_dashboards.py` 기반 로더/대시보드 검증 루틴을 추가했습니다.
