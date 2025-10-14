# 기술 스택 및 구현 방향

**문서 버전**: v2.0
**작성일**: 2025-10-14
**연관 문서**: `docs/PRD.md`, `03-database-schema.md`, `04-message-format.md`

## 1. 개요

슈킹 AI 상담 서비스의 최종 확정 기술 스택과 구현 방향을 정의합니다.

### 1.1. 핵심 설계 원칙

1. **LangGraph Workflow**: 명시적 상태 관리 및 대화 흐름 제어
2. **LangChain Tools**: 검색, 계산 등 기능을 Tool로 모듈화
3. **Vector Search**: pgvector 단독 사용
4. **결정론적 계산**: 세금 계산은 Python 함수로 처리 (LLM 환각 방지)

---

## 2. 최종 기술 스택

### 2.1. 백엔드 프레임워크

| 구분 | 기술 | 버전 | 역할 |
|------|------|------|------|
| **API 서버** | AWS Chalice | 1.31.2 | REST API (Lambda + API Gateway) |
| **데이터베이스** | PostgreSQL | 14+ | 세션, 메시지, RAG 벡터 저장 |
| **벡터 확장** | pgvector | 0.3.6+ | HNSW 벡터 인덱스 |
| **ORM** | SQLAlchemy | 2.0.32 | DB 접근 계층 |

### 2.2. AI/LLM 스택

| 구분 | 기술 | 버전 | 역할 |
|------|------|------|------|
| **LLM** | Google Gemini 2.5 Pro | - | 대화 생성, 의도 파악 |
| **Embedding** | Gemini text-embedding-004 | - | 768차원 벡터 생성 |
| **Agent Framework** | LangGraph | 0.2.60+ | Workflow 상태 관리 |
| **Tools** | LangChain | 0.3.10+ | Tool 인터페이스 및 RAG |

### 2.3. RAG 스택

| 구분 | 기술 | 역할 |
|------|------|------|
| **Vector Store** | PGVector (LangChain) | pgvector 연동 |
| **Embedding** | GoogleGenerativeAIEmbeddings | 법령 텍스트 임베딩 |
| **검색 방식** | Similarity Search | 코사인 유사도 기반 |

### 2.4. 패키지 의존성

```txt
# requirements.txt

# 기존 (유지)
chalice==1.31.2
psycopg2-binary==2.9.9
SQLAlchemy==2.0.32
python-dotenv==1.0.1
pydantic==2.9.2
pgvector==0.3.6

# AI/LLM
google-generativeai==0.8.3

# LangChain/LangGraph
langchain==0.3.10
langchain-google-genai==2.0.8
langchain-postgres==0.0.12
langchain-community==0.3.10
langgraph==0.2.60

# 유틸리티
requests==2.32.4
python-dateutil==2.9.0.post0
```

---

## 3. 아키텍처 개요

### 3.1. 전체 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Vue 3)                      │
│                     http://localhost:5173                    │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  AWS API Gateway + Lambda                    │
│                     (Chalice Framework)                      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph Workflow                        │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  State: ConversationState                             │  │
│  │  - messages: List[Message]                            │  │
│  │  - collected_info: dict                               │  │
│  │  - search_results: List[dict]                         │  │
│  │  - calculation: dict                                  │  │
│  └───────────────────────────────────────────────────────┘  │
│                           │                                  │
│  ┌───────────────────────┼──────────────────────────────┐  │
│  │  Nodes                │                               │  │
│  │  ├─ collect_info ─────┼─> LLM (정보 수집)            │  │
│  │  ├─ search_law ───────┼─> LangChain Tool (RAG)       │  │
│  │  ├─ calculate_tax ────┼─> Python 함수                │  │
│  │  └─ generate_response ─> LLM (답변 생성)            │  │
│  └───────────────────────┴──────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  PostgreSQL  │  │    Gemini    │  │  tax_rule   │
│  + pgvector  │  │   2.5 Pro  │  │   _config   │
│              │  │              │  │   (DB)      │
│ - sessions   │  │ - LLM Call   │  └──────────────┘
│ - messages   │  │ - Embedding  │
│ - law_sources│  └──────────────┘
└──────────────┘
```

### 3.2. LangGraph Workflow 흐름

```
사용자 메시지 입력
         ↓
   [START Node]
         ↓
 ┌───────────────────┐
 │  collect_info     │ ← 정보 충분한지 확인
 │  (정보 수집)      │
 └────────┬──────────┘
          │
    ┌─────┴─────┐
    │ 정보 충분? │
    └─────┬─────┘
      NO  │  YES
          ▼
    Clarifying      ┌──────────────┐
    질문 반환  ←────│ search_law   │ ← LangChain Tool (RAG)
                    │ (법령 검색)  │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ calculate_tax│ ← Python 계산 함수
                    │ (세금 계산)  │
                    └──────┬───────┘
                           │
                    ┌──────▼────────┐
                    │generate_response│ ← LLM 답변 생성
                    │ (답변 생성)    │
                    └──────┬─────────┘
                           │
                      [END Node]
                           ↓
                     DB 저장 + 응답
