# Message Format Specification

**문서 버전**: v1.0
**작성일**: 2025-10-14
**연관 문서**: `docs/prd_detail/api-spec.md`, `02-database-detail.md`

## 1. 개요

슈킹 AI 상담 서비스의 메시지 데이터 구조를 정의합니다.
- **핵심**: 법령 출처(citations) 제공을 통한 신뢰성 확보
- **목적**: 프론트엔드에서 상세한 답변 렌더링 지원
- **저장**: PostgreSQL `messages` 테이블의 `metadata JSONB` 컬럼

### Agent Guardrails 연계
- **Knowledge Fidelity** (`docs/prd_detail/ai-logic/agent.md:15`) — `citations`/`clarifying_context` 구조를 통해 답변마다 근거를 노출하고 근거 부재 시 재확인 절차를 수행한다.
- **Compliance & Privacy** (`docs/prd_detail/ai-logic/agent.md:17`) — 준법 고지, 민감정보 비저장 정책을 `metadata` 필드로 강제하며, 참고자료/웹검색은 참고용으로만 라벨링한다.
- **Deterministic Accuracy** (`docs/prd_detail/ai-logic/agent.md:14`) — 계산 결과(`calculation`, `assumptions`, `warnings`)를 구조화해 결정론 엔진 산출값을 그대로 사용자에게 전달한다.

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

### 3.1. 전체 구조

| 필드 | 설명 | 필수 | 비고 |
|------|------|------|------|
| `citations[]` | 법령/지식 출처 정보 | ✅ | 3.2 참조 |
| `calculation` | 세금 계산 결과 구조 | 옵션 | 3.3 참조 |
| `alternatives[]` | 대안 시나리오 리스트 | 옵션 | 3.4 참조 |
| `tool_calls[]` | 사용된 도구 로그 | 옵션 | 3.5 참조 |
| `assumptions[]` | 적용된 전제 목록 | 옵션 | Clarifying 결과 |
| `clarifying_context[]` | Clarifying 중 제공한 설명 및 참고 자료 | 옵션 | 3.7 참조 |
| `exceptions[]` | 예외/주의 사항 | 옵션 | 답변 본문에 재노출 |
| `recommendations[]` | 후속 권고 사항 | 옵션 | 사용자 액션 안내 |
| `missing_parameters[]` | 미수집 필수 변수 정보 | 옵션 | `{ name, reason }` 구조 |
| `tokens` | 입력/출력 토큰 수 | 옵션 | 분석용 |
| `latency_ms` | 모델 응답 시간 (ms) | 옵션 | 모니터링용 |
| `model` | 사용한 LLM 식별자 | 옵션 | 예: `gemini-2.5-pro` |
| `feedback` | 사용자 피드백 정보 | 옵션 | 3.6 참조 |

`missing_parameters.reason` 값은 `not_provided`, `ambiguous`, `user_unknown` 중 하나를 사용합니다.

---

### 3.2. Citation (법령 인용)

**목적**: 답변의 법적 근거를 명확히 제시

| 필드 | 설명 | 필수 | 비고 |
|------|------|------|------|
| `source_id` | `law_sources` 또는 `knowledge_sources`의 ID | ✅ | 내부 참조용 |
| `source_type` | `law` / `knowledge` | ✅ | 인용 구분 |
| `law_name` | 법령 또는 자료 이름 | ✅ | 예: 상속세및증여세법 |
| `full_reference` | 조·항 등 전체 인용 경로 | ✅ | 예: “제53조 1항” |
| `article`, `paragraph`, `item` | 세부 위치 | 옵션 | 존재할 경우만 기재 |
| `content_snippet` | 인용 텍스트 요약(100~200자) | ✅ | 하이라이트용 |
| `source_url` | 원문 링크 | ✅ | 법제처/국세청 |
| `relevance_score` | 검색 점수 (0~1) | 옵션 | RAG 점검용 |

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

| 필드 | 설명 | 필수 | 비고 |
|------|------|------|------|
| `tax_type` | `gift` / `inheritance` | ✅ | 계산 종류 |
| `assumptions[]` | 계산 전제 목록 | ✅ | Clarifying 결과와 연계 |
| `input` | 입력 변수 집합 | ✅ | `amount`, `relationship`, `is_resident` 등 |
| `steps[]` | 단계별 계산 로그 | ✅ | 각 항목은 `step`, `description`, `value`, `formula`, `reference` 포함 |
| `final_tax` | 최종 산출 세액 | ✅ | KRW |
| `warnings[]` | 주의/가산세 안내 | 옵션 | 문자열 배열 |

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

### 3.7. ClarifyingContext (설명 스니펫)

**목적**: Clarifying 단계에서 사용자에게 제공한 용어 설명과 RAG 기반 참고 자료를 추적하여 이후 노드(계산, QA)에서도 일관된 안내를 유지

| 필드 | 설명 | 필수 | 비고 |
|------|------|------|------|
| `source_id` | `law_sources` 또는 `knowledge_sources` ID | 옵션 | 외부 참조가 없으면 생략 |
| `summary` | 사용자에게 전달한 설명 요약 | ✅ | 200자 내외 권장 |
| `detail_url` | 자세한 참고 링크 | 옵션 | 법제처/국세청 등 |
| `confidence` | 설명에 대한 모델 확신도 (0~1) | 옵션 | Clarifying 모델 출력 |

**JSON 예시**:
```json
{
  "clarifying_context": [
    {
      "source_id": 321,
      "summary": "최근 10년 내 동일인에게서 받은 증여금액은 합산 과세 대상입니다.",
      "detail_url": "https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=237786#0000",
      "confidence": 0.82
    }
  ]
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

## 5. Clarifying Metadata 연계

- Clarifying 질문/응답 이력은 `missing_parameters`, `clarifying_history`(선택) 필드에 기록하고 `04-clarifying-strategy.md`의 규칙을 따른다.
- `assumptions`, `exceptions`, `recommendations` 배열은 계산 결과와 함께 UI에 노출되어야 하며, PRD의 “전제/예외/권고” 요구사항을 충족한다.
- 누락 변수 안내가 포함된 경우, 답변 본문에 동일 내용을 명시하여 사용자가 빠르게 재답변할 수 있도록 한다.

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

    "assumptions": [
      "국내 거주자 기준 계산",
      "배우자 증여 공제 6억원 적용"
    ],
    "exceptions": [
      "해외 재산 증여 시 별도 신고 절차가 필요합니다."
    ],
    "recommendations": [
      "증여 사실을 입증할 수 있는 서류를 5년간 보관하세요."
    ],
    "missingParameters": [],

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
