# Clarifying Workflow 및 계산 Tool 통합 (Issue #23)

**작성일**: 2025-10-16
**관련 Issue**: #23
**관련 PR**: (PR 번호 미정)
**작업 브랜치**: `feature/clarifying-node-phase3`

## 개요

LangGraph 기본 Workflow 구현(Issue #22)에 이어, Phase 3에서는 Clarifying 노드와 증여세 계산 Tool을 통합하여 멀티턴 대화 기반의 파라미터 수집 시스템을 구축했습니다. 사용자가 자연어로 질문하면 AI가 필요한 정보를 단계적으로 질문하고, 모든 정보가 수집되면 계산 Tool을 실행하여 결과를 자연어로 설명합니다.

## 주요 구현 내용

### 1. Clarifying 노드 구현 (9개 변수 수집)

**파일**: `ai/pipelines/langgraph_workflow.py`, `ai/utils/parameter_extraction.py`

#### 9개 변수 정의 (3-Tier 시스템)

**Tier 1: 필수 변수** (반드시 질문)
- `gift_date`: 증여일
- `donor_relationship`: 증여자 관계 (직계존속, 직계비속, 배우자, 기타친족, 기타)
- `gift_property_value`: 증여재산 가액

**Tier 2: 기본값 제공** (Phase 4에서 명시적 질문 예정)
- `is_generation_skipping`: 세대 생략 여부 (기본값: false)
- `is_minor_recipient`: 미성년 수증자 여부 (기본값: false)
- `is_non_resident`: 비거주자 여부 (기본값: false)

**Tier 3: 조건부 변수** (직계존비속만 해당)
- `marriage_deduction_amount`: 혼인 공제액 (기본값: 0)
- `childbirth_deduction_amount`: 출산 공제액 (기본값: 0)
- `secured_debt`: 담보채무 (기본값: 0)

#### Clarifying 노드 로직

```python
async def clarifying_node(state: WorkflowState) -> dict:
    """파라미터 수집 및 질문 생성"""
    user_message = state.get("user_message", "")
    collected = state.get("collected_parameters", {})

    # 1. 현재 메시지에서 파라미터 파싱 (Gemini API)
    new_params = await extract_parameters(user_message)

    # 2. 기존 파라미터와 병합 (최신 값 우선)
    for key, value in new_params.items():
        if value is not None:
            collected[key] = value

    # 3. 필수 변수 체크 (Tier 1)
    missing = check_missing_parameters(collected)

    # 4. 질문 생성 또는 계산 진행
    if missing:
        question = generate_clarifying_question(collected, missing)
        return {
            "collected_parameters": collected,
            "missing_parameters": missing,
            "response": question
        }
    else:
        return {
            "collected_parameters": collected,
            "missing_parameters": []
        }
```

#### 파라미터 파싱 (Gemini API)

**파일**: `ai/utils/parameter_extraction.py`

```python
async def extract_parameters(user_message: str) -> Dict:
    """Gemini API로 자연어에서 파라미터 추출"""
    settings = GeminiSettings.from_env()
    client = GeminiClient(settings)

    response = await client.generate_content(
        system_prompt=PARAMETER_EXTRACTION_PROMPT,
        user_message=user_message
    )

    # JSON 파싱 및 null 값 제거
    params = json.loads(response)
    return {k: v for k, v in params.items() if v is not None}
```

**PARAMETER_EXTRACTION_PROMPT 특징**:
- 9개 변수 각각에 대한 설명 및 예시 포함
- 자연어 표현을 정규화된 값으로 변환 ("1억" → 100000000, "부모님" → "직계존속")
- JSON Schema 형식으로 출력 강제
- Fallback: 파싱 실패 시 빈 dict 반환

#### 질문 생성 전략

**파일**: `ai/prompts/clarifying.py`

```python
CLARIFYING_QUESTIONS = {
    "gift_date": """증여일이 언제인가요?

💡 증여세는 증여일을 기준으로 신고 기한(3개월)과 공제액이 결정됩니다.
예시: 2025년 10월 15일, 올해 3월""",

    "donor_relationship": """증여자는 어떤 관계인가요?

💡 관계에 따라 공제액이 크게 달라집니다.
- 직계존속 (부모, 조부모 등)
- 직계비속 (자녀, 손자녀 등)
- 배우자
- 기타친족 (형제자매, 삼촌 등)
- 기타 (비친족)""",

    # ... 7개 변수 질문 템플릿
}
```

**질문 우선순위**:
1. Tier 1 순서대로 (gift_date → donor_relationship → gift_property_value)
2. 1개씩 질문 (한 번에 여러 개 질문 금지)
3. Emoji와 예시로 사용자 친화적 안내

### 2. 계산 노드 구현

**파일**: `ai/pipelines/langgraph_workflow.py`

```python
async def calculation_node(state: WorkflowState) -> dict:
    """증여세 계산 Tool 실행"""
    from ai.tools import calculate_gift_tax_simple
    from ai.tools.gift_tax.models import GiftTaxSimpleInput

    params = state.get("collected_parameters", {})

    try:
        # 1. 날짜 문자열 → date 객체 변환
        gift_date_obj = date.fromisoformat(params["gift_date"])

        # 2. GiftTaxSimpleInput 생성 (Pydantic 검증)
        tax_input = GiftTaxSimpleInput(
            gift_date=gift_date_obj,
            donor_relationship=params["donor_relationship"],
            gift_property_value=params["gift_property_value"],
            is_generation_skipping=params.get("is_generation_skipping", False),
            is_minor_recipient=params.get("is_minor_recipient", False),
            is_non_resident=params.get("is_non_resident", False),
            marriage_deduction_amount=params.get("marriage_deduction_amount", 0),
            childbirth_deduction_amount=params.get("childbirth_deduction_amount", 0),
            secured_debt=params.get("secured_debt", 0),
        )

        # 3. 계산 Tool 호출
        result = calculate_gift_tax_simple(**tax_input.model_dump())

        # 4. 결과 저장
        return {
            "metadata": {
                "calculation": result
            }
        }
    except Exception as e:
        return {"response": f"계산 중 오류가 발생했습니다: {str(e)}"}
```

**Pydantic 검증**:
- 타입 안전성 보장 (int, bool, date)
- 유효성 검증 (음수 금액 거부 등)
- Phase 1 계산기와 동일한 입력 형식

### 3. 답변 합성 노드 구현

**파일**: `ai/pipelines/langgraph_workflow.py`, `ai/prompts/clarifying.py`

```python
async def synthesis_node(state: WorkflowState) -> dict:
    """계산 결과를 자연어로 변환"""
    calculation = state.get("metadata", {}).get("calculation", {})
    params = state.get("collected_parameters", {})

    # 1. steps 포맷팅
    steps_text = "\n".join([
        f"{s['step']}. {s['description']}: {s['value']:,}원 ({s.get('detail', '')})"
        for s in calculation.get("steps", [])
    ])

    # 2. warnings 포맷팅
    warnings_text = "\n".join([f"- {w}" for w in calculation.get("warnings", [])])

    # 3. Gemini API로 자연어 설명 생성
    settings = GeminiSettings.from_env()
    client = GeminiClient(settings)

    prompt = SYNTHESIS_PROMPT.format(
        final_tax=calculation["final_tax"],
        gift_value=calculation.get("gift_value", params.get("gift_property_value", 0)),
        total_deduction=calculation.get("total_deduction", 0),
        taxable_base=calculation.get("taxable_base", 0),
        steps_formatted=steps_text,
        warnings_formatted=warnings_text
    )

    response = await client.generate_content(
        system_prompt=prompt,
        user_message=f"관계: {params.get('donor_relationship', '알 수 없음')}, 금액: {params.get('gift_property_value', 0):,}원"
    )

    return {"response": response}
```

**SYNTHESIS_PROMPT**:
- 계산 결과를 자연어로 설명하는 시스템 프롬프트
- 최종 납부 세액, 계산 단계, 주의사항을 친절하게 안내
- 준법 고지 포함

**Fallback**: Gemini API 실패 시 템플릿 기반 응답 반환

### 4. Workflow 흐름 개선

**파일**: `ai/pipelines/langgraph_workflow.py`

#### Phase 3 Workflow 흐름도

```
START → intent_node
          ↓
     [intent = "gift_tax"?]
          ├─ YES → clarifying_node
          │          ↓
          │      [missing_parameters 비어있음?]
          │          ├─ NO → response_node (질문 반환) → END
          │          └─ YES → calculation_node → synthesis_node → END
          │
          └─ NO → response_node (일반 정보 또는 out_of_scope) → END
```

#### Conditional Routing

```python
def should_calculate(state: WorkflowState) -> str:
    """계산 가능 여부 판단"""
    missing = state.get("missing_parameters", [])

    if len(missing) == 0:
        return "calculation"  # 계산 가능
    else:
        return "response"     # 질문 계속
```

#### 노드 연결

```python
workflow.add_conditional_edges(
    "intent",
    lambda state: "clarifying" if state.get("intent") == "gift_tax" else "response",
    {
        "clarifying": "clarifying",
        "response": "response"
    }
)

workflow.add_conditional_edges(
    "clarifying",
    should_calculate,
    {
        "calculation": "calculation",
        "response": "response"
    }
)

workflow.add_edge("calculation", "synthesis")
workflow.add_edge("synthesis", END)
workflow.add_edge("response", END)
```

### 5. 멀티턴 대화 지원 (Backend 통합)

**파일**: `backend/chalicelib/services/message_service.py`

#### 이전 메시지 조회 및 파라미터 추출

```python
# Phase 3 추가: 이전 메시지 조회 (최근 10개, 역순)
previous_messages, _ = message_repo.find_all_by_session(
    session_id, limit=10, cursor=None
)

# Phase 3 추가: 마지막 assistant 메시지에서 collected_parameters 추출
previous_collected = {}
for msg in reversed(previous_messages):  # 오래된 것부터 순회
    if msg.role == "assistant" and msg.msg_metadata:
        collected = msg.msg_metadata.get("collected_parameters", {})
        if collected:
            previous_collected = collected
            break  # 가장 최근 assistant 메시지만 사용
```

#### AI 서비스 호출 (파라미터 전달)

```python
# 2. AI 응답 생성 (Phase 3: session_id, previous_collected_parameters 추가)
ai_response = generate_assistant_message(
    content=content,
    session_id=session_id,
    previous_collected_parameters=previous_collected
)
```

#### 서비스 시그니처 변경

**파일**: `ai/service.py`

**Phase 2 (기존)**:
```python
def generate_assistant_message(
    content: str,
    metadata: Optional[Dict[str, object]] = None
) -> Dict[str, object]:
    ...
```

**Phase 3 (변경)**:
```python
def generate_assistant_message(
    content: str,
    session_id: str = "default",
    previous_collected_parameters: Optional[Dict] = None,
    metadata: Optional[Dict[str, object]] = None
) -> Dict[str, object]:
    """멀티턴 대화 지원"""
    result = asyncio.run(run_workflow(
        user_message=content,
        session_id=session_id,
        previous_collected_parameters=previous_collected_parameters
    ))

    return {
        "content": result.get("response", ""),
        "metadata": {
            "intent": result.get("intent", ""),
            "session_id": result.get("session_id", ""),
            "collected_parameters": result.get("collected_parameters", {}),
            "missing_parameters": result.get("missing_parameters", []),
            "calculation": result.get("metadata", {}).get("calculation"),
        },
    }
```

#### metadata 구조 변경

**Phase 3에서 추가된 필드**:
- `collected_parameters`: 현재까지 수집된 파라미터 (Dict)
- `missing_parameters`: 누락된 Tier 1 필수 변수 목록 (List[str])
- `calculation`: 계산 결과 (Dict, 계산 완료 시에만 존재)

### 6. 대화 흐름 예시

#### Turn 1: 초기 질문 (일부 파라미터만 포함)

**User**: "부모님께 1억 받았어요"

**AI**:
```
증여일이 언제인가요?

💡 증여세는 증여일을 기준으로 신고 기한(3개월)과 공제액이 결정됩니다.
예시: 2025년 10월 15일, 올해 3월
```

**metadata.collected_parameters**:
```json
{
  "donor_relationship": "직계존속",
  "gift_property_value": 100000000
}
```

**metadata.missing_parameters**: `["gift_date"]`

#### Turn 2: 증여일 제공 → 계산 실행

**User**: "2025년 10월 15일이요"

**Backend**: 이전 메시지에서 `collected_parameters` 추출 → AI에 전달

**AI**: 파라미터 병합 → 계산 실행 → 자연어 답변 생성

**Response**:
```
부모님으로부터 1억원을 증여받으시는 경우, 최종 납부 세액은 0원입니다.

**계산 과정**:
1. 증여재산 가액: 100,000,000원
2. 증여재산 공제 (직계존속): -50,000,000원 (성인 기준 10년간 5천만원 공제)
3. 과세표준: 50,000,000원
4. 산출세액: 5,000,000원 (누진세율 적용)
5. 최종 납부세액: 5,000,000원

**주의사항**:
- 증여일로부터 3개월 이내 신고 필요
- 기한 후 신고 시 가산세 20% 부과
- 향후 10년 이내 동일인으로부터 추가 증여 시 합산 과세

본 안내는 정보 제공용이며, 정확한 세액은 세무 전문가와 상담하시기 바랍니다.
```

**metadata.collected_parameters**:
```json
{
  "donor_relationship": "직계존속",
  "gift_property_value": 100000000,
  "gift_date": "2025-10-15"
}
```

**metadata.missing_parameters**: `[]`

**metadata.calculation**: (계산 결과 전체 구조 포함)

## 테스트 결과

### 단위 테스트

**파일**: `ai/tests/test_parameter_extraction.py`

11개 테스트 케이스 (모두 통과 ✅):
- `test_check_missing_all_missing`: 모든 Tier 1 변수 누락
- `test_check_missing_gift_date_missing`: gift_date만 누락
- `test_check_missing_none_missing`: 모든 Tier 1 변수 수집됨
- `test_get_next_question_gift_date_first`: 첫 질문은 gift_date
- `test_get_next_question_donor_relationship_second`: 두 번째 질문은 donor_relationship
- `test_get_next_question_no_missing`: 누락 없으면 None 반환
- `test_generate_clarifying_question_single_missing`: 1개 누락 시 질문 생성
- `test_generate_clarifying_question_multiple_missing`: 여러 개 누락 시 순서대로
- `test_generate_clarifying_question_conditional_marriage`: 직계존속 관계 시 혼인 공제 질문
- `test_generate_clarifying_question_conditional_skip_marriage`: 기타친족은 혼인 공제 질문 생략
- `test_generate_clarifying_question_no_missing`: 누락 없으면 None 반환

### E2E 테스트

**파일**: `ai/tests/test_clarifying_workflow.py`

3개 시나리오 테스트:
1. **즉시 계산 가능**: 모든 파라미터 포함된 질문 → 바로 계산 실행
2. **멀티턴 파라미터 수집**: 2번의 질문/답변 후 계산 실행
3. **Intent 분류**: gift_tax, general_info, out_of_scope 정확히 분류

**주의**: 실제 Gemini API 호출 필요 (유효한 GOOGLE_API_KEY 필요)

### 로컬 테스트 (브라우저)

**환경**: `frontend/.env.local`에 Backend API URL 설정

**시나리오 1**: 단계적 질문
1. User: "부모님께 1억 받았어요"
2. AI: "증여일이 언제인가요?" (✅)
3. User: "2025년 10월 15일이요"
4. AI: 계산 결과 반환 (✅)

**시나리오 2**: 즉시 계산
1. User: "2025년 10월 15일에 부모님께 1억원을 받았는데 세금이 얼마나요?"
2. AI: 계산 결과 즉시 반환 (✅)

## 문서 업데이트

### 1. Backend API Contract 문서

**파일**: `ai/backend_api_contract.md`

**Section 5 추가**: "Phase 3: 멀티턴 대화 지원"
- `generate_assistant_message()` 시그니처 변경
- Backend 연동 로직 (코드 예시 포함)
- metadata 구조 변경 (3개 필드 추가)
- 대화 흐름 예시 (Turn 1 → Turn 2)
- 참조 문서 링크

### 2. Message Format 문서

**파일**: `docs/prd_detail/ai-logic/03-message-format.md`

**Section 3.8 추가**: "Phase 3 구현 상태"
- 7개 필드별 구현 상태 표 (✅ 구현됨 / 🔜 Phase 4)
- Phase 3에서 추가된 필드 설명 (collected_parameters, missing_parameters, calculation)
- 멀티턴 대화 지원 설명
- Phase 4 이후 계획 (RAG, Tier 2 질문)

### 3. Agent 운영 규칙 문서

**파일**: `docs/prd_detail/ai-logic/agent.md`

**Python 실행 환경 규칙 추가**:
```
- Python 실행 환경: 모든 Python 명령은 반드시 프로젝트 루트의 `.venv` 가상환경을 활성화한 후 실행
```

## 주요 의사결정

### 1. Gemini API로 파라미터 파싱

**이유**: 자연어 표현을 정규화된 값으로 변환
- "1억" → 100000000
- "부모님" → "직계존속"
- "오늘" → 날짜 객체

**장점**: 유연한 자연어 처리, 높은 정확도
**단점**: API 비용 발생, 지연 시간 증가
**결론**: 사용자 경험 향상이 더 중요

### 2. Tier 2 변수는 기본값 사용 (Phase 4로 연기)

**현재**: is_generation_skipping, is_minor_recipient, is_non_resident는 기본값(false) 사용
**Phase 4**: 명시적으로 질문하고 assumptions 배열에 기록
**이유**: Phase 3 범위 제한, 핵심 기능(Tier 1) 우선 검증

### 3. 1개씩 질문하는 전략

**대안**: 여러 개 누락 시 한 번에 질문 ("증여일과 금액을 알려주세요")
**선택**: 1개씩 질문
**이유**: 사용자 부담 감소, 대화 맥락 유지, 오류 가능성 감소

### 4. Backend 파일 수정 허용

**경계**: LLM 팀은 AI 모듈만 담당
**예외**: Phase 3 멀티턴 지원을 위해 Backend `message_service.py` 수정 허용
**이유**: 이전 메시지 조회 및 파라미터 추출은 Backend 로직과 밀접
**범위**: 최소한의 수정 (107-149줄, 43줄 추가)

## 기술 스택

- **LangGraph**: 0.6.10 (StateGraph, Conditional Edges)
- **langchain-core**: 0.3.79
- **Gemini API**: gemini-2.5-flash (Intent 분류, 파라미터 파싱, 답변 합성)
- **Python**: 3.12 (가상환경 `.venv`)
- **pytest**: 단위 테스트
- **pytest-asyncio**: 비동기 테스트
- **Pydantic**: 데이터 검증 (GiftTaxSimpleInput)

## 향후 계획 (Phase 4+)

### 1. RAG 통합 (Issue #35)
- 법령 검색 Tool 구현
- `citations`, `clarifying_context` 필드 실제 사용
- pgvector 기반 유사도 검색

### 2. Tier 2 명시적 질문
- is_generation_skipping, is_minor_recipient, is_non_resident 질문
- `assumptions` 배열에 기본값 사용 기록
- 사용자에게 전제 조건 명확히 안내

### 3. Tier 3 조건부 질문
- 직계존비속 관계일 때만 혼인/출산 공제, 담보채무 질문
- 기타 관계는 질문 생략

### 4. 상속세 계산 지원
- `inheritance_tax` Intent 처리 로직 구현
- 상속세 특화 Clarifying 질문
- 상속세 계산 Tool 구현

### 5. 프롬프트 최적화
- Edge case 처리 (애매한 표현, 오타)
- Few-shot 예시 추가
- 답변 품질 개선

### 6. 성능 최적화
- Gemini API 호출 횟수 최소화
- 캐싱 전략 검토
- 응답 속도 개선

## 참고 문서

- `docs/prd_detail/ai-logic/agent.md` - Agent Guardrails
- `docs/prd_detail/ai-logic/04-clarifying-strategy.md` - 9개 변수 정의 및 Tier 시스템
- `docs/prd_detail/ai-logic/04-clarifying-implementation-spec.md` - Phase 3 구현 명세
- `docs/prd_detail/ai-logic/03-message-format.md` - metadata 구조 정의
- `ai/backend_api_contract.md` - AI ↔ Backend 통합 계약
- `docs/history/202510161610_langgraph_basic_workflow.md` - Phase 2 구현 (Issue #22)
- `docs/history/202510161552_gift_tax_calculator_implementation.md` - Phase 1 계산기 (Issue #21)

## 관련 커밋

(브랜치 병합 후 커밋 해시 추가 예정)

1. `feat: implement clarifying node with 9-variable system`
   - Clarifying 노드 구현
   - 파라미터 파싱 유틸리티
   - 질문 생성 로직

2. `feat: integrate calculation tool with clarifying workflow`
   - Calculation 노드 구현
   - Synthesis 노드 구현
   - Workflow 흐름 개선

3. `feat: add multi-turn dialogue support in backend`
   - Backend 메시지 조회 로직 추가
   - AI 서비스 시그니처 변경
   - metadata 구조 확장

4. `docs: update backend api contract and message format for phase 3`
   - Backend API 문서 업데이트
   - Message Format 문서 업데이트
   - Agent 운영 규칙 추가

## 성과 및 결론

### 주요 성과

1. **완전한 멀티턴 대화 시스템**: 사용자가 질문을 분할하여 입력해도 파라미터가 누적되어 최종 계산 가능
2. **자연어 이해 능력**: "1억", "부모님", "오늘"과 같은 자연어 표현을 정규화된 값으로 변환
3. **사용자 친화적 질문**: Emoji와 예시로 질문 안내, 1개씩 질문하여 부담 감소
4. **Backend 통합 완료**: 이전 메시지 조회 및 파라미터 누적 로직 구현
5. **포괄적 테스트**: 단위 테스트 11개, E2E 테스트 3개로 안정성 검증

### 기술적 도전과 해결

1. **비동기 Workflow 관리**: LangGraph의 `ainvoke` 사용하여 모든 노드 비동기 처리
2. **파라미터 누적 로직**: 기존 값과 신규 값 병합 시 null 아닌 값만 업데이트
3. **Backend 상태 관리**: PostgreSQL JSONB에 collected_parameters 저장, 다음 턴에서 재사용
4. **날짜 파싱**: 문자열("2025-10-15") → date 객체 변환 및 검증

### 배운 점

1. **LLM 프롬프트 설계**: 정확한 출력 형식 강제하기 위해 JSON Schema + Few-shot 예시 필수
2. **상태 관리 복잡도**: 멀티턴 대화는 Backend와 AI 모듈 간 명확한 계약 필요
3. **테스트 전략**: 실제 API 호출 테스트와 단위 테스트 분리 필요
4. **문서화 중요성**: Backend 통합 로직 변경 시 API Contract 문서 즉시 업데이트 필수

Phase 3 구현으로 슈킹 AI 상담 서비스의 핵심 대화 기능이 완성되었습니다. 사용자는 이제 자연어로 질문하고, AI가 필요한 정보를 단계적으로 수집하여 정확한 증여세 계산 결과를 제공받을 수 있습니다.
