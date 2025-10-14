/**
 * Client ID 관리 서비스
 * localStorage를 사용하여 사용자 식별용 UUID 관리
 */

const CLIENT_ID_KEY = 'gift-tax-client-id';

/**
 * UUID v4 생성
 */
function generateUUID(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * Client ID 가져오기
 * localStorage에 없으면 새로 생성하여 저장
 */
export function getClientId(): string {
  let clientId = localStorage.getItem(CLIENT_ID_KEY);

  if (!clientId) {
    clientId = generateUUID();
    localStorage.setItem(CLIENT_ID_KEY, clientId);
  }

  return clientId;
}

/**
 * Client ID 초기화 (테스트용)
 */
export function resetClientId(): void {
  localStorage.removeItem(CLIENT_ID_KEY);
}

