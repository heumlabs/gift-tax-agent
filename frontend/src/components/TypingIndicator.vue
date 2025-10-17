<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { gsap } from 'gsap';

const container = ref<HTMLElement | null>(null);

onMounted(() => {
  if (container.value) {
    // 컨테이너 페이드인
    gsap.from(container.value, {
      opacity: 0,
      y: 10,
      duration: 0.3,
      ease: 'power2.out',
    });

    // 점들의 순차적 애니메이션
    const dots = container.value.querySelectorAll('.typing-dot');
    dots.forEach((dot, index) => {
      gsap.to(dot, {
        opacity: 0.3,
        scale: 0.8,
        duration: 0.6,
        repeat: -1,
        yoyo: true,
        ease: 'power1.inOut',
        delay: index * 0.2,
      });
    });
  }
});
</script>

<template>
  <div
    ref="container"
    class="flex mb-6 justify-start"
  >
    <!-- AI 아이콘 (모바일에서 숨김) -->
    <div
      class="hidden md:flex flex-shrink-0 w-8 h-8 mr-3 rounded-full bg-accent items-center justify-center text-white font-bold text-sm"
    >
      AI
    </div>

    <div class="flex flex-col max-w-[95%] md:max-w-[85%] lg:max-w-[75%]">
      <div
        class="rounded-2xl px-5 py-4 bg-neutral-card text-neutral-text rounded-bl-sm"
      >
        <div class="flex items-center space-x-2">
          <div 
            class="typing-dot w-2 h-2 rounded-full bg-neutral-text-light"
          ></div>
          <div 
            class="typing-dot w-2 h-2 rounded-full bg-neutral-text-light"
          ></div>
          <div 
            class="typing-dot w-2 h-2 rounded-full bg-neutral-text-light"
          ></div>
        </div>
      </div>

      <!-- 시간 표시 -->
      <div class="text-xs mt-1 px-2 text-left text-neutral-text-light">
        {{ new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }) }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.typing-dot {
  transition: all 0.3s ease;
}
</style>

