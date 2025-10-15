# LLM Functional Specification

> 본 문서는 `docs/prd_detail/ai-logic/agent.md`의 Mission ID 체계를 기반으로, PRD/PRD-Detail 요구사항과 직접 매핑된 구현 항목을 정의한다.

## Mission Alignment
- **Deterministic Accuracy** (`docs/prd_detail/ai-logic/agent.md:14`) — LLM-6.2 및 LLM-13.x 항목은 필수 변수 확보와 결정론 계산 로깅을 통해 엔진 결과를 그대로 반영하도록 점검한다.
- **Knowledge Fidelity** (`docs/prd_detail/ai-logic/agent.md:15`) — LLM-6.3과 LLM-14.x 태스크는 모든 답변에 citation을 포함하고 근거 부족 시 재시도/경고 절차를 구현한다.
- **Guided Conversation** (`docs/prd_detail/ai-logic/agent.md:16`) — LLM-6.1, LLM-6.4, LLM-13.2는 Clarifying 템플릿 및 상태 관리를 `04-clarifying-strategy.md`와 동기화한다.
- **Compliance & Privacy** (`docs/prd_detail/ai-logic/agent.md:17`) — LLM-7.2, LLM-14.2는 준법 고지, 민감정보 필터링, 참고자료 취급 정책을 `03-message-format.md` 기준으로 유지한다.
- **Gemini 모델 표준화** — 모든 챗 파이프라인 초기 버전은 `gemini-2.5-flash` REST 모델을 사용하며, 환경 변수는 `GOOGLE_API_KEY`, `GEMINI_MODEL` 두 가지만 필수로 관리한다.

## Legend
- **Status**: ☐ (미착수), ☐▶ (진행 중), ✅ (완료)
- **Owner**: 담당자 약칭 또는 TBD
- **Linked PRD**: 해당 기능이 지원하는 상위 요구사항 라인 참조

---

## Section PRD-6: Core Features

### LLM-6.1 Clarifying 질문으로 핵심 변수 수집
- **Linked PRD**: `docs/PRD.md:120`, `docs/prd_detail/ai-logic.md:20`, `docs/prd_detail/ai-logic/04-clarifying-strategy.md:11`
- **Tasks**
  - [ ] `LLM-6.1.a` Clarifying 템플릿 정의 및 용어 설명 문구 작성 (Owner: TBD)
  - [ ] `LLM-6.1.b` LangGraph Clarifying 노드 설계 (입력/출력 상태 모델) (Owner: TBD)
  - [ ] `LLM-6.1.c` Clarifying 단계에서 `clarifying_context[]` 메타데이터 기록 (Owner: TBD)
  - [ ] `LLM-6.1.d` Out-of-scope 판별 및 종료 응답 구현 (Owner: TBD)

