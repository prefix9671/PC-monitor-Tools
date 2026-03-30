# Engineering Guidelines

Updated On: 2026-03-30  
Status: Active

## 현재 프로젝트에서 중요한 개발 규칙

- Windows 전용 운영 가정을 깨지 않도록 변경합니다.
- 로그 스키마 변경은 매우 비싸므로, 바꿀 때는 수집기, 로더, 대시보드, 문서를 한 번에 맞춥니다.
- 기본 수집 계약은 1초 샘플링과 5초 집계입니다. 이 값을 바꾸면 구조 문서와 검증 절차를 같이 갱신합니다.
- `build/`, `dist/`, `site/`는 생성 결과물이며 수정 기준이 아닙니다.
- 프로그램 추가, 변경, 삭제 시 메인 로직 코어와 CLI 도구, GUI 도구를 분리합니다.
- 코어 파일이 대략 500~600라인을 넘기기 시작하면 역할별 계층으로 분리하는 것을 기본 원칙으로 삼습니다.

## 변경 시 주의 포인트

### 수집기 변경

- `collectors/sampler.py`, `collectors/aggregator.py`, `collectors/writers.py`는 서로 강하게 연결되어 있습니다.
- CSV 컬럼명은 대시보드와 파서가 직접 참조하므로, 이름이 바뀌면 `data_loader.py`, `dashboards/*.py`, `parsers.py`를 함께 점검합니다.

### 대시보드 변경

- `app.py`와 `dashboards/*.py`는 `load_data()`가 반환하는 컬럼 구조를 전제로 합니다.
- 대용량 로그에서의 렌더 성능을 유지해야 하므로 `storage.py`의 다운샘플링 전략을 함부로 제거하지 않습니다.
- GUI 계층에는 화면 흐름과 입출력만 두고, 핵심 로직은 코어 계층으로 밀어냅니다.

### 패키징 변경

- `run_app.py`, `monitor.spec`, `build.bat`, `start_monitor.bat`는 하나의 배포 흐름으로 봅니다.
- 개발 환경 실행과 패키징 환경 실행을 분리해서 생각합니다.

### 기능 추가 또는 구조 개편

- 가능하면 코어 로직을 먼저 구현하고 CLI 경로를 붙여 Smoke Test로 목적 적합성을 확인한 뒤 GUI를 연결합니다.
- CLI와 GUI가 같은 로직을 각자 복제하지 않도록 공통 코어를 통해 연결합니다.

## 권장 검증

- CLI/수집기: `.\venv\Scripts\python -m pytest tests\test_cli.py`
- 대시보드 파이프라인: `.\venv\Scripts\python verify_dashboards.py`
- 문서: `.\venv\Scripts\python -m mkdocs build`
- 새 기능이나 변경 기능이 CLI 경로를 가진다면 간단한 Smoke Test를 추가하거나 실행합니다.

## 문서 동기화 규칙

- 코드가 바뀌면 관련 활성 문서도 같은 변경에서 갱신합니다.
- 현재 동작이 아니라 계획이라면 `Future` 폴더에 기록합니다.
- 구현 기준과 계획이 충돌하면 구현 기준 문서를 먼저 맞추고, `Future`는 별도로 조정합니다.
