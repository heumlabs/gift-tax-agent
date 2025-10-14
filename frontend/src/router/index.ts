/**
 * Vue Router 설정
 */

import { createRouter, createWebHistory } from 'vue-router';

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'landing',
      component: () => import('@/views/LandingView.vue'),
    },
    {
      path: '/chat',
      name: 'chat',
      component: () => import('@/views/ChatView.vue'),
      children: [
        {
          path: ':sessionId',
          name: 'chat-session',
          component: () => import('@/views/ChatView.vue'),
        },
      ],
    },
  ],
});

export default router;

