#!/bin/bash

# Chalice 배포 패키지 크기 분석 스크립트

echo "========================================="
echo "Chalice 패키지 크기 분석"
echo "========================================="
echo ""

# 가상환경 활성화 (필요시)
if [ -d "../.venv" ]; then
    source ../.venv/bin/activate
fi

# 임시 디렉토리 생성
TEMP_DIR=$(mktemp -d)
echo "임시 디렉토리: $TEMP_DIR"

# requirements 설치
echo "1. 의존성 설치 중..."
pip install -q -r requirements.txt -t "$TEMP_DIR" 2>/dev/null

# 크기 분석
echo ""
echo "2. 패키지별 크기 분석:"
echo "----------------------------------------"
du -sh "$TEMP_DIR"/* | sort -hr | head -20

echo ""
echo "3. 전체 크기:"
TOTAL_SIZE=$(du -sh "$TEMP_DIR" | cut -f1)
echo "총 크기: $TOTAL_SIZE"

echo ""
echo "4. .dist-info 및 불필요한 파일 제거 후:"
find "$TEMP_DIR" -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null
find "$TEMP_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find "$TEMP_DIR" -type d -name "tests" -exec rm -rf {} + 2>/dev/null
find "$TEMP_DIR" -type f -name "*.pyc" -delete 2>/dev/null
find "$TEMP_DIR" -type f -name "*.pyo" -delete 2>/dev/null
find "$TEMP_DIR" -type f -name "*.so" -delete 2>/dev/null

CLEANED_SIZE=$(du -sh "$TEMP_DIR" | cut -f1)
echo "정리 후 크기: $CLEANED_SIZE"

# 정리
rm -rf "$TEMP_DIR"

echo ""
echo "========================================="
echo "Lambda 제한: 50MB (직접), 250MB (S3 경유)"
echo "========================================="

