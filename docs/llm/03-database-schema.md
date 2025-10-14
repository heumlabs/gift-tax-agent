# 데이터베이스 스키마 설계

**문서 버전**: v1.0
**작성일**: 2025-10-14
**연관 문서**: `docs/PRD.md`, `docs/prd_detail/api-spec.md`, `01-data-pipeline.md`

## 1. 개요

슈킹 AI 상담 서비스를 위한 통합 데이터베이스 스키마입니다.
- **DBMS**: PostgreSQL 14 이상
- **확장**: pgvector (벡터 검색용)
- **ORM**: SQLAlchemy 2.0
- **특징**:
  - 익명 사용자 기반 (로그인 없음, `client_id` 기반)
  - RAG용 하이브리드 테이블 (법령 + 지식)
  - 채팅 세션 및 메시지 이력 관리
  - 세금 규정 버전 관리

## 2. ERD (Entity-Relationship Diagram)

### 2.1. DBML (dbdiagram.io)

```dbml
// 슈킹 AI 상담 서비스 데이터베이스 스키마
// https://dbdiagram.io 에서 시각화 가능

Table sessions {
  id uuid [pk, default: `gen_random_uuid()`]
  client_id_hash varchar(64) [not null, note: 'SHA-256 해시']
  title varchar(255) [not null, default: '새로운 상담']
  created_at timestamptz [not null, default: `now()`]
  updated_at timestamptz [not null, default: `now()`]

  indexes {
    (client_id_hash, created_at) [name: 'idx_sessions_client_created']
  }

  Note: '사용자 채팅 세션 (익명 사용자 기반)'
}

Table messages {
  id uuid [pk, default: `gen_random_uuid()`]
  session_id uuid [not null]
  role varchar(16) [not null, note: 'user, assistant, system']
  content text [not null]
  metadata jsonb [default: '{}', note: 'citations, calculation, tool_calls 등']
  created_at timestamptz [not null, default: `now()`]

  indexes {
    (session_id, created_at) [name: 'idx_messages_session_created']
    metadata [type: gin, name: 'idx_messages_metadata']
  }

  Note: '세션별 대화 메시지'
}

Table law_sources {
  id serial [pk]
  chunk_hash varchar(64) [unique, not null, note: '중복 방지용 SHA-256']
  law_name text [not null, note: '예: 상속세및증여세법']
  part text [note: '편']
  chapter text [note: '장']
  section text [note: '절']
  sub_section text [note: '관']
  article text [note: '조']
  paragraph text [note: '항']
  item text [note: '호']
  sub_item text [note: '목']
  full_reference text [not null, note: '전체 인용 경로']
  content text [not null, note: '법령 원문 (500자 이내)']
  embedding vector(768) [note: 'Gemini text-embedding-004']
  source_url text [note: '법제처 원문 링크']
  source_file text [note: '원본 txt 파일']
  created_at timestamptz [not null, default: `now()`]

  indexes {
    (law_name, article) [name: 'idx_law_name_article']
    embedding [type: hnsw, name: 'idx_law_embedding', note: 'vector_cosine_ops']
  }

  Note: '법령 벡터 저장소 (계층 구조 보존)'
}

Table knowledge_sources {
  id serial [pk]
  chunk_hash varchar(64) [unique, not null]
  source_type varchar(50) [not null, note: 'qna, news, web_search, case_study']
  title text [note: '제목 또는 질문']
  content text [not null]
  embedding vector(768)
  metadata jsonb [not null, default: '{}', note: '소스별 고유 정보']
  source_url text
  created_at timestamptz [not null, default: `now()`]

  indexes {
    source_type [name: 'idx_knowledge_type']
    metadata [type: gin, name: 'idx_knowledge_metadata']
    embedding [type: hnsw, name: 'idx_knowledge_embedding', note: 'vector_cosine_ops']
  }

  Note: '기타 지식 벡터 저장소 (Q&A, 뉴스 등)'
}

Table tax_rule_config {
  id serial [pk]
  key varchar(255) [unique, not null, note: '예: gift_tax_rate_2025']
  value_json jsonb [not null, note: '세율, 공제액 등']
  effective_from date [not null]
  effective_to date [note: 'NULL = 현재 유효']
  created_at timestamptz [not null, default: `now()`]

  indexes {
    key [name: 'idx_tax_config_key']
    (effective_from, effective_to) [name: 'idx_tax_config_effective']
  }

  Note: '세금 규정 버전 관리'
}

// Relationships
Ref: messages.session_id > sessions.id [delete: cascade]
```

### 2.2. ERD 이미지 생성 방법

