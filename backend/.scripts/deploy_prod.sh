#!/bin/bash

# 프로덕션 배포 스크립트
# backend 디렉토리로 이동 (스크립트는 backend/.scripts/에 위치)
cd "$(dirname "$0")/.."

echo "========================================="
echo "🚀 슈킹 백엔드 프로덕션 배포"
echo "========================================="
echo ""

# AWS 자격증명 확인
echo "1. AWS 자격증명 확인..."
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS 자격증명이 설정되지 않았습니다."
    echo "다음 명령어로 설정하세요:"
    echo "  export AWS_ACCESS_KEY_ID=your-key"
    echo "  export AWS_SECRET_ACCESS_KEY=your-secret"
    echo "  export AWS_DEFAULT_REGION=ap-northeast-2"
    exit 1
fi
echo "✅ AWS 자격증명 확인 완료"

# 가상환경 확인
echo ""
echo "2. 가상환경 확인..."
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -d ".venv" ]; then
        echo "⚙️  가상환경 활성화 중..."
        source .venv/bin/activate
    else
        echo "❌ 가상환경을 찾을 수 없습니다."
        exit 1
    fi
fi
echo "✅ 가상환경 활성화됨: $VIRTUAL_ENV"

# 의존성 설치
echo ""
echo "3. 의존성 설치..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✅ 의존성 설치 완료"

# Secrets Manager에서 환경변수 가져오기
echo ""
echo "4. 환경변수 가져오기..."
if command -v jq &> /dev/null; then
    ./.scripts/fetch-secrets.sh
else
    echo "⚠️  jq가 설치되어 있지 않습니다. jq를 설치하거나 수동으로 .env 파일을 생성하세요."
    echo "   macOS: brew install jq"
    echo "   Ubuntu: sudo apt-get install jq"
    
    # .env 파일이 있는지 확인
    if [ ! -f ".env" ]; then
        echo "❌ .env 파일이 없습니다. 환경변수 설정이 필요합니다."
        exit 1
    else
        echo "⚠️  기존 .env 파일을 사용합니다."
    fi
fi

# S3 버킷 생성 (Lambda 배포용)
echo ""
echo "5. S3 배포 버킷 준비..."
export AWS_LAMBDA_LAYER_S3_BUCKET=shuking-lambda-deployment
aws s3 mb s3://shuking-lambda-deployment --region ap-northeast-2 2>/dev/null || true
echo "✅ S3 버킷 준비 완료: s3://shuking-lambda-deployment"

# Chalice 배포
echo ""
echo "6. Chalice 배포 시작..."
echo "----------------------------------------"
chalice deploy --stage prod --connection-timeout 300

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================="
    echo "✅ 배포 성공!"
    echo "========================================="
else
    echo ""
    echo "========================================="
    echo "❌ 배포 실패"
    echo "========================================="
    exit 1
fi

