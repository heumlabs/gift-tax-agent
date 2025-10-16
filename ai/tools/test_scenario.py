"""국세청 계산기와 비교를 위한 시나리오 테스트 스크립트."""

from datetime import date

from ai.tools.gift_tax.calculator import calculate_gift_tax_simple
from ai.tools.gift_tax.models import GiftTaxSimpleOutput


def print_result(result: GiftTaxSimpleOutput) -> None:
    """계산 결과를 보기 좋게 출력."""
    print("\n" + "=" * 60)
    print("📊 증여세 계산 결과")
    print("=" * 60)

    print("\n【계산 과정】")
    for step in result["steps"]:
        print(f"\n{step['step']}. {step['description']}")
        print(f"   공식: {step['formula']}")
        print(f"   계산: {step['detail']}")
        print(f"   결과: {step['value']:,}원")

    print("\n" + "=" * 60)
    print("【최종 결과】")
    print("=" * 60)
    print(f"증여재산가액:     {result['gift_value']:,}원")
    print(f"증여재산공제:     {result['total_deduction']:,}원")
    print(f"과세표준:         {result['taxable_base']:,}원")
    print(f"산출세액:         {result['calculated_tax']:,}원")
    print(f"세대생략 할증:    {result['surtax']:,}원")
    print(f"최종 증여세액:    {result['final_tax']:,}원")

    print("\n" + "=" * 60)
    print("【주의사항】")
    print("=" * 60)
    for i, warning in enumerate(result["warnings"], 1):
        print(f"{i}. {warning}")
    print("=" * 60 + "\n")


