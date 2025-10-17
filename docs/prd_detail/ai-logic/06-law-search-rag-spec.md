# Law Search RAG Tool 기능 명세

문서 버전: v1.0
최종 수정: 2025-10-17
연관 문서: `functional-spec.md` (LLM-6.3), `ai-logic.md`

---

## 1. 개요

### 1.1 목적
법령/예규 검색을 통해 LLM 답변의 근거를 제공하는 RAG (Retrieval-Augmented Generation) Tool을 구현합니다.

### 1.2 Tool 정보
- **Tool 이름**: `search_law_tool`
- **현재 상태**: ✅ V3 구현 완료
- **구현 위치**: `ai/tools/law_search/`
- **LangGraph 호환**: O

### 1.3 주요 기능
- 하이브리드 검색 (키워드 30% + 임베딩 70%)
- 법령 원문 및 메타데이터 반환
- 유사도 점수 제공 (confidence 정보)

---

## 2. 아키텍처

### 2.1 데이터베이스

#### 테이블 정보
- **테이블명**: `law_sources_v3`
- **총 레코드**: 2,816개
- **법령 범위**:
  - 상속세및증여세법 (본법 + 시행령 + 시행규칙)
  - 국세기본법 (본법 + 시행령 + 시행규칙)

#### 스키마
```python
class LawSource(SQLModel, table=True):
    id: int
    law_name: str  # 법령명 (예: "상속세및증여세법")
    full_reference: str  # 전체 참조 (예: "상속세및증여세법 제53조(증여재산 공제)")
    content: str  # 원문 텍스트
    full_text_for_embedding: str  # 임베딩용 텍스트
    source_url: str | None  # 법제처 링크
    embedding: list[float]  # 768D 벡터 (정규화됨)
    # ... 기타 필드
```

**참조**: `backend/chalicelib/models/database.py::LawSource`

### 2.2 임베딩 전략

#### 모델 정보
- **모델**: `gemini-embedding-001` (Google Generative AI)
- **차원**: 768D
- **정규화**: O (L2 normalization)
  - 768D, 1536D는 수동 정규화 필요
  - 3072D는 API에서 자동 정규화
- **배치 크기**: 100개

#### 정규화 구현
```python
# ai/clients/gemini.py
if embedding_dimension < 3072:
    import numpy as np
    embedding_np = np.array(embedding)
    normalized = embedding_np / np.linalg.norm(embedding_np)
    return normalized.tolist()
```

#### 정규화 이유
- Cosine similarity 계산 최적화
- PostgreSQL `<=>` 연산자와 호환
- 검색 품질 향상 (V2 대비 +30%p)

### 2.3 검색 알고리즘

#### 하이브리드 검색 구조
```
최종 점수 = (키워드 점수 × 0.3) + (임베딩 점수 × 0.7)
```

#### 키워드 검색 (30%)

**토큰화**:
- 공백 기준 분할
- 최대 3개 키워드 사용

**매칭 필드 및 점수**:
```python
# full_reference (조문명) 매칭: 2.0점
"상속세및증여세법 제53조(증여재산 공제)"

# content (본문) 매칭: 1.0점
"거주자가 다음 각 호의 어느 하나에 해당하는 자로부터..."
```

**점수 정규화**:
```
keyword_score = 총 점수 / (키워드 수 × 3.0)
```

#### 임베딩 검색 (70%)

**프로세스**:
1. 쿼리 임베딩 생성 (자동 정규화)
2. PostgreSQL pgvector로 코사인 유사도 계산
3. 점수 변환: `1 - (embedding <=> query_vector)`

**SQL**:
```sql
1 - (embedding <=> CAST(:query_vector AS vector)) AS embedding_score
```

#### 최종 점수 계산
```sql
SELECT
    law_name,
    full_reference,
    content,
    (
        0.3 * keyword_score +
        0.7 * embedding_score
    ) AS score
FROM law_sources_v3
WHERE embedding IS NOT NULL
ORDER BY score DESC
LIMIT :top_k
```

---

## 3. Tool 인터페이스

### 3.1 함수 시그니처

```python
def search_law_tool(
    query: str,  # 검색 쿼리
    top_k: int = 5,  # 반환 개수 (1~10)
) -> dict  # LawSearchResult
```

**파라미터**:
- `query`: 자연어 또는 키워드 (예: "직계존속 증여재산 공제")
- `top_k`: 결과 개수 (기본 5개, 최소 1, 최대 10)

### 3.2 반환 형식

