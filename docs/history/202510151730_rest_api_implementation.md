# 작업 이력: 202510151730_rest_api_implementation

## 작업 요약
REST API 엔드포인트 구현 및 CI/CD 워크플로우 개선 작업을 완료했습니다. API 명세서에 따라 Sessions 및 Messages API를 구현하고, SQLModel 기반 데이터베이스 모델을 작성했습니다. GitHub Actions에서 Lambda Container Image를 arm64 아키텍처로 빌드하도록 수정하여 CI/CD 파이프라인을 개선했습니다.

## 변경 사항

### 1. CI/CD 워크플로우 개선
- **파일**: `.github/workflows/deploy.yml`
- **변경 내용**:
  - Docker Buildx를 사용하여 `--platform linux/arm64`로 크로스 빌드 추가
  - GitHub Actions 러너(x86_64)와 Lambda 함수(arm64) 간 아키텍처 불일치 해결
  - 빌드 및 푸시 명령어를 단일 `docker buildx build --push`로 통합

### 2. SQLModel 데이터베이스 모델 작성
- **파일**: `backend/chalicelib/models/database.py`
- **구현 내용**:
  - `Client`: 익명 사용자 식별 테이블
  - `Session`: 대화 세션 정보 테이블
  - `Message`: 세션 내 메시지 테이블 (metadata 필드는 `msg_metadata`로 구현하여 SQLAlchemy 예약어 충돌 회피)
  - `Source`: RAG용 법령/예규 문서 테이블 (pgvector 임베딩 지원)
  - `TaxRuleConfig`: 세법 규정 수치 저장 테이블
- **주요 기술**:
  - SQLModel (SQLAlchemy + Pydantic 통합)
  - pgvector 확장을 통한 벡터 검색 지원
  - 인덱스 전략: 커서 기반 페이지네이션을 위한 복합 인덱스

### 3. API 요청/응답 모델 작성
- **파일**: `backend/chalicelib/models/api.py`
- **구현 내용**:
  - Sessions API: `SessionCreate`, `SessionResponse`, `SessionUpdate`, `SessionListResponse`
  - Messages API: `MessageCreate`, `MessageResponse`, `MessageListResponse`, `AssistantMessageResponse`
  - `by_alias=True`를 통한 camelCase 응답 (예: `createdAt`, `nextCursor`)

### 4. 데이터베이스 연결 및 Repository 패턴
- **파일**: 
  - `backend/chalicelib/db/connection.py`: SQLAlchemy 엔진 및 세션 관리
  - `backend/chalicelib/db/repositories.py`: Repository 패턴 구현
- **구현 내용**:
  - `ClientRepository`: 클라이언트 찾기/생성
  - `SessionRepository`: 세션 CRUD 및 커서 기반 페이지네이션
  - `MessageRepository`: 메시지 CRUD 및 커서 기반 페이지네이션
  - Context manager를 통한 안전한 세션 관리

### 5. Auth 미들웨어
- **파일**: `backend/chalicelib/auth/client_auth.py`
- **구현 내용**:
  - `x-client-id` 헤더에서 UUID 추출
  - SHA-256 해싱을 통한 클라이언트 식별
  - `UnauthorizedError` 예외 처리

### 6. Mock 서비스 레이어
- **파일**: 
  - `backend/chalicelib/services/session_service.py`
  - `backend/chalicelib/services/message_service.py`
- **구현 내용**:
  - 실제 DB 연동 전 API 동작 테스트를 위한 Mock 데이터 반환
  - AI 응답 예시: citations, calculation metadata 포함
  - 다른 작업자가 실제 AI 로직을 구현할 수 있도록 인터페이스 정의

### 7. Chalice Routes 구현
- **파일**: `backend/app.py`
- **구현 내용**:
  - `POST /api/sessions`: 새 세션 생성 (201 Created)
  - `GET /api/sessions`: 세션 목록 조회 (페이지네이션)
  - `PATCH /api/sessions/{id}`: 세션 제목 수정
  - `DELETE /api/sessions/{id}`: 세션 삭제 (204 No Content)
  - `GET /api/sessions/{id}/messages`: 메시지 목록 조회 (페이지네이션)
  - `POST /api/sessions/{id}/messages`: 메시지 전송 및 AI 응답
