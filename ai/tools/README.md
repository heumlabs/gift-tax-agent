# AI Tools

LLM Agent가 사용할 수 있는 도구 모음입니다.

## 📦 설치된 Tools

### 1. 증여세 계산 Tool (`calculate_gift_tax_simple`)

국세청 증여세 간편계산기 기준으로 증여세를 정확히 계산합니다.

**위치**: `ai/tools/gift_tax/`

**구성**:
- `models.py`: Pydantic 입출력 모델 (9개 변수)
- `calculator.py`: 6단계 계산 로직
- `constants.py`: 공제액, 세율 등 상수

**LangGraph 통합**: `ai/tools/langchain_wrapper.py`

## 🚀 사용법

### 직접 호출

```python
from datetime import date
from ai.tools.gift_tax.calculator import calculate_gift_tax_simple

result = calculate_gift_tax_simple(
    gift_date=date(2025, 10, 15),
    donor_relationship="직계비속",  # 부모→자녀 (증여자 기준)
    gift_property_value=100_000_000,
)

print(f"최종 세액: {result['final_tax']:,}원")
# 출력: 최종 세액: 5,000,000원
```

### Pydantic 모델 사용

```python
from ai.tools.gift_tax.models import GiftTaxSimpleInput
from ai.tools.gift_tax.calculator import calculate_gift_tax_simple

input_data = GiftTaxSimpleInput(
    gift_date=date(2025, 10, 15),
    donor_relationship="배우자",
    gift_property_value=500_000_000,
)

result = calculate_gift_tax_simple(**input_data.model_dump())
```

### LangGraph에서 사용 (Phase 2)

```python
from ai.tools import calculate_gift_tax_simple

# LangGraph가 자동으로 함수를 Tool로 변환
tools = [calculate_gift_tax_simple]

# Agent 생성 시 tools 전달
agent = create_react_agent(model=llm, tools=tools)
```

## ✅ 테스트

```bash
# 전체 테스트 실행
.venv/bin/python -m pytest ai/tests/tools/ -v

# 커버리지 포함
.venv/bin/python -m pytest ai/tests/tools/ --cov=ai.tools --cov-report=term-missing
```

## 📊 계산 결과 구조

```python
{
    "steps": [
        {
            "step": 1,
            "description": "증여재산가액",
            "formula": "증여받은 재산가액 - 채무액",
            "value": 100000000,
            "detail": "100,000,000원 - 0원"
        },
        # ... 6 steps
    ],
    "gift_value": 100000000,
    "total_deduction": 50000000,
    "taxable_base": 50000000,
    "calculated_tax": 5000000,
    "surtax": 0,
    "final_tax": 5000000,
    "warnings": [
        "증여일로부터 3개월 이내(2026년 01월 13일까지) 신고해야 합니다.",
        "기한 후 신고 시 가산세 20%가 부과됩니다."
    ]
}
```

## 🔗 관련 문서

- [Issue #21](https://github.com/heumlabs/gift-tax-agent/issues/21) - 증여세 계산 Tool 구현 (Phase 1)
- [Issue #22](https://github.com/heumlabs/gift-tax-agent/issues/22) - LangGraph Workflow 구성 (Phase 2)
- [증여세 계산기 스펙](../../docs/prd_detail/ai-logic/05-gift-tax-calculator-spec.md)
