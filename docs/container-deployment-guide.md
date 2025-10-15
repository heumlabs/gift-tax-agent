# Lambda Container Image 배포 가이드

## 개요

Lambda Container Image를 사용하여 **10GB까지** 배포 가능 (기존 50MB 제한 해결)

## 아키텍처

```
┌─────────────────────────────────────────────────────┐
│               GitHub Actions                         │
│  ┌────────────────────────────────────────────────┐ │
│  │ 1. Docker Build                                │ │
│  │ 2. Push to ECR                                 │ │
│  │ 3. Update Lambda                               │ │
│  └────────────────────────────────────────────────┘ │
└─────────────────────┬───────────────────────────────┘
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
┌──────────────────┐      ┌──────────────────┐
│   Amazon ECR     │      │  Lambda Function │
│                  │      │  (Container)     │
│ shuking-lambda   │──────▶  shuking-prod    │
│  :latest         │      │                  │
└──────────────────┘      └──────────────────┘
```

## 파일 구조

```
backend/
├── Dockerfile              # Lambda Container 이미지
├── .dockerignore          # Docker 빌드 제외 파일
├── app.py                 # Chalice app (그대로 유지)
├── lambda_handler.py      # Lambda handler wrapper
├── requirements.txt       # 모든 의존성
└── .scripts/
    ├── migrate-to-container.sh   # 최초 마이그레이션
    └── update-lambda-env.sh      # 환경변수 업데이트
```

## 배포 방법

### 최초 설정 (한 번만)

#### 1. ECR 리포지토리 생성 및 Lambda 함수 전환
```bash
cd backend

# Secrets Manager에서 환경변수 로드
./.scripts/fetch-secrets.sh

# Container로 마이그레이션
./.scripts/migrate-to-container.sh
```

**이 스크립트가 수행하는 작업:**
- ✅ ECR 리포지토리 생성 (`shuking-lambda`)
- ✅ Docker 이미지 빌드
- ✅ ECR에 푸시
- ✅ 기존 Lambda 함수 삭제
- ✅ Container 기반 Lambda 함수 생성

#### 2. 환경변수 설정
```bash
./.scripts/update-lambda-env.sh
```

#### 3. API Gateway 연결 (수동)

기존 Chalice가 생성한 API Gateway를 그대로 사용:

```bash
# API Gateway ID 확인
aws apigateway get-rest-apis --region ap-northeast-2 --query 'items[?name==`shuking`]'

# Lambda Integration 업데이트
API_ID="your-api-id"
RESOURCE_ID="your-resource-id"
LAMBDA_ARN="arn:aws:lambda:ap-northeast-2:862108802423:function:shuking-prod"

aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $RESOURCE_ID \
  --http-method ANY \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri arn:aws:apigateway:ap-northeast-2:lambda:path/2015-03-31/functions/$LAMBDA_ARN/invocations

# API Gateway 배포
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name api
```

### 일반 배포 (자동)

**GitHub Actions를 통한 자동 배포:**

```bash
# main 브랜치에 푸시하면 자동 배포
git push origin main
```

**워크플로우 단계:**
1. Docker 이미지 빌드
2. ECR에 푸시 (`<account>.dkr.ecr.ap-northeast-2.amazonaws.com/shuking-lambda:latest`)
3. Lambda 함수 업데이트
4. 업데이트 완료 대기

### 수동 배포 (로컬)

```bash
cd backend

# 1. Docker 이미지 빌드
docker build -t shuking-lambda:latest .

# 2. ECR 로그인
aws ecr get-login-password --region ap-northeast-2 | \
  docker login --username AWS --password-stdin \
  862108802423.dkr.ecr.ap-northeast-2.amazonaws.com

# 3. 이미지 태그 및 푸시
docker tag shuking-lambda:latest \
  862108802423.dkr.ecr.ap-northeast-2.amazonaws.com/shuking-lambda:latest
docker push 862108802423.dkr.ecr.ap-northeast-2.amazonaws.com/shuking-lambda:latest

# 4. Lambda 함수 업데이트
aws lambda update-function-code \
  --function-name shuking-prod \
  --image-uri 862108802423.dkr.ecr.ap-northeast-2.amazonaws.com/shuking-lambda:latest \
  --region ap-northeast-2

# 5. 업데이트 완료 대기
aws lambda wait function-updated \
  --function-name shuking-prod \
  --region ap-northeast-2
```

## Dockerfile 구조

```dockerfile
FROM public.ecr.aws/lambda/python:3.12

# 의존성 설치 (캐싱 최적화)
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# 애플리케이션 코드
COPY app.py ${LAMBDA_TASK_ROOT}/
COPY lambda_handler.py ${LAMBDA_TASK_ROOT}/

# Lambda handler
CMD ["lambda_handler.handler"]
```

## Lambda Handler Wrapper

`lambda_handler.py`:
```python
from app import app as chalice_app

def handler(event, context):
    """Chalice app을 Lambda handler로 wrapping"""
    return chalice_app(event, context)
```

**Chalice app은 그대로 유지하되, Container에서 실행 가능하도록 wrapper 추가**

## 로컬 테스트

