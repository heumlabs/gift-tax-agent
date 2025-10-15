#!/bin/bash
# Lambda 환경 변수 초기 설정 스크립트
# 
# 사용법: ./setup-lambda-env.sh
# 
# 이 스크립트는 Lambda 함수 생성 후 최초 1회만 실행하면 됩니다.
# 코드 배포 시마다 실행할 필요가 없으며, 환경 변수 변경이 필요할 때만 실행합니다.

set -e

AWS_REGION="ap-northeast-2"
LAMBDA_FUNCTION_NAME="shuking-prod"
SECRET_ARN="arn:aws:secretsmanager:ap-northeast-2:862108802423:secret:shuking-QbyWZz"

echo "🔐 Secrets Manager에서 환경 변수 가져오는 중..."

# Secrets Manager에서 모든 환경 변수 가져오기
SECRET_JSON=$(aws secretsmanager get-secret-value \
  --secret-id "$SECRET_ARN" \
  --query SecretString \
  --output text \
  --region "$AWS_REGION")

# 개별 환경 변수 추출
GOOGLE_API_KEY=$(echo "$SECRET_JSON" | jq -r '.GOOGLE_API_KEY')
DB_HOST=$(echo "$SECRET_JSON" | jq -r '.DB_HOST')
DB_USER=$(echo "$SECRET_JSON" | jq -r '.DB_USER')
DB_PASS=$(echo "$SECRET_JSON" | jq -r '.DB_PASS')
DB_NAME=$(echo "$SECRET_JSON" | jq -r '.DB_NAME')
APP_STAGE=$(echo "$SECRET_JSON" | jq -r '.APP_STAGE')

echo "📝 Lambda 환경 변수 업데이트 중..."

# Lambda 환경 변수 업데이트
aws lambda update-function-configuration \
  --function-name "$LAMBDA_FUNCTION_NAME" \
  --environment "Variables={
    ENVIRONMENT=prod,
    APP_STAGE=$APP_STAGE,
    GOOGLE_API_KEY=$GOOGLE_API_KEY,
    DB_HOST=$DB_HOST,
    DB_USER=$DB_USER,
    DB_PASS=$DB_PASS,
    DB_NAME=$DB_NAME,
    CORS_ALLOW_ORIGIN=https://d49mat9gykfn6.cloudfront.net
  }" \
  --region "$AWS_REGION" > /dev/null

echo "⏳ 설정 업데이트 완료 대기 중..."

# 설정 업데이트 완료 대기
aws lambda wait function-updated \
  --function-name "$LAMBDA_FUNCTION_NAME" \
  --region "$AWS_REGION"

echo "✅ Lambda 환경 변수가 성공적으로 업데이트되었습니다!"
echo ""
echo "설정된 환경 변수:"
echo "  - ENVIRONMENT: prod"
echo "  - APP_STAGE: $APP_STAGE"
echo "  - GOOGLE_API_KEY: ${GOOGLE_API_KEY:0:20}..." 
echo "  - DB_HOST: $DB_HOST"
echo "  - DB_NAME: $DB_NAME"
echo "  - DB_USER: $DB_USER"
echo "  - CORS_ALLOW_ORIGIN: https://d49mat9gykfn6.cloudfront.net"
