# Chalice Configuration (DEPRECATED)

⚠️ **이 디렉토리는 더 이상 사용되지 않습니다.**

## 배경

이전에는 Chalice CLI (`chalice deploy`)를 사용하여 배포했지만, 
Lambda Layer 크기 제한(50MB) 문제로 **Lambda Container Image**로 전환했습니다.

## 현재 배포 방식

### Lambda Container Image
- **Dockerfile**: `backend/Dockerfile`
- **Handler**: `lambda_handler.handler`
- **ECR Repository**: `shuking-lambda`
- **Lambda Function**: `shuking-prod`

### 배포 프로세스
```bash
# 로컬 배포
cd backend
./.scripts/migrate-to-container.sh  # 최초 1회
./.scripts/update-lambda-env.sh     # 환경변수 업데이트

# GitHub Actions
# main 브랜치에 푸시하면 자동으로:
# 1. Docker 이미지 빌드
# 2. ECR에 푸시
# 3. Lambda 함수 업데이트
```

## Chalice App 유지

Chalice **프레임워크**는 그대로 사용합니다:
- `app.py`: Chalice app 정의
- Lambda Handler로 wrapping하여 실행

## 참고

- Chalice의 `automatic_layer`는 50MB 제한 문제를 해결하지 못함
- Container Image는 10GB까지 지원
- API Gateway는 기존 Chalice가 생성한 것을 그대로 사용

