<script setup lang="ts">
import { ref, nextTick } from 'vue';
import Icon from '@/components/common/Icon.vue';
import Button from '@/components/common/Button.vue';

interface Props {
  disabled?: boolean;
  loading?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  loading: false,
});

const emit = defineEmits<{
  send: [message: string];
}>();

const inputText = ref('');
const textarea = ref<HTMLTextAreaElement | null>(null);
const isComposing = ref(false);

/**
 * 자동으로 textarea 높이 조절
 */
const adjustHeight = () => {
  if (textarea.value) {
    textarea.value.style.height = 'auto';
    textarea.value.style.height = `${textarea.value.scrollHeight}px`;
  }
};

/**
 * 메시지 전송
 */
const sendMessage = () => {
  const message = inputText.value.trim();
  if (message && !props.disabled && !props.loading) {
    emit('send', message);
    inputText.value = '';
    nextTick(() => {
      adjustHeight();
      textarea.value?.focus();
    });
  }
};

/**
 * IME 조합 시작 (한글, 중국어, 일본어 등)
 */
const handleCompositionStart = () => {
  isComposing.value = true;
};

/**
 * IME 조합 종료
 */
const handleCompositionEnd = () => {
  isComposing.value = false;
};

/**
 * 키보드 이벤트 처리
 * IME 조합 중에는 Enter 키를 무시하여 한글 입력 문제 해결
 */
const handleKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Enter' && !event.shiftKey && !isComposing.value) {
    event.preventDefault();
    sendMessage();
  }
};
</script>

<template>
  <div class="border-t border-neutral-border bg-neutral-card p-4">
    <div class="flex items-end space-x-3 max-w-4xl mx-auto">
      <!-- 입력 영역 -->
      <div class="flex-1 relative">
        <textarea
          ref="textarea"
          v-model="inputText"
          :disabled="disabled || loading"
          placeholder="질문을 입력하세요... (Shift+Enter: 줄바꿈, Enter: 전송)"
          rows="1"
          class="w-full resize-none rounded-lg border border-neutral-border px-4 py-3 pr-12 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent disabled:bg-slate-50 disabled:text-slate-500 transition-all max-h-40 overflow-y-auto"
          @input="adjustHeight"
          @keydown="handleKeydown"
          @compositionstart="handleCompositionStart"
          @compositionend="handleCompositionEnd"
        ></textarea>
      </div>

      <!-- 전송 버튼 -->
      <Button
        variant="primary"
        size="md"
        :disabled="!inputText.trim() || disabled || loading"
        :loading="loading"
        @click="sendMessage"
      >
        <Icon name="send" :size="20" />
      </Button>
    </div>

    <!-- 안내 메시지 -->
    <div class="text-xs text-neutral-text-light text-center mt-2">
      AI가 생성한 답변은 참고용이며, 중요한 결정은 전문가와 상담하시기 바랍니다.
    </div>
  </div>
</template>

<style scoped>
textarea {
  font-family: inherit;
  line-height: 1.5;
}

textarea::-webkit-scrollbar {
  width: 6px;
}

textarea::-webkit-scrollbar-track {
  background: transparent;
}

textarea::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

textarea::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}
</style>

