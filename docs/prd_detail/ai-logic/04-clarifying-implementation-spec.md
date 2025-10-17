# Phase 3 Clarifying 노드 상세 구현 명세

**문서 버전**: v1.0
**작성일**: 2025-10-16
**대상**: Issue #23 구현
**목적**: 다음 브랜치에서 바로 코드 구현이 가능하도록 모든 모호한 부분을 구체화

---

## 1. 핵심 의사결정

### 1.1 변수 개수 최종 확정: **9개**

**결정**: `past_gifts_value`, `past_tax_paid` 제외

**이유**:
- Phase 1 구현 (`ai/tools/gift_tax/models.py`)에서 9개 변수로 확정
- 국세청 간편계산기 범위 준수 (10년 합산 미지원)
- Issue #21에서 명시적으로 제외 결정

**9개 변수 목록**:
```python
# Tier 1 (필수 기본 정보)
1. gift_date: date
2. donor_relationship: Literal["배우자", "직계존속", "직계비속", "기타친족"]
3. gift_property_value: int

# Tier 2 (특례 판단, 기본값 가능)
4. is_generation_skipping: bool = False
5. is_minor_recipient: bool = False
6. is_non_resident: bool = False

# Tier 3 (공제 및 채무, 조건부/선택)
7. marriage_deduction_amount: int = 0
8. childbirth_deduction_amount: int = 0
9. secured_debt: int = 0
```

### 1.2 멀티턴 대화 상태 관리: **백엔드 세션 기반**

**결정**: PostgreSQL 세션을 통한 대화 히스토리 관리

**현재 구조**:
```
Backend (message_service) → AI (service.py) → LangGraph (workflow)
                               ↓
                  단일 턴만 처리 (이전 맥락 없음)
```

**Phase 3 구조**:
```
Backend (message_service)
  ├─ 이전 메시지 조회 (MessageRepository)
  ├─ collected_parameters 추출
  └─ AI 서비스에 전달
       ↓
AI (service.py)
  ├─ conversation_history 포함
  └─ run_workflow()
       ↓
LangGraph (clarifying_node)
  └─ 파라미터 누적 및 질문 생성
```

**인터페이스 변경**:
```python
# 기존
def generate_assistant_message(content: str, metadata: Optional[Dict] = None) -> Dict

# Phase 3
def generate_assistant_message(
    content: str,
    session_id: str,
    previous_collected_parameters: Optional[Dict] = None,
    metadata: Optional[Dict] = None
) -> Dict
```

### 1.3 파라미터 파싱: **Gemini API 구조화 출력**

**결정**: Gemini API에 JSON 스키마 기반 파싱 요청

**장점**:
- 자연어 유연성 ("1억", "부모님", "오늘")
- 맥락 이해 능력

**단점**:
- API 호출 비용
- 파싱 실패 가능성

**대체 전략**: Gemini 실패 시 기본값 사용 + 명시적 질문

### 1.4 질문 생성: **Tier 순서대로 1개씩**

**결정**: 한 번에 **정확히 1개** 질문만 생성

**이유**:
- 사용자 경험 단순화
- 명확한 대화 흐름
- 응답 품질 향상

**우선순위**:
1. Tier 1 필수 변수 (gift_date, donor_relationship, gift_property_value)
2. Tier 2 특례 변수 (세대생략, 미성년자, 비거주자)
3. Tier 3 공제 변수 (혼인, 출산, 채무)

### 1.5 답변 합성: **템플릿 + LLM 하이브리드**

**결정**: 하이브리드 방식

**구조**:
- **계산 결과 표시**: 템플릿 기반 (일관성)
- **설명 및 가이드**: Gemini API (자연스러움)
- **준법 고지**: 템플릿 (필수 문구)

---

## 2. 파라미터 파싱 상세 명세

### 2.1 Gemini API 프롬프트

