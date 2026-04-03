# Verification Checklist

Updated On: 2026-04-02  
Status: Active

구현을 마친 뒤에는 변경 종류에 따라 아래 검증을 수행합니다.

## 공통

- 영향받는 활성 문서를 함께 업데이트했는지 확인
- `docs/ActiveDocs.md` 기준으로 문서 경로와 우선순위가 유지되는지 확인
- `.\venv\Scripts\python scripts\verify_docs_sync.py`
- 비사소한 코드 변경이 있었다면 이 문서(`docs/Current Phase/VerificationChecklist.md`)가 같은 변경 안에서 갱신되었는지 확인
- 우선순위, 리스크, 운영 기준이 바뀌었다면 `docs/Current Phase/CurrentPhase.md`도 함께 갱신되었는지 확인

## 수집기 또는 로그 스키마 변경

- `.\venv\Scripts\python -m pytest tests\test_cli.py`
- `.\venv\Scripts\python cli.py probe-temp`
- Dell Precision T5/T7 Tower 제어 PC라면 `start` 또는 `probe-temp` 실행 시 DCM 자동 설치/준비 메시지가 보이는지 확인
- Dell 제어 PC라면 `probe-temp`가 가능할 때 `Source: DellCommandMonitor`를 우선 보고하는지 확인
- Dell 제어 PC라면 CPU 온도가 `5.x°C`처럼 비현실적으로 낮게 표시되지 않고, 실제 장비 상태에 맞는 값으로 보이는지 확인
- 일반 PC라면 DCM 설치 시도를 건너뛰고 Libre/OpenHardwareMonitor 또는 Thermal Zone fallback으로 계속 동작하는지 확인
- CLI 경로로 기능을 확인할 수 있다면 목적에 맞는 Smoke Test 수행
- 실제 CSV 컬럼명이 대시보드 기대값과 맞는지 확인
- 같은 날짜 로그 파일에 새 컬럼이 추가될 때 CSV 헤더가 깨지지 않는지 확인
- 구조가 바뀌면 `Architecture/SystemOverview.md`와 `Wiki/ProjectStructure.md` 업데이트

## AOI / Inspector 로그 변경

- `.\venv\Scripts\python aoi_cli.py summary --path "C:\Inspector\shared\operation_0319_north side grab"`
- `.\venv\Scripts\python aoi_cli.py export --path "C:\Inspector\shared\operation_0319_north side grab" --system-path "C:\SystemLogs\resource_YYYYMMDD.csv" --out ".\inspection_export.xlsx"`
- AOI 경로가 파일, 폴더, 확장자 없는 기본 경로를 모두 처리하는지 확인
- `Memory AND Inspector Dashboard`에서 인스펙터 요약 지표와 외부 시스템 메모리 비교가 보이는지 확인
- 메인 화면 대시보드 아래 `검사 결과 XLSX 내보내기` 영역에서 모델명, 총 검사 수, 시작/종료 NO, 미리보기, 다운로드가 모두 보이는지 확인
- 메모리 대시보드에서 중복 인스펙터 상세 차트가 미노출되고, 상세 시계열 안내가 하단 검사 결과 패널로 연결되는지 확인
- `그래프 형식`, 항목별 이름 기반 색상, 표 강조 색상, 투명도 옵션을 바꿨을 때 미리보기 그래프와 표 강조가 함께 반영되는지 확인
- `Memory (시스템)` 값이 검사 시각의 직전 시스템 샘플과 맞는지 확인

## 대시보드 또는 로더 변경

- `.\venv\Scripts\python verify_dashboards.py`
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\playwright-mcp\verify-playwright-mcp.ps1`
- 최근 로그를 읽어 `CPU`, `Memory`, `Storage`, `Custom Graph`가 모두 뜨는지 확인
- `CPU 대시보드`에서 `CPU 사용률과 온도`, `CPU 온도 추이`가 함께 보이고, 온도가 5초 구간 최고값 기준으로 표시되는지 확인
- 주요 버튼, 메뉴, 차트 제목, KPI 라벨이 한국어 UI 기준으로 자연스럽게 보이는지 확인
- `Time Range` 슬라이더와 `Start Time` / `End Time` 직접 입력이 함께 동작하는지 확인
- 시작만 입력했을 때 끝까지, 종료만 입력했을 때 처음부터, 둘 다 입력했을 때 해당 범위만 보이는지 확인
- 없는 시각을 입력했을 때 시작은 다음 샘플, 종료는 이전 샘플로 보정되는지 확인
- Playwright MCP가 구성된 세션에서는 WEB 기반 GUI 검증을 우선하고, 현재 세션에서 `unknown MCP server 'playwright'`가 보이면 Codex 앱 재실행 후 새 세션에서 다시 확인
- 재실행 전에는 `verify_dashboards.py`, AOI CLI export Smoke Test, Streamlit 수동 확인 결과를 함께 남김
- 사용자 흐름이 바뀌면 `Wiki/UserManual.md` 업데이트

## CI 또는 문서 자동화 변경

- `.\venv\Scripts\python scripts\run_ci_dashboard_smoke.py`
- `.\venv\Scripts\python scripts\verify_docs_sync.py`
- GitHub Actions `windows-ci.yml`이 새 검증을 포함하는지 확인
- CI 변경이라면 `docs/Wiki/ReliabilityReport.md`도 같은 변경 안에서 갱신했는지 확인

## 실행 또는 패키징 변경

- `.\venv\Scripts\python -m mkdocs build`
- 관련 기능이 CLI 진입점과 연결된다면 최소 Smoke Test를 추가 수행
- 필요 시 `build.bat` 실행 후 산출물 확인
- `Architecture/RuntimeAndPackaging.md`와 `Wiki/Changelog.md` 업데이트

## 문서만 변경했을 때

- `.\venv\Scripts\python -m mkdocs build`
- 링크, 이미지 경로, nav 구성이 정상인지 확인