- **주요 기술**:
  - CORS 설정: `x-client-id`, `x-session-id` 헤더 허용
  - Pydantic 모델 검증: BadRequestError 처리
  - `model_dump(mode='json', by_alias=True)`: datetime 직렬화 및 camelCase 응답

### 8. Dockerfile 수정
- **파일**: `backend/Dockerfile`
- **변경 내용**:
  - `chalicelib` 디렉토리 복사 추가
  - 이전에는 빈 디렉토리만 생성했으나, 실제 코드 복사로 변경

### 9. Requirements 업데이트
- **파일**: `backend/requirements.txt`
- **추가 패키지**:
  - `sqlmodel==0.0.22`: SQLModel ORM

## 영향 범위

### API 엔드포인트
- **신규 엔드포인트 (6개)**:
  - `POST /api/sessions`
  - `GET /api/sessions`
  - `PATCH /api/sessions/{id}`
  - `DELETE /api/sessions/{id}`
  - `GET /api/sessions/{id}/messages`
  - `POST /api/sessions/{id}/messages`

### 데이터베이스 스키마
- **5개 테이블 모델 정의**:
  - `clients`, `sessions`, `messages`, `sources`, `tax_rule_config`
- **인덱스 전략**:
  - `sessions(client_id_hash, created_at DESC)`
  - `messages(session_id, created_at DESC)`
  - `sources(document_name)`, `sources(embedding)`

### CI/CD 파이프라인
- **GitHub Actions**: arm64 아키텍처 빌드 지원
- **Docker 이미지**: Lambda Container Image로 배포

## 테스트

### 로컬 Docker 테스트
1. **Health Check**:
   ```bash
   curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" \
     -d '{"resource":"/health","path":"/health","httpMethod":"GET",...}'
   # ✅ {"status":"healthy","environment":"dev"}
   ```

2. **POST /api/sessions** (세션 생성):
   ```bash
   curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" \
     -d '{"resource":"/api/sessions",...,"headers":{"x-client-id":"test-uuid"}}'
   # ✅ 201 Created
   # {"id":"...","title":"새로운 상담","createdAt":"2025-10-15T08:29:08.647013"}
   ```

3. **POST /api/sessions/{id}/messages** (메시지 전송):
   ```bash
   curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" \
     -d '{"resource":"/api/sessions/{session_id}/messages",...,"body":"{\"content\":\"배우자에게 1억원 증여시 세금은 얼마인가요?\"}"}'
   # ✅ 200 OK
   # {
   #   "assistantMessage": {
   #     "id": "...",
   #     "role": "assistant",
   #     "content": "배우자로부터 증여받는 경우, 10년간 6억원까지...",
   #     "metadata": {
   #       "citations": [...],
   #       "calculation": {...}
   #     }
   #   }
   # }
   ```

### 테스트 결과
- ✅ Health check 정상 작동
- ✅ Sessions API (POST, GET, PATCH, DELETE) Mock 응답 정상
- ✅ Messages API (GET, POST) Mock 응답 정상
- ✅ CORS 헤더 정상 설정
- ✅ datetime JSON 직렬화 정상
- ✅ camelCase 필드명 변환 정상 (by_alias)

## 기술적 이슈 및 해결

### 1. SQLAlchemy 예약어 충돌
- **문제**: `Message.metadata` 필드가 SQLAlchemy의 예약어와 충돌
- **해결**: 
  ```python
  msg_metadata: Optional[dict] = Field(
      default=None,
      sa_column=Column("metadata", JSONB, nullable=True),
      ...
  )
  ```
  - Python 필드명: `msg_metadata`
  - 데이터베이스 컬럼명: `metadata`

