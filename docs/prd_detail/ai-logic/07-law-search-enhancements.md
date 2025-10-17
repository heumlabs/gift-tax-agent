# Law Search RAG 고도화 기획

문서 버전: v1.0
최종 수정: 2025-10-17
연관 문서: `06-law-search-rag-spec.md` (현재 구현), `functional-spec.md`

---

## 1. 현재 구현 분석

### 1.1 구현 범위

**참조**: `06-law-search-rag-spec.md`

**주요 구성**:
- Tool: `search_law_tool` (LangGraph 호환)
- 검색 방식: 하이브리드 (키워드 30% + 임베딩 70%)
- 임베딩: gemini-embedding-001 (768D, 정규화)
- 데이터: law_sources_v3 테이블 (2,816개 레코드)
- 설정: 환경변수로 변경 가능

**테스트 결과** (`ai/scripts/test.py benchmark`):
- 테스트 쿼리: 10개 (증여세 관련)
- V2 대비: 발견율 +20%p (70%→90%), Top-3 정확도 +30%p (40%→70%)

### 1.2 식별된 제약사항

#### A. Tool 설계 제약

**단일 Tool 문제**:
현재 `search_law_tool` 하나만 제공하여 검색 전략 선택 불가

**시나리오 예시**:

```python
# 시나리오 1: 조문 번호로 검색
search_law_tool("제53조")
# → 키워드 검색: ✓ (필요)
# → 임베딩 검색: ✗ (불필요한 연산)

# 시나리오 2: 의미 기반 검색
search_law_tool("배우자에게 증여 시 공제는?")
# → 키워드: "배우자에게", "증여", "시" 분리 (노이즈)
# → 임베딩: ✓ (필요)
```

**영향**:
- 불필요한 연산으로 지연 증가
- 키워드/임베딩 한쪽만 필요한 경우 품질 저하 가능

#### B. 키워드 검색 제약

**B-1. 키워드 개수 제한**

현재 구현:
```python
# ai/tools/law_search/searcher.py
keywords = [kw.strip() for kw in query.strip().split() if kw.strip()]
# 최대 3개만 사용
params = {
    "kw0": keywords[0] if len(keywords) > 0 else "",
    "kw1": keywords[1] if len(keywords) > 1 else "",
    "kw2": keywords[2] if len(keywords) > 2 else "",
}
```

**문제**:
```python
# 4개 이상 키워드 입력 시
search_law_tool("직계존속 증여 재산 공제 한도")
# → "직계존속", "증여", "재산"만 사용
# → "공제", "한도" 무시됨
```

**B-2. 띄어쓰기 민감도**

```python
search_law_tool("증여재산공제")    # 낮은 점수
search_law_tool("증여재산 공제")   # 높은 점수
```

**원인**: 키워드 ILIKE 매칭이 띄어쓰기 의존

#### C. 품질 관리 제약

**C-1. Score threshold 없음**

```python
result = search_law_tool("...", top_k=5)
# citations[4]["score"] = 0.31 (낮은 품질도 반환)
```

**문제**: 저품질 결과가 LLM에게 전달되어 부정확한 답변 생성 가능

**C-2. Confidence 활용 미정의**

- `score` 필드가 LLM에게 전달됨
- 하지만 시스템 프롬프트에 활용 지침 없음
- LLM이 점수 기반 불확실성 명시 불가

#### D. 쿼리 처리 제약

**쿼리 최적화 성능 미흡**:
- `query_optimizer.py` 존재
- 테스트 결과: 개선 효과 없음 (20% → 20%)

**사용자 쿼리 그대로 검색**:
```python
# 현재
"부모님이 돈 주시면 얼마까지 공제?"

# 이상적 (법령 스타일)
"직계존속 증여재산 공제 한도"
```

#### E. 모니터링 제약

- 검색 품질 메트릭 없음
- Tool 사용 패턴 분석 불가
- A/B 테스트 인프라 없음

---

## 2. 고도화 Task 정의

### 2.1 Tool 분리 (우선순위: 높음)

#### 목표
검색 전략별로 3개 Tool 제공하여 LLM이 상황에 맞게 선택

#### 설계

**Tool 1**: `search_law_by_reference`
```python
def search_law_by_reference(
    reference: str,  # 예: "제53조", "상속세및증여세법 시행령"
    top_k: int = 5,
) -> LawSearchResult:
    """조문 번호나 법령명 검색 (키워드 100%)"""
```

**Tool 2**: `search_law_by_semantic`
```python
def search_law_by_semantic(
    query: str,  # 예: "배우자 증여 시 공제 한도"
    top_k: int = 5,
) -> LawSearchResult:
    """의미 기반 검색 (임베딩 100%)"""
```

**Tool 3**: `search_law_hybrid` (현재 구현)
```python
def search_law_hybrid(
    query: str,
    top_k: int = 5,
) -> LawSearchResult:
    """복합 검색 (키워드 30% + 임베딩 70%)"""
```

