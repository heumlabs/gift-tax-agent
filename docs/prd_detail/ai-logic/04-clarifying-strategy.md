# Clarifying & Variable-Gathering Strategy

**문서 버전**: v2.1
**작성일**: 2025-10-16
**레퍼런스**: `05-gift-tax-calculator-spec.md` (계산 로직 및 변수 정의)
**연관 문서**: `ai-logic.md`, `01-data-pipeline.md`, `03-message-format.md`

## 1. 범위 및 레퍼런스

이 문서는 **국세청 증여세 간편계산기**를 레퍼런스로 삼아, Clarifying 질문을 통해 필수 변수를 수집하는 전략을 정의합니다.

### 핵심 원칙
- **국세청 간편계산기 필수 입력 항목 = 우리의 필수 변수**
- **입력 항목 누락 시 = Clarifying 질문 생성**
- **모든 필수 변수 수집 완료 = TaxCalculationEngine 호출**

상세 계산 로직과 변수 정의는 `05-gift-tax-calculator-spec.md`를 참조하세요.

### Agent Guardrails 연계
- **Guided Conversation** (`docs/prd_detail/ai-logic/agent.md:16`) — Clarifying 루프 설계를 통해 필수 변수를 단계적으로 확보하고 범위 밖 요청을 조기에 차단한다.
- **Compliance & Privacy** (`docs/prd_detail/ai-logic/agent.md:17`) — 민감정보 탐지 시 즉시 대응하고, “정보 제공용” 고지를 포함한 응답 정책을 유지한다.
- **Knowledge Fidelity** (`docs/prd_detail/ai-logic/agent.md:15`) — Clarifying 과정에서 참조한 법령 스니펫을 `clarifying_context`에 기록하여 추후 답변의 근거로 재사용한다.

## 2. 필수 변수 체크리스트 (국세청 간편계산기 기준)

### Tier 1: 필수 기본 정보 (우선 수집)

| 변수명 | 타입 | 설명 | Clarifying 질문 예시 |
|--------|------|------|---------------------|
| `gift_date` | `date` | 증여일자 | "증여일이 언제인가요?" |
| `donor_relationship` | `enum` | 증여자와의 관계 (배우자/직계존속/직계비속/기타친족) | "증여하시는 분과의 관계가 어떻게 되시나요? (예: 부모님, 배우자 등)" |
| `gift_property_value` | `int` | 증여받은 재산가액 (원) | "증여받으신 재산의 가액이 얼마인가요?" |

### Tier 2: 특례 판단 정보

| 변수명 | 타입 | 설명 | Clarifying 질문 예시 |
|--------|------|------|---------------------|
| `is_generation_skipping` | `boolean` | 세대생략 증여 여부 (조부모→손자) | "조부모님께서 손자/손녀에게 직접 증여하시나요? (부모님이 생존해 계신 경우)" |
| `is_minor_recipient` | `boolean` | 수증자 미성년자 여부 (만 19세 미만) | "증여받으시는 분이 미성년자(만 19세 미만)인가요?" |
| `is_non_resident` | `boolean` | 수증자 비거주자 여부 | "증여받으시는 분이 해외에 거주 중이신가요? (1년 중 183일 이상)" |

### Tier 3: 공제 및 합산 정보

| 변수명 | 타입 | 필수 | 설명 | Clarifying 질문 예시 |
|--------|------|------|------|---------------------|
| `past_gifts_value` | `int` | ✅ | 10년 이내 동일인 증여재산 합계 | "최근 10년 내 같은 분에게서 증여받은 적이 있나요? 있다면 총 얼마인가요?" |
| `marriage_deduction_amount` | `int` | 조건부 | 혼인공제액 (최대 1억) | "혼인 전후 2년 이내 증여받으신 것인가요?" |
| `childbirth_deduction_amount` | `int` | 조건부 | 출산공제액 (최대 1억) | "자녀 출생 2년 이내 증여받으신 것인가요?" |
| `secured_debt` | `int` | 조건부 | 담보채무액 | "증여받은 재산에 담보대출이나 임대보증금이 있나요?" |
| `past_tax_paid` | `int` | 조건부 | 사전 증여세액 | "이전 증여 시 납부한 세금이 있나요?" |

### 질문 순서 원칙

1. **Tier 1 → Tier 2 → Tier 3** 순서로 질문
2. 한 번에 **1~2개 질문**만 묶어서 전달
3. 조건부 질문은 **해당 조건 충족 시에만** 질문

### 조건부 질문 규칙

```python
# 혼인공제 질문 조건
if donor_relationship in ["직계존속", "직계비속"]:
    ask_marriage_deduction = True

# 출산공제 질문 조건
if donor_relationship in ["직계존속", "직계비속"]:
    ask_childbirth_deduction = True

# 채무 질문 조건
# 부동산, 건물 등 담보 가능 자산인 경우에만
if asset_type in ["부동산", "건물", "상업용건물"]:
    ask_secured_debt = True

# 사전증여세액 질문 조건
if past_gifts_value > 0:
    ask_past_tax_paid = True
```

