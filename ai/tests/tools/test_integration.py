"""통합 테스트: Tool이 정상적으로 import 및 호출되는지 확인."""

from datetime import date

from ai.tools import GiftTaxSimpleInput, calculate_gift_tax_simple


def test_tool_can_be_imported():
    """Tool이 정상적으로 import 되는지 확인."""
    assert callable(calculate_gift_tax_simple)
    assert calculate_gift_tax_simple.__name__ == "calculate_gift_tax_simple"


def test_tool_has_metadata():
    """Tool에 LangGraph용 메타데이터가 있는지 확인."""
    assert hasattr(calculate_gift_tax_simple, "__tool_name__")
    assert hasattr(calculate_gift_tax_simple, "__tool_description__")
    assert calculate_gift_tax_simple.__tool_name__ == "calculate_gift_tax"
    assert "국세청" in calculate_gift_tax_simple.__tool_description__


def test_tool_execution_basic():
    """Tool이 기본 케이스에서 정상 실행되는지 확인."""
    result = calculate_gift_tax_simple(
        gift_date=date(2025, 10, 15),
        donor_relationship="직계존속",
        gift_property_value=100_000_000,
    )

    assert result is not None
    assert "final_tax" in result
    assert result["final_tax"] == 5_000_000
    assert len(result["steps"]) > 0
    assert len(result["warnings"]) > 0


def test_tool_with_pydantic_model():
    """Pydantic 모델과 함께 사용 가능한지 확인."""
    input_data = GiftTaxSimpleInput(
        gift_date=date(2025, 10, 15),
        donor_relationship="배우자",
        gift_property_value=500_000_000,
    )

    result = calculate_gift_tax_simple(**input_data.model_dump())

    assert result["final_tax"] == 0  # 배우자 6억 공제로 세금 없음
