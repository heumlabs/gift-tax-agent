## 백엔드 아키텍처 설계

문서 버전: v2.0
최종 수정일: 2025-10-14
연관 문서: `docs/PRD.md`, `docs/llm/tech-stack-and-implementation.md`

### 1. 개요

AWS의 서버리스 스택과 **LangGraph 기반 Workflow**를 활용하여 초기 비용을 최소화하고 확장성을 확보합니다.

- **프레임워크**: AWS Chalice (Python)
- **플랫폼**: AWS Lambda, API Gateway
- **데이터베이스**: PostgreSQL (RDS 또는 Aurora Serverless) with pgvector
- **AI Framework**: LangGraph + LangChain
- **핵심 로직**: LangGraph Workflow, RAG (Vector Search), 세무 계산 엔진

### 2. 컴포넌트 및 기술 스택

| 구분             | 기술                                      | 역할                                          |
| :--------------- | :---------------------------------------- | :-------------------------------------------- |
| **API/서버리스** | AWS API Gateway, AWS Lambda, Chalice      | REST API 엔드포인트 제공 및 비즈니스 로직 실행 |
| **데이터베이스** | PostgreSQL on RDS/Aurora (w/ pgvector)  | 세션/메시지 데이터 저장, RAG 문서 벡터 인덱싱 |
| **LLM**          | Google Gemini 2.0 Flash Exp               | 자연어 이해, 답변 생성, 정보 추출             |
| **AI Framework** | LangGraph 0.2.60+                         | Workflow 상태 관리 및 노드 기반 흐름 제어     |
| **RAG**          | LangChain + PGVector                      | 법령 벡터 검색 (Vector Similarity)           |
| **로깅/모니터링**| AWS CloudWatch                            | 로그 수집, 에러 모니터링, 성능 지표 트래킹    |
| **배포**         | GitHub Actions, AWS CLI                   | CI/CD 자동화                                  |
| **보안**         | AWS KMS, IAM, Secrets Manager             | 데이터 암호화, API 키 관리, 접근 제어         |

### 3. 애플리케이션 구조 (Chalice + LangGraph)

LangGraph 기반으로 모듈을 재구성하여 Workflow 중심 아키텍처를 구현합니다.

```
backend/
├── app.py                          # Chalice 앱 정의, 라우팅, 미들웨어
├── chalicelib/
│   ├── __init__.py
│   │
│   ├── graph/                      # ⭐ LangGraph Workflow
│   │   ├── __init__.py
│   │   ├── workflow.py             # Workflow 정의 및 Graph 구성
│   │   ├── nodes.py                # Node 함수들 (collect_info, search_law 등)
│   │   ├── state.py                # ConversationState TypedDict
│   │   └── edges.py                # Conditional Edge 함수들
│   │
│   ├── tools/                      # ⭐ LangChain Tools
│   │   ├── __init__.py
│   │   ├── search_law.py           # 법령 검색 Tool (PGVector)
│   │   ├── calculate_tax.py        # 세금 계산 Tool (래퍼)
│   │   └── search_web.py           # 웹 검색 Tool (선택)
│   │
│   ├── rag/                        # RAG 관련 모듈
│   │   ├── __init__.py
│   │   ├── vectorstore.py          # PGVector 초기화 및 연결
│   │   └── embeddings.py           # Gemini Embedding 래퍼
│   │
│   ├── services/                   # 비즈니스 로직 레이어
│   │   ├── __init__.py
│   │   ├── chat_service.py         # 메시지 처리 오케스트레이션
│   │   ├── session_service.py      # 세션 CRUD
│   │   └── tax_calculator.py       # 순수 Python 세금 계산 로직
│   │
│   ├── db/                         # 데이터베이스 레이어
│   │   ├── __init__.py
│   │   ├── connection.py           # SQLAlchemy 연결 관리
│   │   ├── models.py               # SQLAlchemy ORM 모델
│   │   └── repositories.py         # Repository 패턴 (CRUD 추상화)
│   │
│   ├── prompts/                    # ⭐ 프롬프트 관리
│   │   ├── __init__.py
│   │   ├── system_prompts.py       # 시스템 프롬프트 템플릿
│   │   └── templates.py            # 동적 프롬프트 템플릿
│   │
│   └── utils/                      # 유틸리티
│       ├── __init__.py
│       ├── hash.py                 # client_id SHA-256 해싱
│       ├── logging.py              # 구조화된 JSON 로깅
│       └── validators.py           # 입력 검증 (Pydantic)
│
├── scripts/                        # 데이터 로딩 및 유틸리티
│   ├── build_law_vector_db.py      # 법령 JSON → pgvector
│   ├── seed_tax_rules.py           # tax_rule_config 초기 데이터
│   └── test_workflow.py            # Workflow 단독 테스트
│
├── tests/                          # 테스트
│   ├── test_graph.py               # LangGraph Workflow 테스트
│   ├── test_tools.py               # Tool 단위 테스트
│   ├── test_services.py            # Service 레이어 테스트
│   └── test_api.py                 # API E2E 테스트
│
├── requirements.txt                # 의존성 패키지
└── .chalice/
    └── config.json                 # Chalice 환경별 설정
```

### 4. 핵심 데이터 흐름 (LangGraph Workflow 기반)

