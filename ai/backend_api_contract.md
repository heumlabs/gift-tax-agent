# AI ↔ Backend Integration Contract

본 문서는 LLM 팀이 제공하는 최소 챗 파이프라인을 백엔드에서 사용할 때 필요한 API 계약을 정리한 메모입니다. 백엔드 구현은 Chalice 기준으로 설명하며, 타 스택에서도 동일한 호출 규격을 따르면 됩니다.

## 1. Endpoint Summary

| 항목 | 값 |
|------|-----|
| Method | `POST` |
| Path | `/api/sessions/{sessionId}/messages` |
| Headers | `Content-Type: application/json`, `X-Client-Id`(선택) |
| Request Body | `{ "content": string, "metadata?": object }` |
| Success | `200 OK`, `assistantMessage` payload |
| Errors | `400 INVALID_CONTENT`, `502 GEMINI_ERROR`, 기타 비정상 오류 |

### Request Body
```json
{
  "content": "배우자에게 1억원 증여하면 세금이 어떻게 되나요?",
  "metadata": {
    "sessionContext": "optional arbitrary object"
  }
}
```
- `content`는 공백이 아닌 문자열이어야 하며, 필수입니다.
- `metadata`는 선택 사항으로, 구조에 대한 제약은 없습니다. (추후 Clarifying/계산 단계에서 사용.)

### Success Response (200)
```json
{
  "assistantMessage": {
    "id": "8338f649-a9f9-4f73-95ce-7973547b5d2f",
    "role": "assistant",
    "content": "배우자에게 1억원을 증여하면...",
    "metadata": {
      "citations": [],
      "calculation": null,
      "clarifying_context": [],
      "assumptions": [],
      "missing_parameters": [],
      "exceptions": [],
      "recommendations": [],
      "tool_calls": []
    },
    "createdAt": "2025-10-14T10:05:10.421Z"
  }
}
```

**LLM 모듈 반환 값**:
```python
{
  "content": "배우자에게 1억원을 증여하면...",
  "metadata": { ... }
}
```
- `id`, `role`, `createdAt`은 백엔드가 생성하여 추가합니다.
- `metadata` 구조는 `docs/prd_detail/ai-logic/03-message-format.md`에 정의된 Assistant Message 스키마를 따릅니다. 현재 프로토타입에서는 대부분 빈 배열/`null`을 반환합니다.

### Error Responses
| 상태 코드 | `error.code` | 설명 |
|-----------|--------------|------|
| `400` | `INVALID_CONTENT` | `content`가 문자열이 아닌 경우 |
| `502` | `GEMINI_ERROR` | Gemini REST 호출 실패 (DNS, Timeout 등). 메시지에 원인 문자열 포함 |
| `500` | `PIPELINE_ERROR` | 내부 파이프라인 에러 (현재는 치명 오류만 그대로 전달) |

> 백엔드는 필요 시 위 에러 코드를 후속 처리(재시도, 사용자 안내)하도록 설계하면 됩니다. 추가 에러 코드가 생기면 본 문서를 업데이트합니다.

## 2. 환경 변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `GOOGLE_API_KEY` | Gemini REST 키 | (필수) |
| `GEMINI_MODEL` | 모델명 | `gemini-2.5-flash` |
| `GEMINI_TIMEOUT_SECONDS` | HTTP 타임아웃(초) | `30.0` |

- 루트 `.env` 또는 `backend/.env`에 위 값을 정의하면 LLM 파이프라인에서 자동으로 로드합니다 (`python-dotenv` 사용).

## 3. 최소 응답 시퀀스

1. 백엔드에서 Request 바디 검증 (`content` 문자열 확인).
2. **[Phase 3 추가] 이전 메시지 조회 및 `collected_parameters` 추출** (멀티턴 대화 지원).
3. `ai.service.generate_assistant_message(content, session_id, previous_collected_parameters, metadata)` 호출.
4. 반환된 `{"content": str, "metadata": dict}`에 백엔드가 `id`, `role`, `createdAt`을 추가하여 응답 생성.
5. 예외 발생 시 위 표의 에러 코드/메시지로 변환 후 반환.

