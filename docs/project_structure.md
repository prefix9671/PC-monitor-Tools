# 프로젝트 구조 및 함수 트리

이 문서는 `System Resource Monitor`의 현재 코드 구조를 빠르게 파악하고, 수정 시 영향 범위를 줄이기 위한 **유지보수 기준 문서**입니다.

업데이트 기준: 2026-02-09

## 1. 상위 디렉토리 구조

```text
PC-monitor-Tools/
├─ app.py
├─ data_loader.py
├─ parsers.py
├─ excel_exporter.py
├─ config.py
├─ run_app.py
├─ dashboards/
│  ├─ cpu.py
│  ├─ memory.py
│  ├─ storage.py
│  └─ custom.py
├─ docs/
│  ├─ index.md
│  ├─ project_structure.md
│  ├─ user_manual.md
│  └─ optimization_proposal.md
├─ mkdocs.yml
├─ requirements.txt
├─ Monitor.ps1
├─ start_monitor.bat
├─ build.bat
└─ monitor.spec
```

## 2. 모듈 역할 요약

| 파일/디렉토리 | 역할 |
|---|---|
| `app.py` | Streamlit 메인 엔트리. 파일 선택, 시간 필터, 탭 라우팅, KPI 렌더를 담당 |
| `data_loader.py` | CSV/Parquet 로딩, 파일 타입별 정규화, 병합(`merge_asof`), 캐시 처리 |
| `parsers.py` | Top5 문자열 컬럼 파싱(프로세스별 최대값/시계열) |
| `excel_exporter.py` | 선택된 컬럼과 Top5 컬럼을 엑셀로 내보내기 |
| `dashboards/` | CPU/Memory/Storage/Custom 시각화 화면 모듈 |
| `docs/` | MkDocs 원본 문서 |
| `mkdocs.yml` | 문서 사이트 네비게이션/테마 설정 |
| `Monitor.ps1` | 수집 스크립트(로그 생성) |
| `start_monitor.bat` | 모니터링 스크립트 실행 진입점 |
| `build.bat`, `monitor.spec` | 배포 빌드 자동화(PyInstaller) |

## 3. 실행/데이터 흐름

1. 로그 수집: `Monitor.ps1`가 CSV 로그 생성
2. UI 진입: `app.py` 실행 후 로그 파일 선택
3. 데이터 준비: `load_data()`가 파일을 병렬 처리 후 시간축 기준 병합
4. 시각화: 대시보드 함수가 Plotly figure 생성 후 렌더
5. 내보내기: CSV/Excel 다운로드

## 4. 함수 트리 (핵심)

아래 트리는 실제 코드 기준으로 작성했습니다. 
각 함수에 **상세 주석(목적/성능/주의점)**을 포함했습니다.

### 4.1 `data_loader.py`

```text
data_loader.py
├─ _is_parquet_cache_valid(csv_path, parquet_path)
├─ _downcast_numeric(df)
├─ load_data(files)                    # @st.cache_data
└─ process_single_file(f)
```

| 함수 | 상세 주석 |
|---|---|
| `_is_parquet_cache_valid(csv_path, parquet_path)` | 목적: CSV보다 최신인 Parquet만 캐시로 사용. 성능: 불필요한 CSV 재파싱 방지. 주의: 파일 수정시간이 동일/역전된 환경에서는 캐시 재생성이 발생 가능 |
| `_downcast_numeric(df)` | 목적: `float64/int64`를 더 작은 dtype으로 축소. 성능: 메모리와 직렬화(Plotly JSON) 부담 완화. 주의: 극단적으로 큰 정수 범위가 필요한 경우 downcast 결과 확인 필요 |
| `load_data(files)` | 목적: 파일들을 병렬 처리한 뒤 logman/process 데이터를 합치고 시계열 정렬. 핵심: `ThreadPoolExecutor`, `merge_asof`, 파생 컬럼(`Used(GB)`, `Usage(%)`) 계산. 주의: 병합 tolerance(35초)는 수집 주기 변경 시 함께 검토 |
| `process_single_file(f)` | 목적: 단일 파일 타입 판별 후 정규화 처리. logman 파일은 컬럼 rename/타입 변환, process 파일은 Timestamp 정규화. 성능: `pyarrow` 우선 + Parquet 캐시 저장. 주의: 컬럼명 패턴이 바뀌면 정규식 매핑 로직 업데이트 필요 |

### 4.2 `dashboards/storage.py`

