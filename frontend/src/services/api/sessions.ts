/**
 * Session API
 */

import { apiClient } from './client';
import type {
  CreateSessionResponse,
  GetSessionsResponse,
  UpdateSessionRequest,
  UpdateSessionResponse,
} from '@/types';

/**
 * 세션 목록 조회
 */
export async function getSessions(
  limit: number = 20,
  cursor?: string
): Promise<GetSessionsResponse> {
  const response = await apiClient.get<GetSessionsResponse>('/sessions', {
    params: { limit, cursor },
  });
  return response.data;
}

/**
 * 새 세션 생성
 */
export async function createSession(): Promise<CreateSessionResponse> {
  const response = await apiClient.post<CreateSessionResponse>('/sessions');
  return response.data;
}

/**
 * 세션 제목 수정
 */
export async function updateSession(
  sessionId: string,
  title: string
): Promise<UpdateSessionResponse> {
  const response = await apiClient.patch<UpdateSessionResponse>(
    `/sessions/${sessionId}`,
    { title } as UpdateSessionRequest
  );
  return response.data;
}

/**
 * 세션 삭제
 */
export async function deleteSession(sessionId: string): Promise<void> {
  await apiClient.delete(`/sessions/${sessionId}`);
}

