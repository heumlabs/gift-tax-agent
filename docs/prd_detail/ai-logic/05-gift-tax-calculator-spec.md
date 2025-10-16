# 국세청 증여세 간편계산기 스펙

**문서 버전**: v2.0
**작성일**: 2025-10-16
**레퍼런스**: 국세청 홈택스 증여세 간편계산 서비스
**연관 문서**: `ai-logic/functional-spec.md`

---

## 1. 개요

본 문서는 **국세청 증여세 간편계산기**를 단일 진실 소스(Single Source of Truth)로 삼아, 슈킹 AI의 **증여세 계산 엔진**을 정의합니다.

### 문서 범위
- ✅ 증여세 계산 로직 (6단계)
- ✅ 입력 변수 정의 및 검증 규칙
- ✅ 공제액, 세율, 할증 규칙
- ✅ 계산 결과 출력 형식
- ✅ 테스트 케이스 4개
- ❌ Clarifying 질문 전략 (별도 문서: `ai-logic/04-clarifying-strategy.md`)
- ❌ LangGraph 통합 (Phase 2)

### 핵심 원칙
- **국세청 간편계산기 = 우리의 TaxCalculationEngine**
- **결정론적 계산**: 동일 입력 → 동일 출력 보장
- **검증 가능성**: 각 계산 단계를 steps[] 배열로 기록

---

## 2. 용어 정의

국세청 간편계산기에서 정의한 용어를 그대로 사용합니다.

| 용어 | 정의 |
|------|------|
| **수증자** | 증여를 받은 자 |
| **증여자** | 증여를 하는 자 |
| **거주자** | 국내에 주소를 두거나 183일 이상 거소를 둔 자 |
| **비거주자** | 거주자가 아닌 자 |
| **미성년자** | 증여일 현재 만 19세 미만인 자 |
| **세대생략 증여** | 조부모가 손자에게 증여하는 경우 (단, 수증자의 부모가 사망한 경우 제외) |

---

## 3. 입력 변수 정의

### 3.1. 변수 목록 (총 9개)

| 변수명 | 타입 | 필수 | 기본값 | 설명 |
|--------|------|------|--------|------|
| `gift_date` | `date` | ✅ | - | 증여일자 |
| `donor_relationship` | `enum` | ✅ | - | 증여자와의 관계 (증여자 기준, 예: 부모→자녀=직계비속) |
| `gift_property_value` | `int` | ✅ | - | 증여받은 재산가액 (원) |
| `is_generation_skipping` | `bool` | ✅ | `false` | 세대생략 증여 여부 |
| `is_minor_recipient` | `bool` | ✅ | `false` | 수증자 미성년자 여부 |
| `is_non_resident` | `bool` | ✅ | `false` | 수증자 비거주자 여부 |
| `marriage_deduction_amount` | `int` | 옵션 | `0` | 혼인공제액 (최대 1억) |
| `childbirth_deduction_amount` | `int` | 옵션 | `0` | 출산공제액 (최대 1억) |
| `secured_debt` | `int` | 옵션 | `0` | 담보채무액 |

### 3.2. donor_relationship 허용값

```python
DonorRelationship = Literal[
    "배우자",      # spouse (배우자→배우자)
    "직계존속",    # lineal_ascendant (자녀→부모)
    "직계비속",    # lineal_descendant (부모→자녀, 조부모→손자)
    "기타친족",    # other_relative
]
```

**주의**: 증여자 기준입니다.
- 아버지가 아들에게 증여 → 직계비속 (자)
- 아들이 아버지에게 증여 → 직계존속 (부)

### 3.3. 변수 검증 규칙

```python
from pydantic import BaseModel, Field, field_validator
from datetime import date
from typing import Literal

class GiftTaxSimpleInput(BaseModel):
    """국세청 증여세 간편계산 입력 모델"""

    # Tier 1: 기본 정보
    gift_date: date = Field(..., description="증여일자")
    donor_relationship: Literal["배우자", "직계존속", "직계비속", "기타친족"]
    gift_property_value: int = Field(..., gt=0, description="증여받은 재산가액 (원)")

    # Tier 2: 특례 판단
    is_generation_skipping: bool = Field(default=False, description="세대생략 증여 여부")
    is_minor_recipient: bool = Field(default=False, description="수증자 미성년자 여부")
    is_non_resident: bool = Field(default=False, description="수증자 비거주자 여부")

    # Tier 3: 공제 및 채무
    marriage_deduction_amount: int = Field(default=0, ge=0, le=100_000_000, description="혼인공제액")
    childbirth_deduction_amount: int = Field(default=0, ge=0, le=100_000_000, description="출산공제액")
    secured_debt: int = Field(default=0, ge=0, description="담보채무액")

    @field_validator('secured_debt')
    @classmethod
    def validate_debt(cls, v, info):
        """채무액이 증여재산가액을 초과할 수 없음"""
        if 'gift_property_value' in info.data and v > info.data['gift_property_value']:
            raise ValueError("채무액이 증여재산가액보다 클 수 없습니다")
        return v

    @field_validator('gift_date')
    @classmethod
    def validate_gift_date(cls, v):
        """증여일은 과거 또는 오늘만 허용"""
        if v > date.today():
            raise ValueError("증여일은 미래 날짜일 수 없습니다")
        return v
```

