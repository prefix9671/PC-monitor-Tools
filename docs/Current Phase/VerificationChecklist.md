# Verification Checklist

Updated On: 2026-04-21  
Status: Active

구현을 마친 뒤에는 변경 종류에 따라 아래 검증을 수행합니다.

## 공통

- 영향받는 활성 문서를 함께 업데이트했는지 확인
- `docs/ActiveDocs.md` 기준으로 문서 경로와 우선순위가 유지되는지 확인
- 빌드 또는 최종 패키징 전에는 `.\venv\Scripts\python scripts\run_prebuild_regression.py`를 먼저 실행
- `.\venv\Scripts\python scripts\verify_docs_sync.py`
- `scripts\verify_docs_sync.py`는 문서 동기화만 검사하므로, Playwright나 단위 테스트 실행 자체는 `scripts\run_prebuild_regression.py`로 별도 확인
- `scripts\verify_docs_sync.py`가 한글 경로를 포함한 `bug\` 입력 파일과 로컬 Playwright 산출물을 quoted path/UTF-8 출력 환경에서도 계속 무시하는지 확인
- 비사소한 코드 변경이 있었다면 이 문서(`docs/Current Phase/VerificationChecklist.md`)가 같은 변경 안에서 갱신되었는지 확인
- 우선순위, 리스크, 운영 기준이 바뀌었다면 `docs/Current Phase/CurrentPhase.md`도 함께 갱신되었는지 확인

## 수집기 또는 로그 스키마 변경

- `.\venv\Scripts\python -m pytest tests\test_cli.py`
- `.\venv\Scripts\python cli.py probe-temp`
- Dell Precision T5/T7 Tower 제어 PC라면 `start` 또는 `probe-temp` 실행 시 DCM 자동 설치/준비 메시지가 보이는지 확인
- Dell 제어 PC라면 `probe-temp`가 가능할 때 `Source: DellCommandMonitor`를 우선 보고하는지 확인
- Dell 제어 PC라면 CPU 온도가 `5.x°C`처럼 비현실적으로 낮게 표시되지 않고, 실제 장비 상태에 맞는 값으로 보이는지 확인
- 일반 PC라면 DCM 설치 시도를 건너뛰고 EXE에 동봉된 `lhm-bundle`을 우선 사용해 `pythonnet` 워커를 기동하는지 확인
- 일반 PC라면 `probe-temp` 또는 상태 JSON 에서 `Source: LibreHardwareMonitorCoreMax`와 `CPU Core #n` 형태의 `Sensor` 문자열을 우선 확인
- 일반 PC라면 워커가 30초 간격으로 JSON 상태 파일을 갱신하고, 동봉 번들이 없거나 실패할 때만 OpenHardwareMonitor, PerfRaw Thermal Zone, Thermal Zone fallback 으로 계속 동작하는지 확인
- 앱 맨 아래 `CPU 온도 테스트 실행 및 로그 저장` 버튼을 눌렀을 때 `C:\SystemLogs\cpu_temp_diagnostic_*.log`와 `cpu_temp_diagnostic_latest.log`가 생성되고, force refresh 결과와 provider별 raw preview가 포함되는지 확인
- 어드벤텍 IPC 또는 동일한 `Win32_PerfRawData_Counters_ThermalZoneInformation` 노출 장비라면 raw 값 `353`이 약 `79.9°C`, `3530`이 약 `79.9°C`로 해석되는지 확인
- 어드벤텍 IPC 또는 동일 클래스 장비라면 `_Total` 집계 레코드와 개별 Thermal Zone 이 함께 있을 때 `probe-temp`의 `Sensor` 출력으로 실제 선택된 zone 을 확인하고, 개별 zone 최대값이 `CPU_Temp(C)`에 반영되는지 확인
- 메모리 압박 또는 비정상 콘솔 출력이 섞여도 PowerShell/설치기 stdout/stderr 디코딩에서 `UnicodeDecodeError`가 나지 않고 수집이 계속되는지 확인
- 새 `resource_*.csv`에 `Swap_Used(GB)`, `Swap_Total(GB)`, `Swap_Usage(%)`가 기록되고, 기존 로그는 이 컬럼 없이도 계속 로드되는지 확인
- CLI 경로로 기능을 확인할 수 있다면 목적에 맞는 Smoke Test 수행
- 실제 CSV 컬럼명이 대시보드 기대값과 맞는지 확인
- 같은 날짜 로그 파일에 새 컬럼이 추가될 때 CSV 헤더가 깨지지 않는지 확인
- 구조가 바뀌면 `Architecture/SystemOverview.md`와 `Wiki/ProjectStructure.md` 업데이트

