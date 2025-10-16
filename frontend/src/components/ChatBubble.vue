<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue';
import { gsap } from 'gsap';
import { marked } from 'marked';
import type { Message } from '@/types';

interface Props {
  message: Message;
  isStreaming?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  isStreaming: false,
});

// Marked 설정
marked.setOptions({
  breaks: true, // 줄바꿈을 <br>로 변환
  gfm: true, // GitHub Flavored Markdown 지원
});

const messageContainer = ref<HTMLElement | null>(null);
const displayedContent = ref('');
const chars = computed(() => displayedContent.value.split(''));

/**
 * 마크다운을 HTML로 렌더링 (일반 메시지용)
 */
const renderedHtml = computed(() => {
  if (props.message.role === 'assistant' && !props.isStreaming) {
    return marked(displayedContent.value);
  }
  return '';
});

const formatTime = (isoString: string) => {
  const date = new Date(isoString);
  return date.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
};

/**
 * 페이드인 꼬리 효과를 위한 투명도 계산
 */
const getCharOpacity = (index: number): number => {
  const totalChars = chars.value.length;
  const distanceFromEnd = totalChars - 1 - index;
  
  if (distanceFromEnd === 0 && props.isStreaming) return 0.3;
  if (distanceFromEnd === 1 && props.isStreaming) return 0.5;
  if (distanceFromEnd === 2 && props.isStreaming) return 0.7;
  if (distanceFromEnd === 3 && props.isStreaming) return 0.85;
  
  return 1.0;
};

/**
 * 스트리밍 중 content가 변경될 때마다 업데이트
 */
watch(
  () => props.message.content,
  (newContent) => {
    if (props.isStreaming) {
      displayedContent.value = newContent;
    }
  },
  { immediate: true }
);

/**
 * 일반 메시지의 경우 마운트 시 타이핑 효과 (선택적)
 */
onMounted(() => {
  if (!props.isStreaming && props.message.role === 'assistant') {
    // 일반 메시지는 즉시 표시
    displayedContent.value = props.message.content;
    
    // 메시지 등장 애니메이션
    if (messageContainer.value) {
      gsap.from(messageContainer.value, {
        opacity: 0,
        y: 20,
        duration: 0.4,
        ease: 'power2.out',
      });
    }
  } else {
    displayedContent.value = props.message.content;
  }
});
</script>

