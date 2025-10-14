# Message Format Specification

**문서 버전**: v1.0
**작성일**: 2025-10-14
**연관 문서**: `docs/prd_detail/api-spec.md`, `02-database-schema.md`

## 1. 개요

슈킹 AI 상담 서비스의 메시지 데이터 구조를 정의합니다.
- **핵심**: 법령 출처(citations) 제공을 통한 신뢰성 확보
- **목적**: 프론트엔드에서 상세한 답변 렌더링 지원
- **저장**: PostgreSQL `messages` 테이블의 `metadata JSONB` 컬럼

---

## 2. 데이터베이스 저장 구조

### 2.1. messages 테이블 (복습)

```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(16) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 2.2. metadata 컬럼 역할

| role | content | metadata |
|------|---------|----------|
| `user` | 사용자 질문 원문 | 클라이언트 정보 (선택) |
| `assistant` | LLM 생성 답변 (Markdown) | **citations, calculation, alternatives 등** |
| `system` | 내부 프롬프트 (디버깅용) | 프롬프트 버전 정보 등 |

---

## 3. Assistant Message Metadata 상세

### 3.1. 전체 구조 (TypeScript 정의)

```typescript
interface AssistantMetadata {
  // 핵심: 법령 인용
  citations: Citation[];

  // 세금 계산 결과
  calculation?: TaxCalculation;

  // 대안 시나리오
  alternatives?: Alternative[];

  // Tool 호출 이력 (내부용)
  tool_calls?: ToolCall[];

  // 토큰 사용량 (분석용)
  tokens?: TokenUsage;

  // 응답 생성 시간 (모니터링용)
  latency_ms?: number;

  // 사용 모델
  model?: string;

  // 사용자 피드백 (나중에 업데이트)
  feedback?: Feedback | null;
}
```

---

### 3.2. Citation (법령 인용)

**목적**: 답변의 법적 근거를 명확히 제시

```typescript
interface Citation {
  // DB 참조 (내부용)
  source_id: number;              // law_sources.id 또는 knowledge_sources.id
  source_type: 'law' | 'knowledge';

  // 법령 정보
  law_name: string;               // 예: "상속세및증여세법"
  full_reference: string;         // 예: "상속세및증여세법 제1장 총칙 제53조 1항"
  article?: string;               // 예: "제53조"
  paragraph?: string;             // 예: "1항"
  item?: string;                  // 예: "2호"

  // 인용 내용
  content_snippet: string;        // 해당 조항 원문 일부 (100~200자)

  // 원문 링크 (법제처)
  source_url: string;             // 예: "https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=123456#0000"

  // 관련성 점수 (내부용)
  relevance_score?: number;       // 0~1, RAG 검색 점수
}
```

**JSON 예시**:
```json
{
  "source_id": 123,
  "source_type": "law",
  "law_name": "상속세및증여세법",
  "full_reference": "상속세및증여세법 제1장 총칙 제53조 1항",
  "article": "제53조",
  "paragraph": "1항",
  "content_snippet": "배우자로부터 증여받은 재산에 대해서는 6억원을 공제한다. 다만, 해당 증여자로부터 당해 증여 전 10년 이내에 증여받은 재산가액의 합계액이 6억원 이상인 경우...",
  "source_url": "https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=237786#0000",
  "relevance_score": 0.89
}
```

---

### 3.3. TaxCalculation (세금 계산)

**목적**: 계산 과정을 투명하게 제시

```typescript
interface TaxCalculation {
  // 세금 유형
  tax_type: 'gift' | 'inheritance';

  // 계산 전제 조건
  assumptions: string[];          // 예: ["거주자 간 증여", "과거 10년 증여 없음"]

  // 입력 값
  input: {
    amount: number;               // 증여/상속 재산 가액
    relationship: string;         // 관계 (spouse, lineal_ascendant 등)
    is_resident: boolean;         // 거주자 여부
    past_gifts?: number;          // 과거 10년 증여액
    [key: string]: any;           // 기타 입력값
  };

