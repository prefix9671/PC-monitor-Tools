# Runtime And Packaging

Updated On: 2026-04-13  
Status: Active

## 실행 모드

이 프로젝트는 크게 두 가지 모드를 가집니다.

1. 대시보드 모드
2. 수집기 모드

패키징된 EXE에서는 `run_app.py`가 단일 진입점 역할을 하며, `start` 인자가 있으면 수집기로, `cpu-temp-worker` 인자가 있으면 일반 PC CPU 코어 온도 워커로, 없으면 Streamlit 대시보드로 동작합니다.

## 런타임 흐름

### 개발 환경

- 대시보드: `.\venv\Scripts\python -m streamlit run app.py`
- 수집기: `.\venv\Scripts\python cli.py start`

### 패키징 환경

- 대시보드 실행 파일: `SystemResourceMonitor*.exe`
- 수집기 시작 래퍼: `start_monitor.bat`
- EXE 내부 분기: `run_app.py`

## 관련 파일 역할

| 파일 | 역할 |
|---|---|
| `run_app.py` | EXE 환경에서 대시보드/수집기 분기 |
| `runtime_patches.py` | Streamlit/Tornado 런타임에서 브라우저 종료 시 발생하는 알려진 WebSocket disconnect noise 를 완화 |
| `collectors/cpu_temperature_worker.py` | 일반 PC CPU 코어 최고온도 워커 엔트리 |
| `collectors/libre_hardware_monitor.py` | LibreHardwareMonitor 다운로드/캐시와 `pythonnet` DLL 로드 |
| `scripts/prepare_lhm_bundle.py` | 빌드 전에 LibreHardwareMonitor 번들을 `.artifacts/vendor/lhm-bundle/`로 준비 |
| `scripts/check_git_cl.ps1` | 현재 저장소에서 `git cl`이 필요한 환경인지, 단순히 GitHub PR 흐름이라 불필요한지 진단 |
| `scripts/publish_release_to_share.ps1` | 로컬 release bundle 을 QA 공유 폴더 `\\192.168.1.13\sqa\113_테스트 툴`에도 복사하고, 필요하면 Windows Credential Manager 자격증명을 저장하며, 서버 루트에는 최신 릴리스만 남기고 이전 버전 폴더는 `old/`로 이동 |
| `scripts/run_prebuild_regression.py` | 빌드 전 회귀 러너. 단위 테스트, AOI CLI, 대시보드 스모크, 문서 동기화, MkDocs, headless Playwright 순으로 실행 |
| `aoi_cli.py` | AOI 로그 파서 Smoke Test 및 요약 확인용 CLI |
| `build.bat` | MkDocs 빌드, PyInstaller 실행, 산출물 복사/압축 |
| `monitor.spec` | PyInstaller 입력 정의 |
| `start_monitor.bat` | 관리자 권한 확인 후 EXE를 `start` 인자와 함께 실행 |
| `Monitor.ps1` | 공식 정리 대상인 호환성 스텁 |
| `scripts/run_ci_dashboard_smoke.py` | CI에서 샘플 로그로 대시보드 스모크 검증 |
| `scripts/verify_docs_sync.py` | 코드 변경과 활성 문서 변경의 동기화만 확인하는 문서 게이트. Playwright나 단위 테스트를 실행하지는 않음 |
| `tools/playwright-mcp/launch-playwright-mcp.ps1` | 로컬 Playwright MCP 서버 포트/SSE 스모크용 래퍼 |
| `tools/playwright-mcp/verify-playwright-mcp.ps1` | 로컬 Playwright MCP 서버 Smoke Test |
| `scripts/verify_playwright_dashboards.js` | Streamlit 앱을 실제 브라우저로 열어 CPU, 메모리, 스토리지, 사용자 정의 대시보드를 검증하고 결과를 `.artifacts/playwright-dashboard-test/`에 저장 |
| `scripts/verify_playwright_prebuild_regression.js` | repo-local bug 입력 파일을 업로드해 headless Playwright로 대시보드와 AOI 시간 필터/XLSX 패널 회귀를 검증 |

## 배포 산출물

`build.bat` 기준 주요 산출물은 다음과 같습니다.