## 3. Clarifying 질문 템플릿

각 변수별로 사용자 친화적인 질문 템플릿을 제공합니다.

### 3.1. 질문 작성 원칙
1. **용어 설명 우선**: 전문 용어는 반드시 쉬운 설명과 함께 제공
2. **구체적 예시**: 사용자가 어떻게 답변해야 하는지 예시 제공
3. **시각적 구분**: 💡 (팁/설명), ⚠️ (주의사항) 아이콘 활용
4. **한 번에 1~2개**: 너무 많은 질문 지양

### 3.2. Tier 1 질문 (필수 기본정보)

**gift_date (증여일자)**
```
증여일이 언제인가요?

💡 증여세는 증여일을 기준으로 신고 기한(3개월)과 10년 합산 과세가 결정됩니다.
예시: 2025년 10월 15일, 올해 3월
```

**donor_relationship (증여자와의 관계)**
```
증여하시는 분과의 관계가 어떻게 되시나요?

💡 관계에 따라 공제 한도가 다릅니다:
• 배우자: 6억원
• 부모/자녀: 5천만원
• 기타 친족: 1천만원

선택지: 배우자, 부모님, 자녀, 조부모, 기타
```

**gift_property_value (증여재산가액)**
```
증여받으신 재산의 가액이 얼마인가요?

💡 평가 기준:
• 부동산: 최근 6개월 매매가 또는 공시지가
• 주식: 상장(2개월 평균), 비상장(평가액)

예시: 5억원, 200,000,000원
```

### 3.3. Tier 2 질문 (특례 판단)

**is_generation_skipping (세대생략 증여)**
```
조부모님께서 손자/손녀에게 직접 증여하시는 경우인가요?

⚠️ 세대를 건너뛴 증여: 산출세액의 30% 할증
(단, 부모님이 이미 사망하신 경우 제외)

선택지: 예 / 아니오
```

**is_minor_recipient (미성년자 여부)**
```
증여받으시는 분이 미성년자(만 19세 미만)인가요?

💡 미성년자 공제: 직계존속으로부터 증여 시 2천만원
(성인: 5천만원)

선택지: 예 / 아니오
```

**is_non_resident (비거주자 여부)**
```
증여받으시는 분이 해외에 거주 중이신가요?

💡 비거주자: 1년 중 183일 이상 해외 거주

선택지: 예 / 아니오
```

### 3.4. Tier 3 질문 (공제 및 합산)

**past_gifts_value (10년 합산)**
```
최근 10년 내 같은 분에게서 증여받은 적이 있나요?

💡 증여세는 동일인으로부터 받은 증여를 10년간 합산하여 계산합니다.

선택지: 없음(0원) / 있음(금액 입력)
```

**marriage_deduction_amount (혼인공제)**
```
혼인 전후 2년 이내에 증여받으신 것인가요?

💡 혼인일 전후 각 2년(총 4년) 이내 증여 시 최대 1억원 추가 공제

선택지: 예(금액 입력) / 아니오
```

**childbirth_deduction_amount (출산공제)**
```
자녀 출생 2년 이내에 증여받으신 것인가요?

💡 자녀 출생일로부터 2년 이내 증여 시 최대 1억원 추가 공제

선택지: 예(금액 입력) / 아니오
```

**secured_debt (담보채무)**
```
증여받은 재산에 담보대출이나 임대보증금이 있나요?

💡 부담부 증여: 증여자의 채무를 수증자가 인수하는 경우
예시: 5억 아파트 + 2억 대출 = 실제 증여가액 3억

선택지: 없음(0원) / 있음(금액 입력)
```

**past_tax_paid (사전 증여세액)**
```
이전에 증여받으실 때 납부한 증여세가 있나요?

💡 10년 합산 과세 시, 이전 납부 세액은 공제됩니다.

선택지: 없음(0원) / 있음(금액 입력)
```

## 4. Clarifying 루프 설계

### 4.1. 전체 흐름

```
사용자 질문
    ↓
① 의도 분석 (증여세 계산 의도 확인)
    ↓
② 초기 엔티티 추출 (질문에서 변수 파싱)
    ↓
③ 필수 변수 체크 (Tier 1 → Tier 2 → Tier 3)
    ↓
④ missing_parameters 있음?
    ├─ YES → Clarifying 질문 생성 → ②로 돌아감
    └─ NO → TaxCalculationEngine 호출
```

### 4.2. 단계별 처리 로직

