# Shuking - 증여세 상담 AI 챗봇

## 📌 프로젝트 개요
한국 증여세 관련 상담을 제공하는 AI 챗봇 서비스

## 🚀 배포 정보

### Production API
- **Base URL**: `https://wwlawew4b7.execute-api.ap-northeast-2.amazonaws.com/api`
- **Health Check**: `GET /health`
- **API 문서**: `docs/prd_detail/api-spec.md` 참고

### 주요 엔드포인트
- `GET /health` - 헬스 체크
- `POST /sessions` - 새 세션 생성
- `GET /sessions` - 세션 목록 조회
- `PATCH /sessions/{id}` - 세션 제목 수정
- `DELETE /sessions/{id}` - 세션 삭제
- `GET /sessions/{id}/messages` - 메시지 목록
- `POST /sessions/{id}/messages` - 메시지 전송

## 🏗️ 아키텍처

### Backend
- **Framework**: AWS Chalice (Python 3.12)
- **Deployment**: Lambda Container Image (arm64)
- **API Gateway**: REST API (Regional)
- **Database**: PostgreSQL (pgvector 확장 포함)
- **AI**: Google Gemini 1.5 Pro
- **ORM**: SQLAlchemy + SQLModel

### Frontend
- **Framework**: Vue 3 + Vite
- **Deployment**: CloudFront + S3

## 📦 배포 방식

### Lambda Container Image
- **ECR Repository**: `862108802423.dkr.ecr.ap-northeast-2.amazonaws.com/shuking-lambda`
- **Image Size Limit**: 10GB (vs ZIP 50MB 제한)
- **Architecture**: arm64
- **Runtime**: Python 3.12

### CI/CD
- **Platform**: GitHub Actions
- **Workflow**: `.github/workflows/deploy.yml`
- **Secrets**: AWS Secrets Manager (`shuking-QbyWZz`)

## 🛠️ 로컬 개발

### Backend 실행
```bash
cd backend
source ../.venv/bin/activate  # 또는 pyenv shell shuking
chalice local --port 8000
```

### 환경 변수 설정
```bash
cd backend
./.scripts/fetch-secrets.sh  # AWS Secrets Manager에서 .env 생성
```

## 📚 문서
- [PRD](docs/PRD.md)
- [API 명세서](docs/prd_detail/api-spec.md)
- [데이터베이스 모델](docs/prd_detail/database-model.md)
- [백엔드 아키텍처](docs/prd_detail/backend-architecture.md)
- [작업 히스토리](docs/history/)

## 🔐 Secrets 관리
- AWS Secrets Manager ARN: `arn:aws:secretsmanager:ap-northeast-2:862108802423:secret:shuking-QbyWZz`
- 상세 내용: `docs/secrets-management.md` 참고

## 📝 라이센스
Proprietary