```python
PARAMETER_EXTRACTION_PROMPT = """당신은 증여세 계산을 위한 정보 추출 전문가입니다.

사용자 메시지에서 다음 9개 변수를 추출하세요. 언급되지 않은 변수는 null로 설정합니다.

### 변수 목록

**Tier 1 (필수 기본 정보)**
1. gift_date: 증여일 (YYYY-MM-DD 형식 문자열)
2. donor_relationship: 증여자 관계 ("배우자"|"직계존속"|"직계비속"|"기타친족")
3. gift_property_value: 증여재산가액 (숫자)

**Tier 2 (특례 판단)**
4. is_generation_skipping: 세대생략 여부 (true|false)
5. is_minor_recipient: 미성년자 여부 (true|false)
6. is_non_resident: 비거주자 여부 (true|false)

**Tier 3 (공제 및 채무)**
7. marriage_deduction_amount: 혼인공제액 (숫자, 0~100000000)
8. childbirth_deduction_amount: 출산공제액 (숫자, 0~100000000)
9. secured_debt: 담보채무액 (숫자)

### 파싱 규칙

**금액 변환**:
- "1억" → 100000000
- "5천만원" → 50000000
- "3억5천" → 350000000
- "200만원" → 2000000
- "100,000,000원" → 100000000

**날짜 변환** (기준일: {today}):
- "오늘" → {today}
- "어제" → {yesterday}
- "이번 달 15일" → {this_month_15th}
- "2025년 10월 15일" → "2025-10-15"
- "10/15" → "{current_year}-10-15"

**관계 매핑** (수증자 기준):
- "부모", "부모님", "아버지", "어머니" → "직계존속"
- "자녀", "아들", "딸" → "직계비속"
- "배우자", "남편", "아내" → "배우자"
- "형제", "자매", "친척", "삼촌" → "기타친족"
- "조부모", "할아버지", "할머니" → "직계존속"
- "손자", "손녀" → "직계비속"

**불린 변환**:
- "조부모가 손자에게", "세대를 건너뛴" → is_generation_skipping: true
- "미성년자", "미성년", "만 19세 미만" → is_minor_recipient: true
- "비거주자", "해외 거주", "외국 거주" → is_non_resident: true

**공제액**:
- "혼인 관련", "결혼 전후" → marriage_deduction_amount에 금액 또는 100000000 (최대)
- "출산 관련", "아이 출생" → childbirth_deduction_amount에 금액 또는 100000000 (최대)

**채무**:
- "대출", "담보", "임대보증금" → secured_debt에 금액

### 출력 형식

**중요**: JSON 형식만 출력하세요. 다른 텍스트나 설명은 포함하지 마세요.

```json
{
  "gift_date": "2025-10-15" 또는 null,
  "donor_relationship": "직계존속" 또는 null,
  "gift_property_value": 100000000 또는 null,
  "is_generation_skipping": false,
  "is_minor_recipient": false,
  "is_non_resident": false,
  "marriage_deduction_amount": 0,
  "childbirth_deduction_amount": 0,
  "secured_debt": 0
}
```

### 사용자 메시지

{user_message}
"""
```

### 2.2 파싱 응답 예시

**입력**: "부모님께 1억 받았어요"

**출력**:
```json
{
  "gift_date": null,
  "donor_relationship": "직계존속",
  "gift_property_value": 100000000,
  "is_generation_skipping": false,
  "is_minor_recipient": false,
  "is_non_resident": false,
  "marriage_deduction_amount": 0,
  "childbirth_deduction_amount": 0,
  "secured_debt": 0
}
```

**입력**: "2025년 10월 15일이요"

**출력**:
```json
{
  "gift_date": "2025-10-15",
  "donor_relationship": null,
  "gift_property_value": null,
  "is_generation_skipping": false,
  "is_minor_recipient": false,
  "is_non_resident": false,
  "marriage_deduction_amount": 0,
  "childbirth_deduction_amount": 0,
  "secured_debt": 0
}
```

### 2.3 파싱 실패 처리

```python
def extract_parameters(user_message: str) -> dict:
    """
    Gemini API로 파라미터 추출

    Returns:
        dict: 파싱된 파라미터 (실패 시 빈 dict 또는 기본값)
    """
    try:
        # Gemini API 호출
        response = await gemini_client.generate_content(
            system_prompt=PARAMETER_EXTRACTION_PROMPT.format(
                today=date.today().isoformat(),
                yesterday=(date.today() - timedelta(days=1)).isoformat(),
                user_message=user_message
            ),
            user_message=user_message
        )

        # JSON 파싱
        parsed = json.loads(response)
        return parsed

    except (json.JSONDecodeError, GeminiClientError) as e:
        # 파싱 실패 시 기본값 반환
        logger.warning(f"Parameter extraction failed: {e}")
        return {
            "is_generation_skipping": False,
            "is_minor_recipient": False,
            "is_non_resident": False,
            "marriage_deduction_amount": 0,
            "childbirth_deduction_amount": 0,
            "secured_debt": 0
        }
```

---

## 3. 질문 생성 상세 명세

### 3.1 질문 템플릿 (전체 9개)

