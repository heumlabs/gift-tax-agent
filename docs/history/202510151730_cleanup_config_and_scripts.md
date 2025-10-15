# 작업 이력: 202510151730_cleanup_config_and_scripts

## 작업 요약
Container Image 배포 방식에 맞춰 불필요한 스크립트 삭제 및 환경 변수 관리 구조를 개선했습니다. pydantic-settings를 통한 일관된 설정 관리로 변경하고, GitHub Actions에서 Lambda 환경 변수를 직접 관리하도록 워크플로우를 수정했습니다.

## 변경 사항

### 1. 불필요한 스크립트 삭제
- **삭제된 파일**:
  - `backend/.scripts/migrate-to-container.sh` - Container Image 마이그레이션 완료로 불필요
  - `backend/.scripts/update-lambda-env.sh` - GitHub Actions에서 처리하도록 변경

### 2. config.json 최소화
- **파일**: `backend/.chalice/config.json`
- **변경 전**:
  ```json
  {
    "version": "2.0",
    "app_name": "shuking",
    "automatic_layer": true,
    "stages": {
      "prod": {
        "use_container": false,
        "environment_variables": {...}
      }
    }
  }
  ```
- **변경 후**:
  ```json
  {
    "version": "2.0",
    "app_name": "shuking"
  }
  ```
- **이유**: Container Image 방식에서는 `chalice deploy`를 사용하지 않으므로 config.json의 설정이 Lambda에 적용되지 않음

### 3. pydantic-settings 기반 설정 관리
- **파일**: `backend/config.py`
- **변경 내용**:
  - 개별 DB 설정(`DB_HOST`, `DB_NAME` 등)을 `DATABASE_URL`로 통합
  - `ENVIRONMENT`, `GEMINI_API_KEY`, `CORS_ALLOW_ORIGIN` 추가
  - 환경 변수 로드 우선순위 명시:
    1. Lambda 환경 변수 (프로덕션)
    2. .env 파일 (로컬 개발)

- **변경 전**:
  ```python
  class Settings(BaseSettings):
      APP_STAGE: str = "local"
      DB_HOST: str
      DB_NAME: str
      DB_USER: str
      DB_PASS: str
      GOOGLE_API_KEY: str
  ```

- **변경 후**:
  ```python
  class Settings(BaseSettings):
      ENVIRONMENT: str = "local"
      DATABASE_URL: str
      GEMINI_API_KEY: str
      CORS_ALLOW_ORIGIN: str = "http://localhost:5173"
  ```

### 4. 데이터베이스 연결 수정
- **파일**: `backend/chalicelib/db/connection.py`
- **변경 내용**:
  - `os.getenv("DATABASE_URL")`에서 `settings.DATABASE_URL`로 변경
  - pydantic-settings를 통한 일관된 설정 접근

### 5. app.py 설정 통합
- **파일**: `backend/app.py`
- **변경 내용**:
  - CORS: `os.getenv("CORS_ALLOW_ORIGIN")`에서 `settings.CORS_ALLOW_ORIGIN`으로 변경
  - Health check: `os.getenv("ENVIRONMENT")`에서 `settings.ENVIRONMENT`로 변경

### 6. GitHub Actions 워크플로우 수정
- **파일**: `.github/workflows/deploy.yml`
- **추가 내용**: Lambda 환경 변수 업데이트 단계
  ```yaml
  - name: Update Lambda environment variables
    run: |
      # Secrets Manager에서 DATABASE_URL 가져오기
      DATABASE_URL=$(aws secretsmanager get-secret-value \
        --secret-id shuking/database \
        --query SecretString \
        --output text \
        --region $AWS_REGION | jq -r '.DATABASE_URL')

      # Secrets Manager에서 GEMINI_API_KEY 가져오기
      GEMINI_API_KEY=$(aws secretsmanager get-secret-value \
        --secret-id shuking/api-keys \
        --query SecretString \
        --output text \
        --region $AWS_REGION | jq -r '.GEMINI_API_KEY')

      # Lambda 환경 변수 업데이트
      aws lambda update-function-configuration \
        --function-name $LAMBDA_FUNCTION_NAME \
        --environment "Variables={
          ENVIRONMENT=prod,
          DATABASE_URL=$DATABASE_URL,
          GEMINI_API_KEY=$GEMINI_API_KEY,
          CORS_ALLOW_ORIGIN=https://d49mat9gykfn6.cloudfront.net
        }" \
        --region $AWS_REGION
  ```

