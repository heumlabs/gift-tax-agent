<script setup lang="ts">
import type { Message } from '@/types';

interface Props {
  message: Message;
}

defineProps<Props>();

const formatTime = (isoString: string) => {
  const date = new Date(isoString);
  return date.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
};
</script>

<template>
  <div
    :class="[
      'flex mb-4',
      message.role === 'user' ? 'justify-end' : 'justify-start',
    ]"
  >
    <div
      :class="[
        'max-w-[70%] rounded-lg p-4 shadow-sm',
        message.role === 'user'
          ? 'bg-primary text-white'
          : 'bg-neutral-card text-neutral-text border border-neutral-border',
      ]"
    >
      <!-- 메시지 내용 -->
      <div class="whitespace-pre-wrap break-words">{{ message.content }}</div>

      <!-- AI 메시지의 경우 추가 정보 표시 -->
      <template v-if="message.role === 'assistant' && message.metadata">
        <!-- 계산 정보 -->
        <div
          v-if="message.metadata.calculation"
          class="mt-3 pt-3 border-t border-slate-200"
        >
          <div class="text-sm font-medium mb-2">📊 계산 상세</div>
          <div class="text-sm space-y-1">
            <div v-if="message.metadata.calculation.assumptions?.length">
              <span class="font-medium">전제 조건:</span>
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
              <span class="font-medium">과세 대상:</span>
              <span class="ml-2">{{
                message.metadata.calculation.taxableAmount.toLocaleString()
              }}원</span>
            </div>
            <div v-if="message.metadata.calculation.deduction !== undefined">
              <span class="font-medium">공제액:</span>
              <span class="ml-2">{{
                message.metadata.calculation.deduction.toLocaleString()
              }}원</span>
            </div>
            <div
              v-if="message.metadata.calculation.finalTax !== undefined"
              class="font-bold text-secondary"
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
          class="mt-3 pt-3 border-t border-slate-200"
        >
          <div class="text-sm font-medium mb-2">📚 법령 근거</div>
          <div class="space-y-1">
            <a
              v-for="(citation, idx) in message.metadata.citations"
              :key="idx"
              :href="citation.url"
              target="_blank"
              rel="noopener noreferrer"
              class="block text-sm text-blue-600 hover:text-blue-800 underline"
            >
              {{ citation.text }}
            </a>
          </div>
        </div>
      </template>

      <!-- 시간 표시 -->
      <div
        :class="[
          'text-xs mt-2',
          message.role === 'user' ? 'text-blue-100' : 'text-neutral-text-light',
        ]"
      >
        {{ formatTime(message.createdAt) }}
      </div>
    </div>
  </div>
</template>

