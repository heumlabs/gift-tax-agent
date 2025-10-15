# 간소화된 배포 가이드

## 개요

Chalice의 `automatic_layer=true` 설정과 S3를 활용한 심플한 배포 시스템

## 핵심 원리

### Chalice가 자동으로 처리
```
requirements.txt → Chalice 분석 → Layer 자동 생성 → S3 업로드 → Lambda 배포
```

### 250MB 제한?
- Chalice의 automatic layer가 의존성을 자동으로 분리
- 큰 패키지는 자동으로 S3 경유
- **개발자는 신경 쓸 필요 없음!**

## 배포 방법

### 로컬 배포
```bash
cd backend

# 환경변수 로드
./.scripts/fetch-secrets.sh

# 배포 (Chalice가 알아서 처리)
chalice deploy --stage prod --s3-bucket shuking-lambda-deployment
```

### 자동 배포 (GitHub Actions)
```bash
# main 브랜치에 푸시하면 자동 배포
git add .
git commit -m "Update code"
git push origin main
```

## 의존성 관리

### requirements.txt
```txt
# Chalice framework
chalice
pydantic-settings

# AI/ML
google-generativeai==0.8.3

# Database
psycopg2-binary==2.9.9
SQLAlchemy==2.0.32
pgvector==0.3.6

# Utilities
pydantic==2.9.2
requests==2.32.4
python-dateutil==2.9.0.post0
python-dotenv==1.0.1

# Numpy
numpy==1.26.4
```

**새 패키지 추가:**
1. `requirements.txt`에 추가
2. Git 푸시
3. 끝! (Chalice가 자동 처리)

## 설정 파일

### .chalice/config.json
```json
{
  "version": "2.0",
  "app_name": "shuking",
  "automatic_layer": true,  // 핵심!
  "stages": {
    "prod": {
      "use_container": false,
      "manage_iam_role": false,
      "iam_role_arn": "arn:aws:iam::862108802423:role/shuking-role",
      "api_gateway_stage": "api",
      "lambda_memory_size": 512,
      "lambda_timeout": 60,
      "environment_variables": {
        "ENVIRONMENT": "prod",
        "DATABASE_URL": "${DATABASE_URL}",
        "GEMINI_API_KEY": "${GEMINI_API_KEY}",
        "CORS_ALLOW_ORIGIN": "https://d49mat9gykfn6.cloudfront.net"
      }
    }
  }
}
```

**핵심 설정:**
- `automatic_layer: true` - Chalice가 자동으로 Layer 관리
- `layers` 설정 불필요 - 자동 생성됨

## GitHub Actions 워크플로우

```yaml
deploy-backend:
  env:
    S3_BUCKET: shuking-lambda-deployment
  steps:
    - Setup Python
    - Install dependencies (pip install -r requirements.txt)
    - Fetch secrets
    - chalice deploy --s3-bucket ${S3_BUCKET}  # 끝!
```

**간단한 3단계:**
1. 의존성 설치
2. Secrets 로드
3. Chalice 배포

## S3 버킷

### 버킷 이름
`shuking-lambda-deployment`

### 자동 생성 항목
```
s3://shuking-lambda-deployment/
├── deployments/
│   └── <deployment-package>.zip  # Chalice 앱
└── layers/  # Chalice가 자동 생성한 Layer
    └── <layer-package>.zip
```

## 트러블슈팅

### 배포 실패 시

#### 1. S3 버킷 생성
```bash
aws s3 mb s3://shuking-lambda-deployment --region ap-northeast-2
```

#### 2. IAM 권한 확인
필요한 권한:
- `s3:CreateBucket`
- `s3:PutObject`
- `s3:GetObject`
- `lambda:CreateFunction`
- `lambda:UpdateFunctionCode`
- `lambda:UpdateFunctionConfiguration`

#### 3. 로그 확인
```bash
chalice logs --stage prod
```

### 250MB 초과 시

Chalice의 automatic layer로도 안 되면:

#### Option 1: 불필요한 패키지 제거
```txt
# requirements.txt에서 안 쓰는 패키지 제거
```

#### Option 2: Docker Container (향후)
```dockerfile
FROM public.ecr.aws/lambda/python:3.12
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["app.handler"]
```

## 모니터링

### 배포 크기 확인
```bash
# Chalice 빌드 디렉토리
ls -lh .chalice/deployments/
```

### Lambda 함수 확인
```bash
# 함수 정보
aws lambda get-function --function-name shuking-prod --region ap-northeast-2

# Layer 확인
aws lambda get-function-configuration \
  --function-name shuking-prod \
  --region ap-northeast-2 \
  --query 'Layers'
```

## 이전 방식과 비교

### 이전 (복잡)
```
1. Layer 별도 빌드
2. S3 수동 업로드
3. Layer ARN 확인
4. config.json 수동 업데이트
5. Chalice 배포
```

### 현재 (간단)
```
1. chalice deploy --s3-bucket shuking-lambda-deployment
```

## FAQ

### Q: automatic_layer가 뭔가요?
**A:** Chalice가 requirements.txt를 분석해서 자동으로 Lambda Layer를 생성하는 기능입니다.

### Q: Layer 크기 제한은?
**A:** Chalice가 자동으로 분리하므로 일반적으로 문제없습니다. 전체 250MB 제한만 주의하면 됩니다.

### Q: 배포가 느린 것 같아요
**A:** 첫 배포는 느릴 수 있지만, 이후엔 변경된 부분만 업데이트되어 빠릅니다.

### Q: Layer를 수동으로 관리하고 싶어요
**A:** `automatic_layer: false`로 설정하고 `layers` 배열에 ARN을 직접 지정하면 됩니다.

### Q: S3 비용은?
**A:** 매우 저렴합니다 (월 $1 미만). 배포 패키지는 보통 100MB 이하입니다.

## 결론

**핵심:**
- `automatic_layer: true` - Chalice가 알아서
- `--s3-bucket` - 큰 패키지 자동 업로드
- **개발자는 코드 작성에만 집중!**

간단하고 강력한 배포 시스템입니다. 🚀