  // 계산 단계
  steps: CalculationStep[];

  // 최종 세액
  final_tax: number;

  // 주의사항 및 경고
  warnings: string[];             // 예: ["증여일로부터 3개월 이내 신고 필요"]
}

interface CalculationStep {
  step: number;                   // 단계 번호
  description: string;            // 단계 설명
  value: number;                  // 계산 값
  formula?: string;               // 계산 공식 (선택)
  reference?: string;             // 관련 법령 (선택)
}
```

**JSON 예시**:
```json
{
  "tax_type": "gift",
  "assumptions": [
    "거주자 간 증여",
    "과거 10년 이내 동일인 증여 없음",
    "성인 수증자"
  ],
  "input": {
    "amount": 100000000,
    "relationship": "spouse",
    "is_resident": true,
    "past_gifts": 0
  },
  "steps": [
    {
      "step": 1,
      "description": "증여재산 가액",
      "value": 100000000,
      "formula": "증여받은 금액"
    },
    {
      "step": 2,
      "description": "증여재산 공제 (배우자)",
      "value": -600000000,
      "formula": "10년간 6억원 공제",
      "reference": "상속세및증여세법 제53조"
    },
    {
      "step": 3,
      "description": "과세표준",
      "value": 0,
      "formula": "증여재산 가액 - 공제액 = 100,000,000 - 600,000,000"
    },
    {
      "step": 4,
      "description": "산출세액",
      "value": 0,
      "formula": "과세표준 × 세율 (과세표준이 0 이하이므로 세액 없음)"
    }
  ],
  "final_tax": 0,
  "warnings": [
    "증여일로부터 3개월 이내 신고 필요",
    "기한 후 신고 시 가산세 20% 부과",
    "향후 10년 이내 동일인으로부터 추가 증여 시 합산 과세"
  ]
}
```

---

### 3.4. Alternative (대안 시나리오)

**목적**: 사용자에게 더 나은 선택지 제시

```typescript
interface Alternative {
  title: string;                  // 대안 제목
  description: string;            // 대안 설명
  estimated_tax?: number;         // 예상 세액 (계산 가능한 경우)
  pros?: string[];                // 장점 (선택)
  cons?: string[];                // 단점 (선택)
  note?: string;                  // 추가 설명
}
```

**JSON 예시**:
```json
[
  {
    "title": "증여 시기 분산",
    "description": "5천만원씩 2년에 걸쳐 증여 시 동일한 세액 0원이지만, 리스크 분산 효과가 있습니다.",
    "estimated_tax": 0,
    "pros": [
      "자금 리스크 분산",
      "향후 상황 변화 대응 가능"
    ],
    "cons": [
      "증여 절차 2회 필요",
      "10년 공제 한도 동일하게 차감"
    ]
  },
  {
    "title": "부동산 증여 고려",
    "description": "현금 대신 부동산 증여 시 취득세 등 추가 비용이 발생하므로 종합 검토가 필요합니다.",
    "note": "상세 계산은 별도 상담 필요"
  }
]
```

---

### 3.5. ToolCall (내부용 - 디버깅/분석)

**목적**: Agent가 호출한 Tool 이력 기록

```typescript
interface ToolCall {
  tool: string;                   // Tool 이름
  query?: string;                 // 검색 쿼리 (search_law)
  params?: Record<string, any>;   // Tool 파라미터
  timestamp: string;              // ISO 8601
  results_count?: number;         // 반환 결과 개수
  execution_time_ms: number;      // 실행 시간
  success: boolean;               // 성공 여부
  error?: string;                 // 에러 메시지 (실패 시)
}
```

**JSON 예시**:
```json
[
  {
    "tool": "search_law",
    "query": "배우자 증여재산 공제",
    "timestamp": "2025-10-14T10:05:08.234Z",
    "results_count": 5,
    "execution_time_ms": 234,
    "success": true
  },
  {
    "tool": "calculate_tax",
    "params": {
      "tax_type": "gift",
      "amount": 100000000,
      "relationship": "spouse",
      "is_resident": true
    },
    "timestamp": "2025-10-14T10:05:09.120Z",
    "execution_time_ms": 12,
    "success": true
  }
]
```

---

### 3.6. TokenUsage, Feedback (분석/개선용)

```typescript
interface TokenUsage {
  input: number;                  // 입력 토큰
  output: number;                 // 출력 토큰
  total: number;                  // 합계
}

