/**
 * API 클라이언트 설정
 * Axios 인스턴스 생성 및 인터셉터 설정
 */

import axios, { type AxiosInstance } from 'axios';
import { env } from '@/config/env';
import { getClientId } from '@/services/clientId';

/**
 * Axios 인스턴스 생성
 */
export const apiClient: AxiosInstance = axios.create({
  baseURL: env.apiUrl,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * 요청 인터셉터: 모든 요청에 x-client-id 헤더 추가
 */
apiClient.interceptors.request.use(
  (config) => {
    const clientId = getClientId();
    if (clientId) {
      config.headers['x-client-id'] = clientId;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

/**
 * 응답 인터셉터: 에러 처리
 */
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // API 에러 응답 처리
    if (error.response) {
      console.error('API Error:', error.response.data);
    } else if (error.request) {
      console.error('Network Error:', error.request);
    } else {
      console.error('Error:', error.message);
    }
    return Promise.reject(error);
  }
);

