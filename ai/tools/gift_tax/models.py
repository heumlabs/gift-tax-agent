"""증여세 계산 입력/출력 데이터 모델."""

from __future__ import annotations

from datetime import date
from typing import Literal, TypedDict

from pydantic import BaseModel, Field, field_validator


class GiftTaxSimpleInput(BaseModel):
    """국세청 증여세 간편계산 입력 모델 (9개 변수)."""

    # Tier 1: 기본 정보
    gift_date: date = Field(..., description="증여일자")
    donor_relationship: Literal["배우자", "직계존속", "직계비속", "기타친족"] = Field(
        ..., description="증여자와의 관계 (수증자 기준, 예: 부모→자녀=직계존속)"
    )
    gift_property_value: int = Field(..., gt=0, description="증여받은 재산가액 (원)")

    # Tier 2: 특례 판단
    is_generation_skipping: bool = Field(default=False, description="세대생략 증여 여부")
    is_minor_recipient: bool = Field(default=False, description="수증자 미성년자 여부")
    is_non_resident: bool = Field(default=False, description="수증자 비거주자 여부")

    # Tier 3: 공제 및 채무
    marriage_deduction_amount: int = Field(default=0, ge=0, le=100_000_000, description="혼인공제액 (최대 1억)")
    childbirth_deduction_amount: int = Field(default=0, ge=0, le=100_000_000, description="출산공제액 (최대 1억)")
    secured_debt: int = Field(default=0, ge=0, description="담보채무액")

    @field_validator("secured_debt")
    @classmethod
    def validate_debt(cls, v: int, info) -> int:
        """채무액이 증여재산가액을 초과할 수 없음."""
        if "gift_property_value" in info.data and v > info.data["gift_property_value"]:
            raise ValueError("채무액이 증여재산가액보다 클 수 없습니다")
        return v

    @field_validator("gift_date")
    @classmethod
    def validate_gift_date(cls, v: date) -> date:
        """증여일은 과거 또는 오늘만 허용."""
        if v > date.today():
            raise ValueError("증여일은 미래 날짜일 수 없습니다")
        return v


class CalculationStep(TypedDict):
    """계산 단계 상세."""

    step: int
    description: str
    formula: str
    value: int
    detail: str


class GiftTaxSimpleOutput(TypedDict):
    """계산 결과 출력 (LangGraph State에 병합 가능)."""

    # 기존 필드
    steps: list[CalculationStep]
    gift_value: int
    total_deduction: int
    taxable_base: int
    calculated_tax: int
    surtax: int
    final_tax: int
    warnings: list[str]

    # 새 필드 (Synthesis 개선용)
    calculation_breakdown: dict  # 상세 계산 정보 (공제 세부내역 등)
    tax_bracket_info: dict  # 세율 구간 정보
    formatted_amounts: dict  # 한글 포맷 금액들
