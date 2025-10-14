<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { gsap } from 'gsap';
import Button from '@/components/common/Button.vue';

const router = useRouter();

const heroSection = ref<HTMLElement | null>(null);
const featuresSection = ref<HTMLElement | null>(null);

const faqItems = ref([
  {
    question: '이 서비스는 무료인가요?',
    answer: '네, 슈킹 AI는 완전히 무료로 제공됩니다. 회원가입 없이 바로 이용하실 수 있습니다.',
    isOpen: false,
  },
  {
    question: 'AI의 답변을 완전히 신뢰할 수 있나요?',
    answer:
      'AI는 최신 법령과 예규를 기반으로 답변하지만, 참고용으로만 활용해주세요. 중요한 결정을 내리시기 전에는 반드시 세무 전문가와 상담하시기 바랍니다.',
    isOpen: false,
  },
  {
    question: '세무 신고도 대신 해주나요?',
    answer:
      '아니요, 슈킹 AI는 정보 제공 및 상담만 진행합니다. 실제 세무 신고는 세무사나 세무 대리인을 통해 진행하셔야 합니다.',
    isOpen: false,
  },
  {
    question: '제 대화 기록은 어떻게 관리되나요?',
    answer:
      '모든 대화는 브라우저 식별자를 기반으로 익명으로 저장됩니다. 민감한 개인정보는 수집하지 않으며, 대화 내용은 서비스 개선 목적으로만 사용됩니다.',
    isOpen: false,
  },
]);

const toggleFaq = (index: number) => {
  const item = faqItems.value[index];
  if (item) {
    item.isOpen = !item.isOpen;
  }
};

const startChat = () => {
  router.push('/chat');
};

