<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { gsap } from 'gsap';

const cursor = ref<HTMLElement | null>(null);

onMounted(() => {
  // GSAP를 사용한 깜빡이는 커서 애니메이션
  if (cursor.value) {
    gsap.to(cursor.value, {
      opacity: 0,
      duration: 0.5,
      ease: 'power2.inOut',
      repeat: -1,
      yoyo: true,
    });
  }
});
</script>

<template>
  <div class="inline-flex items-center space-x-1 p-2">
    <span
      ref="cursor"
      class="w-0.5 h-5 bg-accent rounded-full"
    ></span>
  </div>
</template>
