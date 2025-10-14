/**
 * Session API
 * Mock 모드와 실제 API 모드를 전환할 수 있는 구조
 */

import { apiClient } from './client';
import { env } from '@/config/env';
import type {
  CreateSessionResponse,
  GetSessionsResponse,
  UpdateSessionRequest,
  UpdateSessionResponse,
} from '@/types';

// Mock 데이터 import
import {
  mockSessions,
  createMockSession,
} from '@/services/mock/data';

/**
 * 세션 목록 조회
 */
export async function getSessions(
  limit: number = 20,
  cursor?: string
): Promise<GetSessionsResponse> {
  // ============================================================================
  // Mock 모드
  // ============================================================================
  if (env.useMock) {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          sessions: [...mockSessions],
          nextCursor: undefined,
        });
      }, 300); // 네트워크 지연 시뮬레이션
    });
  }

  // ============================================================================
  // 실제 API 호출
  // ============================================================================
  const response = await apiClient.get<GetSessionsResponse>('/sessions', {
    params: { limit, cursor },
  });
  return response.data;
}

/**
 * 새 세션 생성
 */
export async function createSession(): Promise<CreateSessionResponse> {
  // ============================================================================
  // Mock 모드
  // ============================================================================
  if (env.useMock) {
    return new Promise((resolve) => {
      setTimeout(() => {
        const newSession = createMockSession();
        mockSessions.unshift(newSession); // 목록 앞에 추가
        resolve(newSession);
      }, 300);
    });
  }

  // ============================================================================
  // 실제 API 호출
  // ============================================================================
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
  // ============================================================================
  // Mock 모드
  // ============================================================================
  if (env.useMock) {
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        const session = mockSessions.find((s) => s.id === sessionId);
        if (session) {
          session.title = title;
          resolve({ ...session });
        } else {
          reject(new Error('Session not found'));
        }
      }, 300);
    });
  }

  // ============================================================================
  // 실제 API 호출
  // ============================================================================
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
  // ============================================================================
  // Mock 모드
  // ============================================================================
  if (env.useMock) {
    return new Promise((resolve) => {
      setTimeout(() => {
        const index = mockSessions.findIndex((s) => s.id === sessionId);
        if (index !== -1) {
          mockSessions.splice(index, 1);
        }
        resolve();
      }, 300);
    });
  }

  // ============================================================================
  // 실제 API 호출
  // ============================================================================
  await apiClient.delete(`/sessions/${sessionId}`);
}

