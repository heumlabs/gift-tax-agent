#!/bin/bash

# IAM 사용자에게 Secrets Manager 접근 권한을 추가하는 스크립트

set -e

echo "========================================="
echo "🔐 IAM Secrets Manager 권한 추가"
echo "========================================="
echo ""

# IAM 사용자 이름 입력
if [ -z "$1" ]; then
    echo "사용법: $0 <IAM-USER-NAME>"
    echo ""
    echo "예시:"
    echo "  $0 github-actions-user"
    echo ""
    echo "💡 현재 AWS 계정의 IAM 사용자 목록:"
    aws iam list-users --query 'Users[*].[UserName]' --output table
    exit 1
fi

IAM_USER_NAME=$1
POLICY_NAME="SecretsManagerAccessPolicy"
POLICY_FILE="$(dirname "$0")/iam-policy-secretsmanager.json"

# 정책 파일 확인
if [ ! -f "$POLICY_FILE" ]; then
    echo "❌ 정책 파일을 찾을 수 없습니다: $POLICY_FILE"
    exit 1
fi

echo "IAM 사용자: $IAM_USER_NAME"
echo "정책 이름: $POLICY_NAME"
echo ""

# AWS 자격증명 확인
echo "1. AWS 자격증명 확인 중..."
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS 자격증명이 설정되지 않았습니다."
    exit 1
fi
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "✅ AWS Account: $ACCOUNT_ID"

# IAM 사용자 존재 확인
echo ""
echo "2. IAM 사용자 확인 중..."
if ! aws iam get-user --user-name "$IAM_USER_NAME" > /dev/null 2>&1; then
    echo "❌ IAM 사용자를 찾을 수 없습니다: $IAM_USER_NAME"
    exit 1
fi
echo "✅ IAM 사용자 확인 완료"

# 기존 정책 확인
echo ""
echo "3. 기존 정책 확인 중..."
if aws iam get-user-policy --user-name "$IAM_USER_NAME" --policy-name "$POLICY_NAME" > /dev/null 2>&1; then
    echo "⚠️  동일한 이름의 정책이 이미 존재합니다."
    echo "기존 정책을 업데이트하시겠습니까? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "취소되었습니다."
        exit 0
    fi
fi

# 정책 추가
echo ""
echo "4. 정책 추가 중..."
aws iam put-user-policy \
    --user-name "$IAM_USER_NAME" \
    --policy-name "$POLICY_NAME" \
    --policy-document file://"$POLICY_FILE"

echo "✅ 정책 추가 완료"

# 정책 확인
echo ""
echo "5. 추가된 정책 확인..."
aws iam get-user-policy \
    --user-name "$IAM_USER_NAME" \
    --policy-name "$POLICY_NAME" \
    --query 'PolicyDocument.Statement[0]' \
    --output table

echo ""
echo "========================================="
echo "✅ 완료!"
echo "========================================="
echo ""
echo "📋 다음 단계:"
echo "1. GitHub Actions Secrets 확인:"
echo "   - AWS_ACCESS_KEY_ID"
echo "   - AWS_SECRET_ACCESS_KEY"
echo ""
echo "2. 권한 테스트:"
echo "   aws secretsmanager get-secret-value \\"
echo "     --secret-id arn:aws:secretsmanager:ap-northeast-2:862108802423:secret:shuking-QbyWZz \\"
echo "     --region ap-northeast-2"
echo ""
echo "========================================="

