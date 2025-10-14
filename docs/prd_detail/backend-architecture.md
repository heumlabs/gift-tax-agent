## 백엔드 아키텍처 설계

문서 버전: v1.0  
연관 문서: `docs/PRD.md`

### 1. 개요

AWS의 서버리스 스택을 활용하여 초기 비용을 최소화하고 확장성을 확보합니다.

- **프레임워크**: AWS Chalice (Python)
- **플랫폼**: AWS Lambda, API Gateway
- **데이터베이스**: PostgreSQL (RDS 또는 Aurora Serverless) with pgvector
- **핵심 로직**: 상담형 AI 파이프라인, 세무 계산 엔진, RAG

### 2. 컴포넌트 및 기술 스택

| 구분             | 기술                                      | 역할                                          |
| :--------------- | :---------------------------------------- | :-------------------------------------------- |
| **API/서버리스** | AWS API Gateway, AWS Lambda, Chalice      | REST API 엔드포인트 제공 및 비즈니스 로직 실행 |
| **데이터베이스** | PostgreSQL on RDS/Aurora (w/ pgvector)  | 세션/메시지 데이터 저장, RAG 문서 벡터 인덱싱 |
| **LLM**          | Google Gemini 2.5 Pro (via API)           | 자연어 이해, 답변 생성, 상담 흐름 제어        |
| **로깅/모니터링**| AWS CloudWatch                            | 로그 수집, 에러 모니터링, 성능 지표 트래킹    |
| **배포**         | GitHub Actions, AWS CLI                   | CI/CD 자동화                                  |
| **보안**         | AWS KMS, IAM                              | 데이터 암호화, 접근 제어                      |

### 3. 애플리케이션 구조 (Chalice)

모듈화를 통해 각 기능의 책임을 명확히 분리합니다.

```
/
├── app.py              # Chalice 앱 정의, 라우팅, 미들웨어
├── chalicelib/
│   ├── auth/           # 클라이언트 ID 처리 및 검증
│   ├── db/             # 데이터베이스 연결, 리포지토리 패턴 구현
│   ├── llm/            # LLM API 클라이언트, 프롬프트 관리
│   ├── models/         # Pydantic 데이터 모델 (요청/응답, DB 스키마)
│   ├── rag/            # RAG 파이프라인 (임베딩, 검색 로직)
│   ├── services/       # 핵심 비즈니스 로직 (chat, session, tax_calc)
│   └── utils/          # 공통 유틸리티
├── requirements.txt    # 의존성 패키지
└── tests/              # 단위/통합 테스트
```

### 4. 핵심 데이터 흐름 (메시지 처리)

1.  **요청**: 사용자가 메시지를 보내면 `POST /sessions/{id}/messages` 요청이 API Gateway를 통해 Lambda 함수를 트리거합니다.
2.  **인증**: `auth` 미들웨어가 `x-client-id` 헤더를 검증하고 해시하여 컨텍스트에 추가합니다.
3.  **오케스트레이션**: `ChatService`가 전체 흐름을 관장합니다.
4.  **컨텍스트 로드**: `SessionService`가 DB에서 현재 세션의 대화 기록을 조회합니다.
5.  **의도 분석/변수 추출**: `LLMService`가 사용자 메시지에서 의도(증여세 계산, 상속세 문의 등)와 핵심 변수(금액, 관계 등)를 추출합니다.
6.  **변수 검증**: `TaxCalculator`가 계산에 필요한 모든 변수가 수집되었는지 확인합니다.
    -   **부족 시**: `LLMService`에 부족한 변수를 알려주고, 사용자에게 되물을 clarifying 질문을 생성하도록 요청 후 반환합니다.
7.  **RAG 검색**: `RAGService`가 추출된 변수와 대화 내용을 기반으로 `pgvector`에서 관련 법령/예규 문서를 검색합니다.
8.  **프롬프트 생성**: `LLMService`가 아래 정보를 조합하여 Gemini에 전달할 최종 프롬프트를 구성합니다.
    -   시스템 프롬프트 (AI 페르소나, 지침)
    -   대화 기록
    -   RAG 검색 결과 (법령 컨텍스트)
    -   (필요시) `TaxCalculator`의 사전 계산 결과
9.  **LLM 호출**: Gemini API를 호출하여 답변을 생성합니다.
10. **후처리 및 저장**: 응답을 `Message` 데이터 모델에 맞게 가공(인용, 계산 결과 등 분리)하고, 사용자와 AI의 메시지를 DB에 저장합니다.
11. **응답**: 구조화된 JSON 형태로 클라이언트에 최종 결과를 반환합니다.

### 5. 데이터베이스 관리

- **ORM/라이브러리**: SQLAlchemy Core 또는 `psycopg` 라이브러리를 사용한 리포지토리 패턴을 적용하여 DB와 비즈니스 로직을 분리합니다.
- **스키마 마이그레이션**: `Alembic`을 도입하여 DB 스키마 변경을 안전하고 체계적으로 관리합니다.

### 6. 로깅 및 예외 처리

- **구조화된 로깅**: 모든 로그는 `JSON` 형식으로 출력하여 CloudWatch Logs에서 쉽게 검색하고 분석할 수 있도록 합니다. (요청 ID, 클라이언트 ID, 세션 ID 포함)
- **중앙 예외 처리**: Chalice 미들웨어를 사용하여 처리되지 않은 모든 예외를 잡아내고, 표준화된 에러 응답을 반환하며, 심각도에 따라 CloudWatch Alarm으로 연동합니다.
- **핵심 모니터링 지표**:
    -   API Latency (p50, p90, p99)
    -   에러율 (4xx, 5xx)
    -   LLM API 호출 시간 및 토큰 사용량
    -   RAG 검색 정확도 (오프라인 평가)

### 7. 배포 전략 (CI/CD)

- **브랜치 전략**: `main` (운영), `develop` (개발/스테이징) 브랜치를 사용합니다.
- **자동화**:
    1.  `develop` 브랜치에 코드가 푸시되면 GitHub Actions가 트리거됩니다.
    2.  자동으로 테스트, 린트, 빌드를 수행합니다.
    3.  성공 시 `chalice deploy --stage dev` 명령으로 개발 환경에 배포합니다.
    4.  `main` 브랜치로 PR이 머지되면, 동일한 프로세스를 거쳐 `chalice deploy --stage prod`로 운영 환경에 배포합니다.
- **환경 변수 관리**: Chalice의 stage 기능을 사용하여 개발/운영 환경의 설정(DB 정보, API 키 등)을 분리하고, AWS Secrets Manager 또는 Parameter Store를 연동하여 민감 정보를 안전하게 관리합니다.
