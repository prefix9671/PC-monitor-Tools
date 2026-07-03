# Reliability Report

Updated On: 2026-07-03
Status: Active

## 개요

이 프로젝트는 시스템 리소스 병목을 추적하기 위한 관측 도구입니다. 현재 구현은 애플리케이션 내부를 수정하지 않고 OS 수준의 정보를 수집해 CSV로 기록한 뒤, 후속 분석을 대시보드에서 수행하는 구조를 사용합니다.

## 현재 신뢰성 가정

- 수집은 `psutil` 기반의 별도 프로세스로 수행됩니다.
- 일반 PC CPU 코어 온도는 `pythonnet + LibreHardwareMonitorLib.dll` 백그라운드 워커가 별도로 측정해 JSON 상태 파일로 넘깁니다.
- 분석은 저장된 CSV를 읽는 방식이므로 운영 대상 프로세스와 분리됩니다.
- 원시 1초 샘플은 5초 윈도우로 집계되어 대시보드에서 다루기 쉬운 형태로 정리됩니다.

## 운영 측면 장점

### 낮은 결합도

- 수집기와 대시보드는 분리되어 있어 분석 UI가 수집 파이프라인을 직접 막지 않습니다.
- 수집 결과는 파일로 남기므로 나중에 다시 로드해 비교할 수 있습니다.
- LibreHardwareMonitor 번들을 EXE에 함께 동봉해, 현장 PC의 SSL 인증서나 외부망 차단 때문에 GitHub 다운로드가 막혀도 기본 온도 경로를 유지할 수 있습니다.
- LibreHardwareMonitor 0.9.6 계열에서 필요한 PawnIO 설치기도 `pawnio-bundle/PawnIO_setup.exe`로 함께 동봉해, 외부망이 막힌 현장에서도 `install_pawnio.bat` 또는 `SystemResourceMonitor*.exe install-pawnio`로 드라이버 설치를 시도할 수 있습니다.
- 일반 PC CPU 코어 온도는 별도 워커와 파일 기반 handoff 를 써서, 1초 샘플링 루프가 하드웨어 센서 초기화나 DLL 로드 비용에 직접 묶이지 않습니다.
- 대시보드의 `모니터링 시작` 버튼은 PowerShell 대신 Windows ShellExecute `runas`를 직접 사용해, 현장 PC의 PowerShell 5.1/7 런타임 손상과 수집기 시작 경로를 분리합니다.
- Dell DCM, OpenHardwareMonitor, PerfRaw Thermal Zone, MSAcpi Thermal Zone, 물리 메모리, 드라이브 매핑은 `pythonnet + System.Management` WMI 직접 조회를 사용하므로 현장 PC의 PowerShell 런타임 손상과 수집 fallback 경로를 분리합니다.

### 시간축 일관성

- `resource`와 `process` 로그가 같은 5초 경계로 정렬되어 생성됩니다.
- `data_loader.py`는 이 가정을 이용해 exact merge를 수행하므로, 구간 분석이 단순하고 재현 가능합니다.

### 병목 추적 적합성

- CPU 평균/피크, 메모리 사용량, 드라이브별 I/O, 프로세스 Top 5를 함께 봅니다.
- 특정 시점의 스파이크와 상위 프로세스를 교차 비교하기 좋습니다.

## QA 와 운영에서 기대할 수 있는 효과

