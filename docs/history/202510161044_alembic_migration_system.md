# 작업 이력: 202510161044_alembic_migration_system

## 작업 요약
PostgreSQL 데이터베이스 스키마 버전 관리를 위한 Alembic 마이그레이션 시스템 도입 및 GitHub Actions 배포 워크플로우 통합

## 변경 사항

### 1. Alembic 설치 및 초기화
- `backend/requirements.txt`에 `alembic==1.13.3` 추가
- `backend/alembic/` 디렉토리 구조 생성
  - `alembic.ini`: Alembic 설정 파일 (타임스탬프 포맷 마이그레이션 파일명)
  - `alembic/env.py`: 환경 설정 및 마이그레이션 실행 로직
  - `alembic/versions/`: 마이그레이션 파일 저장 디렉토리

### 2. Alembic 환경 설정 (backend/alembic/env.py)
- `config.py`의 `DATABASE_URL`을 동적으로 로드
- SQLModel 메타데이터 자동 인식 (autogenerate 지원)
- pgvector 확장 자동 설치 (`CREATE EXTENSION IF NOT EXISTS vector`)
- **SQLModel → SQLAlchemy 타입 자동 변환**:
  - `AutoString(length=N)` → `sa.String(length=N)`
  - `AutoString()` → `sa.Text()`
  - `Vector(dim)` → `Vector(dim)` (pgvector)
- **pgvector HNSW 인덱스 operator class 자동 추가**:
  - `embedding` 컬럼에 `vector_cosine_ops` 자동 설정
- 타입 변경 및 서버 기본값 변경 자동 감지

### 3. 데이터베이스 모델 PRD 준수 (backend/chalicelib/models/database.py)
- ✅ **PRD 문서 기준으로 모델 수정**:
  - `Source` 테이블 삭제
  - `LawSource` 테이블 추가 (법령 및 예규 전용)
  - `KnowledgeSource` 테이블 추가 (Q&A, 사례집 등)
- 모든 벡터 스토어 테이블에 `chunk_hash` 추가 (중복 방지)
- HNSW 인덱스 설정 (`vector_cosine_ops` 사용)
- GIN 인덱스 설정 (JSONB 메타데이터 검색용)

### 4. 초기 마이그레이션 생성
- `alembic/versions/20251016_1038_c52bc8b9e77c_initial_schema.py`
- 전체 스키마 생성 (5개 테이블):
  - `clients`: 익명 사용자 식별
  - `sessions`: 대화 세션
  - `messages`: 대화 메시지
  - `law_sources`: 법령 벡터 스토어
  - `knowledge_sources`: 지식 벡터 스토어
  - `tax_rule_config`: 세율 및 공제액 설정
- 모든 인덱스 자동 생성 (복합 인덱스, 벡터 인덱스, GIN 인덱스)

### 5. GitHub Actions 배포 워크플로우 업데이트 (.github/workflows/deploy.yml)
- Lambda 함수 업데이트 후 **자동 마이그레이션 단계 추가**:
  1. Python 3.12 환경 설정
  2. Alembic 및 의존성 설치
  3. `.env` 파일 확인 (DATABASE_URL 검증)
  4. `alembic upgrade head` 자동 실행
- 배포 프로세스:
  ```
  Docker 빌드 → ECR 푸시 → Lambda 업데이트 → DB 마이그레이션
  ```

### 6. 문서 업데이트
- **backend/README.md** 신규 작성:
  - Alembic 사용법 상세 가이드
  - 마이그레이션 생성/적용/롤백 방법
  - 트러블슈팅 가이드
  - 로컬 개발 환경 설정
  - API 엔드포인트 문서
- **chalicelib/models/__init__.py**: 
  - `Source` → `LawSource`, `KnowledgeSource` export 변경

## 영향 범위

### 데이터베이스
- ✅ PostgreSQL 스키마 버전 관리 시스템 도입
- ✅ `alembic_version` 테이블 자동 생성 (현재 버전 추적)
- ✅ 프로덕션 DB에 안전한 마이그레이션 적용 가능
- ⚠️ **기존 데이터베이스가 있는 경우**: 
  - 초기 마이그레이션 전 백업 필수
  - 테이블이 이미 존재하면 충돌 가능 (`DROP TABLE` 후 재생성 권장)

### Backend API
- 모델 import 경로 변경: `Source` → `LawSource`, `KnowledgeSource`
- 기존 API 엔드포인트는 영향 없음 (Session, Message 테이블 변경 없음)
- 향후 RAG 구현 시 새로운 테이블 사용 필요

### CI/CD
- `main` 브랜치 푸시 시 자동 마이그레이션 실행
- 배포 시간 약 30초~1분 증가 (마이그레이션 단계 추가)
- 마이그레이션 실패 시 배포 중단 (안전장치)

### 개발 워크플로우
- **모델 변경 시 필수 단계**:
  1. `chalicelib/models/database.py` 수정
  2. `alembic revision --autogenerate -m "message"` 실행
  3. 생성된 마이그레이션 파일 검토
  4. `alembic upgrade head` 적용
  5. Git commit & push

