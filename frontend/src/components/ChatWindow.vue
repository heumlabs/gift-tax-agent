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

/**
 * 스트리밍 메시지 업데이트 시 스크롤
 */
watch(
  () => chatStore.streamingMessage?.content,
  () => {
    scrollToBottom();
  }
);

onMounted(() => {
  scrollToBottom();
});
</script>

<template>
  <div class="flex flex-col h-full bg-neutral-bg-secondary">
    <!-- 메시지 영역 -->
    <div
      ref="messagesContainer"
      class="flex-1 overflow-y-auto p-6 space-y-2"
    >
      <!-- 로딩 상태 -->
      <div
        v-if="chatStore.isLoadingMessages"
        class="flex items-center justify-center h-full"
      >
        <LoadingIndicator />
      </div>

      <!-- 메시지 목록 -->
      <template v-else-if="chatStore.sortedMessages.length > 0 || chatStore.streamingMessage">
        <ChatBubble
          v-for="message in chatStore.sortedMessages"
          :key="message.id"
          :message="message"
        />

        <!-- 스트리밍 중인 메시지 -->
        <ChatBubble
          v-if="chatStore.streamingMessage"
          :key="chatStore.streamingMessage.id"
          :message="chatStore.streamingMessage"
          :is-streaming="true"
        />

        <!-- AI 응답 대기 중 (스트리밍 시작 전) -->
        <div v-else-if="chatStore.isLoadingResponse" class="flex justify-start">
          <div class="flex-shrink-0 w-8 h-8 mr-3 rounded-full bg-accent flex items-center justify-center text-white font-bold text-sm">
            AI
          </div>
          <div class="bg-neutral-card rounded-2xl rounded-bl-sm px-5 py-3">
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
      :disabled="chatStore.isLoadingMessages || chatStore.isStreaming"
      :loading="chatStore.isLoadingResponse || chatStore.isStreaming"
      @send="handleSendMessage"
    />
  </div>
</template>

<style scoped>
/* 스크롤바 스타일 (다크 모드) */
.overflow-y-auto::-webkit-scrollbar {
  width: 8px;
}

.overflow-y-auto::-webkit-scrollbar-track {
  background: #171717;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  background: #404040;
  border-radius: 4px;
}

.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: #525252;
}
</style>
