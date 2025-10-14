## 데이터베이스 모델링

문서 버전: v1.1  
연관 문서: `docs/PRD.md`, `docs/prd_detail/backend-architecture.md`, `docs/llm/03-database-schema.md`

### 1. 개요

PostgreSQL을 주 데이터베이스로 사용하며, 벡터 검색 기능이 필요한 RAG 문서는 `pgvector` 확장을 활용하여 관리합니다. 모든 테이블은 일관된 명명 규칙을 따르며, 타임스탬프는 UTC 기준의 `timestamptz` 타입을 사용합니다. 벡터 스토어는 법령과 일반 지식을 분리하여 관리합니다.

### 2. ERD (Entity-Relationship Diagram)

```
+--------------+       +--------------+       +---------------+
|   clients    |       |   sessions   |       |    messages   |
|--------------|       |--------------|       |---------------|
| id (PK)      |--(1)  | id (PK)      |--(1)  | id (PK)       |
| client_id_hash|       | client_id_hash|     | session_id (FK)|
| created_at   |       | title        |       | role          |
+--------------+       | created_at   |       | content       |
                       | updated_at   |       | metadata      |
                       +--------------+       | created_at    |
                                              +---------------+

+-------------------+       +---------------------+       +-------------------+
|   law_sources     |       |  knowledge_sources  |       |  tax_rule_config  |
|-------------------|       |---------------------|       |-------------------|
| id (PK)           |       | id (PK)             |       | id (PK)           |
| law_name          |       | source_type         |       | key               |
| full_reference    |       | title               |       | value_json        |
| content           |       | content             |       | effective_from    |
| embedding (vector)|       | embedding (vector)  |       | effective_to      |
| source_url        |       | metadata            |       | created_at        |
| created_at        |       | created_at          |       +-------------------+
| chunk_hash        |       | chunk_hash          |
+-------------------+       +---------------------+
```
*(참고: 위 다이어그램은 텍스트로 표현된 관계도입니다.)*

### 3. 테이블 명세

---

#### `clients`
익명 사용자를 식별하기 위한 테이블. MVP에서는 필수적이지 않으나 확장성을 위해 정의합니다.

| 컬럼명          | 데이터 타입     | 제약 조건                      | 설명                                         |
| :-------------- | :-------------- | :----------------------------- | :------------------------------------------- |
| `id`            | `bigserial`     | `Primary Key`                  | 고유 식별자 (Auto-increment)                 |
| `client_id_hash`| `varchar(64)`   | `Not Null`, `Unique`           | localStorage UUID의 SHA-256 해시값           |
| `created_at`    | `timestamptz`   | `Not Null`, `Default now()`    | 생성 일시                                    |

---

#### `sessions`
사용자와 AI 간의 개별 대화(세션) 정보를 저장합니다.

| 컬럼명          | 데이터 타입     | 제약 조건                      | 설명                                         |
| :-------------- | :-------------- | :----------------------------- | :------------------------------------------- |
| `id`            | `uuid`          | `Primary Key`, `Default gen_random_uuid()` | 고유 세션 ID                                   |
| `client_id_hash`| `varchar(64)`   | `Not Null`                     | `clients.client_id_hash`를 참조하는 외래 키    |
| `title`         | `varchar(255)`  | `Not Null`                     | 세션 제목 (예: "자녀 증여세 상담")         |
| `created_at`    | `timestamptz`   | `Not Null`, `Default now()`    | 생성 일시                                    |
| `updated_at`    | `timestamptz`   | `Not Null`, `Default now()`    | 마지막 수정 일시 (메시지 추가 시 갱신)       |

---

#### `messages`
세션에 속한 개별 메시지를 저장합니다.

| 컬럼명       | 데이터 타입     | 제약 조건                           | 설명                                         |
| :----------- | :-------------- | :---------------------------------- | :------------------------------------------- |
| `id`         | `uuid`          | `Primary Key`, `Default gen_random_uuid()` | 고유 메시지 ID                                 |
| `session_id` | `uuid`          | `Not Null`, `Foreign Key(sessions.id)` | 메시지가 속한 세션 ID                          |
| `role`       | `varchar(16)`   | `Not Null`, `Check in ('user', 'assistant', 'system')` | 메시지 발신자 (사용자, AI, 시스템) |
| `content`    | `text`          | `Not Null`                          | 메시지 본문                                  |
| `metadata`   | `jsonb`         | `Default '{}'`                      | 추가 정보 (인용, 계산 결과 등 구조화된 데이터) |
| `created_at` | `timestamptz`   | `Not Null`, `Default now()`         | 생성 일시                                    |

