# Frontend ↔ Backend API Contract

본 문서는 Frontend에서 Backend API를 호출하여 증여세 계산 챗봇을 구현할 때 필요한 API 명세를 정의합니다.

## 목차
1. [Base URL](#1-base-url)
2. [API Endpoints](#2-api-endpoints)
3. [Data Models](#3-data-models)
4. [TypeScript 타입 정의](#4-typescript-타입-정의)
5. [Error Handling](#5-error-handling)
6. [사용 예시](#6-사용-예시)

---

## 1. Base URL

```
Development: http://localhost:8000
Production: TBD
```

---

## 2. API Endpoints

### 2.1. 세션 생성

새로운 대화 세션을 생성합니다.

**Endpoint:** `POST /sessions`

**Request Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "client_id_hash": "optional-hash-string"
}
```

**Response:** `201 Created`
```json
{
  "id": "61e3f2ba-4130-40bc-bf21-a2f904fcd493",
  "client_id_hash": "hash-string",
  "created_at": "2025-10-17T09:30:00Z"
}
```

### 2.2. 메시지 전송

세션에 사용자 메시지를 전송하고 AI 응답을 받습니다.

**Endpoint:** `POST /sessions/{session_id}/messages`

**Request Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "content": "올해 8월에 아빠한테 10억 정도 받을거 같은데"
}
```

**Response:** `200 OK`
```json
{
  "id": "msg-uuid",
  "session_id": "session-uuid",
  "role": "assistant",
  "content": "📋 증여세 계산 결과\n\n아버지께서 증여하시는 10억원에 대한 증여세는 약 2억 2,500만원이에요...",
  "created_at": "2025-10-17T09:31:00Z",
  "msg_metadata": {
    "intent": "gift_tax",
    "collected_parameters": {
      "gift_date": "2025-08-01",
      "donor_relationship": "직계존속",
      "gift_property_value": 1000000000,
      "is_generation_skipping": false,
      "is_minor_recipient": false,
      "is_non_resident": false,
      "marriage_deduction_amount": 0,
      "childbirth_deduction_amount": 0,
      "secured_debt": 0
    },
    "missing_parameters": [],
    "calculation": {
      "final_tax": 225000000,
      "gift_value": 1000000000,
      "total_deduction": 50000000,
      "taxable_base": 950000000,
      "steps": [
        {
          "step": 1,
          "value": 1000000000,
          "detail": "1,000,000,000원 - 0원",
          "formula": "증여받은 재산가액 - 채무액",
          "description": "증여재산가액"
        },
        {
          "step": 2,
          "value": 50000000,
          "detail": "기본 50,000,000원 + 혼인 0원 + 출산 0원",
          "formula": "기본공제 + 혼인공제 + 출산공제",
          "description": "증여재산공제"
        },
        {
          "step": 3,
          "value": 950000000,
          "detail": "1,000,000,000원 - 50,000,000원",
          "formula": "증여재산가액 - 증여재산공제",
          "description": "과세표준"
        },
        {
          "step": 4,
          "value": 285000000,
          "detail": "950,000,000원 × 30%",
          "formula": "과세표준 × 세율",
          "description": "산출세액 (누진공제 차감 전)"
        },
        {
          "step": 5,
          "value": 60000000,
          "detail": "5억 초과 ~ 10억 이하 구간",
          "formula": "세율 구간별 누진공제",
          "description": "누진공제"
        },
        {
          "step": 6,
          "value": 225000000,
          "detail": "285,000,000원 - 60,000,000원",
          "formula": "산출세액 - 누진공제",
          "description": "최종 증여세액"
        }
      ],
      "calculation_breakdown": {
        "formatted_amounts": {
          "gift_value": "10억원",
          "total_deduction": "5,000만원",
          "taxable_base": "9억 5,000만원",
          "calculated_tax": "2억 8,500만원",
          "progressive_deduction": "6,000만원",
          "final_tax": "2억 2,500만원"
        },
        "tax_bracket": {
          "range": "5억 초과 ~ 10억 이하",
          "min": 500000001,
          "max": 1000000000,
          "rate": 0.30,
          "rate_display": "30%",
          "progressive_deduction": 60000000,
          "progressive_deduction_formatted": "6,000만원",
          "is_current": true
        },
        "all_tax_brackets": [
          {
            "range": "1억 이하",
            "min": 0,
            "max": 100000000,
            "rate": 0.10,
            "rate_display": "10%",
            "progressive_deduction": 0,
            "progressive_deduction_formatted": "0원",
            "is_current": false
          },
          {
            "range": "1억 초과 ~ 5억 이하",
            "min": 100000001,
            "max": 500000000,
            "rate": 0.20,
            "rate_display": "20%",
            "progressive_deduction": 10000000,
            "progressive_deduction_formatted": "1,000만원",
            "is_current": false
          },
          {
            "range": "5억 초과 ~ 10억 이하",
            "min": 500000001,
            "max": 1000000000,
            "rate": 0.30,
            "rate_display": "30%",
            "progressive_deduction": 60000000,
            "progressive_deduction_formatted": "6,000만원",
            "is_current": true
          },
          {
            "range": "10억 초과 ~ 30억 이하",
            "min": 1000000001,
            "max": 3000000000,
            "rate": 0.40,
            "rate_display": "40%",
            "progressive_deduction": 160000000,
            "progressive_deduction_formatted": "1.6억원",
            "is_current": false
          },
          {
            "range": "30억 초과",
            "min": 3000000001,
            "max": null,
            "rate": 0.50,
            "rate_display": "50%",
            "progressive_deduction": 460000000,
            "progressive_deduction_formatted": "4.6억원",
            "is_current": false
          }
        ],
        "calculation_steps_detailed": [
          {
            "step": 1,
            "description": "증여재산가액",
            "value": 1000000000,
            "formatted": "10억원"
          },
          {
            "step": 2,
            "description": "증여재산공제 (직계존속 → 성인자녀)",
            "value": 50000000,
            "formatted": "5,000만원",
            "breakdown": {
              "basic": "5,000만원",
              "marriage": null,
              "childbirth": null
            }
          },
          {
            "step": 3,
            "description": "과세표준",
            "value": 950000000,
            "formatted": "9억 5,000만원",
            "calculation": "10억원 - 5,000만원"
          },
          {
            "step": 4,
            "description": "산출세액 (누진공제 전)",
            "value": 285000000,
            "formatted": "2억 8,500만원",
            "calculation": "9.5억원 × 30%"
          },
          {
            "step": 5,
            "description": "누진공제",
            "value": 60000000,
            "formatted": "6,000만원",
            "info": "5억 초과 ~ 10억 이하 구간"
          },
          {
            "step": 6,
            "description": "최종 증여세액",
            "value": 225000000,
            "formatted": "2억 2,500만원",
            "calculation": "2억 8,500만원 - 6,000만원"
          }
        ]
      },
      "warnings": [
        "증여일로부터 3개월 이내(2025년 10월 31일까지, 남은 기간: 13일) 신고해야 합니다."
      ]
    }
  }
}
```

### 2.3. 대화 내역 조회

세션의 대화 내역을 조회합니다.

**Endpoint:** `GET /sessions/{session_id}/messages?limit=30&cursor={cursor}`

**Query Parameters:**
- `limit` (optional): 가져올 메시지 개수 (기본값: 30)
- `cursor` (optional): 페이지네이션 커서

**Response:** `200 OK`
```json
{
  "messages": [
    {
      "id": "msg-1",
      "session_id": "session-uuid",
      "role": "user",
      "content": "증여세 계산해줘",
      "created_at": "2025-10-17T09:30:00Z",
      "msg_metadata": null
    },
    {
      "id": "msg-2",
      "session_id": "session-uuid",
      "role": "assistant",
      "content": "증여일이 언제인가요?",
      "created_at": "2025-10-17T09:30:01Z",
      "msg_metadata": {
        "intent": "gift_tax",
        "collected_parameters": {},
        "missing_parameters": ["gift_date", "donor_relationship", "gift_property_value"]
      }
    }
  ],
  "next_cursor": null
}
```

---

## 3. Data Models

### 3.1. Message Metadata

메시지 메타데이터는 대화의 상태와 계산 결과를 포함합니다.

**필드 설명:**

- `intent`: 사용자 의도 (`"gift_tax"`, `"inheritance_tax"`, `"general_info"`, `"out_of_scope"`)
- `collected_parameters`: 수집된 증여세 계산 파라미터
- `missing_parameters`: 아직 수집되지 않은 필수 파라미터
- `calculation`: 계산 결과 (모든 파라미터 수집 완료 시에만 존재)

### 3.2. Collected Parameters

**9개 변수 (3개 Tier):**

**Tier 1 (필수 기본 정보):**
1. `gift_date`: 증여일 (YYYY-MM-DD)
2. `donor_relationship`: 증여자 관계 (`"직계존속"`, `"직계비속"`, `"배우자"`, `"기타친족"`)
3. `gift_property_value`: 증여재산가액 (숫자)

**Tier 2 (특례 판단):**
4. `is_generation_skipping`: 세대생략 여부 (boolean)
5. `is_minor_recipient`: 미성년자 여부 (boolean)
6. `is_non_resident`: 비거주자 여부 (boolean)

**Tier 3 (공제 및 채무):**
7. `marriage_deduction_amount`: 혼인공제액 (숫자, 0~100000000)
8. `childbirth_deduction_amount`: 출산공제액 (숫자, 0~100000000)
9. `secured_debt`: 담보채무액 (숫자)

### 3.3. Calculation Result

계산 결과는 두 가지 형식으로 제공됩니다:

1. **steps**: 기존 형식 (호환성 유지)
2. **calculation_breakdown**: 신규 상세 형식

**calculation_breakdown 구조:**

- `formatted_amounts`: 모든 금액을 읽기 좋은 형식으로 변환 ("10억원", "5,000만원" 등)
- `tax_bracket`: 현재 적용되는 세율 구간 정보
- `all_tax_brackets`: 전체 세율표 (현재 구간 강조 포함)
- `calculation_steps_detailed`: 상세한 계산 단계 (포맷팅된 금액 + 계산식 포함)

---

## 4. TypeScript 타입 정의

```typescript
// ============================================================================
// Session
// ============================================================================

interface Session {
  id: string;
  client_id_hash?: string;
  created_at: string;
}

// ============================================================================
// Message
// ============================================================================

interface Message {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  msg_metadata?: MessageMetadata;
}

interface MessageMetadata {
  intent?: Intent;
  collected_parameters?: CollectedParameters;
  missing_parameters?: string[];
  calculation?: CalculationResult;
}

type Intent = 'gift_tax' | 'inheritance_tax' | 'general_info' | 'out_of_scope';

// ============================================================================
// Collected Parameters
// ============================================================================

interface CollectedParameters {
  // Tier 1: 필수 기본 정보
  gift_date?: string;  // YYYY-MM-DD
  donor_relationship?: DonorRelationship;
  gift_property_value?: number;

  // Tier 2: 특례 판단
  is_generation_skipping?: boolean;
  is_minor_recipient?: boolean;
  is_non_resident?: boolean;

  // Tier 3: 공제 및 채무
  marriage_deduction_amount?: number;
  childbirth_deduction_amount?: number;
  secured_debt?: number;
}

type DonorRelationship = '직계존속' | '직계비속' | '배우자' | '기타친족';

// ============================================================================
// Calculation Result
// ============================================================================

interface CalculationResult {
  final_tax: number;
  gift_value: number;
  total_deduction: number;
  taxable_base: number;
  steps: CalculationStep[];
  calculation_breakdown: CalculationBreakdown;
  warnings: string[];
}

// 기존 호환성 유지
interface CalculationStep {
  step: number;
  value: number;
  detail: string;
  formula: string;
  description: string;
}

// ============================================================================
// Calculation Breakdown (신규)
// ============================================================================

interface CalculationBreakdown {
  formatted_amounts: FormattedAmounts;
  tax_bracket: TaxBracket;
  all_tax_brackets: TaxBracket[];
  calculation_steps_detailed: DetailedCalculationStep[];
}

interface FormattedAmounts {
  gift_value: string;          // "10억원"
  total_deduction: string;     // "5,000만원"
  taxable_base: string;        // "9억 5,000만원"
  calculated_tax: string;      // "2억 8,500만원"
  progressive_deduction: string; // "6,000만원"
  final_tax: string;           // "2억 2,500만원"
}

interface TaxBracket {
  range: string;                        // "5억 초과 ~ 10억 이하"
  min: number;
  max: number | null;
  rate: number;                         // 0.30
  rate_display: string;                 // "30%"
  progressive_deduction: number;        // 60000000
  progressive_deduction_formatted: string; // "6,000만원"
  is_current: boolean;                  // 현재 구간 여부
}

interface DetailedCalculationStep {
  step: number;
  description: string;
  value: number;
  formatted: string;
  calculation?: string;  // "10억원 - 5,000만원"
  breakdown?: {
    basic?: string;
    marriage?: string | null;
    childbirth?: string | null;
  };
  info?: string;
}
```

---

## 5. Error Handling

### 5.1. HTTP Status Codes

| Status Code | 설명 |
|-------------|------|
| `200 OK` | 성공 |
| `201 Created` | 세션 생성 성공 |
| `400 Bad Request` | 잘못된 요청 |
| `404 Not Found` | 리소스 없음 (세션 또는 메시지) |
| `500 Internal Server Error` | 서버 내부 오류 |
| `502 Bad Gateway` | Gemini API 오류 |

### 5.2. Error Response Format

```json
{
  "error": "Error Type",
  "message": "Human-readable error message"
}
```

**예시:**

**400 Bad Request:**
```json
{
  "error": "Bad Request",
  "message": "Invalid session_id format"
}
```

**404 Not Found:**
```json
{
  "error": "Not Found",
  "message": "Session not found"
}
```

**500 Internal Server Error:**
```json
{
  "error": "Internal Server Error",
  "message": "An unexpected error occurred"
}
```

**502 Bad Gateway:**
```json
{
  "error": "Gemini Error",
  "message": "Failed to communicate with Gemini API"
}
```

---

## 6. 사용 예시

### 6.1. API Client 구현

```typescript
class GiftTaxApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }

  async createSession(clientIdHash?: string): Promise<Session> {
    const response = await fetch(`${this.baseUrl}/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ client_id_hash: clientIdHash }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message);
    }

    return response.json();
  }

  async sendMessage(sessionId: string, content: string): Promise<Message> {
    const response = await fetch(
      `${this.baseUrl}/sessions/${sessionId}/messages`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message);
    }

    return response.json();
  }

  async getMessages(
    sessionId: string,
    limit: number = 30,
    cursor?: string
  ): Promise<{ messages: Message[]; next_cursor: string | null }> {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (cursor) params.append('cursor', cursor);

    const response = await fetch(
      `${this.baseUrl}/sessions/${sessionId}/messages?${params}`
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message);
    }

    return response.json();
  }
}
```

### 6.2. React Hook 예시

```typescript
import { useState, useMemo } from 'react';

