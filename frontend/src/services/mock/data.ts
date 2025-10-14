/**
 * Mock 데이터
 * 실제 API 응답 형식과 동일하게 구성
 */

import type { Session, Message } from '@/types';

// ============================================================================
// Mock 세션 데이터
// ============================================================================

export const mockSessions: Session[] = [
  {
    id: 'session-1',
    title: '배우자 증여세 문의',
    createdAt: '2025-10-14T09:00:00Z',
  },
  {
    id: 'session-2',
    title: '자녀 증여세 계산',
    createdAt: '2025-10-13T14:30:00Z',
  },
  {
    id: 'session-3',
    title: '상속세 관련 질문',
    createdAt: '2025-10-12T11:15:00Z',
  },
];

// ============================================================================
// Mock 메시지 데이터
// ============================================================================

export const mockMessages: Record<string, Message[]> = {
  'session-1': [
    {
      id: 'msg-1-1',
      role: 'user',
      content: '배우자에게 1억원을 증여하려고 하는데 세금이 얼마나 나올까요?',
      createdAt: '2025-10-14T09:00:10Z',
    },
    {
      id: 'msg-1-2',
      role: 'assistant',
      content:
        '배우자로부터 증여받는 경우, 10년간 6억원까지 증여재산 공제가 적용되어 납부할 세액은 일반적으로 없습니다.\n\n배우자 간 증여의 경우 상속세및증여세법 제53조에 따라 10년간 6억원까지 공제가 적용됩니다. 따라서 1억원을 증여받으시는 경우, 공제 한도 내이므로 증여세가 발생하지 않습니다.\n\n다만, 최근 10년 이내에 배우자로부터 다른 증여를 받으신 적이 있다면 그 금액과 합산하여 공제 한도를 계산하게 됩니다.',
      metadata: {
        citations: [
          {
            text: '상속세및증여세법 제53조 (증여재산공제)',
            url: 'https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=235435#0000',
          },
        ],
        calculation: {
          assumptions: [
            '거주자 간 증여',
            '최근 10년 이내 배우자로부터의 증여 없음',
          ],
          taxableAmount: 100000000,
          deduction: 600000000,
          finalTax: 0,
        },
      },
      createdAt: '2025-10-14T09:00:15Z',
    },
    {
      id: 'msg-1-3',
      role: 'user',
      content: '그럼 5년 전에 3억원을 증여받았다면 어떻게 되나요?',
      createdAt: '2025-10-14T09:01:00Z',
    },
    {
      id: 'msg-1-4',
      role: 'assistant',
      content:
        '5년 전에 3억원을 증여받으셨다면, 이번 1억원과 합산하여 총 4억원이 되며, 여전히 6억원 공제 한도 내이므로 증여세가 발생하지 않습니다.\n\n증여재산공제는 10년간 누적하여 적용되므로, 5년 전 3억원 + 이번 1억원 = 총 4억원이 되며, 6억원 공제 한도에서 차감하면 과세표준이 0원이 됩니다.\n\n따라서 이번 증여에 대해서도 증여세가 발생하지 않습니다. 다만, 향후 5년 이내에 추가로 2억원을 초과하여 증여받으시게 되면 그때부터는 증여세가 발생하게 됩니다.',
      metadata: {
        citations: [
          {
            text: '상속세및증여세법 제53조 (증여재산공제)',
            url: 'https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=235435#0000',
          },
        ],
        calculation: {
          assumptions: [
            '거주자 간 증여',
            '5년 전 배우자로부터 3억원 증여받음',
          ],
          taxableAmount: 400000000,
          deduction: 600000000,
          finalTax: 0,
        },
      },
      createdAt: '2025-10-14T09:01:08Z',
    },
  ],
  'session-2': [
    {
      id: 'msg-2-1',
      role: 'user',
      content: '성인 자녀에게 5천만원을 증여하려고 합니다.',
      createdAt: '2025-10-13T14:30:10Z',
    },
    {
      id: 'msg-2-2',
      role: 'assistant',
      content:
        '성인 자녀에게 5천만원을 증여하시는 경우, 증여재산공제 5천만원을 적용하면 과세표준이 0원이 되어 증여세가 발생하지 않습니다.\n\n성인 자녀(만 19세 이상)의 경우 10년간 5천만원까지 증여재산공제가 적용됩니다(상속세및증여세법 제53조). 따라서 5천만원을 증여하시면 공제 한도와 정확히 일치하여 세금이 없습니다.\n\n만약 추가로 증여를 고려하신다면, 10년 후에 다시 5천만원 공제를 받으실 수 있습니다.',
      metadata: {
        citations: [
          {
            text: '상속세및증여세법 제53조 (증여재산공제)',
            url: 'https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=235435#0000',
          },
        ],
        calculation: {
          assumptions: [
            '직계비속(성인 자녀)에게 증여',
            '최근 10년 이내 동일인에 대한 증여 없음',
          ],
          taxableAmount: 50000000,
          deduction: 50000000,
          finalTax: 0,
        },
      },
      createdAt: '2025-10-13T14:30:18Z',
    },
  ],
  'session-3': [
    {
      id: 'msg-3-1',
      role: 'user',
      content: '상속세 기본 공제가 어떻게 되나요?',
      createdAt: '2025-10-12T11:15:10Z',
    },
    {
      id: 'msg-3-2',
      role: 'assistant',
      content:
        '상속세의 기본공제는 2억원이며, 배우자가 있는 경우 배우자공제(최소 5억원)가 추가로 적용됩니다.\n\n상속세및증여세법 제18조에 따라 기본공제 2억원이 적용되며, 배우자 상속공제는 실제 상속받은 금액과 5억원 중 큰 금액으로 적용됩니다(최대 30억원).\n\n예를 들어, 배우자가 있고 상속재산이 10억원인 경우:\n- 기본공제: 2억원\n- 배우자공제: 최소 5억원\n- 합계: 최소 7억원 공제\n\n따라서 과세표준은 3억원이 되며, 이에 대한 세율을 적용하여 상속세를 계산하게 됩니다.',
      metadata: {
        citations: [
          {
            text: '상속세및증여세법 제18조 (상속공제)',
            url: 'https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=235435#0000',
          },
          {
            text: '상속세및증여세법 제19조 (배우자 상속공제)',
            url: 'https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=235435#0000',
          },
        ],
      },
      createdAt: '2025-10-12T11:15:20Z',
    },
  ],
};

