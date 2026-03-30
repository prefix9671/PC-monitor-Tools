# 문서 허브

Updated On: 2026-03-30  
Status: Active

이 `docs` 폴더는 사람과 AI 에이전트가 같은 기준 문서를 빠르게 찾을 수 있도록 재구성한 허브입니다.

## 먼저 읽을 문서

1. [ActiveDocs.md](ActiveDocs.md)
2. [Current Phase/CurrentPhase.md](Current%20Phase/CurrentPhase.md)
3. [Architecture/SystemOverview.md](Architecture/SystemOverview.md)
4. [Best Practices/DocumentationWorkflow.md](Best%20Practices/DocumentationWorkflow.md)

## 폴더 역할

| 폴더 | 목적 | 권한 수준 |
|---|---|---|
| `Current Phase` | 지금 당장 유효한 목표, 리스크, 검증 기준 | 가장 높음 |
| `Architecture` | 현재 구현된 시스템의 구조와 런타임 동작 | 높음 |
| `Best Practices` | 변경 방식, 문서화 규칙, 검증 절차 | 높음 |
| `Wiki` | 참고용 구조 문서, 사용자 가이드, 변경 이력 | 중간 |
| `Future` | 아직 구현되지 않은 계획과 아이디어 | 낮음 |

## 탐색 규칙

- 활성 문서는 반드시 [ActiveDocs.md](ActiveDocs.md)에 등록합니다.
- 계획을 세우거나 구조를 바꾸기 전에는 `Current Phase`와 관련 `Architecture` 문서를 먼저 확인합니다.
- 구현이 끝나면 영향받는 활성 문서를 같은 변경에서 함께 업데이트합니다.
- `Future` 문서는 아이디어 저장소이며, 현재 동작의 출처로 사용하지 않습니다.

## 충돌 해결 규칙

1. `ActiveDocs.md`에 없는 문서는 비활성 문서로 간주합니다.
2. 폴더 우선순위는 `Current Phase` > `Architecture` > `Best Practices` > `Wiki` > `Future` 입니다.
3. 같은 계층 안에서는 `Updated On` 날짜가 더 최신인 문서를 우선합니다.
4. 같은 날짜라면 더 구체적인 문서가 개요 문서보다 우선합니다.

## 현재 추천 진입점

- 구조를 이해하려면: [Architecture/SystemOverview.md](Architecture/SystemOverview.md)
- 실행과 패키징을 확인하려면: [Architecture/RuntimeAndPackaging.md](Architecture/RuntimeAndPackaging.md)
- 문서 갱신 절차를 따르려면: [Best Practices/DocumentationWorkflow.md](Best%20Practices/DocumentationWorkflow.md)
- 사용자 관점 동작을 확인하려면: [Wiki/UserManual.md](Wiki/UserManual.md)
