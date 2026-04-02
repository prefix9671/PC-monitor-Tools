# Runtime And Packaging

Updated On: 2026-04-02  
Status: Active

## 실행 모드

이 프로젝트는 크게 두 가지 모드를 가집니다.

1. 대시보드 모드
2. 수집기 모드

패키징된 EXE에서는 `run_app.py`가 단일 진입점 역할을 하며, `start` 인자가 있으면 수집기로, 없으면 Streamlit 대시보드로 동작합니다.

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
| `aoi_cli.py` | AOI 로그 파서 Smoke Test 및 요약 확인용 CLI |
| `build.bat` | MkDocs 빌드, PyInstaller 실행, 산출물 복사/압축 |
| `monitor.spec` | PyInstaller 입력 정의 |
| `start_monitor.bat` | 관리자 권한 확인 후 EXE를 `start` 인자와 함께 실행 |
| `Monitor.ps1` | 공식 정리 대상인 호환성 스텁 |
| `scripts/run_ci_dashboard_smoke.py` | CI에서 샘플 로그로 대시보드 스모크 검증 |
| `scripts/verify_docs_sync.py` | 코드 변경과 활성 문서 변경의 동기화 확인 |
| `tools/playwright-mcp/launch-playwright-mcp.ps1` | 로컬 Playwright MCP 서버 래퍼 |
| `tools/playwright-mcp/verify-playwright-mcp.ps1` | 로컬 Playwright MCP 서버 Smoke Test |

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
- WEB GUI 자동화 기준 래퍼는 `tools/playwright-mcp/launch-playwright-mcp.ps1` 입니다.
- Codex Desktop용 MCP 연결은 사용자 로컬 `C:\Users\Win11_SPC_General\.codex\config.toml`의 `[mcp_servers.playwright]` 항목을 사용합니다.

## 알려진 주의 사항

- `Monitor.ps1`는 공식 정리 대상이며 배포 산출물에 포함하지 않습니다. 필요할 때만 레거시 안내용 스텁으로 취급합니다.
- Streamlit 앱이 런타임에 불러오는 로컬 파이썬 모듈은 `monitor.spec`의 `datas`에 포함되어야 합니다. 예를 들어 `inspector_logs/` 같은 폴더가 빠지면 EXE에서 `ModuleNotFoundError`가 발생할 수 있습니다.
- 포터블 배포 흐름을 바꿀 때는 `build.bat`, `monitor.spec`, `run_app.py`, `start_monitor.bat`, 관련 문서를 함께 확인합니다.
- Playwright MCP는 Node.js LTS와 로컬 `tools/playwright-mcp/` 패키지 설치를 전제로 하며, 기본 브라우저 채널은 `msedge`, 기본 실행 모드는 `headless + isolated` 입니다.

## 문서 업데이트 트리거

- 실행 인자 규칙, EXE 진입점, 빌드 스크립트, 배포 산출물이 바뀌면 이 문서를 업데이트합니다.
