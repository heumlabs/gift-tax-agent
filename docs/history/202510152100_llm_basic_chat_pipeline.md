# 작업 이력: 202510152100_llm_basic_chat_pipeline

## 작업 요약
Gemini REST API 기반 최소 채팅 파이프라인을 구축하고 Chalice API 엔드포인트와 통합했습니다. LLM 팀 독립 모듈(`ai/`)을 신규 생성하여 프로토타입 검증 완료했습니다. 관련 변경 사항은 PR `#19 feat: stand up minimal chat pipeline for Chalice API`로 제출 예정입니다.

## 변경 사항
### AI 모듈 구현 (`ai/`)
- Gemini REST 비동기 클라이언트 구현 (httpx 기반, SDK 제거)
- 단일 턴 ChatPipeline 및 진입점 함수 (`generate_assistant_message`)
- ChatRequest/ChatResponse 스키마 정의 (메타데이터 구조 완비)
- 환경 변수 기반 설정 로더 (`GOOGLE_API_KEY`, `GEMINI_MODEL`)
- 시스템 프롬프트 정의 (슈킹 페르소나, 준법 고지)
- CLI 테스트 스크립트 및 pytest 단위 테스트 17개 작성
- AI 모듈 문서화 (`ai/README.md`, Chalice 통합 테스트 가이드 포함)

### 백엔드 통합
- `POST /api/sessions/{id}/messages` 엔드포인트 추가
- `google-generativeai` SDK 제거 → `httpx` 추가 (Lambda 250MB 제한 해결)
- 환경 변수 예시 파일 추가 (`.env.example`, `backend/.env.example`)

### 문서 업데이트
- `functional-spec.md`: Issue #19 완료 task 체크 표시 (5개), Change Log 추가
  - LLM-6.2.c: 응답 메타데이터 필드 매핑
  - LLM-6.4.a: 세션 상태 저장 구조 설계
  - LLM-7.2.a: 시스템 프롬프트 준법 문구 포함
  - LLM-7.4.a: Gemini REST API 전환 및 SDK 제거
  - LLM-AI-3.1.a: 시스템 프롬프트 페르소나 정의
- `agent.md`: LLM 팀 작업 범위 및 가드레일 명시

## 영향 범위
- LLM 팀이 `ai/` 디렉토리에서 독립적으로 채팅 로직 개발 가능
- 프론트엔드가 `/api/sessions/{id}/messages`를 통해 LLM 응답 수신 가능
- Lambda 배포 용량 문제 해결 (SDK 40MB → httpx 경량화)
- 향후 LangGraph, RAG, TaxCalculationEngine 추가 시 확장 가능한 구조 확립

## 테스트
- pytest 17개 테스트 전체 통과 (schemas, config, service 레이어)
- Chalice local 통합 테스트 완료 (curl 검증)
- 정상 응답 및 메타데이터 구조 확인

## 기타
- 변경 내용은 `feature/llm-basic-chat-pipeline` 브랜치에서 관리
- 3개 커밋으로 분리 (AI 모듈, 백엔드 통합, 문서 업데이트)
- GH Issue #19 완료 대기