## AOI / Inspector 로그 변경

- `.\venv\Scripts\python aoi_cli.py summary --path ".\bug\operation_0319_north side grab.log"`
- `.\venv\Scripts\python aoi_cli.py export --path ".\bug\operation_0319_north side grab.log" --out ".\inspection_export.xlsx"`
- 개발 경로 `.streamlit/config.toml`과 EXE 경로 `run_app.py`가 모두 1GB 업로드 한도를 유지하는지 확인
- 앱 진입 시 기본 AOI 경로 `C:\Inspector\shared\operation.txt`를 자동으로 시도하고, 해당 경로가 없을 때는 경고 없이 조용히 대기하는지 확인
- 기본 경로에 로그가 있으면 파일 업로드와 같은 경로로 자동 업로드 처리되고, 성공 메시지와 `인스팩터 로그 다른 이름으로 저장` 버튼이 활성화되는지 확인
- `인스팩터 로그 다른 이름으로 저장` 버튼이 현재 불러온 원본 TXT / LOG를 그대로 저장하고, 여러 파일이면 ZIP으로 묶는지 확인
- 큰 단일 인스펙터 로그는 청크 단위 스레드 병렬화, 여러 인스펙터 로그는 파일 단위 스레드 병렬화가 사용되는지 확인
- `Memory AND Inspector Dashboard`에서 인스펙터 요약 지표와 외부 시스템 메모리 비교가 보이는지 확인
- 메인 화면 대시보드 아래 `검사 결과 XLSX 내보내기` 영역에서 모델명, 총 검사 수, 시작/종료 NO, 미리보기, 다운로드가 모두 보이는지 확인
- 미리보기 표와 그래프가 `메모리 (인스펙터)`를 다시 함께 표시하는지 확인
- 검사 결과 XLSX 기본 출력이 `NO`, `Frame`, `Total`, `메모리 (시스템)`이고, 옵션을 켰을 때만 `메모리 (인스펙터)`가 오른쪽에 추가되는지 확인
- 검사 결과 XLSX에 `Inspection_12h_Samples` 시트가 추가되고, 상단에 적용 시작/종료 시각과 종료 시점 수동 지정 여부가 기록되는지 확인
- `Inspection_12h_Samples` 시트가 현재 시간 필터 시작 시각 기준 `+0h, +12h, ...` 블록을 만들고, 각 기준점 이후 종료 시각 이내 첫 10개를 사용하는지 확인
- 현재 시간 필터를 바꾸면 AOI 패널 미리보기, 그래프, XLSX 다운로드가 모두 같은 범위를 따르고, `NO`는 원본 번호를 유지하는지 확인
- AOI 이벤트 `Timestamp`와 시스템 로그 `Timestamp`의 정밀도가 `datetime64[us]` / `datetime64[ns]`로 섞여도 `aoi_cli.py export`와 검사 결과 재구성이 `MergeError` 없이 동작하는지 확인
- 실로그 export 가 120초 안에 끝나지 않으면 `bug\operation_0319_north side grab.log`를 기반으로 축약 mock 로그를 만들어 같은 검증을 다시 수행
- 메모리 대시보드에서 중복 인스펙터 상세 차트가 미노출되고, 상세 시계열 안내가 하단 검사 결과 패널로 연결되는지 확인
- `그래프 형식`, 항목별 이름 기반 색상, 표 강조 색상, 투명도 옵션을 바꿨을 때 미리보기 그래프와 표 강조가 함께 반영되는지 확인
- `메모리 (시스템)` 값이 검사 시각의 직전 시스템 샘플과 맞는지 확인