---

## 4. 공제액 및 세율 규칙

### 4.1. 기본 공제

```python
GIFT_DEDUCTION_BASE = {
    "배우자": 600_000_000,        # 6억원
    "직계존속": 50_000_000,       # 5천만원 (부모→자녀)
    "직계비속": 50_000_000,       # 5천만원 (자녀→부모)
    "기타친족": 10_000_000,       # 1천만원
}
```

### 4.2. 미성년자 특례

```python
MINOR_DEDUCTION = 20_000_000    # 2천만원
# 미성년자가 직계존속으로부터 증여받는 경우 5천만원 대신 적용
```

### 4.3. 혼인/출산 공제

```python
MARRIAGE_DEDUCTION_LIMIT = 100_000_000   # 1억원
CHILDBIRTH_DEDUCTION_LIMIT = 100_000_000 # 1억원
# 기본 공제와 별도로 추가 공제
```

### 4.4. 세율 구조 (2024년 기준)

```python
TAX_BRACKETS = [
    {"limit": 100_000_000, "rate": 0.10, "progressive_deduction": 0},
    {"limit": 500_000_000, "rate": 0.20, "progressive_deduction": 10_000_000},
    {"limit": 1_000_000_000, "rate": 0.30, "progressive_deduction": 60_000_000},
    {"limit": 3_000_000_000, "rate": 0.40, "progressive_deduction": 160_000_000},
    {"limit": float('inf'), "rate": 0.50, "progressive_deduction": 460_000_000},
]
```

### 4.5. 세대생략 할증

```python
GENERATION_SKIPPING_SURTAX_RATE = 0.30  # 30% 할증
# 조부모→손자 증여 시 산출세액의 30%를 할증
# 단, 수증자의 부모가 사망한 경우 제외
```

---

## 5. 계산 로직

### 5.1. 전체 계산 흐름

```
[입력: GiftTaxSimpleInput]
  ↓
① 증여재산가액 = 증여받은 재산가액 - 채무액
  ↓
② 증여재산공제 = 기본공제 + 혼인공제 + 출산공제
  ↓
③ 과세표준 = 증여재산가액 - 증여재산공제
  ↓
④ 산출세액 = 과세표준 × 세율 - 누진공제
  ↓
⑤ 세대생략 할증세액 = 산출세액 × 30% (해당 시)
  ↓
⑥ 증여세액 = 산출세액 + 할증세액
  ↓
[출력: GiftTaxSimpleOutput]
```

### 5.2. 계산 함수 시그니처

```python
from datetime import date, timedelta
from typing import TypedDict

class CalculationStep(TypedDict):
    """계산 단계 상세"""
    step: int
    description: str
    formula: str
    value: int
    detail: str

class GiftTaxSimpleOutput(TypedDict):
    """계산 결과 출력"""
    steps: list[CalculationStep]
    gift_value: int
    total_deduction: int
    taxable_base: int
    calculated_tax: int
    surtax: int
    final_tax: int
    warnings: list[str]

def calculate_gift_tax_simple(
    gift_date: date,
    donor_relationship: str,
    is_generation_skipping: bool,
    is_minor_recipient: bool,
    is_non_resident: bool,
    gift_property_value: int,
    marriage_deduction_amount: int = 0,
    childbirth_deduction_amount: int = 0,
    secured_debt: int = 0,
    past_gifts_value: int = 0,
    past_tax_paid: int = 0,
) -> GiftTaxSimpleOutput:
    """국세청 증여세 간편계산 로직"""
    ...
```

### 5.3. 구현 코드

