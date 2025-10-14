#!/bin/bash

# AWS Credentials 검증 스크립트
# 사용법: 
#   export AWS_ACCESS_KEY_ID="your-key"
#   export AWS_SECRET_ACCESS_KEY="your-secret"
#   export AWS_DEFAULT_REGION="ap-northeast-2"
#   ./test-aws-credentials.sh

echo "========================================="
echo "AWS Credentials 검증 시작"
echo "========================================="
echo ""

# 1. STS로 기본 인증 확인
echo "1. 기본 인증 확인 (STS Get Caller Identity)..."
if aws sts get-caller-identity > /dev/null 2>&1; then
    echo "✅ 인증 성공!"
    aws sts get-caller-identity
else
    echo "❌ 인증 실패! AWS credentials를 확인해주세요."
    exit 1
fi
echo ""

# 2. S3 권한 확인
echo "2. S3 권한 확인..."
if aws s3 ls > /dev/null 2>&1; then
    echo "✅ S3 접근 가능!"
    echo "버킷 목록:"
    aws s3 ls
else
    echo "⚠️  S3 접근 권한 없음"
fi
echo ""

# 3. 프로젝트 S3 버킷 확인
echo "3. 프로젝트 S3 버킷 확인 (shuking.tax)..."
if aws s3 ls s3://shuking.tax/ > /dev/null 2>&1; then
    echo "✅ shuking.tax 버킷 접근 가능!"
else
    echo "⚠️  shuking.tax 버킷 접근 불가 (버킷이 없거나 권한 없음)"
fi
echo ""

# 4. CloudFront 권한 확인
echo "4. CloudFront 권한 확인..."
if aws cloudfront list-distributions > /dev/null 2>&1; then
    echo "✅ CloudFront 접근 가능!"
    echo "배포 목록:"
    aws cloudfront list-distributions --query 'DistributionList.Items[*].[Id,DomainName,Status]' --output table
else
    echo "⚠️  CloudFront 접근 권한 없음"
fi
echo ""

# 5. 프로젝트 CloudFront 배포 확인
echo "5. 프로젝트 CloudFront 배포 확인 (E31QVR9HFDDSUI)..."
if aws cloudfront get-distribution --id E31QVR9HFDDSUI > /dev/null 2>&1; then
    echo "✅ CloudFront 배포 E31QVR9HFDDSUI 접근 가능!"
    aws cloudfront get-distribution --id E31QVR9HFDDSUI --query 'Distribution.[Id,DomainName,Status]' --output table
else
    echo "⚠️  CloudFront 배포 E31QVR9HFDDSUI 접근 불가"
fi
echo ""

echo "========================================="
echo "검증 완료!"
echo "========================================="