```python
CLARIFYING_QUESTIONS = {
    # Tier 1
    "gift_date": """증여일이 언제인가요?

💡 증여세는 증여일을 기준으로 신고 기한(3개월)과 공제액이 결정됩니다.
예시: 2025년 10월 15일, 올해 3월""",

    "donor_relationship": """증여하시는 분과의 관계가 어떻게 되시나요?

💡 관계에 따라 공제 한도가 다릅니다:
• 배우자: 6억원
• 부모/자녀: 5천만원
• 기타 친족: 1천만원

선택지: 배우자, 부모님, 자녀, 조부모, 기타""",

    "gift_property_value": """증여받으신 재산의 가액이 얼마인가요?

💡 평가 기준:
• 부동산: 최근 6개월 매매가 또는 공시지가
• 주식: 상장(2개월 평균), 비상장(평가액)

예시: 5억원, 200,000,000원""",

    # Tier 2
    "is_generation_skipping": """조부모님께서 손자/손녀에게 직접 증여하시는 경우인가요?

⚠️ 세대를 건너뛴 증여: 산출세액의 30% 할증
(단, 부모님이 이미 사망하신 경우 제외)

선택지: 예 / 아니오""",

    "is_minor_recipient": """증여받으시는 분이 미성년자(만 19세 미만)인가요?

💡 미성년자 공제: 직계존속으로부터 증여 시 2천만원
(성인: 5천만원)

선택지: 예 / 아니오""",

    "is_non_resident": """증여받으시는 분이 해외에 거주 중이신가요?

💡 비거주자: 1년 중 183일 이상 해외 거주

선택지: 예 / 아니오""",

    # Tier 3
    "marriage_deduction_amount": """혼인 전후 2년 이내에 증여받으신 것인가요?

💡 혼인일 전후 각 2년(총 4년) 이내 증여 시 최대 1억원 추가 공제

선택지: 예(금액 입력) / 아니오""",

    "childbirth_deduction_amount": """자녀 출생 2년 이내에 증여받으신 것인가요?

💡 자녀 출생일로부터 2년 이내 증여 시 최대 1억원 추가 공제

선택지: 예(금액 입력) / 아니오""",

    "secured_debt": """증여받은 재산에 담보대출이나 임대보증금이 있나요?

💡 부담부 증여: 증여자의 채무를 수증자가 인수하는 경우
예시: 5억 아파트 + 2억 대출 = 실제 증여가액 3억

선택지: 없음(0원) / 있음(금액 입력)"""
}
```

### 3.2 질문 우선순위 알고리즘

```python
def get_next_question(collected_parameters: dict, missing_parameters: list) -> Optional[str]:
    """
    다음 질문할 변수 선택

    우선순위:
    1. Tier 1 필수 변수
    2. Tier 2 특례 변수 (기본값 사용 가능하지만 물어봄)
    3. Tier 3 조건부 변수

    Returns:
        str: 변수명 (예: "gift_date") 또는 None (모두 수집됨)
    """
    # Tier 1 체크
    tier1_required = ["gift_date", "donor_relationship", "gift_property_value"]
    for param in tier1_required:
        if param in missing_parameters:
            return param

    # Tier 2 체크 (Phase 3에서는 기본값 사용, Phase 4에서 질문 추가)
    # Phase 3에서는 Tier 2를 건너뛰고 바로 계산

    # Tier 3 조건부 체크
    donor_relationship = collected_parameters.get("donor_relationship")

    # 혼인공제 (직계존속/비속만)
    if donor_relationship in ["직계존속", "직계비속"]:
        if "marriage_deduction_amount" not in collected_parameters:
            return "marriage_deduction_amount"
        if "childbirth_deduction_amount" not in collected_parameters:
            return "childbirth_deduction_amount"

    # 담보채무 (Phase 3에서는 생략, 기본값 0 사용)

    # 모든 필수 변수 수집 완료
    return None
```

### 3.3 질문 생성 로직

```python
def generate_clarifying_question(
    collected_parameters: dict,
    missing_parameters: list
) -> Optional[str]:
    """
    Clarifying 질문 생성

    Returns:
        str: 질문 텍스트 또는 None (계산 가능)
    """
    next_param = get_next_question(collected_parameters, missing_parameters)

    if next_param is None:
        return None  # 계산 가능

    # 질문 템플릿 반환
    return CLARIFYING_QUESTIONS.get(next_param, f"{next_param}을(를) 알려주세요.")
```

---

## 4. 답변 합성 상세 명세

### 4.1 답변 합성 프롬프트