## 테스트

### 수행한 테스트

1. ✅ **Alembic 설치 및 초기화**
   ```bash
   alembic init alembic
   ```

2. ✅ **마이그레이션 autogenerate**
   ```bash
   alembic revision --autogenerate -m "initial_schema"
   ```
   - SQLModel AutoString → SQLAlchemy 타입 자동 변환 확인
   - pgvector Vector 타입 인식 확인

3. ✅ **마이그레이션 적용**
   ```bash
   alembic upgrade head
   ```
   - 5개 테이블 생성 성공
   - HNSW 인덱스 (vector_cosine_ops) 생성 성공
   - GIN 인덱스 (JSONB) 생성 성공
   - 복합 인덱스 생성 성공

4. ✅ **마이그레이션 롤백**
   ```bash
   alembic downgrade base
   ```
   - 모든 테이블 삭제 성공
   - 클린 롤백 확인

5. ✅ **마이그레이션 상태 확인**
   ```bash
   alembic current
   alembic history
   ```

### 확인사항

- ✅ pgvector 확장 자동 설치
- ✅ SQLModel 타입이 표준 SQLAlchemy 타입으로 변환
- ✅ HNSW 인덱스에 operator class 자동 추가
- ✅ Foreign Key 제약조건 정상 작동
- ✅ Check 제약조건 정상 작동 (`role IN ('user', 'assistant')`)
- ✅ 서버 기본값 (gen_random_uuid(), now()) 정상 작동

## 기술적 세부사항

### Alembic 설정 특징

1. **파일명 포맷**: `YYYYMMDD_HHMM_<revision_id>_<slug>.py`
   - 시간순 정렬 용이
   - Git 머지 충돌 최소화

2. **autogenerate 커스터마이징**:
   ```python
   def render_item(type_, obj, autogen_context):
       # SQLModel AutoString → SQLAlchemy 표준 타입
       if type_ == "type" and isinstance(obj, AutoString):
           if obj.length:
               return f"sa.String(length={obj.length})"
           else:
               return "sa.Text()"
   ```

3. **pgvector 지원**:
   - `CREATE EXTENSION IF NOT EXISTS vector` 자동 실행
   - HNSW 인덱스 생성 시 `vector_cosine_ops` 명시
   - 코사인 유사도 검색 최적화

### 마이그레이션 안전성

- ✅ 트랜잭션 DDL 사용 (PostgreSQL 지원)
- ✅ 마이그레이션 실패 시 자동 롤백
- ✅ 타입 변경 자동 감지
- ✅ 서버 기본값 변경 자동 감지

## 향후 과제

1. **마이그레이션 테스트 자동화**
   - 스테이징 환경에서 마이그레이션 사전 테스트
   - 롤백 시나리오 자동 테스트

2. **데이터 마이그레이션 전략**
   - 스키마 변경 + 데이터 변환이 필요한 경우 전략 수립
   - 대용량 테이블 마이그레이션 시 다운타임 최소화 방안

3. **백업 자동화**
   - 프로덕션 마이그레이션 전 자동 백업
   - 복구 절차 문서화

4. **모니터링**
   - 마이그레이션 실행 시간 모니터링
   - 마이그레이션 실패 알림

## 관련 문서

- `backend/README.md`: Alembic 사용법 전체 가이드
- `docs/prd_detail/database-model.md`: 데이터베이스 스키마 명세
- `backend/alembic/env.py`: Alembic 환경 설정
- `backend/alembic.ini`: Alembic 설정 파일
- `.github/workflows/deploy.yml`: CI/CD 배포 워크플로우

## 주의사항

### 프로덕션 배포 시

1. **초기 마이그레이션 적용 시**:
   - 기존 테이블이 있으면 충돌 가능
   - 가능하면 빈 데이터베이스에서 시작
   - 또는 기존 스키마를 Alembic으로 관리하도록 전환 필요

2. **Secrets Manager 설정 확인**:
   - `DATABASE_URL` 환경 변수 필수
   - DB 접근 권한 확인

3. **롤백 준비**:
   - 마이그레이션 전 데이터베이스 백업
   - 롤백 명령어 숙지: `alembic downgrade -1`

### 개발 시

1. **마이그레이션 파일 검토 필수**:
   - autogenerate가 항상 정확하지 않음
   - 특히 복잡한 스키마 변경 시 수동 확인 필요

2. **마이그레이션 파일 편집**:
   - 생성된 후에도 Git commit 전까지 자유롭게 수정 가능
   - 이미 적용된 마이그레이션은 수정 금지

3. **브랜치 병합 시 충돌**:
   - 마이그레이션 파일 타임스탬프로 순서 자동 결정
   - 필요시 `alembic merge` 사용

---

**작성자**: AI Agent  
**작성일**: 2025-10-16  
**관련 브랜치**: feature/llm-basic-chat-pipeline

