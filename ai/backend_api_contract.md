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
2. `ai.service.generate_assistant_message(content, metadata)` 호출.
3. 반환된 `assistantMessage` 객체를 그대로 응답(`200 OK`)으로 전달.
4. 예외 발생 시 위 표의 에러 코드/메시지로 변환 후 반환.

## 4. 테스트 메모

- 로컬 확인은 `python -m ai.scripts.send_message "질문"`으로 LLM 파이프라인을 먼저 검증한 뒤,
- Chalice `Client` 또는 프론트엔드에서 동일한 JSON을 보내면 됩니다. (네트워크 차단 환경에서는 Gemini 호출이 실패할 수 있음)

추가 요구사항이나 에러 코드가 생기면 이 문서를 갱신해 백엔드 팀과 공유합니다.
