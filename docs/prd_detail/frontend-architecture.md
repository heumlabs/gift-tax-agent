## 프런트엔드 아키텍처 설계

문서 버전: v2.0
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

Pinia를 사용하여 중앙 집중식으로 상태를 관리합니다. 새로운 디자인 시스템과 동적 사용자 경험을 위해 `chatStore`의 역할이 확장됩니다.

-   **`sessionStore`**:
    -   기존 역할을 유지합니다. (세션 목록 관리, 생성, 수정, 삭제)

-   **`chatStore`**:
    -   **State**:
        -   `messages`: 현재 세션의 전체 메시지 목록.
        -   `isStreaming`: AI 응답이 스트리밍 중인지 여부를 나타내는 boolean 상태.
        -   `streamingMessage`: 현재 스트리밍 중인 메시지 객체. 초기에는 내용(`content`)이 비어있으며, 스트림을 통해 점진적으로 채워집니다.
    -   **Actions**:
        -   `fetchMessages`: 기존 역할 유지.
        -   `sendMessage`:
            1.  사용자 메시지를 `messages` 목록에 즉시 추가 (Optimistic UI).
            2.  AI 응답 스트리밍 API를 호출.
            3.  `isStreaming`을 `true`로 설정하고, 빈 `streamingMessage` 객체를 생성.
            4.  스트림을 통해 데이터 조각(token)이 수신될 때마다 `streamingMessage`의 `content`를 업데이트.
            5.  스트림이 종료되면, `isStreaming`을 `false`로 변경하고 완성된 `streamingMessage`를 `messages` 목록에 추가한 후 `streamingMessage`를 초기화.

### 4. API 통신

-   **라이브러리**: `axios`를 기본으로 사용하되, AI 응답 스트리밍을 위해 `fetch` API 또는 이벤트 소스 라이브러리(`@microsoft/fetch-event-source`)를 활용하여 Server-Sent Events (SSE)를 처리합니다.
-   **API 클라이언트 (`src/services/api.ts`)**:
    -   기존 `axios` 인스턴스는 세션 관리 등 일반적인 REST API 호출에 사용됩니다.
    -   스트리밍 요청을 위한 별도의 함수(`streamChatResponse`)를 구현합니다. 이 함수는 SSE 연결을 수립하고, 수신되는 데이터 이벤트를 처리하여 `chatStore`의 액션을 호출하는 역할을 합니다.

### 5. 라우팅 (Vue Router)

-   `'/'`: 메인 채팅 페이지. `currentSessionId`가 없다면 새 세션을 생성하도록 유도하거나, 마지막 세션으로 리디렉션합니다.
-   `'/s/:sessionId'`: 특정 세션 ID에 해당하는 채팅 페이지. 페이지 진입 시 해당 세션의 메시지를 불러옵니다.

### 6. 핵심 컴포넌트 설계

새로운 디자인 가이드와 동적 경험을 위해 컴포넌트의 역할과 구현 방식이 다음과 같이 변경됩니다.

-   **`ChatView.vue`**:
    -   메인 레이아웃과 반응형 처리를 담당하는 기존 역할은 유지됩니다.
    -   다크 모드를 기본 테마로 적용하기 위해 최상위 컨테이너에 관련 스타일을 적용합니다.

-   **`SessionList.vue`**:
    -   다크 모드 디자인 가이드에 맞춰 스타일을 업데이트합니다.

-   **`ChatWindow.vue`**:
    -   `chatStore`의 `isStreaming`과 `streamingMessage` 상태를 구독합니다.
    -   `messages` 목록을 렌더링하고, `isStreaming`이 `true`일 경우, `streamingMessage`를 별도의 `ChatBubble` 컴포넌트로 렌더링하여 실시간 업데이트를 표시합니다.
    -   AI 응답 대기 중일 때, 기존 `LoadingIndicator` 대신 새로운 `TypingIndicator`를 표시하여 AI가 응답을 생성 중임을 시각적으로 전달합니다.

-   **`MessageInput.vue`**:
    -   새로운 미니멀리즘 디자인을 적용합니다.
    -   `isStreaming` 상태일 때는 입력창을 비활성화하여 중복 요청을 방지합니다.

-   **`ChatBubble.vue`**:
    -   **Props**: `isStreaming: boolean` prop을 추가로 받아, 일반 메시지와 스트리밍 중인 메시지를 구분합니다.
    -   **로직**: `isStreaming`이 `true`이고 `message.content`가 변경될 때마다, 타이핑 효과 애니메이션을 트리거합니다.
    -   **페이드인 꼬리 효과 구현**: 메시지 텍스트를 개별 `<span>` 요소로 분리하고, 마지막 3-5개 글자에 동적으로 투명도를 적용합니다. 새 글자가 추가될 때마다 이전 글자들의 투명도를 GSAP로 애니메이션하여 자연스럽게 증가시킵니다.

-   **`TypingIndicator.vue` (신규 또는 `LoadingIndicator.vue` 수정)**:
    -   AI가 응답을 준비하고 있음을 나타내는 깜빡이는 커서(Caret) 형태의 애니메이션을 구현합니다.
    -   `ChatWindow` 내에서 AI 응답이 시작되기 전에 표시됩니다.

### 7. 빌드 및 배포

-   **개발 서버 및 빌드**: Vite를 사용하여 빠른 개발 서버와 최적화된 프로덕션 빌드를 수행합니다.
-   **배포**:
    -   GitHub Actions를 통해 CI/CD 파이프라인을 구축합니다.
    -   `main` 브랜치에 코드가 머지되면 자동으로 빌드하여 정적 파일을 생성합니다.
    -   빌드된 결과물은 AWS S3에 업로드하고 CloudFront를 통해 사용자에게 제공하여 빠른 전송 속도를 보장합니다.

### 8. 사용자 경험(UX) 개선 사항

-   **실시간 스트리밍 UI**: AI의 응답을 기다리는 동안 사용자가 지루함을 느끼지 않도록, 생성되는 과정을 실시간으로 보여줍니다. 이는 시스템이 작동하고 있다는 즉각적인 피드백을 제공하며 사용자 경험을 크게 향상시킵니다.
-   **무한 스크롤**: 기존 UX 개선 사항을 유지하여, 긴 대화 기록도 효율적으로 탐색할 수 있도록 합니다.
-   **상태에 따른 명확한 피드백**: 메시지 전송 중, AI 응답 스트리밍 중, 에러 발생 등 각 상태에 대한 명확한 시각적 피드백(입력창 비활성화, 인디케이터 표시 등)을 제공합니다.