```python
SYNTHESIS_PROMPT = """당신은 증여세 계산 결과를 친절하게 설명하는 AI입니다.

아래 계산 결과를 바탕으로 사용자에게 자연스럽게 설명해주세요.

### 계산 결과

**최종 세액**: {final_tax:,}원
**증여재산가액**: {gift_value:,}원
**공제액**: {total_deduction:,}원
**과세표준**: {taxable_base:,}원

### 계산 단계
{steps_formatted}

### 주의사항
{warnings_formatted}

---

다음 형식으로 답변하세요:

1. **결과 요약**: "증여자와 수증자 관계, 금액을 언급하며 최종 세액 명시"
2. **계산 과정 설명**: "주요 단계를 1-2문장으로 설명"
3. **주의사항 안내**: "신고 기한, 가산세 등 필수 안내"

**중요**: 답변 끝에 반드시 다음 문구를 포함하세요:
"본 안내는 정보 제공용이며, 정확한 세액은 세무 전문가와 상담하시기 바랍니다."
"""
```

### 4.2 템플릿 기반 답변 예시

**입력**:
```python
{
    "donor_relationship": "직계존속",
    "gift_property_value": 100000000,
    "final_tax": 5000000,
    "gift_value": 100000000,
    "total_deduction": 50000000,
    "taxable_base": 50000000,
    "steps": [...],
    "warnings": [...]
}
```

**출력**:
```
부모님께서 자녀에게 1억원을 증여하신 경우, 최종 납부 세액은 **500만원**입니다.

**계산 과정**:
1. 증여재산가액: 1억원
2. 증여재산공제: 5천만원 (직계존속 기본공제)
3. 과세표준: 5천만원
4. 산출세액: 500만원 (과세표준 × 10%)

**주의사항**:
- 증여일로부터 3개월 이내(2026년 1월 15일까지) 신고해야 합니다.
- 기한 후 신고 시 가산세 20%가 부과됩니다.

본 안내는 정보 제공용이며, 정확한 세액은 세무 전문가와 상담하시기 바랍니다.
```

---

## 5. Workflow 노드 상세 설계

### 5.1 전체 Workflow 구조

```
START
  ↓
intent_node (기존)
  ↓
[intent = "gift_tax"?]
  ↓ YES
clarifying_node (신규)
  ├─ 파라미터 파싱
  ├─ 누적 병합
  └─ 누락 체크
  ↓
[missing_parameters 비어있음?]
  ├─ NO → response_node (질문 반환) → END
  └─ YES ↓
calculation_node (신규)
  ├─ Pydantic 검증
  └─ Tool 호출
  ↓
synthesis_node (신규)
  ├─ 템플릿 적용
  └─ LLM 설명 생성
  ↓
END
```

### 5.2 Node: clarifying_node

**함수 시그니처**:
```python
async def clarifying_node(state: WorkflowState) -> dict:
    """
    Clarifying 노드: 파라미터 수집 및 질문 생성

    Args:
        state: WorkflowState
            - user_message: 현재 사용자 입력
            - collected_parameters: 이전까지 수집된 파라미터
            - intent: "gift_tax"

    Returns:
        dict: 업데이트할 상태
            - collected_parameters: 병합된 파라미터
            - missing_parameters: 누락 목록
            - response: 질문 텍스트 (있는 경우)
    """
```

**처리 로직 (의사코드)**:
```python
# 1. 현재 메시지에서 파라미터 파싱
new_params = await extract_parameters(state["user_message"])

# 2. 기존 파라미터와 병합 (최신 값 우선)
collected = state.get("collected_parameters", {})
collected.update({k: v for k, v in new_params.items() if v is not None})

# 3. 필수 변수 체크
required = ["gift_date", "donor_relationship", "gift_property_value"]
missing = [p for p in required if p not in collected or collected[p] is None]

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

### 5.3 Node: calculation_node

**함수 시그니처**:
```python
async def calculation_node(state: WorkflowState) -> dict:
    """
    계산 노드: GiftTaxSimpleInput 생성 및 Tool 호출

    Args:
        state: WorkflowState
            - collected_parameters: 9개 변수 완성

    Returns:
        dict: 업데이트할 상태
            - metadata.calculation: 계산 결과
    """
```

**처리 로직 (의사코드)**:
```python
from ai.tools import calculate_gift_tax_simple
from ai.tools.gift_tax.models import GiftTaxSimpleInput
from datetime import date

# 1. collected_parameters → Pydantic 모델 변환
params = state["collected_parameters"]

try:
    # 날짜 문자열 → date 객체
    gift_date_obj = date.fromisoformat(params["gift_date"])

    # GiftTaxSimpleInput 생성 (Pydantic 검증)
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

    # 2. 계산 Tool 호출
    result = calculate_gift_tax_simple(**tax_input.model_dump())

    # 3. 결과 저장
    return {
        "metadata": {
            "calculation": result
        }
    }

except Exception as e:
    # 검증 실패 또는 계산 오류
    return {
        "response": f"계산 중 오류가 발생했습니다: {str(e)}"
    }
