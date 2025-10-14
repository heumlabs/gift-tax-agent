/**
 * Message API
 * Mock 모드와 실제 API 모드를 전환할 수 있는 구조
 */

import { apiClient } from './client';
import { env } from '@/config/env';
import type {
  GetMessagesResponse,
  SendMessageRequest,
  SendMessageResponse,
} from '@/types';

// Mock 데이터 import
import {
  getMockMessagesBySessionId,
  addMockMessage,
} from '@/services/mock/data';

/**
 * 세션의 메시지 목록 조회
 */
export async function getMessages(
  sessionId: string,
  limit: number = 30,
  cursor?: string
): Promise<GetMessagesResponse> {
  // ============================================================================
  // Mock 모드
  // ============================================================================
  if (env.useMock) {
    return new Promise((resolve) => {
      setTimeout(() => {
        const messages = getMockMessagesBySessionId(sessionId);
        resolve({
          messages: [...messages],
          nextCursor: undefined,
        });
      }, 300);
    });
  }

  // ============================================================================
  // 실제 API 호출
  // ============================================================================
  const response = await apiClient.get<GetMessagesResponse>(
    `/sessions/${sessionId}/messages`,
    {
      params: { limit, cursor },
    }
  );
  return response.data;
}

/**
 * 메시지 전송 및 AI 응답 수신
 */
export async function sendMessage(
  sessionId: string,
  content: string
): Promise<SendMessageResponse> {
  // ============================================================================
  // Mock 모드
  // ============================================================================
  if (env.useMock) {
    return new Promise((resolve) => {
      // AI 응답 시뮬레이션 (1-2초 지연)
      const delay = 1000 + Math.random() * 1000;
      setTimeout(() => {
        const assistantMessage = addMockMessage(sessionId, content);
        resolve({ assistantMessage });
      }, delay);
    });
  }

  // ============================================================================
  // 실제 API 호출
  // ============================================================================
  const response = await apiClient.post<SendMessageResponse>(
    `/sessions/${sessionId}/messages`,
    { content } as SendMessageRequest
  );
  return response.data;
}