```

---

## 4. LangGraph Workflow 상세 설계

### 4.1. State 정의

```python
from typing import TypedDict, List, Optional, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages

class ConversationState(TypedDict):
    """대화 상태 관리"""

    # 메시지 히스토리 (LangGraph 자동 관리)
    messages: Annotated[List[BaseMessage], add_messages]

    # 사용자로부터 수집된 정보
    collected_info: dict  # {amount, relationship, is_resident, ...}

    # 필수 정보 체크리스트
    required_fields: List[str]  # ["amount", "relationship", ...]

    # RAG 검색 결과
    search_results: Optional[List[dict]]

    # 세금 계산 결과
    calculation: Optional[dict]

    # 최종 응답
    final_response: Optional[str]

    # 세션 정보
    session_id: str
    client_id_hash: str
```

### 4.2. Nodes 정의

#### Node 1: collect_info (정보 수집)

```python
from langchain_google_genai import ChatGoogleGenerativeAI

async def collect_info_node(state: ConversationState) -> ConversationState:
    """
    사용자 메시지에서 필수 정보 추출 및 부족한 정보 확인
    """
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro")

    # 시스템 프롬프트: 정보 추출
    extraction_prompt = f"""
    사용자 메시지에서 다음 정보를 추출하세요:
    - amount: 증여/상속 금액
    - relationship: 관계 (spouse, lineal_ascendant 등)
    - is_resident: 거주자 여부
    - past_gifts: 과거 10년 증여액

    현재까지 수집된 정보: {state['collected_info']}
    새로운 메시지: {state['messages'][-1].content}

    JSON 형식으로 추출된 정보를 반환하세요.
    """

    # LLM 호출
    response = await llm.ainvoke(extraction_prompt)
    extracted = json.loads(response.content)

    # State 업데이트
    state['collected_info'].update(extracted)

    return state
```

#### Node 2: search_law (법령 검색)

```python
from langchain.tools import Tool
from langchain_postgres import PGVector
from langchain_google_genai import GoogleGenerativeAIEmbeddings

class SearchLawTool(Tool):
    name = "search_law"
    description = "증여세/상속세 관련 법령을 검색합니다."

    def __init__(self):
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004"
        )

        self.vectorstore = PGVector(
            connection_string=DATABASE_URL,
            embedding_function=embeddings,
            collection_name="law_sources",
        )

    def _run(self, query: str, k: int = 5) -> List[dict]:
        """벡터 검색 실행"""
        docs = self.vectorstore.similarity_search(query, k=k)

        return [
            {
                "source_id": doc.metadata.get("id"),
                "law_name": doc.metadata.get("law_name"),
                "full_reference": doc.metadata.get("full_reference"),
                "content_snippet": doc.page_content[:200],
                "source_url": doc.metadata.get("source_url"),
            }
            for doc in docs
        ]

async def search_law_node(state: ConversationState) -> ConversationState:
    """법령 검색 Node"""
    tool = SearchLawTool()

    # 검색 쿼리 생성 (collected_info 기반)
    query = f"{state['collected_info'].get('relationship', '')} 증여 공제"

    # Tool 실행
    results = tool.run(query, k=5)

    # State 업데이트
    state['search_results'] = results

    return state
