#!/bin/bash

# AWS Secrets Manager에서 환경변수를 가져와 .env 파일을 생성하는 스크립트
# backend 디렉토리로 이동 (스크립트는 backend/.scripts/에 위치)
cd "$(dirname "$0")/.."

set -e

SECRET_ARN="arn:aws:secretsmanager:ap-northeast-2:862108802423:secret:shuking-QbyWZz"
REGION="ap-northeast-2"
ENV_FILE=".env"

echo "========================================="
echo "🔐 AWS Secrets Manager에서 환경변수 가져오기"
echo "========================================="
echo ""

# AWS 자격증명 확인
echo "1. AWS 자격증명 확인 중..."
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS 자격증명이 설정되지 않았습니다."
    echo "다음 환경변수를 설정하세요:"
    echo "  AWS_ACCESS_KEY_ID"
    echo "  AWS_SECRET_ACCESS_KEY"
    echo "  AWS_DEFAULT_REGION"
    exit 1
fi
echo "✅ AWS 자격증명 확인 완료"

# Secret 가져오기
echo ""
echo "2. Secrets Manager에서 secret 가져오는 중..."
echo "Secret ARN: $SECRET_ARN"

SECRET_JSON=$(aws secretsmanager get-secret-value \
    --secret-id "$SECRET_ARN" \
    --region "$REGION" \
    --query 'SecretString' \
    --output text)

if [ -z "$SECRET_JSON" ]; then
    echo "❌ Secret을 가져올 수 없습니다."
    exit 1
fi

echo "✅ Secret 가져오기 완료"

# .env 파일 생성
echo ""
echo "3. .env 파일 생성 중..."

# 기존 .env 파일 백업
if [ -f "$ENV_FILE" ]; then
    BACKUP_FILE="${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "⚠️  기존 .env 파일을 백업합니다: $BACKUP_FILE"
    cp "$ENV_FILE" "$BACKUP_FILE"
fi

# JSON에서 환경변수 추출하여 .env 파일 생성
echo "$SECRET_JSON" | jq -r 'to_entries | .[] | "\(.key)=\(.value)"' > "$ENV_FILE"

if [ $? -eq 0 ] && [ -s "$ENV_FILE" ]; then
    echo "✅ .env 파일 생성 완료: $ENV_FILE"
    echo ""
    echo "📝 생성된 환경변수 목록:"
    echo "----------------------------------------"
    cat "$ENV_FILE" | cut -d'=' -f1 | while read key; do
        echo "  - $key"
    done
else
    echo "❌ .env 파일 생성 실패"
    exit 1
fi

echo ""
echo "========================================="
echo "✅ 완료!"
echo "========================================="
echo ""
echo "💡 생성된 .env 파일은 민감한 정보를 포함하고 있습니다."
echo "   Git에 커밋하지 마세요!"
echo "========================================="