## 대시보드 또는 로더 변경

- `.\venv\Scripts\python verify_dashboards.py`
- `.\venv\Scripts\python scripts\run_prebuild_regression.py`
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\playwright-mcp\verify-playwright-mcp.ps1`
- 브라우저 탭 종료나 headless 캡처 종료 후 Streamlit 콘솔에 반복 `Task exception was never retrieved` / `WebSocketClosedError` traceback, `Exception in callback ... CancelledError`, `gzip ... I/O operation on closed file` 종료 노이즈가 남지 않는지 확인
- 작업 완료 후 WEB 최종 검증 루틴:
  `.\venv\Scripts\python -m streamlit run app.py --server.headless true --server.port 8502`
  별도 터미널에서 `node.exe .\scripts\verify_playwright_dashboards.js http://127.0.0.1:8502`
  완료 후 `.artifacts\playwright-dashboard-test\dashboard-summary.json`, `01-home.png`, `02-cpu.png`, `03-memory.png`, `04-storage.png`, `05-custom.png`, `console-messages.md`를 확인
- `scripts\run_prebuild_regression.py`는 repo-local bug 입력 파일 업로드 기준으로 headless Playwright 회귀를 수행하며, 각 step의 실패 조건과 STDOUT을 `.artifacts\prebuild-regression\`과 `.artifacts\playwright-prebuild-regression\`에 남김
- `scripts\verify_docs_sync.py`는 `scripts\run_prebuild_regression.py`, `scripts\verify_playwright_dashboards.js`, `scripts\verify_playwright_prebuild_regression.js`, `tools\playwright-mcp\*.ps1` 변경 시 관련 활성 문서 갱신도 함께 요구
- headless Playwright 회귀의 대표 실패 조건:
  페이지 미기동, 시스템 CSV 업로드 후 차트 미렌더, AOI 업로드 후 NO input 미생성, 시간 필터 후 NO 범위 미축소
- 최근 로그를 읽어 `CPU`, `Memory`, `Storage`, `Custom Graph`가 모두 뜨는지 확인
- `CPU 대시보드`에서 `CPU 사용률과 온도`, `CPU 온도 추이`가 함께 보이고, 온도가 5초 구간 최고값 기준으로 표시되는지 확인
- `메모리 + 인스펙터 대시보드`에서 페이지 파일 사용량, 스왑 사용률, 가상 메모리 상태가 함께 보이고 `0`이면 `현재 스왑된 메모리가 없습니다`로 안내되는지 확인
- 스왑 사용률이 1%를 넘는 구간이 있는 로그에서도 메모리 대시보드가 크래시하지 않고, `스왑 시작` 점선/배경 강조가 타임스탬프 축에서 정상 표시되는지 확인
- 어드벤텍 IPC 로그를 사용한다면 `CPU_Temp(C)`가 `_Total` 평균성 레코드가 아니라 개별 Thermal Zone 최대값에 맞게 표시되는지 함께 확인
- 주요 버튼, 메뉴, 차트 제목, KPI 라벨이 한국어 UI 기준으로 자연스럽게 보이는지 확인
- `Time Range` 슬라이더와 `Start Time` / `End Time` 직접 입력이 함께 동작하는지 확인
- 시작만 입력했을 때 끝까지, 종료만 입력했을 때 처음부터, 둘 다 입력했을 때 해당 범위만 보이는지 확인
- 없는 시각을 입력했을 때 시작은 다음 샘플, 종료는 이전 샘플로 보정되는지 확인
- Playwright MCP가 구성된 세션에서는 WEB 기반 GUI 검증을 우선하고, Codex용 `[mcp_servers.playwright]`는 `node.exe + @playwright/mcp cli.js` direct stdio 구성을 사용하며 `launch-playwright-mcp.ps1`는 포트/SSE 스모크 용도로만 확인
- 현재 세션에서 `unknown MCP server 'playwright'` 또는 MCP initialize 실패가 보이면 Codex 앱 재실행 후 새 세션에서 다시 확인
- 재실행 전에는 `verify_dashboards.py`, AOI CLI export Smoke Test, Streamlit 수동 확인 결과를 함께 남김
- 사용자 흐름이 바뀌면 `Wiki/UserManual.md` 업데이트

## CI 또는 문서 자동화 변경

- `.\venv\Scripts\python scripts\run_ci_dashboard_smoke.py`
- `.\venv\Scripts\python scripts\verify_docs_sync.py`
- GitHub Actions `windows-ci.yml`이 새 검증을 포함하는지 확인
- CI 변경이라면 `docs/Wiki/ReliabilityReport.md`도 같은 변경 안에서 갱신했는지 확인

## 실행 또는 패키징 변경

- `.\venv\Scripts\python -m mkdocs build`
- `.\venv\Scripts\python scripts\run_prebuild_regression.py`
- `git cl` 오류를 확인해야 하면 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\check_git_cl.ps1`를 실행해, GitHub 원격에서의 비필수 경고인지 depot_tools 환경 누락인지 먼저 구분
- `build.bat`를 실행해 로컬 release bundle 과 `\\192.168.1.13\sqa\113_테스트 툴\<빌드명>\` 복사가 모두 완료되는지 확인
- QA 공유 폴더 direct copy 가 실패하면 Windows Credential Manager 자격증명 입력 프롬프트가 뜨고, 이를 저장한 뒤 재시도되는지 확인
- QA 공유 폴더 루트에는 현재 빌드 폴더만 남고, 이전 버전 폴더가 `\\192.168.1.13\sqa\113_테스트 툴\old\` 아래로 이동하는지 확인
- 관련 기능이 CLI 진입점과 연결된다면 최소 Smoke Test를 추가 수행
- 일반 PC CPU 온도 워커를 변경했다면 개발 환경 또는 빌드 산출물에서 `cpu-temp-worker --once` 경로가 예외 없이 실행되고, 릴리스 폴더 또는 EXE 내부에 `lhm-bundle`이 포함되는지 확인
- 필요 시 `build.bat` 실행 후 산출물 확인
- `Architecture/RuntimeAndPackaging.md`와 `Wiki/Changelog.md` 업데이트

## 문서만 변경했을 때

- `.\venv\Scripts\python -m mkdocs build`
- 링크, 이미지 경로, nav 구성이 정상인지 확인
- 사용자 시작 흐름이나 제어판 사용법을 바꿨다면 `node .\scripts\capture_user_manual_assets.js entry-monitoring http://127.0.0.1:8507`로 raw/approved UI 자산을 다시 생성
- 대시보드별 설명이나 AOI / 인스펙터 업로드, XLSX 내보내기 설명을 바꿨다면 `node .\scripts\capture_user_manual_assets.js dashboards-inspector http://127.0.0.1:8507`로 실UI 자산을 다시 생성
- `.artifacts\manual-assets\entry-monitoring\approved\` PNG를 실제로 열어 한국어 텍스트, 버튼 라벨, 성공 메시지 구도가 의도대로 찍혔는지 확인
- `.artifacts\manual-assets\dashboards-inspector\approved\` PNG를 실제로 열어 시스템 로그 선택, 시간 범위 필터, 대시보드 제목, AOI 업로드 성공 상태, XLSX 버튼이 의도대로 보이는지 확인
- 승인한 스크린샷만 `docs\images\manual\`에 반영하고, Windows UAC 같은 네이티브 창은 텍스트 설명으로만 유지
