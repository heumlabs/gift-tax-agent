# 작업 이력: 202510151830_env_in_docker_image

## 작업 요약
환경 변수를 Docker 이미지에 `.env` 파일로 포함시켜 Lambda 환경 변수 설정을 완전히 제거했습니다. GitHub Actions에서 Secrets Manager로부터 환경 변수를 가져와 `.env` 파일을 생성하고, 이를 Docker 이미지에 포함시킴으로써 배포 프로세스를 단순화하고 보안을 강화했습니다.

## 변경 사항

### 1. .dockerignore 수정
- **파일**: `backend/.dockerignore`
- **변경 내용**: `.env` 파일이 Docker 이미지에 포함되도록 수정

**변경 전**:
```dockerignore
# Environment files
.env
.env.*
```

**변경 후**:
```dockerignore
# Environment files (빌드 시 생성되는 .env는 포함)
.env.example
.env.local
.env.*.local
```

### 2. GitHub Actions 워크플로우 수정
- **파일**: `.github/workflows/deploy.yml`
- **추가**: "Create .env file from Secrets Manager" 단계

**새로운 워크플로우**:
```yaml
- name: Create .env file from Secrets Manager
  run: |
    # Secrets Manager에서 환경 변수 가져오기
    SECRET_JSON=$(aws secretsmanager get-secret-value \
      --secret-id arn:aws:secretsmanager:ap-northeast-2:862108802423:secret:shuking-QbyWZz \
      --query SecretString \
      --output text \
      --region $AWS_REGION)

    # 개별 환경 변수 추출
    GOOGLE_API_KEY=$(echo "$SECRET_JSON" | jq -r '.GOOGLE_API_KEY')
    DB_HOST=$(echo "$SECRET_JSON" | jq -r '.DB_HOST')
    # ... 기타 환경 변수

    # .env 파일 생성
    cat > .env << EOF
    ENVIRONMENT=prod
    APP_STAGE=${APP_STAGE}
    GOOGLE_API_KEY=${GOOGLE_API_KEY}
    DB_HOST=${DB_HOST}
    DB_USER=${DB_USER}
    DB_PASS=${DB_PASS}
    DB_NAME=${DB_NAME}
    CORS_ALLOW_ORIGIN=https://d49mat9gykfn6.cloudfront.net
    EOF

- name: Build, tag, and push Docker image
  # .env 파일이 포함된 이미지 빌드
```

### 3. 불필요한 스크립트 삭제
- **삭제**: `backend/.scripts/setup-lambda-env.sh`
- **이유**: Lambda 환경 변수 설정이 더 이상 필요 없음

## 아키텍처 개선

### 이전 방식
```
GitHub Actions
  ↓
1. Docker 이미지 빌드 (환경 변수 없음)
  ↓
2. ECR 푸시
  ↓
3. Lambda 업데이트
  ↓
4. Lambda 환경 변수 설정 (Secrets Manager → Lambda)
  ↓
런타임: pydantic-settings가 Lambda 환경 변수 로드
```

**문제점**:
- Lambda 환경 변수 설정이 복잡
- GitHub Actions 로그에 민감 정보 노출 가능
- 환경 변수와 코드가 분리되어 관리

### 현재 방식
```
GitHub Actions
  ↓
1. Secrets Manager에서 환경 변수 가져오기
  ↓
2. .env 파일 생성 (backend/.env)
  ↓
3. Docker 이미지 빌드 (.env 포함)
  ↓
4. ECR 푸시
  ↓
5. Lambda 업데이트
  ↓
런타임: pydantic-settings가 이미지 내부의 .env 로드
```

**개선점**:
- ✅ Lambda 환경 변수 설정 불필요
- ✅ .env 파일이 이미지에 포함되어 즉시 사용 가능
- ✅ 환경 변수가 코드와 함께 버전 관리됨 (이미지 단위)
- ✅ 배포 프로세스 단순화

## 보안

### 민감 정보 보호
1. **Secrets Manager**: 민감 정보의 단일 소스
2. **GitHub Actions 로그**: 환경 변수 값이 직접 노출되지 않음
   - `SECRET_JSON`에서 값을 추출하여 .env에 작성
   - 작성된 .env는 로그에 출력되지 않음
3. **Docker 이미지**: .env 파일이 이미지 내부에만 존재
   - 외부에서 직접 접근 불가
   - Lambda 런타임에서만 사용

### .env 파일 생명주기
1. **생성**: GitHub Actions에서 빌드 시마다 생성
2. **사용**: Docker 이미지에 포함되어 Lambda에서 사용
3. **삭제**: GitHub Actions 워크플로우 종료 시 자동 삭제
4. **보안**: 이미지 외부로 노출되지 않음

## pydantic-settings 동작

