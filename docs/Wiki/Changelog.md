# Changelog

Updated On: 2026-03-30  
Status: Active

## [2026-03-30] - 문서 거버넌스 재구성

### 변경 사항

- `docs` 폴더를 `Architecture`, `Best Practices`, `Wiki`, `Future`, `Current Phase` 구조로 재편했습니다.
- `docs/ActiveDocs.md`를 추가해 활성 문서 인덱스를 만들었습니다.
- `AGENTS.md`를 추가해 에이전트가 계획 수립 전과 구현 후에 문서를 확인하도록 규칙을 정의했습니다.
- 기존 루트 문서는 호환성 stub로 남기고, 활성 문서는 새 경로로 이동했습니다.

### AOI / Inspector 로그 연동

- 사용자가 AOI / Inspector 로그 파일 경로를 직접 입력할 수 있도록 Streamlit UI를 확장했습니다.
- `inspector_logs/core.py`와 `aoi_cli.py`를 추가해 AOI 로그 파서 코어와 CLI Smoke Test 경로를 분리했습니다.
- 메모리 탭을 `Memory AND Inspector Dashboard`로 확장하고, `Frame`, `Total`, `Working Set` 시각화와 `Inspector APP (log)` 비교를 추가했습니다.
- AOI / Inspector 로그는 이제 `Browse files` 기반 업로드 선택을 기본으로 지원하고, 경로 입력은 고급 옵션으로 유지했습니다.

## [2026-03-25] - 포터블 배포 대응 및 수집기 정교화

### 해결된 버그

- 포터블 실행 시 경로 인식 오류를 줄이기 위해 EXE 기준 실행 흐름을 정리했습니다.
- PyInstaller 임시 경로와 원본 EXE 경로의 혼동 문제를 완화했습니다.

### 기능 개선

- `run_app.py` 기반 단일 진입점 구조를 도입했습니다.
- 디스크 활성 시간 퍼센트 표현을 사용자 관점에서 더 직관적으로 보정했습니다.

### 문서 및 테스트

- 포터블 배포 검증을 위한 `test_portable.bat`를 추가했습니다.

## [2026-03-24] - 파이썬 네이티브 수집기 마이그레이션

### 주요 변경 사항

- 기존 하이브리드 수집 방식에서 `psutil` 기반 네이티브 수집기로 전환했습니다.
- `data_loader.py`를 exact merge 기반 로딩 구조로 단순화했습니다.
- 대시보드가 5초 집계 컬럼을 직접 참조하도록 정리했습니다.
- `verify_dashboards.py` 기반 헤드리스 자가 검증 루틴을 추가했습니다.
