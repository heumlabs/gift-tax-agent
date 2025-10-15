#!/bin/bash

# Lambda Layer 생성 스크립트
# 사용법: ./.scripts/create-layer.sh <layer-name> <requirements-file>
# backend 디렉토리로 이동 (스크립트는 backend/.scripts/에 위치)
cd "$(dirname "$0")/.."

set -e

if [ $# -lt 2 ]; then
    echo "사용법: $0 <layer-name> <requirements-file>"
    echo ""
    echo "예시:"
    echo "  $0 shuking-ai-layer requirements-ai.txt"
    echo "  $0 shuking-db-layer requirements-db.txt"
    exit 1
fi

LAYER_NAME=$1
REQ_FILE=$2
REGION=${AWS_DEFAULT_REGION:-ap-northeast-2}
PYTHON_VERSION=python3.12

echo "========================================="
echo "🚀 Lambda Layer 생성: $LAYER_NAME"
echo "========================================="
echo ""

# Requirements 파일 확인
if [ ! -f "$REQ_FILE" ]; then
    echo "❌ Requirements 파일을 찾을 수 없습니다: $REQ_FILE"
    exit 1
fi

echo "📦 Requirements 파일: $REQ_FILE"
cat "$REQ_FILE"
echo ""

# 임시 디렉토리 생성
echo "1. 패키지 설치 중..."
rm -rf python layer-build
mkdir -p python

# 패키지 설치
pip install -q -r "$REQ_FILE" -t python/ --platform manylinux2014_x86_64 --only-binary=:all: --python-version 3.12 || \
pip install -q -r "$REQ_FILE" -t python/

echo "✅ 패키지 설치 완료"

# 불필요한 파일 제거
echo ""
echo "2. 패키지 최적화 중..."
find python -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find python -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find python -type f -name "*.pyc" -delete 2>/dev/null || true
find python -type f -name "*.pyo" -delete 2>/dev/null || true
find python -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find python -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

echo "✅ 최적화 완료"

# 크기 확인
echo ""
echo "3. Layer 크기 확인..."
LAYER_SIZE=$(du -sh python | cut -f1)
echo "Layer 크기: $LAYER_SIZE"

# ZIP 생성
echo ""
echo "4. ZIP 파일 생성 중..."
zip -rq ${LAYER_NAME}.zip python/
ZIP_SIZE=$(du -sh ${LAYER_NAME}.zip | cut -f1)
echo "✅ ZIP 파일 생성 완료: ${LAYER_NAME}.zip ($ZIP_SIZE)"

# AWS에 업로드
echo ""
echo "5. AWS Lambda Layer 게시 중..."
LAYER_VERSION=$(aws lambda publish-layer-version \
    --layer-name ${LAYER_NAME} \
    --description "Auto-generated layer from $REQ_FILE" \
    --zip-file fileb://${LAYER_NAME}.zip \
    --compatible-runtimes ${PYTHON_VERSION} \
    --region ${REGION} \
    --query 'Version' \
    --output text)

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
LAYER_ARN="arn:aws:lambda:${REGION}:${ACCOUNT_ID}:layer:${LAYER_NAME}:${LAYER_VERSION}"

echo "✅ Layer 게시 완료!"
echo ""
echo "========================================="
echo "📋 Layer 정보"
echo "========================================="
echo "Layer ARN: $LAYER_ARN"
echo "Version: $LAYER_VERSION"
echo "Region: $REGION"
echo ""
echo ".chalice/config.json에 다음을 추가하세요:"
echo ""
echo "  \"layers\": ["
echo "    \"$LAYER_ARN\""
echo "  ]"
echo ""

# 정리
echo "6. 임시 파일 정리 중..."
rm -rf python ${LAYER_NAME}.zip
echo "✅ 정리 완료"

echo ""
echo "========================================="
echo "✅ 완료!"
echo "========================================="

