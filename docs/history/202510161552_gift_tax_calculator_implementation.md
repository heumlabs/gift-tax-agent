# Gift Tax Calculator Implementation (Issue #21)

**Date**: 2025-10-16
**Branch**: `feature/gift-tax-calculation-tool`
**PR**: #33
**Status**: ✅ Completed

---

## Overview

국세청 증여세 간편계산기를 기반으로 증여세 계산 엔진을 구현했습니다. LangGraph Phase 2 통합을 위한 Tool 형태로 설계되었습니다.

---

## Key Decisions

### 1. Scope: 간편계산기 (9개 변수)

**Initial Scope (11 variables)**: 과거 증여 합산 로직 포함
**Final Scope (9 variables)**: 국세청 간편계산기 범위로 축소

**제외된 변수**:
- `past_gifts_value` (10년 내 과거 증여재산가액)
- `past_tax_paid` (기납부세액)

**Rationale**:
- 간편계산기는 10년 합산 과세를 지원하지 않음
- Phase 1에서는 단순 계산에 집중
- 사용자가 직접 입력하기 어려운 정보

### 2. CRITICAL: donor_relationship 기준 변경

**Initial Implementation**: 증여자(주는 사람) 기준
**Final Implementation**: 수증자(받는 사람) 기준 ✅

| 증여 케이스 | 변경 전 | 변경 후 |
|------------|---------|---------|
| 부모 → 자녀 | `직계비속` | `직계존속` |
| 자녀 → 부모 | `직계존속` | `직계비속` |
| 조부모 → 손자 | `직계비속` | `직계존속` |

**Discovery Process**:
1. CodeRabbit 리뷰: "코드베이스 전체가 '증여자 기준'으로 일관되나, 국세청 기준과 불일치"
2. 사용자 확인: "증여자와의 관계라고 쓰여있는데" (홈택스 화면)
3. 핵심 통찰: **"수증자가 세금 내나?"** → Yes!
4. 결론: 세금 내는 사람(수증자) 입장에서 관계 표현

**Impact**:
- BREAKING CHANGE
- 모든 코드, 테스트, 문서 전면 수정
- 9개 파일 변경

---

## Major Bugs & Fixes

### Bug 1: Non-resident Logic Missing

**Symptom**:
- 거주자: 과세표준 250,000,000원
- 비거주자: 과세표준 300,000,000원 (동일해야 하는데 차이 발생)

**Root Cause**:
`is_non_resident` 파라미터가 존재하지만 `get_base_deduction()`에서 사용되지 않음

**Fix**:
```python
def get_base_deduction(donor_relationship: str, is_minor: bool, is_non_resident: bool) -> int:
    # 비거주자는 공제 없음 (CRITICAL FIX!)
    if is_non_resident:
        return 0
    # ...
```

**Test Results**:
- 거주자 (부모→자녀 3억): 과세표준 2.5억, 세금 4천만원 ✓
- 비거주자 (부모→자녀 3억): 과세표준 3억, 세금 5천만원 ✓

### Bug 2: donor_relationship Interpretation Wrong

**Symptom**: 모든 테스트 케이스의 관계 값이 반대

**Discovery**:
- User: "증여자 기준이지" + 홈택스 양식 스크린샷
- 홈택스 예시: "아버지가 아들에게 증여하는 경우: 자(子)"
- 하지만 실제로는 "부(父)" 선택이 맞음 (아들 입장에서)

**Fix**: 전체 코드베이스 수정 (위 섹션 참조)

### Bug 3: Pydantic v2 Exception Type

**Symptom**: 테스트에서 `ValueError` 기대하지만 실제로는 `ValidationError` 발생

**Fix**:
```python
from pydantic import ValidationError  # v2.9.2
# Changed all validation tests to expect ValidationError
```

### Bug 4: Variable Name Inconsistency

**Symptom**:
- `ask_marriage_deduction` vs `marriage_deduction_amount`
- `ask_childbirth_deduction` vs `childbirth_deduction_amount`

**Fix**: 모든 변수명에 `_amount` suffix 일관성 유지

### Bug 5: secured_debt Conditional Logic Inconsistency

**Symptom**:
- 04-clarifying-strategy.md: "조건부"
- 실제 코드: `ask_secured_debt = True` (항상 질문)

**Fix**:
- Tier 3 테이블: "조건부" → "선택"
- Phase 1: 기본값 0 사용, Phase 2에서 맥락 기반 질문으로 개선 예정

---

## Implementation Details

### Architecture

```
ai/tools/gift_tax/
├── models.py           # Pydantic v2 입력/출력 모델
├── constants.py        # 공제액, 세율 상수
├── calculator.py       # 6단계 계산 로직
└── langchain_wrapper.py # LangGraph Tool 래퍼
```

### 6-Step Calculation Flow

1. **증여재산가액**: `gift_property_value - secured_debt`
2. **증여재산공제**: 기본공제 + 혼인공제 + 출산공제
3. **과세표준**: `증여재산가액 - 총공제액`
4. **산출세액**: 누진세율 적용 (10%~50%)
5. **할증세액**: 세대생략 시 30% 할증
6. **최종세액**: `산출세액 + 할증세액`

### Key Features

**Pydantic v2 Models**:
- `GiftTaxSimpleInput`: 9개 변수 검증
- `GiftTaxSimpleOutput`: TypedDict (LangGraph State 병합 가능)

**Validation Rules**:
- 채무액 ≤ 증여재산가액
- 증여일 ≤ 오늘
- 혼인/출산 공제 ≤ 1억원

**Special Cases**:
- 비거주자: 공제 0원
- 미성년자 특례: 직계존속으로부터 증여 시 2천만원 (5천만원 대신)
- 세대생략: 산출세액의 30% 할증

---

## Testing Strategy

