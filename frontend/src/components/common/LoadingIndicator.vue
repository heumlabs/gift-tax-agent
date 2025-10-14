<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { gsap } from 'gsap';

const dot1 = ref<HTMLElement | null>(null);
const dot2 = ref<HTMLElement | null>(null);
const dot3 = ref<HTMLElement | null>(null);

onMounted(() => {
  // GSAP를 사용한 pulsing 애니메이션
  const timeline = gsap.timeline({ repeat: -1 });

  timeline
    .to(dot1.value, {
      opacity: 0.3,
      scale: 0.8,
      duration: 0.4,
      ease: 'power1.inOut',
    })
    .to(
      dot2.value,
      {
        opacity: 0.3,
        scale: 0.8,
        duration: 0.4,
        ease: 'power1.inOut',
      },
      '-=0.2'
    )
    .to(
      dot3.value,
      {
        opacity: 0.3,
        scale: 0.8,
        duration: 0.4,
        ease: 'power1.inOut',
      },
      '-=0.2'
    )
    .to(dot1.value, {
      opacity: 1,
      scale: 1,
      duration: 0.4,
      ease: 'power1.inOut',
    })
    .to(
      dot2.value,
      {
        opacity: 1,
        scale: 1,
        duration: 0.4,
        ease: 'power1.inOut',
      },
      '-=0.2'
    )
    .to(
      dot3.value,
      {
        opacity: 1,
        scale: 1,
        duration: 0.4,
        ease: 'power1.inOut',
      },
      '-=0.2'
    );
});
</script>

<template>
  <div class="flex items-center space-x-2 p-4">
    <span
      ref="dot1"
      class="w-2 h-2 bg-primary rounded-full"
    ></span>
    <span
      ref="dot2"
      class="w-2 h-2 bg-primary rounded-full"
    ></span>
    <span
      ref="dot3"
      class="w-2 h-2 bg-primary rounded-full"
    ></span>
  </div>
</template>