interface Feedback {
  type: 'thumbs_up' | 'thumbs_down';
  comment?: string;               // 사용자 코멘트 (선택)
  timestamp: string;              // 피드백 시각
}
```

**JSON 예시**:
```json
{
  "tokens": {
    "input": 1234,
    "output": 567,
    "total": 1801
  },
  "latency_ms": 3421,
  "model": "gemini-2.5-pro",
  "feedback": {
    "type": "thumbs_up",
    "comment": "도움이 되었습니다!",
    "timestamp": "2025-10-14T10:10:00Z"
  }
}
```

---

## 4. User Message Metadata (간소)

사용자 메시지는 단순하게 유지합니다.

```typescript
interface UserMetadata {
  client_info?: {
    user_agent?: string;          // 브라우저 정보
    ip_hash?: string;             // 해시된 IP (분석용, 선택)
  };
  attachments?: Attachment[];     // 향후 확장: 파일 첨부
}

interface Attachment {
  type: 'image' | 'pdf' | 'document';
  filename: string;
  size_bytes: number;
  url: string;                    // S3 등 저장소 URL
}
```

---

## 5. API 응답 형식

### 5.1. POST `/api/sessions/{id}/messages`

**Request**:
```json
{
  "content": "배우자에게 1억원 증여시 세금은 얼마인가요?"
}
```

**Response**:
```json
{
  "userMessage": {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "role": "user",
    "content": "배우자에게 1억원 증여시 세금은 얼마인가요?",
    "createdAt": "2025-10-14T10:05:00.000Z"
  },

  "assistantMessage": {
    "id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
    "role": "assistant",
    "content": "배우자 간 증여는 10년간 6억원까지 공제되므로, 1억원 증여 시 **납부세액은 0원**입니다.\n\n**법적 근거**\n상속세및증여세법 제53조에 따라 배우자로부터 증여받은 재산에 대해서는 6억원을 공제합니다...",

    "citations": [
      {
        "sourceId": 123,
        "sourceType": "law",
        "lawName": "상속세및증여세법",
        "fullReference": "상속세및증여세법 제1장 총칙 제53조 1항",
        "article": "제53조",
        "paragraph": "1항",
        "contentSnippet": "배우자로부터 증여받은 재산에 대해서는 6억원을 공제한다...",
        "sourceUrl": "https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=237786#0000",
        "relevanceScore": 0.89
      }
    ],

    "calculation": {
      "taxType": "gift",
      "assumptions": [
        "거주자 간 증여",
        "과거 10년 이내 동일인 증여 없음",
        "성인 수증자"
      ],
      "input": {
        "amount": 100000000,
        "relationship": "spouse",
        "isResident": true,
        "pastGifts": 0
      },
      "steps": [
        {
          "step": 1,
          "description": "증여재산 가액",
          "value": 100000000,
          "formula": "증여받은 금액"
        },
        {
          "step": 2,
          "description": "증여재산 공제 (배우자)",
          "value": -600000000,
          "formula": "10년간 6억원 공제",
          "reference": "상속세및증여세법 제53조"
        },
        {
          "step": 3,
          "description": "과세표준",
          "value": 0,
          "formula": "증여재산 가액 - 공제액"
        },
        {
          "step": 4,
          "description": "산출세액",
          "value": 0,
          "formula": "과세표준 × 세율"
        }
      ],
      "finalTax": 0,
      "warnings": [
        "증여일로부터 3개월 이내 신고 필요",
        "기한 후 신고 시 가산세 20% 부과"
      ]
    },

    "alternatives": [
      {
        "title": "증여 시기 분산",
        "description": "5천만원씩 2년에 걸쳐 증여 시 동일한 세액이지만 리스크 분산 효과",
        "estimatedTax": 0,
        "pros": ["자금 리스크 분산", "상황 변화 대응 가능"]
      }
    ],

    "createdAt": "2025-10-14T10:05:10.421Z"
  }
}
```

**응답 필드 설명**:
- `content`: Markdown 형식의 답변 본문
- `citations`: **핵심** - 법령 출처 배열
- `calculation`: 세금 계산 과정 (있는 경우)
- `alternatives`: 대안 시나리오 (있는 경우)
- ❌ `toolCalls`, `tokens`, `latencyMs`: 내부용, 응답에서 제외

---

### 5.2. GET `/api/sessions/{id}/messages`

**Response**:
```json
{
  "messages": [
    {
      "id": "...",
      "role": "user",
      "content": "...",
      "createdAt": "..."
    },
    {
      "id": "...",
      "role": "assistant",
      "content": "...",
      "citations": [...],
      "calculation": {...},
      "alternatives": [...],
      "createdAt": "..."
    }
  ],
  "nextCursor": "msg_xyz_timestamp"
}
```

---

## 6. Frontend 렌더링 가이드

### 6.1. Vue 컴포넌트 예시

```vue
<template>
  <div class="message" :class="`message-${message.role}`">
    <!-- 사용자 메시지 -->
    <div v-if="message.role === 'user'" class="user-message">
      <div class="avatar">👤</div>
      <div class="content">{{ message.content }}</div>
    </div>

    <!-- AI 메시지 -->
    <div v-else-if="message.role === 'assistant'" class="assistant-message">
      <div class="avatar">🤖</div>

      <div class="message-body">
        <!-- 답변 본문 (Markdown) -->
        <div class="content" v-html="renderMarkdown(message.content)"></div>

        <!-- 법령 인용 (핵심!) -->
        <div v-if="message.citations?.length" class="citations-section">
          <h4 class="section-title">📚 법적 근거</h4>
          <div class="citations-grid">
            <a
              v-for="citation in message.citations"
              :key="citation.sourceId"
              :href="citation.sourceUrl"
              target="_blank"
              class="citation-card"
            >
              <div class="citation-header">
                <span class="law-name">{{ citation.lawName }}</span>
                <span class="article">{{ citation.article }}</span>
              </div>
              <p class="snippet">{{ citation.contentSnippet }}</p>
              <span class="external-link-icon">↗</span>
            </a>
          </div>
        </div>

        <!-- 계산 과정 -->
        <div v-if="message.calculation" class="calculation-section">
          <h4 class="section-title">🧮 계산 과정</h4>
          <div class="calculation-steps">
            <div
              v-for="step in message.calculation.steps"
              :key="step.step"
              class="calc-step"
            >
              <span class="step-number">{{ step.step }}</span>
              <span class="step-description">{{ step.description }}</span>
              <span class="step-value">{{ formatCurrency(step.value) }}</span>
            </div>
          </div>
          <div class="final-tax">
            <span>최종 납부세액</span>
            <strong>{{ formatCurrency(message.calculation.finalTax) }}</strong>
          </div>
          <div v-if="message.calculation.warnings?.length" class="warnings">
            <p v-for="(warning, idx) in message.calculation.warnings" :key="idx">
              ⚠️ {{ warning }}
            </p>
          </div>
        </div>

        <!-- 대안 시나리오 -->
        <div v-if="message.alternatives?.length" class="alternatives-section">
          <h4 class="section-title">💡 고려할 대안</h4>
          <div class="alternatives-grid">
            <div
              v-for="(alt, idx) in message.alternatives"
              :key="idx"
              class="alternative-card"
            >
              <h5>{{ alt.title }}</h5>
              <p>{{ alt.description }}</p>
              <div v-if="alt.estimatedTax !== undefined" class="alt-tax">
                예상 세액: {{ formatCurrency(alt.estimatedTax) }}
              </div>
              <ul v-if="alt.pros?.length" class="pros">
                <li v-for="pro in alt.pros" :key="pro">✓ {{ pro }}</li>
              </ul>
            </div>
          </div>
        </div>

        <!-- 피드백 버튼 -->
        <div class="feedback-buttons">
          <button @click="sendFeedback('thumbs_up')">👍 도움됨</button>
          <button @click="sendFeedback('thumbs_down')">👎 개선 필요</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { marked } from 'marked';

