"""국세청 증여세 간편계산 로직 (6단계)."""

from __future__ import annotations

from datetime import date, timedelta

from .constants import (
    CHILDBIRTH_DEDUCTION_LIMIT,
    GENERATION_SKIPPING_SURTAX_RATE,
    GIFT_DEDUCTION_BASE,
    MARRIAGE_DEDUCTION_LIMIT,
    MINOR_DEDUCTION,
    TAX_BRACKETS,
)
from .models import CalculationStep, GiftTaxSimpleOutput


def calculate_gift_tax_simple(
    gift_date: date,
    donor_relationship: str,
    gift_property_value: int,
    is_generation_skipping: bool = False,
    is_minor_recipient: bool = False,
    is_non_resident: bool = False,
    marriage_deduction_amount: int = 0,
    childbirth_deduction_amount: int = 0,
    secured_debt: int = 0,
    current_date: date | None = None,
) -> GiftTaxSimpleOutput:
    """
    국세청 증여세 간편계산 로직.

    Args:
        gift_date: 증여일자
        donor_relationship: 증여자 관계 (수증자 기준, 배우자/직계존속/직계비속/기타친족)
                           예: 부모→자녀 증여 시 "직계존속" (자녀 입장에서 부모)
        gift_property_value: 증여받은 재산가액
        is_generation_skipping: 세대생략 증여 여부
        is_minor_recipient: 수증자 미성년자 여부
        is_non_resident: 수증자 비거주자 여부
        marriage_deduction_amount: 혼인공제액
        childbirth_deduction_amount: 출산공제액
        secured_debt: 담보채무액
        current_date: 현재 날짜 (기한 후 신고 가산세 계산용, 기본값: 오늘)

    Returns:
        GiftTaxSimpleOutput: 계산 결과 (6단계 + 가산세 + warnings)

    Note:
        LangGraph에서 호출 시:
        - 입력: State.collected_parameters에서 추출
        - 출력: State.metadata.calculation에 저장
    """
    steps: list[CalculationStep] = []

    # ① 증여재산가액
    gift_value = gift_property_value - secured_debt
    steps.append(
        {
            "step": 1,
            "description": "증여재산가액",
            "formula": "증여받은 재산가액 - 채무액",
            "value": gift_value,
            "detail": f"{gift_property_value:,}원 - {secured_debt:,}원",
        }
    )

    # ② 증여재산공제
    base_deduction = get_base_deduction(donor_relationship, is_minor_recipient, is_non_resident)
    marriage_deduction = min(marriage_deduction_amount, MARRIAGE_DEDUCTION_LIMIT)
    childbirth_deduction = min(childbirth_deduction_amount, CHILDBIRTH_DEDUCTION_LIMIT)
    total_deduction = base_deduction + marriage_deduction + childbirth_deduction

    steps.append(
        {
            "step": 2,
            "description": "증여재산공제",
            "formula": "기본공제 + 혼인공제 + 출산공제",
            "value": total_deduction,
            "detail": f"기본 {base_deduction:,}원 + 혼인 {marriage_deduction:,}원 + 출산 {childbirth_deduction:,}원",
        }
    )

    # ③ 과세표준
    taxable_base = gift_value - total_deduction

    steps.append(
        {
            "step": 3,
            "description": "과세표준",
            "formula": "증여재산가액 - 증여재산공제",
            "value": max(taxable_base, 0),
            "detail": f"{gift_value:,}원 - {total_deduction:,}원",
        }
    )

    if taxable_base <= 0:
        # 주의사항 (세금 0원이어도 신고기한 안내)
        warnings = generate_warnings(
            gift_date=gift_date,
            is_generation_skipping=is_generation_skipping,
            current_date=current_date or date.today(),
        )

        # 새 필드: calculation_breakdown, tax_bracket_info, formatted_amounts
        calculation_breakdown = {
            "base_deduction": base_deduction,
            "marriage_deduction": marriage_deduction,
            "childbirth_deduction": childbirth_deduction,
            "donor_relationship": donor_relationship,
            "is_minor_recipient": is_minor_recipient,
            "is_non_resident": is_non_resident,
        }

        tax_bracket_info = get_tax_bracket_info(0)

        formatted_amounts = {
            "gift_value": format_amount(gift_value),
            "total_deduction": format_amount(total_deduction),
            "taxable_base": "0원",
            "calculated_tax": "0원",
            "surtax": "0원",
            "final_tax": "0원",
        }

        return {
            "steps": steps,
            "gift_value": gift_value,
            "total_deduction": total_deduction,
            "taxable_base": 0,
            "calculated_tax": 0,
            "surtax": 0,
            "final_tax": 0,
            "warnings": warnings,
            "calculation_breakdown": calculation_breakdown,
            "tax_bracket_info": tax_bracket_info,
            "formatted_amounts": formatted_amounts,
        }

    # ④ 산출세액
    calculated_tax = apply_tax_rate(taxable_base)

    steps.append(
        {
            "step": 4,
            "description": "산출세액",
            "formula": "과세표준 × 세율 - 누진공제",
            "value": calculated_tax,
            "detail": get_tax_rate_detail(taxable_base),
        }
    )

    # ⑤ 세대생략 할증
    surtax = 0
    if is_generation_skipping:
        surtax = int(calculated_tax * GENERATION_SKIPPING_SURTAX_RATE)
        steps.append(
            {
                "step": 5,
                "description": "세대생략 할증세액 (30%)",
                "formula": "산출세액 × 30%",
                "value": surtax,
                "detail": "조부모→손자 증여로 30% 할증 적용",
            }
        )

    # ⑥ 최종 증여세액
    final_tax = calculated_tax + surtax

    steps.append(
        {
            "step": 6,
            "description": "최종 증여세액",
            "formula": "산출세액 + 할증세액",
            "value": max(final_tax, 0),
            "detail": f"{calculated_tax:,}원 + {surtax:,}원",
        }
    )

    # 주의사항
    warnings = generate_warnings(
        gift_date=gift_date,
        is_generation_skipping=is_generation_skipping,
        current_date=current_date or date.today(),
    )

    # 새 필드: calculation_breakdown, tax_bracket_info, formatted_amounts
    calculation_breakdown = {
        "base_deduction": base_deduction,
        "marriage_deduction": marriage_deduction,
        "childbirth_deduction": childbirth_deduction,
        "donor_relationship": donor_relationship,
        "is_minor_recipient": is_minor_recipient,
        "is_non_resident": is_non_resident,
        "is_generation_skipping": is_generation_skipping,
    }

    tax_bracket_info = get_tax_bracket_info(max(taxable_base, 0))

    formatted_amounts = {
        "gift_value": format_amount(gift_value),
        "total_deduction": format_amount(total_deduction),
        "taxable_base": format_amount(max(taxable_base, 0)),
        "calculated_tax": format_amount(calculated_tax),
        "surtax": format_amount(surtax),
        "final_tax": format_amount(max(final_tax, 0)),
    }

    return {
        "steps": steps,
        "gift_value": gift_value,
        "total_deduction": total_deduction,
        "taxable_base": max(taxable_base, 0),
        "calculated_tax": calculated_tax,
        "surtax": surtax,
        "final_tax": max(final_tax, 0),
        "warnings": warnings,
        "calculation_breakdown": calculation_breakdown,
        "tax_bracket_info": tax_bracket_info,
        "formatted_amounts": formatted_amounts,
    }