#### 4.1. API 요청 → Workflow 실행

```
1. API 요청
   POST /api/sessions/{session_id}/messages
   Headers: x-client-id
   Body: {"content": "배우자에게 1억원 증여시 세금은?"}
   ↓
2. Chalice Handler (app.py)
   ├─ client_id 검증 및 해싱
   ├─ 세션 존재 확인
   └─ ChatService.process_message() 호출
   ↓
3. ChatService (services/chat_service.py)
   ├─ 세션 컨텍스트 로드 (이전 메시지)
   ├─ ConversationState 초기화
   └─ LangGraph Workflow 실행
   ↓
4. LangGraph Workflow
   [상세 흐름은 4.2 참조]
   ↓
5. 후처리 및 응답
   ├─ metadata 구성 (citations, calculation)
   ├─ DB 저장 (user + assistant messages)
   └─ API 응답 반환
```

#### 4.2. LangGraph Workflow 내부 흐름

```
                    [START]
                       ↓
            ┌──────────────────────┐
            │   collect_info       │
            │  (정보 수집 Node)    │
            │                      │
            │ - LLM으로 정보 추출  │
            │ - collected_info 업데이트
            └──────────┬───────────┘
                       │
              ┌────────▼─────────┐
              │  check_info_     │
              │  complete()      │
              │  (Conditional)   │
              └────┬─────────┬───┘
                NO │         │ YES
                   │         │
          ┌────────▼──┐   ┌──▼──────────────┐
          │  clarify  │   │  search_law     │
          │  (Node)   │   │  (Node)         │
          │           │   │                 │
          │ Clarifying│   │ - SearchLawTool │
          │ 질문 생성  │   │ - PGVector 검색 │
          └─────┬─────┘   │ - top 5 결과   │
                │         └──────┬──────────┘
                │                │
                │         ┌──────▼──────────┐
                │         │  calculate_tax  │
                │         │  (Node)         │
                │         │                 │
                │         │ - TaxCalculator │
                │         │ - Python 계산   │
                │         └──────┬──────────┘
                │                │
                │         ┌──────▼──────────┐
                │         │ generate_       │
                │         │ response        │
                │         │ (Node)          │
                │         │                 │
                │         │ - LLM 답변 생성│
                │         │ - Markdown     │
                │         └──────┬──────────┘
                │                │
                ▼                ▼
              [END]            [END]
```

#### 4.3. 각 컴포넌트 역할

| 컴포넌트 | 책임 | 위치 |
|----------|------|------|
| **ChatService** | Workflow 실행 오케스트레이션, State 초기화, DB 저장 | `services/chat_service.py` |
| **collect_info Node** | LLM으로 필수 정보 추출 (amount, relationship 등) | `graph/nodes.py` |
| **check_info_complete** | 필수 정보 충족 여부 확인 (Conditional Edge) | `graph/edges.py` |
| **clarify Node** | 부족한 정보에 대한 Clarifying 질문 생성 | `graph/nodes.py` |
| **search_law Node** | SearchLawTool 실행 → pgvector 검색 | `graph/nodes.py` |
| **SearchLawTool** | PGVector 래핑, 법령 벡터 검색 | `tools/search_law.py` |
| **calculate_tax Node** | TaxCalculator 호출 → 결정론적 계산 | `graph/nodes.py` |
| **TaxCalculator** | 세금 계산 로직 (순수 Python, LLM 없음) | `services/tax_calculator.py` |
| **generate_response Node** | LLM에 컨텍스트 전달 → 자연어 답변 생성 | `graph/nodes.py` |

### 5. 데이터베이스 관리

- **ORM/라이브러리**: SQLAlchemy Core를 사용한 리포지토리 패턴으로 DB와 비즈니스 로직 분리
- **스키마 마이그레이션**: Alembic으로 DB 스키마 버전 관리
- **Vector Store**: LangChain의 PGVector 클래스를 통해 pgvector 연동
- **상세 스키마**: `docs/llm/03-database-schema.md` 참조

### 6. 로깅 및 예외 처리

- **구조화된 로깅**: 모든 로그는 `JSON` 형식으로 출력하여 CloudWatch Logs에서 쉽게 검색하고 분석할 수 있도록 합니다. (요청 ID, 클라이언트 ID, 세션 ID 포함)
- **중앙 예외 처리**: Chalice 미들웨어를 사용하여 처리되지 않은 모든 예외를 잡아내고, 표준화된 에러 응답을 반환하며, 심각도에 따라 CloudWatch Alarm으로 연동합니다.
- **핵심 모니터링 지표**:
    -   API Latency (p50, p90, p99)
    -   에러율 (4xx, 5xx)
    -   LLM API 호출 시간 및 토큰 사용량
    -   RAG 검색 정확도 (오프라인 평가)

### 7. 배포 전략 (CI/CD)

- **브랜치 전략**: `main` (운영) 브랜치를 사용합니다.
- **자동화**:
    1.  `feature` 브랜치에 코드가 푸시되면 GitHub Actions가 트리거됩니다.
    2.  자동으로 PR을 생성합니다.
    3.  `main` 브랜치로 PR이 머지되면, 자동으로 배포합니다.
- **환경 변수 관리**: AWS Secrets Manager 또는 Parameter Store를 연동하여 민감 정보를 안전하게 관리합니다.