1. https://dbdiagram.io 접속
2. 위 DBML 코드 복사
3. 좌측 에디터에 붙여넣기
4. Export → PNG/PDF 다운로드

또는 CLI 사용:
```bash
# dbml2sql 설치
npm install -g @dbml/cli

# SQL 변환
dbml2sql database-schema.dbml --postgres -o schema.sql
```

## 3. 테이블 상세 명세

### 3.1. sessions (채팅 세션)

사용자와 AI 간의 개별 대화 세션을 관리합니다.

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
|--------|------------|----------|------|
| `id` | `UUID` | `PRIMARY KEY`, `DEFAULT gen_random_uuid()` | 고유 세션 ID |
| `client_id_hash` | `VARCHAR(64)` | `NOT NULL`, `INDEX` | 익명 클라이언트 식별자 (SHA-256 해시) |
| `title` | `VARCHAR(255)` | `NOT NULL`, `DEFAULT '새로운 상담'` | 세션 제목 (사용자 편집 가능) |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL`, `DEFAULT NOW()` | 생성 일시 |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL`, `DEFAULT NOW()` | 마지막 메시지 시각 (트리거로 자동 갱신) |

**인덱스**:
```sql
CREATE INDEX idx_sessions_client_created ON sessions(client_id_hash, created_at DESC);
```

**비고**:
- `client_id`는 프론트엔드 localStorage의 UUID를 서버에서 SHA-256 해시한 값
- 로그인 기능 없음, 브라우저별로 독립적인 세션 관리

---

### 3.2. messages (채팅 메시지)

세션에 속한 사용자 및 AI 메시지를 저장합니다.

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
|--------|------------|----------|------|
| `id` | `UUID` | `PRIMARY KEY`, `DEFAULT gen_random_uuid()` | 고유 메시지 ID |
| `session_id` | `UUID` | `NOT NULL`, `FOREIGN KEY(sessions.id) ON DELETE CASCADE` | 소속 세션 ID |
| `role` | `VARCHAR(16)` | `NOT NULL`, `CHECK IN ('user', 'assistant', 'system')` | 발신자 역할 |
| `content` | `TEXT` | `NOT NULL` | 메시지 본문 |
| `metadata` | `JSONB` | `DEFAULT '{}'` | 구조화된 추가 정보 (아래 참조) |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL`, `DEFAULT NOW()` | 생성 일시 |

**metadata JSONB 구조 예시**:
```json
{
  "citations": [
    {
      "law": "상속세및증여세법",
      "article": "제53조",
      "full_reference": "상속세및증여세법 제1장 총칙 제53조",
      "url": "https://www.law.go.kr/..."
    }
  ],
  "calculation": {
    "assumptions": ["거주자 간 증여", "과거 10년 증여 없음"],
    "taxableAmount": 100000000,
    "deduction": 600000000,
    "finalTax": 0
  },
  "tool_calls": [
    {
      "tool": "search_law",
      "query": "배우자 증여재산 공제",
      "results_count": 5
    }
  ],
  "tokens": {
    "input": 1234,
    "output": 567
  },
  "latency_ms": 3421
}
```

**인덱스**:
```sql
CREATE INDEX idx_messages_session_created ON messages(session_id, created_at ASC);
CREATE INDEX idx_messages_metadata ON messages USING GIN(metadata);
```

**비고**:
- `role='system'`은 내부 프롬프트 디버깅용 (선택)
- `metadata`에 tool 호출 이력, 인용, 계산 결과 등 구조화된 데이터 저장

---

### 3.3. law_sources (법령 벡터 저장소)

법령 문서의 계층 구조를 보존하며 벡터 검색을 지원합니다.

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
|--------|------------|----------|------|
| `id` | `SERIAL` | `PRIMARY KEY` | 고유 청크 ID |
| `chunk_hash` | `VARCHAR(64)` | `UNIQUE`, `NOT NULL` | 콘텐츠 SHA-256 해시 (중복 방지) |
| `law_name` | `TEXT` | `NOT NULL`, `INDEX` | 법령명 (예: "상속세및증여세법") |
| `part` | `TEXT` | | 편 (예: "제1편") |
| `chapter` | `TEXT` | | 장 (예: "제1장 총칙") |
| `section` | `TEXT` | | 절 (예: "제1절 통칙") |
| `sub_section` | `TEXT` | | 관 (드물게 존재) |
| `article` | `TEXT` | `INDEX` | 조 (예: "제53조") |
| `paragraph` | `TEXT` | | 항 (예: "1항") |
| `item` | `TEXT` | | 호 (예: "1호") |
| `sub_item` | `TEXT` | | 목 (예: "가목") |
| `full_reference` | `TEXT` | `NOT NULL` | 인용 경로 (예: "상속세및증여세법 제1장 총칙 제53조 1항") |
| `content` | `TEXT` | `NOT NULL` | 법령 조각 원문 (500자 이내 권장) |
| `embedding` | `VECTOR(768)` | | Gemini text-embedding-004 벡터 |
| `source_url` | `TEXT` | | 법제처 원문 링크 |
| `source_file` | `TEXT` | | 원본 txt 파일 경로 (추적용) |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL`, `DEFAULT NOW()` | 생성 일시 |