```text
dashboards/storage.py
├─ _downsample_for_plot(df, value_cols, max_points=6000)
├─ _collect_drive_columns(columns, prefixes)
└─ render_storage_dashboard(st, df, parse_process_column)
```

| 함수 | 상세 주석 |
|---|---|
| `_downsample_for_plot(df, value_cols, max_points=6000)` | 목적: 대용량 시계열의 전송량을 제한하면서 형태 보존. 방식: 버킷 단위로 `first/last + 로컬 min/max` 인덱스를 유지. 효과: JSON payload를 크게 줄여 렌더 대기시간 단축. 주의: `max_points`를 낮출수록 미세 진동이 생략될 수 있음 |
| `_collect_drive_columns(columns, prefixes)` | 목적: `DiskTime_`, `DiskRead_`, `DiskWrite_` 중 실제 드라이브(`_[A-Z]:`) 컬럼만 선별. 주의: 컬럼 네이밍 규칙이 바뀌면 정규식(`DRIVE_COL_PATTERN`) 수정 필요 |
| `render_storage_dashboard(...)` | 목적: Storage 화면 전체 렌더. 포함 기능: (1) Active Time 라인차트, (2) I/O Throughput 라인차트, (3) Top5 Disk I/O 바차트. 성능 옵션: `Chart Quality(Fast/Balanced/Detailed/Original)` 제공, large dataset에서 원본 모드는 느릴 수 있음 경고 표시 |

#### Storage 품질 모드 주석

| 모드 | 목표 포인트 수 | 사용 시점 |
|---|---:|---|
| `Fast` | 12,000 | 원격 접속/저사양 장비에서 빠른 탐색 |
| `Balanced` (기본) | 30,000 | 일반 분석 기본값 |
| `Detailed` | 60,000 | 형상 확인이 중요한 장애 분석 |
| `Original (slow)` | 제한 없음 | 최종 검증(속도보다 원본 재현 우선) |

### 4.3 `parsers.py`

```text
parsers.py
├─ parse_process_column(df_col)
└─ extract_process_time_series(df, col_name)
```

| 함수 | 상세 주석 |
|---|---|
| `parse_process_column(df_col)` | 목적: `procA:123 | procB:45` 형태 문자열을 파싱해 프로세스별 최대값 산출. 주의: 동일 시점에 동일 프로세스 중복 등장 시 합산 후 최대 비교 |
| `extract_process_time_series(df, col_name)` | 목적: 요약 문자열 컬럼을 시계열 long-format(`Timestamp, Process, Value`)으로 변환. 주의: 데이터량이 큰 경우 후속 필터링(Top N, 시간구간)을 함께 사용 권장 |

### 4.4 `dashboards/*.py`

```text
dashboards/cpu.py
└─ render_cpu_dashboard(st, df)

dashboards/memory.py
└─ render_memory_dashboard(st, df, parse_process_column, extract_process_time_series, total_mem)

dashboards/custom.py
└─ render_custom_dashboard(st, df, parse_process_column)
```

| 함수 | 상세 주석 |
|---|---|
| `render_cpu_dashboard` | CPU 사용률/온도 2축 시각화 및 요약 지표 출력 |
| `render_memory_dashboard` | 메모리/스왑 추이, Top 메모리 프로세스, 프로세스별 시계열 제공 |
| `render_custom_dashboard` | 사용자 선택 컬럼 시계열 + 엑셀 내보내기 UI |

### 4.5 기타 함수

```text
excel_exporter.py
├─ parse_top5_string(data_str)
└─ generate_excel(df, selected_cols)

run_app.py
└─ resolve_path(path)
```

## 5. 문서 유지보수 규칙

1. 함수 시그니처가 바뀌면 이 문서의 함수 트리를 같은 커밋에서 같이 수정
2. 성능 관련 파라미터(`max_points`, cache 조건, merge tolerance) 변경 시 "상세 주석" 섹션 갱신
3. 신규 대시보드 파일 추가 시 `dashboards/*.py` 섹션에 함수/역할 추가
4. 배포 흐름 변경 시 `build.bat`, `monitor.spec`, `run_app.py` 설명 동기화

## 6. 빠른 점검 체크리스트

- `data_loader.py` 변경 후: Parquet 캐시 유효성/병합 결과 확인
- `dashboards/storage.py` 변경 후: 1일/3일 로그 각각에서 렌더 속도와 형상 확인
- `parsers.py` 변경 후: Top5 문자열 이상치(`no_active_io`, 빈 문자열) 회귀 확인
- 문서 변경 후: `mkdocs build`로 링크/렌더 확인
