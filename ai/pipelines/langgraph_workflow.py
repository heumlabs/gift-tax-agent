"""
LangGraph 기본 Workflow (Phase 2)

Issue #22에서 정의한 단순한 3-노드 Workflow를 구현합니다.
- Intent 분석 노드: 키워드 기반 의도 분류
- Response 생성 노드: Intent별 하드코딩 응답
- Phase 3에서 Clarifying 노드와 조건부 분기 추가 예정
"""

from langgraph.graph import StateGraph, START, END
from ai.schemas.workflow_state import WorkflowState
from ai.clients.gemini import GeminiClient
from ai.config import GeminiSettings
from ai.prompts import DEFAULT_SYSTEM_PROMPT


def intent_node(state: WorkflowState) -> dict:
    """
    Intent 분석 노드

    Phase 2에서는 단순 키워드 기반으로 의도를 분류합니다.
    Phase 3에서 LLM 기반 정교한 Intent 분류로 대체 예정입니다.

    Args:
        state: 현재 workflow 상태

    Returns:
        업데이트할 상태 (intent 필드)
    """
    user_message = state.get("user_message", "").lower()

    # 키워드 기반 분류
    # 1순위: 증여세/상속세 명확한 키워드
    if "증여" in user_message:
        intent = "gift_tax"
    elif "상속" in user_message:
        intent = "inheritance_tax"
    # 2순위: 일반 세무 관련 키워드 또는 인사말
    elif any(keyword in user_message for keyword in ["세금", "세액", "공제", "신고", "재산", "과세", "면제", "안녕", "도와", "궁금"]):
        intent = "general_info"
    # 3순위: 도메인 외 질문 거절
    else:
        intent = "out_of_scope"

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


def create_workflow() -> StateGraph:
    """
    LangGraph Workflow 생성

    단순한 선형 흐름:
    START → intent_node → response_node → END

    Phase 3에서 조건부 분기 추가 예정:
    - Clarifying 노드 추가
    - missing_parameters 여부에 따른 분기
    - 계산 Tool 호출

    Returns:
        컴파일된 StateGraph
    """
    # StateGraph 생성
    workflow = StateGraph(WorkflowState)

    # 노드 추가
    workflow.add_node("intent", intent_node)
    workflow.add_node("response", response_node)

    # 엣지 연결 (선형 흐름)
    workflow.add_edge(START, "intent")
    workflow.add_edge("intent", "response")
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