```

### 5.4 Node: synthesis_node

**함수 시그니처**:
```python
async def synthesis_node(state: WorkflowState) -> dict:
    """
    답변 합성 노드: 계산 결과를 자연어로 변환

    Args:
        state: WorkflowState
            - metadata.calculation: 계산 결과
            - collected_parameters: 수집된 파라미터

    Returns:
        dict: 업데이트할 상태
            - response: 자연어 답변
    """
```

**처리 로직 (의사코드)**:
```python
from ai.clients.gemini import GeminiClient
from ai.config import GeminiSettings

calculation = state["metadata"]["calculation"]
params = state["collected_parameters"]

# 1. steps 포맷팅
steps_text = "\n".join([
    f"{s['step']}. {s['description']}: {s['value']:,}원 ({s.get('detail', '')})"
    for s in calculation["steps"]
])

# 2. warnings 포맷팅
warnings_text = "\n".join([f"- {w}" for w in calculation["warnings"]])

# 3. Gemini API로 자연어 설명 생성
settings = GeminiSettings.from_env()
client = GeminiClient(settings)

prompt = SYNTHESIS_PROMPT.format(
    final_tax=calculation["final_tax"],
    gift_value=calculation["gift_value"],
    total_deduction=calculation["total_deduction"],
    taxable_base=calculation["taxable_base"],
    steps_formatted=steps_text,
    warnings_formatted=warnings_text
)

response = await client.generate_content(
    system_prompt=prompt,
    user_message=f"관계: {params['donor_relationship']}, 금액: {params['gift_property_value']:,}원"
)

return {
    "response": response
}
```

### 5.5 분기 조건 함수

```python
def should_calculate(state: WorkflowState) -> str:
    """
    계산 가능 여부 판단

    Returns:
        "response": 질문 필요 (missing_parameters 있음)
        "calculation": 계산 가능 (필수 변수 모두 수집)
    """
    missing = state.get("missing_parameters", [])

    if len(missing) == 0:
        return "calculation"
    else:
        return "response"
```

---

## 6. 멀티턴 대화 상태 관리

### 6.1 Backend 인터페이스 변경

#### 파일: `ai/service.py`

**기존**:
```python
def generate_assistant_message(content: str, metadata: Optional[Dict] = None) -> Dict:
    result = asyncio.run(run_workflow(user_message=content))
    return {
        "content": result.get("response", ""),
        "metadata": {
            "intent": result.get("intent", ""),
            "session_id": result.get("session_id", ""),
        },
    }
```

**Phase 3**:
```python
def generate_assistant_message(
    content: str,
    session_id: str,
    previous_collected_parameters: Optional[Dict] = None,
    metadata: Optional[Dict] = None
) -> Dict:
    """
    사용자 메시지를 받아 LangGraph Workflow 실행

    Args:
        content: 사용자 메시지
        session_id: 세션 ID (대화 컨텍스트 추적용)
        previous_collected_parameters: 이전까지 수집된 파라미터
        metadata: 추가 메타데이터

    Returns:
        dict: {
            "content": str,
            "metadata": {
                "intent": str,
                "collected_parameters": dict,
                "missing_parameters": list,
                "calculation": dict (있는 경우)
            }
        }
    """
    result = asyncio.run(run_workflow(
        user_message=content,
        session_id=session_id,
        previous_collected_parameters=previous_collected_parameters or {}
    ))

    return {
        "content": result.get("response", ""),
        "metadata": {
            "intent": result.get("intent", ""),
            "collected_parameters": result.get("collected_parameters", {}),
            "missing_parameters": result.get("missing_parameters", []),
            "calculation": result.get("metadata", {}).get("calculation"),
        },
    }
```

#### 파일: `ai/pipelines/langgraph_workflow.py`

**run_workflow 수정**:
```python
async def run_workflow(
    user_message: str,
    session_id: str = "default",
    previous_collected_parameters: Optional[dict] = None
) -> WorkflowState:
    """
    Workflow 실행 (비동기)

    Args:
        user_message: 사용자 입력
        session_id: 세션 ID
        previous_collected_parameters: 이전까지 수집된 파라미터 (누적)

    Returns:
        WorkflowState: 최종 상태
    """
    graph = create_workflow()

    # 초기 상태 (이전 파라미터 포함)
    initial_state: WorkflowState = {
        "session_id": session_id,
        "user_message": user_message,
        "messages": [],
        "collected_parameters": previous_collected_parameters or {},  # 누적
        "missing_parameters": [],
        "metadata": {},
    }

    final_state = await graph.ainvoke(initial_state)
    return final_state