#### 시스템 프롬프트 가이드

```markdown
# 법령 검색 Tool 선택

1. search_law_by_reference
   - 조문 번호 명시: "제53조", "제26조 2항"
   - 법령명 명시: "상속세및증여세법 시행령"

2. search_law_by_semantic
   - 상황/개념 설명: "배우자 증여 시 공제"
   - 조문 모름

3. search_law_hybrid
   - 혼합: "제53조 관련 증여 공제"
   - 판단 애매함
```

#### 구현 방향

```
ai/tools/law_search/
├── reference_search.py  # Tool 1
├── semantic_search.py   # Tool 2
├── hybrid_search.py     # Tool 3 (searcher.py 리팩토링)
└── wrapper.py           # 3개 모두 export
```

### 2.2 키워드 개수 제한 해제 (우선순위: 높음)

#### 현재 문제
- 최대 3개 키워드만 사용
- 4개 이상 입력 시 뒤쪽 키워드 무시됨

#### 해결 방안

**옵션 1**: 동적 SQL 생성
```python
keywords = query.split()
conditions = " OR ".join([
    f"(full_reference ILIKE :kw{i} OR content ILIKE :kw{i})"
    for i in range(len(keywords))
])
sql = f"... WHERE {conditions} ..."
```

**옵션 2**: PostgreSQL Full-Text Search
```sql
-- tsvector 활용
WHERE to_tsvector('korean', content) @@ to_tsquery('korean', :query)
```

**추천**: 옵션 1 (동적 SQL)
- 구현 간단
- 기존 로직 유지
- PostgreSQL 한국어 Full-Text Search 지원 제한적

### 2.3 Score Threshold (우선순위: 높음)

#### 설계

```python
def search_law_tool(
    query: str,
    top_k: int = 5,
    score_threshold: float | None = None,  # 추가
) -> LawSearchResult:
```

**환경변수**:
```bash
LAW_SEARCH_SCORE_THRESHOLD=0.5  # 기본값
```

**SQL**:
```sql
WHERE embedding IS NOT NULL
  AND score >= :threshold
ORDER BY score DESC
```

**Tool별 기본값**:
```python
search_law_by_reference(..., score_threshold=0.8)  # 높음
search_law_by_semantic(..., score_threshold=0.4)   # 낮음
search_law_hybrid(..., score_threshold=0.5)        # 중간
```

### 2.4 띄어쓰기 정규화 (우선순위: 중간)

#### 옵션 비교

| 옵션 | 장점 | 단점 |
|------|------|------|
| 형태소 분석 (Kiwipiepy) | 정확함 | 74MB (Lambda 제약) |
| 규칙 기반 (용어 사전) | 가볍고 빠름 | 수동 관리 |
| LLM 전처리 | 유연함 | 비용, 지연 |

#### 추천: 하이브리드

```python
def normalize_query(query: str) -> str:
    # 1단계: 규칙 기반 (빠름)
    for term, normalized in COMMON_LAW_TERMS.items():
        query = query.replace(term, normalized)

    # 2단계: 복잡한 경우만 LLM
    if needs_llm_normalization(query):
        query = await normalize_with_llm(query)

    return query
```

**구현**:
- `ai/tools/law_search/normalizer.py` 신규
- 상위 100개 법령 용어 사전
- `searcher.py`에서 전처리 단계 추가

### 2.5 쿼리 최적화 프롬프트 개선 (우선순위: 중간)

#### 현재 문제
- `query_optimizer.py` 성능 미흡
- 프롬프트가 법령 스타일 반영 부족

#### 개선 방향

```python
QUERY_OPTIMIZATION_PROMPT = """
사용자 질문을 법령 원문 스타일로 변환하세요.

# 변환 규칙
1. 구어 → 법률 용어
   "부모님" → "직계존속"
   "돈" → "재산"

2. 구체적 수치 포함
   "한도" → "5천만원 공제 한도" (문맥에 맞게)

3. 법령 표현
   "~하면" → "~한 경우"

4. 간결하게 (5-8 단어)

# 예시
입력: "부모님이 돈 주시면 세금 안 내나요?"
출력: 직계존속 증여 재산 공제 한도

입력: "배우자한테 증여하면?"
출력: 배우자 증여 공제 6억원
"""
```

**Few-shot 예시**: 성공 케이스 10개 추가

### 2.6 Confidence 활용 (우선순위: 중간)

#### 시스템 프롬프트 추가

```markdown
# 검색 결과 Confidence 처리

score 기준:
- 0.7 이상: 확신 있게 답변
- 0.5~0.7: "해당 규정에 따르면..." 표현
- 0.5 미만: 불확실성 명시

낮은 신뢰도 답변:
"검색된 법령의 관련성이 낮아 확실하지 않습니다.
전문가 상담을 권장합니다."
```

#### 메타데이터 확장

```python
{
    "citations": [...],
    "confidence": "high",  # high/medium/low
    "min_score": 0.85
}
```

