# 워크플로우 재설계 - 2025-10-16

## 배경

기존 구현(Phase 3.1)과 문서(Phase 3)가 완전히 다른 설계를 따르고 있어 혼란 발생:
- **문서**: 단순 파이프라인 (Intent → Clarifying → Calculation → Synthesis)
- **구현**: Agent 기반 시스템 (Receptionist, Calculator 역할 분리)

## 주요 문제점

### 1. 문서 vs 구현 불일치
- Agent 개념이 문서에 없음
- 매 턴마다 Intent를 재분류 (문서: 첫 턴만 분류)
- Calculator 노드가 너무 많은 책임 (이탈 감지 + 파싱 + 질문 + 계산 + 합성)

### 2. Exit Detection의 LLM 과의존
- 매 Clarifying 턴마다 Gemini API 호출
- "6월이라고 했잖아"를 continue로 판단해야 하는데 불확실성
- 키워드 기반으로 충분함

### 3. 파라미터 누적 버그
- extract_parameters() 실패 시 기본값 반환 → collected에 덮어씌움
- Tier 2/3 변수가 파싱 실패 시에도 False/0으로 설정됨

## 재설계 내용

### 1. 워크플로우 구조 단순화

**기존 (Phase 3.1)**:
```
START → [collected_parameters 있음?]
         ├─ NO → receptionist (Agent) → calculator (Agent)
         └─ YES → calculator (Agent) → [agent=?]
```

**재설계 (Phase 3 문서 기준)**:
```
START → [collected_parameters 있음?]
         ├─ NO → intent_node → [gift_tax?]
         │                      ├─ YES → clarifying_node → [누락?]
         │                      │                            ├─ YES → response (질문) → END
         │                      │                            └─ NO → calculation_node → synthesis_node → END
         │                      └─ NO → response_node → END
         │
         └─ YES → clarifying_node (Intent 건너뜀) → [누락?]
                                                     ├─ YES → response (질문) → END
                                                     └─ NO → calculation_node → synthesis_node → END
```

**주요 개선**:
- `agent` 필드 제거 (WorkflowState 단순화)
- Intent는 첫 턴에만 분류 (문서와 일치)
- Clarifying, Calculation, Synthesis 노드 명확히 분리 (단일 책임 원칙)

### 2. Exit Detection 키워드 기반 변경

**기존**: Gemini API 호출 (매 턴마다)

**재설계**: 키워드 우선 처리
```python
EXIT_KEYWORDS = ["그만", "취소", "안할래", "됐어", ...]
INHERITANCE_KEYWORDS = ["상속세", "상속", ...]
GIFT_KEYWORDS = ["증여세", "증여"]

def detect_exit_intent_keyword(user_message: str):
    # 1. 종료 키워드 우선
    # 2. 상속세 전환 (증여세 키워드 없을 때만)
    # 3. 증여세 전환 (상속세 키워드 없을 때만)
    # 4. 그 외 정상 진행
```

**장점**:
- LLM 호출 제거 → 비용 절감, 속도 향상
- 명확한 키워드 → 정확도 향상
- "6월이라고 했잖아" 같은 불만 표현도 정상 진행

### 3. 파라미터 누적 로직 수정

**기존 문제**:
```python
# extract_parameters() 실패 시
return {
    "is_generation_skipping": False,  # 기본값 반환
    "is_minor_recipient": False,
    ...
}

# clarifying_node에서 병합
for key, value in new_params.items():
    if value is not None:  # False, 0도 덮어씌움!
        collected[key] = value
```

**재설계**:
```python
# extract_parameters() 실패 시
return {}  # 빈 dict 반환

# clarifying_node에서 Tier 1만 병합
tier1_keys = ["gift_date", "donor_relationship", "gift_property_value"]
for key in tier1_keys:
    if key in new_params and new_params[key] is not None:
        collected[key] = value

# Tier 2/3 기본값은 calculation_node에서 추가
```

**장점**:
- 파싱 실패 시 collected 오염 방지
- Tier 1 필수 변수만 수집 (문서와 일치)
- 기본값은 계산 시점에 추가 (명확한 책임 분리)

## 변경 파일 목록

### 수정
1. `ai/schemas/workflow_state.py` - agent 필드 제거
2. `ai/pipelines/langgraph_workflow.py` - 전면 재작성 (문서 기준)
3. `ai/utils/exit_detection.py` - 키워드 기반으로 변경
4. `ai/utils/parameter_extraction.py` - 실패 시 빈 dict 반환
5. `ai/tests/conftest.py` - Mock 제거 (실제 API 호출)
6. `ai/tests/test_clarifying_workflow.py` - E2E 테스트로 변경

## 테스트 전략

**기존**: 룰 기반 Mock (Intent, 파라미터 추출 등)

**재설계**: 실제 Gemini API 호출
- E2E 테스트는 `@pytest.mark.skip` (수동 실행)
- 기본 워크플로우 테스트만 자동 실행
- Mock 없이 실제 API로 통합 테스트

**이유**:
- 룰 기반 Mock은 불필요하게 복잡
- 실제 API 동작을 검증해야 의미 있음
- LLM 응답은 비결정적이므로 Mock이 오히려 문제

## 완료 기준

- [x] Agent 개념 제거 (문서와 일치)
- [x] Intent는 첫 턴에만 분류
- [x] Clarifying, Calculation, Synthesis 노드 분리
- [x] Exit Detection 키워드 기반 변경
- [x] 파라미터 누적 로직 수정
- [x] 테스트 간소화 (Mock 제거)

## 다음 단계

1. **실제 API로 E2E 테스트** (수동)
   ```bash
   export GOOGLE_API_KEY=<your-key>
   pytest ai/tests/test_clarifying_workflow.py::TestClarifyingWorkflowE2E -v
   ```

2. **문서 업데이트**
   - `04-clarifying-implementation-spec.md` 수정 (Agent 개념 제거)
   - `functional-spec.md` 업데이트 (완료 항목 체크)

3. **Backend 연동**
   - `message_service.py`에서 `previous_collected_parameters` 전달
   - 세션별 파라미터 누적 확인

## 핵심 교훈

1. **문서를 먼저 읽고 구현하기** - 코드만 보면 설계 의도 파악 어려움
2. **단순한 것이 최고** - Agent 개념보다 단순 파이프라인이 더 명확
3. **키워드가 LLM보다 나을 때도 있음** - Exit Detection은 키워드로 충분
4. **테스트는 실제 동작 검증** - 룰 기반 Mock은 불필요

## 레퍼런스

- [04-clarifying-strategy.md](../prd_detail/ai-logic/04-clarifying-strategy.md) - Clarifying 전략 v2.2
- [04-clarifying-implementation-spec.md](../prd_detail/ai-logic/04-clarifying-implementation-spec.md) - Phase 3 구현 명세
- [functional-spec.md](../prd_detail/ai-logic/functional-spec.md) - LLM Functional Spec
