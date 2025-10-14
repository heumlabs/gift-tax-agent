# Lambda 배포 패키지 크기 최적화

## 문제

Chalice 배포 시 다음과 같은 에러 발생:
```
ChaliceDeploymentError: ERROR - While sending your chalice handler code to Lambda to 
publish_layer_version function "shuking-prod-managed-layer", received the 
following error:

An error occurred (RequestEntityTooLargeException) when calling the 
PublishLayerVersion operation: Request must be smaller than 70167211 bytes for
the PublishLayerVersion operation

This is likely because the deployment package is 65.8 MB. Lambda only allows 
deployment packages that are 50.0 MB or less in size.
```

## 원인

`google-generativeai`, `SQLAlchemy`, `psycopg2-binary` 등 대용량 패키지로 인해 배포 패키지가 65.8MB로 증가

## AWS Lambda 크기 제한

- **직접 업로드**: 50MB (압축 후)
- **S3 경유**: 250MB (압축 후) / 250MB (압축 해제 후)
- **Container Image**: 10GB

## 해결 방법

### 1. S3를 통한 배포 (적용됨) ✅

Lambda Layer를 S3를 통해 업로드하도록 설정:

```bash
# 환경변수 설정
export AWS_LAMBDA_LAYER_S3_BUCKET=shuking-lambda-deployment

# S3 버킷 생성 (최초 1회)
aws s3 mb s3://shuking-lambda-deployment --region ap-northeast-2

# 배포
chalice deploy --stage prod
```

#### GitHub Actions에서 자동 적용

`.github/workflows/deploy.yml`에서 자동으로 S3 버킷을 생성하고 사용:

```yaml
- name: Deploy to production
  env:
    AWS_LAMBDA_LAYER_S3_BUCKET: shuking-lambda-deployment
  run: |
    aws s3 mb s3://shuking-lambda-deployment --region ap-northeast-2 2>/dev/null || true
    chalice deploy --stage prod --connection-timeout 300
```

### 2. 불필요한 파일 제외

`.chaliceignore` 파일로 불필요한 파일 제외:
- 테스트 파일
- 문서 파일
- 타입 스텁
- 캐시 파일
- IDE 설정

### 3. Lambda 설정 최적화

`.chalice/config.json`에서 메모리와 타임아웃 설정:

```json
{
  "lambda_memory_size": 512,
  "lambda_timeout": 60
}
```

## 배포 방법

### 로컬에서 배포

```bash
cd backend
./deploy_prod.sh
```

### 패키지 크기 분석

```bash
cd backend
./analyze_package_size.sh
```

## 추가 최적화 옵션

### 옵션 1: Slim 패키지 사용

일부 패키지는 slim 버전 제공:
```
psycopg2-binary → psycopg2 (컴파일 필요)
```

### 옵션 2: Layer 분리

자주 변경되지 않는 패키지는 별도 Layer로 분리:
- numpy (이미 적용됨)
- pandas
- scipy

### 옵션 3: Container Image (향후 고려)

10GB까지 지원하지만 Cold Start가 느릴 수 있음:

```json
{
  "use_container": true
}
```

## 참고

- Chalice 문서: https://aws.github.io/chalice/topics/packaging.html
- Lambda 제한: https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html

