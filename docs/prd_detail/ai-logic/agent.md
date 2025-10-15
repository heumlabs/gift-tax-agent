# LLM Agent Mission

## 1. Purpose
- PRD 목표를 달성하기 위해 LLM 팀이 지켜야 할 역할과 성공 기준을 한 페이지에 명시한다.
- 실행 세부사항(체크리스트, 담당자)은 `docs/prd_detail/ai-logic/functional-spec.md`에서 관리하고, 본 문서는 방향성과 가드레일만 유지한다.

## 2. Scope & Boundaries
- **도메인 한정**: 증여·상속 세무 상담 이외의 주제는 답변하지 않는다 `docs/PRD.md:3`.
- **파이프라인 단계**: Clarifying → RAG 검색 → 결정론적 세액 계산 → 답변 합성 순서를 LangGraph로 강제한다 `docs/prd_detail/ai-logic.md:12`.
- **결정론 계산**: 세액 산출은 반드시 `TaxCalculationEngine`으로 수행한다(`LLM`은 설명·인용 책임) `docs/prd_detail/ai-logic.md:30`.
- **데이터 소스**: `law_sources`, `knowledge_sources`, `tax_rule_config` 등 LLM 전용 테이블만 사용하며 스키마 변경 시 PRD-Detail과 동기화한다 `docs/prd_detail/database-model.md:24`.

## 3. Mission Pillars
1. **Deterministic Accuracy** — 필수 변수가 확보된 뒤에만 계산 엔진을 호출하고, 결과·가정·예외를 구조화하여 제공한다 `docs/PRD.md:124` `docs/prd_detail/ai-logic/03-message-format.md:96`.
2. **Knowledge Fidelity** — 모든 답변에 법령/예규 근거를 첨부하고, 근거 부족 시 불확실성을 고지한다 `docs/PRD.md:150` `docs/prd_detail/ai-logic/03-message-format.md:64`.
3. **Guided Conversation** — Clarifying 단계에서 용어 설명과 함께 필수 변수를 수집하고, 범위 밖 요청 시 대화를 종료한다 `docs/prd_detail/ai-logic/04-clarifying-strategy.md:27`.
4. **Compliance & Privacy** — “정보 제공용” 고지를 유지하고 민감정보는 저장하지 않는다 `docs/PRD.md:156` `docs/prd_detail/ai-logic/03-message-format.md:10`.

## 4. Operating Guardrails
- Clarifying에서 수집하지 못한 변수는 임의 추정으로 채우지 않는다.
- Citation이 비었을 때는 품질 경고와 함께 RAG 재시도를 수행하거나 답변을 중단한다.
- LangGraph 상태에는 필요한 최소 컨텍스트만 유지하여 토큰 예산을 준수한다 `docs/PRD.md:166`.
- 외부 검색 도구(WebSearchTool)는 참고자료로만 사용하고, 근거로 삼지 않는다 `docs/PRD.md:152`.

## 5. Coordination Artifacts
- **Functional Spec**: `docs/prd_detail/ai-logic/functional-spec.md` — ID별 구현 작업, 체크리스트, 담당자.
- **Data Pipeline**: `docs/prd_detail/ai-logic/01-data-pipeline.md` — 임베딩·적재 파이프라인.
- **Message Format**: `docs/prd_detail/ai-logic/03-message-format.md` — 메타데이터 스키마.
- **Clarifying Strategy**: `docs/prd_detail/ai-logic/04-clarifying-strategy.md` — 질문 템플릿과 상태 관리.

## 6. Change Management
- PRD 또는 PRD-Detail이 수정되면, 관련 Mission Pillar와 Guardrail을 재검토한다.
- Functional Spec의 상태 변경(✅ 등)은 주간 공유 시 본 문서와 함께 참고한다.
- 가드레일을 위반하는 신규 요구가 발생하면 Product 팀과 합의 후 문서를 업데이트한다.
- LLM 팀은 `ai/` 및 `docs/prd_detail/ai-logic/` 디렉터리 내에서만 코드를 수정하며, 백엔드·프론트엔드 등 타 영역 수정은 원칙적으로 수행하지 않는다.
- 공용 의존성(`requirements-ai.txt` 등)처럼 타 팀에 영향을 줄 수 있는 변경은 사전에 사용자 요청을 통해 명시적 허락을 받은 뒤 진행한다.
- LLM 기능 목표를 달성하기 위해 타 영역을 수정해야 하는 경우에는 먼저 사용자에게 상황을 공유하고 관련 팀의 동의를 확보한 다음 작업한다.
- 루트 프로젝트 문서(`README.md`, `SETUP.md` 등) 및 백엔드 배포 관련 문서는 담당 팀의 승인을 받기 전에는 수정하지 않는다. LLM 관련 안내는 `ai/README.md` 등 전용 문서에서 관리한다.
