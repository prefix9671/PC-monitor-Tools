# Runtime And Packaging

Updated On: 2026-04-10  
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
| `collectors/cpu_temperature_worker.py` | 일반 PC CPU 코어 최고온도 워커 엔트리 |
| `collectors/libre_hardware_monitor.py` | LibreHardwareMonitor 다운로드/캐시와 `pythonnet` DLL 로드 |
| `scripts/prepare_lhm_bundle.py` | 빌드 전에 LibreHardwareMonitor 번들을 `.artifacts/vendor/lhm-bundle/`로 준비 |
| `aoi_cli.py` | AOI 로그 파서 Smoke Test 및 요약 확인용 CLI |
| `build.bat` | MkDocs 빌드, PyInstaller 실행, 산출물 복사/압축 |
| `monitor.spec` | PyInstaller 입력 정의 |
| `start_monitor.bat` | 관리자 권한 확인 후 EXE를 `start` 인자와 함께 실행 |
| `Monitor.ps1` | 공식 정리 대상인 호환성 스텁 |
| `scripts/run_ci_dashboard_smoke.py` | CI에서 샘플 로그로 대시보드 스모크 검증 |
| `scripts/verify_docs_sync.py` | 코드 변경과 활성 문서 변경의 동기화 확인 |
| `tools/playwright-mcp/launch-playwright-mcp.ps1` | 로컬 Playwright MCP 서버 포트/SSE 스모크용 래퍼 |
| `tools/playwright-mcp/verify-playwright-mcp.ps1` | 로컬 Playwright MCP 서버 Smoke Test |
| `scripts/verify_playwright_dashboards.js` | Streamlit 앱을 실제 브라우저로 열어 CPU, 메모리, 스토리지, 사용자 정의 대시보드를 검증하고 결과를 `.artifacts/playwright-dashboard-test/`에 저장 |

## 배포 산출물

`build.bat` 기준 주요 산출물은 다음과 같습니다.

- `.artifacts/releases/<빌드명>/SystemResourceMonitor*.exe`
- `.artifacts/releases/<빌드명>/start_monitor.bat`
- `.artifacts/releases/<빌드명>/Manual.zip`
- `.artifacts/manual-site/`
- `.artifacts/pyinstaller/`

## 현재 운영 기준

- 문서 사이트는 `mkdocs build` 결과로 `.artifacts/manual-site/`에 생성됩니다.
- `.artifacts/`, `build/`, `dist/`, `site/`는 생성 산출물이므로 소스 코드의 출처로 사용하지 않습니다.
- 수집기 실행의 현재 기준 래퍼는 `start_monitor.bat` 입니다.
- 일반 PC CPU 온도 워커는 개발 환경에서는 `python -m collectors.cpu_temperature_worker`, 패키징 환경에서는 `SystemResourceMonitor*.exe cpu-temp-worker` 분기를 사용합니다.
- 빌드 시 `scripts/prepare_lhm_bundle.py`가 LibreHardwareMonitor 번들을 `.artifacts/vendor/lhm-bundle/`로 준비하고, `monitor.spec`가 이를 EXE 내부 `lhm-bundle/` 데이터로 포함합니다.
- WEB GUI 자동화에서 Codex Desktop stdio MCP 연결은 사용자 로컬 `C:\Users\Win11_SPC_General\.codex\config.toml`의 `[mcp_servers.playwright]` 항목이 `node.exe + tools/playwright-mcp/node_modules/@playwright/mcp/cli.js`를 직접 가리키는 구성을 사용합니다.
- `tools/playwright-mcp/launch-playwright-mcp.ps1`는 stdin/stdout MCP 본 연결이 아니라 포트/SSE 기동 확인과 수동 스모크용 래퍼로 유지합니다.
- 작업 완료 후 최종 WEB 대시보드 검증은 `verify-playwright-mcp.ps1`로 서버 준비를 확인한 뒤, `python -m streamlit run app.py --server.port 8502`와 `node.exe .\scripts\verify_playwright_dashboards.js http://127.0.0.1:8502` 조합으로 수행합니다.

## 알려진 주의 사항

- `Monitor.ps1`는 공식 정리 대상이며 배포 산출물에 포함하지 않습니다. 필요할 때만 레거시 안내용 스텁으로 취급합니다.
- Streamlit 앱이 런타임에 불러오는 로컬 파이썬 모듈은 `monitor.spec`의 `datas`에 포함되어야 합니다. 예를 들어 `inspector_logs/` 같은 폴더가 빠지면 EXE에서 `ModuleNotFoundError`가 발생할 수 있습니다.
- `monitor.spec`는 Streamlit 전체 서브모듈을 수집하되 `streamlit.external.langchain` 같은 optional 모듈은 제외해, 실제로 사용하지 않는 LangChain 의존성 경고가 빌드를 오염시키지 않도록 유지합니다.
- `monitor.spec`는 일반 PC CPU 코어 온도 워커를 위해 `pythonnet`, `clr_loader`, `Python.Runtime.dll` 계열 런타임 파일과 `lhm-bundle/` 디렉터리도 함께 포함해야 합니다.
- `monitor.spec`는 일반 PC CPU 코어 온도 워커를 위해 `pythonnet`, `clr_loader`, `Python.Runtime.dll` 계열 런타임 파일도 함께 포함해야 합니다.
- 포터블 배포 흐름을 바꿀 때는 `build.bat`, `monitor.spec`, `run_app.py`, `start_monitor.bat`, 관련 문서를 함께 확인합니다.
- Playwright MCP는 Node.js LTS와 로컬 `tools/playwright-mcp/` 패키지 설치를 전제로 하며, 기본 브라우저 채널은 `msedge`, 기본 실행 모드는 `headless + isolated` 입니다. Codex stdio 연결에서는 PowerShell 래퍼보다 Node CLI 직결 구성이 필요합니다.

## 문서 업데이트 트리거

- 실행 인자 규칙, EXE 진입점, 빌드 스크립트, 배포 산출물이 바뀌면 이 문서를 업데이트합니다.