const renderMarkdown = (content: string) => marked(content);

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('ko-KR', {
    style: 'currency',
    currency: 'KRW'
  }).format(value);
};

const sendFeedback = async (type: 'thumbs_up' | 'thumbs_down') => {
  // PATCH /api/messages/{id}/feedback
  await api.patchMessageFeedback(message.id, { type });
};
</script>
```

---

### 6.2. 스타일 가이드 (Tailwind CSS)

```vue
<style>
.citation-card {
  @apply block p-4 border border-gray-200 rounded-lg hover:border-blue-500 transition-colors;
  @apply bg-white hover:bg-blue-50;
}

.law-name {
  @apply font-semibold text-gray-900;
}

.article {
  @apply text-sm text-blue-600 ml-2;
}

.snippet {
  @apply text-sm text-gray-600 mt-2 line-clamp-2;
}

.calc-step {
  @apply flex justify-between items-center py-2 border-b border-gray-100;
}

.final-tax {
  @apply flex justify-between items-center mt-4 p-4 bg-blue-50 rounded-lg;
  @apply text-lg font-bold text-blue-900;
}

.warnings {
  @apply mt-4 p-3 bg-yellow-50 border-l-4 border-yellow-400 text-sm;
}
</style>
```

---

## 7. 데이터 검증

### 7.1. Pydantic 모델 (백엔드)

```python
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Literal
from datetime import datetime