**인덱스**:
```sql
CREATE INDEX idx_law_name_article ON law_sources(law_name, article);
CREATE INDEX idx_law_embedding ON law_sources USING hnsw(embedding vector_cosine_ops);
```

**비고**:
- HNSW 인덱스는 IVFFlat보다 빠르고 정확함 (pgvector 0.5.0+)
- `chunk_hash`로 동일 내용 중복 삽입 방지
- 계층 컬럼(`part`, `chapter` 등)은 정확한 조문 인용을 위해 필수

---

### 3.4. knowledge_sources (기타 지식 벡터 저장소)

Q&A, 뉴스, 웹 검색 등 법령 외 지식을 유연하게 관리합니다.

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
|--------|------------|----------|------|
| `id` | `SERIAL` | `PRIMARY KEY` | 고유 청크 ID |
| `chunk_hash` | `VARCHAR(64)` | `UNIQUE`, `NOT NULL` | 콘텐츠 SHA-256 해시 |
| `source_type` | `VARCHAR(50)` | `NOT NULL`, `INDEX` | 소스 유형 (qna, news, web_search, case_study) |
| `title` | `TEXT` | | 제목 또는 질문 |
| `content` | `TEXT` | `NOT NULL` | 본문 또는 답변 |
| `embedding` | `VECTOR(768)` | | Gemini 임베딩 벡터 |
| `metadata` | `JSONB` | `NOT NULL`, `DEFAULT '{}'` | 소스별 고유 메타데이터 (아래 참조) |
| `source_url` | `TEXT` | | 원본 URL |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL`, `DEFAULT NOW()` | 생성 일시 |

**metadata JSONB 구조 예시**:
```json
// source_type='qna'
{
  "platform": "네이버지식인",
  "category": "증여세",
  "upvotes": 42,
  "tags": ["배우자공제", "부동산"]
}

// source_type='news'
{
  "publisher": "조세일보",
  "published_date": "2024-03-15",
  "category": "세법개정",
  "keywords": ["증여세", "공제한도"]
}

// source_type='web_search'
{
  "crawled_date": "2024-10-14",
  "domain": "nts.go.kr",
  "relevance_score": 0.95
}
```

**인덱스**:
```sql
CREATE INDEX idx_knowledge_type ON knowledge_sources(source_type);
CREATE INDEX idx_knowledge_metadata ON knowledge_sources USING GIN(metadata);
CREATE INDEX idx_knowledge_embedding ON knowledge_sources USING hnsw(embedding vector_cosine_ops);
```

**비고**:
- `source_type`으로 소스별 필터링 및 가중치 적용 가능
- 새로운 소스 추가시 스키마 변경 불필요 (JSONB 활용)

---

### 3.5. tax_rule_config (세금 규정 설정)

세율, 공제액 등 변경 가능한 세법 규정 수치를 버전 관리합니다.

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
|--------|------------|----------|------|
| `id` | `SERIAL` | `PRIMARY KEY` | 고유 설정 ID |
| `key` | `VARCHAR(255)` | `UNIQUE`, `NOT NULL` | 설정 키 (예: `gift_tax_rate_2025`) |
| `value_json` | `JSONB` | `NOT NULL` | 설정 값 (JSON 형식, 아래 참조) |
| `effective_from` | `DATE` | `NOT NULL` | 효력 시작일 |
| `effective_to` | `DATE` | | 효력 종료일 (NULL = 현재 유효) |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL`, `DEFAULT NOW()` | 레코드 생성 일시 |

**value_json 구조 예시**:
```json
// key='gift_tax_deduction_2025'
{
  "spouse": 600000000,
  "lineal_ascendant": 50000000,
  "lineal_ascendant_minor": 20000000,
  "others": 10000000
}

// key='gift_tax_rate_2025'
{
  "brackets": [
    {"max": 100000000, "rate": 0.10, "deduction": 0},
    {"max": 500000000, "rate": 0.20, "deduction": 10000000},
    {"max": 1000000000, "rate": 0.30, "deduction": 60000000},
    {"max": 3000000000, "rate": 0.40, "deduction": 160000000},
    {"max": null, "rate": 0.50, "deduction": 460000000}
  ]
}
```