```

### 6.2 Backend Service 변경

#### 파일: `backend/chalicelib/services/message_service.py`

**create_message_and_get_response 수정**:
```python
def create_message_and_get_response(
    self, session_id: str, client_id_hash: str, content: str
) -> AssistantMessageResponse:
    with get_db_session() as db:
        # 세션 권한 검증
        session_repo = SessionRepository(db)
        session = session_repo.find_by_id(session_id, client_id_hash)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        message_repo = MessageRepository(db)

        # 1. 이전 메시지 조회 (최근 10개)
        previous_messages, _ = message_repo.find_all_by_session(
            session_id, limit=10, cursor=None
        )

        # 2. 마지막 assistant 메시지에서 collected_parameters 추출
        previous_collected = {}
        for msg in reversed(previous_messages):
            if msg.role == "assistant" and msg.msg_metadata:
                previous_collected = msg.msg_metadata.get("collected_parameters", {})
                if previous_collected:
                    break

        # 3. 사용자 메시지 저장
        user_message = message_repo.create(
            session_id=session_id,
            role="user",
            content=content,
            metadata=None
        )

        # 4. AI 응답 생성 (이전 파라미터 전달)
        ai_response = generate_assistant_message(
            content=content,
            session_id=session_id,
            previous_collected_parameters=previous_collected
        )

        # 5. AI 응답 메시지 저장
        assistant_message_db = message_repo.create(
            session_id=session_id,
            role="assistant",
            content=ai_response["content"],
            metadata=ai_response.get("metadata")
        )

        assistant_message = MessageResponse(
            id=assistant_message_db.id,
            role=assistant_message_db.role,
            content=assistant_message_db.content,
            metadata=assistant_message_db.msg_metadata,
            createdAt=assistant_message_db.created_at,
        )

        return AssistantMessageResponse(assistantMessage=assistant_message)
```

---

## 7. 구현 파일 체크리스트

### 7.1 신규 생성 파일

#### `ai/prompts/clarifying.py`
```python
"""Clarifying 단계 프롬프트 및 질문 템플릿"""

# 파라미터 추출 프롬프트
PARAMETER_EXTRACTION_PROMPT = """..."""

# 질문 템플릿 (9개)
CLARIFYING_QUESTIONS = {
    "gift_date": """...""",
    "donor_relationship": """...""",
    # ... (전체 9개)
}

# 답변 합성 프롬프트
SYNTHESIS_PROMPT = """..."""
```

#### `ai/utils/parameter_extraction.py`
```python
"""파라미터 추출 및 질문 생성 유틸리티"""

from typing import Optional, Dict, List
from datetime import date, timedelta
import json
from ai.clients.gemini import GeminiClient
from ai.config import GeminiSettings
from ai.prompts.clarifying import PARAMETER_EXTRACTION_PROMPT, CLARIFYING_QUESTIONS

async def extract_parameters(user_message: str) -> dict:
    """Gemini API로 파라미터 추출"""
    # [구현 내용은 위 2.3 참조]
    pass

def check_missing_parameters(collected_parameters: dict) -> list:
    """누락 변수 체크"""
    required = ["gift_date", "donor_relationship", "gift_property_value"]
    missing = [p for p in required if p not in collected_parameters or collected_parameters[p] is None]
    return missing

def get_next_question(collected_parameters: dict, missing_parameters: list) -> Optional[str]:
    """다음 질문할 변수 선택"""
    # [구현 내용은 위 3.2 참조]
    pass

def generate_clarifying_question(collected_parameters: dict, missing_parameters: list) -> Optional[str]:
    """질문 생성"""
    # [구현 내용은 위 3.3 참조]
    pass
```

### 7.2 수정 파일

#### `ai/pipelines/langgraph_workflow.py`

**추가할 노드**:
1. `clarifying_node()` - 위 5.2 참조
2. `calculation_node()` - 위 5.3 참조
3. `synthesis_node()` - 위 5.4 참조

**수정할 함수**:
1. `create_workflow()` - 노드 추가 및 분기 로직
2. `run_workflow()` - previous_collected_parameters 파라미터 추가
3. `should_use_tool()` 제거 → `should_calculate()` 추가

**새로운 Workflow 구조**:
```python
def create_workflow() -> StateGraph:
    workflow = StateGraph(WorkflowState)

    # 노드 추가
    workflow.add_node("intent", intent_node)
    workflow.add_node("clarifying", clarifying_node)  # 신규
    workflow.add_node("calculation", calculation_node)  # 신규
    workflow.add_node("synthesis", synthesis_node)  # 신규
    workflow.add_node("response", response_node)

    # 엣지 연결
    workflow.add_edge(START, "intent")

    # intent → clarifying (gift_tax만)
    workflow.add_conditional_edges(
        "intent",
        lambda state: "clarifying" if state["intent"] == "gift_tax" else "response",
        {
            "clarifying": "clarifying",
            "response": "response"
        }
    )

    # clarifying → calculation or response
    workflow.add_conditional_edges(
        "clarifying",
        should_calculate,
        {
            "calculation": "calculation",
            "response": "response"
        }
    )

    # calculation → synthesis
    workflow.add_edge("calculation", "synthesis")

    # synthesis → END
    workflow.add_edge("synthesis", END)
    workflow.add_edge("response", END)

    return workflow.compile()