### 2. SQLModel nullable/sa_column 충돌
- **문제**: `nullable=False`와 `sa_column`을 동시에 사용 불가
- **해결**: `nullable`을 `Column()` 내부로 이동
  ```python
  # 변경 전
  value_json: dict = Field(nullable=False, sa_column=Column(JSONB), ...)
  
  # 변경 후
  value_json: dict = Field(sa_column=Column(JSONB, nullable=False), ...)
  ```

### 3. datetime JSON 직렬화
- **문제**: `datetime` 객체가 JSON 직렬화 시 오류
- **해결**: Pydantic `model_dump(mode='json')`사용
  ```python
  return Response(
      body=session.model_dump(mode='json', by_alias=True),
      status_code=201
  )
  ```

### 4. GitHub Actions arm64 빌드
- **문제**: GitHub Actions 러너(x86_64)와 Lambda(arm64) 아키텍처 불일치
- **해결**: Docker Buildx를 사용한 크로스 빌드
  ```yaml
  - name: Set up Docker Buildx
    uses: docker/setup-buildx-action@v3

  - name: Build, tag, and push Docker image
    run: |
      docker buildx build \
        --platform linux/arm64 \
        --push \
        -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG \
        .
  ```

## 다음 단계

### 실제 AI 로직 구현 (다른 작업자)
1. **LLM 서비스 구현**:
   - `chalicelib/llm/`: Gemini API 클라이언트
   - 프롬프트 엔지니어링 (docs/prd_detail/ai-logic.md 참고)

2. **RAG 파이프라인 구현**:
   - `chalicelib/rag/`: pgvector 기반 법령 검색
   - 임베딩 생성 및 유사도 검색

3. **세금 계산 엔진**:
   - `chalicelib/services/tax_calc.py`: 결정론적 세금 계산
   - `tax_rule_config` 테이블 활용

4. **실제 DB 연동**:
   - Mock 서비스를 실제 Repository 사용으로 교체
   - 트랜잭션 관리 및 에러 핸들링

### 데이터베이스 마이그레이션
1. Alembic 초기화
2. 초기 마이그레이션 생성 (5개 테이블)
3. 인덱스 생성
4. pgvector 확장 활성화

### 배포 준비
1. GitHub Actions 워크플로우 검증 (main 브랜치 merge 후)
2. Lambda 환경 변수 설정 (DATABASE_URL, GEMINI_API_KEY 등)
3. RDS PostgreSQL 연결 테스트

## 기타

### 디렉토리 구조
```
backend/
├── app.py                      # Chalice 앱 및 routes
├── lambda_handler.py           # Lambda 진입점
├── Dockerfile                  # Container Image 정의
├── requirements.txt            # 의존성 (sqlmodel 추가)
└── chalicelib/
    ├── auth/                   # 클라이언트 인증
    │   ├── client_auth.py
    │   └── __init__.py
    ├── db/                     # 데이터베이스 레이어
    │   ├── connection.py       # SQLAlchemy 엔진/세션
    │   ├── repositories.py     # Repository 패턴
    │   └── __init__.py
    ├── models/                 # 데이터 모델
    │   ├── database.py         # SQLModel 스키마
    │   ├── api.py              # Pydantic 요청/응답
    │   └── __init__.py
    ├── services/               # 비즈니스 로직
    │   ├── session_service.py  # 세션 관리 (Mock)
    │   ├── message_service.py  # 메시지 관리 (Mock)
    │   └── __init__.py
    └── __init__.py
```

### API 명세 준수
- ✅ 모든 엔드포인트가 `docs/prd_detail/api-spec.md` 명세를 따름
- ✅ 에러 응답 형식 (`{"error": {"code": "...", "message": "..."}}`)은 Chalice 기본 형식 사용
- ✅ camelCase 응답 필드명 (createdAt, nextCursor, assistantMessage 등)
- ✅ 페이지네이션 커서 지원 (구현은 Repository에서 처리)

### 참고 문서
- `docs/prd_detail/api-spec.md`: REST API 명세
- `docs/prd_detail/database-model.md`: 데이터베이스 모델 설계
- `docs/prd_detail/backend-architecture.md`: 백엔드 아키텍처
- `docs/prd_detail/ai-logic.md`: AI 로직 및 RAG 설계

