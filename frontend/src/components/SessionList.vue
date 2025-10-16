<script setup lang="ts">
import { ref } from 'vue';
import { useSessionStore } from '@/store';
import Button from '@/components/common/Button.vue';
import Icon from '@/components/common/Icon.vue';

interface Props {
  isVisible?: boolean;
}

withDefaults(defineProps<Props>(), {
  isVisible: true,
});

const emit = defineEmits<{
  'session-select': [sessionId: string];
  close: [];
}>();

const sessionStore = useSessionStore();

const editingSessionId = ref<string | null>(null);
const editingTitle = ref('');

/**
 * 새 세션 생성
 */
const handleCreateSession = async () => {
  const newSession = await sessionStore.createSession();
  if (newSession) {
    emit('session-select', newSession.id);
  }
};

/**
 * 세션 선택
 */
const handleSelectSession = (sessionId: string) => {
  sessionStore.setCurrentSession(sessionId);
  emit('session-select', sessionId);
};

/**
 * 세션 제목 수정 시작
 */
const startEditingTitle = (sessionId: string, currentTitle: string) => {
  editingSessionId.value = sessionId;
  editingTitle.value = currentTitle;
};

/**
 * 세션 제목 수정 완료
 */
const finishEditingTitle = async () => {
  if (editingSessionId.value && editingTitle.value.trim()) {
    await sessionStore.updateSessionTitle(
      editingSessionId.value,
      editingTitle.value.trim()
    );
  }
  editingSessionId.value = null;
  editingTitle.value = '';
};

/**
 * 세션 삭제
 */
const handleDeleteSession = async (sessionId: string) => {
  if (confirm('이 세션을 삭제하시겠습니까?')) {
    const success = await sessionStore.deleteSession(sessionId);
    if (success && sessionStore.currentSessionId) {
      emit('session-select', sessionStore.currentSessionId);
    }
  }
};
</script>

<template>
  <div
    v-show="isVisible"
    class="w-sidebar bg-neutral-card border-r border-neutral-border flex flex-col h-full"
  >
    <!-- 헤더 -->
    <div class="p-4 border-b border-neutral-border">
      <div class="flex items-center justify-between mb-4">
        <h1 class="text-xl font-bold text-neutral-text">슈킹 AI</h1>
        <button
          class="lg:hidden p-2 hover:bg-neutral-card-hover rounded-lg transition-colors"
          @click="emit('close')"
        >
          <Icon name="close" :size="20" class="text-neutral-text-light" />
        </button>
      </div>
      <Button
        variant="primary"
        size="md"
        full-width
        :loading="sessionStore.isLoading"
        @click="handleCreateSession"
      >
        <Icon name="plus" :size="20" class="mr-2" />
        새 상담
      </Button>
    </div>

    <!-- 세션 목록 -->
    <div class="flex-1 overflow-y-auto p-2">
      <div
        v-if="sessionStore.isLoading && sessionStore.sessions.length === 0"
        class="text-center text-neutral-text-light py-8"
      >
        로딩 중...
      </div>

      <div
        v-else-if="sessionStore.sortedSessions.length === 0"
        class="text-center text-neutral-text-light py-8"
      >
        세션이 없습니다
      </div>

      <div v-else class="space-y-1">
        <div
          v-for="session in sessionStore.sortedSessions"
          :key="session.id"
          :class="[
            'group relative p-3 rounded-lg cursor-pointer transition-all duration-200',
            sessionStore.currentSessionId === session.id
              ? 'bg-primary/20 border border-primary/50'
              : 'hover:bg-neutral-card-hover',
          ]"
          @click="handleSelectSession(session.id)"
        >
          <!-- 세션 제목 (편집 중이 아닐 때) -->
          <div
            v-if="editingSessionId !== session.id"
            class="flex items-start justify-between"
          >
            <div class="flex-1 min-w-0">
              <div
                :class="[
                  'font-medium truncate',
                  sessionStore.currentSessionId === session.id
                    ? 'text-primary'
                    : 'text-neutral-text',
                ]"
              >
                {{ session.title }}
              </div>
              <div class="text-xs text-neutral-text-light mt-1">
                {{ new Date(session.createdAt).toLocaleDateString('ko-KR') }}
              </div>
            </div>

            <!-- 액션 버튼들 -->
            <div class="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity ml-2">
              <button
                class="p-1 hover:bg-neutral-border rounded transition-colors"
                @click.stop="startEditingTitle(session.id, session.title)"
              >
                <Icon name="edit" :size="16" class="text-neutral-text-light" />
              </button>
              <button
                class="p-1 hover:bg-danger/20 rounded transition-colors"
                @click.stop="handleDeleteSession(session.id)"
              >
                <Icon name="delete" :size="16" class="text-danger" />
              </button>
            </div>
          </div>

          <!-- 세션 제목 편집 중 -->
          <div v-else @click.stop>
            <input
              v-model="editingTitle"
              type="text"
              class="w-full px-2 py-1 bg-neutral-bg-secondary text-neutral-text border border-primary rounded focus:outline-none focus:ring-2 focus:ring-primary"
              @keydown.enter="finishEditingTitle"
              @keydown.esc="editingSessionId = null"
              @blur="finishEditingTitle"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 푸터 -->
    <div class="p-4 border-t border-neutral-border text-xs text-neutral-text-light text-center">
      <p>슈킹 AI v1.0</p>
      <p class="mt-1">세금 절세를 위한 AI 상담사</p>
    </div>
  </div>
</template>

<style scoped>
.overflow-y-auto::-webkit-scrollbar {
  width: 6px;
}

.overflow-y-auto::-webkit-scrollbar-track {
  background: transparent;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  background: #404040;
  border-radius: 3px;
}

.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: #525252;
}
</style>