def run_scenario(
    scenario_name: str,
    gift_date: date,
    donor_relationship: str,
    gift_property_value: int,
    **kwargs,
) -> None:
    """시나리오 실행."""
    print(f"\n🧪 시나리오: {scenario_name}")
    print(f"   증여일자: {gift_date}")
    print(f"   증여자 관계: {donor_relationship}")
    print(f"   증여재산가액: {gift_property_value:,}원")

    if kwargs:
        print("   추가 정보:")
        for key, value in kwargs.items():
            if value:
                print(f"   - {key}: {value}")

    result = calculate_gift_tax_simple(
        gift_date=gift_date,
        donor_relationship=donor_relationship,
        gift_property_value=gift_property_value,
        **kwargs,
    )

    print_result(result)


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🔍 국세청 증여세 간편계산기 비교 테스트")
    print("=" * 70)

    # 시나리오 선택
    print("\n📝 테스트 시나리오를 선택하세요:\n")
    print("  1: 직접 입력 (커스텀)")
    print("  2: 부모→성인자녀 3억 (거주자)")
    print("  3: 부모→성인자녀 3억 (비거주자)")
    print("  4: 배우자 3억 (거주자)")
    print("  5: 배우자 3억 (비거주자)")
    print("  6: 배우자 8억 (거주자)")
    print("  7: 배우자 8억 (비거주자)")
    print("  8: 조부모→손자 2억 (세대생략, 거주자)")
    print("  9: 조부모→손자 2억 (세대생략, 비거주자)")
    scenario_choice = input("\n선택 (기본: 2): ") or "2"

    today = date.today()

    # 시나리오별 설정
    if scenario_choice == "1":
        # 직접 입력
        print("\n📝 아래 값을 입력해주세요 (Enter로 기본값 사용)\n")

        # 증여일자
        year = int(input("증여일자 - 년도 (기본: 2025): ") or "2025")
        month = int(input("증여일자 - 월 (기본: 10): ") or "10")
        day = int(input("증여일자 - 일 (기본: 16): ") or "16")
        gift_date = date(year, month, day)

        # 증여자 관계 (수증자 기준)
        print("\n증여자와의 관계 (수증자 기준):")
        print("  1: 배우자")
        print("  2: 직계존속 (부모→자녀, 조부모→손자)")
        print("  3: 직계비속 (자녀→부모)")
        print("  4: 기타친족")
        rel_choice = input("선택 (기본: 2): ") or "2"
        rel_map = {"1": "배우자", "2": "직계존속", "3": "직계비속", "4": "기타친족"}
        donor_relationship = rel_map[rel_choice]

        # 증여재산가액
        gift_value_input = input("\n증여받은 재산가액 (원, 기본: 300000000): ") or "300000000"
        gift_property_value = int(gift_value_input)

        # 세대생략
        is_gen_skip = input("\n세대를 건너뛴 증여입니까? (y/n, 기본: n): ").lower() == "y"

        # 미성년자
        is_minor = input("수증자가 미성년자입니까? (y/n, 기본: n): ").lower() == "y"

        # 비거주자
        is_non_res = input("수증자가 비거주자입니까? (y/n, 기본: n): ").lower() == "y"

        # 혼인공제
        marriage_input = input("\n혼인 증여재산공제 금액 (원, 기본: 0): ") or "0"
        marriage_deduction_amount = int(marriage_input)

        # 출산공제
        birth_input = input("출산 증여재산공제 금액 (원, 기본: 0): ") or "0"
        childbirth_deduction_amount = int(birth_input)

        # 채무액
        debt_input = input("채무액 (원, 기본: 0): ") or "0"
        secured_debt = int(debt_input)

    elif scenario_choice == "3":
        # 부모→성인자녀 3억 (비거주자)
        gift_date = today
        donor_relationship = "직계존속"  # 부모→자녀 (자녀 입장에서 부모는 직계존속)
        gift_property_value = 300_000_000
        is_gen_skip = False
        is_minor = False
        is_non_res = True
        marriage_deduction_amount = 0
        childbirth_deduction_amount = 0
        secured_debt = 0

    elif scenario_choice == "4":
        # 배우자 3억 (거주자)
        gift_date = today
        donor_relationship = "배우자"
        gift_property_value = 300_000_000
        is_gen_skip = False
        is_minor = False
        is_non_res = False
        marriage_deduction_amount = 0
        childbirth_deduction_amount = 0
        secured_debt = 0

    elif scenario_choice == "5":
        # 배우자 3억 (비거주자)
        gift_date = today
        donor_relationship = "배우자"
        gift_property_value = 300_000_000
        is_gen_skip = False
        is_minor = False
        is_non_res = True
        marriage_deduction_amount = 0
        childbirth_deduction_amount = 0
        secured_debt = 0

    elif scenario_choice == "6":
        # 배우자 8억 (거주자)
        gift_date = today
        donor_relationship = "배우자"
        gift_property_value = 800_000_000
        is_gen_skip = False
        is_minor = False
        is_non_res = False
        marriage_deduction_amount = 0
        childbirth_deduction_amount = 0
        secured_debt = 0

    elif scenario_choice == "7":
        # 배우자 8억 (비거주자)
        gift_date = today
        donor_relationship = "배우자"
        gift_property_value = 800_000_000
        is_gen_skip = False
        is_minor = False
        is_non_res = True
        marriage_deduction_amount = 0
        childbirth_deduction_amount = 0
        secured_debt = 0

    elif scenario_choice == "8":
        # 조부모→손자 2억 (세대생략, 거주자)
        gift_date = today
        donor_relationship = "직계존속"  # 조부모→손자 (손자 입장에서 조부모는 직계존속)
        gift_property_value = 200_000_000
        is_gen_skip = True
        is_minor = False
        is_non_res = False
        marriage_deduction_amount = 0
        childbirth_deduction_amount = 0
        secured_debt = 0

    elif scenario_choice == "9":
        # 조부모→손자 2억 (세대생략, 비거주자)
        gift_date = today
        donor_relationship = "직계존속"  # 조부모→손자 (손자 입장에서 조부모는 직계존속)
        gift_property_value = 200_000_000
        is_gen_skip = True
        is_minor = False
        is_non_res = True
        marriage_deduction_amount = 0
        childbirth_deduction_amount = 0
        secured_debt = 0

    else:
        # 기본: 부모→성인자녀 3억
        gift_date = today
        donor_relationship = "직계존속"  # 부모→자녀 (자녀 입장에서 부모는 직계존속)
        gift_property_value = 300_000_000
        is_gen_skip = False
        is_minor = False
        is_non_res = False
        marriage_deduction_amount = 0
        childbirth_deduction_amount = 0
        secured_debt = 0

    print("\n" + "=" * 70)
    print("📋 입력 요약")
    print("=" * 70)
    print(f"증여일자:                 {gift_date}")
    print(f"증여자 관계:              {donor_relationship}")
    print(f"증여받은 재산가액:        {gift_property_value:,}원")
    print(f"세대생략 증여:            {'예' if is_gen_skip else '아니오'}")
    print(f"미성년자 수증자:          {'예' if is_minor else '아니오'}")
    print(f"비거주자:                 {'예' if is_non_res else '아니오'}")
    print(f"혼인공제:                 {marriage_deduction_amount:,}원")
    print(f"출산공제:                 {childbirth_deduction_amount:,}원")
    print(f"채무액:                   {secured_debt:,}원")
    print("=" * 70)

    # 계산 실행
    result = calculate_gift_tax_simple(
        gift_date=gift_date,
        donor_relationship=donor_relationship,
        gift_property_value=gift_property_value,
        is_generation_skipping=is_gen_skip,
        is_minor_recipient=is_minor,
        is_non_resident=is_non_res,
        marriage_deduction_amount=marriage_deduction_amount,
        childbirth_deduction_amount=childbirth_deduction_amount,
        secured_debt=secured_debt,
    )

    print_result(result)

    print("\n💡 국세청 홈택스에서 동일한 값으로 계산하여 비교해보세요!")
    print("   https://www.hometax.go.kr")
    print("   증여세 신고 > 증여세 자동계산 > 간편계산")
    print("\n" + "=" * 70 + "\n")