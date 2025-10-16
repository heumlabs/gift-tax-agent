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
  // 메시지 추가 순서를 추적하기 위한 시퀀스 번호
  let messageSequence = 0;
  const messageOrderMap = ref(new Map<string, number>());

  // ============================================================================
  // Getters
  // ============================================================================

  const sortedMessages = computed(() => {
    return [...messages.value].sort((a, b) => {
      const timeA = new Date(a.createdAt).getTime();
      const timeB = new Date(b.createdAt).getTime();
      
      // 시간이 다르면 시간순으로 정렬
      if (timeA !== timeB) {
        return timeA - timeB;
      }
      
      // 시간이 같으면 추가된 순서대로 정렬 (클라이언트에서 생성한 메시지 처리용)
      const orderA = messageOrderMap.value.get(a.id) || 0;
      const orderB = messageOrderMap.value.get(b.id) || 0;
      return orderA - orderB;
    });
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
      
      // 서버에서 받은 메시지들의 순서 정보 초기화
      const newOrderMap = new Map<string, number>();
      messageSequence = 0;
      response.messages.forEach((msg) => {
        newOrderMap.set(msg.id, messageSequence++);
      });
      messageOrderMap.value = newOrderMap;
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
    const newOrderMap1 = new Map(messageOrderMap.value);
    newOrderMap1.set(tempUserMessage.id, messageSequence++);
    messageOrderMap.value = newOrderMap1;
    messages.value.push(tempUserMessage);

    try {
      const response = await messageApi.sendMessage(sessionId, content);

      // 임시 메시지 제거
      messages.value = messages.value.filter(
        (m) => m.id !== tempUserMessage.id
      );
      const newOrderMap2 = new Map(messageOrderMap.value);
      newOrderMap2.delete(tempUserMessage.id);
      messageOrderMap.value = newOrderMap2;

      // 사용자 메시지와 AI 응답을 모두 추가
      // 서버 응답의 createdAt을 사용하되, 추가 순서도 기록
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: 'user',
        content,
        // 서버 응답보다 살짝 이전 시간으로 설정 (사용자 메시지가 먼저 표시되도록)
        createdAt: new Date(
          new Date(response.assistantMessage.createdAt).getTime() - 1000
        ).toISOString(),
      };
      
      const newOrderMap3 = new Map(messageOrderMap.value);
      newOrderMap3.set(userMessage.id, messageSequence++);
      newOrderMap3.set(response.assistantMessage.id, messageSequence++);
      messageOrderMap.value = newOrderMap3;
      
      messages.value.push(userMessage);
      messages.value.push(response.assistantMessage);

      return true;
    } catch (e) {
      // 실패 시 임시 메시지 제거
      messages.value = messages.value.filter(
        (m) => m.id !== tempUserMessage.id
      );
      const newOrderMap4 = new Map(messageOrderMap.value);
      newOrderMap4.delete(tempUserMessage.id);
      messageOrderMap.value = newOrderMap4;
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
    messageOrderMap.value = new Map<string, number>();
    messageSequence = 0;
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