```python
def calculate_gift_tax_simple(
    gift_date: date,
    donor_relationship: str,
    is_generation_skipping: bool,
    is_minor_recipient: bool,
    is_non_resident: bool,
    gift_property_value: int,
    marriage_deduction_amount: int = 0,
    childbirth_deduction_amount: int = 0,
    secured_debt: int = 0,
    past_gifts_value: int = 0,
    past_tax_paid: int = 0,
) -> GiftTaxSimpleOutput:
    """국세청 증여세 간편계산 로직"""
    steps = []

    # ① 증여재산가액
    gift_value = gift_property_value - secured_debt
    steps.append({
        "step": 1,
        "description": "증여재산가액",
        "formula": "증여받은 재산가액 - 채무액",
        "value": gift_value,
        "detail": f"{gift_property_value:,}원 - {secured_debt:,}원"
    })

    # ② 증여재산공제
    base_deduction = get_base_deduction(donor_relationship, is_minor_recipient)
    marriage_deduction = min(marriage_deduction_amount, MARRIAGE_DEDUCTION_LIMIT)
    childbirth_deduction = min(childbirth_deduction_amount, CHILDBIRTH_DEDUCTION_LIMIT)
    total_deduction = base_deduction + marriage_deduction + childbirth_deduction

    steps.append({
        "step": 2,
        "description": "증여재산공제",
        "formula": "기본공제 + 혼인공제 + 출산공제",
        "value": total_deduction,
        "detail": f"기본 {base_deduction:,}원 + 혼인 {marriage_deduction:,}원 + 출산 {childbirth_deduction:,}원"
    })

    # ③ 과세표준 (10년 합산)
    taxable_base = (gift_value + past_gifts_value) - total_deduction

    steps.append({
        "step": 3,
        "description": "과세표준",
        "formula": "(증여재산가액 + 사전증여재산) - 증여재산공제",
        "value": max(taxable_base, 0),
        "detail": f"({gift_value:,}원 + {past_gifts_value:,}원) - {total_deduction:,}원"
    })

    if taxable_base <= 0:
        return {
            "steps": steps,
            "gift_value": gift_value,
            "total_deduction": total_deduction,
            "taxable_base": 0,
            "calculated_tax": 0,
            "surtax": 0,
            "final_tax": 0,
            "warnings": ["과세표준이 0 이하이므로 납부할 증여세가 없습니다."]
        }

    # ④ 산출세액
    calculated_tax = apply_tax_rate(taxable_base)

    steps.append({
        "step": 4,
        "description": "산출세액",
        "formula": "과세표준 × 세율 - 누진공제",
        "value": calculated_tax,
        "detail": get_tax_rate_detail(taxable_base)
    })

    # ⑤ 세대생략 할증
    surtax = 0
    if is_generation_skipping:
        surtax = int(calculated_tax * GENERATION_SKIPPING_SURTAX_RATE)
        steps.append({
            "step": 5,
            "description": "세대생략 할증세액 (30%)",
            "formula": "산출세액 × 30%",
            "value": surtax,
            "detail": "조부모→손자 증여로 30% 할증 적용"
        })

    # ⑥ 최종 증여세액
    final_tax = calculated_tax + surtax - past_tax_paid

    steps.append({
        "step": 6,
        "description": "최종 증여세액",
        "formula": "(산출세액 + 할증세액) - 사전증여세액",
        "value": max(final_tax, 0),
        "detail": f"({calculated_tax:,}원 + {surtax:,}원) - {past_tax_paid:,}원"
    })

    # 주의사항
    warnings = generate_warnings(
        gift_date=gift_date,
        is_generation_skipping=is_generation_skipping,
        past_gifts_value=past_gifts_value,
    )

    return {
        "steps": steps,
        "gift_value": gift_value,
        "total_deduction": total_deduction,
        "taxable_base": max(taxable_base, 0),
        "calculated_tax": calculated_tax,
        "surtax": surtax,
        "final_tax": max(final_tax, 0),
        "warnings": warnings,
    }


def get_base_deduction(donor_relationship: str, is_minor: bool) -> int:
    """기본 공제액 계산"""
    if is_minor and donor_relationship == "직계존속":
        return MINOR_DEDUCTION  # 2천만원
    return GIFT_DEDUCTION_BASE.get(donor_relationship, 10_000_000)


def apply_tax_rate(taxable_base: int) -> int:
    """세율 적용 및 산출세액 계산"""
    for bracket in TAX_BRACKETS:
        if taxable_base <= bracket["limit"]:
            return int(
                taxable_base * bracket["rate"] - bracket["progressive_deduction"]
            )
    return 0


def get_tax_rate_detail(taxable_base: int) -> str:
    """세율 적용 상세 설명"""
    for bracket in TAX_BRACKETS:
        if taxable_base <= bracket["limit"]:
            rate_percent = int(bracket["rate"] * 100)
            deduction = bracket["progressive_deduction"]
            return f"{taxable_base:,}원 × {rate_percent}% - {deduction:,}원"
    return ""


def generate_warnings(gift_date: date, is_generation_skipping: bool, past_gifts_value: int) -> list[str]:
    """주의사항 생성"""
    warnings = []

    # 신고 기한
    filing_deadline = gift_date + timedelta(days=90)
    warnings.append(f"증여일로부터 3개월 이내({filing_deadline.strftime('%Y년 %m월 %d일')}까지) 신고해야 합니다.")

    # 기한 후 신고 가산세
    warnings.append("기한 후 신고 시 가산세 20%가 부과됩니다.")

    # 10년 합산 안내
    if past_gifts_value > 0:
        warnings.append("향후 10년 이내 동일인으로부터 추가 증여 시 이번 증여와 합산하여 과세됩니다.")
    else:
        warnings.append("향후 10년 이내 동일인으로부터 추가 증여 시 합산 과세됩니다.")

    # 세대생략 할증 안내
    if is_generation_skipping:
        warnings.append("세대를 건너뛴 증여로 30% 할증이 적용되었습니다.")

    return warnings
```