### 2.7 성능 모니터링 (우선순위: 낮음)

#### 로깅

```python
def log_search_event(tool, query, results, latency_ms):
    logger.info({
        "event": "law_search",
        "tool": tool,
        "query_hash": hash(query),  # PII 제거
        "result_count": len(results),
        "top_score": results[0]["score"] if results else 0,
        "latency_ms": latency_ms
    })
```

#### 메트릭
- Top-K 정확도 (K=1,3,5)
- MRR (Mean Reciprocal Rank)
- Tool 사용 빈도

---

## 3. 보류 Task

### 3.1 MMR (다양성)

**이유**:
- 법령 검색은 "정확한 조문" 찾기가 목표
- 다양성보다 정확성 우선
- 현재 데이터가 조문 단위로 분할되어 중복 적음

### 3.2 Reranker

**검토 필요**:
- Cohere Rerank API: 비용 증가, 지연 +200ms
- Cross-encoder: Lambda 제약

**결정**: Tool 분리/Threshold 먼저 적용 후 재평가

---

## 4. 우선순위 로드맵

### Phase 1: 핵심 개선

| Task | 우선순위 | 예상 공수 |
|------|---------|----------|
| Tool 3개 분리 | 높음 | 3일 |
| 키워드 개수 제한 해제 | 높음 | 1일 |
| Score threshold | 높음 | 1일 |
| Confidence 프롬프트 | 중간 | 1일 |

**목표**: 검색 전략 선택 가능, 저품질 결과 제거

### Phase 2: 품질 개선

| Task | 우선순위 | 예상 공수 |
|------|---------|----------|
| 띄어쓰기 정규화 | 중간 | 2일 |
| 쿼리 최적화 개선 | 중간 | 2일 |
| 모니터링 로깅 | 낮음 | 2일 |

**목표**: 검색 품질 향상, 모니터링 기반 구축

### Phase 3: 실험적 개선

| Task | 조건 |
|------|------|
| MMR | Phase 2 후 필요성 재평가 |
| Reranker | 비용/성능 분석 후 결정 |

---

## 5. functional-spec.md 반영

### LLM-14.4 Law Search 고도화 (신규)

```markdown
### LLM-14.4 Law Search Tool 고도화
- **Linked Spec**: `07-law-search-enhancements.md`
- **Tasks**
  - [ ] `LLM-14.4.a` Tool 3개 분리 (reference/semantic/hybrid) (Owner: TBD)
  - [ ] `LLM-14.4.b` 키워드 개수 제한 해제 (동적 SQL) (Owner: TBD)
  - [ ] `LLM-14.4.c` Score threshold 파라미터 추가 (Owner: TBD)
  - [ ] `LLM-14.4.d` Confidence 기반 답변 가이드 프롬프트 (Owner: TBD)
  - [ ] `LLM-14.4.e` 띄어쓰기 정규화 (규칙 기반) (Owner: TBD)
  - [ ] `LLM-14.4.f` 쿼리 최적화 프롬프트 개선 (Owner: TBD)
```

---

## 6. GitHub Issues 제안

### Issue #XX: Law Search Tool 분리 및 키워드 개선

**라벨**: `enhancement`, `rag`, `phase-1`

```markdown
## 목표
검색 전략별 Tool 분리 및 키워드 제한 해제

## Tasks
- [ ] 3개 Tool 구현 (reference/semantic/hybrid)
- [ ] 키워드 개수 제한 해제 (동적 SQL)
- [ ] 시스템 프롬프트 Tool 선택 가이드
- [ ] 단위 테스트
- [ ] 벤치마크 비교

## 완료 기준
- 3개 Tool 동작 확인
- 4개 이상 키워드 검색 테스트
```

### Issue #XX: Score Threshold 및 Confidence

**라벨**: `enhancement`, `rag`, `phase-1`

```markdown
## 목표
저품질 결과 필터링 및 LLM confidence 처리

## Tasks
- [ ] score_threshold 파라미터 추가
- [ ] 환경변수 지원
- [ ] Confidence 프롬프트 추가
- [ ] 메타데이터 확장

## 완료 기준
- Threshold 동작 확인
- LLM 불확실성 명시 테스트
```

### Issue #XX: 띄어쓰기 정규화 및 쿼리 최적화

**라벨**: `enhancement`, `rag`, `phase-2`

```markdown
## 목표
띄어쓰기 오류 해결 및 쿼리 품질 향상

## Tasks
- [ ] 법령 용어 사전 작성 (100개)
- [ ] normalizer.py 구현
- [ ] 쿼리 최적화 프롬프트 개선
- [ ] Few-shot 예시 추가

## 완료 기준
- 띄어쓰기 케이스 개선
- 벤치마크 재실행
```

---

## 7. 참조

- **현재 구현**: `06-law-search-rag-spec.md`
- **코드**: `ai/tools/law_search/`
- **테스트**: `ai/scripts/test.py`
- **기능 명세**: `functional-spec.md`
