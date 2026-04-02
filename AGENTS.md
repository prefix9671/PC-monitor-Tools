# AGENTS.md

Updated On: 2026-04-02

## 목적

이 저장소에서 작업하는 에이전트는 코드 변경 전에 현재 기준 문서를 확인하고, 구현 후에는 관련 문서를 함께 갱신해야 합니다. 문서와 코드가 어긋나면 오래된 판단이 반복되므로, 이 파일은 에이전트의 기본 행동 규칙을 정의합니다.

## 필수 워크플로

1. 계획을 세우기 전, 구조를 확신할 수 없을 때, 또는 비사소한 변경을 시작하기 전에는 반드시 `docs/ActiveDocs.md`를 먼저 확인합니다.
2. `docs/ActiveDocs.md`에서 관련 문서를 찾고, 최소한 `Current Phase`, `Architecture`, `Best Practices`의 관련 문서를 읽습니다.
3. `docs/ActiveDocs.md`에 등록된 문서만 활성 문서로 취급합니다.
4. 구현을 마친 뒤에는 영향받는 활성 문서를 다시 훑고, 필요한 문서를 같은 변경 안에서 업데이트합니다.
5. 새 기준 문서가 필요하면 문서를 만들고 `docs/ActiveDocs.md`에 등록합니다.
6. PowerShell로 한글 문서를 읽을 때는 `Get-Content -Encoding UTF8`를 기본으로 사용합니다.
7. 문서-코드 매핑과 자동 검증 기준은 `docs/Best Practices/DocumentationWorkflow.md`와 `scripts/doc_sync_rules.toml`을 기준으로 따릅니다.

## 문서 우선순위

문서가 서로 충돌하면 아래 순서로 판단합니다.

1. `docs/Current Phase`
2. `docs/Architecture`
3. `docs/Best Practices`
4. `docs/Wiki`
5. `docs/Future`

같은 계층 안에서 충돌하면 `Updated On` 날짜가 더 최신인 문서를 우선합니다. 같은 날짜라면 더 구체적인 문서를 우선합니다. `docs/Future` 문서는 현재 구현을 덮어쓰지 않습니다.

## 문서 참조 구조

- `docs/ActiveDocs.md`
  활성 문서 진입점입니다.
- `docs/Current Phase/*`
  현재 우선순위, 리스크, 검증 체크를 설명합니다.
- `docs/Architecture/*`
  현재 구조와 실행 기준을 설명합니다.
- `docs/Best Practices/DocumentationWorkflow.md`
  문서-코드 매핑, 작업 마감 게이트, 문서 운영 규칙의 기준 문서입니다.
- `scripts/doc_sync_rules.toml`
  `scripts/verify_docs_sync.py`와 CI가 함께 사용하는 기계 판독 규칙 소스입니다.

## 구현 구조 규칙

- 프로그램을 추가, 변경, 삭제할 때는 메인 로직 코어와 CLI 도구, GUI 도구를 분리합니다.
- 비즈니스 로직과 도메인 로직은 코어 계층에 두고, CLI와 GUI는 입출력과 오케스트레이션에 집중합니다.
- 가능하면 기능은 코어를 먼저 만들고 CLI 경로로 연결한 뒤, GUI는 그 위에 얹는 방식으로 진행합니다.
- CLI 경로로 구현한 기능은 목적에 맞게 동작하는지 반드시 Smoke Test를 수행합니다.
- 하나의 로직 코어 파일이나 모듈이 대략 500~600라인을 넘기기 시작하면 역할별로 계층화하거나 하위 모듈로 분리합니다.

## 저장소별 주의 사항

- 이 프로젝트는 Windows 전용 운영 가정을 갖고 있습니다.
- 현재 실행 기준은 `start_monitor.bat`와 `run_app.py` 흐름을 우선합니다.
- `.artifacts/`, `build/`, `dist/`, `site/`는 생성 산출물이므로 기준 문서나 기준 코드로 삼지 않습니다.
- 로그 스키마를 바꾸면 수집기, 로더, 대시보드, 문서를 함께 갱신해야 합니다.
- WEB 기반 GUI 검증이 필요하면 먼저 `tools/playwright-mcp/launch-playwright-mcp.ps1`와 `~/.codex/config.toml`의 `playwright` MCP 구성이 살아 있는지 확인합니다.
- 문서를 PowerShell로 읽을 때는 기본 인코딩에 의존하지 말고 `-Encoding UTF8`를 명시합니다.
