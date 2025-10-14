/**
 * 환경변수 관리
 */

export const env = {
  // API 서버 URL
  apiUrl: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  
  // Mock 모드 활성화 여부
  useMock: import.meta.env.VITE_USE_MOCK === 'true',
};

