# LangGraph 기본 Workflow 구현 (Issue #22)

**작성일**: 2025-10-16
**관련 Issue**: #22
**관련 PR**: #34
**작업 브랜치**: `feature/langgraph-basic-workflow`

## 개요

증여세 계산 Tool 구현(Issue #21)에 이어, LangGraph 기반의 기본 Workflow를 구축하고 Gemini API 기반 Intent 분류 시스템을 구현했습니다. Phase 2의 핵심 목표는 키워드가 없어도 맥락상 정확한 의도 분류가 가능한 시스템을 만드는 것이었습니다.

## 주요 구현 내용

### 1. LangGraph Workflow 구조 (Phase 2)

**파일**: `ai/pipelines/langgraph_workflow.py`, `ai/schemas/workflow_state.py`

#### WorkflowState 정의 (8개 필드)
```python
class WorkflowState(TypedDict, total=False):
    session_id: str
    messages: list[dict]
    user_message: str
    intent: Literal["gift_tax", "inheritance_tax", "general_info", "out_of_scope"]
    collected_parameters: dict
    missing_parameters: list[str]
    response: str
    metadata: dict
```

#### Workflow 노드 구성
1. **Intent Node** (비동기): Gemini API 기반 의도 분류
2. **Tool Node** (비동기): 증여세 계산 Tool 실행
3. **Response Node** (비동기): Intent별 응답 생성

#### 흐름도
```
START → intent_node → should_use_tool?
                       ├─ gift_tax → tool_node → END
                       └─ others → response_node → END
```

### 2. Gemini 기반 Intent 분류

**파일**: `ai/prompts/system.py`

#### 기존 문제점 (키워드 기반)
- "증여세 계산해줘" → ✅ gift_tax
- "부모님께 돈을 받았는데 세금 얼마내야해?" → ❌ general_info (키워드 없음)

#### 개선 사항 (Gemini API 기반)
```python
async def intent_node(state: WorkflowState) -> dict:
    """Gemini API를 통한 정교한 Intent 분류"""
    settings = GeminiSettings.from_env()
    client = GeminiClient(settings)

    intent_raw = await client.generate_content(
        system_prompt=INTENT_CLASSIFICATION_PROMPT,
        user_message=user_message
    )

    intent = intent_raw.strip().lower()
    # 유효성 검증 및 fallback 처리
```

#### INTENT_CLASSIFICATION_PROMPT
- 4가지 의도 명확히 정의 (gift_tax, inheritance_tax, general_info, out_of_scope)
- 키워드 없이도 맥락 기반 분류 가능
- 정확히 1개 단어만 출력하도록 강제
- Few-shot 예시 포함

**예시**:
- "부모님께 돈을 받았는데" → gift_tax (맥락 이해)
- "할아버지가 돌아가셔서" → inheritance_tax (맥락 이해)
- "오늘 날씨 어때?" → out_of_scope

### 3. Tool Node 통합

**파일**: `ai/pipelines/langgraph_workflow.py`

```python
async def tool_node(state: WorkflowState) -> dict:
    """증여세 계산 Tool 실행"""
    from ai.tools import calculate_gift_tax_simple
    from datetime import date

    if intent == "gift_tax":
        result = calculate_gift_tax_simple(
            gift_date=date(2025, 10, 16),
            donor_relationship="직계존속",
            gift_property_value=100_000_000,
            # ... (Phase 3에서 Clarifying으로 실제 파라미터 수집 예정)
        )
        response = f"증여세 계산 결과: {result['final_tax']:,}원"
```

#### Conditional Routing
```python
def should_use_tool(state: WorkflowState) -> str:
    intent = state.get("intent", "general_info")
    if intent == "gift_tax":
        return "tool"
    else:
        return "response"
```

### 4. Backend 통합

**파일**: `ai/service.py`

기존 `ChatPipeline` 대신 LangGraph Workflow 사용:
```python
def generate_assistant_message(content: str, metadata: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    result = asyncio.run(run_workflow(user_message=content))

    return {
        "content": result.get("response", ""),
        "metadata": {
            "intent": result.get("intent", ""),
            "session_id": result.get("session_id", ""),
        },
    }
```

### 5. Out-of-Scope 처리

도메인 외 질문을 정중하게 거절:
```python
if intent == "out_of_scope":
    response = "죄송합니다. 저는 증여세와 상속세 관련 상담만 도와드릴 수 있습니다. 증여세나 상속세 관련 질문이 있으시면 말씀해 주세요."
```

## 테스트 결과

### E2E 테스트 (브라우저)
✅ **키워드 없는 증여세 질의**: "부모님한테 돈을 받았는데 세금 얼마내야해?" → Tool 호출 성공
✅ **키워드 없는 상속세 질의**: "할아버지가 돌아가셔서..." → inheritance_tax 분류
✅ **일반 인사**: "안녕하세요" → Gemini 응답
✅ **Out-of-scope**: "오늘 날씨 어때요?" → 거절 메시지

### 단위 테스트
**파일**: `ai/tests/test_langgraph_workflow.py`

- 10개 테스트 케이스 작성
- Workflow 생성, State 초기화, Intent 분류, Tool 실행 검증
- **주의**: 실제 Gemini API 호출 필요 (유효한 GOOGLE_API_KEY 필요)

## 기술 스택

- **LangGraph**: 0.6.10
- **langchain-core**: 0.3.79
- **Gemini API**: text-embedding-004 (향후 RAG용), gemini-2.5-flash (Intent 분류)
- **Python**: 3.12 (가상환경)
- **pytest-asyncio**: 비동기 테스트

## 의존성 통합

**파일**: `backend/requirements.txt`

```txt
# AI/ML
httpx>=0.28.0,<0.29.0
langgraph==0.6.10
langchain-core==0.3.79
```

## 개발 환경 설정

### 로컬 개발 환경 구성

**파일**: `local/docker-compose.yml`

PostgreSQL + pgvector 환경 (로컬 테스트용):
```yaml
services:
  postgres:
    image: pgvector/pgvector:pg17
    container_name: shuking-postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

### .gitignore 정리

**파일**: `.gitignore`

추가 항목:
- `.python-version` (로컬 Python 버전 관리)
- `package-lock.json` (npm 의존성 락 파일)

## 주요 의사결정

### 1. Intent 분류를 Gemini API로 전환
- **이유**: 키워드 기반은 "부모님께 돈을 받았는데"와 같은 자연어 표현을 처리 불가
- **장점**: 맥락 기반 정확한 분류, 유연한 질의 처리
- **단점**: 모든 요청마다 API 호출 비용/지연 발생
- **결론**: 정확도 향상이 더 중요하다고 판단

### 2. Tool Node에 하드코딩 파라미터 사용
- **이유**: Phase 3의 Clarifying 노드 구현 전까지 임시 방안
- **현재**: 테스트용 고정 파라미터로 Tool 호출 검증
- **Phase 3**: Clarifying 노드로 사용자로부터 실제 파라미터 수집

### 3. ChatPipeline 제거하고 LangGraph Workflow로 전환
- **이유**: 단일 진실 소스(Single Source of Truth) 유지
- **기존**: ChatPipeline (간단한 메시지 기능)
- **현재**: LangGraph Workflow (상태 관리, 조건부 분기)

## 향후 계획 (Phase 3)

### 1. Clarifying 노드 구현
- 필수 파라미터 체크 및 질문 생성
- `docs/prd_detail/ai-logic/04-clarifying-strategy.md` 참고
- `collected_parameters`, `missing_parameters` State 활용

### 2. RAG 통합
- Issue #35: 법령 검색 Tool 구현
- `law_sources` 테이블 활용
- Citation 구조 정규화

### 3. 상속세 계산 지원
- `inheritance_tax` Intent 처리 로직 구현
- 상속세 특화 Clarifying 질문

### 4. 대화 맥락 유지
- `messages` State에 대화 기록 저장
- 이전 질문 참조 가능

## 참고 문서

- `docs/prd_detail/ai-logic/agent.md` - Agent Guardrails
- `docs/prd_detail/ai-logic/ai-logic.md` - AI 로직 설계
- `docs/prd_detail/ai-logic/04-clarifying-strategy.md` - Clarifying 전략
- `docs/prd_detail/ai-logic/functional-spec.md` - LLM-6.x 태스크 정의

## 관련 커밋

1. `feat: implement LangGraph basic workflow with out-of-scope handling (#22)`
   - LangGraph Workflow 기본 구조 구현
   - Out-of-scope 처리 추가

2. `feat: improve intent classification with Gemini API`
   - Gemini 기반 Intent 분류로 전환
   - Tool Node 통합
   - Backend 연동

3. `chore: update .gitignore and remove package-lock.json from tracking`
   - .gitignore 정리
   - 개발 환경 파일 제외
