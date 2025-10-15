# Clarifying & Variable-Gathering Strategy

**문서 버전**: v1.0  
**작성일**: 2025-10-14  
**연관 문서**: `docs/prd_detail/ai-logic.md`, `01-data-pipeline.md`, `03-message-format.md`

## 1. 범위

이 문서는 PRD 및 `docs/prd_detail/ai-logic.md`에서 정의한 상담 흐름을 LLM 팀이 구현할 때 참고하는 **필수 변수 수집(clarifying)** 전략을 정리합니다. 실제 대화 오케스트레이션은 PRD_DETAIL이 단일 진실 소스이며, 여기서는 LLM 관련 구현 세부 규칙만 기술합니다.

### Agent Guardrails 연계
- **Guided Conversation** (`docs/prd_detail/ai-logic/agent.md:16`) — Clarifying 루프 설계를 통해 필수 변수를 단계적으로 확보하고 범위 밖 요청을 조기에 차단한다.
- **Compliance & Privacy** (`docs/prd_detail/ai-logic/agent.md:17`) — 민감정보 탐지 시 즉시 대응하고, “정보 제공용” 고지를 포함한 응답 정책을 유지한다.
- **Knowledge Fidelity** (`docs/prd_detail/ai-logic/agent.md:15`) — Clarifying 과정에서 참조한 법령 스니펫을 `clarifying_context`에 기록하여 추후 답변의 근거로 재사용한다.

## 2. 필수 변수 체크리스트

| 카테고리 | 변수 | 설명 | 필수 여부 | 비고 |
|----------|------|------|-----------|------|
| 기본 | `tax_type` | `gift` / `inheritance` | ✅ | 사용자 초기 질문에서 유추 |
| 관계 | `relationship` | 배우자, 직계존속, 직계비속, 기타 | ✅ | 공제 한도 계산 |
| 거주 | `is_resident` | 국내 거주자 여부 | ✅ | 비거주자 계산 분기 |
| 금액 | `amount` | 증여/상속 대상 금액 또는 평가액 | ✅ | 단위: KRW |
| 기간 | `past_gifts` / `past_inheritance` | 최근 10년 동일인 증여/상속 합계 | ✅ (증여) / 옵션(상속) | 누적 과세 판단 |
| 자산 유형 | `asset_type` | 현금, 부동산, 주식, 사업체 등 | ✅ | 특례 적용 분기 |
| 채무/부담 | `has_debt` | 부담부 증여/채무 상속 여부 | 옵션 | 가산세/차감 |
| 특례 | `eligible_exemption` | 가업상속, 영농상속, 증여특례 등 | 옵션 | 추가 정보 필요 시 세부 필드 |
| 신고 상태 | `planned_filing_date` | 신고 예정일 / 지연 여부 | 옵션 | 가산세 안내 |

> PRD 기준 필수 항목을 우선 수집하고, 추가 특례는 사용자가 관심을 표할 때만 질문합니다.

Clarifying 단계에서 수집하려는 값이 사용자의 배경지식 밖에 있을 가능성이 높으므로, 질문 전후로 간단한 설명과 예시를 제공하는 것을 기본 규칙으로 합니다. 예: “최근 10년 내 동일인에게서 받은 증여가 있는지 확인하고 있어요. 동일인은 증여자 본인을 의미합니다.”

## 3. Clarifying 루프 설계

1. **초기 분석**: 사용자의 첫 메시지를 `docs/prd_detail/ai-logic.md`에서 정의한 의도 분류기로 분류하고, 초기 엔티티 추출.  
2. **부족 변수 판정**: 필수 체크리스트와 비교하여 `missing_parameters` 집합을 구성.  
3. **Clarifying 질문 생성**:
   - 질문은 한 번에 1~2개씩 묶어서 전달.
   - 질문 템플릿은 PRD_DETAIL의 예시 문구를 기반으로 `docs/prd_detail/ai-logic/04-clarifying-strategy.md`에서 관리한다.
   - 질문 직전에는 필요한 개념을 짧게 설명하고, RAG 검색에서 확보한 관련 법령·가이드의 핵심 문장을 함께 보여 사용자가 왜 필요한지 이해하도록 돕는다.
   - 사용자가 “모른다/확인 중”이라고 응답하면, 예외 처리 안내와 함께 다음 질문으로 넘어간다.
