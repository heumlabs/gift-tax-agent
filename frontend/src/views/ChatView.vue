<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useSessionStore } from '@/store';
import SessionList from '@/components/SessionList.vue';
import ChatWindow from '@/components/ChatWindow.vue';
import Icon from '@/components/common/Icon.vue';

const route = useRoute();
const router = useRouter();
const sessionStore = useSessionStore();

const isSidebarVisible = ref(true);
const isMobile = ref(false);

/**
 * 현재 세션 ID
 */
const currentSessionId = computed(() => {
  const sessionIdFromRoute = route.params.sessionId as string;
  return sessionIdFromRoute || sessionStore.currentSessionId;
});

/**
 * 반응형 체크
 */
const checkMobile = () => {
  isMobile.value = window.innerWidth < 1024;
  if (!isMobile.value) {
    isSidebarVisible.value = true;
  }
};

/**
 * 사이드바 토글
 */
const toggleSidebar = () => {
  isSidebarVisible.value = !isSidebarVisible.value;
};

/**
 * 세션 선택 핸들러
 */
const handleSessionSelect = (sessionId: string) => {
  router.push(`/chat/${sessionId}`);
  
  // 모바일에서는 세션 선택 시 사이드바 닫기
  if (isMobile.value) {
    isSidebarVisible.value = false;
  }
};

/**
 * 사이드바 닫기 (모바일)
 */
const closeSidebar = () => {
  if (isMobile.value) {
    isSidebarVisible.value = false;
  }
};

onMounted(async () => {
  // 세션 목록 불러오기
  await sessionStore.fetchSessions();

  // 반응형 체크
  checkMobile();
  window.addEventListener('resize', checkMobile);

  // URL에 sessionId가 없으면 첫 번째 세션이나 새 세션으로 이동
  if (!route.params.sessionId) {
    if (sessionStore.sessions.length > 0) {
      const firstSession = sessionStore.sortedSessions[0];
      if (firstSession) {
        router.replace(`/chat/${firstSession.id}`);
      }
    } else {
      // 세션이 없으면 새로 생성
      const newSession = await sessionStore.createSession();
      if (newSession) {
        router.replace(`/chat/${newSession.id}`);
      }
    }
  }
});
</script>

<template>
  <div class="flex h-screen overflow-hidden">
    <!-- 모바일 오버레이 -->
    <div
      v-if="isMobile && isSidebarVisible"
      class="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
      @click="closeSidebar"
    ></div>

    <!-- 사이드바 -->
    <div
      :class="[
        'fixed lg:relative z-50 h-full transition-transform duration-300',
        isSidebarVisible ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
      ]"
    >
      <SessionList
        :is-visible="true"
        @session-select="handleSessionSelect"
        @close="closeSidebar"
      />
    </div>

    <!-- 메인 콘텐츠 -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- 헤더 (모바일용) -->
      <div class="lg:hidden flex items-center justify-between p-4 bg-neutral-card border-b border-neutral-border">
        <button
          class="p-2 hover:bg-slate-100 rounded-lg transition-colors"
          @click="toggleSidebar"
        >
          <Icon name="menu" :size="24" />
        </button>
        <h1 class="text-lg font-bold text-neutral-text">슈킹 AI</h1>
        <div class="w-10"></div>
      </div>

      <!-- 채팅 영역 -->
      <div class="flex-1 overflow-hidden">
        <ChatWindow
          v-if="currentSessionId"
          :key="currentSessionId"
          :session-id="currentSessionId"
        />
        <div
          v-else
          class="flex items-center justify-center h-full bg-neutral-bg"
        >
          <div class="text-center">
            <div class="text-6xl mb-4">🤖</div>
            <p class="text-neutral-text-light">세션을 선택하거나 새로 생성해주세요.</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 모바일에서 사이드바 애니메이션 */
@media (max-width: 1023px) {
  .fixed.z-50 {
    width: 280px;
  }
}
</style>