```

#### `ai/service.py`
- `generate_assistant_message()` 수정 (위 6.1 참조)

#### `backend/chalicelib/services/message_service.py`
- `create_message_and_get_response()` 수정 (위 6.2 참조)

### 7.3 테스트 파일

#### `ai/tests/test_clarifying_workflow.py` (신규)
```python
"""Clarifying Workflow E2E 테스트"""

import pytest
from ai.pipelines.langgraph_workflow import run_workflow

class TestClarifyingWorkflow:
    """Phase 3 Clarifying 노드 테스트"""

    @pytest.mark.asyncio
    async def test_scenario_1_full_conversation(self):
        """
        시나리오 1: 4턴 대화
        Turn 1: "부모님께 1억 받았어요" → 증여일 질문
        Turn 2: "2025년 10월 15일이요" → 계산 실행
        Turn 3: 계산 결과 반환
        """
        # Turn 1
        result1 = await run_workflow(
            user_message="부모님께 1억 받았어요",
            session_id="test-scenario-1"
        )

        assert result1["intent"] == "gift_tax"
        assert "증여일" in result1["response"]
        assert result1["collected_parameters"]["donor_relationship"] == "직계존속"
        assert result1["collected_parameters"]["gift_property_value"] == 100000000
        assert "gift_date" in result1["missing_parameters"]

        # Turn 2: 이전 파라미터 전달
        result2 = await run_workflow(
            user_message="2025년 10월 15일이요",
            session_id="test-scenario-1",
            previous_collected_parameters=result1["collected_parameters"]
        )

        assert result2["collected_parameters"]["gift_date"] == "2025-10-15"
        assert len(result2["missing_parameters"]) == 0

        # 계산 결과 확인
        assert "metadata" in result2
        assert "calculation" in result2["metadata"]
        assert result2["metadata"]["calculation"]["final_tax"] == 5000000

        # 자연어 답변 확인
        assert "500만원" in result2["response"] or "5,000,000원" in result2["response"]

    @pytest.mark.asyncio
    async def test_scenario_2_immediate_calculation(self):
        """
        시나리오 2: 1턴 즉시 계산
        "배우자에게 5억원을 2025년 10월 15일에 증여했어요"
        """
        result = await run_workflow(
            user_message="배우자에게 5억원을 2025년 10월 15일에 증여했어요",
            session_id="test-scenario-2"
        )

        # 모든 변수 수집 확인
        assert result["collected_parameters"]["donor_relationship"] == "배우자"
        assert result["collected_parameters"]["gift_property_value"] == 500000000
        assert result["collected_parameters"]["gift_date"] == "2025-10-15"
        assert len(result["missing_parameters"]) == 0

        # 계산 결과 확인 (배우자 6억 공제 → 세금 0원)
        assert result["metadata"]["calculation"]["final_tax"] == 0
        assert "0원" in result["response"]
