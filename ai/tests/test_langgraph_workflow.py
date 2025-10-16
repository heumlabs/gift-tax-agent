"""
LangGraph Workflow E2E 테스트 (Issue #22)

Phase 2 Acceptance Criteria:
- State가 노드 간 정상 전달됨
- Intent 분류가 예상대로 동작함
- Workflow가 에러 없이 실행됨
"""

import pytest
from ai.pipelines.langgraph_workflow import run_workflow, create_workflow
from ai.schemas.workflow_state import WorkflowState


class TestLangGraphWorkflow:
    """LangGraph 기본 Workflow 테스트"""

    def test_workflow_creation(self):
        """Workflow가 정상적으로 생성되는지 확인"""
        graph = create_workflow()
        assert graph is not None

    @pytest.mark.asyncio
    async def test_case1_general_greeting(self):
        """
        Case 1: 일반 인사
        - 입력: "안녕하세요"
        - 예상: intent = "general_info", response에 Gemini 응답 포함
        """
        result = await run_workflow("안녕하세요", session_id="test-case-1")

        # State 필드 확인
        assert "intent" in result
        assert "response" in result
        assert "session_id" in result

        # Intent 검증
        assert result["intent"] == "general_info"

        # Response 검증 (Gemini API 호출 결과)
        assert result["response"] is not None
        assert len(result["response"]) > 0
        # 응답이 있어야 함 (에러 메시지거나 정상 응답)
        assert isinstance(result["response"], str)

        # 입력 메시지 보존 확인
        assert result["user_message"] == "안녕하세요"

        # Session ID 확인
        assert result["session_id"] == "test-case-1"

    @pytest.mark.asyncio
    async def test_case2_gift_tax_intent(self):
        """
        Case 2: 증여세 언급
        - 입력: "증여세 계산 도와주세요"
        - 예상: intent = "gift_tax", response = "증여세 계산을 도와드리겠습니다."
        """
        result = await run_workflow("증여세 계산 도와주세요", session_id="test-case-2")

        # Intent 검증
        assert result["intent"] == "gift_tax"

        # Response 검증
        assert result["response"] == "증여세 계산을 도와드리겠습니다."

        # State 전달 확인
        assert result["user_message"] == "증여세 계산 도와주세요"
        assert result["session_id"] == "test-case-2"

    @pytest.mark.asyncio
    async def test_case3_inheritance_tax_intent(self):
        """
        Case 3: 상속세 언급
        - 입력: "상속세가 궁금해요"
        - 예상: intent = "inheritance_tax", response = "상속세 관련 안내를 드리겠습니다."
        """
        result = await run_workflow("상속세가 궁금해요", session_id="test-case-3")

        # Intent 검증
        assert result["intent"] == "inheritance_tax"

        # Response 검증
        assert result["response"] == "상속세 관련 안내를 드리겠습니다."

        # State 전달 확인
        assert result["user_message"] == "상속세가 궁금해요"
        assert result["session_id"] == "test-case-3"

    @pytest.mark.asyncio
    async def test_state_fields_initialization(self):
        """State 필드들이 올바르게 초기화되는지 확인"""
        result = await run_workflow("테스트 메시지")

        # 8개 필수 필드 확인
        assert "session_id" in result
        assert "messages" in result
        assert "user_message" in result
        assert "intent" in result
        assert "collected_parameters" in result
        assert "missing_parameters" in result
        assert "response" in result
        assert "metadata" in result

        # 초기값 검증
        assert isinstance(result["messages"], list)
        assert isinstance(result["collected_parameters"], dict)
        assert isinstance(result["missing_parameters"], list)
        assert isinstance(result["metadata"], dict)

    @pytest.mark.asyncio
    async def test_intent_keyword_detection(self):
        """Intent 키워드 감지가 정확한지 확인"""
        # "증여" 키워드
        result1 = await run_workflow("부모님께 증여받았습니다")
        assert result1["intent"] == "gift_tax"

        # "상속" 키워드
        result2 = await run_workflow("아버지 상속 재산")
        assert result2["intent"] == "inheritance_tax"

        # 키워드 없음
        result3 = await run_workflow("세금이 얼마나 나올까요?")
        assert result3["intent"] == "general_info"

    @pytest.mark.asyncio
    async def test_workflow_error_handling(self):
        """빈 메시지나 비정상 입력에 대한 처리"""
        # 빈 문자열
        result = await run_workflow("")
        assert "intent" in result
        assert "response" in result

        # intent는 out_of_scope여야 함 (키워드 없음)
        assert result["intent"] == "out_of_scope"

    @pytest.mark.asyncio
    async def test_out_of_scope_weather(self):
        """
        Out-of-scope Case 1: 날씨 질문
        - 입력: "오늘 날씨 어때?"
        - 예상: intent = "out_of_scope", 거절 메시지
        """
        result = await run_workflow("오늘 날씨 어때?")

        # Intent 검증
        assert result["intent"] == "out_of_scope"

        # 거절 메시지 검증
        assert "증여세와 상속세" in result["response"]
        assert "상담만 도와드릴 수 있습니다" in result["response"]

    @pytest.mark.asyncio
    async def test_out_of_scope_cooking(self):
        """
        Out-of-scope Case 2: 요리 질문
        - 입력: "피자 만드는 법 알려줘"
        - 예상: intent = "out_of_scope", 거절 메시지
        """
        result = await run_workflow("피자 만드는 법 알려줘")

        # Intent 검증
        assert result["intent"] == "out_of_scope"

        # 거절 메시지 검증
        assert result["response"] == "죄송합니다. 저는 증여세와 상속세 관련 상담만 도와드릴 수 있습니다. 증여세나 상속세 관련 질문이 있으시면 말씀해 주세요."

    @pytest.mark.asyncio
    async def test_general_info_tax_related(self):
        """
        일반 세무 질문은 general_info로 분류
        - 입력: "세금 신고 기한이 언제야?"
        - 예상: intent = "general_info", Gemini API 호출
        """
        result = await run_workflow("세금 신고 기한이 언제야?")

        # Intent 검증
        assert result["intent"] == "general_info"

        # Response는 Gemini API 호출 결과여야 함
        assert result["response"] is not None
        assert len(result["response"]) > 0