---

## 6. 테스트 케이스

### Case 1: 기본 케이스 (부모→성인 자녀, 현금 1억)

**입력**:
```python
{
    "gift_date": date(2025, 10, 15),
    "donor_relationship": "직계존속",
    "is_generation_skipping": False,
    "is_minor_recipient": False,
    "is_non_resident": False,
    "gift_property_value": 100_000_000,
    "past_gifts_value": 0,
}
```

**예상 결과**:
```python
{
    "gift_value": 100_000_000,
    "total_deduction": 50_000_000,
    "taxable_base": 50_000_000,
    "calculated_tax": 5_000_000,
    "surtax": 0,
    "final_tax": 5_000_000,
}
```

**계산 근거**:
- 증여재산가액: 1억원
- 기본공제: 5천만원 (직계존속 성인)
- 과세표준: 5천만원
- 산출세액: 5천만원 × 10% = 500만원

---

### Case 2: 배우자 증여 (5억)

**입력**:
```python
{
    "gift_date": date(2025, 10, 15),
    "donor_relationship": "배우자",
    "gift_property_value": 500_000_000,
}
```

**예상 결과**:
```python
{
    "gift_value": 500_000_000,
    "total_deduction": 600_000_000,
    "taxable_base": 0,
    "calculated_tax": 0,
    "surtax": 0,
    "final_tax": 0,
}
```

**계산 근거**:
- 증여재산가액: 5억원
- 기본공제: 6억원 (배우자)
- 과세표준: 0원 (5억 - 6억 = 음수 → 0)

---

### Case 3: 세대생략 증여 (조부모→손자, 2억)

**입력**:
```python
{
    "gift_date": date(2025, 10, 15),
    "donor_relationship": "직계존속",
    "is_generation_skipping": True,
    "is_minor_recipient": True,
    "gift_property_value": 200_000_000,
}
```

**예상 결과**:
```python
{
    "gift_value": 200_000_000,
    "total_deduction": 20_000_000,
    "taxable_base": 180_000_000,
    "calculated_tax": 26_000_000,
    "surtax": 7_800_000,
    "final_tax": 33_800_000,
}
```

**계산 근거**:
- 증여재산가액: 2억원
- 기본공제: 2천만원 (미성년자 특례)
- 과세표준: 1.8억원
- 산출세액: 1.8억 × 20% - 1천만원 = 2,600만원
- 할증세액: 2,600만원 × 30% = 780만원
- 최종세액: 3,380만원

---

### Case 4: 부담부 증여 (부동산 5억, 대출 2억)

**입력**:
```python
{
    "gift_date": date(2025, 10, 15),
    "donor_relationship": "직계존속",
    "gift_property_value": 500_000_000,
    "secured_debt": 200_000_000,
}
```

**예상 결과**:
```python
{
    "gift_value": 300_000_000,
    "total_deduction": 50_000_000,
    "taxable_base": 250_000_000,
    "calculated_tax": 35_000_000,
    "surtax": 0,
    "final_tax": 35_000_000,
}
```

**계산 근거**:
- 증여재산가액: 5억 - 2억 = 3억원
- 기본공제: 5천만원
- 과세표준: 2.5억원
- 산출세액: 2.5억 × 20% - 1천만원 = 4,000만원

---

## 7. 구현 체크리스트

### Phase 1 (본 Issue #21)
- [ ] `GiftTaxSimpleInput` Pydantic 모델 구현
- [ ] `calculate_gift_tax_simple()` 함수 구현
- [ ] 헬퍼 함수 구현 (`get_base_deduction`, `apply_tax_rate`, `generate_warnings`)
- [ ] 테스트 케이스 4개 작성 및 검증 (pytest)
- [ ] Agent Tool 인터페이스 구현 (LangChain Tool)

### Phase 2 (별도 Issue)
- [ ] LangGraph 기본 Workflow 구성
- [ ] Clarifying 노드와 계산 엔진 통합

### Phase 3 (별도 Issue)
- [ ] RAG 검색 및 citation 통합
- [ ] 전체 파이프라인 E2E 테스트

---

## 부록: 참고 자료

- 국세청 홈택스 증여세 간편계산: https://www.hometax.go.kr
- 상속세및증여세법: `.dataset/ko-law-parser/law/상속세및증여세법.json`
- 상속세및증여세법 시행령: `.dataset/ko-law-parser/law/상속세및증여세법시행령.json`
