# Project Structure

Updated On: 2026-03-30  
Status: Active

## 루트 구조

```text
PC-monitor-Tools/
├─ aoi_cli.py
├─ app.py
├─ cli.py
├─ config.py
├─ data_loader.py
├─ excel_exporter.py
├─ inspector_logs/
├─ parsers.py
├─ run_app.py
├─ verify_dashboards.py
├─ collectors/
├─ dashboards/
├─ tests/
├─ docs/
├─ build.bat
├─ start_monitor.bat
├─ Monitor.ps1
├─ monitor.spec
├─ mkdocs.yml
└─ requirements.txt
```

## 핵심 디렉토리

| 경로 | 설명 |
|---|---|
| `collectors/` | 샘플링, 집계, 로그 기록을 담당하는 수집 엔진 |
| `dashboards/` | CPU, Memory, Storage, Custom 화면 |
| `tests/` | 현재는 CLI 기반 기본 검증 테스트 포함 |
| `docs/` | 사람과 에이전트를 위한 기준 문서 |

## 주요 파일 역할

| 파일 | 설명 |
|---|---|
| `app.py` | Streamlit 메인 앱 |
| `aoi_cli.py` | AOI / Inspector 로그 파서 요약 CLI |
| `cli.py` | 수집기 CLI |
| `run_app.py` | 패키징된 EXE의 단일 진입점 |
| `data_loader.py` | CSV 로딩, 캐시, exact merge |
| `inspector_logs/` | AOI / Inspector 로그 경로 해석과 이벤트 파싱 코어 |
| `parsers.py` | Top 5 문자열 파싱 |
| `excel_exporter.py` | 엑셀 내보내기 |
| `verify_dashboards.py` | 헤드리스 대시보드 자가 점검 |
| `build.bat` | 문서 사이트와 EXE 빌드 |

## `docs` 구조

```text
docs/
├─ ActiveDocs.md
├─ DocsHub.md
├─ index.md
├─ Architecture/
├─ Best Practices/
├─ Current Phase/
├─ Future/
├─ Wiki/
├─ images/
└─ stylesheets/
```

## 참고 메모

- `build/`, `dist/`, `site/`는 생성 산출물이므로 구조 설명의 기준이 아닙니다.
- 현재 문서 탐색 시작점은 `docs/ActiveDocs.md` 입니다.
- 더 상세한 아키텍처 설명은 [../Architecture/SystemOverview.md](../Architecture/SystemOverview.md)를 참고합니다.