onMounted(() => {
  // Hero 섹션 애니메이션
  if (heroSection.value) {
    gsap.fromTo(
      heroSection.value.children,
      { opacity: 0, y: 30 },
      {
        opacity: 1,
        y: 0,
        duration: 1,
        stagger: 0.2,
        ease: 'power2.out',
      }
    );
  }
});
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-blue-50">
    <!-- Hero Section -->
    <section ref="heroSection" class="relative min-h-screen flex items-center justify-center px-4 py-20">
      <!-- 배경 그라데이션 효과 -->
      <div class="absolute inset-0 overflow-hidden pointer-events-none">
        <div
          class="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob"
        ></div>
        <div
          class="absolute top-1/3 right-1/4 w-96 h-96 bg-purple-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-2000"
        ></div>
        <div
          class="absolute bottom-1/4 left-1/3 w-96 h-96 bg-pink-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-4000"
        ></div>
      </div>

      <div class="relative max-w-4xl mx-auto text-center z-10">
        <!-- 메인 헤드라인 -->
        <h1 class="text-6xl md:text-7xl font-extrabold text-neutral-text mb-6 leading-tight">
          내야 할 세금은 똑똑하게,<br />아낄 돈은 알뜰하게<br />
          <span class="text-primary">'슈킹'</span>하세요.
        </h1>

        <!-- 서브 헤드라인 -->
        <p class="text-xl md:text-2xl text-neutral-text-light mb-12 font-medium leading-relaxed">
          AI 세무 상담사 '슈킹'이 합법적인 절세 전략으로<br />
          당신의 소중한 자산을 지키는 방법을 알려드립니다.
        </p>

        <!-- CTA 버튼 -->
        <Button variant="primary" size="lg" class="text-xl px-12 py-4 shadow-xl hover:shadow-2xl transform hover:scale-105 transition-all" @click="startChat">
          무료로 AI 상담 시작하기
        </Button>

        <!-- 부가 정보 -->
        <p class="mt-6 text-sm text-neutral-text-light">
          회원가입 없이 바로 시작 • 100% 무료
        </p>
      </div>
    </section>

    <!-- Problem & Solution Section -->
    <section class="py-20 px-4 bg-white">
      <div class="max-w-6xl mx-auto">
        <h2 class="text-4xl font-bold text-center text-neutral-text mb-4">
          복잡한 세금, 잘못된 정보... 이제 끝.
        </h2>
        <p class="text-center text-neutral-text-light mb-12">
          슈킹 AI는 이 모든 문제를 해결합니다.
        </p>

        <div class="grid md:grid-cols-3 gap-8">
          <!-- 문제점 1 -->
          <div class="bg-slate-50 rounded-2xl p-8 text-center hover:shadow-lg transition-shadow">
            <div class="text-5xl mb-4">🧩</div>
            <h3 class="text-xl font-bold text-neutral-text mb-3">복잡한 법규</h3>
            <p class="text-neutral-text-light">어려운 용어와 계속 바뀌는 규정들</p>
          </div>

          <!-- 문제점 2 -->
          <div class="bg-slate-50 rounded-2xl p-8 text-center hover:shadow-lg transition-shadow">
            <div class="text-5xl mb-4">💰</div>
            <h3 class="text-xl font-bold text-neutral-text mb-3">높은 비용</h3>
            <p class="text-neutral-text-light">세무사 상담의 높은 문턱</p>
          </div>

          <!-- 문제점 3 -->
          <div class="bg-slate-50 rounded-2xl p-8 text-center hover:shadow-lg transition-shadow">
            <div class="text-5xl mb-4">🔍</div>
            <h3 class="text-xl font-bold text-neutral-text mb-3">부정확한 정보</h3>
            <p class="text-neutral-text-light">신뢰할 수 없는 인터넷 검색 결과</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Features Section -->
    <section ref="featuresSection" class="py-20 px-4 bg-neutral-bg">
      <div class="max-w-6xl mx-auto">
        <h2 class="text-4xl font-bold text-center text-neutral-text mb-4">
          슈킹, 이름은 이래도 실력은 진짜.
        </h2>
        <p class="text-center text-neutral-text-light mb-12">
          세금 절약을 위한 강력한 기능들
        </p>

        <div class="grid md:grid-cols-3 gap-8">
          <!-- 기능 1 -->
          <div class="bg-white rounded-2xl p-8 hover:shadow-xl transition-all transform hover:-translate-y-2">
            <div class="text-5xl mb-4">🤖</div>
            <h3 class="text-xl font-bold text-neutral-text mb-3">24/7 AI 상담</h3>
            <p class="text-neutral-text-light mb-4">
              언제든지 답하는 AI 세무사. 시간과 장소에 구애받지 않고 즉시 답변을 받으세요.
            </p>
          </div>

          <!-- 기능 2 -->
          <div class="bg-white rounded-2xl p-8 hover:shadow-xl transition-all transform hover:-translate-y-2">
            <div class="text-5xl mb-4">📚</div>
            <h3 class="text-xl font-bold text-neutral-text mb-3">정확한 근거 제시</h3>
            <p class="text-neutral-text-light mb-4">
              모든 답변은 최신 법령과 예규를 근거로 합니다. 출처를 함께 확인하세요.
            </p>
          </div>

          <!-- 기능 3 -->
          <div class="bg-white rounded-2xl p-8 hover:shadow-xl transition-all transform hover:-translate-y-2">
            <div class="text-5xl mb-4">💡</div>
            <h3 class="text-xl font-bold text-neutral-text mb-3">맞춤형 추가 질문</h3>
            <p class="text-neutral-text-light mb-4">
              상황에 맞는 추가 질문으로 더 정확한 결과를 제공합니다.
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- How It Works Section -->
    <section class="py-20 px-4 bg-white">
      <div class="max-w-4xl mx-auto">
        <h2 class="text-4xl font-bold text-center text-neutral-text mb-4">
          단 3단계면 충분합니다.
        </h2>
        <p class="text-center text-neutral-text-light mb-12">
          간단하고 빠른 상담 프로세스
        </p>

        <div class="space-y-8">
          <div class="flex items-center gap-6">
            <div
              class="flex-shrink-0 w-16 h-16 bg-primary text-white rounded-full flex items-center justify-center text-2xl font-bold"
            >
              1
            </div>
            <div>
              <h3 class="text-xl font-bold text-neutral-text mb-2">💬 질문하기</h3>
              <p class="text-neutral-text-light">궁금한 점을 편하게 물어보세요.</p>
            </div>
          </div>

          <div class="flex items-center gap-6">
            <div
              class="flex-shrink-0 w-16 h-16 bg-primary text-white rounded-full flex items-center justify-center text-2xl font-bold"
            >
              2
            </div>
            <div>
              <h3 class="text-xl font-bold text-neutral-text mb-2">✅ 정보 확인</h3>
              <p class="text-neutral-text-light">AI의 추가 질문에 답해주세요.</p>
            </div>
          </div>

          <div class="flex items-center gap-6">
            <div
              class="flex-shrink-0 w-16 h-16 bg-primary text-white rounded-full flex items-center justify-center text-2xl font-bold"
            >
              3
            </div>
            <div>
              <h3 class="text-xl font-bold text-neutral-text mb-2">📄 답변 확인</h3>
              <p class="text-neutral-text-light">근거와 함께 상세한 답변을 받으세요.</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Trust Section -->
    <section class="py-20 px-4 bg-neutral-bg">
      <div class="max-w-4xl mx-auto">
        <h2 class="text-4xl font-bold text-center text-neutral-text mb-12">
          슈킹 AI는 신뢰를 최우선으로 생각합니다.
        </h2>

        <!-- 이름의 유래 -->
        <div class="bg-white rounded-2xl p-8 mb-8 shadow-lg">
          <h3 class="text-2xl font-bold text-neutral-text mb-4">
            잠깐, '슈킹'이 무슨 뜻인가요?
          </h3>
          <p class="text-neutral-text-light leading-relaxed">
            '슈킹'은 '돈을 긁어모은다'는 뜻에서 유래한 재미있는 이름입니다. 저희는 당신이 불필요한 세금을 내지 않고,
            합법적으로 아낄 수 있는 돈을 알뜰하게 '슈킹'할 수 있도록 돕겠다는 유쾌한 다짐을 담았습니다.
            <strong>이름은 가벼워도, 답변의 근거는 결코 가볍지 않습니다.</strong>
          </p>
        </div>

        <div class="grid md:grid-cols-2 gap-6">
          <!-- 신뢰 요소 1 -->
          <div class="bg-white rounded-xl p-6">
            <div class="text-4xl mb-3">🏛️</div>
            <h3 class="text-lg font-bold text-neutral-text mb-2">정부 데이터 기반</h3>
            <p class="text-neutral-text-light text-sm">
              국세법령정보시스템 등 공공 데이터를 기반으로 학습합니다.
            </p>
          </div>

          <!-- 신뢰 요소 2 -->
          <div class="bg-white rounded-xl p-6">
            <div class="text-4xl mb-3">🔒</div>
            <h3 class="text-lg font-bold text-neutral-text mb-2">개인정보 보호</h3>
            <p class="text-neutral-text-light text-sm">
              민감 정보는 수집하지 않으며, 모든 대화는 익명으로 처리됩니다.
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- FAQ Section -->
    <section class="py-20 px-4 bg-white">
      <div class="max-w-3xl mx-auto">
        <h2 class="text-4xl font-bold text-center text-neutral-text mb-12">
          자주 묻는 질문
        </h2>

        <div class="space-y-4">
          <div
            v-for="(faq, index) in faqItems"
            :key="index"
            class="border border-neutral-border rounded-lg overflow-hidden"
          >
            <button
              class="w-full px-6 py-4 text-left flex items-center justify-between hover:bg-slate-50 transition-colors"
              @click="toggleFaq(index)"
            >
              <span class="font-medium text-neutral-text">{{ faq.question }}</span>
              <svg
                :class="['w-5 h-5 transform transition-transform', faq.isOpen ? 'rotate-180' : '']"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            <div
              v-show="faq.isOpen"
              class="px-6 py-4 bg-slate-50 text-neutral-text-light"
            >
              {{ faq.answer }}
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Final CTA Section -->
    <section class="py-20 px-4 bg-gradient-to-r from-blue-500 to-purple-600 text-white">
      <div class="max-w-3xl mx-auto text-center">
        <h2 class="text-4xl md:text-5xl font-bold mb-4">
          이제, AI 세무 전문가와 함께하세요.
        </h2>
        <p class="text-xl mb-8 opacity-90">
          복잡한 세금 문제, 슈킹이 명쾌한 첫걸음을 안내합니다.
        </p>
        <Button
          variant="secondary"
          size="lg"
          class="text-xl px-12 py-4 shadow-xl hover:shadow-2xl transform hover:scale-105 transition-all bg-white text-primary hover:bg-gray-50"
          @click="startChat"
        >
          무료로 AI 상담 시작하기
        </Button>
      </div>
    </section>

    <!-- Footer -->
    <footer class="py-8 px-4 bg-neutral-text text-white text-center">
      <p class="text-sm opacity-75">© 2025 슈킹 AI. All rights reserved.</p>
      <p class="text-xs opacity-50 mt-2">
        본 서비스는 정보 제공 목적이며, 법적 효력을 갖지 않습니다.
      </p>
    </footer>
  </div>
</template>

<style scoped>
@keyframes blob {
  0%,
  100% {
    transform: translate(0px, 0px) scale(1);
  }
  33% {
    transform: translate(30px, -50px) scale(1.1);
  }
  66% {
    transform: translate(-20px, 20px) scale(0.9);
  }
}

.animate-blob {
  animation: blob 7s infinite;
}

.animation-delay-2000 {
  animation-delay: 2s;
}

.animation-delay-4000 {
  animation-delay: 4s;
}
</style>

