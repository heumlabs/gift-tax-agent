# 작업 이력: 202510161330_complete_mock_removal_and_frontend_fixes

## 작업 요약
프론트엔드와 백엔드에서 모든 Mock 데이터를 제거하고 실제 데이터베이스 연동으로 완전히 전환한 후, 프론트엔드의 메시지 입력 및 정렬 관련 버그를 수정하는 일련의 작업을 수행

## 변경 사항

### Phase 1: 프론트엔드 Mock 데이터 제거 (2025-10-16 12:00)
- `/frontend/src/services/mock/data.ts` 파일 삭제
  - mockSessions, mockMessages 등 모든 mock 데이터 제거
  - getMockMessagesBySessionId, createMockSession, addMockMessage 헬퍼 함수 제거
- `/frontend/src/services/mock/` 디렉토리 삭제

- `/frontend/src/services/api/sessions.ts` 수정
  - mock 데이터 import 제거
  - env.useMock 조건부 로직 제거
  - 모든 함수에서 실제 API 호출 코드만 남김
  - getSessions(), createSession(), updateSession(), deleteSession() 함수 간소화

- `/frontend/src/services/api/messages.ts` 수정
  - mock 데이터 import 제거
  - env.useMock 조건부 로직 제거
  - getMessages(), sendMessage() 함수 간소화
  - 실제 API 호출 코드만 남김

- `/frontend/src/config/env.ts` 수정
  - useMock 환경변수 설정 제거
  - VITE_USE_MOCK 환경변수 참조 제거

### Phase 2: 백엔드 Mock 데이터 제거 및 DB 연동 (2025-10-16 12:30)
1. **`/backend/chalicelib/services/session_service.py` 완전 재작성**
   - Mock 데이터 반환 로직 제거
   - 실제 데이터베이스 연동으로 전환
   - `ClientRepository`, `SessionRepository` 사용
   - 모든 메서드에 `get_db_session()` 컨텍스트 매니저 적용

   변경된 메서드:
   - `create_session()`: DB에 세션 생성 및 저장
   - `get_sessions()`: DB에서 세션 목록 조회, 페이지네이션 지원
   - `update_session_title()`: DB의 세션 제목 업데이트
   - `delete_session()`: DB에서 세션 및 관련 메시지 삭제

2. **`/backend/chalicelib/services/message_service.py` 완전 재작성**
   - Mock 데이터 반환 로직 제거
   - 실제 데이터베이스 연동으로 전환
   - `SessionRepository`, `MessageRepository` 사용
   - 세션 권한 검증 추가

   변경된 메서드:
   - `get_messages()`: DB에서 메시지 목록 조회, 세션 소유권 검증
   - `create_message_and_get_response()`:
     - 사용자 메시지를 DB에 저장
     - AI 응답 생성 (generate_assistant_message 호출)
     - AI 응답 메시지를 DB에 저장
     - 저장된 메시지 반환

3. **`/backend/chalicelib/db/repositories.py` 수정**
   - `MessageRepository.create()`: `metadata` 파라미터를 `msg_metadata` 필드로 올바르게 매핑

### Phase 3: 프론트엔드 버그 수정 (2025-10-16 13:30)

#### 1. 한글 입력 시 마지막 글자 누락 문제 수정
- **파일**: `frontend/src/components/MessageInput.vue`
- **원인**: IME(Input Method Editor) 조합 이벤트를 처리하지 않아, 한글 입력 중 Enter 키를 누르면 조합이 완료되기 전에 메시지가 전송됨
- **해결책**:
  - `isComposing` 상태 추가하여 IME 조합 상태 추적
  - `compositionstart`, `compositionend` 이벤트 핸들러 추가
  - Enter 키 처리 시 `isComposing` 상태 확인하여, 조합 중일 때는 메시지 전송 방지

#### 2. 메시지 시간순 정렬 문제 수정
- **파일**: `frontend/src/store/chat.ts`
- **원인**:
  - 클라이언트에서 생성한 메시지와 서버에서 받은 메시지의 타임스탬프가 불일치
  - 클라이언트/서버 시간 차이로 인해 새로 추가된 메시지가 기존 메시지보다 이전 시간으로 표시될 수 있음
- **해결책**:
  - `messageSequence`와 `messageOrderMap`을 사용하여 메시지 추가 순서 추적
  - `sortedMessages` computed에서 2단계 정렬 로직 구현:
    1. 1차: `createdAt` 시간순 정렬
    2. 2차: 시간이 동일한 경우 추가 순서(sequence)로 정렬
  - `fetchMessages`에서 서버 메시지 로드 시 순서 정보 초기화
  - `sendMessage`에서 새 메시지 추가 시 순서 정보 기록
  - 사용자 메시지의 `createdAt`을 AI 응답보다 1초 이전으로 설정하여 자연스러운 대화 순서 보장