```python
{
    "citations": [
        {
            "law": "상속세및증여세법",
            "article": "제53조(증여재산 공제)",
            "full_reference": "상속세및증여세법 제53조(증여재산 공제)",
            "content": "거주자가 다음 각 호의 어느 하나에 해당하는 자로부터 증여를 받은 경우...",
            "url": "https://www.law.go.kr/법령/상속세및증여세법",
            "score": 0.8524  # 최종 하이브리드 점수 (0~1)
        },
        // ... top_k개
    ]
}
```

**타입 정의**: `ai/tools/law_search/models.py`
```python
class LawCitation(TypedDict):
    law: str
    article: str
    full_reference: str
    content: str
    url: str | None
    score: float

class LawSearchResult(TypedDict):
    citations: list[LawCitation]
```

### 3.3 내부 구현

#### 파일 구조
```
ai/tools/law_search/
├── __init__.py          # 공개 API
├── wrapper.py           # LangGraph 호환 wrapper
├── searcher.py          # 핵심 검색 로직
├── models.py            # TypedDict 정의
└── query_optimizer.py   # 쿼리 최적화 (선택적)
```

#### 호출 흐름
```
LangGraph Agent
    ↓
search_law_tool (wrapper.py)
    ↓
search_law (searcher.py)
    ↓
GeminiClient.generate_embedding (ai/clients/gemini.py)
    ↓
PostgreSQL + pgvector (law_sources_v3)
```

---

## 4. 설정

### 4.1 환경변수

```bash
# backend/.env

# 임베딩 모델
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
GEMINI_EMBEDDING_DIMENSION=768

# 검색 테이블
LAW_SEARCH_TABLE=law_sources_v3

# 하이브리드 검색 가중치
LAW_SEARCH_KEYWORD_WEIGHT=0.3   # 키워드 30%
LAW_SEARCH_EMBEDDING_WEIGHT=0.7 # 임베딩 70%
```

### 4.2 코드 설정

**설정 파일**: `ai/config.py`

```python
@dataclass(frozen=True)
class GeminiSettings:
    # ...
    embedding_model: str = "gemini-embedding-001"
    embedding_dimension: int = 768
    law_search_table: str = "law_sources_v3"
    law_search_keyword_weight: float = 0.3
    law_search_embedding_weight: float = 0.7
```

### 4.3 설정 우선순위
1. 환경변수 (최우선)
2. 코드 기본값

---

## 5. 성능 벤치마크

### 5.1 테스트 환경

**테스트 데이터**:
- 쿼리 개수: 10개
- 주제: 증여세 관련 (제53조 중심)
- Top-K: 10개
- 평가 기준: 제53조(증여재산 공제) 발견 여부

**테스트 도구**: `ai/scripts/test.py benchmark`

### 5.2 V2 vs V3 비교

| 지표 | V2 (text-embedding-004) | V3 (gemini-001+정규화) | 개선 |
|------|------------------------|----------------------|------|
| **모델** | text-embedding-004 | gemini-embedding-001 | - |
| **정규화** | X | O | - |
| **발견율** | 70% (7/10) | **90% (9/10)** | **+20%p** |
| **Top-3 정확도** | 40% (4/10) | **70% (7/10)** | **+30%p** |
| **평균 순위** | 4.3위 | 2.1위 | -2.2위 |

### 5.3 주요 개선 사례

| 쿼리 | V2 순위 | V3 순위 | 개선 |
|------|---------|---------|------|
| "증여재산 공제" | 8위 | **1위** | ↑7 |
| "직계존속 증여 공제" | 미발견 | **4위** | ✨ |
| "배우자 증여 공제" | 8위 | **1위** | ↑7 |
| "직계존속 5천만원 공제" | 4위 | **1위** | ↑3 |
| "증여세 과세가액 공제" | 미발견 | **5위** | ✨ |

### 5.4 하락 사례

| 쿼리 | V2 순위 | V3 순위 | 변화 |
|------|---------|---------|------|
| "증여세 신고기한" | 1위 | 3위 | ↓2 |

**분석**: 여전히 Top-3 내 유지, 실질적 영향 없음

---

## 6. 제약사항 및 알려진 이슈

### 6.1 띄어쓰기 민감도

**문제**:
```python
search_law_tool("증여재산공제")    # 낮은 점수
search_law_tool("증여재산 공제")   # 높은 점수
```

**원인**: 키워드 매칭은 띄어쓰기에 민감
**영향**: 키워드 30% 비중 → 최종 점수 차이 발생
**해결 방안**: 띄어쓰기 정규화 (07 고도화 문서 참조)