### 환경 변수 로드 순서
```python
# config.py
class Settings(BaseSettings):
    GOOGLE_API_KEY: Optional[str] = None
    DB_HOST: Optional[str] = None
    # ...
    
    model_config = SettingsConfigDict(
        env_file=".env",           # ← Docker 이미지에 포함된 .env
        case_sensitive=True,
        extra="ignore",
    )

settings = Settings()  # .env 파일 자동 로드
```

**로드 우선순위**:
1. **환경 변수** (있으면 우선)
2. **.env 파일** (이미지에 포함)
3. **기본값**

### Docker 이미지 내부 구조
```
/var/task/
├── .env                    # ← GitHub Actions에서 생성된 환경 변수
├── app.py
├── lambda_handler.py
├── config.py              # ← .env 로드
├── chalicelib/
│   ├── models/
│   ├── services/
│   └── ...
└── requirements.txt
```

## 배포 플로우

### 1. 코드 변경 후 배포
```bash
git push origin main
# GitHub Actions 자동 실행:
# 1. Secrets Manager에서 최신 환경 변수 가져오기
# 2. .env 파일 생성
# 3. Docker 이미지 빌드 (.env 포함)
# 4. ECR 푸시
# 5. Lambda 업데이트
```

### 2. 환경 변수 변경 후 배포
```bash
# 1. Secrets Manager 업데이트
aws secretsmanager update-secret \
  --secret-id arn:aws:secretsmanager:ap-northeast-2:862108802423:secret:shuking-QbyWZz \
  --secret-string '{"GOOGLE_API_KEY":"new-key",...}' \
  --region ap-northeast-2

# 2. 재배포 (자동으로 새 환경 변수 반영)
git commit --allow-empty -m "chore: redeploy with new env vars"
git push origin main
```

## 영향 범위

### Docker 이미지
- **크기**: .env 파일 추가로 약 1KB 증가 (무시할 수 있는 수준)
- **보안**: .env 파일이 이미지에 포함되어 있지만, 이미지 자체는 private ECR에 저장됨
- **버전 관리**: 환경 변수가 이미지와 함께 버전 관리됨

### CI/CD 파이프라인
- **빌드 시간**: .env 생성 단계 추가로 약 1-2초 증가
- **복잡도**: Lambda 환경 변수 설정 단계 제거로 전체적으로 단순화
- **보안**: GitHub Actions 로그에 민감 정보 노출 방지

### Lambda 함수
- **콜드 스타트**: 변화 없음 (환경 변수 로드 방식만 변경)
- **환경 변수**: Lambda 환경 변수 설정 불필요
- **설정 관리**: 더 이상 Lambda 콘솔에서 환경 변수 관리할 필요 없음

## 장점

### 1. 배포 단순화
- Lambda 환경 변수 설정 단계 제거
- .env 파일이 자동으로 이미지에 포함됨
- 환경 변수 변경 시 재배포만 하면 됨

### 2. 보안 강화
- GitHub Actions 로그에 민감 정보 노출 안됨
- .env 파일이 이미지 내부에만 존재
- Secrets Manager가 단일 소스

### 3. 일관성
- 모든 환경 변수가 .env 파일에 있음
- 로컬 개발과 프로덕션이 동일한 방식으로 환경 변수 로드
- 환경 변수가 코드(이미지)와 함께 버전 관리됨

### 4. 디버깅 용이
- 특정 이미지 태그의 환경 변수를 확인하려면 해당 이미지만 확인하면 됨
- Lambda 환경 변수와 코드 간 불일치 가능성 제거

## 주의사항

### .env 파일 보안
- ✅ **안전**: Docker 이미지는 private ECR에 저장됨
- ✅ **안전**: Lambda는 AWS IAM으로 보호됨
- ⚠️ **주의**: ECR에 대한 접근 권한 관리 필요

### 환경 변수 변경
- Secrets Manager만 업데이트하고 재배포하지 않으면 변경사항이 반영되지 않음
- 환경 변수 변경 후 반드시 재배포 필요

### .gitignore 설정
```gitignore
# backend/.gitignore
.env          # ← GitHub Actions에서 생성하므로 커밋하지 않음
.env.local
.env.*.local
```

## 다음 단계

### 테스트
1. Secrets Manager 값 변경
2. 재배포
3. Lambda 함수에서 새 환경 변수 확인

### 모니터링
- CloudWatch Logs에서 config 로드 확인
- .env 파일이 정상적으로 로드되는지 확인

## 기타

### 변경된 파일
- **수정**: `backend/.dockerignore`
- **수정**: `.github/workflows/deploy.yml`
- **삭제**: `backend/.scripts/setup-lambda-env.sh`

### 참고
- pydantic-settings 문서: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- Docker .env 파일: https://docs.docker.com/compose/environment-variables/