def format_amount(amount: int) -> str:
    """
    금액을 읽기 좋은 한글 형식으로 변환.

    Args:
        amount: 금액 (원)

    Returns:
        str: 한글 포맷 금액

    Examples:
        >>> format_amount(1_000_000_000)
        '10억원'
        >>> format_amount(950_000_000)
        '9억 5,000만원'
        >>> format_amount(50_000_000)
        '5,000만원'
        >>> format_amount(150_000_000)
        '1억 5,000만원'
        >>> format_amount(0)
        '0원'
    """
    if amount == 0:
        return "0원"

    eok = amount // 100_000_000  # 억 단위
    remainder = amount % 100_000_000
    man = remainder // 10_000  # 만 단위

    parts = []
    if eok > 0:
        parts.append(f"{eok}억")
    if man > 0:
        parts.append(f"{man:,}만원")
    elif eok > 0:
        # 정확히 억 단위일 때
        return f"{eok}억원"

    return " ".join(parts) if parts else "0원"


def get_tax_bracket_info(taxable_base: int) -> dict:
    """
    과세표준에 해당하는 세율 구간 정보 반환.

    Args:
        taxable_base: 과세표준

    Returns:
        dict: 세율 구간 정보
            - bracket: 구간 설명 (예: "10억 초과 30억 이하")
            - rate: 세율 (%)
            - progressive_deduction: 누진공제액
            - description: 상세 설명

    Examples:
        >>> info = get_tax_bracket_info(1_500_000_000)
        >>> info['bracket']
        '10억 초과 30억 이하'
        >>> info['rate']
        40
    """
    if taxable_base == 0:
        return {
            "bracket": "과세표준 0원",
            "rate": 0,
            "progressive_deduction": 0,
            "description": "과세표준 0원 (세금 없음)",
        }

    for bracket in TAX_BRACKETS:
        if taxable_base <= bracket["limit"]:
            rate_percent = int(bracket["rate"] * 100)

            # 구간 설명 생성
            if bracket["limit"] == 100_000_000:
                bracket_desc = "1억 이하"
            elif bracket["limit"] == 500_000_000:
                bracket_desc = "1억 초과 5억 이하"
            elif bracket["limit"] == 1_000_000_000:
                bracket_desc = "5억 초과 10억 이하"
            elif bracket["limit"] == 3_000_000_000:
                bracket_desc = "10억 초과 30억 이하"
            else:
                bracket_desc = "30억 초과"

            return {
                "bracket": bracket_desc,
                "rate": rate_percent,
                "progressive_deduction": bracket["progressive_deduction"],
                "description": f"{bracket_desc} 구간으로 {rate_percent}% 세율 적용",
            }

    # Fallback (마지막 구간)
    return {
        "bracket": "30억 초과",
        "rate": 50,
        "progressive_deduction": 460_000_000,
        "description": "30억 초과 구간으로 50% 세율 적용",
    }


