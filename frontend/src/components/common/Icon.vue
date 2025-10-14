<script setup lang="ts">
/**
 * 아이콘 컴포넌트
 * 간단한 SVG 아이콘을 표시합니다.
 */

interface Props {
  name: 'menu' | 'send' | 'plus' | 'edit' | 'delete' | 'close' | 'check' | 'chevron-down';
  size?: number;
  class?: string;
}

withDefaults(defineProps<Props>(), {
  size: 24,
  class: '',
});
</script>

<template>
  <svg
    :width="size"
    :height="size"
    :class="class"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    viewBox="0 0 24 24"
  >
    <!-- Menu (햄버거) -->
    <template v-if="name === 'menu'">
      <line x1="3" y1="12" x2="21" y2="12"></line>
      <line x1="3" y1="6" x2="21" y2="6"></line>
      <line x1="3" y1="18" x2="21" y2="18"></line>
    </template>

    <!-- Send (전송) -->
    <template v-else-if="name === 'send'">
      <line x1="22" y1="2" x2="11" y2="13"></line>
      <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
    </template>

    <!-- Plus (추가) -->
    <template v-else-if="name === 'plus'">
      <line x1="12" y1="5" x2="12" y2="19"></line>
      <line x1="5" y1="12" x2="19" y2="12"></line>
    </template>

    <!-- Edit (수정) -->
    <template v-else-if="name === 'edit'">
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
    </template>

    <!-- Delete (삭제) -->
    <template v-else-if="name === 'delete'">
      <polyline points="3 6 5 6 21 6"></polyline>
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
    </template>

    <!-- Close (닫기) -->
    <template v-else-if="name === 'close'">
      <line x1="18" y1="6" x2="6" y2="18"></line>
      <line x1="6" y1="6" x2="18" y2="18"></line>
    </template>

    <!-- Check (확인) -->
    <template v-else-if="name === 'check'">
      <polyline points="20 6 9 17 4 12"></polyline>
    </template>

    <!-- Chevron Down (아래 화살표) -->
    <template v-else-if="name === 'chevron-down'">
      <polyline points="6 9 12 15 18 9"></polyline>
    </template>
  </svg>
</template>

