# 🚀 빠른 시작 가이드

이 문서는 슈킹 프로젝트를 로컬에서 빠르게 실행하기 위한 단계별 가이드입니다.

## ⚡ 빠른 실행 (요약)

```bash
# 1. 백엔드 설정 및 실행
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# .env 파일을 편집하여 설정 변경
./run_local.sh  # 또는: chalice local --port 8000

# 2. 새 터미널에서 프론트엔드 설정 및 실행
cd frontend
npm install
cp .env.example .env
# .env 파일을 편집하여 설정 변경
./run_dev.sh  # 또는: npm run dev
```

## 📝 상세 가이드

### 1단계: 백엔드 설정

#### 1.1 Python 가상환경 생성

```bash
cd backend
python -m venv venv
```

#### 1.2 가상환경 활성화

**macOS/Linux:**
```bash
source venv/bin/activate
```

**Windows (PowerShell):**
```powershell
venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
venv\Scripts\activate.bat
```

#### 1.3 Python 패키지 설치

```bash
pip install -r requirements.txt
```

설치되는 주요 패키지:
- `chalice`: AWS Chalice 프레임워크
- `google-generativeai`: Google Gemini AI 연동
- `psycopg2-binary`: PostgreSQL 드라이버
- `SQLAlchemy`: ORM 기반
- `sqlmodel`: SQLAlchemy 위에서 모델 정의를 단순화
- `pgvector`: 벡터 연산 및 임베딩 저장
- `python-dotenv`: 환경 변수 관리

#### 1.4 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 편집하여 실제 값으로 변경:

```env
# 데이터베이스 설정 (로컬 개발 시)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/shuking

# Google Gemini API 키 (필수)
GEMINI_API_KEY=your_actual_gemini_api_key_here

# 환경 설정
ENVIRONMENT=dev

# CORS 설정 (프론트엔드 URL)
CORS_ALLOW_ORIGIN=http://localhost:5173
```