- `.artifacts/releases/<빌드명>/SystemResourceMonitor*.exe`
- `.artifacts/releases/<빌드명>/start_monitor.bat`
- `.artifacts/releases/<빌드명>/Manual.zip`
- `\\192.168.1.13\sqa\113_테스트 툴\<빌드명>\`
- `.artifacts/manual-site/`
- `.artifacts/pyinstaller/`

## 현재 운영 기준

- 문서 사이트는 `mkdocs build` 결과로 `.artifacts/manual-site/`에 생성됩니다.
- `.artifacts/`, `build/`, `dist/`, `site/`는 생성 산출물이므로 소스 코드의 출처로 사용하지 않습니다.
- 수집기 실행의 현재 기준 래퍼는 `start_monitor.bat` 입니다.
- `build.bat`는 로컬 `.artifacts/releases/<빌드명>/` 생성 후 `scripts/publish_release_to_share.ps1`를 호출해 QA 공유 폴더 `\\192.168.1.13\sqa\113_테스트 툴\<빌드명>\`에도 같은 bundle 을 복사합니다.
- QA 공유 폴더 복사는 먼저 Windows Credential Manager 또는 현재 Windows 세션 자격증명으로 직접 시도합니다.
- direct copy 가 실패하면 `scripts/publish_release_to_share.ps1`가 사용자에게 한 번만 자격증명을 묻고, 이를 Windows Credential Manager에 저장한 뒤 다시 복사합니다. 기본 사용자 제안값은 `qa`입니다.
- 새 빌드 복사가 성공하면 QA 공유 폴더 루트에서는 현재 빌드와 `old/`를 제외한 이전 버전 폴더를 모두 `\\192.168.1.13\sqa\113_테스트 툴\old\` 아래로 이동해 최신본만 남깁니다.
- 일반 PC CPU 온도 워커는 개발 환경에서는 `python -m collectors.cpu_temperature_worker`, 패키징 환경에서는 `SystemResourceMonitor*.exe cpu-temp-worker` 분기를 사용합니다.
- 빌드 시 `scripts/prepare_lhm_bundle.py`가 LibreHardwareMonitor 번들을 `.artifacts/vendor/lhm-bundle/`로 준비하고, `monitor.spec`가 이를 EXE 내부 `lhm-bundle/` 데이터로 포함합니다.
- 빌드 전에는 `scripts/run_prebuild_regression.py`가 먼저 실행되어 단위 테스트, AOI CLI, 대시보드 스모크, 문서 동기화, MkDocs, headless Playwright 회귀를 모두 통과해야 합니다.
- `scripts/verify_docs_sync.py`는 위 회귀들을 실행하는 스크립트가 아니라, Playwright 회귀 스크립트나 MCP 런처가 바뀌었을 때 관련 활성 문서가 같이 갱신됐는지만 판정합니다.
- WEB GUI 자동화에서 Codex Desktop stdio MCP 연결은 사용자 로컬 `C:\Users\Win11_SPC_General\.codex\config.toml`의 `[mcp_servers.playwright]` 항목이 `node.exe + tools/playwright-mcp/node_modules/@playwright/mcp/cli.js`를 직접 가리키는 구성을 사용합니다.
- `tools/playwright-mcp/launch-playwright-mcp.ps1`는 stdin/stdout MCP 본 연결이 아니라 포트/SSE 기동 확인과 수동 스모크용 래퍼로 유지합니다.
- 작업 완료 후 최종 WEB 대시보드 검증은 `verify-playwright-mcp.ps1`로 서버 준비를 확인한 뒤, `python -m streamlit run app.py --server.port 8502`와 `node.exe .\scripts\verify_playwright_dashboards.js http://127.0.0.1:8502` 조합으로 수행합니다.
- 최종 검증 직전의 headless 회귀는 `.\venv\Scripts\python.exe scripts\run_prebuild_regression.py` 한 번으로 재실행할 수 있고, 각 step의 실패 조건과 STDOUT은 `.artifacts/prebuild-regression/` 및 `.artifacts/playwright-prebuild-regression/`에 남습니다.
- 개발 환경 `streamlit run app.py`와 EXE 진입점 `run_app.py`는 모두 `runtime_patches.py`를 통해 브라우저 disconnect 시 `Task exception was never retrieved / WebSocketClosedError` 노이즈를 줄입니다.
- 이 저장소의 코드 리뷰 기본 경로는 GitHub `git push + pull request` 이며, depot_tools 기반 `git cl`은 필수 전제가 아닙니다. `git cl` 오류가 보고되면 `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check_git_cl.ps1`로 먼저 원인이 “GitHub 원격이라 불필요”인지 “실제 git-cl 환경 누락”인지 구분합니다.

## 알려진 주의 사항

- `Monitor.ps1`는 공식 정리 대상이며 배포 산출물에 포함하지 않습니다. 필요할 때만 레거시 안내용 스텁으로 취급합니다.
- Streamlit 앱이 런타임에 불러오는 로컬 파이썬 모듈은 `monitor.spec`의 `datas`에 포함되어야 합니다. 예를 들어 `inspector_logs/` 같은 폴더가 빠지면 EXE에서 `ModuleNotFoundError`가 발생할 수 있습니다.
- `monitor.spec`는 Streamlit 전체 서브모듈을 수집하되 `streamlit.external.langchain` 같은 optional 모듈은 제외해, 실제로 사용하지 않는 LangChain 의존성 경고가 빌드를 오염시키지 않도록 유지합니다.
- `monitor.spec`는 일반 PC CPU 코어 온도 워커를 위해 `pythonnet`, `clr_loader`, `Python.Runtime.dll` 계열 런타임 파일과 `lhm-bundle/` 디렉터리도 함께 포함해야 합니다.
- `monitor.spec`는 일반 PC CPU 코어 온도 워커를 위해 `pythonnet`, `clr_loader`, `Python.Runtime.dll` 계열 런타임 파일도 함께 포함해야 합니다.
- `build.bat`는 packaging 전에 `scripts/run_prebuild_regression.py`가 성공해야만 계속 진행하고, packaging 뒤에는 QA 공유 폴더 복사와 이전 버전 `old/` 아카이브까지 통과해야 완료됩니다. 로컬 bug 입력 로그, headless Playwright 검증 환경, 또는 QA 공유 폴더 접근/자격증명 준비가 안 되면 빌드가 중단됩니다.
- 포터블 배포 흐름을 바꿀 때는 `build.bat`, `monitor.spec`, `run_app.py`, `start_monitor.bat`, 관련 문서를 함께 확인합니다.
- Playwright MCP는 Node.js LTS와 로컬 `tools/playwright-mcp/` 패키지 설치를 전제로 하며, 기본 브라우저 채널은 `msedge`, 기본 실행 모드는 `headless + isolated` 입니다. Codex stdio 연결에서는 PowerShell 래퍼보다 Node CLI 직결 구성이 필요합니다.

## 문서 업데이트 트리거

- 실행 인자 규칙, EXE 진입점, 빌드 스크립트, 배포 산출물이 바뀌면 이 문서를 업데이트합니다.