### 6.2 하이브리드 검색의 한계

**시나리오 1**: 조문 번호 검색
```python
search_law_tool("제53조")
# → 키워드만으로 충분하지만 임베딩 검색도 실행 (불필요)
```

**시나리오 2**: 의미 기반 검색
```python
search_law_tool("배우자에게 증여 시 공제는?")
# → 키워드 검색이 노이즈 발생 가능
```

**해결 방안**: Tool 분리 (07 고도화 문서 참조)

### 6.3 Score 필드 노출

**현재 동작**:
- LLM에게 `score` 필드가 그대로 전달됨

**장점**:
- Confidence 정보로 활용 가능
- LLM이 "확실하지 않음" 명시 가능

**단점**:
- 토큰 사용량 증가
- LLM이 점수에 과도하게 의존 가능

**결정**: 현재 유지 (고도화 시 재검토)

### 6.4 데이터베이스 제약

**V2/V3 공존**:
- V2 테이블 (`law_sources_v2`) 유지 중
- 비교 테스트용
- Production 배포 시 V3만 사용 예정

**테이블 크기**:
- 2,816개 레코드 (고정)
- 법령 업데이트 시 재빌드 필요

---

## 7. 버전 히스토리

### V1 (초기 - 2025-10-15)
- **모델**: text-embedding-004
- **검색**: 임베딩만 (100%)
- **테이블**: law_sources
- **성능**: 낮음 (Top-3 < 30%)
- **문제**: 키워드 매칭 부재

### V2 (중간 - 2025-10-16)
- **모델**: text-embedding-004
- **검색**: 하이브리드 도입 (키워드 30% + 임베딩 70%)
- **테이블**: law_sources_v2
- **성능**: 중간 (Top-3 40%)
- **개선**: 하이브리드 검색으로 정확도 향상

### V3 (현재 - 2025-10-17) ✅
- **모델**: gemini-embedding-001
- **차원**: 768D + L2 정규화
- **검색**: 하이브리드 유지
- **테이블**: law_sources_v3
- **성능**: **높음 (Top-3 70%)**
- **개선**:
  - 임베딩 모델 변경
  - 정규화 적용
  - 발견율 +20%p, Top-3 정확도 +30%p

---

## 8. 사용 예시

### 8.1 기본 사용

```python
from ai.tools import search_law_tool

# 기본 검색
result = search_law_tool("배우자 증여 공제", top_k=5)

# 결과 처리
for citation in result["citations"]:
    print(f"[{citation['full_reference']}]")
    print(f"점수: {citation['score']:.4f}")
    print(f"{citation['content'][:100]}...")
```

### 8.2 LangGraph 통합

```python
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from ai.tools import search_law_tool

# Tool 등록
tools = [search_law_tool]

# Agent 생성
agent = create_react_agent(
    model=ChatGoogleGenerativeAI(model="gemini-2.5-flash"),
    tools=tools,
)

# 실행
result = agent.invoke({
    "messages": [("user", "증여세 공제 한도는 얼마인가요?")]
})
```

### 8.3 테스트 CLI

```bash
# 대화형 검색
python ai/scripts/test.py interactive

# V2/V3 비교
python ai/scripts/test.py compare "증여재산 공제"

# 벤치마크
python ai/scripts/test.py benchmark

# 상세 분석
python ai/scripts/test.py test "직계존속 증여" --top-k 10
```

---

## 9. 참조

### 9.1 코드
- **구현**: `ai/tools/law_search/`
- **설정**: `ai/config.py::GeminiSettings`
- **DB 모델**: `backend/chalicelib/models/database.py::LawSource`
- **Gemini Client**: `ai/clients/gemini.py`

### 9.2 문서
- **상위 기획**: `ai-logic.md`
- **기능 명세**: `functional-spec.md` (LLM-6.3)
- **고도화 기획**: `07-law-search-enhancements.md`

### 9.3 테스트
- **CLI 도구**: `ai/scripts/test.py`
- **단위 테스트**: `ai/tests/test_law_search.py`
- **README**: `ai/scripts/README.md`

---

## 10. 다음 단계 (고도화)

**문서 참조**: `07-law-search-enhancements.md`

**주요 Task**:
1. Tool 분리 (keyword / semantic / hybrid)
2. Score threshold 기능
3. 띄어쓰기 정규화
4. Confidence 활용 프롬프트
5. 성능 모니터링

**우선순위**: 07 문서의 Phase 1, 2, 3 참조
