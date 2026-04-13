# Documentation Workflow

Updated On: 2026-04-14  
Status: Active

## 목적

문서가 AI 에이전트의 작업 정확도를 높이려면, 코드 변경과 문서 변경이 항상 함께 움직여야 합니다. 이 문서는 `docs` 폴더를 운영하는 기본 절차를 정의합니다.

## 기본 원칙

- `docs/ActiveDocs.md`는 활성 문서의 단일 인덱스입니다.
- 계획을 세우거나 불확실성이 생기면 먼저 `ActiveDocs.md`를 보고 관련 문서를 엽니다.
- 구현이 끝나면 영향받는 활성 문서를 같은 변경 안에서 업데이트합니다.
- 활성 상태가 아닌 문서는 현재 동작의 출처로 사용하지 않습니다.
- 문서-코드 매핑의 사람 기준 문서는 이 파일이고, 기계 기준 소스는 `scripts/doc_sync_rules.toml`입니다.

## 기준 소스

- `docs/Best Practices/DocumentationWorkflow.md`
  사람이 읽는 기준 문서입니다. 에이전트와 개발자는 여기의 설명을 먼저 따릅니다.
- `scripts/doc_sync_rules.toml`
  `scripts/verify_docs_sync.py`와 CI가 함께 쓰는 기계 판독 규칙 소스입니다.
- `scripts/verify_docs_sync.py`
  문서 매핑과 활성 문서 동기화만 검사합니다. 단위 테스트나 headless Playwright 회귀 실행기는 아니며, 실제 회귀 실행은 `scripts/run_prebuild_regression.py`가 담당합니다.
  `git`가 한글 경로를 quoted path 형태로 돌려주는 경우도 포함해, 로컬 `bug/` 입력과 Playwright 산출물 같은 비기준 파일은 ignore 규칙으로 계속 제외해야 합니다.
- `AGENTS.md`
  저장소 진입 규칙과 문서 트리만 요약하고, 세부 매핑은 이 문서를 참조합니다.

## 문서 업데이트 절차

1. `ActiveDocs.md`에서 관련 문서를 찾습니다.
2. `Current Phase`와 `Architecture` 문서를 먼저 읽어 현재 기준을 확인합니다.
3. 변경 범위에 맞는 `Best Practices`, `Wiki`, `Future` 문서를 추가로 읽습니다.
4. 구현 후 영향받는 문서를 수정하고 `Updated On` 날짜를 갱신합니다.
5. 새 문서를 만들었다면 `ActiveDocs.md`에 등록합니다.
6. `mkdocs build`로 링크와 렌더를 확인합니다.
7. 코드 변경이 있다면 `scripts/verify_docs_sync.py`로 문서 동기화를 확인합니다.
8. 브라우저 회귀나 build 전 실행 게이트까지 확인해야 하는 작업이면 `scripts/run_prebuild_regression.py`를 별도로 실행합니다.

## 작업 마감 체크

- 비사소한 코드 변경이 있었다면 기본적으로 `docs/Current Phase/VerificationChecklist.md`를 같은 변경 안에서 업데이트합니다.
- 우선순위, 리스크, 운영 기준이 바뀌었다면 `docs/Current Phase/CurrentPhase.md`를 함께 업데이트합니다.
- 런타임, 패키징, CI 변경은 `docs/Wiki/ReliabilityReport.md`를 자동 요구 대상으로 취급합니다.
- Playwright 회귀 자동화, headless 브라우저 검증, MCP 런처 변경은 `docs/Architecture/RuntimeAndPackaging.md`, `docs/Wiki/ReliabilityReport.md`, `docs/Current Phase/VerificationChecklist.md`를 자동 요구 대상으로 취급합니다.
- 위 규칙의 자동 판정은 `scripts/doc_sync_rules.toml`을 기준으로 하고, `scripts/verify_docs_sync.py`가 이를 검사합니다.

## PowerShell 인코딩 규칙

- 한글 문서를 PowerShell로 읽을 때는 `Get-Content -Encoding UTF8`를 사용합니다.
- `docs/` 트리의 문서, `README.md`, `AGENTS.md` 같은 한국어 기준 문서도 같은 규칙을 적용합니다.
- Windows 콘솔에서 기본 인코딩에 의존한 문서 읽기는 기준 작업 방식으로 인정하지 않습니다.

## 어떤 변경이 어떤 문서를 건드리는가

| 변경 종류 | 반드시 확인/업데이트할 문서 |
|---|---|
| 모든 비사소한 코드 변경 | `Current Phase/VerificationChecklist.md` |
| 모듈 구조 변경 | `Architecture/SystemOverview.md`, `Wiki/ProjectStructure.md` |
| 실행/배포 흐름 변경 | `Architecture/RuntimeAndPackaging.md`, `Wiki/Changelog.md`, `Wiki/ReliabilityReport.md`, `Current Phase/CurrentPhase.md` |
| CI 또는 검증 자동화 변경 | `Wiki/ReliabilityReport.md`, `Current Phase/VerificationChecklist.md` |
| Playwright / 회귀 자동화 변경 | `Architecture/RuntimeAndPackaging.md`, `Wiki/ReliabilityReport.md`, `Current Phase/VerificationChecklist.md` |
| 테스트 절차 변경 | `Current Phase/VerificationChecklist.md`, 필요 시 `Best Practices/EngineeringGuidelines.md` |
| UI/사용 흐름 변경 | `Wiki/UserManual.md`, 필요 시 `Wiki/Changelog.md` |
| 우선순위/리스크/운영 기준 변경 | `Current Phase/CurrentPhase.md` |
| 신규 계획 추가 | `Future/Roadmap.md` 또는 `Future/IdeasAndBacklog.md` |

## 충돌 처리

1. `Current Phase`가 현재 기준을 결정합니다.
2. 구조적 사실은 `Architecture`가 설명합니다.
3. 일반 가이드는 `Best Practices`를 따릅니다.
4. `Wiki`는 참고 문서이며, 구체적 구현 사실과 충돌하면 상위 문서를 우선합니다.
5. `Future`는 계획 문서이며, 현재 구현과 충돌해도 현재 구현을 덮어쓰지 않습니다.

## 작성 규칙

- 문서마다 `Updated On`과 `Status`를 유지합니다.
- 애매한 표현보다 현재 구현 사실을 직접 씁니다.
- 실행 경로, 로그 경로, 파일명, 테스트 명령은 실제 코드 기준으로 적습니다.
- 더 이상 권위가 없는 오래된 문서는 삭제하거나 호환성 stub로 바꾸고, `ActiveDocs.md`에서 제거합니다.
