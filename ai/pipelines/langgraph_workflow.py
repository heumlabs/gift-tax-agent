"""
LangGraph 기본 Workflow (Phase 2)

Issue #22에서 정의한 3-노드 Workflow를 구현합니다.
- Intent 분석 노드: Gemini API 기반 정교한 의도 분류
- Tool 노드: 증여세 계산 Tool 실행 (하드코딩 파라미터)
- Response 생성 노드: Intent별 응답 생성 (general_info는 Gemini API 호출)
- Phase 3에서 Clarifying 노드와 파라미터 수집 로직 추가 예정
"""

from langgraph.graph import StateGraph, START, END
from ai.schemas.workflow_state import WorkflowState
from ai.clients.gemini import GeminiClient
from ai.config import GeminiSettings
from ai.prompts import DEFAULT_SYSTEM_PROMPT, INTENT_CLASSIFICATION_PROMPT
import asyncio


async def intent_node(state: WorkflowState) -> dict:
    """
    Intent 분석 노드

    Gemini API를 사용하여 사용자 질문의 의도를 정확히 분류합니다.
    4가지 의도: gift_tax, inheritance_tax, general_info, out_of_scope

    Args:
        state: 현재 workflow 상태

    Returns:
        업데이트할 상태 (intent 필드)
    """
    user_message = state.get("user_message", "")

    try:
        # Gemini API를 통한 Intent 분류
        settings = GeminiSettings.from_env()
        client = GeminiClient(settings)

        # Intent 분류 전용 프롬프트 사용
        intent_raw = await client.generate_content(
            system_prompt=INTENT_CLASSIFICATION_PROMPT,
            user_message=user_message
        )

        # 응답에서 공백/개행 제거 후 소문자로 정규화
        intent = intent_raw.strip().lower()

        # 유효한 intent인지 검증
        valid_intents = ["gift_tax", "inheritance_tax", "general_info", "out_of_scope"]
        if intent not in valid_intents:
            # Gemini가 잘못된 응답을 한 경우 기본값으로 general_info 사용
            intent = "general_info"

    except Exception as e:
        # API 오류 시 안전하게 general_info로 fallback
        print(f"Intent classification error: {e}")
        intent = "general_info"

    return {"intent": intent}


async def response_node(state: WorkflowState) -> dict:
    """
    Response 생성 노드

    Phase 2에서는 Intent별로 하드코딩된 응답을 반환합니다.
    Phase 3에서 Clarifying 노드 연동 및 계산 Tool 호출 로직 추가 예정입니다.

    Args:
        state: 현재 workflow 상태

    Returns:
        업데이트할 상태 (response 필드)
    """
    intent = state.get("intent", "general_info")
    user_message = state.get("user_message", "")

    # Intent별 응답 생성
    if intent == "gift_tax":
        response = "증여세 계산을 도와드리겠습니다."
    elif intent == "inheritance_tax":
        response = "상속세 관련 안내를 드리겠습니다."
    elif intent == "out_of_scope":
        # 도메인 외 질문 거절
        response = "죄송합니다. 저는 증여세와 상속세 관련 상담만 도와드릴 수 있습니다. 증여세나 상속세 관련 질문이 있으시면 말씀해 주세요."
    else:
        # general_info의 경우 Gemini API 호출
        try:
            settings = GeminiSettings.from_env()
            client = GeminiClient(settings)
            response = await client.generate_content(
                system_prompt=DEFAULT_SYSTEM_PROMPT,
                user_message=user_message
            )
        except Exception as e:
            response = f"죄송합니다. 일시적인 오류가 발생했습니다: {str(e)}"

    return {"response": response}


async def tool_node(state: WorkflowState) -> dict:
    """
    Tool 실행 노드

    Phase 2에서는 간단한 하드코딩 파라미터로 실제 Tool 호출 테스트
    Phase 3에서 Clarifying 노드와 연동하여 실제 파라미터 수집

    Args:
        state: 현재 workflow 상태

    Returns:
        업데이트할 상태 (response 필드)
    """
    from ai.tools import calculate_gift_tax_simple
    from datetime import date

    intent = state.get("intent")

    if intent == "gift_tax":
        # 간단한 테스트용 하드코딩 입력 (Phase 3에서 Clarifying으로 대체)
        try:
            # 실제 증여세 계산 Tool 호출
            result = calculate_gift_tax_simple(
                gift_date=date(2025, 10, 16),
                donor_relationship="직계존속",
                gift_property_value=100_000_000,
                is_generation_skipping=False,
                is_minor_recipient=False,
                is_non_resident=False,
            )

            response = f"증여세 계산 결과: {result['final_tax']:,}원 (테스트용 하드코딩 파라미터)"
        except Exception as e:
            response = f"증여세 계산 중 오류 발생: {str(e)}"
    else:
        # 다른 intent는 기존 response 유지
        response = state.get("response", "")

    return {"response": response}


def should_use_tool(state: WorkflowState) -> str:
    """
    Tool 노드 사용 여부 판단

    Args:
        state: 현재 workflow 상태

    Returns:
        다음 노드 이름 ("tool" 또는 "response")
    """
    intent = state.get("intent", "general_info")

    # gift_tax는 Tool 노드로, 나머지는 Response 노드로
    if intent == "gift_tax":
        return "tool"
    else:
        return "response"


def create_workflow() -> StateGraph:
    """
    LangGraph Workflow 생성

    Phase 2 흐름 (Tool 노드 추가):
    START → intent_node → should_use_tool?
                            ├─ tool → tool_node → END
                            └─ response → response_node → END

    Phase 3에서 추가 예정:
    - Clarifying 노드 추가
    - missing_parameters 여부에 따른 분기

    Returns:
        컴파일된 StateGraph
    """
    # StateGraph 생성
    workflow = StateGraph(WorkflowState)

    # 노드 추가
    workflow.add_node("intent", intent_node)
    workflow.add_node("tool", tool_node)
    workflow.add_node("response", response_node)

    # 엣지 연결
    workflow.add_edge(START, "intent")

    # 조건부 분기: intent에 따라 tool 또는 response로
    workflow.add_conditional_edges(
        "intent",
        should_use_tool,
        {
            "tool": "tool",
            "response": "response",
        }
    )

    # 최종 노드에서 END로
    workflow.add_edge("tool", END)
    workflow.add_edge("response", END)

    # 컴파일
    return workflow.compile()


async def run_workflow(user_message: str, session_id: str = "default") -> WorkflowState:
    """
    Workflow 실행 헬퍼 함수 (비동기)

    Args:
        user_message: 사용자 입력 메시지
        session_id: 세션 ID (기본값: "default")

    Returns:
        최종 WorkflowState
    """
    graph = create_workflow()

    # 초기 상태
    initial_state: WorkflowState = {
        "session_id": session_id,
        "user_message": user_message,
        "messages": [],
        "collected_parameters": {},
        "missing_parameters": [],
        "metadata": {},
    }

    # Workflow 실행 (비동기)
    final_state = await graph.ainvoke(initial_state)

    return final_state