- 장시간 실행 중 메모리 증가 추세 확인
- 디스크 처리량 급증 구간 파악
- 특정 프로세스가 자원 피크를 유발하는 시점 식별
- 로그를 보존해 장애 재분석 가능
- CI에서 단위 테스트, 대시보드 스모크, 문서 동기화 검사를 함께 돌려 회귀를 더 일찍 발견 가능
- CI의 Python 의존성은 `runtime_patches.py` 테스트가 직접 사용하는 `tornado`를 명시 설치해, GitHub Actions의 깨끗한 runner 에서도 로컬 Streamlit 환경과 같은 import 조건으로 검증 가능
- GitHub Actions 공식 JavaScript action 은 Node.js 24 기반 major 버전을 사용해 Node.js 20 deprecation 경고가 CI 실패 원인과 섞이지 않도록 유지
- PyInstaller가 실제 미사용 optional 모듈에 끌려가지 않도록 패키징 대상을 좁혀 빌드 경고 노이즈를 줄일 수 있음
- 일반 PC CPU 온도 경로는 동봉된 LibreHardwareMonitor 번들을 우선 사용하고, 추가로 캐시/다운로드와 OpenHardwareMonitor / Thermal Zone fallback 을 유지해 현장 대응 폭을 넓힐 수 있음
- PawnIO 미설치 상태는 `start_monitor.bat`의 사전 확인과 CPU 온도 진단 로그의 `lhm_worker.pawnio` 섹션에서 확인할 수 있음
- PowerShell이 실행되지 않는 PC에서도 WMI provider 자체가 정상이라면 Dell/Advantech 온도 fallback과 디스크 문자 매핑을 계속 시도할 수 있음
- Playwright MCP 브라우저 검증은 stdio 직결 구성으로 유지해 GUI 자동화에서 연결 실패 가능성을 낮출 수 있음
- 작업 완료 후 `scripts/verify_playwright_dashboards.js`로 실제 Streamlit 대시보드 4종을 다시 열어 보고, 스크린샷과 콘솔 메시지를 아티팩트로 남길 수 있음
- `scripts/run_prebuild_regression.py`는 bug 폴더의 고정 입력 로그와 headless Playwright를 묶어, 빌드 전에 같은 회귀 시나리오를 반복 실행할 수 있음
- 같은 prebuild 회귀 안에서 최소 fixture `tests\fixtures\inspector_time_filter_range_regression.log`의 `2026-05-13 15:00:00 -> 16:44:59` 필터 결과가 `NO 2 -> 4`, 3건으로 유지되는지 별도 확인해, 시간 필터 후 인스펙터 결과가 1건으로 접히는 UI 상태 회귀를 조기에 탐지할 수 있음
- `scripts/verify_docs_sync.py`는 Playwright 회귀를 직접 실행하지는 않지만, Playwright 회귀 스크립트와 MCP 런처가 바뀌었을 때 관련 활성 문서가 함께 갱신됐는지 자동으로 확인할 수 있음
- `scripts/verify_docs_sync.py`는 Git이 한글 경로를 quoted path 또는 UTF-8로 출력하는 환경에서도 `bug/` 입력과 로컬 GUI 산출물을 비기준 변경으로 오인하지 않도록 유지해야 함
- prebuild regression step마다 실패 조건과 STDOUT을 별도 로그/JSON으로 남겨 현장 재현이나 원격 디버깅에 유리함
- 로컬 릴리스와 QA 공유 폴더 릴리스가 같은 `build.bat` 경로에서 동시에 생성되므로, QA 전달 누락을 packaging 단계에서 더 일찍 발견할 수 있음
- QA 공유 폴더 루트에서 최신 릴리스만 남기고 이전 버전은 `old/`로 이동하므로, 현장에서 최신본을 찾는 시간이 줄어듦
- AOI / 인스펙터 로그 업로드는 개발/패키징 모두 1GB로 고정되어, 장시간 운전 로그를 UI 업로드 경로로 재현하기 쉬움
- AOI 파서는 큰 단일 로그는 청크 단위, 여러 로그는 파일 단위 스레드 병렬화를 사용해 장시간 로그 재검증의 체감 대기 시간을 줄임
- 브라우저 탭 종료나 headless 캡처 종료 시 Streamlit/Tornado가 남기던 반복 `WebSocketClosedError`, static asset flush `CancelledError`, gzip closed-file 종료 노이즈를 런타임 패치로 줄여, 실제 오류와 종료 노이즈를 구분하기 쉬움
- UI 버튼 시작 실패가 계속 `액세스가 거부되었습니다`로 보이면 PowerShell 자체보다 Windows UAC, 파일 차단, AppLocker/WDAC/Defender 정책, 로컬 관리자 권한 문제를 우선 조사할 수 있음

## 현재 한계와 주의점

- 관리자 권한이 없으면 일부 프로세스 정보 수집이 제한될 수 있습니다.
- PawnIO는 커널 드라이버이므로 파일 동봉만으로 활성화되지 않고, 관리자 권한 설치와 환경에 따라 재부팅이 필요할 수 있습니다.
- 로그 스키마가 변하면 대시보드와 파서가 함께 영향을 받습니다.
- `Monitor.ps1`는 현재 운영 기준 실행 경로가 아니므로, 신뢰성 기준은 `start_monitor.bat`와 `run_app.py` 조합을 우선합니다.
- 문서 동기화가 느슨해지면 운영 기준과 검증 절차가 실제 코드보다 뒤처질 수 있으므로 `scripts/verify_docs_sync.py`를 유지해야 합니다.
- 이 문서는 런타임, 패키징, CI 변경에서 자동 요구 대상으로 취급하고, 그 외 작업에서는 선택 검토 문서로 유지합니다.
- Playwright MCP를 PowerShell 래퍼 경유 stdio로 연결하면 stdin 전달 문제로 initialize 실패가 날 수 있으므로, Codex 구성은 Node CLI 직결 상태를 유지해야 합니다.
- headless Playwright regression은 repo-local `bug/` 입력 파일과 Edge headless 채널을 전제로 하므로, 해당 입력이나 브라우저가 없으면 packaging 전에 실패하도록 두었습니다.
- QA 공유 폴더 복사는 먼저 현재 Windows 세션/Windows Credential Manager 자격증명을 사용하고, 실패 시 사용자 입력을 받아 Credential Manager에 저장한 뒤 재시도합니다. 따라서 네트워크 경로가 불가하거나 입력을 취소하면 빌드 마지막 단계가 실패할 수 있습니다.
- QA 공유 폴더 복사 뒤에는 이전 버전 폴더를 `old/`로 이동하는 단계도 포함되므로, 공유 폴더 쓰기 권한뿐 아니라 move 권한도 필요합니다.

## 결론

현재 구조는 "분리된 수집 + 파일 기반 저장 + 후행 분석" 모델을 따르며, 운영 환경을 크게 침범하지 않으면서 병목 탐지와 회귀 비교에 유리합니다.
