# Changelog

Updated On: 2026-03-31  
Status: Active

## [2026-03-31] - Time Range 직접 입력 추가

### 변경 사항

- `Time Range` 슬라이더와 함께 `Start Time`, `End Time` 직접 입력 UI를 추가했습니다.
- 시작만 입력하면 해당 시각부터 로그 끝까지, 종료만 입력하면 로그 처음부터 해당 시각까지 보이도록 확장했습니다.
- 입력한 시각과 정확히 일치하는 데이터가 없을 때 시작은 다음 샘플, 종료는 이전 샘플로 자동 보정하도록 정리했습니다.
- 수동 시각 입력 규칙을 `data_loader.py`의 순수 함수로 분리해 UI와 필터 로직을 분리했습니다.
- 사용자 메뉴얼과 검증 체크리스트를 새 시간 필터 흐름에 맞게 업데이트했습니다.

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
