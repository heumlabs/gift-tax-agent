"""
파라미터 추출 및 질문 생성 유틸리티 단위 테스트

Issue #23 Phase 3 구현 검증용 테스트
"""

import pytest

from ai.utils.parameter_extraction import (
    check_missing_parameters,
    generate_clarifying_question,
    get_next_question,
)


class TestCheckMissingParameters:
    """check_missing_parameters() 함수 테스트"""

    def test_all_tier1_missing(self):
        """Tier 1 변수 모두 누락"""
        result = check_missing_parameters({})
        assert set(result) == {"gift_date", "donor_relationship", "gift_property_value"}

    def test_partial_tier1_missing(self):
        """Tier 1 변수 일부 누락"""
        result = check_missing_parameters(
            {
                "donor_relationship": "직계존속",
                "gift_property_value": 100000000
            }
        )
        assert result == ["gift_date"]

    def test_tier1_complete(self):
        """Tier 1 변수 모두 수집됨"""
        result = check_missing_parameters(
            {
                "gift_date": "2025-10-15",
                "donor_relationship": "직계존속",
                "gift_property_value": 100000000
            }
        )
        assert result == []

    def test_null_value_treated_as_missing(self):
        """null 값은 누락으로 간주"""
        result = check_missing_parameters(
            {
                "gift_date": None,
                "donor_relationship": "직계존속"
            }
        )
        assert "gift_date" in result
        assert "gift_property_value" in result


class TestGetNextQuestion:
    """get_next_question() 함수 테스트"""

    def test_tier1_priority(self):
        """Tier 1 변수 우선 반환"""
        result = get_next_question(
            collected_parameters={"donor_relationship": "직계존속"},
            missing_parameters=["gift_date", "gift_property_value"]
        )
        assert result == "gift_date"  # Tier 1 순서대로

    def test_tier1_complete_no_conditional(self):
        """Tier 1 완료, 조건부 질문 없음 (배우자)"""
        result = get_next_question(
            collected_parameters={
                "gift_date": "2025-10-15",
                "donor_relationship": "배우자",
                "gift_property_value": 500000000
            },
            missing_parameters=[]
        )
        assert result is None  # 계산 가능

    def test_tier1_complete_with_conditional(self):
        """Tier 1 완료, 조건부 질문 있음 (직계존속)"""
        result = get_next_question(
            collected_parameters={
                "gift_date": "2025-10-15",
                "donor_relationship": "직계존속",
                "gift_property_value": 100000000
            },
            missing_parameters=[]
        )
        assert result == "marriage_deduction_amount"  # 조건부 질문

    def test_all_complete(self):
        """모든 변수 수집 완료"""
        result = get_next_question(
            collected_parameters={
                "gift_date": "2025-10-15",
                "donor_relationship": "직계존속",
                "gift_property_value": 100000000,
                "marriage_deduction_amount": 0,
                "childbirth_deduction_amount": 0
            },
            missing_parameters=[]
        )
        assert result is None  # 계산 가능


class TestGenerateClarifyingQuestion:
    """generate_clarifying_question() 함수 테스트"""

    def test_generates_question_for_missing_tier1(self):
        """Tier 1 누락 시 질문 생성"""
        question = generate_clarifying_question(
            collected_parameters={},
            missing_parameters=["gift_date", "donor_relationship", "gift_property_value"]
        )
        assert question is not None
        assert "증여일" in question

    def test_returns_none_when_complete(self):
        """모두 수집 완료 시 None 반환"""
        question = generate_clarifying_question(
            collected_parameters={
                "gift_date": "2025-10-15",
                "donor_relationship": "배우자",
                "gift_property_value": 500000000
            },
            missing_parameters=[]
        )
        assert question is None

    def test_conditional_question_for_lineal(self):
        """직계존속/비속 시 혼인공제 질문"""
        question = generate_clarifying_question(
            collected_parameters={
                "gift_date": "2025-10-15",
                "donor_relationship": "직계비속",
                "gift_property_value": 100000000
            },
            missing_parameters=[]
        )
        assert question is not None
        assert "혼인" in question
