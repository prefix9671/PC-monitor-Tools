# Changelog

Updated On: 2026-04-01  
Status: Active

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
