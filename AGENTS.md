# AGENTS.md

Updated On: 2026-03-30

## 목적

이 저장소에서 작업하는 에이전트는 코드 변경 전에 현재 기준 문서를 확인하고, 구현 후에는 관련 문서를 함께 갱신해야 합니다. 문서와 코드가 어긋나면 오래된 판단이 반복되므로, 이 파일은 에이전트의 기본 행동 규칙을 정의합니다.

## 필수 워크플로

1. 계획을 세우기 전, 구조를 확신할 수 없을 때, 또는 비사소한 변경을 시작하기 전에는 반드시 `docs/ActiveDocs.md`를 먼저 확인합니다.
2. `docs/ActiveDocs.md`에서 관련 문서를 찾고, 최소한 `Current Phase`, `Architecture`, `Best Practices`의 관련 문서를 읽습니다.
3. `docs/ActiveDocs.md`에 등록된 문서만 활성 문서로 취급합니다.
4. 구현을 마친 뒤에는 영향받는 활성 문서를 다시 훑고, 필요한 문서를 같은 변경 안에서 업데이트합니다.
5. 새 기준 문서가 필요하면 문서를 만들고 `docs/ActiveDocs.md`에 등록합니다.

## 문서 우선순위

문서가 서로 충돌하면 아래 순서로 판단합니다.

1. `docs/Current Phase`
2. `docs/Architecture`
3. `docs/Best Practices`
4. `docs/Wiki`
5. `docs/Future`

같은 계층 안에서 충돌하면 `Updated On` 날짜가 더 최신인 문서를 우선합니다. 같은 날짜라면 더 구체적인 문서를 우선합니다. `docs/Future` 문서는 현재 구현을 덮어쓰지 않습니다.

## 구현 후 문서 점검 규칙

- 구조 변경: `docs/Architecture/*`, `docs/Wiki/ProjectStructure.md`
- 실행/패키징 변경: `docs/Architecture/RuntimeAndPackaging.md`, `docs/Wiki/Changelog.md`
- UI/사용 흐름 변경: `docs/Wiki/UserManual.md`
- 테스트 절차 변경: `docs/Current Phase/VerificationChecklist.md`
- 우선순위나 리스크 변경: `docs/Current Phase/CurrentPhase.md`

## 구현 구조 규칙

- 프로그램을 추가, 변경, 삭제할 때는 메인 로직 코어와 CLI 도구, GUI 도구를 분리합니다.
- 비즈니스 로직과 도메인 로직은 코어 계층에 두고, CLI와 GUI는 입출력과 오케스트레이션에 집중합니다.
- 가능하면 기능은 코어를 먼저 만들고 CLI 경로로 연결한 뒤, GUI는 그 위에 얹는 방식으로 진행합니다.
- CLI 경로로 구현한 기능은 목적에 맞게 동작하는지 반드시 Smoke Test를 수행합니다.
- 하나의 로직 코어 파일이나 모듈이 대략 500~600라인을 넘기기 시작하면 역할별로 계층화하거나 하위 모듈로 분리합니다.

## 저장소별 주의 사항

- 이 프로젝트는 Windows 전용 운영 가정을 갖고 있습니다.
- 현재 실행 기준은 `start_monitor.bat`와 `run_app.py` 흐름을 우선합니다.
- `build/`, `dist/`, `site/`는 생성 산출물이므로 기준 문서나 기준 코드로 삼지 않습니다.
- 로그 스키마를 바꾸면 수집기, 로더, 대시보드, 문서를 함께 갱신해야 합니다.
