# 증여세 계산 워크플로 고도화 설계 문서

## 목차
1. [응답 품질 개선](#1-응답-품질-개선)
2. [Calculation API 스펙](#2-calculation-api-스펙)
3. [Frontend API Contract](#3-frontend-api-contract)

---

# 1. 응답 품질 개선

## 1.1 현황 분석

### 현재 응답 예시
```
직계존속으로부터 1,000,000,000원을 증여받을 경우, 예상되는 증여세는 225,000,000원입니다.

증여재산가액 1,000,000,000원에서 직계존속 공제액 50,000,000원을 제외한 과세표준은 950,000,000원입니다. 과세표준 950,000,000원은 5억 초과 10억 이하 세율 구간에 해당하여 30%의 세율이 적용됩니다. 이를 통해 산출된 최종 증여세액은 225,000,000원입니다.
```

### 문제점
- ❌ 기계적이고 딱딱한 톤
- ❌ 숫자 가독성 떨어짐 (1,000,000,000원)
- ❌ 계산 과정 불명확 (누진공제 설명 없음)
- ❌ 세율 구간 상세 설명 부족
- ❌ 추가 고려사항 안내 없음
- ❌ 한 문단에 모든 정보 압축

### 목표 응답 (ChatGPT 수준 + 전문성)
```
📋 증여세 계산 결과

아버지께서 증여하시는 10억원에 대한 증여세는 약 2억 2,500만원이에요.

📊 상세 계산 과정

① 증여재산가액
   10억원

② 증여재산공제
   - 직계존속(부모) → 성인자녀 기본공제: 5,000만원

③ 과세표준
   10억원 - 5,000만원 = 9억 5,000만원

④ 세율 적용
   과세표준 9.5억원은 '5억 초과 ~ 10억 이하' 구간에 해당해요.

   [증여세 세율표]
   • 1억 이하: 10% (누진공제 0원)
   • 1억 초과 ~ 5억 이하: 20% (누진공제 1,000만원)
   • 5억 초과 ~ 10억 이하: 30% (누진공제 6,000만원) ← 여기!
   • 10억 초과 ~ 30억 이하: 40% (누진공제 1.6억원)
   • 30억 초과: 50% (누진공제 4.6억원)

   계산:
   9.5억원 × 30% = 2억 8,500만원
   2억 8,500만원 - 6,000만원(누진공제) = 2억 2,500만원

⚠️ 추가로 확인이 필요한 사항

• 과거 10년간 동일인(아버지)으로부터 증여받은 금액이 있으신가요?
  → 있다면 합산되어 세금이 더 나올 수 있어요.

• 현금 증여인가요, 부동산 증여인가요?
  → 부동산은 취득세(3.5%) + 지방교육세(0.35%)가 별도로 발생해요.

📅 신고 기한
증여일(2025년 8월 1일)로부터 3개월 이내인 2025년 10월 31일까지 신고하셔야 해요.
현재 기준 13일 남았으니 서두르시는 게 좋겠어요!

💡 참고사항
이 계산은 기본적인 정보를 바탕으로 한 예상치예요.
정확한 신고를 위해서는 세무사와 상담하시는 걸 권장드려요.
```

## 1.2 개선 전략

### 페르소나 설정
**30대 초반 여성 세무사**
- 전문적이지만 친근함
- 존댓말 + 반말 적절히 혼용 ("~이에요", "~해요")
- 딱딱한 법률 용어보다는 쉬운 설명 우선
- 이모지 적절히 활용 (과하지 않게)
- "~입니다" → "~이에요/해요"

### 숫자 표기법 개선
**현재:** 1,000,000,000원
**개선:** 10억원

**규칙:**
- 억 단위: "10억원", "4.5억원"
- 천만 단위: "5,000만원", "2억 2,500만원"
- 혼합: "9억 5,000만원"
- 소수점: 억 단위에서만 사용 (예: 4.5억)

### 응답 구조화
```
1. 📋 결과 요약 (1-2줄)
   - 핵심 정보만 간결하게

2. 📊 상세 계산 과정
   ① 증여재산가액
   ② 증여재산공제
   ③ 과세표준
   ④ 세율 적용
      - 세율표 시각화
      - 누진공제 상세 설명
      - 단계별 계산

3. ⚠️ 추가 확인사항
   - 과거 증여 여부
   - 재산 종류 (현금/부동산)
   - 기타 특수 상황

4. 📅 신고 기한
   - 명확한 날짜
   - 남은 기간
   - 기한 후 불이익

5. 💡 참고사항
   - 면책 조항 (부드럽게)
   - 추가 상담 권유
```

## 1.3 구현 계획

### Phase 1: Calculator 개선

**파일:** `ai/tools/gift_tax/calculator.py`

**새 유틸 함수 추가:**

```python
def format_amount(amount: int) -> str:
    """
    금액을 읽기 좋은 형식으로 변환

    Examples:
        1000000000 → "10억원"
        950000000 → "9억 5,000만원"
        50000000 → "5,000만원"
        225000000 → "2억 2,500만원"
        450000000 → "4.5억원"
    """
    억 = amount // 100000000
    만 = (amount % 100000000) // 10000

    if 만 == 0:
        return f"{억}억원"
    elif 만 % 1000 == 0:
        # 천만 단위로 떨어지면
        천만 = 만 // 1000
        return f"{억}억 {천만:,}만원" if 억 > 0 else f"{천만:,}만원"
    else:
        # 소수점 표현 (억 단위만)
        if 억 > 0 and 만 >= 5000:
            return f"{억 + 만/10000:.1f}억원"
        return f"{억}억 {만:,}만원" if 억 > 0 else f"{만:,}만원"


def get_tax_bracket_info(taxable_base: int) -> dict:
    """
    과세표준에 해당하는 세율 구간 정보 반환
    """
    brackets = [
        (100000000, 0.10, 0, "1억 이하"),
        (500000000, 0.20, 10000000, "1억 초과 ~ 5억 이하"),
        (1000000000, 0.30, 60000000, "5억 초과 ~ 10억 이하"),
        (3000000000, 0.40, 160000000, "10억 초과 ~ 30억 이하"),
        (float('inf'), 0.50, 460000000, "30억 초과"),
    ]

    for max_val, rate, deduction, range_str in brackets:
        if taxable_base <= max_val:
            return {
                "range": range_str,
                "rate": rate,
                "rate_display": f"{int(rate * 100)}%",
                "progressive_deduction": deduction,
                "progressive_deduction_formatted": format_amount(deduction)
            }


def get_all_tax_brackets(current_taxable_base: int) -> list[dict]:
    """
    전체 세율표 정보 반환 (현재 구간 표시 포함)
    """
    brackets_data = [
        (0, 100000000, 0.10, 0, "1억 이하"),
        (100000001, 500000000, 0.20, 10000000, "1억 초과 ~ 5억 이하"),
        (500000001, 1000000000, 0.30, 60000000, "5억 초과 ~ 10억 이하"),
        (1000000001, 3000000000, 0.40, 160000000, "10억 초과 ~ 30억 이하"),
        (3000000001, float('inf'), 0.50, 460000000, "30억 초과"),
    ]

    result = []
    for min_val, max_val, rate, deduction, range_str in brackets_data:
        is_current = min_val <= current_taxable_base <= max_val
        result.append({
            "range": range_str,
            "min": min_val,
            "max": max_val if max_val != float('inf') else None,
            "rate": rate,
            "rate_display": f"{int(rate * 100)}%",
            "progressive_deduction": deduction,
            "progressive_deduction_formatted": format_amount(deduction),
            "is_current": is_current
        })

    return result
```

**기존 함수 개선:**

`calculate_gift_tax_simple()` 함수에 `calculation_breakdown` 추가:

```python
def calculate_gift_tax_simple(...) -> GiftTaxSimpleOutput:
    """
    기존 로직 + breakdown 추가
    """
    # ... 기존 계산 로직 ...

    # Breakdown 정보 생성
    tax_bracket = get_tax_bracket_info(taxable_base)
    all_brackets = get_all_tax_brackets(taxable_base)

    # 관계 한글 변환
    relationship_map = {
        "직계존속": "부모님",
        "직계비속": "자녀",
        "배우자": "배우자",
        "기타친족": "기타 친족"
    }
    relationship_korean = relationship_map.get(donor_relationship, donor_relationship)
    recipient_type = "미성년자녀" if is_minor_recipient else "성인자녀"

    calculation_steps = [
        {
            "step": 1,
            "description": "증여재산가액",
            "value": gift_property_value,
            "formatted": format_amount(gift_property_value)
        },
        {
            "step": 2,
            "description": f"증여재산공제 ({relationship_korean} → {recipient_type})",
            "value": total_deduction,
            "formatted": format_amount(total_deduction),
            "breakdown": {
                "basic": format_amount(basic_deduction),
                "marriage": format_amount(marriage_deduction_amount) if marriage_deduction_amount else None,
                "childbirth": format_amount(childbirth_deduction_amount) if childbirth_deduction_amount else None
            }
        },
        {
            "step": 3,
            "description": "과세표준",
            "value": taxable_base,
            "formatted": format_amount(taxable_base),
            "calculation": f"{format_amount(gift_property_value)} - {format_amount(total_deduction)}"
        },
        {
            "step": 4,
            "description": "산출세액 (누진공제 전)",
            "value": calculated_tax,
            "formatted": format_amount(calculated_tax),
            "calculation": f"{format_amount(taxable_base)} × {tax_bracket['rate_display']}"
        },
        {
            "step": 5,
            "description": "누진공제",
            "value": tax_bracket["progressive_deduction"],
            "formatted": tax_bracket["progressive_deduction_formatted"],
            "info": tax_bracket["range"]
        },
        {
            "step": 6,
            "description": "최종 증여세액",
            "value": final_tax,
            "formatted": format_amount(final_tax),
            "calculation": f"{format_amount(calculated_tax)} - {tax_bracket['progressive_deduction_formatted']}"
        }
    ]

    breakdown = {
        "formatted_amounts": {
            "gift_value": format_amount(gift_property_value),
            "total_deduction": format_amount(total_deduction),
            "taxable_base": format_amount(taxable_base),
            "calculated_tax": format_amount(calculated_tax),
            "progressive_deduction": tax_bracket["progressive_deduction_formatted"],
            "final_tax": format_amount(final_tax)
        },
        "tax_bracket": tax_bracket,
        "all_tax_brackets": all_brackets,
        "calculation_steps_detailed": calculation_steps
    }

    return GiftTaxSimpleOutput(
        # 기존 필드들...
        calculation_breakdown=breakdown  # 새로 추가
    )
```

### Phase 2: Synthesis Prompt 재설계

**파일:** `ai/prompts/clarifying.py`

새로운 `SYNTHESIS_PROMPT` 추가:

```python
SYNTHESIS_PROMPT_V2 = """당신은 30대 초반 여성 세무사예요. 전문성을 유지하면서도 친근하고 이해하기 쉽게 설명해주세요.

### 페르소나 가이드라인
- 존댓말 + 반말 혼용: "~이에요", "~해요", "~하셔야 해요"
- 전문적이지만 부담스럽지 않게
- 불필요한 인사말 제거 ("안녕하세요", "문의하신")
- 이모지 적절히 활용 (섹션 구분용)

### 계산 결과 정보

**최종 증여세**: {final_tax_formatted}
**증여재산가액**: {gift_value_formatted}
**공제액**: {deduction_formatted}
**과세표준**: {taxable_base_formatted}

**세율 구간**: {tax_bracket_range}
**적용 세율**: {tax_rate}
**누진공제**: {progressive_deduction_formatted}

**상세 계산 과정**:
{calculation_steps_formatted}

**전체 세율표**:
{all_tax_brackets_formatted}

**주의사항**:
{warnings_formatted}

---

### 응답 구조

아래 구조를 **반드시** 따라주세요:

```
📋 증여세 계산 결과

[한 줄 요약: 누구에게서, 얼마를 증여받을 때, 증여세가 얼마인지]

📊 상세 계산 과정

① 증여재산가액
   [금액과 간단한 설명]

② 증여재산공제
   - [공제 종류와 금액 설명]

③ 과세표준
   [계산식 포함]

④ 세율 적용
   과세표준 [금액]은 '[구간명]' 구간에 해당해요.

   [증여세 세율표]
   [전체 세율표를 bullets로, 현재 구간은 화살표나 강조로 표시]

   계산:
   [단계별 계산 과정을 명확하게]
   - 산출세액 계산
   - 누진공제 차감
   - 최종세액

⚠️ 추가로 확인이 필요한 사항

• 과거 10년간 동일인으로부터 증여받은 금액이 있으신가요?
  → [설명]

• 현금 증여인가요, 부동산 증여인가요?
  → [설명]

[warnings가 있으면 여기에 추가로 표시]

📅 신고 기한
[증여일 기준 3개월, 정확한 날짜, 남은 기간]
[기한 경과 시 가산세 안내]

💡 참고사항
이 계산은 기본적인 정보를 바탕으로 한 예상치예요.
정확한 신고를 위해서는 세무사와 상담하시는 걸 권장드려요.
```

### 작성 규칙

1. **숫자 표기**
   - 억 단위: "10억원", "4.5억원"
   - 천만 단위: "5,000만원", "2억 2,500만원"
   - 억/만 혼합: "9억 5,000만원"

2. **톤앤매너**
   - "~입니다" → "~이에요/해요"
   - "하시기 바랍니다" → "~하시는 걸 권장드려요"
   - "과세표준" 같은 용어는 사용하되, 바로 뒤에 쉬운 설명 추가

3. **계산 과정 설명**
   - 각 단계마다 "왜 이렇게 계산하는지" 간단히 설명
   - 누진공제 개념을 쉽게 설명

4. **세율표 표시**
   - 전체 세율표를 보여주되
   - 현재 해당하는 구간은 화살표나 "← 여기!" 같은 표시로 강조

---

### Few-shot 예제

**예제 1: 부모 → 성인자녀 10억 증여**

입력:
- 증여재산가액: 10억원
- 관계: 직계존속
- 공제액: 5,000만원
- 과세표준: 9억 5,000만원
- 세율: 30%, 누진공제 6,000만원
- 최종세액: 2억 2,500만원

출력:
```
📋 증여세 계산 결과

아버지께서 증여하시는 10억원에 대한 증여세는 약 2억 2,500만원이에요.

📊 상세 계산 과정

① 증여재산가액
   10억원

② 증여재산공제
   - 직계존속(부모) → 성인자녀 기본공제: 5,000만원

③ 과세표준
   10억원 - 5,000만원 = 9억 5,000만원

④ 세율 적용
   과세표준 9.5억원은 '5억 초과 ~ 10억 이하' 구간에 해당해요.

   [증여세 세율표]
   • 1억 이하: 10% (누진공제 0원)
   • 1억 초과 ~ 5억 이하: 20% (누진공제 1,000만원)
   • 5억 초과 ~ 10억 이하: 30% (누진공제 6,000만원) ← 여기!
   • 10억 초과 ~ 30억 이하: 40% (누진공제 1.6억원)
   • 30억 초과: 50% (누진공제 4.6억원)

   계산:
   9.5억원 × 30% = 2억 8,500만원
   2억 8,500만원 - 6,000만원(누진공제) = 2억 2,500만원

⚠️ 추가로 확인이 필요한 사항

• 과거 10년간 동일인(아버지)으로부터 증여받은 금액이 있으신가요?
  → 있다면 합산되어 세금이 더 나올 수 있어요.

• 현금 증여인가요, 부동산 증여인가요?
  → 부동산은 취득세(3.5%) + 지방교육세(0.35%)가 별도로 발생해요.

📅 신고 기한
증여일(2025년 8월 1일)로부터 3개월 이내인 2025년 10월 31일까지 신고하셔야 해요.
현재 기준 13일 남았으니 서두르시는 게 좋겠어요!

💡 참고사항
이 계산은 기본적인 정보를 바탕으로 한 예상치예요.
정확한 신고를 위해서는 세무사와 상담하시는 걸 권장드려요.
```

**예제 2: 배우자 간 5억 증여**

입력:
- 증여재산가액: 5억원
- 관계: 배우자
- 공제액: 6억원 (배우자 공제)
- 과세표준: 0원 (공제 후 음수이므로)
- 최종세액: 0원

출력:
```
📋 증여세 계산 결과

배우자께서 증여하시는 5억원에 대한 증여세는 0원이에요!

📊 상세 계산 과정

① 증여재산가액
   5억원

② 증여재산공제
   - 배우자 간 증여 공제: 6억원

③ 과세표준
   5억원 - 6억원 = -1억원 → 0원

   공제액이 증여재산가액보다 크기 때문에 과세표준이 0원이 돼요.
   따라서 증여세가 발생하지 않아요!

⚠️ 추가로 확인이 필요한 사항

• 과거 10년간 배우자로부터 증여받은 금액이 있으신가요?
  → 10년간 합산하여 6억원까지 공제되므로, 과거 증여액이 있다면 공제 한도가 줄어들 수 있어요.

📅 신고 기한
증여세가 0원이어도 증여일로부터 3개월 이내에는 신고를 하셔야 해요.
신고를 하지 않으면 추후 문제가 될 수 있으니 꼭 신고하세요!

💡 참고사항
이 계산은 기본적인 정보를 바탕으로 한 예상치예요.
정확한 신고를 위해서는 세무사와 상담하시는 걸 권장드려요.
```

---

이제 위 구조와 예제를 참고하여, 제공된 계산 결과를 바탕으로 응답을 생성해주세요.
"""
```

### Phase 3: Synthesis Node 개선

**파일:** `ai/pipelines/langgraph_workflow.py`

`_synthesize_response()` 함수 개선:

```python
async def _synthesize_response(
    calculation: dict, collected: dict, intent: str
) -> str:
    """
    계산 결과를 자연어로 합성 (개선 버전)

    Args:
        calculation: 계산 결과 (breakdown 포함)
        collected: 수집된 파라미터
        intent: 사용자 의도

    Returns:
        자연어 응답
    """
    try:
        from ai.prompts.clarifying import SYNTHESIS_PROMPT_V2

        # Breakdown 정보 추출
        breakdown = calculation.get("calculation_breakdown", {})

        # 세율 구간표 포맷팅
        all_brackets = breakdown.get("all_tax_brackets", [])
        tax_brackets_text = "\n".join([
            f"   • {b['range']}: {b['rate_display']} "
            f"(누진공제 {b['progressive_deduction_formatted']})"
            + (" ← 여기!" if b.get("is_current") else "")
            for b in all_brackets
        ])

        # 계산 단계 포맷팅
        calc_steps = breakdown.get("calculation_steps_detailed", [])
        steps_text = "\n".join([
            f"   {s['description']}: {s['formatted']}"
            + (f" ({s['calculation']})" if s.get('calculation') else "")
            for s in calc_steps
        ])

        # Warnings 포맷팅
        warnings = calculation.get("warnings", [])
        warnings_text = "\n".join([f"⚠️ {w}" for w in warnings]) if warnings else ""

        # 포맷팅된 금액 정보
        formatted_amounts = breakdown.get("formatted_amounts", {})
        tax_bracket = breakdown.get("tax_bracket", {})

        # 프롬프트 변수 준비
        prompt_vars = {
            "final_tax_formatted": formatted_amounts.get("final_tax", ""),
            "gift_value_formatted": formatted_amounts.get("gift_value", ""),
            "deduction_formatted": formatted_amounts.get("total_deduction", ""),
            "taxable_base_formatted": formatted_amounts.get("taxable_base", ""),
            "tax_bracket_range": tax_bracket.get("range", ""),
            "tax_rate": tax_bracket.get("rate_display", ""),
            "progressive_deduction_formatted": tax_bracket.get("progressive_deduction_formatted", ""),
            "calculation_steps_formatted": steps_text,
            "all_tax_brackets_formatted": tax_brackets_text,
            "warnings_formatted": warnings_text
        }

        # 프롬프트 생성
        prompt = SYNTHESIS_PROMPT_V2.format(**prompt_vars)

        # Gemini API 호출
        settings = GeminiSettings.from_env()
        client = GeminiClient(settings)

        response = await client.generate_content(
            system_prompt="",
            user_message=prompt
        )

        LOGGER.info("Synthesis successful with V2 prompt")
        return response

    except GeminiClientError:
        LOGGER.exception("Synthesis error")
        # Fallback: 간단한 템플릿 기반 응답
        from ai.tools.gift_tax.calculator import format_amount

        final_tax = calculation.get("final_tax", 0)
        gift_value = calculation.get("gift_value", 0)

        fallback_response = f"""증여세 계산 결과예요.

증여재산 {format_amount(gift_value)}에 대한 증여세는 약 {format_amount(final_tax)}이에요.

정확한 계산을 위해서는 세무사와 상담하시는 걸 권장드려요.
"""
        return fallback_response
```

---

# 2. Calculation API 스펙

## 2.1 현재 Steps 구조 분석

### 기존 출력 예시
```json
{
  "calculation": {
    "steps": [
      {
        "step": 1,
        "value": 1000000000,
        "detail": "1,000,000,000원 - 0원",
        "formula": "증여받은 재산가액 - 채무액",
        "description": "증여재산가액"
      },
      {
        "step": 2,
        "value": 50000000,
        "detail": "기본 50,000,000원 + 혼인 0원 + 출산 0원",
        "formula": "기본공제 + 혼인공제 + 출산공제",
        "description": "증여재산공제"
      },
      {
        "step": 3,
        "value": 950000000,
        "detail": "1,000,000,000원 - 50,000,000원",
        "formula": "증여재산가액 - 증여재산공제",
        "description": "과세표준"
      },
      {
        "step": 4,
        "value": 225000000,
        "detail": "950,000,000원 × 30% - 60,000,000원",
        "formula": "과세표준 × 세율 - 누진공제",
        "description": "산출세액"
      },
      {
        "step": 6,
        "value": 225000000,
        "detail": "225,000,000원 + 0원",
        "formula": "산출세액 + 할증세액",
        "description": "최종 증여세액"
      }
    ]
  }
}
```

### 문제점
1. **Step 5 누락**: Step 4에서 6으로 바로 점프
2. **누진공제 설명 부족**: Step 4에 통합되어 있음
3. **할증세액 표시**: 거의 항상 0원인데 별도 step
4. **Unicode escape**: `\uc99d\uc5ec` 같은 형태 (JSON 인코딩 문제)

## 2.2 개선된 API 출력 구조

### 완전한 응답 예시

```json
{
  "final_tax": 225000000,
  "gift_value": 1000000000,
  "total_deduction": 50000000,
  "taxable_base": 950000000,

  "steps": [
    {
      "step": 1,
      "value": 1000000000,
      "detail": "1,000,000,000원 - 0원",
      "formula": "증여받은 재산가액 - 채무액",
      "description": "증여재산가액"
    },
    {
      "step": 2,
      "value": 50000000,
      "detail": "기본 50,000,000원 + 혼인 0원 + 출산 0원",
      "formula": "기본공제 + 혼인공제 + 출산공제",
      "description": "증여재산공제"
    },
    {
      "step": 3,
      "value": 950000000,
      "detail": "1,000,000,000원 - 50,000,000원",
      "formula": "증여재산가액 - 증여재산공제",
      "description": "과세표준"
    },
    {
      "step": 4,
      "value": 285000000,
      "detail": "950,000,000원 × 30%",
      "formula": "과세표준 × 세율",
      "description": "산출세액 (누진공제 차감 전)"
    },
    {
      "step": 5,
      "value": 60000000,
      "detail": "5억 초과 ~ 10억 이하 구간",
      "formula": "세율 구간별 누진공제",
      "description": "누진공제"
    },
    {
      "step": 6,
      "value": 225000000,
      "detail": "285,000,000원 - 60,000,000원",
      "formula": "산출세액 - 누진공제",
      "description": "최종 증여세액"
    }
  ],

  "calculation_breakdown": {
    "formatted_amounts": {
      "gift_value": "10억원",
      "total_deduction": "5,000만원",
      "taxable_base": "9억 5,000만원",
      "calculated_tax": "2억 8,500만원",
      "progressive_deduction": "6,000만원",
      "final_tax": "2억 2,500만원"
    },

    "tax_bracket": {
      "range": "5억 초과 ~ 10억 이하",
      "min": 500000001,
      "max": 1000000000,
      "rate": 0.30,
      "rate_display": "30%",
      "progressive_deduction": 60000000,
      "progressive_deduction_formatted": "6,000만원",
      "is_current": true
    },

    "all_tax_brackets": [
      {
        "range": "1억 이하",
        "min": 0,
        "max": 100000000,
        "rate": 0.10,
        "rate_display": "10%",
        "progressive_deduction": 0,
        "progressive_deduction_formatted": "0원",
        "is_current": false
      },
      {
        "range": "1억 초과 ~ 5억 이하",
        "min": 100000001,
        "max": 500000000,
        "rate": 0.20,
        "rate_display": "20%",
        "progressive_deduction": 10000000,
        "progressive_deduction_formatted": "1,000만원",
        "is_current": false
      },
      {
        "range": "5억 초과 ~ 10억 이하",
        "min": 500000001,
        "max": 1000000000,
        "rate": 0.30,
        "rate_display": "30%",
        "progressive_deduction": 60000000,
        "progressive_deduction_formatted": "6,000만원",
        "is_current": true
      },
      {
        "range": "10억 초과 ~ 30억 이하",
        "min": 1000000001,
        "max": 3000000000,
        "rate": 0.40,
        "rate_display": "40%",
        "progressive_deduction": 160000000,
        "progressive_deduction_formatted": "1.6억원",
        "is_current": false
      },
      {
        "range": "30억 초과",
        "min": 3000000001,
        "max": null,
        "rate": 0.50,
        "rate_display": "50%",
        "progressive_deduction": 460000000,
        "progressive_deduction_formatted": "4.6억원",
        "is_current": false
      }
    ],

    "calculation_steps_detailed": [
      {
        "step": 1,
        "description": "증여재산가액",
        "value": 1000000000,
        "formatted": "10억원"
      },
      {
        "step": 2,
        "description": "증여재산공제 (직계존속 → 성인자녀)",
        "value": 50000000,
        "formatted": "5,000만원",
        "breakdown": {
          "basic": "5,000만원",
          "marriage": null,
          "childbirth": null
        }
      },
      {
        "step": 3,
        "description": "과세표준",
        "value": 950000000,
        "formatted": "9억 5,000만원",
        "calculation": "10억원 - 5,000만원"
      },
      {
        "step": 4,
        "description": "산출세액 (누진공제 전)",
        "value": 285000000,
        "formatted": "2억 8,500만원",
        "calculation": "9.5억원 × 30%"
      },
      {
        "step": 5,
        "description": "누진공제",
        "value": 60000000,
        "formatted": "6,000만원",
        "info": "5억 초과 ~ 10억 이하 구간"
      },
      {
        "step": 6,
        "description": "최종 증여세액",
        "value": 225000000,
        "formatted": "2억 2,500만원",
        "calculation": "2억 8,500만원 - 6,000만원"
      }
    ]
  },

  "warnings": [
    "증여일로부터 3개월 이내(2025년 10월 31일까지, 남은 기간: 13일) 신고해야 합니다."
  ]
}
```

---

# 3. Frontend API Contract

## 3.1 개요

이 문서는 Frontend와 Backend 간 증여세 계산 API 통신 규격을 정의합니다.

**관련 문서:**
- [Backend API Contract](ai/backend_api_contract.md) - 기존 문서 (AI ↔ Backend)
- 본 문서 - Frontend ↔ Backend

## 3.2 Base URL

```
Development: http://localhost:8000
Production: TBD
```

## 3.3 API Endpoints

### 3.3.1 세션 생성

**Endpoint:** `POST /sessions`

**Request:**
```json
{
  "client_id_hash": "optional-hash-string"
}
```

**Response:** `201 Created`
```json
{
  "id": "61e3f2ba-4130-40bc-bf21-a2f904fcd493",
  "client_id_hash": "hash-string",
  "created_at": "2025-10-17T09:30:00Z"
}
```

### 3.3.2 메시지 전송 (증여세 계산 요청)

**Endpoint:** `POST /sessions/{session_id}/messages`

**Request:**
```json
{
  "content": "올해 8월에 아빠한테 10억 정도 받을거 같은데"
}
```

**Response:** `200 OK`

응답 예시는 섹션 2.2의 "완전한 응답 예시" 참조.

`msg_metadata` 필드에 다음 정보 포함:
- `intent`: 사용자 의도 ("gift_tax", "inheritance_tax", "general_info", "out_of_scope")
- `collected_parameters`: 수집된 파라미터 (9개 변수)
- `calculation`: 계산 결과 (steps + calculation_breakdown 포함)

### 3.3.3 대화 내역 조회

**Endpoint:** `GET /sessions/{session_id}/messages?limit=30`

**Response:** `200 OK`
```json
{
  "messages": [
    {
      "id": "msg-1",
      "session_id": "session-uuid",
      "role": "user",
      "content": "증여세 계산해줘",
      "created_at": "2025-10-17T09:30:00Z",
      "msg_metadata": null
    },
    {
      "id": "msg-2",
      "session_id": "session-uuid",
      "role": "assistant",
      "content": "증여일이 언제인가요?",
      "created_at": "2025-10-17T09:30:01Z",
      "msg_metadata": {
        "intent": "gift_tax",
        "collected_parameters": {},
        "missing_parameters": ["gift_date", "donor_relationship", "gift_property_value"]
      }
    }
  ],
  "next_cursor": null
}
```

## 3.4 TypeScript 타입 정의

```typescript
// Session
interface Session {
  id: string;
  client_id_hash?: string;
  created_at: string;
}

// Message
interface Message {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  msg_metadata?: MessageMetadata;
}

// Message Metadata
interface MessageMetadata {
  intent?: 'gift_tax' | 'inheritance_tax' | 'general_info' | 'out_of_scope';
  collected_parameters?: CollectedParameters;
  missing_parameters?: string[];
  calculation?: CalculationResult;
}

// Collected Parameters
interface CollectedParameters {
  gift_date?: string;  // YYYY-MM-DD
  donor_relationship?: '직계존속' | '직계비속' | '배우자' | '기타친족';
  gift_property_value?: number;
  is_generation_skipping?: boolean;
  is_minor_recipient?: boolean;
  is_non_resident?: boolean;
  marriage_deduction_amount?: number;
  childbirth_deduction_amount?: number;
  secured_debt?: number;
}

// Calculation Result
interface CalculationResult {
  final_tax: number;
  gift_value: number;
  total_deduction: number;
  taxable_base: number;
  steps: CalculationStep[];
  calculation_breakdown: CalculationBreakdown;
  warnings: string[];
}

// Calculation Step (기존 스펙)
interface CalculationStep {
  step: number;
  value: number;
  detail: string;
  formula: string;
  description: string;
}

// Calculation Breakdown (신규)
interface CalculationBreakdown {
  formatted_amounts: {
    gift_value: string;
    total_deduction: string;
    taxable_base: string;
    calculated_tax: string;
    progressive_deduction: string;
    final_tax: string;
  };

  tax_bracket: TaxBracket;
  all_tax_brackets: TaxBracket[];
  calculation_steps_detailed: DetailedCalculationStep[];
}

// Tax Bracket
interface TaxBracket {
  range: string;
  min: number;
  max: number | null;
  rate: number;
  rate_display: string;
  progressive_deduction: number;
  progressive_deduction_formatted: string;
  is_current: boolean;
}

// Detailed Calculation Step
interface DetailedCalculationStep {
  step: number;
  description: string;
  value: number;
  formatted: string;
  calculation?: string;
  breakdown?: {
    basic?: string;
    marriage?: string | null;
    childbirth?: string | null;
  };
  info?: string;
}
```

## 3.5 Frontend 활용 예시

### 시각화 예시 1: 계산 과정 표시

```tsx
interface CalculationStep {
  step: number;
  description: string;
  value: number;
  formatted: string;
  calculation?: string;
  breakdown?: {
    basic?: string;
    marriage?: string | null;
    childbirth?: string | null;
  };
}

function CalculationProcess({ steps }: { steps: CalculationStep[] }) {
  return (
    <div className="calculation-process">
      <h3>📊 상세 계산 과정</h3>
      {steps.map((step) => (
        <div key={step.step} className="step-item">
          <div className="step-number">#{step.step}</div>
          <div className="step-content">
            <div className="step-description">{step.description}</div>
            <div className="step-value">{step.formatted}</div>
            {step.calculation && (
              <div className="step-calculation">
                = {step.calculation}
              </div>
            )}
            {step.breakdown && (
              <div className="step-breakdown">
                {step.breakdown.basic && <span>기본: {step.breakdown.basic}</span>}
                {step.breakdown.marriage && <span>혼인: {step.breakdown.marriage}</span>}
                {step.breakdown.childbirth && <span>출산: {step.breakdown.childbirth}</span>}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
```

### 시각화 예시 2: 세율표 표시

```tsx
interface TaxBracket {
  range: string;
  rate_display: string;
  progressive_deduction_formatted: string;
  is_current: boolean;
}

function TaxBracketTable({ brackets }: { brackets: TaxBracket[] }) {
  return (
    <div className="tax-bracket-table">
      <h4>증여세 세율표</h4>
      <table>
        <thead>
          <tr>
            <th>과세표준 구간</th>
            <th>세율</th>
            <th>누진공제</th>
          </tr>
        </thead>
        <tbody>
          {brackets.map((bracket, idx) => (
            <tr
              key={idx}
              className={bracket.is_current ? 'current-bracket' : ''}
            >
              <td>
                {bracket.range}
                {bracket.is_current && <span className="badge">현재</span>}
              </td>
              <td>{bracket.rate_display}</td>
              <td>{bracket.progressive_deduction_formatted}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

### 시각화 예시 3: 결과 요약 카드

```tsx
interface CalculationSummary {
  gift_value: string;
  total_deduction: string;
  taxable_base: string;
  final_tax: string;
}

function SummaryCard({ summary }: { summary: CalculationSummary }) {
  return (
    <div className="summary-card">
      <h2>📋 계산 결과</h2>
      <div className="summary-row">
        <span className="label">증여재산가액</span>
        <span className="value">{summary.gift_value}</span>
      </div>
      <div className="summary-row">
        <span className="label">공제액</span>
        <span className="value deduction">-{summary.total_deduction}</span>
      </div>
      <div className="summary-row total">
        <span className="label">과세표준</span>
        <span className="value">{summary.taxable_base}</span>
      </div>
      <div className="summary-row highlight">
        <span className="label">최종 증여세</span>
        <span className="value tax">{summary.final_tax}</span>
      </div>
    </div>
  );
}
```

## 3.6 Error Responses

### 4xx Client Errors

**400 Bad Request**
```json
{
  "error": "Bad Request",
  "message": "Invalid session_id format"
}
```

**404 Not Found**
```json
{
  "error": "Not Found",
  "message": "Session not found"
}
```

### 5xx Server Errors

**500 Internal Server Error**
```json
{
  "error": "Internal Server Error",
  "message": "An unexpected error occurred"
}
```

## 3.7 API Client 구현 예시

```typescript
class GiftTaxApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }

  async createSession(clientIdHash?: string): Promise<Session> {
    const response = await fetch(`${this.baseUrl}/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ client_id_hash: clientIdHash }),
    });
    return response.json();
  }

  async sendMessage(sessionId: string, content: string): Promise<Message> {
    const response = await fetch(
      `${this.baseUrl}/sessions/${sessionId}/messages`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      }
    );
    return response.json();
  }

  async getMessages(
    sessionId: string,
    limit: number = 30,
    cursor?: string
  ): Promise<{ messages: Message[]; next_cursor: string | null }> {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (cursor) params.append('cursor', cursor);

    const response = await fetch(
      `${this.baseUrl}/sessions/${sessionId}/messages?${params}`
    );
    return response.json();
  }
}
```

---

## 부록: 구현 체크리스트

### Backend 구현 (ai/tools/gift_tax/calculator.py)
- [ ] `format_amount()` 함수 구현
- [ ] `get_tax_bracket_info()` 함수 구현
- [ ] `get_all_tax_brackets()` 함수 구현
- [ ] `calculate_gift_tax_simple()` 에 `calculation_breakdown` 추가
- [ ] Steps 1-6 모두 포함 (누락 없이)
- [ ] 유니코드 escape 문제 해결

### Prompt 개선 (ai/prompts/clarifying.py)
- [ ] `SYNTHESIS_PROMPT_V2` 작성
- [ ] 페르소나 가이드라인 추가
- [ ] Few-shot 예제 3개 추가
- [ ] 구조화된 응답 템플릿 명시

### Synthesis Node (ai/pipelines/langgraph_workflow.py)
- [ ] `_synthesize_response()` 개선
- [ ] Breakdown 정보 활용
- [ ] Fallback 응답 개선

### 테스트
- [ ] 10억 증여 시나리오
- [ ] 5억 배우자 증여 시나리오
- [ ] 50억 고액 증여 시나리오
- [ ] 응답 품질 검증
- [ ] API 응답 형식 검증

---

**문서 버전:** 1.0
**최종 수정일:** 2025-10-17
