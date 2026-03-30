# Active Docs

Updated On: 2026-03-30  
Status: Active

이 문서는 `docs` 폴더의 활성 문서를 추적하는 빠른 인덱스입니다. 사람과 AI 에이전트는 문서를 탐색할 때 항상 이 파일부터 확인합니다.

## 사용 규칙

1. 계획 수립, 구현 전 구조 확인, 불확실성 해소가 필요할 때 가장 먼저 이 파일을 엽니다.
2. 이 파일에 없는 문서는 기본적으로 비활성 또는 호환성 문서로 간주합니다.
3. 구현을 마친 뒤에는 영향받는 활성 문서를 같은 변경 안에서 함께 업데이트합니다.
4. 새 기준 문서를 만들면 이 파일에 즉시 등록합니다.

## 충돌 해결 규칙

1. 문서 권한 순서는 `Current Phase` > `Architecture` > `Best Practices` > `Wiki` > `Future` 입니다.
2. 같은 계층이라면 `Updated On` 날짜가 더 최신인 문서를 우선합니다.
3. 같은 날짜라면 더 구체적인 문서가 개요 문서보다 우선합니다.
4. `Future` 문서는 현재 동작을 덮어쓰지 않습니다.

## 최소 읽기 세트

- [Current Phase/CurrentPhase.md](Current%20Phase/CurrentPhase.md)
- [Architecture/SystemOverview.md](Architecture/SystemOverview.md)
- [Best Practices/DocumentationWorkflow.md](Best%20Practices/DocumentationWorkflow.md)
- [DocsHub.md](DocsHub.md)

## 활성 문서 목록

| Path | Tier | Purpose | Update When |
|---|---|---|---|
| [Current Phase/CurrentPhase.md](Current%20Phase/CurrentPhase.md) | Current Phase | 현재 개발 단계, 활성 리스크, 즉시 지켜야 할 기준 | 현재 목표, 리스크, 운영 기준이 바뀔 때 |
| [Current Phase/VerificationChecklist.md](Current%20Phase/VerificationChecklist.md) | Current Phase | 변경 후 실행해야 할 검증 절차 | 테스트 절차나 필수 검증이 바뀔 때 |
| [DocsHub.md](DocsHub.md) | Best Practices | 사람과 에이전트를 위한 문서 허브와 탐색 규칙 | 문서 진입 구조나 탐색 규칙이 바뀔 때 |
| [Architecture/SystemOverview.md](Architecture/SystemOverview.md) | Architecture | 현재 구현 아키텍처와 데이터 흐름 | 모듈 경계, 데이터 흐름, 로그 스키마가 바뀔 때 |
| [Architecture/RuntimeAndPackaging.md](Architecture/RuntimeAndPackaging.md) | Architecture | 실행 모드, 패키징 흐름, 배포 산출물 | 엔트리포인트, 빌드, 배포 흐름이 바뀔 때 |
| [Best Practices/DocumentationWorkflow.md](Best%20Practices/DocumentationWorkflow.md) | Best Practices | 문서 유지보수와 ActiveDocs 운영 규칙 | 문서 운영 정책이 바뀔 때 |
| [Best Practices/EngineeringGuidelines.md](Best%20Practices/EngineeringGuidelines.md) | Best Practices | 코드/테스트/로그 스키마 변경 시 지켜야 할 규칙 | 개발 규칙, 검증 원칙이 바뀔 때 |
| [Wiki/ProjectStructure.md](Wiki/ProjectStructure.md) | Wiki | 프로젝트 구조와 파일 역할 참고서 | 파일 구조나 주요 모듈 설명이 바뀔 때 |
| [Wiki/UserManual.md](Wiki/UserManual.md) | Wiki | 사용자 관점 실행 및 분석 가이드 | UI, 로그 선택, 대시보드 동작이 바뀔 때 |
| [Wiki/ReliabilityReport.md](Wiki/ReliabilityReport.md) | Wiki | 운영/QA 관점 신뢰성 설명 | 수집 방식, 운영 가정, 성능 영향 설명이 바뀔 때 |
| [Wiki/Changelog.md](Wiki/Changelog.md) | Wiki | 릴리스 수준 변경 이력 | 의미 있는 구조/기능 변화가 생길 때 |
| [Future/Roadmap.md](Future/Roadmap.md) | Future | 가까운 개선 계획과 방향 | 계획 우선순위가 바뀔 때 |
| [Future/IdeasAndBacklog.md](Future/IdeasAndBacklog.md) | Future | 보류 아이디어와 장기 과제 | 보류 항목을 추가/삭제할 때 |
