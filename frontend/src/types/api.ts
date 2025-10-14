/**
 * API 관련 TypeScript 타입 정의
 * API 명세서 (docs/prd_detail/api-spec.md) 기반
 */

// ============================================================================
// Session 관련 타입
// ============================================================================

export interface Session {
  id: string;
  title: string;
  createdAt: string;
}

export interface CreateSessionResponse {
  id: string;
  title: string;
  createdAt: string;
}

export interface GetSessionsResponse {
  sessions: Session[];
  nextCursor?: string;
}

export interface UpdateSessionRequest {
  title: string;
}

export interface UpdateSessionResponse {
  id: string;
  title: string;
  createdAt: string;
}

// ============================================================================
// Message 관련 타입
// ============================================================================

export interface Citation {
  text: string;
  url: string;
}

export interface Calculation {
  assumptions: string[];
  taxableAmount: number;
  deduction: number;
  finalTax: number;
}

export interface MessageMetadata {
  citations?: Citation[];
  calculation?: Calculation;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  metadata?: MessageMetadata;
  createdAt: string;
}

export interface GetMessagesResponse {
  messages: Message[];
  nextCursor?: string;
}

export interface SendMessageRequest {
  content: string;
}

export interface SendMessageResponse {
  assistantMessage: Message;
}

// ============================================================================
// Error 관련 타입
// ============================================================================

export interface ApiError {
  code: string;
  message: string;
}

export interface ApiErrorResponse {
  error: ApiError;
}

