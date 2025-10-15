# 작업 이력: 202510151951_api_deployment_fixes

## 작업 요약
Lambda Container Image 배포 완료 및 API Gateway 설정, CloudWatch Logs 권한 추가

## 변경 사항

### 1. CloudWatch Logs 권한 추가
- `minimal-shuking-policies` IAM 정책 업데이트
- 추가된 권한:
  - `logs:CreateLogStream`
  - `logs:PutLogEvents`
- Lambda 함수 로그 생성 가능

### 2. Docker 이미지 수정
- `Dockerfile`에 `config.py` 및 `.env` 파일 포함
- pydantic-settings가 `.env` 파일에서 환경변수 로드
- ECR 이미지: `862108802423.dkr.ecr.ap-northeast-2.amazonaws.com/shuking-lambda:latest`

### 3. API Gateway 설정
- 새로운 API Gateway 생성: `wwlawew4b7`
- Proxy 통합 구성 (`{proxy+}` 리소스)
- Lambda 호출 권한 부여
- **API Gateway URL**: `https://wwlawew4b7.execute-api.ap-northeast-2.amazonaws.com/api`

### 4. app.py 라우트 수정
- API Gateway stage가 `/api`이므로 app.py 라우트에서 `/api` prefix 제거
- 라우트: `/health`, `/sessions`, `/sessions/{id}`, `/sessions/{id}/messages`
- 실제 URL: `/api/health`, `/api/sessions` 등

### 5. GitHub Actions 워크플로우
- `.github/workflows/deploy.yml`에서 `cd backend` 제거
- `working-directory: ./backend` 설정 활용
- `.env` 파일 생성: Secrets Manager → Docker 이미지에 포함

## 영향 범위

### Lambda 함수
- **함수명**: `shuking-prod`
- **패키지 타입**: Container Image (10GB 제한)
- **아키텍처**: arm64
- **런타임**: Python 3.12
- **메모리**: 512 MB
- **타임아웃**: 60초

### API Gateway
- **API ID**: `wwlawew4b7`
- **Stage**: `api`
- **엔드포인트 타입**: REGIONAL
- **Base URL**: `https://wwlawew4b7.execute-api.ap-northeast-2.amazonaws.com/api`

### IAM 정책
- **정책명**: `minimal-shuking-policies`
- **버전**: v8 (최신)
- CloudWatch Logs 쓰기 권한 추가

## 테스트

### Lambda 직접 호출 테스트
```bash
aws lambda invoke --function-name shuking-prod --region ap-northeast-2 \
  --cli-binary-format raw-in-base64-out \
  --payload file://test-event.json response.json
```
✅ 성공 (statusCode: 200)

### API Gateway 테스트
- Health check: `/api/health`
- 세션 생성: `POST /api/sessions`
- 세션 목록: `GET /api/sessions`
- 메시지 조회: `GET /api/sessions/{id}/messages`
- 메시지 전송: `POST /api/sessions/{id}/messages`

**참고**: Mock 데이터 반환 (실제 서비스 로직은 추후 구현 예정)

## 기타

### 삭제된 파일
- `backend/.scripts/migrate-to-container.sh` (일회성 스크립트)
- `backend/.scripts/update-lambda-env.sh` (환경변수는 .env로 관리)
- `.chalice/deployed/prod.json` (재배포를 위해 초기화)

### 주요 문서
- `docs/secrets-management.md`: Secrets Manager 사용법
- `docs/prd_detail/api-spec.md`: API 명세서
- `docs/prd_detail/database-model.md`: 데이터베이스 스키마
- `docs/prd_detail/backend-architecture.md`: 백엔드 아키텍처

### 다음 작업
- [ ] 실제 서비스 로직 구현 (AI 응답 생성)
- [ ] 데이터베이스 연결 테스트
- [ ] Vector 검색 기능 구현
- [ ] Frontend 연동 테스트