```

#### Node 3: calculate_tax (세금 계산)

```python
async def calculate_tax_node(state: ConversationState) -> ConversationState:
    """결정론적 세금 계산"""

    calculator = TaxCalculator()  # 순수 Python 클래스

    result = calculator.calculate_gift_tax(
        amount=state['collected_info']['amount'],
        relationship=state['collected_info']['relationship'],
        is_resident=state['collected_info'].get('is_resident', True),
        past_gifts=state['collected_info'].get('past_gifts', 0),
    )

    # State 업데이트
    state['calculation'] = result

    return state
```

#### Node 4: generate_response (답변 생성)

```python
async def generate_response_node(state: ConversationState) -> ConversationState:
    """최종 답변 생성"""
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro")

    prompt = f"""
    다음 정보를 종합하여 답변을 생성하세요:

    [법령 검색 결과]
    {json.dumps(state['search_results'], ensure_ascii=False, indent=2)}

    [계산 결과]
    {json.dumps(state['calculation'], ensure_ascii=False, indent=2)}

    [답변 형식]
    1. 핵심 답변 (2-3문장)
    2. 법적 근거 (조문 인용)
    3. 계산 과정
    4. 주의사항

    Markdown 형식으로 작성하세요.
    """

    response = await llm.ainvoke(prompt)

    state['final_response'] = response.content

    return state
```

### 4.3. Conditional Edges (조건부 분기)

```python
def check_info_complete(state: ConversationState) -> str:
    """정보가 충분한지 확인"""
    required = ["amount", "relationship"]
    collected = state['collected_info']

    if all(field in collected for field in required):
        return "search_law"  # 다음 노드로
    else:
        return "clarify"  # Clarifying 질문
```

### 4.4. Graph 구성

```python
from langgraph.graph import StateGraph, END

def create_workflow() -> StateGraph:
    """LangGraph Workflow 생성"""

    workflow = StateGraph(ConversationState)

    # Nodes 추가
    workflow.add_node("collect_info", collect_info_node)
    workflow.add_node("search_law", search_law_node)
    workflow.add_node("calculate_tax", calculate_tax_node)
    workflow.add_node("generate_response", generate_response_node)
    workflow.add_node("clarify", clarify_node)  # Clarifying 질문 생성

    # Entry Point
    workflow.set_entry_point("collect_info")

    # Conditional Edges
    workflow.add_conditional_edges(
        "collect_info",
        check_info_complete,
        {
            "search_law": "search_law",
            "clarify": "clarify",
        }
    )

    # Sequential Edges
    workflow.add_edge("search_law", "calculate_tax")
    workflow.add_edge("calculate_tax", "generate_response")

    # End
    workflow.add_edge("generate_response", END)
    workflow.add_edge("clarify", END)

    return workflow.compile()
```

---

## 5. 백엔드 모듈 구조

```
backend/
├── app.py                          # Chalice 진입점
├── chalicelib/
│   ├── __init__.py
│   │
│   ├── graph/                      # LangGraph
│   │   ├── __init__.py
│   │   ├── workflow.py             # Workflow 정의
│   │   ├── nodes.py                # Node 함수들
│   │   └── state.py                # State TypedDict
│   │
│   ├── tools/                      # LangChain Tools
│   │   ├── __init__.py
│   │   ├── search_law.py           # 법령 검색 Tool
│   │   ├── calculate_tax.py        # 세금 계산 Tool (래퍼)
│   │   └── search_web.py           # 웹 검색 (선택)
│   │
│   ├── rag/                        # RAG 관련
│   │   ├── __init__.py
│   │   ├── vectorstore.py          # PGVector 초기화
│   │   └── embeddings.py           # Gemini Embedding 래퍼
│   │
│   ├── services/                   # 비즈니스 로직
│   │   ├── __init__.py
│   │   ├── chat_service.py         # 메시지 처리 오케스트레이션
│   │   ├── session_service.py      # 세션 관리
│   │   └── tax_calculator.py       # 순수 Python 계산
│   │
│   ├── db/                         # DB 접근
│   │   ├── __init__.py
│   │   ├── connection.py           # SQLAlchemy 연결
│   │   ├── models.py               # SQLAlchemy 모델
│   │   └── repositories.py         # Repository 패턴
│   │
│   ├── prompts/                    # 프롬프트 관리
│   │   ├── __init__.py
│   │   ├── system_prompts.py       # 시스템 프롬프트
│   │   └── templates.py            # 프롬프트 템플릿
│   │
│   └── utils/                      # 유틸리티
│       ├── __init__.py
│       ├── hash.py                 # client_id 해싱
│       ├── logging.py              # 구조화된 로깅
│       └── validators.py           # 입력 검증
│
├── scripts/                        # 데이터 로딩 스크립트
│   ├── build_law_vector_db.py      # 법령 → pgvector
│   ├── seed_tax_rules.py           # 세금 규정 초기화
│   └── test_workflow.py            # Workflow 테스트
│
└── tests/
    ├── test_graph.py
    ├── test_tools.py
    └── test_services.py