### LLM-6.2 필수 변수 확보 후 세액 계산 및 전제/예외 제시
- **Linked PRD**: `docs/PRD.md:124`, `docs/PRD.md:132`, `docs/prd_detail/ai-logic/03-message-format.md:96`
- **Tasks**
  - [ ] `LLM-6.2.a` 계산 가능 조건 검사 로직 구현 (Owner: TBD)
  - [ ] `LLM-6.2.b` TaxCalculationEngine 호출 인터페이스 설계 (Owner: TBD)
  - [x] `LLM-6.2.c` 계산 결과를 `calculation`, `assumptions`, `exceptions`, `recommendations` 필드에 매핑 (Owner: LLM, Issue: #19)
  - [ ] `LLM-6.2.d` 계산 불가 시 RAG 안내로 되돌리는 분기 처리 (Owner: TBD)

### LLM-6.3 법령/예규 근거 링크 노출
- **Linked PRD**: `docs/PRD.md:128`, `docs/PRD.md:150`, `docs/prd_detail/ai-logic/03-message-format.md:64`
- **Tasks**
  - [ ] `LLM-6.3.a` SearchLaw Tool 구현 및 HNSW 검색 최적화 (Owner: TBD)
  - [ ] `LLM-6.3.b` Retrieval 결과를 citation 구조로 정규화 (Owner: TBD)
  - [ ] `LLM-6.3.c` Citation 미존재 시 경고 메시지 및 품질 로그 남기기 (Owner: TBD)

### LLM-6.4 세션 맥락 유지 및 재질문 응답
- **Linked PRD**: `docs/PRD.md:5`, `docs/PRD.md:120`, `docs/prd_detail/ai-logic/03-message-format.md:41`
- **Tasks**
  - [x] `LLM-6.4.a` 세션 상태(수집 변수, Clarifying 히스토리, RAG 컨텍스트) 저장 구조 설계 (Owner: LLM, Issue: #19)
  - [ ] `LLM-6.4.b` LangGraph 상태머신에서 컨텍스트 재사용 로직 구현 (Owner: TBD)
  - [ ] `LLM-6.4.c` 메시지 메타데이터와 DB 스키마 일치 검증 (Owner: TBD)

---

## Section PRD-7: Non-Functional Requirements

### LLM-7.1 응답 지연 목표 준수
- **Linked PRD**: `docs/PRD.md:138`, `docs/PRD.md:162`
- **Tasks**
  - [ ] `LLM-7.1.a` 파이프라인 단계별 SLA 측정 지표 정의 (Owner: TBD)
  - [ ] `LLM-7.1.b` LangGraph 토폴로지 최적화 및 병렬 Tool 호출 검토 (Owner: TBD)
  - [ ] `LLM-7.1.c` 지연 초과 시 폴백 시나리오 구현 (Owner: TBD)

### LLM-7.2 준법/프라이버시 고지 및 PII 관리
- **Linked PRD**: `docs/PRD.md:156`, `docs/prd_detail/ai-logic/03-message-format.md:10`
- **Tasks**
  - [x] `LLM-7.2.a` 시스템 프롬프트에 준법 문구 포함 (Owner: LLM, Issue: #19)
  - [ ] `LLM-7.2.b` 사용자 입력에서 민감정보 감지 시 응답 가이드라인 정의 (Owner: TBD)
  - [ ] `LLM-7.2.c` Metadata에 PII 저장 금지 검증 로직 추가 (Owner: TBD)

### LLM-7.3 토큰 사용량 관리
- **Linked PRD**: `docs/PRD.md:166`, `docs/prd_detail/ai-logic/01-data-pipeline.md:109`
- **Tasks**
  - [ ] `LLM-7.3.a` Prompt/Context 용량 예산 수립 (Owner: TBD)
  - [ ] `LLM-7.3.b` Retrieval chunk 필터링 정책 정의 (Owner: TBD)
  - [ ] `LLM-7.3.c` 토큰 사용량 분석 및 리포트 대시보드 초안 (Owner: TBD)

### LLM-7.4 LLM API 호출 및 배포 패키지 경량화
- **Linked PRD**: `docs/PRD.md:162`, `docs/prd_detail/ai-logic/01-data-pipeline.md:14`
- **Mission Pillar**: **Compliance & Privacy**, **Knowledge Fidelity**
- **Background**: AWS Lambda 레이어 총 용량 한도(250MB) 초과로 `google-generativeai` SDK를 포함한 배포가 실패했으며, 대안으로 Gemini REST API 호출(기본 모델: `gemini-2.5-flash`)을 채택하기로 결정했다. API 호출 시 필요한 환경 변수는 `GOOGLE_API_KEY`(필수)와 `GEMINI_MODEL`(선택, 기본값 `gemini-2.5-flash`)로 제한한다.
- **Tasks**
  - [x] `LLM-7.4.a` Gemini 호출을 REST API 기반으로 재설계하고 SDK 의존성을 제거 (Owner: LLM, Issue: #19)
  - [ ] `LLM-7.4.b` Lambda 배포 아티팩트(레이어 포함) 용량이 250MB 이하임을 CI에서 검증 (Owner: TBD)
  - [ ] `LLM-7.4.c` 패키지 용량 초과 시 S3 기반 배포 또는 기타 경량화 옵션을 위한 대응 플랜 문서화 (Owner: TBD)

---

## Section PRD-13: Tax Calculation Logic

### LLM-13.1 증여세 계산 규칙 준수
- **Linked PRD**: `docs/PRD.md:136`, `docs/PRD.md:140`, `docs/prd_detail/ai-logic/03-message-format.md:103`
- **Tasks**
  - [ ] `LLM-13.1.a` Gift Tax 입력 파라미터 맵핑 정의 (Owner: TBD)
  - [ ] `LLM-13.1.b` 계산 단계 로그(step/fomula) 포맷 설계 (Owner: TBD)
  - [ ] `LLM-13.1.c` 가산세·공제 규칙을 엔진에 통합 (Owner: TBD)

### LLM-13.2 상속세 계산 규칙 준수
- **Linked PRD**: `docs/PRD.md:142`, `docs/prd_detail/ai-logic.md:12`
- **Tasks**
  - [ ] `LLM-13.2.a` Inheritance Tax 파라미터 체크리스트 작성 (Owner: TBD)
  - [ ] `LLM-13.2.b` Clarifying 분기에서 상속 특화 질문 추가 (Owner: TBD)
  - [ ] `LLM-13.2.c` 상속세 계산 로직/특례 안내 템플릿 작성 (Owner: TBD)

### LLM-13.3 계산 결과에 전제·예외·권고 포함
- **Linked PRD**: `docs/PRD.md:148`, `docs/prd_detail/ai-logic/03-message-format.md:41`
- **Tasks**
  - [ ] `LLM-13.3.a` 전제/예외 용어 사전 정의 (Owner: TBD)
  - [ ] `LLM-13.3.b` 계산 결과와 텍스트 답변 동기화 로직 구현 (Owner: TBD)
  - [ ] `LLM-13.3.c` 권고 시나리오 템플릿(예: 분할 증여) 정리 (Owner: TBD)

---

## Section PRD-14: RAG & Citation Rules

### LLM-14.1 문장 단위 인용 및 링크 제공
- **Linked PRD**: `docs/PRD.md:150`, `docs/prd_detail/ai-logic/03-message-format.md:70`
- **Tasks**
  - [ ] `LLM-14.1.a` Chunk 요약 규칙 및 길이 제한 설정 (Owner: TBD)
  - [ ] `LLM-14.1.b` Citation Snippet 하이라이트 로직 구현 (Owner: TBD)
  - [ ] `LLM-14.1.c` UI에서 링크 표시를 위한 메타데이터 검증 (Owner: TBD)

### LLM-14.2 웹 검색 결과의 참고자료 처리
- **Linked PRD**: `docs/PRD.md:152`, `docs/prd_detail/ai-logic/03-message-format.md:45`
- **Tasks**
  - [ ] `LLM-14.2.a` WebSearchTool 응답 포맷 정의 (Owner: TBD)
  - [ ] `LLM-14.2.b` 참고자료 라벨/주의 문구 템플릿 작성 (Owner: TBD)
  - [ ] `LLM-14.2.c` 참고자료만 있을 때의 답변 정책 수립 (Owner: TBD)

### LLM-14.3 근거 부족 시 불확실성 안내
- **Linked PRD**: `docs/PRD.md:154`, `docs/prd_detail/ai-logic/03-message-format.md:96`
- **Tasks**
  - [ ] `LLM-14.3.a` 근거 부족 감지 로직 정의 (Owner: TBD)
  - [ ] `LLM-14.3.b` 경고/추가 확인 안내 메시지 템플릿 작성 (Owner: TBD)
  - [ ] `LLM-14.3.c` 품질 모니터링 리포트에 미인용 건수 포함 (Owner: TBD)

---

## Section PRD Detail Alignment

### AI Logic (`docs/prd_detail/ai-logic.md`)
- 요구사항별 Task는 위 `LLM-6.x` 및 `LLM-13.x` 항목에서 분배됨. 추가 세부 작업은 다음을 따른다.
  - [x] `LLM-AI-3.1.a` 시스템 프롬프트에 페르소나/구조화 출력 지시 포함 (Owner: LLM, Issue: #19)
  - [ ] `LLM-AI-4.1.a` 법령 데이터 파이프라인 검증 스크립트 작성 (Owner: TBD)
  - [ ] `LLM-AI-4.3.a` 데이터 갱신 프로세스 체크리스트 정리 (Owner: TBD)

### 데이터 모델 (`docs/prd_detail/database-model.md`)
- [ ] `LLM-DB-2.1.a` `law_sources`/`knowledge_sources` 스키마 적용 여부 점검 (Owner: TBD)
- [ ] `LLM-DB-2.2.a` `messages.metadata` JSON 스키마 테스트 (Owner: TBD)
- [ ] `LLM-DB-3.1.a` `tax_rule_config` Seed 데이터 준비 (Owner: TBD)

---

## Change Log
- 2025-10-15: Issue #19 완료 - Gemini REST 파이프라인 구축, 응답 스키마 정의, 시스템 프롬프트 작성, 단위 테스트 추가
- 2025-10-15: 문서 초안 작성 (Owner: TBD)