### Test Coverage: 10/10 Passed ✅

**Calculation Tests (6)**:
1. 부모→성인자녀 1억 (기본 케이스)
2. 배우자 5억 (세금 0원)
3. 조부모→손자 2억 (세대생략 + 미성년자)
4. 부담부증여 (5억 부동산 - 2억 대출)
5. 비거주자 3억
6. 기타친족 1억

**Validation Tests (4)**:
1. 채무액 > 증여재산가액
2. 미래 증여일
3. 음수 증여가액
4. 혼인공제 > 1억원

### User Validation

국세청 홈택스 간편계산기와 직접 비교 검증:

| 시나리오 | 우리 계산 | 국세청 계산 | 일치 |
|---------|----------|------------|------|
| 부모→자녀 3억 (거주자) | 4천만원 | 4천만원 | ✓ |
| 부모→자녀 3억 (비거주자) | 5천만원 | 5천만원 | ✓ |
| 배우자 3억 | 0원 | 0원 | ✓ |
| 배우자 8억 | 3천만원 | 3천만원 | ✓ |
| 배우자 8억 (비거주자) | 1억8천만원 | 1억8천만원 | ✓ |

### Test Scenarios (CLI Tool)

`ai/tools/test_scenario.py` - 9개 시나리오:
1. 직접 입력 (커스텀)
2. 부모→성인자녀 3억 (거주자)
3. 부모→성인자녀 3억 (비거주자)
4. 배우자 3억 (거주자)
5. 배우자 3억 (비거주자)
6. 배우자 8억 (거주자)
7. 배우자 8억 (비거주자)
8. 조부모→손자 2억 (세대생략, 거주자)
9. 조부모→손자 2억 (세대생략, 비거주자)

---

## Code Review Resolution

### CodeRabbit Reviews: 11개 전부 해결 ✅

1. ✅ Pydantic ValidationError 타입 수정
2. ✅ README 변수 개수 수정 (11개 → 9개)
3. ✅ test_scenario.py import path 수정
4. ✅ 10년 합산 문서 제거
5. ✅ donor_relationship 테스트 케이스 수정
6. ✅ 비거주자 테스트 추가
7. ✅ 기타친족 테스트 추가
8. ✅ 곱셈 기호 호환성 (× → *)
9. ✅ asset_type undefined 변수 제거
10. ✅ donor_relationship 의미 명확화 (수증자 기준)
11. ✅ 변수명 일관성 (_amount suffix)

---

## Documentation

### Created/Updated Files

**Specification**:
- `docs/prd_detail/ai-logic/05-gift-tax-calculator-spec.md` (v2.0)
  - 9개 변수 정의
  - 6단계 계산 로직
  - 4개 테스트 케이스
  - 수증자 기준 명확화

**Clarifying Strategy**:
- `docs/prd_detail/ai-logic/04-clarifying-strategy.md`
  - 3 Tier 질문 전략
  - RELATIONSHIP_MAPPING 테이블 (수증자 기준)
  - 조건부 질문 규칙

**Usage Guide**:
- `ai/tools/README.md`
  - 기본 사용법
  - Pydantic 모델 사용법
  - LangGraph 통합 예시

---

## Commit History

```
3fca654 Initial commit (Issue #21 spec)
[... 개발 과정 ...]
262b098 docs: fix variable naming consistency and conditional logic clarity
d0d9b05 fix: change donor_relationship from donor to recipient perspective (BREAKING)
```

**Key Commits**:
1. **Scope Reduction**: 11개 → 9개 변수 (10년 합산 제외)
2. **Non-resident Fix**: 공제 0원 로직 추가
3. **donor_relationship Perspective Fix**: 증여자 기준 → 수증자 기준 (BREAKING)

---

## Next Steps (Phase 2)

### LangGraph Integration (Issue #22)

**Planned Features**:
1. **Clarifying Loop**: 누락 변수 질문 전략 구현
2. **RAG Integration**: 계산 불가 시 문서 검색
3. **State Management**: LangGraph State에 계산 결과 저장
4. **Context-aware Questions**: `secured_debt` 조건부 질문 (부동산 언급 시)

**Architecture**:
```python
State = {
    "messages": [...],
    "collected_parameters": {...},
    "metadata": {
        "calculation": GiftTaxSimpleOutput,
        "missing_parameters": [...],
    }
}
```

---

## Lessons Learned

### 1. 국세청 기준이 절대적 진리

- 초기 가정(증여자 기준)이 완전히 틀렸음
- 실제 홈택스 화면과 직접 비교 필수
- "누가 세금 내나?"가 핵심 질문

### 2. 문서와 코드의 일관성

- 작은 불일치도 큰 버그로 이어짐
- 변수명, 주석, 문서 모두 동기화 필수
- CodeRabbit 리뷰가 많은 불일치 발견

### 3. 테스트 주도 개발의 중요성

- 국세청 계산기와 실시간 비교 테스트
- 모든 엣지 케이스 커버 (비거주자, 세대생략 등)
- CLI 테스트 도구로 빠른 검증

### 4. Breaking Change 관리

- donor_relationship 변경은 BREAKING CHANGE
- 명확한 커밋 메시지와 문서화
- 모든 영향 파일 한번에 수정

---

## References

- **국세청 홈택스**: https://hometax.go.kr/websquare/websquare.html?w2xPath=/ui/pp/index_pp.xml&menuCd=UTERNAAU42
- **Issue #21**: [링크]
- **PR #33**: [링크]
- **관련 법령**: 상속세 및 증여세법 제53조, 제54조, 제57조

---

## Contributors

- AI Agent: Implementation & Documentation
- 19kim: Review, Testing, Direction

**Total Time**: ~8 hours
**Lines Changed**: 9 files, 108 insertions(+), 104 deletions(-)