function useGiftTaxChat(sessionId: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const client = useMemo(() => new GiftTaxApiClient(), []);

  const sendMessage = async (content: string) => {
    setIsLoading(true);

    try {
      // User message 추가
      const userMsg: Message = {
        id: `temp-${Date.now()}`,
        session_id: sessionId,
        role: 'user',
        content,
        created_at: new Date().toISOString(),
      };
      setMessages(prev => [...prev, userMsg]);

      // API 호출
      const assistantMsg = await client.sendMessage(sessionId, content);

      // Assistant message 추가
      setMessages(prev => [...prev.slice(0, -1), userMsg, assistantMsg]);
    } catch (error) {
      console.error('Failed to send message:', error);
      // 에러 처리 로직
    } finally {
      setIsLoading(false);
    }
  };

  return { messages, sendMessage, isLoading };
}
```

### 6.3. React 컴포넌트 예시

#### 계산 과정 표시

```tsx
function CalculationProcess({ steps }: { steps: DetailedCalculationStep[] }) {
  return (
    <div className="calculation-process">
      <h3>📊 상세 계산 과정</h3>
      {steps.map((step) => (
        <div key={step.step} className="step-item">
          <div className="step-number">#{step.step}</div>
          <div className="step-content">
            <div className="step-description">{step.description}</div>
            <div className="step-value">{step.formatted}</div>
            {step.calculation && (
              <div className="step-calculation">
                = {step.calculation}
              </div>
            )}
            {step.breakdown && (
              <div className="step-breakdown">
                {step.breakdown.basic && <span>기본: {step.breakdown.basic}</span>}
                {step.breakdown.marriage && <span>혼인: {step.breakdown.marriage}</span>}
                {step.breakdown.childbirth && <span>출산: {step.breakdown.childbirth}</span>}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
```

#### 세율표 표시

```tsx
function TaxBracketTable({ brackets }: { brackets: TaxBracket[] }) {
  return (
    <div className="tax-bracket-table">
      <h4>증여세 세율표</h4>
      <table>
        <thead>
          <tr>
            <th>과세표준 구간</th>
            <th>세율</th>
            <th>누진공제</th>
          </tr>
        </thead>
        <tbody>
          {brackets.map((bracket, idx) => (
            <tr
              key={idx}
              className={bracket.is_current ? 'current-bracket' : ''}
            >
              <td>
                {bracket.range}
                {bracket.is_current && <span className="badge">현재</span>}
              </td>
              <td>{bracket.rate_display}</td>
              <td>{bracket.progressive_deduction_formatted}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

#### 결과 요약 카드

```tsx
function SummaryCard({ summary }: { summary: FormattedAmounts }) {
  return (
    <div className="summary-card">
      <h2>📋 계산 결과</h2>
      <div className="summary-row">
        <span className="label">증여재산가액</span>
        <span className="value">{summary.gift_value}</span>
      </div>
      <div className="summary-row">
        <span className="label">공제액</span>
        <span className="value deduction">-{summary.total_deduction}</span>
      </div>
      <div className="summary-row total">
        <span className="label">과세표준</span>
        <span className="value">{summary.taxable_base}</span>
      </div>
      <div className="summary-row highlight">
        <span className="label">최종 증여세</span>
        <span className="value tax">{summary.final_tax}</span>
      </div>
    </div>
  );
}
```

---

## 부록: 대화 흐름 예시

### Turn 1: 초기 질문
**User:** "증여세 계산해줘"

**Response:**
```json
{
  "role": "assistant",
  "content": "증여일이 언제인가요?\n\n💡 증여세는 증여일을 기준으로 신고 기한(3개월)과 공제액이 결정됩니다.\n예시: 2025년 10월 15일, 올해 3월",
  "msg_metadata": {
    "intent": "gift_tax",
    "collected_parameters": {},
    "missing_parameters": ["gift_date", "donor_relationship", "gift_property_value"]
  }
}
```

### Turn 2: 일부 정보 제공
**User:** "올해 8월에 아빠한테 10억 정도 받을거 같은데"

**Response:**
```json
{
  "role": "assistant",
  "content": "📋 증여세 계산 결과\n\n아버지께서 증여하시는 10억원에 대한 증여세는 약 2억 2,500만원이에요...",
  "msg_metadata": {
    "intent": "gift_tax",
    "collected_parameters": {
      "gift_date": "2025-08-01",
      "donor_relationship": "직계존속",
      "gift_property_value": 1000000000,
      "is_generation_skipping": false,
      "is_minor_recipient": false,
      "is_non_resident": false,
      "marriage_deduction_amount": 0,
      "childbirth_deduction_amount": 0,
      "secured_debt": 0
    },
    "missing_parameters": [],
    "calculation": {
      "final_tax": 225000000,
      // ... 계산 결과
    }
  }
}
```

---

**문서 버전:** 1.0
**최종 수정일:** 2025-10-17
