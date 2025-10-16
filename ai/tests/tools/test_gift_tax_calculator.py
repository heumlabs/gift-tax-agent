"""증여세 계산기 테스트 (5개 케이스)."""

from datetime import date

import pytest
from pydantic import ValidationError

from ai.tools.gift_tax.calculator import calculate_gift_tax_simple
from ai.tools.gift_tax.models import GiftTaxSimpleInput


class TestGiftTaxCalculator:
    """국세청 증여세 간편계산기 테스트."""

    def test_case1_basic_parent_to_adult_child_100m(self):
        """Case 1: 부모→성인 자녀, 현금 1억."""
        # Given
        input_data = GiftTaxSimpleInput(
            gift_date=date(2025, 10, 15),
            donor_relationship="직계비속",  # 부모→자녀 = 직계비속
            gift_property_value=100_000_000,
            is_generation_skipping=False,
            is_minor_recipient=False,
            is_non_resident=False,
        )

        # When
        result = calculate_gift_tax_simple(**input_data.model_dump())

        # Then
        assert result["gift_value"] == 100_000_000
        assert result["total_deduction"] == 50_000_000
        assert result["taxable_base"] == 50_000_000
        assert result["calculated_tax"] == 5_000_000
        assert result["surtax"] == 0
        assert result["final_tax"] == 5_000_000
        assert len(result["steps"]) == 5  # 할증 없을 때는 step 5 생략
        assert len(result["warnings"]) >= 2  # 신고 기한 + 가산세

    def test_case2_spouse_500m_no_tax(self):
        """Case 2: 배우자 증여 5억 (세금 0원)."""
        # Given
        input_data = GiftTaxSimpleInput(
            gift_date=date(2025, 10, 15),
            donor_relationship="배우자",
            gift_property_value=500_000_000,
        )

        # When
        result = calculate_gift_tax_simple(**input_data.model_dump())

        # Then
        assert result["gift_value"] == 500_000_000
        assert result["total_deduction"] == 600_000_000
        assert result["taxable_base"] == 0
        assert result["calculated_tax"] == 0
        assert result["surtax"] == 0
        assert result["final_tax"] == 0
        assert "과세표준이 0 이하" in result["warnings"][0]

    def test_case3_generation_skipping_200m(self):
        """Case 3: 세대생략 증여 (조부모→손자 2억, 미성년자)."""
        # Given
        input_data = GiftTaxSimpleInput(
            gift_date=date(2025, 10, 15),
            donor_relationship="직계비속",  # 조부모→손자 = 직계비속
            gift_property_value=200_000_000,
            is_generation_skipping=True,
            is_minor_recipient=True,
        )

        # When
        result = calculate_gift_tax_simple(**input_data.model_dump())

        # Then
        assert result["gift_value"] == 200_000_000
        assert result["total_deduction"] == 20_000_000  # 미성년자 특례
        assert result["taxable_base"] == 180_000_000
        assert result["calculated_tax"] == 26_000_000
        assert result["surtax"] == 7_800_000  # 30% 할증
        assert result["final_tax"] == 33_800_000
        assert any("30% 할증" in step["detail"] for step in result["steps"] if step["step"] == 5)
        assert any("30% 할증" in w for w in result["warnings"])

    def test_case4_secured_debt_500m_property_200m_debt(self):
        """Case 4: 부담부 증여 (부동산 5억, 대출 2억)."""
        # Given
        input_data = GiftTaxSimpleInput(
            gift_date=date(2025, 10, 15),
            donor_relationship="직계비속",  # 부모→자녀 = 직계비속
            gift_property_value=500_000_000,
            secured_debt=200_000_000,
        )

        # When
        result = calculate_gift_tax_simple(**input_data.model_dump())

        # Then
        assert result["gift_value"] == 300_000_000  # 5억 - 2억
        assert result["total_deduction"] == 50_000_000
        assert result["taxable_base"] == 250_000_000
        assert result["calculated_tax"] == 40_000_000  # 2.5억 * 20% - 1천만 = 4천만
        assert result["surtax"] == 0
        assert result["final_tax"] == 40_000_000

    def test_case5_non_resident_300m(self):
        """Case 5: 비거주자 (부모→자녀 3억, 공제 0원)."""
        # Given
        input_data = GiftTaxSimpleInput(
            gift_date=date(2025, 10, 15),
            donor_relationship="직계비속",  # 부모→자녀 = 직계비속
            gift_property_value=300_000_000,
            is_non_resident=True,  # 비거주자
        )

        # When
        result = calculate_gift_tax_simple(**input_data.model_dump())

        # Then
        assert result["gift_value"] == 300_000_000
        assert result["total_deduction"] == 0  # 비거주자는 공제 0원
        assert result["taxable_base"] == 300_000_000
        assert result["calculated_tax"] == 50_000_000  # 3억 * 20% - 1천만 = 5천만
        assert result["surtax"] == 0
        assert result["final_tax"] == 50_000_000

    def test_case6_other_relative_100m(self):
        """Case 6: 기타친족 (1억, 공제 1천만원)."""
        # Given
        input_data = GiftTaxSimpleInput(
            gift_date=date(2025, 10, 15),
            donor_relationship="기타친족",
            gift_property_value=100_000_000,
        )

        # When
        result = calculate_gift_tax_simple(**input_data.model_dump())

        # Then
        assert result["gift_value"] == 100_000_000
        assert result["total_deduction"] == 10_000_000  # 기타친족 공제 1천만원
        assert result["taxable_base"] == 90_000_000
        assert result["calculated_tax"] == 9_000_000  # 9천만 * 10% = 900만
        assert result["surtax"] == 0
        assert result["final_tax"] == 9_000_000


class TestGiftTaxInputValidation:
    """입력 데이터 검증 테스트."""

    def test_secured_debt_exceeds_property_value_raises_error(self):
        """채무액이 재산가액을 초과하면 에러."""
        with pytest.raises(ValidationError, match="채무액이 증여재산가액보다 클 수 없습니다"):
            GiftTaxSimpleInput(
                gift_date=date(2025, 10, 15),
                donor_relationship="직계비속",
                gift_property_value=100_000_000,
                secured_debt=150_000_000,  # 재산가액보다 큼
            )

    def test_future_gift_date_raises_error(self):
        """미래 증여일은 에러."""
        with pytest.raises(ValidationError, match="증여일은 미래 날짜일 수 없습니다"):
            GiftTaxSimpleInput(
                gift_date=date(2099, 12, 31),
                donor_relationship="배우자",
                gift_property_value=100_000_000,
            )

    def test_negative_gift_value_raises_error(self):
        """증여재산가액은 양수여야 함."""
        with pytest.raises(ValidationError):
            GiftTaxSimpleInput(
                gift_date=date(2025, 10, 15),
                donor_relationship="직계비속",
                gift_property_value=-100_000_000,
            )

    def test_marriage_deduction_exceeds_limit(self):
        """혼인공제액이 1억 초과 시 에러."""
        with pytest.raises(ValidationError):
            GiftTaxSimpleInput(
                gift_date=date(2025, 10, 15),
                donor_relationship="직계비속",
                gift_property_value=500_000_000,
                marriage_deduction_amount=150_000_000,  # 1억 초과
            )