**Step 1: 초기 분석**
- 사용자 첫 질문에서 의도 분류 (gift_tax, inheritance_tax, general_info)
- LLM으로 초기 엔티티 추출
  - 예: "부모님께 1억 받았어요" → `{donor_relationship: "직계존속", gift_property_value: 100000000}`

**Step 2: 필수 변수 체크**
- Tier 1 필수 변수 확인: gift_date, donor_relationship, gift_property_value
- Tier 2 기본값 가능: is_generation_skipping (false), is_minor_recipient (false), is_non_resident (false)
- Tier 3 필수: past_gifts_value
- 조건부 변수: 관계/자산 유형에 따라 추가 질문

**Step 3: Clarifying 질문 생성**
- 누락 변수를 Tier 순서대로 정렬
- 상위 1~2개만 질문 (한 번에 너무 많이 묻지 않기)
- 질문 템플릿 적용 (위 3.2~3.4 참조)

**Step 4: 사용자 응답 처리**
- 응답을 파싱하여 collected_parameters에 추가
- 다시 Step 2로 돌아가 누락 변수 재확인

### 4.3. 종료 조건

**계산 가능 조건 (TaxCalculationEngine 호출)**
- Tier 1 필수 변수 모두 수집 완료
- Tier 2 변수 수집 또는 기본값 사용
- Tier 3 필수 변수(past_gifts_value) 수집 완료

**계산 불가 → RAG 안내**
- 3회 이상 동일 변수 수집 실패
- 사용자가 "모른다/확인 중" 응답
- 일반 정보 제공 모드로 전환

**대화 종료**
- 사용자 중단 요청
- Out-of-scope 주제 감지
- 세션 보존 후 종료

## 5. 메시지 메타데이터 매핑

Clarifying 단계에서 사용되는 정보는 `messages.metadata`에 저장합니다.

### 5.1. 저장 항목

| 필드 | 설명 | 예시 |
|------|------|------|
| `intent` | 의도 분류 | `gift_tax`, `inheritance_tax`, `general_info` |
| `collected_parameters` | 현재까지 수집된 변수 | `{"donor_relationship": "직계존속", "gift_property_value": 100000000}` |
| `missing_parameters` | 누락된 필수 변수 목록 | `[{"name": "gift_date", "reason": "not_provided"}]` |
| `clarifying_history` | 질문/응답 로그 (선택) | `[{"question": "증여일이 언제인가요?", "timestamp": "..."}]` |
| `clarifying_context` | RAG 참조 스니펫 | `[{"source_id": 123, "summary": "10년 합산 설명"}]` |

### 5.2. missing_parameters.reason 값

- `not_provided`: 사용자가 제공하지 않음
- `ambiguous`: 모호한 응답
- `user_unknown`: 사용자가 모른다고 응답

## 6. LangGraph 통합

Clarifying 전략은 LangGraph 워크플로우의 첫 번째 주요 노드로 동작합니다.

### 6.1. Clarifying 노드 역할
- 의도 분류 및 초기 엔티티 추출
- 누락 변수 판단 및 질문 생성
- 필요 시 SearchLawTool 호출하여 법령 스니펫 제공

### 6.2. 분기 조건

| 조건 | 이동 노드 | 설명 |
|------|----------|------|
| `missing_parameters` 비어있음 | **TaxCalculationEngine** | 모든 필수 변수 수집 완료 → 계산 실행 |
| 사용자가 일반 정보 요청 | **General QA/RAG** | 계산 불가 → 법령 안내 모드 |
| Out-of-scope 주제 | **종료 핸들러** | 증여/상속과 무관 → 정중히 종료 |

### 6.3. 컨텍스트 공유
- `clarifying_context`와 `collected_parameters`는 LangGraph 전역 상태로 관리
- 이후 노드(계산, QA)에서 재사용
- RAG 결과는 중복 검색 방지를 위해 전역 상태에 캐싱

## 7. 응답 생성 시 주의 사항

### 7.1. 계산 실행 조건
- `missing_parameters`가 비어있지 않으면 **계산하지 않음**
- 다시 Clarifying 질문 생성

### 7.2. 기본값 가정
- 사용자가 "계속" 요청 시 Tier 2 변수는 기본값 사용 가능
- `metadata.assumptions`에 가정 내용 명시
- 답변 본문에도 동일하게 노출

### 7.3. 질문 우선순위
Tier 1 → Tier 2 → Tier 3 순서 준수

## 8. 향후 개선 항목

1. **질문 템플릿 외부화**: YAML 파일로 분리하여 PM/세무사 피드백 신속 반영
2. **적응형 질문**: 사용자 이해도에 따라 장문/단문 질문 자동 조절
3. **UI 연동**: 누락 변수 자동 요약 카드 생성 (프런트엔드 협의)

---

## 변경 이력

- 2025-10-15: v2.0 - 국세청 간편계산기 기준으로 전면 개편
- 2025-10-14: v1.0 - 초안 작성
