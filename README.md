# 시스템 리소스 모니터 (System Resource Monitor)

Windows 11 워크스테이션을 위한 고성능, 정밀 시스템 리소스 모니터링 도구입니다.
**Logman(1초 단위)**과 **PowerShell(30초 단위)**을 결합한 하이브리드 모니터링 방식을 사용하여, 시스템 전반의 미세한 피크와 상세 프로세스 점유율을 동시에 추적합니다.

## ✨ 주요 기능 (Features)

### 1. 하이브리드 모니터링 (Hybrid Monitoring)
- **고정밀 모니터 (Logman)**
    - **주기**: **1초** (초정밀)
    - **대상**: 전체 CPU, 가용 메모리, 디스크 I/O (읽기/쓰기), 디스크 큐 길이.
    - **목적**: 순간적인 시스템 부하(튀는 현상)를 놓치지 않고 포착.
- **프로세스 상세 모니터 (PowerShell)**
    - **주기**: **30초** (사용자 설정 가능)
    - **대상**: 메모리 점유 상위 5개 프로세스, 디스크 I/O 상위 5개 프로세스.
    - **목적**: 부하를 유발하는 구체적인 원인(프로세스) 식별.

### 2. 하드웨어 지원
- **CPU**: 사용량(%) 및 온도(°C).
- **GPU**: NVIDIA 외장 그래픽(`nvidia-smi`) 및 Intel/AMD 내장 그래픽(성능 카운터) 동시 지원.
- **Storage**: 드라이브별 사용량 및 실시간 I/O 성능.

### 3. 인터랙티브 대시보드
- **기술 스택**: Python [Streamlit](https://streamlit.io/) + [Plotly](https://plotly.com/).
- **기능**:
    - **데이터 통합**: 서로 다른 주기의 두 로그 파일(Logman, PowerShell)을 자동으로 병합하여 시각화.
    - **시각화**: 1초 단위의 정밀한 타임라인 그래프 위에 상위 프로세스 정보를 오버레이.
    - **편의성**: 관리자 권한으로 모니터링 시작, 로그 파일 자동 탐색.

## 🚀 사용 방법 (Usage)

### 1. 모니터링 시작 (데이터 수집)
제공된 배치 파일을 **관리자 권한**으로 실행합니다.

```cmd
start_monitor.bat
```
- **Logman**과 **PowerShell** 스크립트가 동시에 실행됩니다.
- 로그 파일은 `C:\SystemLogs` 폴더에 자동 저장됩니다.
    - 글로벌 로그: `Global_Usage_YYYYMMDD_HHMM.csv`
    - 프로세스 로그: `System_Log_YYYY-MM-DD.csv`
- 종료하려면 실행된 창에서 아무 키나 누르세요.

### 2. 대시보드 실행 (분석)
빌드된 실행 파일(`SystemResourceMonitor_....exe`) 또는 파이썬 스크립트를 실행합니다.

**실행 파일 사용 시:**
1. `SystemResourceMonitor_xxxx_revX.exe` 실행.
2. 실행 시 자동으로 웹 브라우저가 열리며 대시보드가 표시됩니다.
3. 좌측 사이드바에서 로그 파일이 있는 `C:\SystemLogs` 폴더가 자동 선택됩니다. ("Select from..." 메뉴)

**개발 환경 실행 시:**
```bash
python -m streamlit run app.py
```

## 📂 폴더 구조 (Project Structure)

```
sys_resource_monitor/
├── app.py                  # Streamlit 메인 애플리케이션 (데이터 병합 및 시각화)
├── Monitor.ps1             # PowerShell 프로세스 상세 수집 스크립트
├── start_monitor.bat       # [NEW] 모니터링 통합 실행 스크립트
├── data_loader.py          # 하이브리드 데이터 로딩 및 병합 로직
├── parsers.py              # 로그 파싱 유틸리티
├── dashboards/             # 대시보드 모듈 (CPU, Memory, Storage 등)
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
- **권한**: 관리자 권한 (하드웨어 성능 카운터 및 Logman 접근용)
- **Python**: 3.9+ (개발 및 실행 시)