```bash
# Docker 이미지 빌드
cd backend
docker build -t shuking-lambda:test .

# 로컬에서 실행
docker run -p 9000:8080 \
  -e DATABASE_URL="your-db-url" \
  -e GEMINI_API_KEY="your-key" \
  -e CORS_ALLOW_ORIGIN="http://localhost:5173" \
  shuking-lambda:test

# 다른 터미널에서 테스트
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d '{"httpMethod": "GET", "path": "/health", "headers": {}}'
```

## 환경변수 관리

### Secrets Manager 사용
```bash
# 환경변수 로드
./.scripts/fetch-secrets.sh

# Lambda에 적용
./.scripts/update-lambda-env.sh
```

### 수동 설정
```bash
aws lambda update-function-configuration \
  --function-name shuking-prod \
  --environment '{
    "Variables": {
      "ENVIRONMENT": "prod",
      "DATABASE_URL": "your-url",
      "GEMINI_API_KEY": "your-key",
      "CORS_ALLOW_ORIGIN": "https://d49mat9gykfn6.cloudfront.net"
    }
  }' \
  --region ap-northeast-2
```

## 모니터링

### Lambda 로그 확인
```bash
# 최근 로그
aws logs tail /aws/lambda/shuking-prod --follow

# 특정 기간
aws logs tail /aws/lambda/shuking-prod \
  --since 1h \
  --format short
```

### Lambda 함수 정보
```bash
aws lambda get-function \
  --function-name shuking-prod \
  --region ap-northeast-2
```

### 이미지 정보
```bash
aws ecr describe-images \
  --repository-name shuking-lambda \
  --region ap-northeast-2
```

## 트러블슈팅

### 1. 이미지 빌드 실패
```bash
# Docker 로그 확인
docker build --progress=plain -t shuking-lambda:debug .
```

### 2. ECR 푸시 실패
```bash
# ECR 로그인 다시 시도
aws ecr get-login-password --region ap-northeast-2 | \
  docker login --username AWS --password-stdin \
  862108802423.dkr.ecr.ap-northeast-2.amazonaws.com

# 권한 확인
aws ecr get-repository-policy --repository-name shuking-lambda
```

### 3. Lambda 업데이트 실패
```bash
# Lambda 상태 확인
aws lambda get-function-configuration \
  --function-name shuking-prod \
  --region ap-northeast-2 \
  --query 'State'

# 재시도
aws lambda update-function-code \
  --function-name shuking-prod \
  --image-uri 862108802423.dkr.ecr.ap-northeast-2.amazonaws.com/shuking-lambda:latest
```

### 4. Handler 오류
```bash
# 로그에서 오류 확인
aws logs tail /aws/lambda/shuking-prod --follow

# 일반적인 원인:
# - CMD ["lambda_handler.handler"] 경로 오류
# - 모듈 import 실패
# - 환경변수 누락
```

## 비용

### Container Image
- **ECR 스토리지**: $0.10/GB/월
- **예상 이미지 크기**: ~200MB
- **월 비용**: ~$0.02

### Lambda
- **실행 시간**: 기존과 동일
- **메모리**: 512MB
- **추가 비용 없음**

## 장점

### 1. 크기 제한 해결
- ❌ Zip: 50MB
- ❌ Layer: 250MB
- ✅ Container: **10GB**

### 2. 의존성 관리 간소화
- 모든 의존성이 이미지에 포함
- Layer 관리 불필요
- requirements.txt만 관리

### 3. 로컬 개발 환경
```bash
docker run -p 9000:8080 shuking-lambda:local
```

### 4. 확장성
- 추후 다른 서비스로 전환 용이
- Docker 표준 활용

## 참고 문서

- [AWS Lambda Container Images](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html)
- [Amazon ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/what-is-ecr.html)
- [Chalice Framework](https://aws.github.io/chalice/)

## 체크리스트

### 최초 설정
- [ ] ECR 리포지토리 생성
- [ ] Docker 이미지 빌드 및 푸시
- [ ] Lambda 함수 생성 (Container)
- [ ] 환경변수 설정
- [ ] API Gateway 연결
- [ ] 테스트

### 일반 배포
- [ ] 코드 변경
- [ ] Git 커밋 & 푸시
- [ ] GitHub Actions 확인
- [ ] Lambda 함수 동작 확인
- [ ] API 엔드포인트 테스트

## FAQ

### Q: Chalice는 더 이상 사용하지 않나요?
**A:** Chalice **프레임워크**는 그대로 사용합니다. `app.py`의 Chalice app을 Container에서 실행하는 것입니다.

### Q: 기존 API Gateway는?
**A:** 그대로 사용합니다. Lambda 함수만 Container로 전환하고, API Gateway Integration을 업데이트합니다.

### Q: 배포 시간은?
**A:** 첫 배포: ~5분, 이후: ~2-3분 (이미지 캐싱 활용)

### Q: 롤백은?
**A:** 이전 이미지로 Lambda 업데이트:
```bash
aws lambda update-function-code \
  --function-name shuking-prod \
  --image-uri <account>.dkr.ecr.ap-northeast-2.amazonaws.com/shuking-lambda:<previous-tag>
```

### Q: 콜드 스타트는?
**A:** Container Image는 Zip보다 약간 느릴 수 있지만 (1-2초), 큰 차이는 없습니다.

