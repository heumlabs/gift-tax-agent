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

/**
 * 메시지 전송 및 스트리밍 AI 응답 수신 (시뮬레이션)
 * 백엔드가 스트리밍을 지원하지 않으므로, 클라이언트 측에서 타이핑 효과를 시뮬레이션합니다.
 */
export async function sendMessageWithStreaming(
  sessionId: string,
  content: string,
  onChunk: (chunk: string) => void
): Promise<SendMessageResponse> {
  // 실제 API 호출
  const response = await sendMessage(sessionId, content);
  
  // 응답을 받은 후 클라이언트 측에서 타이핑 효과 시뮬레이션
  const fullContent = response.assistantMessage.content;
  let currentIndex = 0;
  const chunkSize = 3; // 한 번에 표시할 글자 수
  const delay = 30; // 각 청크 간 지연 시간 (ms)
  
  return new Promise((resolve) => {
    const interval = setInterval(() => {
      if (currentIndex < fullContent.length) {
        const nextIndex = Math.min(currentIndex + chunkSize, fullContent.length);
        const chunk = fullContent.substring(0, nextIndex);
        onChunk(chunk);
        currentIndex = nextIndex;
      } else {
        clearInterval(interval);
        resolve(response);
      }
    }, delay);
  });
}

