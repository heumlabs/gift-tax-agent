# 작업 이력: 202510151800_remove_env_update_from_cicd

## 작업 요약
GitHub Actions에서 Lambda 환경 변수 업데이트 단계를 제거하여 민감 정보 노출을 방지하고, CI/CD 파이프라인을 간소화했습니다. Lambda 환경 변수는 초기 설정 후 변경할 필요가 없으므로, 별도의 설정 스크립트로 분리했습니다.

## 변경 사항

### 1. GitHub Actions 워크플로우 수정
- **파일**: `.github/workflows/deploy.yml`
- **제거**: "Update Lambda environment variables" 단계
- **이유**:
  1. **보안**: GitHub Actions 로그에 민감 정보(DB 비밀번호 등) 노출 방지
  2. **효율성**: Lambda 환경 변수는 코드 배포 시마다 변경할 필요 없음
  3. **간소화**: pydantic-settings가 Lambda 환경 변수를 자동으로 로드하므로, 한 번만 설정하면 됨

**변경 전**:
```yaml
- name: Update Lambda environment variables
  run: |
    # Secrets Manager에서 환경 변수 가져오기
    SECRET_JSON=$(aws secretsmanager get-secret-value ...)
    
    # Lambda 환경 변수 업데이트 (매 배포마다 실행)
    aws lambda update-function-configuration ...
```

**변경 후**:
```yaml
# Note: Lambda 환경 변수는 초기 설정 후 변경할 필요가 없음
# 환경 변수 초기 설정은 backend/.scripts/setup-lambda-env.sh 스크립트 사용
```

### 2. 환경 변수 설정 스크립트 추가
- **파일**: `backend/.scripts/setup-lambda-env.sh`
- **용도**: Lambda 함수 생성 후 최초 1회 환경 변수 설정
- **특징**:
  - Secrets Manager에서 자동으로 환경 변수 가져오기
  - 민감 정보는 로컬에서만 처리 (GitHub Actions 로그에 노출 안됨)
  - 환경 변수 변경이 필요할 때만 수동으로 실행

**사용법**:
```bash
cd backend/.scripts
./setup-lambda-env.sh
```

**스크립트 기능**:
1. Secrets Manager에서 환경 변수 가져오기
2. Lambda 함수 환경 변수 업데이트
3. 업데이트 완료 대기
4. 설정된 환경 변수 요약 출력 (비밀번호는 마스킹)

## 영향 범위

### CI/CD 파이프라인
- **배포 속도**: Lambda 환경 변수 업데이트 단계 제거로 배포 시간 단축 (~10초)
- **보안**: GitHub Actions 로그에 민감 정보 노출 방지
- **워크플로우**: 이미지 빌드 → ECR 푸시 → Lambda 코드 업데이트 (환경 변수 단계 제거)

### Lambda 환경 변수 관리
- **초기 설정**: `setup-lambda-env.sh` 스크립트 실행 (1회)
- **코드 배포**: GitHub Actions 자동 배포 (환경 변수 변경 없음)
- **환경 변수 변경**: `setup-lambda-env.sh` 스크립트 재실행

## 보안 개선

### 문제점 (이전)
GitHub Actions 로그에서 다음과 같은 정보가 노출될 수 있었음:
```
DB_HOST=alfred-agent-stag.cb16259gyybz.ap-northeast-2.rds.amazonaws.com
DB_USER=shuking
DB_PASS=shuking-t@x!234  # ⚠️ 노출 위험
```

### 해결 (현재)
- Lambda 환경 변수는 로컬에서 스크립트로 설정
- GitHub Actions에서는 환경 변수를 건드리지 않음
- Secrets Manager 내용이 GitHub Actions 로그에 노출되지 않음

## 사용 가이드

### 1. Lambda 함수 최초 배포 시

```bash
# 1. Lambda 함수 생성 (migrate-to-container.sh 또는 수동)
cd backend/.scripts
./migrate-to-container.sh  # 이미 생성되어 있으면 생략

# 2. 환경 변수 설정
./setup-lambda-env.sh
```

### 2. 코드 배포 시

```bash
# GitHub Actions가 자동으로 처리 (main 브랜치 병합 시)
# 환경 변수는 변경되지 않음
```

### 3. 환경 변수 변경이 필요한 경우

```bash
# 1. Secrets Manager 업데이트
aws secretsmanager update-secret \
  --secret-id arn:aws:secretsmanager:ap-northeast-2:862108802423:secret:shuking-QbyWZz \
  --secret-string '{"GOOGLE_API_KEY":"new-key","DB_HOST":"..."}' \
  --region ap-northeast-2

# 2. Lambda 환경 변수 재설정
cd backend/.scripts
./setup-lambda-env.sh
```

## 환경 변수 설정 내용

`setup-lambda-env.sh` 스크립트가 설정하는 환경 변수:

```bash
ENVIRONMENT=prod                              # 환경 (prod/dev)
APP_STAGE=prod                                # 앱 스테이지 (하위 호환성)
GOOGLE_API_KEY=AIzaSy...                     # Gemini API 키
DB_HOST=alfred-agent-stag...                  # PostgreSQL 호스트
DB_USER=shuking                               # DB 사용자
DB_PASS=shuking-t@x!234                       # DB 비밀번호
DB_NAME=shuking                               # DB 이름
CORS_ALLOW_ORIGIN=https://d49mat9gykfn6...    # CORS 허용 오리진
```

이 환경 변수들은 `config.py`의 pydantic-settings가 자동으로 로드합니다.

## 기술적 배경

### pydantic-settings 동작 원리

```python
# config.py
class Settings(BaseSettings):
    GOOGLE_API_KEY: Optional[str] = None
    DB_HOST: Optional[str] = None
    # ...
    
    model_config = SettingsConfigDict(
        env_file=".env",           # 로컬 개발: .env 파일
        case_sensitive=True,
        extra="ignore",
    )

settings = Settings()  # Lambda 환경 변수 자동 로드
```

**환경 변수 로드 우선순위**:
1. **Lambda 환경 변수** (프로덕션) ← 우선
2. `.env` 파일 (로컬 개발)

### Lambda Container Image 특성

- **환경 변수**: Lambda 함수 설정에 저장되어 있음
- **이미지 업데이트**: 코드만 업데이트, 환경 변수는 유지됨
- **pydantic-settings**: 컨테이너 시작 시 환경 변수 자동 로드

따라서 코드 배포 시마다 환경 변수를 재설정할 필요가 없습니다.

## 다음 단계

### Lambda 함수가 이미 존재하는 경우
환경 변수가 이미 설정되어 있으므로 추가 작업 불필요

### Lambda 함수를 새로 생성하는 경우
```bash
cd backend/.scripts
./setup-lambda-env.sh
```

## 기타

### 변경된 파일
- **수정**: `.github/workflows/deploy.yml`
- **추가**: `backend/.scripts/setup-lambda-env.sh`

### 참고
- 환경 변수는 Lambda 함수 설정에 안전하게 저장됨
- Secrets Manager는 환경 변수의 소스로만 사용 (Lambda에 직접 주입하지 않음)
- GitHub Actions는 코드 배포만 담당, 환경 설정은 분리됨

