"""
LangGraph Workflow State 정의

Issue #22에서 정의한 8개 필드를 포함한 State 모델입니다.
노드 간 데이터 전달 및 상태 관리를 담당합니다.
"""

from typing import TypedDict, Literal


class WorkflowState(TypedDict, total=False):
    """
    LangGraph Workflow의 전역 상태

    Phase 2에서는 기본 구조만 정의하고,
    Phase 3에서 Clarifying 노드가 collected_parameters와 missing_parameters를 업데이트합니다.
    """

    # 세션 정보
    session_id: str

    # 대화 메시지 히스토리
    messages: list[dict]

    # 현재 사용자 입력
    user_message: str

    # 의도 분류 결과 (gift_tax, inheritance_tax, general_info, out_of_scope)
    intent: Literal["gift_tax", "inheritance_tax", "general_info", "out_of_scope"]

    # 수집된 변수들 (Phase 3에서 Clarifying 노드가 사용)
    collected_parameters: dict

    # 누락된 필수 변수 (Phase 3에서 Clarifying 노드가 사용)
    missing_parameters: list[str]

    # LLM 생성 응답
    response: str

    # 메타데이터 (calculation, citations 등)
    metadata: dict

    # Web search 결과 (Google Search Grounding)
    web_search_results: dict | None