def get_all_tax_brackets() -> list[dict]:
    """
    전체 세율표 반환 (사용자 안내용).

    Returns:
        list[dict]: 세율표 목록
            각 항목: {limit_desc, rate_percent, progressive_deduction_formatted}

    Example:
        >>> brackets = get_all_tax_brackets()
        >>> brackets[0]
        {'limit_desc': '1억 이하', 'rate_percent': '10%', 'progressive_deduction_formatted': '0원'}
    """
    bracket_descriptions = [
        ("1억 이하", 100_000_000),
        ("1억 초과 5억 이하", 500_000_000),
        ("5억 초과 10억 이하", 1_000_000_000),
        ("10억 초과 30억 이하", 3_000_000_000),
        ("30억 초과", 10_000_000_000),
    ]

    result = []
    for desc, limit in bracket_descriptions:
        for bracket in TAX_BRACKETS:
            if bracket["limit"] == limit or (limit > TAX_BRACKETS[-1]["limit"] and bracket == TAX_BRACKETS[-1]):
                rate_percent = int(bracket["rate"] * 100)
                progressive_deduction = bracket["progressive_deduction"]

                result.append({
                    "limit_desc": desc,
                    "rate_percent": f"{rate_percent}%",
                    "progressive_deduction_formatted": format_amount(progressive_deduction),
                })
                break

    return result


def get_base_deduction(donor_relationship: str, is_minor: bool, is_non_resident: bool) -> int:
    """
    기본 공제액 계산.

    Args:
        donor_relationship: 증여자 관계 (수증자 기준, 예: 부모→자녀 = 직계존속)
        is_minor: 미성년자 여부
        is_non_resident: 비거주자 여부

    Returns:
        int: 기본 공제액
    """
    # 비거주자는 공제 없음
    if is_non_resident:
        return 0

    # 미성년자 특례: 직계존속으로부터 미성년자 증여 (부모→미성년자녀)
    if is_minor and donor_relationship == "직계존속":
        return MINOR_DEDUCTION  # 2천만원
    return GIFT_DEDUCTION_BASE.get(donor_relationship, 10_000_000)


def apply_tax_rate(taxable_base: int) -> int:
    """
    세율 적용 및 산출세액 계산.

    Args:
        taxable_base: 과세표준

    Returns:
        int: 산출세액
    """
    for bracket in TAX_BRACKETS:
        if taxable_base <= bracket["limit"]:
            return int(taxable_base * bracket["rate"] - bracket["progressive_deduction"])
    return 0


def get_tax_rate_detail(taxable_base: int) -> str:
    """
    세율 적용 상세 설명.

    Args:
        taxable_base: 과세표준

    Returns:
        str: 세율 적용 상세 (예: "50,000,000원 × 10% - 0원")
    """
    for bracket in TAX_BRACKETS:
        if taxable_base <= bracket["limit"]:
            rate_percent = int(bracket["rate"] * 100)
            deduction = bracket["progressive_deduction"]
            return f"{taxable_base:,}원 × {rate_percent}% - {deduction:,}원"
    return ""


def generate_warnings(gift_date: date, is_generation_skipping: bool, current_date: date) -> list[str]:
    """
    주의사항 생성.

    Args:
        gift_date: 증여일자
        is_generation_skipping: 세대생략 증여 여부
        current_date: 현재 날짜 (기한 경과 판단용)

    Returns:
        list[str]: 주의사항 목록
    """
    warnings = []

    # 신고 기한
    filing_deadline = gift_date + timedelta(days=90)

    # 기한 경과 여부 확인
    if current_date > filing_deadline:
        # 기한 경과 - 경고 메시지
        overdue_days = (current_date - filing_deadline).days
        warnings.append(
            f"⚠️ 신고기한({filing_deadline.strftime('%Y년 %m월 %d일')})이 {overdue_days}일 경과했습니다. "
            f"즉시 신고하셔야 하며, 기한 후 신고 가산세(무신고 20%, 납부지연 등)가 부과될 수 있습니다."
        )
    else:
        # 기한 내 - 일반 안내
        remaining_days = (filing_deadline - current_date).days
        warnings.append(
            f"증여일로부터 3개월 이내({filing_deadline.strftime('%Y년 %m월 %d일')}까지, 남은 기간: {remaining_days}일) 신고해야 합니다."
        )
        warnings.append("기한 후 신고 시 가산세가 부과됩니다.")

    # 세대생략 할증 안내
    if is_generation_skipping:
        warnings.append("세대를 건너뛴 증여로 30% 할증이 적용되었습니다.")

    return warnings