```

---

## 6. 데이터 흐름 (End-to-End)

```
1. 사용자 메시지 수신
   POST /api/sessions/{id}/messages
   Body: {"content": "배우자에게 1억원 증여시 세금은?"}
   ↓

2. Chalice Handler (app.py)
   ├─ client_id 검증 (x-client-id 헤더)
   ├─ 세션 존재 확인
   └─ ChatService.process_message() 호출
   ↓

3. ChatService (services/chat_service.py)
   ├─ 세션 컨텍스트 로드 (이전 대화)
   ├─ State 초기화
   │   - messages: 이전 대화 + 새 메시지
   │   - collected_info: {}
   │   - session_id, client_id_hash
   └─ Workflow 실행
   ↓

4. LangGraph Workflow 실행
   ├─ Node: collect_info
   │   ├─ LLM으로 정보 추출
   │   └─ collected_info 업데이트
   ↓
   ├─ Conditional: check_info_complete
   │   ├─ 정보 부족 → clarify Node (Clarifying 질문)
   │   └─ 정보 충분 → search_law Node
   ↓
   ├─ Node: search_law (정보 충분한 경우)
   │   ├─ SearchLawTool 실행
   │   │   ├─ Gemini Embedding
   │   │   └─ pgvector 유사도 검색 (top 5)
   │   └─ search_results 업데이트
   ↓
   ├─ Node: calculate_tax
   │   ├─ TaxCalculator.calculate_gift_tax()
   │   │   ├─ tax_rule_config 조회
   │   │   └─ Python 계산
   │   └─ calculation 업데이트
   ↓
   └─ Node: generate_response
       ├─ LLM에 컨텍스트 전달
       │   - search_results (법령)
       │   - calculation (계산)
       └─ final_response 생성
   ↓

5. ChatService 후처리
   ├─ citations 추출 (search_results → Citation 객체)
   ├─ metadata 구성
   │   - citations
   │   - calculation
   │   - tool_calls (내부용)
   │   - tokens, latency_ms
   └─ DB 저장
       ├─ User Message 저장
       └─ Assistant Message 저장 (metadata 포함)
   ↓

6. API 응답 반환
   {
     "userMessage": {...},
     "assistantMessage": {
       "content": "...",
       "citations": [...],
       "calculation": {...}
     }
   }
```

---

## 7. 배포 전략

### 7.1. Lambda 배포 (기본)

```bash
# Chalice 배포
cd backend
chalice deploy --stage prod

