#!/bin/bash

# 모든 Lambda Layer를 한 번에 생성하는 스크립트

set -e

echo "========================================="
echo "🚀 모든 Lambda Layer 생성 시작"
echo "========================================="
echo ""

# AWS 자격증명 확인
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS 자격증명이 설정되지 않았습니다."
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=${AWS_DEFAULT_REGION:-ap-northeast-2}

echo "AWS Account: $ACCOUNT_ID"
echo "Region: $REGION"
echo ""

# Layer 생성
LAYERS=(
    "shuking-ai-layer:requirements-ai.txt"
    "shuking-db-layer:requirements-db.txt"
    "shuking-utils-layer:requirements-utils.txt"
)

LAYER_ARNS=()

for layer_info in "${LAYERS[@]}"; do
    IFS=':' read -r layer_name req_file <<< "$layer_info"
    
    echo ""
    echo "========================================="
    echo "Creating: $layer_name"
    echo "========================================="
    
    ./create-layer.sh "$layer_name" "$req_file"
    
    # ARN 저장
    VERSION=$(aws lambda list-layer-versions \
        --layer-name "$layer_name" \
        --region "$REGION" \
        --query 'LayerVersions[0].Version' \
        --output text)
    
    ARN="arn:aws:lambda:${REGION}:${ACCOUNT_ID}:layer:${layer_name}:${VERSION}"
    LAYER_ARNS+=("$ARN")
done

echo ""
echo "========================================="
echo "✅ 모든 Layer 생성 완료!"
echo "========================================="
echo ""
echo "📋 생성된 Layer ARN 목록:"
echo ""

for arn in "${LAYER_ARNS[@]}"; do
    echo "  - $arn"
done

echo ""
echo "📝 .chalice/config.json 업데이트 내용:"
echo ""
echo "  \"layers\": ["
echo "    \"arn:aws:lambda:ap-northeast-2:862108802423:layer:numpy-py312:1\","
for arn in "${LAYER_ARNS[@]}"; do
    echo "    \"$arn\","
done | sed '$ s/,$//'
echo "  ]"
echo ""

echo "🔄 requirements.txt를 requirements-app.txt로 변경하세요:"
echo "  mv requirements.txt requirements.txt.backup"
echo "  cp requirements-app.txt requirements.txt"
echo ""
echo "========================================="

