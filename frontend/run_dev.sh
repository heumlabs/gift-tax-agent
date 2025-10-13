#!/bin/bash

# 스크립트 실행 위치를 frontend 디렉토리로 설정
cd "$(dirname "$0")"

echo "🚀 슈킹 프론트엔드 개발 서버를 시작합니다..."

# .env 파일 확인
if [ ! -f .env ]; then
    echo "⚠️  .env 파일이 없습니다."
    echo ".env.example을 복사하여 .env 파일을 생성하세요:"
    echo "  cp .env.example .env"
    exit 1
fi

# node_modules 확인
if [ ! -d "node_modules" ]; then
    echo "📦 의존성을 설치합니다..."
    npm install
fi

# Vite 개발 서버 실행
echo "✅ Vite 개발 서버를 시작합니다..."
npm run dev

