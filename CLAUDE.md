# CLAUDE.md

이 저장소의 작업 규칙은 Codex/Claude 공용으로 `AGENTS.md`를 단일 기준으로 따른다.

@AGENTS.md

## Claude 세션 보충
- 문서 진입점: `docs/ActiveDocs.md` 를 먼저 읽는다.
- 문서-코드 매핑과 자동 검증 기준은 `docs/Best Practices/DocumentationWorkflow.md` 와 `scripts/doc_sync_rules.toml` 을 따른다.
- Bash/PowerShell 로 한글 문서를 읽을 때는 항상 UTF-8 을 명시한다. 예: `Get-Content -Encoding UTF8 -Raw <path>`.
- 위 import 한 `AGENTS.md` 가 충돌 시 기준 문서다.
