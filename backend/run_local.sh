#!/bin/bash

# 스크립트 실행 위치를 backend 디렉토리로 설정
cd "$(dirname "$0")"

echo "🚀 슈킹 백엔드 서버를 시작합니다..."

# 가상환경 활성화 확인
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  가상환경이 활성화되지 않았습니다."
    echo "다음 명령어로 가상환경을 활성화하세요:"
    echo "  source venv/bin/activate"
    exit 1
fi

# .env 파일 확인
if [ ! -f .env ]; then
    echo "⚠️  .env 파일이 없습니다."
    echo ".env.example을 복사하여 .env 파일을 생성하세요:"
    echo "  cp .env.example .env"
    exit 1
fi

# Chalice 로컬 서버 실행
echo "✅ Chalice 로컬 서버를 포트 8000에서 시작합니다..."
chalice local --port 8000

