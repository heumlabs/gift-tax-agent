/**
 * Session Store
 * 세션 목록 및 현재 세션 상태 관리
 */

import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { Session } from '@/types';
import * as sessionApi from '@/services/api/sessions';

export const useSessionStore = defineStore('session', () => {
  // ============================================================================
  // State
  // ============================================================================

  const sessions = ref<Session[]>([]);
  const currentSessionId = ref<string | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  // ============================================================================
  // Getters
  // ============================================================================

  const currentSession = computed(() => {
    if (!currentSessionId.value) return null;
    return sessions.value.find((s) => s.id === currentSessionId.value) || null;
  });

  const sortedSessions = computed(() => {
    return [...sessions.value].sort(
      (a, b) =>
        new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    );
  });

  // ============================================================================
  // Actions
  // ============================================================================

  /**
   * 세션 목록 불러오기
   */
  async function fetchSessions() {
    isLoading.value = true;
    error.value = null;

    try {
      const response = await sessionApi.getSessions();
      sessions.value = response.sessions;
    } catch (e) {
      error.value = '세션 목록을 불러오는데 실패했습니다.';
      console.error('Failed to fetch sessions:', e);
    } finally {
      isLoading.value = false;
    }
  }

  /**
   * 새 세션 생성
   */
  async function createSession(): Promise<Session | null> {
    isLoading.value = true;
    error.value = null;

    try {
      const newSession = await sessionApi.createSession();
      sessions.value.unshift(newSession);
      currentSessionId.value = newSession.id;
      return newSession;
    } catch (e) {
      error.value = '세션 생성에 실패했습니다.';
      console.error('Failed to create session:', e);
      return null;
    } finally {
      isLoading.value = false;
    }
  }

  /**
   * 세션 제목 수정
   */
  async function updateSessionTitle(
    sessionId: string,
    title: string
  ): Promise<boolean> {
    try {
      const updatedSession = await sessionApi.updateSession(sessionId, title);
      const index = sessions.value.findIndex((s) => s.id === sessionId);
      if (index !== -1) {
        sessions.value[index] = updatedSession;
      }
      return true;
    } catch (e) {
      error.value = '세션 제목 수정에 실패했습니다.';
      console.error('Failed to update session title:', e);
      return false;
    }
  }

  /**
   * 세션 삭제
   */
  async function deleteSession(sessionId: string): Promise<boolean> {
    try {
      await sessionApi.deleteSession(sessionId);
      sessions.value = sessions.value.filter((s) => s.id !== sessionId);

      // 현재 세션이 삭제된 경우 currentSessionId 초기화
      if (currentSessionId.value === sessionId) {
        currentSessionId.value = sessions.value[0]?.id || null;
      }

      return true;
    } catch (e) {
      error.value = '세션 삭제에 실패했습니다.';
      console.error('Failed to delete session:', e);
      return false;
    }
  }

  /**
   * 현재 세션 설정
   */
  function setCurrentSession(sessionId: string) {
    currentSessionId.value = sessionId;
  }

  return {
    // State
    sessions,
    currentSessionId,
    isLoading,
    error,

    // Getters
    currentSession,
    sortedSessions,

    // Actions
    fetchSessions,
    createSession,
    updateSessionTitle,
    deleteSession,
    setCurrentSession,
  };
});

