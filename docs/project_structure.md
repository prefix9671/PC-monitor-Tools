# 프로젝트 구조 (Project Structure)

이 문서는 **System Resource Monitor** 프로젝트의 파일 구조 및 주요 구성 요소에 대한 최신 정보를 제공합니다.

## 루트 디렉토리 (Root Directory)

| 파일/디렉토리 | 설명 |
| :--- | :--- |
| `app.py` | Streamlit 대시보드의 메인 진입점. UI 레이아웃, 사이드바 제어 및 모듈 렌더링을 담당합니다. |
| `Monitor.ps1` | 실시간 데이터 수집기(PowerShell). CPU, 메모리, GPU, 디스크 성능을 수집해 CSV로 저장합니다. |
| `excel_exporter.py` | **[NEW]** 선택한 지표 및 상위 프로세스 정보를 엑셀(`.xlsx`) 파일로 변환하는 모듈입니다. |
| `mkdocs.yml` | **[NEW]** MkDocs Material 웹 매뉴얼 사이트의 설정 및 테마 구성을 정의하는 파일입니다. |
| `site/` | **[NEW]** `mkdocs build` 명령어를 통해 생성된 정적 웹 매뉴얼 사이트 결과물입니다. |
| `config.py` | 로그 디렉토리 및 애플리케이션 상수 설정을 포함합니다. |
| `data_loader.py` | 수집된 CSV 로그를 효율적으로 로딩하고 캐싱하는 데이터 처리 모듈입니다. |
| `parsers.py` | 로그 데이터 가공 및 상위 점유 프로세스 정보 추출을 위한 유틸리티입니다. |
| `run_app.py` | PyInstaller 빌드 시 실행 파일을 구동하기 위한 래퍼 스크립트입니다. |
| `monitor.spec` | **[UPDATE]** `site/` 폴더와 `excel_exporter`를 포함하도록 업데이트된 빌드 명세 파일입니다. |
| `build.bat` | **[UPDATE]** 웹 매뉴얼 빌드와 PyInstaller 빌드를 한 번에 수행하는 자동화 스크립트입니다. |
| `requirements.txt` | `openpyxl`, `mkdocs-material` 등 확장된 의존성 라이브러리 목록입니다. |
| `dashboards/` | CPU, 메모리, 저장공간 등 각 대시보드 화면을 담당하는 모듈 폴더입니다. |
| `docs/` | 매뉴얼 원본 마크다운, 이미지 및 스타일시트를 포함하는 문서 폴더입니다. |

## 대시보드 디렉토리 (`dashboards/`)

| 파일 | 설명 |
| :--- | :--- |
| `cpu.py` | CPU 사용률 및 온도 추이를 시각화합니다. |
| `memory.py` | 메모리 사용량 점유율 및 상위 Memory Offender를 분석합니다. |
| `storage.py` | 각 드라이브별 I/O 스피드와 상위 Disk I/O 프로세스를 시각화합니다. |
| `custom.py` | **[UPDATE]** 사용자가 직접 지표를 선택하고, 시작 시간을 지정하여 엑셀로 내보내는 통합 분석 뷰입니다. |

## 문서 디렉토리 (`docs/`)

-   `index.md`: 웹 매뉴얼 사이트의 메인 홈 페이지.
-   `user_manual.md`: **[UPDATE]** 기능 상세 가이드 및 툴바 조작법이 포함된 통합 매뉴얼 원본.
-   `stylesheets/extra.css`: 웹 매뉴얼의 가독성 향상(리스트 간격 등)을 위한 커스텀 스타일.
-   `images/`: 매뉴얼에 사용되는 대시보드 및 툴바 스크린샷 이미지들.

## 데이터 및 제어 흐름 (Data & Control Flow)

1.  **데이터 수집**: 사용자가 UI에서 'Start Monitor'를 누르면 `Monitor.ps1`이 실행되어 CSV 로그를 생성합니다.
2.  **데이터 조회**: `app.py`에서 로그를 선택하면 `data_loader.py`와 `parsers.py`가 데이터를 정제합니다.
3.  **결과 출력**: `dashboards/` 모듈들이 Plotly 차트를 생성하고, `excel_exporter.py`가 필요시 엑셀 보고서를 작성합니다.
4.  **매뉴얼 서빙**: `build.bat` 실행 시 MkDocs가 `docs/`를 `site/`로 빌드하여 실행 파일 내에서 웹 기반 매뉴얼을 볼 수 있게 합니다.