**🔑 Google Gemini API 키 발급 방법:**
1. [Google AI Studio](https://makersuite.google.com/app/apikey) 접속
2. "Get API key" 클릭
3. 새 프로젝트 생성 또는 기존 프로젝트 선택
4. API 키 복사하여 `.env` 파일에 붙여넣기

#### 1.5 데이터베이스 설정 (선택사항)

로컬 PostgreSQL이 설치되어 있다면:

```sql
-- PostgreSQL에 접속하여 실행
CREATE DATABASE shuking;
CREATE USER shuking WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE shuking TO shuking;

-- pgvector 확장 설치 (벡터 검색용)
\c shuking
CREATE EXTENSION vector;
```

> **참고**: 현재는 데이터베이스 없이도 기본 API 테스트가 가능합니다.

#### 1.6 백엔드 실행

**방법 1: 실행 스크립트 사용 (권장)**
```bash
./run_local.sh
```

**방법 2: 직접 실행**
```bash
chalice local --port 8000
```

백엔드가 `http://localhost:8000`에서 실행됩니다.

#### 1.7 백엔드 동작 확인

새 터미널을 열고:

```bash
# 헬스 체크
curl http://localhost:8000/health

# 테스트 API
curl http://localhost:8000/api/test
```

예상 응답:
```json
{
  "status": "healthy",
  "environment": "dev"
}
```

### 2단계: 프론트엔드 설정

#### 2.1 새 터미널 열기

백엔드는 계속 실행 중인 상태로 두고 **새 터미널 창**을 엽니다.

#### 2.2 프론트엔드 디렉토리로 이동

```bash
cd frontend
```

#### 2.3 Node.js 패키지 설치

```bash
npm install
```

설치되는 주요 패키지:
- `vue`: Vue 3 프레임워크
- `vite`: 빌드 도구
- `typescript`: TypeScript 지원

#### 2.4 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일 확인 (기본값으로도 동작):

```env
# 백엔드 API URL
VITE_API_URL=http://localhost:8000

# 애플리케이션 환경
VITE_APP_ENV=development
```

#### 2.5 프론트엔드 실행

**방법 1: 실행 스크립트 사용 (권장)**
```bash
./run_dev.sh
```

**방법 2: 직접 실행**
```bash
npm run dev
```

프론트엔드가 `http://localhost:5173`에서 실행됩니다.

#### 2.6 브라우저에서 확인

브라우저를 열고 `http://localhost:5173`에 접속합니다.

### 3단계: 전체 시스템 테스트

1. **백엔드 확인**: 
   - `http://localhost:8000/health` 접속
   - 또는 터미널에서: `curl http://localhost:8000/health`

2. **프론트엔드 확인**: 
   - `http://localhost:5173` 접속
   - Vue 앱이 정상적으로 로드되는지 확인

3. **CORS 테스트**:
   - 프론트엔드에서 백엔드 API 호출 테스트

## 🐛 문제 해결

### 백엔드 관련

**문제: `chalice: command not found`**
```bash
# 가상환경이 활성화되었는지 확인
which python
# /path/to/backend/venv/bin/python 이 출력되어야 함

# 가상환경 재활성화
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows
```

**문제: `ModuleNotFoundError`**
```bash
# 의존성 재설치
pip install -r requirements.txt
```

**문제: 포트 8000이 이미 사용 중**
```bash
# 다른 포트로 실행
chalice local --port 8001

# 또는 프로세스 종료
lsof -ti:8000 | xargs kill -9  # macOS/Linux
```

### 프론트엔드 관련

**문제: `node: command not found`**
- Node.js를 설치하세요: [https://nodejs.org/](https://nodejs.org/)
- 최소 버전: Node.js 18 이상

**문제: npm 설치 오류**
```bash
# 캐시 정리 후 재설치
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

**문제: 포트 5173이 이미 사용 중**
- Vite가 자동으로 다음 사용 가능한 포트를 찾습니다 (예: 5174)

### CORS 오류

프론트엔드에서 백엔드 API 호출 시 CORS 오류가 발생하면:

1. 백엔드 `.env` 파일의 `CORS_ALLOW_ORIGIN` 확인
2. 백엔드 재시작
3. 브라우저 개발자 도구의 Console 탭에서 오류 확인

## 🔄 개발 워크플로우

### 일반적인 개발 흐름

```bash
# 매일 작업 시작
cd backend
source venv/bin/activate  # 가상환경 활성화
./run_local.sh            # 백엔드 실행

# 새 터미널
cd frontend
./run_dev.sh              # 프론트엔드 실행
```

### 코드 변경 시

- **백엔드**: Chalice가 자동으로 재로드됨 (파일 저장 시)
- **프론트엔드**: Vite의 HMR(Hot Module Replacement)로 즉시 반영

### 의존성 추가 시

**백엔드:**
```bash
pip install 새패키지
pip freeze > requirements.txt
```

**프론트엔드:**
```bash
npm install 새패키지
# package.json이 자동으로 업데이트됨
```

## 📚 다음 단계

1. **API 문서 확인**: `docs/PRD.md`에서 API 명세 확인
2. **컴포넌트 개발**: `frontend/src/components/`에 새 컴포넌트 추가
3. **백엔드 엔드포인트 추가**: `backend/app.py`에 새 라우트 추가

## 💡 유용한 명령어

### 백엔드

```bash
# 의존성 설치
pip install -r requirements.txt

# 로컬 서버 실행
chalice local

# 배포 (AWS)
chalice deploy

# 로그 확인
chalice logs
```

### 프론트엔드

```bash
# 개발 서버 실행
npm run dev

# 프로덕션 빌드
npm run build

# 빌드 미리보기
npm run preview

# 타입 체크
npm run build  # TypeScript 컴파일 포함
```

## 🆘 도움이 필요하신가요?

- **README**: 프로젝트 전체 개요는 [README.md](../README.md) 참조
- **PRD**: 제품 요구사항은 [docs/PRD.md](../docs/PRD.md) 참조
- **GitHub Issues**: 문제 발생 시 이슈 등록

---

✨ 즐거운 개발 되세요! Happy Coding!