# 결과:
# - Lambda 함수 생성
# - API Gateway 엔드포인트 생성
# - CloudWatch Logs 자동 설정
```

**Lambda 설정**:
- **메모리**: 1024MB (LangChain + Gemini SDK)
- **Timeout**: 30초
- **환경 변수**:
  - `DATABASE_URL`
  - `GEMINI_API_KEY`
  - `CORS_ALLOW_ORIGIN`
  - `ENVIRONMENT=prod`

### 7.2. Cold Start 최적화

**문제**: Lambda Cold Start 시 라이브러리 로딩 지연

**해결책**:
1. **Lambda Layer** 사용
   ```bash
   # 의존성을 Layer로 분리
   pip install -r requirements.txt -t python/lib/python3.9/site-packages/
   zip -r dependencies.zip python/
   # → Lambda Layer 업로드
   ```

2. **전역 변수 활용**
   ```python
   # app.py 전역 스코프
   _workflow = None
   _vectorstore = None

   def get_workflow():
       global _workflow
       if _workflow is None:
           _workflow = create_workflow()  # 1회만 실행
       return _workflow
   ```

3. **Provisioned Concurrency** (선택)
   - 항상 Warm 상태 유지 (비용 증가)
   - POC에서는 불필요

---

## 8. 성능 목표 및 모니터링

### 8.1. 성능 목표 (PRD 기준)

| 지표 | 목표 | 측정 방법 |
|------|------|----------|
| 첫 응답 시간 (p50) | 5초 이하 | CloudWatch Latency |
| 첫 응답 시간 (p95) | 15초 이하 | CloudWatch Latency |
| Vector 검색 시간 | 500ms 이하 | Custom Metric |
| LLM 호출 시간 | 2~5초 | Gemini API 응답 시간 |
| 동시 요청 처리 | 200 RPS | Lambda Auto-scaling |

### 8.2. CloudWatch 메트릭

```python
# chalicelib/utils/metrics.py
import time
from functools import wraps

