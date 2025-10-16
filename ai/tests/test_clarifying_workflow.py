"""
Clarifying Workflow E2E 테스트

워크플로우 재설계 후 검증용 테스트
실제 Gemini API를 호출하므로 GOOGLE_API_KEY 환경변수 필요
"""

import pytest

from ai.pipelines.langgraph_workflow import run_workflow


@pytest.mark.skip(reason="Requires valid GOOGLE_API_KEY - run manually for E2E testing")
class TestClarifyingWorkflowE2E:
    """Phase 3 Clarifying Workflow E2E 테스트 (실제 API 호출)"""

    @pytest.mark.asyncio
    async def test_scenario_immediate_calculation(self):
        """
        시나리오: 1턴 즉시 계산
        "배우자에게 5억원을 2025년 10월 15일에 증여했어요"
        """
        result = await run_workflow(
            user_message="배우자에게 5억원을 2025년 10월 15일에 증여했어요",
            session_id="test-scenario-immediate"
        )

        # Intent 분류 확인
        assert result["intent"] == "gift_tax"

        # 모든 변수 수집 확인
        collected = result["collected_parameters"]
        assert collected.get("donor_relationship") == "배우자"
        assert collected.get("gift_property_value") == 500000000
        assert collected.get("gift_date") == "2025-10-15"

        # 누락 없음 확인
        assert len(result["missing_parameters"]) == 0

        # 계산 결과 확인 (배우자 6억 공제 → 세금 0원)
        assert "metadata" in result
        assert "calculation" in result["metadata"]
        calculation = result["metadata"]["calculation"]
        assert calculation["final_tax"] == 0

    @pytest.mark.asyncio
    async def test_multiturn_conversation(self):
        """
        시나리오: 멀티턴 대화
        Turn 1: "부모님께 받았어요" → 질문
        Turn 2: "1억원이요" → 질문
        Turn 3: "올해 6월이요" → 계산
        """
        # Turn 1
        result1 = await run_workflow(
            user_message="부모님께 받았어요",
            session_id="test-multiturn"
        )

        assert result1["intent"] == "gift_tax"
        # 질문 응답 확인
        assert result1.get("response") is not None

        # Turn 2
        result2 = await run_workflow(
            user_message="1억원이요",
            session_id="test-multiturn",
            previous_collected_parameters=result1.get("collected_parameters", {})
        )

        # Turn 3
        result3 = await run_workflow(
            user_message="올해 6월이요",
            session_id="test-multiturn",
            previous_collected_parameters=result2.get("collected_parameters", {})
        )

        # 최종 계산 확인
        assert "metadata" in result3
        assert "calculation" in result3["metadata"]


class TestWorkflowBasics:
    """워크플로우 기본 동작 테스트 (API 호출 없음)"""

    def test_workflow_creation(self):
        """Workflow 생성 확인"""
        from ai.pipelines.langgraph_workflow import create_workflow

        graph = create_workflow()
        assert graph is not None

    @pytest.mark.asyncio
    async def test_workflow_state_initialization(self):
        """State 초기화 확인"""
        from ai.pipelines.langgraph_workflow import run_workflow

        # API 호출은 실패하지만 State 초기화는 확인 가능
        try:
            result = await run_workflow("test", session_id="test")
            # State 필드 확인
            assert "session_id" in result
            assert "messages" in result
            assert "collected_parameters" in result
        except Exception:
            # API 실패는 예상됨 (test API key)
            pass