class Citation(BaseModel):
    source_id: int
    source_type: Literal["law", "knowledge"]
    law_name: str
    full_reference: str
    article: Optional[str] = None
    paragraph: Optional[str] = None
    content_snippet: str
    source_url: HttpUrl
    relevance_score: Optional[float] = None

class CalculationStep(BaseModel):
    step: int
    description: str
    value: int
    formula: Optional[str] = None
    reference: Optional[str] = None

class TaxCalculation(BaseModel):
    tax_type: Literal["gift", "inheritance"]
    assumptions: List[str]
    input: dict
    steps: List[CalculationStep]
    final_tax: int
    warnings: List[str]

class Alternative(BaseModel):
    title: str
    description: str
    estimated_tax: Optional[int] = None
    pros: Optional[List[str]] = None
    cons: Optional[List[str]] = None
    note: Optional[str] = None

class AssistantMetadata(BaseModel):
    citations: List[Citation]
    calculation: Optional[TaxCalculation] = None
    alternatives: Optional[List[Alternative]] = None
    tool_calls: Optional[List[dict]] = None
    tokens: Optional[dict] = None
    latency_ms: Optional[int] = None
    model: Optional[str] = None
    feedback: Optional[dict] = None
```

---

## 8. 메타데이터 활용 시나리오

### 8.1. 분석 및 개선

```sql
-- 가장 많이 인용된 법령 TOP 10
SELECT
  citation->>'law_name' AS law_name,
  citation->>'article' AS article,
  COUNT(*) AS citation_count
FROM messages,
  jsonb_array_elements(metadata->'citations') AS citation
WHERE role = 'assistant'
GROUP BY law_name, article
ORDER BY citation_count DESC
LIMIT 10;