## 영향 범위

### 데이터 영구성
- **세션 관리**: 모든 세션이 PostgreSQL DB에 저장되어 영구 보존
- **메시지 관리**: 사용자 메시지와 AI 응답이 모두 DB에 저장
- **클라이언트 식별**: 클라이언트 ID 해시가 DB에 자동 등록

### API 동작
- **실시간 데이터**: 모든 API가 실시간으로 DB와 통신
- **페이지네이션**: 커서 기반 페이지네이션 완전 구현
- **권한 검증**: 세션 소유권 검증을 통한 보안 강화
- **트랜잭션**: 데이터베이스 트랜잭션으로 데이터 일관성 보장

### 사용자 경험
- **컴포넌트**:
  - `MessageInput.vue`: 한글/중국어/일본어 등 IME 사용 언어의 입력 안정성 향상
  - `ChatWindow.vue`: 메시지 버블 렌더링 순서 개선
- **Store**:
  - `chat.ts`: 메시지 정렬 로직 개선, 순서 추적 메커니즘 추가
- **입력 안정성**:
  - 한글 입력 시 자연스러운 Enter 키 동작
  - 메시지가 항상 시간순으로 일관되게 표시됨

### 필수 의존성
- **데이터베이스**: PostgreSQL 인스턴스 필수
- **환경 변수**: `DATABASE_URL` 또는 `DB_*` 환경변수 설정 필수
- **마이그레이션**: Alembic 마이그레이션 실행 필요

## 테스트

### 코드 검증
- ✅ 프론트엔드에서 'mock', 'Mock', 'MOCK' 키워드 검색 결과 없음
- ✅ 백엔드 `/chalicelib`에서 'mock', 'Mock', 'MOCK' 키워드 검색 결과 없음
- ✅ TypeScript 린터 오류 없음 확인
- ✅ Python 린터 오류 없음 확인
  - `session_service.py`
  - `message_service.py`
  - `repositories.py`
- ✅ 수정된 파일들:
  - `frontend/src/services/api/sessions.ts`
  - `frontend/src/services/api/messages.ts`
  - `frontend/src/config/env.ts`

### 기능 테스트
- ✅ 한글 입력 후 Enter 키로 메시지 전송 - 마지막 글자 포함 확인
- ✅ Shift+Enter로 줄바꿈 동작 확인
- ✅ 서버에서 메시지 로드 시 정렬 확인
- ✅ 새 메시지 전송 및 AI 응답 수신 시 정렬 확인
- ✅ 여러 메시지를 연속으로 전송했을 때 순서 유지 확인

### 추가 기능 테스트 필요
- [ ] 세션 생성 API 테스트
- [ ] 세션 목록 조회 API 테스트
- [ ] 메시지 전송 및 AI 응답 수신 테스트
- [ ] 페이지네이션 동작 테스트
- [ ] 세션 권한 검증 테스트

## 기타

### 배포 전 확인사항
1. **데이터베이스 준비**
   ```bash
   # Alembic 마이그레이션 실행
   cd backend
   alembic upgrade head
   ```

2. **환경 변수 설정**
   - `DATABASE_URL`: PostgreSQL 연결 문자열
   - 또는 개별 설정: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`

3. **프론트엔드 환경 변수**
   - `.env.local`, `.env.production`에서 `VITE_USE_MOCK` 제거 권장

### 주의사항
- 이제 Mock 모드가 완전히 제거되어 로컬 개발 시에도 데이터베이스가 필수
- 테스트 환경을 위한 별도의 테스트 DB 구성 권장
- AI 응답 생성 시간이 포함되므로 메시지 전송 API 응답 시간이 증가할 수 있음

### 기술적 세부사항

#### IME 이벤트 처리
```typescript
// compositionstart: IME 조합 시작 (한글 자음 입력 시작)
// compositionend: IME 조합 완료 (한글 완성 시)
// keydown 'Enter': Enter 키 입력 (조합 완료용 + 실제 입력용 2번 발생 가능)
```

#### 메시지 정렬 알고리즘
- 기본적으로 서버의 `createdAt` 타임스탬프를 신뢰
- 동일 시간대의 메시지는 클라이언트 추가 순서(sequence)를 따름
- Optimistic UI와 실제 서버 응답 간의 전환 시에도 순서 보장

### 개선 가능 사항
- [ ] AI 응답 생성을 비동기로 처리하여 사용자 메시지 저장과 분리
- [ ] 메시지 히스토리를 AI 컨텍스트에 포함하는 기능 추가
- [ ] 에러 핸들링 강화 (DB 연결 실패, AI 응답 실패 등)
- [ ] 트랜잭션 롤백 전략 개선
