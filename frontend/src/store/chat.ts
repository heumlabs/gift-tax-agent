/**
 * Chat Store
 * 메시지 관리 및 채팅 상태 관리
 */

import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { Message } from '@/types';
import * as messageApi from '@/services/api/messages';

export const useChatStore = defineStore('chat', () => {
  // ============================================================================
  // State
  // ============================================================================

  const messages = ref<Message[]>([]);
  const isLoadingMessages = ref(false);
  const isLoadingResponse = ref(false);
  const error = ref<string | null>(null);
  const currentSessionId = ref<string | null>(null);

  // ============================================================================
  // Getters
  // ============================================================================

  const sortedMessages = computed(() => {
    return [...messages.value].sort(
      (a, b) =>
        new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
    );
  });

  // ============================================================================
  // Actions
  // ============================================================================

  /**
   * 특정 세션의 메시지 불러오기
   */
  async function fetchMessages(sessionId: string) {
    isLoadingMessages.value = true;
    error.value = null;
    currentSessionId.value = sessionId;

    try {
      const response = await messageApi.getMessages(sessionId);
      messages.value = response.messages;
    } catch (e) {
      error.value = '메시지를 불러오는데 실패했습니다.';
      console.error('Failed to fetch messages:', e);
    } finally {
      isLoadingMessages.value = false;
    }
  }

  /**
   * 메시지 전송 (Optimistic UI 적용)
   */
  async function sendMessage(
    sessionId: string,
    content: string
  ): Promise<boolean> {
    if (!content.trim()) return false;

    isLoadingResponse.value = true;
    error.value = null;

    // Optimistic UI: 사용자 메시지를 즉시 화면에 표시
    const tempUserMessage: Message = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content,
      createdAt: new Date().toISOString(),
    };
    messages.value.push(tempUserMessage);

    try {
      const response = await messageApi.sendMessage(sessionId, content);

      // 임시 메시지 제거 후 실제 응답으로 교체
      messages.value = messages.value.filter(
        (m) => m.id !== tempUserMessage.id
      );

      // 사용자 메시지와 AI 응답을 모두 추가
      // (서버가 사용자 메시지를 반환하지 않으므로 클라이언트에서 추가)
      const userMessage: Message = {
        ...tempUserMessage,
        id: `user-${Date.now()}`,
      };
      messages.value.push(userMessage);
      messages.value.push(response.assistantMessage);

      return true;
    } catch (e) {
      // 실패 시 임시 메시지 제거
      messages.value = messages.value.filter(
        (m) => m.id !== tempUserMessage.id
      );
      error.value = '메시지 전송에 실패했습니다.';
      console.error('Failed to send message:', e);
      return false;
    } finally {
      isLoadingResponse.value = false;
    }
  }

  /**
   * 메시지 초기화
   */
  function clearMessages() {
    messages.value = [];
    currentSessionId.value = null;
  }

  return {
    // State
    messages,
    isLoadingMessages,
    isLoadingResponse,
    error,
    currentSessionId,

    // Getters
    sortedMessages,

    // Actions
    fetchMessages,
    sendMessage,
    clearMessages,
  };
});

