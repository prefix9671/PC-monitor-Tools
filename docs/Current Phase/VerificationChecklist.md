# Verification Checklist

Updated On: 2026-03-31  
Status: Active

구현을 마친 뒤에는 변경 종류에 따라 아래 검증을 수행합니다.

## 공통

- 영향받는 활성 문서를 함께 업데이트했는지 확인
- `docs/ActiveDocs.md` 기준으로 문서 경로와 우선순위가 유지되는지 확인

## 수집기 또는 로그 스키마 변경

- `.\venv\Scripts\python -m pytest tests\test_cli.py`
- CLI 경로로 기능을 확인할 수 있다면 목적에 맞는 Smoke Test 수행
- 실제 CSV 컬럼명이 대시보드 기대값과 맞는지 확인
- 구조가 바뀌면 `Architecture/SystemOverview.md`와 `Wiki/ProjectStructure.md` 업데이트

## AOI / Inspector 로그 변경

- `.\venv\Scripts\python aoi_cli.py summary --path "C:\Inspector\shared\operation_0319_north side grab"`
- AOI 경로가 파일, 폴더, 확장자 없는 기본 경로를 모두 처리하는지 확인
- `Memory AND Inspector Dashboard`에서 `Frame`, `Total`, `Working Set`이 모두 보이는지 확인

## 대시보드 또는 로더 변경

- `.\venv\Scripts\python verify_dashboards.py`
- 최근 로그를 읽어 `CPU`, `Memory`, `Storage`, `Custom Graph`가 모두 뜨는지 확인
- 주요 버튼, 메뉴, 차트 제목, KPI 라벨이 한국어 UI 기준으로 자연스럽게 보이는지 확인
- `Time Range` 슬라이더와 `Start Time` / `End Time` 직접 입력이 함께 동작하는지 확인
- 시작만 입력했을 때 끝까지, 종료만 입력했을 때 처음부터, 둘 다 입력했을 때 해당 범위만 보이는지 확인
- 없는 시각을 입력했을 때 시작은 다음 샘플, 종료는 이전 샘플로 보정되는지 확인
- 사용자 흐름이 바뀌면 `Wiki/UserManual.md` 업데이트

## 실행 또는 패키징 변경

- `.\venv\Scripts\python -m mkdocs build`
- 관련 기능이 CLI 진입점과 연결된다면 최소 Smoke Test를 추가 수행
- 필요 시 `build.bat` 실행 후 산출물 확인
- `Architecture/RuntimeAndPackaging.md`와 `Wiki/Changelog.md` 업데이트

## 문서만 변경했을 때

- `.\venv\Scripts\python -m mkdocs build`
- 링크, 이미지 경로, nav 구성이 정상인지 확인