def track_latency(metric_name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            result = await func(*args, **kwargs)
            latency_ms = (time.time() - start) * 1000

            # CloudWatch Metric 전송
            cloudwatch.put_metric_data(
                Namespace='Syuking/Backend',
                MetricData=[{
                    'MetricName': metric_name,
                    'Value': latency_ms,
                    'Unit': 'Milliseconds'
                }]
            )

            return result
        return wrapper
    return decorator

# 사용
@track_latency('SearchLawLatency')
async def search_law_node(state):
    ...
```

---

## 9. 보안 및 비용 관리

### 9.1. 보안

| 항목 | 조치 |
|------|------|
| API 키 | AWS Secrets Manager에 저장 |
| DB 연결 | IAM 인증 또는 Secrets Manager |
| client_id | SHA-256 해시 |
| CORS | 프론트엔드 도메인만 허용 |
| Rate Limiting | API Gateway Throttling (1000 req/s) |

### 9.2. 비용 관리

**Lambda 비용** (예상):
- 요청: 100만 건/월
- 실행 시간: 평균 3초
- 메모리: 1024MB
- **월 비용**: ~$20

**Gemini API 비용** (예상):
- 입력 토큰: 평균 2,000/요청
- 출력 토큰: 평균 500/요청
- Flash 모델 단가: 무료 티어 → 유료 시 검토

**PostgreSQL 비용**:
- RDS t3.micro: ~$15/월
- 또는 Neon/Supabase 무료 티어

**총 예상 비용**: ~$35~50/월 (POC 단계)

---

## 10. 테스트 전략

### 10.1. 단위 테스트

```python
# tests/test_tools.py
import pytest
from chalicelib.tools.search_law import SearchLawTool

@pytest.mark.asyncio
async def test_search_law_tool():
    tool = SearchLawTool()
    results = tool.run("배우자 증여 공제", k=5)

    assert len(results) > 0
    assert "제53조" in str(results)
    assert all("source_url" in r for r in results)
```

### 10.2. 통합 테스트 (Workflow)

```python
# tests/test_graph.py
import pytest
from chalicelib.graph.workflow import create_workflow

@pytest.mark.asyncio
async def test_workflow_full_info():
    """정보가 충분한 경우 전체 흐름 테스트"""
    workflow = create_workflow()

    initial_state = {
        "messages": [
            HumanMessage(content="배우자에게 1억원 증여시 세금은?")
        ],
        "collected_info": {
            "amount": 100000000,
            "relationship": "spouse",
            "is_resident": True,
        },
        "session_id": "test-session",
        "client_id_hash": "test-client",
    }

    result = await workflow.ainvoke(initial_state)

    assert result['final_response'] is not None
    assert result['search_results'] is not None
    assert result['calculation']['final_tax'] == 0
```

### 10.3. E2E 테스트

```python
# tests/test_api.py
import pytest
from chalice.test import Client

def test_create_message_api():
    with Client(app) as client:
        # 세션 생성
        session_response = client.http.post(
            '/api/sessions',
            headers={'x-client-id': 'test-client-123'},
        )
        session_id = session_response.json_body['id']

        # 메시지 전송
        message_response = client.http.post(
            f'/api/sessions/{session_id}/messages',
            headers={'x-client-id': 'test-client-123'},
            body={'content': '배우자에게 1억원 증여시 세금은?'},
        )

        assistant = message_response.json_body['assistantMessage']

        assert 'citations' in assistant
        assert len(assistant['citations']) > 0
        assert assistant['calculation']['finalTax'] == 0
```

---

## 11. 구현 우선순위 (3주 계획)

### Week 1: 기반 구축
- [x] DB 스키마 설계 완료
- [ ] Day 1-2: PostgreSQL 환경 구축
  - RDS 또는 로컬 PostgreSQL 설정
  - pgvector 확장 설치
  - 테이블 생성 (schema.sql 실행)
- [ ] Day 3-4: 법령 데이터 로딩
  - `scripts/build_law_vector_db.py` 작성
  - JSON → chunks 추출
  - Gemini 임베딩 (배치)
  - pgvector 저장
- [ ] Day 5: RAG 검색 테스트
  - PGVector 연동
  - 검색 품질 확인

### Week 2: LangGraph + Tools
- [ ] Day 1-2: LangGraph Workflow 구현
  - State 정의
  - Nodes 구현 (collect_info, search_law, calculate_tax)
  - Graph 연결
- [ ] Day 3: Tool 구현
  - SearchLawTool (PGVector 래핑)
  - TaxCalculator (순수 Python)
- [ ] Day 4-5: Workflow 테스트 및 디버깅
  - 단위 테스트
  - 통합 테스트
  - 프롬프트 튜닝

### Week 3: API + 통합
- [ ] Day 1-2: Chalice API 구현
  - POST /api/sessions
  - POST /api/sessions/{id}/messages
  - GET /api/sessions/{id}/messages
- [ ] Day 3: 프론트엔드 연동
  - API 호출
  - Message 렌더링 (citations, calculation)
- [ ] Day 4: E2E 테스트
  - 실제 대화 시나리오 테스트
  - 성능 측정
- [ ] Day 5: 배포 및 문서화
  - Lambda 배포
  - CloudWatch 설정
  - README 업데이트

---

## 12. 향후 개선 방향

### Phase 2 (4주차 이후)

1. **Hybrid Search 추가**
   - PostgreSQL Full-Text Search
   - 또는 BM25 (Lambda 메모리 허용 시)

2. **Reranker 도입**
   - Cohere Rerank API
   - 검색 품질 개선

3. **Streaming 응답**
   - Server-Sent Events (SSE)
   - 긴 답변을 실시간으로 전송

4. **대안 시나리오 자동 생성**
   - Multi-scenario Tool
   - 여러 케이스 비교

5. **ECS/Fargate 전환**
   - Cold Start 제거
   - 더 복잡한 로직 지원

---

## 13. 참고 문서

- [LangGraph 공식 문서](https://langchain-ai.github.io/langgraph/)
- [LangChain Tools](https://python.langchain.com/docs/modules/tools/)
- [Chalice Documentation](https://aws.github.io/chalice/)
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [Gemini API](https://ai.google.dev/gemini-api/docs)

---

## 14. 체크리스트

### 개발 시작 전
- [ ] PostgreSQL + pgvector 설치 완료
- [ ] Gemini API 키 발급
- [ ] AWS 계정 준비 (배포용)
- [ ] requirements.txt 의존성 설치
- [ ] .env 파일 설정

### 구현 중
- [ ] LangGraph State 정의
- [ ] 모든 Node 함수 작성
- [ ] Tool 인터페이스 구현
- [ ] 프롬프트 작성 및 테스트
- [ ] DB Repository 패턴 구현

### 배포 전
- [ ] 단위 테스트 통과
- [ ] 통합 테스트 통과
- [ ] E2E 테스트 통과
- [ ] 성능 목표 달성 확인
- [ ] 보안 체크리스트 확인
