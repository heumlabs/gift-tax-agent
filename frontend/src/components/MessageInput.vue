<script setup lang="ts">
import { ref, nextTick, watch } from 'vue';
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
const showButton = ref(false);

/**
 * 전송 버튼 표시 여부
 */
watch(
  () => inputText.value,
  (newValue) => {
    showButton.value = newValue.trim().length > 0;
  }
);

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
    showButton.value = false;
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
  <div class="border-t border-neutral-border bg-neutral-card p-6">
    <div class="flex items-end space-x-3 max-w-4xl mx-auto">
      <!-- 입력 영역 -->
      <div class="flex-1 relative">
        <textarea
          ref="textarea"
          v-model="inputText"
          :disabled="disabled || loading"
          placeholder="메시지를 입력하세요..."
          rows="1"
          class="w-full resize-none bg-transparent text-neutral-text placeholder-neutral-text-light px-4 py-3 pr-12 focus:outline-none border-b-2 border-neutral-border focus:border-primary transition-all max-h-40 overflow-y-auto"
          @input="adjustHeight"
          @keydown="handleKeydown"
          @compositionstart="handleCompositionStart"
          @compositionend="handleCompositionEnd"
        ></textarea>
      </div>

      <!-- 전송 버튼 (fade-in/out) -->
      <Transition
        enter-active-class="transition-all duration-200 ease-out"
        leave-active-class="transition-all duration-150 ease-in"
        enter-from-class="opacity-0 scale-90"
        enter-to-class="opacity-100 scale-100"
        leave-from-class="opacity-100 scale-100"
        leave-to-class="opacity-0 scale-90"
      >
        <Button
          v-show="showButton"
          variant="primary"
          size="md"
          :disabled="!inputText.trim() || disabled || loading"
          :loading="loading"
          @click="sendMessage"
        >
          <Icon name="send" :size="20" />
        </Button>
      </Transition>
    </div>

    <!-- 안내 메시지 -->
    <div class="text-xs text-neutral-text-light text-center mt-3">
      AI가 생성한 답변은 참고용이며, 중요한 결정은 전문가와 상담하시기 바랍니다.
    </div>
  </div>
</template>

<style scoped>
textarea {
  font-family: inherit;
  line-height: 1.6;
  font-weight: 500;
}

textarea::-webkit-scrollbar {
  width: 4px;
}

textarea::-webkit-scrollbar-track {
  background: transparent;
}

textarea::-webkit-scrollbar-thumb {
  background: #404040;
  border-radius: 2px;
}

textarea::-webkit-scrollbar-thumb:hover {
  background: #525252;
}
</style>
