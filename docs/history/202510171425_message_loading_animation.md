# 작업 이력: 202510171425_message_loading_animation

## 작업 요약
API 호출 후 응답을 받기 전까지 표시되는 메시지 로딩 애니메이션을 구현했습니다. AI 메시지 버블 형태로 3개의 점이 순차적으로 펄스하는 애니메이션을 추가하여 사용자에게 시스템이 응답을 처리 중임을 시각적으로 전달합니다.

## 변경 사항

### 1. 새로운 컴포넌트 생성
- **파일**: `frontend/src/components/TypingIndicator.vue`
- AI 메시지 버블 형태의 로딩 인디케이터 컴포넌트 생성
- 3개의 점이 순차적으로 페이드인/아웃하며 스케일 변화하는 애니메이션
- GSAP 라이브러리를 활용한 부드러운 애니메이션 효과
- 컨테이너 페이드인 효과로 자연스러운 등장
- 모바일에서는 AI 아이콘 숨김 처리

### 2. ChatWindow.vue 수정
- **파일**: `frontend/src/components/ChatWindow.vue`
- `TypingIndicator` 컴포넌트 import 추가
- 템플릿 조건문 수정:
  - `v-else-if` 조건에 `chatStore.isLoadingResponse` 추가하여 로딩 중에도 메시지 영역 표시
  - `TypingIndicator`를 `isLoadingResponse && !streamingMessage` 조건으로 표시
  - API 응답 대기 중에는 TypingIndicator, 응답 수신 후에는 ChatBubble의 타이핑 애니메이션 표시

### 3. chat.ts 스토어 로직 수정
- **파일**: `frontend/src/store/chat.ts`
- 스트리밍 시작 시점 변경:
  - 기존: API 호출 전에 `startStreaming()` 호출
  - 변경: API 응답 수신 후 첫 번째 청크를 받을 때 `startStreaming()` 호출
- `isLoadingResponse` 상태 관리 개선:
  - API 호출 시작 시 `true` 설정
  - 첫 번째 청크 수신 시 `false`로 변경하여 로딩에서 타이핑 애니메이션으로 전환

## 영향 범위

### 컴포넌트
- **새로 추가**: `TypingIndicator.vue`
- **수정**: `ChatWindow.vue` - 로딩 상태 표시 로직

### 스토어
- **수정**: `chat.ts` - 메시지 전송 및 스트리밍 시작 타이밍

### UX 개선
- 사용자가 메시지 전송 후 시스템 응답을 기다리는 동안 시각적 피드백 제공
- API 응답 대기 중 (TypingIndicator) → 타이핑 애니메이션 (ChatBubble) 자연스러운 전환

## 동작 흐름

1. **사용자 메시지 전송**
   - `isLoadingResponse = true`
   - 사용자 메시지 즉시 화면에 표시 (Optimistic UI)

2. **API 요청 → 응답 대기 (1~3초)**
   - `TypingIndicator` 컴포넌트 표시
   - 3개의 점이 순차적으로 펄스하는 애니메이션

3. **API 응답 수신**
   - 첫 번째 타이핑 청크 수신 시:
     - `startStreaming()` 호출
     - `isLoadingResponse = false`
     - `streamingMessage` 생성

4. **타이핑 애니메이션**
   - `TypingIndicator` 사라짐
   - `ChatBubble`의 스트리밍 모드로 타이핑 효과 표시
   - 페이드인 꼬리 효과로 자연스러운 타이핑 느낌

## 기술적 세부사항

### TypingIndicator 애니메이션
```javascript
// 각 점마다 0.2초씩 지연하여 순차적 애니메이션
gsap.to(dot, {
  opacity: 0.3,
  scale: 0.8,
  duration: 0.6,
  repeat: -1,        // 무한 반복
  yoyo: true,        // 왕복 애니메이션
  ease: 'power1.inOut',
  delay: index * 0.2,
});
```

### 조건부 렌더링 로직
```vue
<!-- API 응답 대기 중 -->
<TypingIndicator v-if="chatStore.isLoadingResponse && !chatStore.streamingMessage" />

<!-- 타이핑 애니메이션 중 -->
<ChatBubble
  v-else-if="chatStore.streamingMessage"
  :is-streaming="true"
/>
```

## 테스트

### 수행한 테스트 케이스
1. ✅ 첫 메시지 전송 시 TypingIndicator 표시 확인
2. ✅ API 응답 수신 후 TypingIndicator → ChatBubble 전환 확인
3. ✅ 연속 메시지 전송 시 애니메이션 정상 동작 확인
4. ✅ 모바일 반응형 레이아웃 확인 (AI 아이콘 숨김)

### 확인사항
- TypingIndicator가 AI 메시지 버블과 동일한 스타일로 표시됨
- 애니메이션이 부드럽게 동작하며 성능 이슈 없음
- 로딩 상태와 스트리밍 상태 간 전환이 자연스러움
- 스크롤이 자동으로 하단으로 이동하여 항상 최신 상태 표시

## 기타

### 디자인 일관성
- `ChatBubble`과 동일한 스타일 적용:
  - `bg-neutral-card`, `rounded-2xl`, `rounded-bl-sm`
  - AI 아이콘 크기 및 위치
  - 시간 표시 형식 및 위치

### 성능 최적화
- GSAP 애니메이션 사용으로 GPU 가속 활용
- 컴포넌트 언마운트 시 자동으로 애니메이션 정리

### 추후 개선 가능 사항
- 네트워크 지연이 길 경우 추가 메시지 표시 (예: "잠시만 기다려주세요...")
- 로딩 애니메이션 스타일 커스터마이징 옵션 추가
- 에러 발생 시 TypingIndicator를 에러 메시지로 전환하는 기능