**Note**: LLM 모듈은 핵심 AI 로직(`content`, `metadata`)만 반환하며, 인프라 필드(`id`, `role`, `createdAt`)는 백엔드가 생성합니다.

## 4. 테스트 메모

- 로컬 확인은 `python -m ai.scripts.send_message "질문"`으로 LLM 파이프라인을 먼저 검증한 뒤,
- Chalice `Client` 또는 프론트엔드에서 동일한 JSON을 보내면 됩니다. (네트워크 차단 환경에서는 Gemini 호출이 실패할 수 있음)

추가 요구사항이나 에러 코드가 생기면 이 문서를 갱신해 백엔드 팀과 공유합니다.

---

## 5. Phase 3: 멀티턴 대화 지원 (Issue #23)

### 5.1. generate_assistant_message() 시그니처 변경

**기존 (Phase 2)**:
```python
generate_assistant_message(content: str, metadata: Optional[Dict] = None)
```

**변경 (Phase 3)**:
```python
generate_assistant_message(
    content: str,
    session_id: str = "default",
    previous_collected_parameters: Optional[Dict] = None,
    metadata: Optional[Dict] = None
)
```

### 5.2. 백엔드 연동 로직 (message_service.py)

**구현 위치**: `backend/chalicelib/services/message_service.py:107-119`

#### 1. 이전 메시지 조회
```python
# Phase 3 추가: 이전 메시지 조회 (최근 10개, 역순)
previous_messages, _ = message_repo.find_all_by_session(
    session_id, limit=10, cursor=None
)
```

#### 2. collected_parameters 추출
```python
# Phase 3 추가: 마지막 assistant 메시지에서 collected_parameters 추출
previous_collected = {}
for msg in reversed(previous_messages):  # 오래된 것부터 순회
    if msg.role == "assistant" and msg.msg_metadata:
        collected = msg.msg_metadata.get("collected_parameters", {})
        if collected:
            previous_collected = collected
            break  # 가장 최근 assistant 메시지만 사용
```

#### 3. AI 서비스 호출
```python
# 2. AI 응답 생성 (Phase 3: session_id, previous_collected_parameters 추가)
ai_response = generate_assistant_message(
    content=content,
    session_id=session_id,
    previous_collected_parameters=previous_collected
)
```

### 5.3. metadata 구조 변경

**Phase 3에서 추가된 필드**:
- `collected_parameters`: 현재까지 수집된 파라미터 (Dict)
- `missing_parameters`: 누락된 필수 변수 목록 (List[str])
- `calculation`: 계산 결과 (Dict, 계산 완료 시에만 존재)

이 필드들은 `messages.msg_metadata` (JSONB)에 저장되며, 다음 턴에서 `previous_collected_parameters`로 재사용됩니다.

### 5.4. 대화 흐름 예시

**Turn 1**:
- User: "부모님께 1억 받았어요"
- AI: "증여일이 언제인가요?"
- `metadata.collected_parameters`: `{"donor_relationship": "직계존속", "gift_property_value": 100000000}`
- `metadata.missing_parameters`: `["gift_date"]`

**Turn 2**:
- User: "2025년 10월 15일이요"
- Backend: 이전 메시지에서 `collected_parameters` 추출 → AI에 전달
- AI: 파라미터 누적 → 계산 실행 → 결과 반환
- `metadata.collected_parameters`: `{"donor_relationship": "직계존속", "gift_property_value": 100000000, "gift_date": "2025-10-15"}`
- `metadata.missing_parameters`: `[]`
- `metadata.calculation`: `{"final_tax": 5000000, ...}`

### 5.5. 참조 문서

- `docs/prd_detail/ai-logic/04-clarifying-implementation-spec.md`: Phase 3 구현 명세
- `docs/prd_detail/ai-logic/04-clarifying-strategy.md`: 9개 변수 정의 및 Tier 순서
- `docs/prd_detail/ai-logic/03-message-format.md`: metadata 구조 정의