// ============================================================================
// Mock 데이터 헬퍼 함수
// ============================================================================

/**
 * 세션 ID로 메시지 목록 조회
 */
export function getMockMessagesBySessionId(sessionId: string): Message[] {
  return mockMessages[sessionId] || [];
}

/**
 * 새 세션 생성
 */
let sessionCounter = mockSessions.length;
export function createMockSession(): Session {
  sessionCounter++;
  return {
    id: `session-${sessionCounter}`,
    title: '새로운 상담',
    createdAt: new Date().toISOString(),
  };
}

/**
 * 메시지 추가 (Mock AI 응답 포함)
 */
let messageCounter = 100;
export function addMockMessage(
  sessionId: string,
  userMessage: string
): Message {
  messageCounter++;

  const userMsg: Message = {
    id: `msg-${messageCounter}`,
    role: 'user',
    content: userMessage,
    createdAt: new Date().toISOString(),
  };

  // 세션의 메시지 배열이 없으면 생성
  if (!mockMessages[sessionId]) {
    mockMessages[sessionId] = [];
  }

  mockMessages[sessionId].push(userMsg);

  // AI 응답 생성 (간단한 Mock)
  messageCounter++;
  const aiMsg: Message = {
    id: `msg-${messageCounter}`,
    role: 'assistant',
    content: `질문 "${userMessage}"에 대한 답변입니다. (Mock 응답)\n\n현재는 Mock 모드로 동작하고 있습니다. 실제 AI 응답을 받으시려면 환경변수 VITE_USE_MOCK을 false로 설정해주세요.`,
    metadata: {
      citations: [
        {
          text: 'Mock 법령 참조',
          url: 'https://example.com',
        },
      ],
    },
    createdAt: new Date().toISOString(),
  };

  mockMessages[sessionId].push(aiMsg);

  return aiMsg;
}

