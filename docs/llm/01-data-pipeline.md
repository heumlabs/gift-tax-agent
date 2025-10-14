# 슈킹(Syuking) 구현 계획서

**문서 버전:** v2.0
**작성일:** 2025-10-14
**연관 문서**: `02-database-schema.md`, `03-message-format.md`

## 1. 개요

슈킹 AI 상담 서비스의 **데이터 파이프라인 및 초기 데이터 로딩**에 집중한 구현 계획입니다.

- **목표**: 법령 텍스트를 처리하여 pgvector에 저장하고 RAG 시스템 구축
- **범위**: 데이터 준비 및 벡터 DB 구축 (상세 상담 플로우는 `docs/prd_detail/ai-logic.md` 참조)

## 2. 기술 스택 요약

- **데이터베이스**: PostgreSQL 14+ + pgvector 0.3.6+
- **임베딩**: Google Gemini text-embedding-004 (768차원)
- **LLM**: Google Gemini 2.5 Pro
- **검색 방식**: Vector Search Only (HNSW 인덱스)

## 3. 구현 단계

### 1단계: DB 스키마 설정

> 상세 스키마는 `02-database-schema.md` 참조

```bash
# pgvector 확장 활성화
psql -d gift_tax_agent -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 테이블 생성 (02-database-schema.md의 SQL 스크립트 실행)
psql -d gift_tax_agent -f backend/database/schema.sql
```

**핵심 테이블**:
- `law_sources`: 법령 벡터 저장 (계층 구조 보존)
- `knowledge_sources`: Q&A, 뉴스 등 지식 저장
- `sessions`, `messages`: 대화 관리
- `tax_rule_config`: 세율/공제액 버전 관리

### 2단계: 법령 데이터 파이프라인 구축

**스크립트**: `backend/scripts/build_law_vector_db.py`

**실행**:
```bash
cd backend
python -m scripts.build_law_vector_db
```

**처리 흐름**:
1. `.dataset/ko-law-parser/law/*.json` 파일 로드
2. 계층 구조 탐색하며 법령 chunk 추출
   - `full_reference` 생성 (예: "상속세및증여세법 제53조 1항")
   - 500자 이내로 분할
3. Gemini Embedding API 배치 호출 (768차원 벡터)
4. `law_sources` 테이블에 INSERT (중복 방지: `chunk_hash`)

**예상 데이터**: 국세 관련 법령 약 5,000~10,000 chunks

### 3단계: 세금 규정 데이터 초기화

**스크립트**: `backend/scripts/seed_tax_rules.py`

```bash
python -m scripts.seed_tax_rules
```

**데이터 예시**:
```json
{
  "key": "gift_tax_deduction_2025",
  "value_json": {
    "spouse": 600000000,
    "lineal_ascendant": 50000000,
    "lineal_descendant": 50000000,
    "others": 10000000
  },
  "effective_from": "2025-01-01"
}
```

**설명**: `ai-logic.md`에서 정의한 TaxCalculationEngine이 참조하는 정형 규칙 데이터(`tax_rule_config` 테이블)를 미리 적재하여, LLM이 회신 과정에서 사용할 세율·공제액이 항상 최신 상태로 유지되도록 합니다. 대화 흐름에서 필요한 변수들이 수집되면 이 테이블의 값으로 결정론적 계산을 수행하고, 그 결과가 최종 답변 합성 단계에 전달됩니다.

### 4단계: LangGraph Workflow 구현

> 상세 설계는 `docs/prd_detail/ai-logic.md` 참조

**핵심 구현 사항**:
- `chalicelib/graph/workflow.py`: LangGraph Workflow 정의
- `chalicelib/tools/search_law.py`: 벡터 검색 Tool
- `chalicelib/services/tax_calculator.py`: 결정론적 세금 계산

**벡터 검색 로직**:
```python
# 1. 사용자 쿼리 임베딩
query_vector = gemini_embedding(user_query)

# 2. pgvector 검색 (코사인 유사도)
results = db.query("""
    SELECT id, content, full_reference, source_url,
           1 - (embedding <=> %s::vector) AS score
    FROM law_sources
    ORDER BY embedding <=> %s::vector
    LIMIT 5
""", (query_vector, query_vector))
```

## 4. 구현 우선순위 (3주 계획)

### Week 1: 데이터 준비
- [ ] PostgreSQL + pgvector 환경 구축
- [ ] DB 스키마 생성 (`02-database-schema.md` 스크립트 실행)
- [ ] 법령 데이터 파이프라인 작성 (`build_law_vector_db.py`)
- [ ] 법령 데이터 임베딩 및 적재 (5,000~10,000 chunks)
- [ ] 벡터 검색 품질 테스트

### Week 2: LangGraph + RAG
- [ ] LangGraph Workflow 구현 (`docs/prd_detail/ai-logic.md` 참조)
- [ ] SearchLawTool 구현 (pgvector 연동)
- [ ] TaxCalculator 구현 (순수 Python)
- [ ] 세금 규정 초기 데이터 적재 (`seed_tax_rules.py`)
- [ ] Workflow 통합 테스트

### Week 3: API + 프론트 연동
- [ ] Chalice API 엔드포인트 구현 (`POST /api/sessions/{id}/messages`)
- [ ] 프론트엔드 연동 및 UI 렌더링
- [ ] E2E 테스트 시나리오 실행
- [ ] Lambda 배포 및 CloudWatch 모니터링 설정

## 5. 향후 개선 사항 (Phase 2)

- **검색 개선**: Reranker 추가 (Cohere API), 하이브리드 검색 (BM25) 검토
- **지식 확장**: `knowledge_sources`에 Q&A, 뉴스 데이터 추가
- **웹 검색**: Tavily API 통합으로 최신 정보 보완
- **스트리밍**: SSE를 통한 실시간 답변 생성
- **규정 최신화**: 법령 개정 자동 업데이트 파이프라인