---

#### `law_sources`
법령과 예규 전문을 벡터 스토어로 관리합니다. 계층 구조(편/장/절/조/항/호)를 보존하여 정밀한 인용이 가능합니다.

| 컬럼명            | 데이터 타입     | 제약 조건                      | 설명                                         |
| :---------------- | :-------------- | :----------------------------- | :------------------------------------------- |
| `id`              | `serial`        | `Primary Key`                  | 고유 문서 조각(chunk) ID                       |
| `chunk_hash`      | `varchar(64)`   | `Not Null`, `Unique`           | 중복 방지를 위한 SHA-256 해시                 |
| `law_name`        | `text`          | `Not Null`                     | 법령 이름 (예: "상속세및증여세법")            |
| `full_reference`  | `text`          | `Not Null`                     | 전체 인용 경로 (예: `제1편 제2장 제53조`)      |
| `content`         | `text`          | `Not Null`                     | 분할된 텍스트 원문 (500자 내외)               |
| `embedding`       | `vector(768)`   |                                | `content` 임베딩                              |
| `source_url`      | `text`          |                                | 법제처 등 원문 링크                           |
| `source_file`     | `text`          |                                | 원본 텍스트 파일 경로                         |
| `created_at`      | `timestamptz`   | `Not Null`, `Default now()`    | 데이터 적재 일시                               |

---

#### `knowledge_sources`
법령 외 Q&A, 사례집 등 보조 지식을 저장합니다.

| 컬럼명            | 데이터 타입     | 제약 조건                      | 설명                                         |
| :---------------- | :-------------- | :----------------------------- | :------------------------------------------- |
| `id`              | `serial`        | `Primary Key`                  | 고유 조각 ID                                 |
| `chunk_hash`      | `varchar(64)`   | `Not Null`, `Unique`           | 중복 방지를 위한 SHA-256 해시                 |
| `source_type`     | `varchar(50)`   | `Not Null`                     | 자료 유형 (예: `qna`, `news`, `case_study`) |
| `title`           | `text`          |                                | 자료 제목 또는 질문                           |
| `content`         | `text`          | `Not Null`                     | 분할된 텍스트 원문                            |
| `embedding`       | `vector(768)`   |                                | `content` 임베딩                              |
| `metadata`        | `jsonb`         | `Not Null`, `Default '{}'`     | 출처별 부가 정보 (예: 태그, 작성일)            |
| `source_url`      | `text`          |                                | 원문 링크                                    |
| `created_at`      | `timestamptz`   | `Not Null`, `Default now()`    | 데이터 적재 일시                               |

---

#### `tax_rule_config`
세율, 공제액 등 자주 변경될 수 있는 세법 규정 수치를 저장하여 코드 변경 없이 계산 로직을 업데이트할 수 있도록 합니다.

| 컬럼명           | 데이터 타입     | 제약 조건                      | 설명                                         |
| :--------------- | :-------------- | :----------------------------- | :------------------------------------------- |
| `id`             | `bigserial`     | `Primary Key`                  | 고유 설정 ID                                 |
| `key`            | `varchar(255)`  | `Not Null`, `Unique`           | 설정 키 (예: `gift_tax_rate_2025`)           |
| `value_json`     | `jsonb`         | `Not Null`                     | 설정 값 (JSON 형식, 예: 세율 구간 정보)    |
| `effective_from` | `date`          | `Not Null`                     | 해당 규정의 효력 시작일                      |
| `effective_to`   | `date`          |                                | 해당 규정의 효력 종료일                      |
| `created_at`     | `timestamptz`   | `Not Null`, `Default now()`    | 레코드 생성 일시                               |

### 4. 인덱스 전략

-   `sessions(client_id_hash, created_at DESC)`: 특정 사용자의 세션 목록을 최신순으로 빠르게 조회.
-   `messages(session_id, created_at DESC)`: 특정 세션의 메시지를 최신순으로 빠르게 조회.
-   `messages USING gin(metadata)`: 메타데이터 JSONB 필드의 키/값 검색 성능 향상.
-   `law_sources USING hnsw(embedding)`: 벡터 유사도 검색 속도 향상. 필요 시 `ivfflat`을 선택적으로 사용.
-   `law_sources(law_name, full_reference)`: 특정 법령 조항 기준 조회 최적화.
-   `knowledge_sources USING hnsw(embedding)`: 보조 지식 벡터 검색 속도 향상.
-   `knowledge_sources(source_type)`: 유형별 자료 필터링 성능 향상.
-   `tax_rule_config(key)`: 특정 규정 키 조회 성능 최적화.