```

#### `ai/tests/test_langgraph_workflow.py` (수정)
- 기존 `test_case2_gift_tax_intent` 수정 (Clarifying 노드 통과 확인)
- Tool 노드 테스트 수정 (하드코딩 제거)

---

## 8. 테스트 계획

### 8.1 단위 테스트

#### 파라미터 파싱 테스트 (10개)
1. "1억" → 100000000
2. "부모님" → "직계존속"
3. "오늘" → date.today()
4. "배우자에게 5억" → {donor_relationship, gift_property_value}
5. "조부모가 손자에게" → is_generation_skipping=true
6. "미성년자" → is_minor_recipient=true
7. "혼인 관련 1억" → marriage_deduction_amount=100000000
8. "대출 2억" → secured_debt=200000000
9. 파싱 실패 시 기본값 반환
10. null 값 처리

#### 질문 생성 테스트 (5개)
1. Tier 1 누락 → gift_date 질문
2. Tier 1 완료 → 계산 진행
3. 직계존속 관계 → 혼인공제 질문
4. 배우자 관계 → 혼인공제 질문 안함
5. 모든 변수 수집 → None 반환

### 8.2 E2E 테스트

#### 시나리오 1: 4턴 대화 (상세)

**Turn 1**:
- 입력: "부모님께 1억 받았어요"
- 파싱: donor_relationship="직계존속", gift_property_value=100000000
- 누락: gift_date
- 응답: "증여일이 언제인가요?..."

**Turn 2**:
- 입력: "2025년 10월 15일이요"
- 파싱: gift_date="2025-10-15"
- 누적: {donor_relationship, gift_property_value, gift_date}
- 누락: 없음 (Tier 2는 기본값 사용)
- 동작: 계산 Tool 호출
- 응답: "부모님께서 자녀에게 1억원을 증여하신 경우, 최종 납부 세액은 **500만원**입니다..."

**검증**:
- [ ] collected_parameters 누적됨
- [ ] final_tax = 5,000,000
- [ ] 응답에 계산 과정 포함
- [ ] 준법 고지 포함

#### 시나리오 2: 1턴 즉시 계산

**Turn 1**:
- 입력: "배우자에게 5억원을 2025년 10월 15일에 증여했고, 과거 증여는 없어요"
- 파싱: 모든 필수 변수
- 누락: 없음
- 동작: 즉시 계산
- 응답: "배우자 간 증여는 6억원까지 공제되므로, 최종 납부 세액은 **0원**입니다."

**검증**:
- [ ] 1턴 만에 계산 완료
- [ ] final_tax = 0

### 8.3 통합 테스트

#### Backend 연동 테스트
1. 세션 생성
2. 메시지 1 전송 → 질문 응답
3. 메시지 2 전송 (이전 파라미터 누적 확인)
4. 계산 결과 응답
5. DB에 metadata 저장 확인

---

## 9. 구현 우선순위

### Phase 1: 기본 파싱 및 질문 생성 (2시간)
1. `ai/prompts/clarifying.py` 작성
2. `ai/utils/parameter_extraction.py` 작성
3. 단위 테스트 (파라미터 파싱, 질문 생성)

### Phase 2: Workflow 노드 구현 (2시간)
4. `clarifying_node` 구현
5. `calculation_node` 구현
6. `synthesis_node` 구현
7. Workflow 분기 로직 수정

### Phase 3: Backend 연동 (1.5시간)
8. `ai/service.py` 수정
9. `message_service.py` 수정
10. E2E 테스트 작성 및 실행

### Phase 4: 문서화 및 Issue 업데이트 (0.5시간)
11. 구현 히스토리 문서 작성
12. Issue #23 업데이트

**총 예상 시간**: 6시간

---

## 10. 완료 기준

### 기능 요구사항
- [ ] 파라미터 파싱 프롬프트 작성 완료
- [ ] 9개 변수 질문 템플릿 작성 완료
- [ ] Clarifying 노드 구현 (파싱, 누적, 질문 생성)
- [ ] Calculation 노드 구현 (Pydantic 검증, Tool 호출)
- [ ] Synthesis 노드 구현 (템플릿 + LLM 합성)
- [ ] 멀티턴 대화 상태 관리 (Backend 연동)
- [ ] Workflow 분기 로직 (계산 가능 여부)

### 테스트 요구사항
- [ ] 단위 테스트 15개 통과
- [ ] E2E 시나리오 2개 통과
- [ ] 통합 테스트 (Backend 연동) 통과

### 문서 요구사항
- [ ] 상세 기획 문서 작성 (본 문서)
- [ ] Issue #23 업데이트
- [ ] 04-clarifying-strategy.md 수정
- [ ] 구현 히스토리 문서 작성

---

## 11. 다음 단계 (Phase 4+)

Phase 3 완료 후 개선 사항:

1. **Tier 2 변수 질문 추가**
   - 현재는 기본값 사용
   - 명시적으로 물어보는 옵션

2. **정규식 기반 파싱 폴백**
   - Gemini 실패 시 정규식 사용
   - 금액, 날짜 파싱

3. **에러 처리 강화**
   - 사용자가 "모르겠어요" 응답 시
   - 3회 실패 시 RAG 안내로 전환

4. **프롬프트 최적화**
   - 파싱 정확도 향상
   - Few-shot 예시 추가

5. **RAG 통합**
   - 법령 근거 제공
   - Citation 구조 정규화

---

## 부록: 참고 문서

- [04-clarifying-strategy.md](./04-clarifying-strategy.md) - Clarifying 전략 v2.0
- [05-gift-tax-calculator-spec.md](./05-gift-tax-calculator-spec.md) - 계산 Tool 명세
- [03-message-format.md](./03-message-format.md) - Message Format Spec
- [functional-spec.md](./functional-spec.md) - LLM Functional Spec
- Issue #21 - Gift Tax Calculator Implementation
- Issue #22 - LangGraph Basic Workflow
- Issue #23 - Clarifying Node Integration (본 구현)
