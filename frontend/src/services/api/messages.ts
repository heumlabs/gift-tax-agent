/**
 * Message API
 */

import { apiClient } from './client';
import type {
  GetMessagesResponse,
  SendMessageRequest,
  SendMessageResponse,
} from '@/types';

/**
 * 세션의 메시지 목록 조회
 */
export async function getMessages(
  sessionId: string,
  limit: number = 30,
  cursor?: string
): Promise<GetMessagesResponse> {
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
  const response = await apiClient.post<SendMessageResponse>(
    `/sessions/${sessionId}/messages`,
    { content } as SendMessageRequest
  );
  return response.data;
}

