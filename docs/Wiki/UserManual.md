# User Manual

Updated On: 2026-03-30  
Status: Active

이 문서는 현재 구현된 Streamlit 대시보드와 수집기 사용 방법을 설명합니다.

## 프로그램 시작

### 수집 시작

1. 관리자 권한으로 `start_monitor.bat` 또는 대시보드의 `Start Monitor` 버튼을 사용합니다.
2. 수집기가 시작되면 `C:\SystemLogs`에 로그를 기록합니다.
3. 종료하려면 열린 콘솔 창에서 `Ctrl + C`를 누르거나 창을 닫습니다.

기록되는 주요 파일:

- `resource_YYYYMMDD.csv`
- `process_YYYYMMDD.csv`
- `summary_YYYYMMDD.log`

### 대시보드 실행

- 개발 환경: `.\venv\Scripts\python -m streamlit run app.py`
- 패키징 환경: `SystemResourceMonitor*.exe`

![메인 대시보드](../images/main_dashboard.png)

## 화면 구성

### Control Panel

- `Start Monitor`: 관리자 권한으로 수집기 실행
- `Refresh Log Data`: Streamlit 캐시를 비우고 최신 로그 반영
- 안내 문구: 1초 샘플링 / 5초 집계 정책 표시

### Log File Selection

- `Upload Log CSV(s)`: CSV 직접 업로드
- `Select Record Date from C:\SystemLogs`: 날짜별 로컬 로그 선택
- 기본 동작: 최근 7일 이내 로그를 자동 선택
- `Time Range`: 로딩된 데이터 범위를 시간으로 필터링

### AOI / Inspector Log

- `Upload AOI / Inspector Log(s)`에서 `Browse files`를 눌러 TXT 또는 LOG 파일을 직접 선택할 수 있습니다.
- 개발자가 아닌 블랙박스 테스터도 파일 탐색기에서 바로 선택해 사용할 수 있도록 설계되었습니다.
- 원본 TXT / LOG는 수정하지 않고, 필요한 `InspTime` / `Working Set Memory Size` 라인만 읽어 별도 시계열로 정리합니다.
- 필요할 때만 `Advanced: Load AOI / Inspector Log by Path`를 열어 경로 입력 방식도 사용할 수 있습니다.
- 예시 경로: `C:\Inspector\shared\operation_0319_north side grab`

## 대시보드 화면

- `CPU Dashboard`
- `Memory AND Inspector Dashboard`
- `Storage Dashboard`
- `Custom Graph`

그래프 오른쪽 상단 도구 모음에서 확대, 이동, 리셋, 이미지 저장을 할 수 있습니다.

![그래프 툴바](../images/graph_toolbar.png)

## Storage Dashboard

스토리지 화면은 데이터 크기에 따라 차트 품질을 조절할 수 있습니다.

- `Fast`
- `Balanced`
- `Detailed`
- `Original (slow)`

권장 사용 순서:

1. `Balanced`로 전체 추세 확인
2. 필요한 구간만 `Detailed`로 확대
3. 최종 검증만 `Original (slow)` 사용

![스토리지 대시보드](../images/storage_dashboard.png)

## CPU 와 Memory Dashboard

### CPU

- CPU 평균/피크 시각화
- 수집된 경우 CPU 온도 표시
- 요약 KPI 확인

![CPU 대시보드](../images/cpu_dashboard.png)

### Memory

- 메모리 사용량 및 사용률
- 상위 메모리 프로세스
- `Inspector APP (log)` Working Set 메모리 비교
- Inspector `Frame` 검사 시간, `Total` 검사 시간, `Working Set` 시계열
- 외부 시스템 모니터 메모리와 AOI 로그 메모리 비교

![메모리 대시보드](../images/memory_dashboard.png)

## Custom Graph 와 엑셀 내보내기

1. 원하는 수치 컬럼을 선택합니다.
2. 필요 시 시작 시각을 조정합니다.
3. `Download as Excel (.xlsx)` 또는 병합 CSV 다운로드를 사용합니다.

![엑셀 내보내기](../images/excel_export_ui.png)

## 문제 해결

### 로그가 보이지 않을 때

- `C:\SystemLogs`가 존재하는지 확인합니다.
- 관리자 권한으로 수집기를 실행했는지 확인합니다.
- `Refresh Log Data`로 캐시를 비웁니다.
- AOI 로그는 `Upload AOI / Inspector Log(s)`에서 직접 파일을 다시 선택해 봅니다.

### 그래프가 느릴 때

- `Storage Dashboard`에서는 `Fast` 또는 `Balanced`를 먼저 사용합니다.
- `Time Range`를 좁혀서 다시 확인합니다.

### 매뉴얼 사이트를 열고 싶을 때

- 대시보드의 `웹 매뉴얼 열기 (MkDocs)` 버튼을 사용하면 패키징된 `site/index.html`을 엽니다.
