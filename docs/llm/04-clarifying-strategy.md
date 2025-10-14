# Clarifying & Variable-Gathering Strategy

**문서 버전**: v1.0  
**작성일**: 2025-10-14  
**연관 문서**: `docs/prd_detail/ai-logic.md`, `01-data-pipeline.md`, `03-message-format.md`

## 1. 범위

이 문서는 PRD 및 `docs/prd_detail/ai-logic.md`에서 정의한 상담 흐름을 LLM 팀이 구현할 때 참고하는 **필수 변수 수집(clarifying)** 전략을 정리합니다. 실제 대화 오케스트레이션은 PRD_DETAIL이 단일 진실 소스이며, 여기서는 LLM 관련 구현 세부 규칙만 기술합니다.

## 2. 필수 변수 체크리스트

| 카테고리 | 변수 | 설명 | 필수 여부 | 비고 |
|----------|------|------|-----------|------|
| 기본 | `tax_type` | `gift` / `inheritance` | ✅ | 사용자 초기 질문에서 유추 |
| 관계 | `relationship` | 배우자, 직계존속, 직계비속, 기타 | ✅ | 공제 한도 계산 |
| 거주 | `is_resident` | 국내 거주자 여부 | ✅ | 비거주자 계산 분기 |
| 금액 | `amount` | 증여/상속 대상 금액 또는 평가액 | ✅ | 단위: KRW |
| 기간 | `past_gifts` / `past_inheritance` | 최근 10년 동일인 증여/상속 합계 | ✅ (증여) / 옵션(상속) | 누적 과세 판단 |
| 자산 유형 | `asset_type` | 현금, 부동산, 주식, 사업체 등 | ✅ | 특례 적용 분기 |
| 채무/부담 | `has_debt` | 부담부 증여/채무 상속 여부 | 옵션 | 가산세/차감 |
| 특례 | `eligible_exemption` | 가업상속, 영농상속, 증여특례 등 | 옵션 | 추가 정보 필요 시 세부 필드 |
| 신고 상태 | `planned_filing_date` | 신고 예정일 / 지연 여부 | 옵션 | 가산세 안내 |

> PRD 기준 필수 항목을 우선 수집하고, 추가 특례는 사용자가 관심을 표할 때만 질문합니다.

## 3. Clarifying 루프 설계

1. **초기 분석**: 사용자의 첫 메시지를 `docs/prd_detail/ai-logic.md`에서 정의한 의도 분류기로 분류하고, 초기 엔티티 추출.  
2. **부족 변수 판정**: 필수 체크리스트와 비교하여 `missing_parameters` 집합을 구성.  
3. **Clarifying 질문 생성**:
   - 질문은 한 번에 1~2개씩 묶어서 전달.
   - 질문 템플릿은 PRD_DETAIL의 예시 문구를 기반으로 `docs/llm/04-clarifying-strategy.md`에서 관리.
   - 사용자가 “모른다/확인 중”이라고 응답하면, 예외 처리 안내와 함께 다음 질문으로 넘어감.
4. **반복**: `missing_parameters`가 비어질 때까지 2~3단계 반복.  
5. **종료 조건**:
   - 필수 변수 충족 → 계산/검색 모듈로 이동  
   - 3회 이상 동일 변수를 수집하지 못함 → “추가 정보 확보 후 다시 시도” 메시지와 체크리스트 제공  
   - 사용자가 중단 요청 → 세션 보존 후 종료

## 4. 메시지 메타데이터 매핑

Clarifying 단계에서 사용되는 정보는 다음 규칙으로 `metadata`에 저장합니다.

```json
{
  "intent": "gift_tax",
  "collected_parameters": {
    "relationship": "spouse",
    "is_resident": true
  },
  "missing_parameters": [
    { "name": "amount", "reason": "not_provided" },
    { "name": "past_gifts", "reason": "clarification_required" }
  ],
  "clarifying_history": [
    {
      "question": "증여 금액이 얼마인지 알려주실 수 있을까요?",
      "timestamp": "2025-10-14T07:32:01Z"
    }
  ]
}
```

- `intent`: PRD_DETAIL에서 정의된 분류 키 (`gift_tax`, `inheritance_tax`, `general_info` 등)  
- `collected_parameters`: 현재까지 확인된 변수  
- `missing_parameters`: 수집되지 않은 필수 변수 목록과 사유 (`not_provided`, `ambiguous`, `user_unknown`)  
- `clarifying_history`: 질문·응답 로그(선택), 향후 UI에서 재활용 가능

## 5. 응답 생성 시 주의 사항

- `missing_parameters`가 비어있지 않다면 최종 계산/답변을 실행하지 않고 다시 Clarifying 질문을 생성합니다.  
- 사용자가 “계속”을 요청했지만 일부 변수는 기본값으로 가정해야 하는 경우, `metadata.assumptions`에 가정 내용을 명시하고 답변 본문에 동일하게 노출합니다.  
- 여러 변수 중 일부만 누락된 경우, 우선순위는 `relationship` → `amount` → `past_gifts` → `asset_type` 순으로 재질문합니다.

## 6. 향후 개선 항목

1. Clarifying 질문 템플릿을 YAML 등 외부 설정으로 분리하여 PM/세무사 피드백을 신속히 반영  
2. 질문 난이도에 따른 적응형 전략(사용자 이해도에 따라 장문/단문 질문 조절)  
3. 누락 변수 자동 요약 카드 생성 (프런트엔드와 협의)

---

> Clarifying 로직 변경 시 `docs/prd_detail/ai-logic.md`를 우선 수정하고, 이 문서와 `03-message-format.md`의 관련 필드 정의를 동기화해야 합니다.
