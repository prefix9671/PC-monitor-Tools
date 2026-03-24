# 시스템 리소스 모니터 (System Resource Monitor)

Windows 11 워크스테이션을 위한 고성능, 정밀 시스템 리소스 모니터링 도구입니다.
**Python `psutil`** 기반의 네이티브 수집기를 사용하여 **1초 샘플링 / 5초 Peak·Avg 집계** 방식으로 시스템 전반의 미세한 피크와 상세 프로세스 점유율을 동시에 추적합니다.

## ✨ 주요 기능 (Features)

### 1. Python 네이티브 모니터링 (psutil Collector)
- **샘플링 주기**: **1초** (고정밀)
- **집계 주기**: **5초** (Peak/Average)
- **대상**: 전체 CPU, 메모리(사용량 GB / %), 드라이브별 디스크 I/O(읽기/쓰기 B/s), 디스크 Active Time(%).
- **프로세스 추적**: CPU/메모리/디스크 I/O 상위 5개 프로세스를 5초 윈도우 기준 Peak값으로 기록.
- **드라이브 매핑**: 수집기 시작 시 Windows 파티션 정보를 자동 조회하여 `PhysicalDriveX` → 실제 드라이브 문자(`C:`, `D:`)로 변환.

### 2. 인터랙티브 대시보드
- **기술 스택**: Python [Streamlit](https://streamlit.io/) + [Plotly](https://plotly.com/).
- **기능**:
    - **날짜 기반 자동 로드**: 오늘 기준 최근 1주일(7일) 이내의 로그를 자동 선택하여 즉시 표시.
    - **데이터 통합**: `resource_*.csv`와 `process_*.csv`를 Timestamp 기준 Exact Merge로 완벽 병합.
    - **시각화**: 5초 단위의 정밀한 타임라인 그래프 위에 상위 프로세스 정보를 오버레이.
    - **편의성**: 관리자 권한으로 모니터링 시작, 로그 파일 자동 탐색.

## 🚀 사용 방법 (Usage)

### 1. 모니터링 시작 (데이터 수집)
제공된 배치 파일을 **관리자 권한**으로 실행합니다.

```cmd
start_monitor.bat
```
- Python `psutil` 기반 수집기(`collector_main.py`)가 실행됩니다.
- 로그 파일은 `C:\SystemLogs` 폴더에 자동 저장됩니다.
    - 리소스 로그: `resource_YYYYMMDD.csv`
    - 프로세스 로그: `process_YYYYMMDD.csv`
    - 요약 로그: `summary_YYYYMMDD.log`
- 종료하려면 실행된 창에서 <kbd>Ctrl</kbd> + <kbd>C</kbd>를 누르거나 창을 닫으세요.

### 2. 대시보드 실행 (분석)
빌드된 실행 파일(`SystemResourceMonitor_....exe`) 또는 파이썬 스크립트를 실행합니다.

**실행 파일 사용 시:**
1. `SystemResourceMonitor_xxxx_revX.exe` 실행.
2. 실행 시 자동으로 웹 브라우저가 열리며 대시보드가 표시됩니다.
3. 좌측 사이드바에서 최근 1주일 이내의 로그가 자동 선택됩니다.

**개발 환경 실행 시 (시스템 진입점):**
```bash
# 가상환경 파이썬 직접 실행 (권장)
.\venv\Scripts\python -m streamlit run app.py

# 또는 가상환경 활성화 후 실행
.\venv\Scripts\Activate.ps1
python -m streamlit run app.py
```

## 📂 폴더 구조 (Project Structure)

```
PC-monitor-Tools/
├── app.py                  # Streamlit 메인 애플리케이션 (날짜 기반 로그 선택, 시각화)
├── collector_main.py       # Python psutil 수집기 메인 루프
├── collectors/             # 수집 엔진 모듈 (샘플러, 집계기, 파일 라이터)
├── data_loader.py          # 신규 CSV 로딩 및 Exact Merge 로직
├── parsers.py              # 로그 파싱 유틸리티
├── dashboards/             # 대시보드 모듈 (CPU, Memory, Storage, Custom)
├── config.py               # 전역 설정 (로그 경로, 수집 주기 등)
├── Monitor.ps1             # 수집기 실행 래퍼 (PowerShell)
├── start_monitor.bat       # 수집기 실행 래퍼 (Batch)
├── monitor.spec            # PyInstaller 빌드 설정
├── build.bat               # 통합 빌드 스크립트
└── requirements.txt        # Python 의존성
```

상세 구조 및 설명은 [docs/project_structure.md](docs/project_structure.md)를 참고하세요.

## 🛠 빌드 방법 (Building)

소스 코드를 수정 후 배포용 파일을 생성하려면 `build.bat`을 실행하세요.

```cmd
build.bat
```

**`dist/` 폴더 산출물:**
1. **`SystemResourceMonitor_....exe`**: 대시보드 실행 파일.
2. **`start_monitor.bat`**: 모니터링 실행 스크립트.
3. **`Monitor.ps1`**: 보조 스크립트.
4. **`Manual.zip`**: 사용자 매뉴얼 (웹 문서).

## 📋 요구 사항 (Requirements)
- **OS**: Windows 10/11
- **권한**: 관리자 권한 (프로세스 정보 접근 및 디스크 카운터용)
- **Python**: 3.9+ (개발 및 실행 시)
- **주요 라이브러리**: `psutil`, `pandas`, `streamlit`, `plotly`

