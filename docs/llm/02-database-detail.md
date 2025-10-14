# LLM 데이터베이스 메모

**문서 버전**: v2.0  
**작성일**: 2025-10-14  
**연관 문서**: `docs/prd_detail/database-model.md`, `01-data-pipeline.md`

## 1. 범위

이 문서는 **LLM 팀이 직접 관리·활용하는 데이터 구조**만 다룹니다. 전체 서비스 스키마(세션, 메시지 등)는 PRD 산출물인 `docs/prd_detail/database-model.md`를 단일 진실 소스로 삼습니다. 중복 정의를 피하기 위해 이 문서에서는 LLM 파이프라인에 특화된 테이블과 인덱스, 운영 정책만 명시합니다.

## 2. LLM 핵심 테이블

### 2.1. `law_sources`
- 목적: 법령·예규 원문을 조 단위로 벡터화하여 보관  
- 주요 컬럼
  - `chunk_hash` (`varchar(64)`, unique): 중복 방지용 SHA-256
  - `law_name`, `full_reference`: 법령명과 계층형 인용 경로
  - `content` (`text`): 500자 내외의 원문 조각
  - `embedding` (`vector(768)`): Gemini `text-embedding-004` 결과
  - `source_url`, `source_file`: 원본 추적 메타데이터
- 필수 인덱스
  - `embedding`에 `USING hnsw` (vector_cosine_ops)
  - `law_name, full_reference` 복합 인덱스 (법령/조문 조회용)

### 2.2. `knowledge_sources`
- 목적: FAQ, Q&A, 뉴스 등 비법령 지식의 벡터 저장소  
- 주요 컬럼: `chunk_hash`, `source_type`, `title`, `content`, `embedding`, `metadata`, `source_url`, `created_at`
- 필수 인덱스
  - `embedding`에 `USING hnsw`
  - `source_type` (필터링)
  - `metadata`에 GIN (태그 검색)

### 2.3. `tax_rule_config`
- 목적: 세율/공제 등 결정론적 계산에 쓰이는 규칙 데이터의 버전 관리  
- 주요 컬럼: `key`, `value_json`, `effective_from`, `effective_to`, `created_at`
- 주의 사항
  - `value_json`은 범용 구조를 허용하지만, 최소 키(`bracket`, `rate`, `deduction` 등)는 문서화하여 공유
  - 연도별로 신규 레코드를 추가하고, 폐기 시 `effective_to`를 설정

### 2.4. `messages.metadata` (참조만)
- LLM 파이프라인은 메시지 테이블의 `metadata` JSONB에 계산 결과, 인용, 도구 호출 로그를 기록합니다.
- JSON 스키마 요약
  - `citations[]`: `law`, `article`, `full_reference`, `url`
  - `calculation`: `assumptions`, `taxableAmount`, `deduction`, `finalTax`
  - `tool_calls[]`: `tool`, `query`, `results_count`
- 인덱스: `GIN` (`messages USING gin(metadata)`) — PRD 문서에서 관리되지만, LLM 팀은 키 충돌 없이 구조를 유지해야 합니다.

## 3. 운영 가이드

- **데이터 적재**
  - 법령/지식 데이터는 `.dataset/ko-law-parser`에서 생성된 JSON을 `build_law_vector_db.py`로 배치 적재
  - 세율·공제 정보는 `seed_tax_rules.py`로 삽입하되, 수동 입력 시에도 동일 스키마 준수
- **임베딩 모델 변경 시**
  - `embedding` 차원이 바뀌면 pgvector 컬럼 재생성 또는 새 컬럼 추가가 필요하므로 사전 협의 필수
  - 기존 데이터와 혼재할 경우 `embedding_model` 컬럼을 추가하거나 테이블을 분리하는 방식을 고려
- **데이터 정합성 점검**
  - `chunk_hash`/`source_url` 기반 중복 체크
  - `tax_rule_config`는 주 1회 이상 유효 기간 겹침 검증 (배치 스크립트에 포함 예정)

## 4. 향후 과제

1. `tax_rule_config` 구조 표준화 (세액 계산 엔진과 합의된 JSON 스키마 정의)
2. 법령/지식 데이터에 대한 변경 이력 관리(`*_history` 테이블 또는 S3 버전 아카이브)
3. `messages.metadata` JSON 스키마에 대한 자동 검증 파이프라인 도입 (pydantic 등)

---

> 전체 데이터베이스 개요, 컬럼 타입, 제약 조건 등의 세부 사항은 `docs/prd_detail/database-model.md`를 참고하세요.