4. **반복**: `missing_parameters`가 비어질 때까지 2~3단계 반복.  
5. **종료 조건**:
   - 필수 변수 충족 → 계산/검색 모듈로 이동  
   - 3회 이상 동일 변수를 수집하지 못함 → “추가 정보 확보 후 다시 시도” 메시지와 체크리스트 제공  
   - 사용자가 중단 요청 → 세션 보존 후 종료

## 4. 메시지 메타데이터 매핑

Clarifying 단계에서 사용되는 정보는 다음 규칙으로 `metadata`에 저장합니다.

```json
{
  "intent": "gift_tax",
  "collected_parameters": {
    "relationship": "spouse",
    "is_resident": true
  },
  "missing_parameters": [
    { "name": "amount", "reason": "not_provided" },
    { "name": "past_gifts", "reason": "clarification_required" }
  ],
  "clarifying_history": [
    {
      "question": "증여 금액이 얼마인지 알려주실 수 있을까요?",
      "timestamp": "2025-10-14T07:32:01Z"
    }
  ]
}
```

- `intent`: PRD_DETAIL에서 정의된 분류 키 (`gift_tax`, `inheritance_tax`, `general_info` 등)  
- `collected_parameters`: 현재까지 확인된 변수  
- `missing_parameters`: 수집되지 않은 필수 변수 목록과 사유 (`not_provided`, `ambiguous`, `user_unknown`)  
- `clarifying_history`: 질문·응답 로그(선택), 향후 UI에서 재활용 가능
- `clarifying_context`: Clarifying 단계에서 참고한 RAG 스니펫이나 설명 텍스트, 사용자가 이해한 정도 등을 기록하는 배열. 각 항목은 `{ "source_id": ..., "summary": ... }` 구조를 사용한다.

## 5. LangGraph 통합

Clarifying 전략은 LangGraph 워크플로우의 첫 번째 주요 노드로 실행되며 다음과 같이 동작합니다.

1. **Clarifying 노드**
   - 의도 분류 모델 출력과 현재까지의 `collected_parameters`를 입력으로 받는다.
   - 부족한 변수를 판단한 뒤, 질문과 함께 관련 개념 설명을 생성한다.
   - 필요한 경우 `SearchLawTool`을 호출하여 요약된 법령 스니펫을 `clarifying_context`에 저장하고 사용자에게 전달한다.

2. **분기 조건**
   - `missing_parameters`가 비어 있으면 → **Deterministic Calculation 노드**로 이동한다.
   - `missing_parameters`가 남아 있으나 사용자가 일반 정보만 원하는 것으로 판단되거나 계산 조건을 충족하기 어렵다고 응답하면 → **General QA/RAG 노드**로 이동한다.
   - 대화 주제가 상속/증여와 무관하거나 Clarifying 질문에도 일관된 응답이 없는 경우 → **Out-of-Scope 핸들러**에서 정중히 종료한다.

3. **컨텍스트 공유**
   - Clarifying 노드가 수집한 `clarifying_context`와 `collected_parameters`는 이후 노드(계산, QA)에서도 공통적으로 참조한다.
   - RAG 결과는 LangGraph 전역 상태(`context.retrieval_chunks`)에 추가하여 중복 검색을 최소화한다.

## 6. 응답 생성 시 주의 사항

- `missing_parameters`가 비어있지 않다면 최종 계산/답변을 실행하지 않고 다시 Clarifying 질문을 생성합니다.  
- 사용자가 “계속”을 요청했지만 일부 변수는 기본값으로 가정해야 하는 경우, `metadata.assumptions`에 가정 내용을 명시하고 답변 본문에 동일하게 노출합니다.  
- 여러 변수 중 일부만 누락된 경우, 우선순위는 `relationship` → `amount` → `past_gifts` → `asset_type` 순으로 재질문합니다.

## 7. 향후 개선 항목

1. Clarifying 질문 템플릿을 YAML 등 외부 설정으로 분리하여 PM/세무사 피드백을 신속히 반영  
2. 질문 난이도에 따른 적응형 전략(사용자 이해도에 따라 장문/단문 질문 조절)  
3. 누락 변수 자동 요약 카드 생성 (프런트엔드와 협의)

---

> Clarifying 로직 변경 시 `docs/prd_detail/ai-logic.md`를 우선 수정하고, 이 문서와 `03-message-format.md`의 관련 필드 정의를 동기화해야 합니다.
