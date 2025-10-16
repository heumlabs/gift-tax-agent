"""LangChain/LangGraph Tool wrappers for AI tools.

이 모듈은 순수 Python 함수를 LangGraph에서 사용 가능한 Tool로 변환합니다.
Issue #22에서 LangGraph workflow에 통합될 예정입니다.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from pydantic import Field

from .gift_tax.calculator import calculate_gift_tax_simple as _calculate_gift_tax
from .gift_tax.models import GiftTaxSimpleOutput


def calculate_gift_tax_simple(
    gift_date: Annotated[date, Field(description="증여일자 (YYYY-MM-DD)")],
    donor_relationship: Annotated[
        str,
        Field(
            description="증여자와의 관계",
            pattern="^(배우자|직계존속|직계비속|기타친족)$",
        ),
    ],
    gift_property_value: Annotated[int, Field(description="증여받은 재산가액 (원)", gt=0)],
    is_generation_skipping: Annotated[bool, Field(description="세대생략 증여 여부")] = False,
    is_minor_recipient: Annotated[bool, Field(description="수증자 미성년자 여부")] = False,
    is_non_resident: Annotated[bool, Field(description="수증자 비거주자 여부")] = False,
    marriage_deduction_amount: Annotated[
        int, Field(description="혼인공제액 (최대 1억)", ge=0, le=100_000_000)
    ] = 0,
    childbirth_deduction_amount: Annotated[
        int, Field(description="출산공제액 (최대 1억)", ge=0, le=100_000_000)
    ] = 0,
    secured_debt: Annotated[int, Field(description="담보채무액", ge=0)] = 0,
    current_date: Annotated[date | None, Field(description="현재 날짜 (기한 경과 판단용)")] = None,
) -> GiftTaxSimpleOutput:
    """
    국세청 증여세 간편계산기 Tool (LangGraph 호환).

    이 함수는 LangGraph의 ToolNode에서 자동으로 Tool로 변환됩니다.
    Type annotations과 Field 메타데이터를 통해 자동으로 스키마가 생성됩니다.

    Args:
        gift_date: 증여일자
        donor_relationship: 증여자 관계 (수증자 기준, 배우자/직계존속/직계비속/기타친족)
                           예: 부모→자녀 증여 시 "직계존속"
        gift_property_value: 증여받은 재산가액 (원)
        is_generation_skipping: 세대생략 증여 여부
        is_minor_recipient: 수증자 미성년자 여부
        is_non_resident: 수증자 비거주자 여부
        marriage_deduction_amount: 혼인공제액 (최대 1억)
        childbirth_deduction_amount: 출산공제액 (최대 1억)
        secured_debt: 담보채무액
        current_date: 현재 날짜 (기한 경과 판단용, 기본값: None)

    Returns:
        GiftTaxSimpleOutput: 계산 결과 (6단계 + 주의사항)

    Example:
        >>> from datetime import date
        >>> result = calculate_gift_tax_simple(
        ...     gift_date=date(2025, 10, 15),
        ...     donor_relationship="직계존속",
        ...     gift_property_value=100_000_000,
        ... )
        >>> result["final_tax"]
        5000000

    LangGraph 사용 예시:
        ```python
        from langgraph.prebuilt import create_react_agent
        from langchain_google_genai import ChatGoogleGenerativeAI

        # LangGraph가 자동으로 함수를 Tool로 변환
        tools = [calculate_gift_tax_simple]

        agent = create_react_agent(
            model=ChatGoogleGenerativeAI(model="gemini-2.5-flash"),
            tools=tools,
        )

        # Agent가 필요 시 Tool 자동 호출
        result = agent.invoke({
            "messages": [("user", "부모님이 1억원 주시면 세금이 얼마인가요?")]
        })
        ```
    """
    return _calculate_gift_tax(
        gift_date=gift_date,
        donor_relationship=donor_relationship,
        gift_property_value=gift_property_value,
        is_generation_skipping=is_generation_skipping,
        is_minor_recipient=is_minor_recipient,
        is_non_resident=is_non_resident,
        marriage_deduction_amount=marriage_deduction_amount,
        childbirth_deduction_amount=childbirth_deduction_amount,
        secured_debt=secured_debt,
        current_date=current_date,
    )


# Tool metadata (LangGraph가 참조)
calculate_gift_tax_simple.__tool_name__ = "calculate_gift_tax"  # type: ignore
calculate_gift_tax_simple.__tool_description__ = (  # type: ignore
    "국세청 증여세 간편계산기 기준으로 증여세를 정확히 계산합니다. "
    "9개 필수/선택 변수를 입력받아 6단계 계산 과정과 최종 세액을 반환합니다."
)


__all__ = ["calculate_gift_tax_simple"]
