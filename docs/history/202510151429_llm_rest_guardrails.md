# 작업 이력: 202510151429_llm_rest_guardrails

## 작업 요약
LLM 문서 세트를 `docs/prd_detail/ai-logic/` 경로로 통합하고, Gemini REST 호출 전환 및 Lambda 배포 용량 가드레일을 PRD-Detail 문서에 반영했습니다. 관련 변경 사항은 PR `#18 chore: document LLM REST guardrails`로 제출되었습니다.

## 변경 사항
- `docs/llm/01-04-*.md`, `docs/llm/db-diagram.png` 삭제 후 `docs/prd_detail/ai-logic/` 하위로 재배치
- `docs/prd_detail/ai-logic/functional-spec.md`에 비기능 요구 LLM-7.4 추가 (Gemini REST 호출, Lambda 레이어 250MB 한도 준수)
- 파이프라인/DB/메시지/Clarifying 문서에 Agent Guardrails 및 배포 용량 운영 지침 명시
- `docs/prd_detail/ai-logic/agent.md`, `docs/prd_detail/database-model.md` 참조 경로 및 가드레일 링크 정리
- `docs/history/202510141456_rebase_origin_main.md`는 기존 기록 보존을 위해 수정하지 않고, 신규 작업 이력 파일로 현 변경분 기록

## 영향 범위
- LLM 팀이 단일 PRD-Detail 경로에서 모든 가드레일과 세부 설계를 추적 가능
- Lambda 배포 실패 원인(레이어 용량 초과)에 대응하는 운영 정책이 문서화되어 재발 방지에 도움
- Gemini SDK 제거를 전제로 한 REST 호출 전략이 명시되어 의존성 관리 부담 감소

## 테스트
- 문서 변경 (별도 테스트 없음)

## 기타
- 변경 내용은 `docs-llm-guardrails-rest-api` 브랜치에서 관리되고, GH PR(#18)로 리뷰 요청이 올라가 있습니다.
