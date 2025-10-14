# 슈킹 (Syuking) - 증여세/상속세 AI 상담 서비스

증여세와 상속세에 대한 AI 기반 상담 서비스입니다.

## 📋 목차

- [프로젝트 개요](#프로젝트-개요)
- [기술 스택](#기술-스택)
- [시작하기](#시작하기)
  - [사전 요구사항](#사전-요구사항)
  - [설치 및 실행](#설치-및-실행)
- [프로젝트 구조](#프로젝트-구조)
- [개발 가이드](#개발-가이드)

## 🎯 프로젝트 개요

슈킹은 복잡한 증여세/상속세 규정을 AI를 활용하여 쉽게 이해하고 계산할 수 있도록 돕는 상담형 서비스입니다.

주요 기능:
- 💬 대화형 AI 상담
- 📊 증여세/상속세 계산
- 📚 법령 및 예규 인용
- 💾 세션 관리 및 이력 저장

## 🛠 기술 스택

### Backend
- **Framework**: AWS Chalice (Python)
- **Database**: PostgreSQL (pgvector 확장 포함)
- **AI**: Google Gemini 1.5 Pro
- **ORM**: SQLAlchemy + SQLModel

### Frontend
- **Framework**: Vue 3
- **Build Tool**: Vite
- **Language**: TypeScript
- **Styling**: Tailwind CSS 3 (예정)
- **Animation**: GSAP (예정)

## 🚀 시작하기

### 사전 요구사항

- Python 3.9 이상
- Node.js 18 이상
- PostgreSQL 14 이상
- Google Gemini API Key

### 설치 및 실행

#### 1. 저장소 클론

```bash
git clone <repository-url>
cd gift-tax-agent
```

#### 2. 백엔드 설정

```bash
# 백엔드 디렉토리로 이동
cd backend

# Python 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일을 편집하여 실제 값으로 변경하세요:
# - DATABASE_URL: PostgreSQL 연결 정보
# - GEMINI_API_KEY: Google Gemini API 키
```

#### 3. 백엔드 실행

```bash
# Chalice 로컬 서버 실행 (포트 8000)
chalice local --port 8000
```

백엔드가 `http://localhost:8000`에서 실행됩니다.

#### 4. 프론트엔드 설정

새 터미널 창을 열고:

```bash
# 프론트엔드 디렉토리로 이동
cd frontend

# 의존성 설치
npm install

# 환경 변수 설정
cp .env.example .env
# .env 파일을 편집하여 백엔드 URL을 설정하세요
```

#### 5. 프론트엔드 실행

```bash
# Vite 개발 서버 실행 (포트 5173)
npm run dev
```

프론트엔드가 `http://localhost:5173`에서 실행됩니다.

### ✅ 동작 확인

1. 백엔드 헬스 체크:
   ```bash
   curl http://localhost:8000/health
   ```

2. CORS 테스트:
   ```bash
   curl http://localhost:8000/api/test
   ```

3. 브라우저에서 `http://localhost:5173` 접속

## 📁 프로젝트 구조

```
gift-tax-agent/
├── backend/                 # 백엔드 (Chalice)
│   ├── .chalice/           # Chalice 설정
│   │   └── config.json     # 환경별 설정
│   ├── app.py              # 메인 애플리케이션
│   ├── requirements.txt    # Python 의존성
│   └── .env.example        # 환경 변수 템플릿
├── frontend/               # 프론트엔드 (Vue 3)
│   ├── src/               # 소스 코드
│   │   ├── App.vue        # 메인 컴포넌트
│   │   ├── main.ts        # 엔트리 포인트
│   │   └── components/    # Vue 컴포넌트
│   ├── package.json       # Node 의존성
│   └── .env.example       # 환경 변수 템플릿
└── docs/                  # 문서
    ├── PRD.md             # 제품 요구사항 명세
    └── idea.md            # 아이디어 노트
```

## 💻 개발 가이드

### 백엔드 개발

1. **새로운 API 엔드포인트 추가**:
   ```python
   @app.route('/api/endpoint', methods=['POST'], cors=cors_config)
   def new_endpoint():
       return {'data': 'value'}
   ```

2. **환경 변수 사용**:
   ```python
   import os
   value = os.getenv('VARIABLE_NAME')
   ```

### 프론트엔드 개발

1. **개발 서버**: `npm run dev`
2. **프로덕션 빌드**: `npm run build`
3. **프리뷰**: `npm run preview`

### 데이터베이스 설정

PostgreSQL 데이터베이스 생성:

```sql
CREATE DATABASE syuking_db;
CREATE USER syuking_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE syuking_db TO syuking_user;

-- pgvector 확장 설치 (벡터 검색용)
CREATE EXTENSION vector;
```

## 📝 환경 변수

### Backend (.env)

```env
DATABASE_URL=postgresql://username:password@localhost:5432/syuking_db
GEMINI_API_KEY=your_gemini_api_key_here
ENVIRONMENT=dev
CORS_ALLOW_ORIGIN=http://localhost:5173
```

### Frontend (.env)

```env
VITE_API_URL=http://localhost:8000
VITE_APP_ENV=development
```

## 🔧 문제 해결

### 백엔드가 실행되지 않는 경우

1. Python 가상환경이 활성화되어 있는지 확인
2. 모든 의존성이 설치되었는지 확인: `pip install -r requirements.txt`
3. .env 파일이 올바르게 설정되었는지 확인

### 프론트엔드가 실행되지 않는 경우

1. Node.js 버전 확인: `node --version` (18 이상 필요)
2. 의존성 재설치: `rm -rf node_modules && npm install`
3. .env 파일이 올바르게 설정되었는지 확인

### CORS 오류가 발생하는 경우

1. 백엔드 .env의 `CORS_ALLOW_ORIGIN`이 프론트엔드 URL과 일치하는지 확인
2. 백엔드를 재시작하여 환경 변수를 다시 로드

## 📚 참고 문서

- [Chalice Documentation](https://aws.github.io/chalice/)
- [Vue 3 Documentation](https://vuejs.org/)
- [Vite Documentation](https://vitejs.dev/)
- [PRD (Product Requirements Document)](./docs/PRD.md)

## 📄 라이선스

이 프로젝트는 개인 프로젝트입니다.

## 👥 기여

현재 개인 프로젝트로 진행 중입니다.
