## 프런트엔드 아키텍처 설계

문서 버전: v1.0  
연관 문서: `docs/PRD.md`, `docs/design-guide.md`

### 1. 개요

Vue 3의 Composition API를 적극적으로 활용하여 반응적이고 유지보수하기 쉬운 애플리케이션을 구축합니다.

- **프레임워크**: Vue 3
- **빌드 도구**: Vite
- **언어**: TypeScript
- **상태 관리**: Pinia
- **UI 스타일링**: Tailwind CSS 3
- **애니메이션**: GSAP

### 2. 프로젝트 구조

컴포넌트, 상태, 서비스 등 기능별로 모듈을 명확하게 분리합니다.

```
/src
├── assets/         # 정적 에셋 (이미지, 폰트)
├── components/     # 재사용 가능한 UI 컴포넌트 (e.g., ChatBubble.vue)
│   └── common/     # 앱 전역에서 사용되는 기본 컴포넌트 (e.g., Button.vue)
├── views/          # 페이지 레벨의 컴포넌트 (e.g., ChatView.vue)
├── composables/    # 재사용 가능한 Composition API 함수 (e.g., useApiClient.ts)
├── router/         # Vue Router 설정
├── services/       # 외부 서비스 연동 (API 클라이언트, 로컬 스토리지 관리)
├── store/          # Pinia 스토어 (상태 관리)
├── styles/         # 전역 CSS, Tailwind 설정
├── types/          # TypeScript 타입 정의
└── main.ts         # 애플리케이션 진입점
```

### 3. 상태 관리 (Pinia)

Pinia를 사용하여 중앙 집중식으로 상태를 관리합니다.

-   **`sessionStore`**:
    -   **State**: `sessions` (세션 목록), `currentSessionId`, `isLoading`
    -   **Actions**: `fetchSessions`, `createSession`, `updateSessionTitle`, `deleteSession`
    -   세션 관련 API 호출과 상태 변경을 담당합니다.

-   **`chatStore`**:
    -   **State**: `messages` (현재 세션의 메시지 목록), `isLoadingResponse` (AI 응답 대기 여부)
    -   **Actions**: `fetchMessages`, `sendMessage`
    -   특정 세션의 메시지를 관리하고, 새 메시지 전송 및 응답 수신을 처리합니다.

### 4. API 통신

-   **라이브러리**: `axios`를 사용하여 API 클라이언트를 구현합니다.
-   **API 클라이언트 (`src/services/api.ts`)**:
    -   `axios` 인스턴스를 생성하고 기본 URL(`baseURL`)을 설정합니다.
    -   요청 인터셉터(interceptor)를 사용하여 모든 요청 헤더에 `x-client-id`를 자동으로 추가합니다.
-   **클라이언트 ID 관리 (`src/services/clientId.ts`)**:
    -   애플리케이션 최초 실행 시 UUID를 생성하여 `localStorage`에 저장합니다.
    -   이후 모든 세션에서 동일한 ID를 사용하여 사용자를 식별합니다.

### 5. 라우팅 (Vue Router)

-   `'/'`: 메인 채팅 페이지. `currentSessionId`가 없다면 새 세션을 생성하도록 유도하거나, 마지막 세션으로 리디렉션합니다.
-   `'/s/:sessionId'`: 특정 세션 ID에 해당하는 채팅 페이지. 페이지 진입 시 해당 세션의 메시지를 불러옵니다.

### 6. 핵심 컴포넌트 설계

-   **`ChatView.vue`**:
    -   메인 레이아웃을 담당합니다.
    -   `SessionList`와 `ChatWindow` 컴포넌트를 자식으로 가집니다.
    -   화면 크기에 따라 `SessionList`의 가시성을 제어합니다 (모바일에서는 토글 방식).

-   **`SessionList.vue`**:
    -   `sessionStore`의 세션 목록을 구독하여 화면에 렌더링합니다.
    -   '새 상담' 버튼과 각 세션 항목(클릭, 이름 변경, 삭제)에 대한 이벤트를 처리합니다.

-   **`ChatWindow.vue`**:
    -   `chatStore`의 메시지 목록을 구독하여 `ChatBubble` 컴포넌트로 렌더링합니다.
    -   `MessageInput` 컴포넌트를 포함하며, 메시지 전송 이벤트를 처리합니다.
    -   `isLoadingResponse` 상태에 따라 `LoadingIndicator`를 표시합니다.

-   **`MessageInput.vue`**:
    -   `textarea`와 전송 버튼으로 구성됩니다.
    -   `Shift+Enter` (줄바꿈), `Enter` (전송) 입력을 처리합니다.
    -   입력 내용이 변경될 때마다 `textarea`의 높이를 자동으로 조절합니다.

-   **`LoadingIndicator.vue`**:
    -   GSAP를 사용하여 미려한 로딩 애니메이션을 구현합니다. (PRD 요구사항: 최소 400ms 노출)

### 7. 빌드 및 배포

-   **개발 서버 및 빌드**: Vite를 사용하여 빠른 개발 서버와 최적화된 프로덕션 빌드를 수행합니다.
-   **배포**:
    -   GitHub Actions를 통해 CI/CD 파이프라인을 구축합니다.
    -   `main` 브랜치에 코드가 머지되면 자동으로 빌드하여 정적 파일을 생성합니다.
    -   빌드된 결과물은 AWS S3에 업로드하고 CloudFront를 통해 사용자에게 제공하여 빠른 전송 속도를 보장합니다.

### 8. 사용자 경험(UX) 개선 사항

-   **Optimistic UI**: 메시지 전송 시, 서버 응답을 기다리지 않고 우선 사용자 메시지를 UI에 즉시 표시하여 체감 속도를 높입니다. 실패 시 에러 상태를 표시합니다.
-   **무한 스크롤**: 스크롤을 위로 올리면 이전 메시지를 불러오는 무한 스크롤을 구현하여 초기 로딩 속도를 개선합니다.