-- 평균 응답 시간
SELECT AVG((metadata->>'latency_ms')::int) AS avg_latency_ms
FROM messages
WHERE role = 'assistant'
  AND metadata->>'latency_ms' IS NOT NULL;

-- Tool 별 평균 실행 시간
SELECT
  tool_call->>'tool' AS tool_name,
  AVG((tool_call->>'execution_time_ms')::int) AS avg_execution_ms
FROM messages,
  jsonb_array_elements(metadata->'tool_calls') AS tool_call
WHERE role = 'assistant'
GROUP BY tool_name;

-- 긍정 피드백률
SELECT
  COUNT(CASE WHEN metadata->'feedback'->>'type' = 'thumbs_up' THEN 1 END) * 100.0 /
  COUNT(CASE WHEN metadata->'feedback' IS NOT NULL THEN 1 END) AS positive_feedback_rate
FROM messages
WHERE role = 'assistant';
```

### 8.2. 품질 모니터링

```python
# 인용 없는 답변 탐지 (품질 이슈)
no_citation_messages = db.query("""
    SELECT id, content, created_at
    FROM messages
    WHERE role = 'assistant'
      AND (metadata->'citations' IS NULL
           OR jsonb_array_length(metadata->'citations') = 0)
    ORDER BY created_at DESC
    LIMIT 10;
""")

# 높은 latency 탐지
slow_responses = db.query("""
    SELECT id, session_id, (metadata->>'latency_ms')::int AS latency
    FROM messages
    WHERE role = 'assistant'
      AND (metadata->>'latency_ms')::int > 10000  -- 10초 이상
    ORDER BY latency DESC;
""")
```

---

## 9. 버전 관리 및 마이그레이션

### 9.1. 메타데이터 스키마 버전

향후 필드 추가 시 하위 호환성 유지:

```json
{
  "_schema_version": "1.0",
  "citations": [...],
  "calculation": {...},
  // 향후 추가 필드
  "related_cases": [...],  // v1.1
  "tax_saving_tips": [...] // v1.2
}
```

### 9.2. 마이그레이션 예시

```sql
-- v1.0 → v1.1: related_cases 추가
UPDATE messages
SET metadata = metadata || '{"related_cases": []}'::jsonb
WHERE role = 'assistant'
  AND metadata->>'_schema_version' = '1.0';
```

---

## 10. 보안 및 프라이버시

### 10.1. 민감 정보 제외

**절대 저장하지 않을 정보**:
- 실명
- 주민등록번호
- 계좌번호
- 정확한 주소

### 10.2. IP 해싱

```python
import hashlib

def hash_ip(ip: str) -> str:
    """IP를 SHA-256 해시로 변환 (분석용)"""
    return hashlib.sha256(ip.encode()).hexdigest()[:16]

# 사용
metadata = {
    "client_info": {
        "ip_hash": hash_ip(request.remote_addr)
    }
}
```

---

## 11. 체크리스트

### 11.1. 백엔드 구현 시

- [ ] `citations` 배열은 항상 포함 (비어있어도 `[]`)
- [ ] `source_url`은 유효한 URL인지 검증
- [ ] `calculation`은 세금 계산 시에만 포함
- [ ] `tool_calls`, `tokens`는 DB에만 저장 (API 응답 제외)
- [ ] Pydantic 모델로 데이터 검증

### 11.2. 프론트엔드 구현 시

- [ ] `citations`가 없어도 에러 안나게 옵셔널 체이닝
- [ ] Markdown 렌더링 (`marked` 라이브러리)
- [ ] 금액 포맷팅 (Intl.NumberFormat)
- [ ] 외부 링크는 `target="_blank"` + `rel="noopener"`
- [ ] 피드백 전송 API 구현

---

## 12. 다음 단계

1. ✅ Message Format 문서 완료
2. ⏭️ 기술 스택 및 구현 방향 문서 작성
3. ⏭️ LangGraph Workflow 설계 문서
4. ⏭️ API 엔드포인트 상세 명세
