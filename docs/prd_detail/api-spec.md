## API 명세서

문서 버전: v1.0  
연관 문서: `docs/PRD.md`, `docs/backend-architecture.md`

### 1. 일반 사항

-   **Base URL**: `/api`
-   **인증**: 모든 요청의 헤더에 `x-client-id: <uuid>`를 포함해야 합니다. 서버는 이 ID를 기반으로 사용자의 데이터를 식별합니다.
-   **데이터 형식**: 모든 요청과 응답의 본문(body)은 `JSON` 형식입니다.
-   **에러 응답 형식**:
    ```json
    {
      "error": {
        "code": "ERROR_CODE",
        "message": "A human-readable error message."
      }
    }
    ```

### 2. 엔드포인트: Sessions

세션(대화) 생성 및 관리를 담당합니다.

---

#### `POST /sessions`

새로운 대화 세션을 생성합니다.

-   **Headers**:
    -   `x-client-id`: `string` (Required)
-   **Request Body**: (Empty)
-   **Responses**:
    -   `201 Created`: 성공적으로 세션이 생성됨
        ```json
        {
          "id": "e7b2d3a0-3b8b-4b4e-9b0a-7e1d6e8e1d6e",
          "title": "새로운 상담",
          "createdAt": "2025-10-14T10:00:00Z"
        }
        ```

---

#### `GET /sessions`

해당 클라이언트의 모든 세션 목록을 조회합니다.

-   **Headers**:
    -   `x-client-id`: `string` (Required)
-   **Query Parameters**:
    -   `limit`: `integer` (Optional, Default: 20) - 페이지당 항목 수
    -   `cursor`: `string` (Optional) - 페이지네이션 커서
-   **Responses**:
    -   `200 OK`:
        ```json
        {
          "sessions": [
            {
              "id": "e7b2d3a0-3b8b-4b4e-9b0a-7e1d6e8e1d6e",
              "title": "자녀 증여세 관련",
              "createdAt": "2025-10-14T10:00:00Z"
            }
          ],
          "nextCursor": "some_opaque_string"
        }
        ```

---

#### `PATCH /sessions/{id}`

특정 세션의 제목을 수정합니다.

-   **Path Parameters**:
    -   `id`: `string` (Required) - 세션 ID
-   **Headers**:
    -   `x-client-id`: `string` (Required)
-   **Request Body**:
    ```json
    {
      "title": "수정된 제목"
    }
    ```
-   **Responses**:
    -   `200 OK`: 성공적으로 제목이 변경됨
        ```json
        {
          "id": "e7b2d3a0-3b8b-4b4e-9b0a-7e1d6e8e1d6e",
          "title": "수정된 제목",
          "createdAt": "2025-10-14T10:00:00Z"
        }
        ```

---

#### `DELETE /sessions/{id}`

특정 세션을 삭제합니다.

-   **Path Parameters**:
    -   `id`: `string` (Required) - 세션 ID
-   **Headers**:
    -   `x-client-id`: `string` (Required)
-   **Responses**:
    -   `204 No Content`: 성공적으로 삭제됨

---

### 3. 엔드포인트: Messages

특정 세션 내의 메시지를 관리하고 AI 응답을 생성합니다.

---

#### `GET /sessions/{id}/messages`

특정 세션의 메시지 목록을 조회합니다.

-   **Path Parameters**:
    -   `id`: `string` (Required) - 세션 ID
-   **Headers**:
    -   `x-client-id`: `string` (Required)
-   **Query Parameters**:
    -   `limit`: `integer` (Optional, Default: 30)
    -   `cursor`: `string` (Optional) - 이전 메시지 조회를 위한 페이지네이션 커서
-   **Responses**:
    -   `200 OK`:
        ```json
        {
          "messages": [
            {
              "id": "msg_abc",
              "role": "user",
              "content": "안녕하세요?",
              "createdAt": "2025-10-14T10:01:00Z"
            },
            {
              "id": "msg_def",
              "role": "assistant",
              "content": "네, 안녕하세요! 무엇을 도와드릴까요?",
              "metadata": {
                "citations": []
              },
              "createdAt": "2025-10-14T10:01:05Z"
            }
          ],
          "nextCursor": "some_opaque_string_for_older_messages"
        }
        ```

---

#### `POST /sessions/{id}/messages`

사용자 메시지를 보내고 AI의 응답을 받습니다.

-   **Path Parameters**:
    -   `id`: `string` (Required) - 세션 ID
-   **Headers**:
    -   `x-client-id`: `string` (Required)
-   **Request Body**:
    ```json
    {
      "content": "배우자에게 1억원 증여시 세금은 얼마인가요?"
    }
    ```
-   **Responses**:
    -   `200 OK`:
        ```json
        {
          "assistantMessage": {
            "id": "msg_xyz",
            "role": "assistant",
            "content": "배우자로부터 증여받는 경우, 10년간 6억원까지 증여재산 공제가 적용되어 납부할 세액은 일반적으로 없습니다.",
            "metadata": {
              "citations": [
                {
                  "text": "상속세및증여세법 제53조",
                  "url": "https://www.law.go.kr/..."
                }
              ],
              "calculation": {
                "assumptions": ["거주자 간 증여", "최근 10년 이내 동일인 증여 없음"],
                "taxableAmount": 100000000,
                "deduction": 600000000,
                "finalTax": 0
              }
            },
            "createdAt": "2025-10-14T10:05:10Z"
          }
        }
        ```