<template>
  <div
    ref="messageContainer"
    :class="[
      'flex mb-6',
      message.role === 'user' ? 'justify-end' : 'justify-start',
    ]"
  >
    <!-- AI 아이콘 -->
    <div
      v-if="message.role === 'assistant'"
      class="flex-shrink-0 w-8 h-8 mr-3 rounded-full bg-accent flex items-center justify-center text-white font-bold text-sm"
    >
      AI
    </div>

    <div class="flex flex-col max-w-[75%]">
      <div
        :class="[
          'rounded-2xl px-5 py-3',
          message.role === 'user'
            ? 'bg-primary text-white rounded-br-sm'
            : 'bg-neutral-card text-neutral-text rounded-bl-sm',
        ]"
      >
        <!-- 사용자 메시지 또는 스트리밍 중인 AI 메시지 (페이드인 꼬리 효과) -->
        <div
          v-if="message.role === 'user' || isStreaming"
          class="whitespace-pre-wrap break-words leading-relaxed"
        >
          <span
            v-for="(char, index) in chars"
            :key="`${message.id}-char-${index}`"
            :style="{ opacity: getCharOpacity(index) }"
            class="transition-opacity duration-200"
          >{{ char }}</span>
        </div>

        <!-- AI 메시지 (마크다운 렌더링) -->
        <div
          v-else-if="message.role === 'assistant'"
          class="markdown-content leading-relaxed"
          v-html="renderedHtml"
        ></div>

        <!-- AI 메시지의 경우 추가 정보 표시 -->
        <template v-if="message.role === 'assistant' && message.metadata && !isStreaming">
          <!-- 계산 정보 -->
          <div
            v-if="message.metadata.calculation"
            class="mt-4 pt-4 border-t border-neutral-border"
          >
            <div class="text-sm font-semibold mb-2 text-accent">📊 계산 상세</div>
            <div class="text-sm space-y-2">
              <div v-if="message.metadata.calculation.assumptions?.length">
                <span class="font-medium text-neutral-text-light">전제 조건:</span>
                <ul class="list-disc list-inside ml-2 mt-1">
                  <li
                    v-for="(assumption, idx) in message.metadata.calculation.assumptions"
                    :key="idx"
                    class="text-neutral-text-light"
                  >
                    {{ assumption }}
                  </li>
                </ul>
              </div>
              <div v-if="message.metadata.calculation.taxableAmount !== undefined">
                <span class="font-medium text-neutral-text-light">과세 대상:</span>
                <span class="ml-2 text-neutral-text">{{
                  message.metadata.calculation.taxableAmount.toLocaleString()
                }}원</span>
              </div>
              <div v-if="message.metadata.calculation.deduction !== undefined">
                <span class="font-medium text-neutral-text-light">공제액:</span>
                <span class="ml-2 text-neutral-text">{{
                  message.metadata.calculation.deduction.toLocaleString()
                }}원</span>
              </div>
              <div
                v-if="message.metadata.calculation.finalTax !== undefined"
                class="font-bold text-accent"
              >
                <span class="font-medium">최종 세액:</span>
                <span class="ml-2">{{
                  message.metadata.calculation.finalTax.toLocaleString()
                }}원</span>
              </div>
            </div>
          </div>

          <!-- 법령 출처 -->
          <div
            v-if="message.metadata.citations?.length"
            class="mt-4 pt-4 border-t border-neutral-border"
          >
            <div class="text-sm font-semibold mb-2 text-accent">📚 법령 근거</div>
            <div class="space-y-1">
              <a
                v-for="(citation, idx) in message.metadata.citations"
                :key="idx"
                :href="citation.url"
                target="_blank"
                rel="noopener noreferrer"
                class="block text-sm text-primary hover:text-primary-hover underline"
              >
                {{ citation.text }}
              </a>
            </div>
          </div>
        </template>
      </div>

      <!-- 시간 표시 -->
      <div
        :class="[
          'text-xs mt-1 px-2',
          message.role === 'user' ? 'text-right text-neutral-text-light' : 'text-left text-neutral-text-light',
        ]"
      >
        {{ formatTime(message.createdAt) }}
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 마크다운 컨텐츠 스타일링 */
.markdown-content {
  font-weight: 500;
}

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4),
.markdown-content :deep(h5),
.markdown-content :deep(h6) {
  font-weight: 700;
  margin-top: 1em;
  margin-bottom: 0.5em;
  color: #E5E5E5;
}

.markdown-content :deep(h1) {
  font-size: 1.5em;
}

.markdown-content :deep(h2) {
  font-size: 1.25em;
}

.markdown-content :deep(h3) {
  font-size: 1.125em;
}

.markdown-content :deep(p) {
  margin-bottom: 0.75em;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin-left: 1.5em;
  margin-bottom: 0.75em;
}

.markdown-content :deep(li) {
  margin-bottom: 0.25em;
}

.markdown-content :deep(code) {
  background-color: rgba(255, 255, 255, 0.1);
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.9em;
  color: #818CF8;
}

.markdown-content :deep(pre) {
  background-color: rgba(255, 255, 255, 0.05);
  padding: 1rem;
  border-radius: 0.5rem;
  overflow-x: auto;
  margin-bottom: 0.75em;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.markdown-content :deep(pre code) {
  background-color: transparent;
  padding: 0;
  color: #E5E5E5;
}

.markdown-content :deep(blockquote) {
  border-left: 3px solid #818CF8;
  padding-left: 1rem;
  margin-left: 0;
  margin-bottom: 0.75em;
  color: #A3A3A3;
  font-style: italic;
}

.markdown-content :deep(a) {
  color: #3B82F6;
  text-decoration: underline;
}

.markdown-content :deep(a:hover) {
  color: #2563EB;
}

.markdown-content :deep(strong) {
  font-weight: 700;
  color: #E5E5E5;
}

.markdown-content :deep(em) {
  font-style: italic;
}

.markdown-content :deep(hr) {
  border: none;
  border-top: 1px solid #404040;
  margin: 1em 0;
}

.markdown-content :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin-bottom: 0.75em;
}

.markdown-content :deep(th),
.markdown-content :deep(td) {
  border: 1px solid #404040;
  padding: 0.5rem;
  text-align: left;
}

.markdown-content :deep(th) {
  background-color: rgba(255, 255, 255, 0.05);
  font-weight: 600;
}
</style>