**인덱스**:
```sql
CREATE INDEX idx_tax_config_key ON tax_rule_config(key);
CREATE INDEX idx_tax_config_effective ON tax_rule_config(effective_from, effective_to);
```

**비고**:
- 세법 개정시 코드 변경 없이 DB만 업데이트
- `effective_to IS NULL`인 레코드가 현재 유효한 규정
- TaxCalculator가 현재 날짜 기준으로 적용할 규정 조회

---

## 4. 초기화 스크립트

### 4.1. 확장 설치

```sql
-- PostgreSQL 확장 활성화
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

### 4.2. 테이블 생성 순서

```sql
-- 1. 세션 테이블
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id_hash VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL DEFAULT '새로운 상담',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sessions_client_created ON sessions(client_id_hash, created_at DESC);

-- 2. 메시지 테이블
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(16) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_messages_session_created ON messages(session_id, created_at ASC);
CREATE INDEX idx_messages_metadata ON messages USING GIN(metadata);

-- 3. 법령 벡터 저장소
CREATE TABLE law_sources (
    id SERIAL PRIMARY KEY,
    chunk_hash VARCHAR(64) UNIQUE NOT NULL,
    law_name TEXT NOT NULL,
    part TEXT,
    chapter TEXT,
    section TEXT,
    sub_section TEXT,
    article TEXT,
    paragraph TEXT,
    item TEXT,
    sub_item TEXT,
    full_reference TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(768),
    source_url TEXT,
    source_file TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_law_name_article ON law_sources(law_name, article);
CREATE INDEX idx_law_embedding ON law_sources USING hnsw(embedding vector_cosine_ops);

-- 4. 기타 지식 벡터 저장소
CREATE TABLE knowledge_sources (
    id SERIAL PRIMARY KEY,
    chunk_hash VARCHAR(64) UNIQUE NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    title TEXT,
    content TEXT NOT NULL,
    embedding VECTOR(768),
    metadata JSONB NOT NULL DEFAULT '{}',
    source_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_knowledge_type ON knowledge_sources(source_type);
CREATE INDEX idx_knowledge_metadata ON knowledge_sources USING GIN(metadata);
CREATE INDEX idx_knowledge_embedding ON knowledge_sources USING hnsw(embedding vector_cosine_ops);

-- 5. 세금 규정 설정
CREATE TABLE tax_rule_config (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value_json JSONB NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tax_config_key ON tax_rule_config(key);
CREATE INDEX idx_tax_config_effective ON tax_rule_config(effective_from, effective_to);
```

### 4.3. 트리거 (세션 updated_at 자동 갱신)

```sql
CREATE OR REPLACE FUNCTION update_session_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE sessions
    SET updated_at = NOW()
    WHERE id = NEW.session_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_session_timestamp
AFTER INSERT ON messages
FOR EACH ROW
EXECUTE FUNCTION update_session_timestamp();
```

---

## 5. 데이터 관리 정책

### 5.1. 데이터 보관 기간

| 테이블 | 보관 기간 | 삭제 정책 |
|--------|----------|----------|
| `sessions` | 1년 | 마지막 메시지 이후 1년 경과시 자동 삭제 (cron) |
| `messages` | 1년 | 세션 삭제시 CASCADE 자동 삭제 |
| `law_sources` | 영구 | 법령 개정시 obsolete 마킹 후 보관 |
| `knowledge_sources` | 2년 | 관련성 낮은 데이터 주기적 정리 |
| `tax_rule_config` | 영구 | 이력 관리용 |

### 5.2. 백업 전략

- **일일 백업**: 전체 DB 덤프 (S3 저장)
- **실시간 복제**: RDS Read Replica 또는 Aurora
- **벡터 인덱스 재구축**: 주간 1회 (성능 최적화)

### 5.3. 보안

- `client_id_hash`: SHA-256 해시, 원본 UUID 서버 저장 금지
- 메시지 내용: KMS 암호화 (at-rest)
- 개인식별정보(PII): 수집 금지 원칙

---

## 6. 성능 고려사항

### 6.1. 벡터 검색 최적화

```sql
-- HNSW 인덱스 파라미터 튜닝 (데이터 크기에 따라 조정)
CREATE INDEX idx_law_embedding ON law_sources
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 검색 정확도 vs 속도 조정 (세션별 설정 가능)
SET hnsw.ef_search = 40;  -- 기본값, 높을수록 정확하지만 느림
```

### 6.2. 쿼리 최적화 예시

```sql
-- 하이브리드 검색: 벡터 + 키워드 결합
WITH vector_search AS (
    SELECT id, content, full_reference,
           1 - (embedding <=> %s::vector) AS vector_score
    FROM law_sources
    ORDER BY embedding <=> %s::vector
    LIMIT 20
),
ranked_results AS (
    SELECT *,
           vector_score * 0.7 AS final_score  -- 가중치 조정 가능
    FROM vector_search
)
SELECT * FROM ranked_results
ORDER BY final_score DESC
LIMIT 10;
```

### 6.3. 연결 풀링

- SQLAlchemy 연결 풀: `pool_size=10`, `max_overflow=20`
- Lambda 환경: 연결 재사용 (`pool_pre_ping=True`)

---

## 7. 마이그레이션 계획

### 7.1. 초기 데이터 로딩

1. **법령 데이터**: `scripts/build_law_vector_db.py`
   - `.dataset/ko-law-parser/law/*.json` → `law_sources`
   - 약 10,000 청크 예상

2. **세금 규정**: `scripts/seed_tax_rules.py`
   - 2025년 기준 세율/공제액 → `tax_rule_config`

3. **지식 데이터** (선택): `scripts/build_knowledge_vector_db.py`
   - Q&A, 뉴스 크롤링 → `knowledge_sources`

### 7.2. 스키마 버전 관리

- **도구**: Alembic (SQLAlchemy 마이그레이션 도구)
- **버전**: `alembic/versions/001_initial_schema.py`

---

## 8. 부록: 샘플 데이터

### 8.1. tax_rule_config 초기 데이터

```sql
-- 2025년 증여세 공제액
INSERT INTO tax_rule_config (key, value_json, effective_from, effective_to)
VALUES (
    'gift_tax_deduction_2025',
    '{
        "spouse": 600000000,
        "lineal_ascendant": 50000000,
        "lineal_ascendant_minor": 20000000,
        "lineal_descendant": 50000000,
        "lineal_descendant_minor": 20000000,
        "others": 10000000
    }',
    '2025-01-01',
    NULL
);

-- 2025년 증여세율
INSERT INTO tax_rule_config (key, value_json, effective_from, effective_to)
VALUES (
    'gift_tax_rate_2025',
    '{
        "brackets": [
            {"max": 100000000, "rate": 0.10, "deduction": 0},
            {"max": 500000000, "rate": 0.20, "deduction": 10000000},
            {"max": 1000000000, "rate": 0.30, "deduction": 60000000},
            {"max": 3000000000, "rate": 0.40, "deduction": 160000000},
            {"max": null, "rate": 0.50, "deduction": 460000000}
        ]
    }',
    '2025-01-01',
    NULL
);
```

### 8.2. 세션/메시지 샘플 데이터

```sql
-- 테스트 세션
INSERT INTO sessions (id, client_id_hash, title)
VALUES (
    'e7b2d3a0-3b8b-4b4e-9b0a-7e1d6e8e1d6e',
    'a1b2c3d4e5f6...',  -- SHA-256 해시
    '배우자 증여세 상담'
);

-- 테스트 메시지
INSERT INTO messages (session_id, role, content, metadata)
VALUES (
    'e7b2d3a0-3b8b-4b4e-9b0a-7e1d6e8e1d6e',
    'user',
    '배우자에게 1억원 증여시 세금은?',
    '{}'
);

INSERT INTO messages (session_id, role, content, metadata)
VALUES (
    'e7b2d3a0-3b8b-4b4e-9b0a-7e1d6e8e1d6e',
    'assistant',
    '배우자 간 증여는 10년간 6억원까지 공제되므로 납부세액이 없습니다.',
    '{
        "citations": [
            {
                "law": "상속세및증여세법",
                "article": "제53조",
                "url": "https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=123456"
            }
        ],
        "calculation": {
            "assumptions": ["거주자 간 증여", "과거 10년 증여 없음"],
            "taxableAmount": 100000000,
            "deduction": 600000000,
            "finalTax": 0
        }
    }'
);
```

---

## 9. 다음 단계

1. ✅ DB 스키마 검토 및 승인
2. ⏭️ 로컬 PostgreSQL 환경 구축
3. ⏭️ 초기화 스크립트 실행 및 테스트
4. ⏭️ 법령 데이터 로딩 스크립트 개발 (`scripts/build_law_vector_db.py`)
5. ⏭️ SQLAlchemy 모델 정의 (`chalicelib/db/models.py`)
