# Current Phase

Updated On: 2026-07-03
Status: Active

## 현재 단계

현재 프로젝트는 `psutil` 기반 네이티브 수집기 전환을 마친 뒤, 포터블 실행 흐름과 문서 체계, CI 검증을 함께 안정화하는 단계에 있습니다.

## 현재 기준선

- 수집기: 1초 샘플링, 5초 집계
- 로그 경로: `C:\SystemLogs`
- UI: Streamlit + Plotly
- 데이터 결합: `resource/process` exact merge
- 배포: `run_app.py` + `monitor.spec` + `build.bat`
- PowerShell 독립성: 대시보드 `모니터링 시작`은 Windows `ShellExecuteW("runas")`, 수집기 WMI fallback은 `pythonnet + System.Management` 직접 조회를 사용
- 빌드 게이트: `scripts/run_prebuild_regression.py` 선행 통과 후 패키징
- AOI / 인스펙터 업로드 한도: 1GB
- 빌드 산출물: 로컬 `.artifacts/releases/<빌드명>/`과 QA 공유 폴더 `\\192.168.1.13\sqa\113_테스트 툴\<빌드명>\` 동시 배포, 서버 루트는 최신 빌드 1개만 유지하고 이전 버전은 `old/`로 아카이브. 배포 폴더에는 `SystemResourceMonitor*.exe`, `start_monitor.bat`, `install_pawnio.bat`, `pawnio-bundle/`, `Manual.zip`이 포함됩니다.
- 운영 하드웨어 기준: Dell T5820 / T5860 / T7860 계열 제어 PC에서는 Dell Command Monitor 기반 CPU 온도 경로를 우선 사용하고, 일반 PC는 EXE에 동봉된 `lhm-bundle` 또는 로컬 bundle 을 사용하는 `pythonnet + LibreHardwareMonitorLib.dll` 워커가 `CPU Core #n` 최고온도를 30초마다 갱신합니다. LibreHardwareMonitor 0.9.6 계열은 PawnIO 드라이버 설치가 필요할 수 있으므로 배포본에는 `pawnio-bundle/PawnIO_setup.exe`와 `install_pawnio.bat`를 함께 넣고, `start_monitor.bat`가 미설치 상태를 감지하면 설치 여부를 묻습니다. 어드벤텍 IPC 같은 장비는 워커 실패 시 `Win32_PerfRawData_Counters_ThermalZoneInformation` Kelvin fallback 경로를 포함합니다.

## 이미 완료된 큰 변화

- Logman 중심 구조에서 파이썬 네이티브 수집기로 마이그레이션
- 날짜 기반 로그 선택 UI 정리
- 헤드리스 대시보드 자가 검증 스크립트 추가
- 포터블 EXE 진입점 정리
- PowerShell이 손상된 현장 PC에서도 대시보드 `모니터링 시작` 버튼과 수집기 WMI fallback 경로가 동작할 수 있도록 PowerShell `Start-Process`, `Get-CimInstance`, `Get-Partition` 의존성 제거

## 지금 중요하게 봐야 할 것

- 활성 문서와 실제 코드가 계속 동기화되는지 유지
- 비사소한 코드 변경에는 `VerificationChecklist.md`를 기본 문서 게이트로 유지
- 리스크, 우선순위, 운영 기준이 실제로 바뀌는 경우에만 `CurrentPhase.md`를 필수 갱신 대상으로 유지
- 로그 스키마 변경이 대시보드와 파서를 깨지 않는지 확인
- AOI / 인스펙터 대용량 업로드와 멀티스레드 파싱 경로가 `main`에 유지되는지 확인
- 패키징 흐름에서 실제 기준 파일이 무엇인지 문서에 명확히 유지
- QA 공유 폴더 동시 배포가 기본 흐름으로 유지되는지, 자격증명 방식이 Windows Credential Manager 기준인지, 서버 루트 정리가 최신본 1개 + `old/` 아카이브 규칙을 지키는지 확인
- Playwright MCP 기반 WEB 대시보드 검증은 stdio 호환 구성이 유지되는지 함께 확인
- 최종 패키징 전 bug 입력 파일 기반 headless Playwright 회귀가 반복 가능하고, step별 STDOUT/실패 조건이 남는지 유지

## 활성 리스크

- `Monitor.ps1`가 현재 코드베이스와 완전히 정렬되지 않았을 가능성이 있으므로, 실행 기준은 `start_monitor.bat`, EXE 경로, 대시보드 `모니터링 시작` 버튼의 ShellExecute 경로를 우선합니다.
- `Monitor.ps1`는 공식 정리 대상이며, 호환성 안내 스텁으로만 유지됩니다.
- 생성 산출물은 `.artifacts/` 아래로 분리하되, 레거시 `build/`, `dist/`, `site/`가 Git에 다시 추적되지 않도록 유지해야 합니다.
- QA 공유 폴더 `\\192.168.1.13\sqa\113_테스트 툴` 접근이 안 되거나 Windows Credential Manager 자격증명이 없고 사용자 입력도 취소되면 packaging 마지막 단계에서 실패할 수 있습니다.
- QA 공유 폴더의 이전 버전 이동 권한이 없으면 최신 빌드 복사는 성공해도 `old/` 아카이브 단계에서 packaging 이 실패할 수 있습니다.
- 문서가 업데이트되지 않으면 AI 에이전트가 오래된 경로와 규칙을 참조할 위험이 있습니다.
- `CurrentPhase.md`는 꼭 필요한 상황에서만 갱신하도록 좁혔기 때문에, 실제 리스크/우선순위/운영 기준 변경이 있었는지 작업 종료 전에 한 번 더 확인해야 합니다.

## 현재 단계의 완료 조건

- 구조, 실행, 문서 기준점이 `docs/ActiveDocs.md`를 통해 빠르게 탐색 가능할 것
- 구현 후 문서 업데이트가 기본 워크플로로 정착할 것
- 실행과 패키징 흐름이 문서와 실제 코드에서 크게 어긋나지 않을 것