### 7. .env.example 파일 추가
- **파일**: `backend/.env.example`
- **내용**:
  ```env
  ENVIRONMENT=local
  DATABASE_URL=postgresql://postgres:password@localhost:5432/shuking
  GEMINI_API_KEY=your-gemini-api-key-here
  CORS_ALLOW_ORIGIN=http://localhost:5173
  ```

## 영향 범위

### 설정 관리
- **로컬 개발**: `.env` 파일에서 환경 변수 로드
- **프로덕션**: Lambda 환경 변수에서 로드 (Secrets Manager 경유)
- **일관성**: pydantic-settings를 통한 통일된 설정 접근

### Container Image 배포
- `config.json`은 최소한의 정보만 유지 (app_name만)
- Lambda 환경 변수는 GitHub Actions에서 직접 관리
- Secrets Manager를 통한 민감 정보 보호

### 개발 환경
- `.env.example`을 복사하여 로컬 `.env` 파일 생성 필요
- `DATABASE_URL` 형식으로 통합된 연결 문자열 사용

## 기술적 개선 사항

### 1. 환경 변수 관리 일원화
**이전 문제점**:
- `config.json`의 `environment_variables`는 Container Image 방식에서 적용되지 않음
- `os.getenv()`와 pydantic-settings가 혼재
- 개별 DB 설정 vs DATABASE_URL 불일치

**개선 결과**:
- pydantic-settings를 통한 일관된 환경 변수 로드
- Lambda 환경 변수를 GitHub Actions에서 명시적으로 관리
- DATABASE_URL 형식으로 통합

### 2. Container Image 배포 최적화
**변경 사항**:
- `chalice deploy` 의존성 제거 (config.json 최소화)
- GitHub Actions에서 직접 Lambda 관리
- Secrets Manager를 통한 안전한 비밀 정보 관리

### 3. 개발 환경 개선
**추가 사항**:
- `.env.example` 파일로 필요한 환경 변수 명시
- pydantic-settings 타입 힌트로 IDE 지원 향상
- 설정 클래스에 docstring 추가

## AWS Secrets Manager 설정

기존 시크릿 사용: `arn:aws:secretsmanager:ap-northeast-2:862108802423:secret:shuking-QbyWZz`

현재 구조:
```json
{
  "GOOGLE_API_KEY": "AIzaSy...",
  "DB_HOST": "alfred-agent-stag.cb16259gyybz.ap-northeast-2.rds.amazonaws.com",
  "DB_USER": "shuking",
  "DB_PASS": "shuking-t@x!234",
  "DB_NAME": "shuking",
  "APP_STAGE": "prod"
}
```

**하위 호환성**: config.py가 `DATABASE_URL` 또는 개별 `DB_*` 필드 모두 지원하도록 구현됨

## 테스트

### 로컬 개발 환경
1. `.env.example`을 `.env`로 복사
2. 실제 값으로 환경 변수 수정
3. `chalice local` 또는 Docker로 테스트

### CI/CD 파이프라인
1. AWS Secrets Manager에 시크릿 생성
2. GitHub Actions 실행
3. Lambda 환경 변수 자동 업데이트 확인

## 다음 단계

1. **로컬 .env 파일 생성**:
   ```bash
   cd backend
   cp .env.example .env
   # .env 파일 수정하여 실제 값 입력
   ```

2. **Lambda IAM 권한 확인**:
   - Lambda 실행 역할(`shuking-role`)에 Secrets Manager 접근 권한 필요
   ```json
   {
     "Effect": "Allow",
     "Action": [
       "secretsmanager:GetSecretValue"
     ],
     "Resource": [
       "arn:aws:secretsmanager:ap-northeast-2:862108802423:secret:shuking-QbyWZz"
     ]
   }
   ```

3. **(선택) Secrets Manager 시크릿 업데이트**:
   - 필요시 새로운 환경 변수를 기존 시크릿에 추가
   ```bash
   aws secretsmanager update-secret \
     --secret-id arn:aws:secretsmanager:ap-northeast-2:862108802423:secret:shuking-QbyWZz \
     --secret-string '{"GOOGLE_API_KEY":"...","DB_HOST":"...","DB_USER":"...","DB_PASS":"...","DB_NAME":"...","APP_STAGE":"prod"}' \
     --region ap-northeast-2
   ```

## 기타

### 삭제된 파일 요약
- `backend/.scripts/migrate-to-container.sh`
- `backend/.scripts/update-lambda-env.sh`

### 추가된 파일
- `backend/.env.example`

### pydantic-settings 장점
1. **타입 안전성**: IDE 자동완성 및 타입 체크
2. **검증**: Pydantic 기반 자동 데이터 검증
3. **환경 독립성**: .env 파일과 환경 변수 모두 지원
4. **명시적**: 필요한 모든 설정이 코드에 명시됨

