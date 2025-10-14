<script setup lang="ts">
import { ref, watch, nextTick, onMounted } from 'vue';
import { useChatStore } from '@/store';
import ChatBubble from '@/components/ChatBubble.vue';
import MessageInput from '@/components/MessageInput.vue';
import LoadingIndicator from '@/components/common/LoadingIndicator.vue';

interface Props {
  sessionId: string;
}

const props = defineProps<Props>();

const chatStore = useChatStore();
const messagesContainer = ref<HTMLElement | null>(null);

/**
 * 메시지 목록 하단으로 스크롤
 */
const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    }
  });
};

/**
 * 메시지 전송
 */
const handleSendMessage = async (content: string) => {
  const success = await chatStore.sendMessage(props.sessionId, content);
  if (success) {
    scrollToBottom();
  }
};

/**
 * sessionId 변경 시 메시지 불러오기
 */
watch(
  () => props.sessionId,
  async (newSessionId) => {
    if (newSessionId) {
      await chatStore.fetchMessages(newSessionId);
      scrollToBottom();
    }
  },
  { immediate: true }
);

/**
 * 새 메시지 추가 시 스크롤
 */
watch(
  () => chatStore.messages.length,
  () => {
    scrollToBottom();
  }
);

onMounted(() => {
  scrollToBottom();
});
</script>

<template>
  <div class="flex flex-col h-full bg-neutral-bg">
    <!-- 메시지 영역 -->
    <div
      ref="messagesContainer"
      class="flex-1 overflow-y-auto p-4 space-y-4"
    >
      <!-- 로딩 상태 -->
      <div
        v-if="chatStore.isLoadingMessages"
        class="flex items-center justify-center h-full"
      >
        <LoadingIndicator />
      </div>

      <!-- 메시지 목록 -->
      <template v-else-if="chatStore.sortedMessages.length > 0">
        <ChatBubble
          v-for="message in chatStore.sortedMessages"
          :key="message.id"
          :message="message"
        />

        <!-- AI 응답 대기 중 -->
        <div v-if="chatStore.isLoadingResponse" class="flex justify-start">
          <div class="bg-neutral-card rounded-lg shadow-sm border border-neutral-border">
            <LoadingIndicator />
          </div>
        </div>
      </template>

      <!-- 빈 상태 -->
      <div v-else class="flex flex-col items-center justify-center h-full text-center">
        <div class="text-6xl mb-4">💬</div>
        <h3 class="text-xl font-bold text-neutral-text mb-2">
          새로운 상담을 시작하세요
        </h3>
        <p class="text-neutral-text-light">
          증여세, 상속세에 대해 궁금한 점을 물어보세요.
        </p>
      </div>
    </div>

    <!-- 입력 영역 -->
    <MessageInput
      :disabled="chatStore.isLoadingMessages"
      :loading="chatStore.isLoadingResponse"
      @send="handleSendMessage"
    />
  </div>
</template>

<style scoped>
/* 스크롤바 스타일 */
.overflow-y-auto::-webkit-scrollbar {
  width: 8px;
}

.overflow-y-auto::-webkit-scrollbar-track {
  background: #f1f5f9;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 4px;
}

.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}
</style>

