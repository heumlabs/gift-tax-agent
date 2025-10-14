# 작업 이력

## 2025-10-14 - GitHub Actions 워크플로우 추가

- `.github/workflows/on-push-feature-branch.yml` 생성 (feature 브랜치 push 시 자동 PR 생성)

## 2025-10-13 - 프로젝트 초기 설정 및 로컬 개발 환경 구축

- `.gitignore`에 `.history/` 제외 항목 추가
- `backend/requirements.txt`에 Python 의존성 패키지 추가 (Chalice, Gemini AI, PostgreSQL 등)
- `backend/app.py`에 CORS 설정 및 헬스체크 엔드포인트 추가
- `backend/.gitignore` 파일 생성 (Python 프로젝트 제외 항목)
- `backend/.chalice/config.json` 생성 (Chalice 환경 설정)
- `backend/run_local.sh` 생성 (백엔드 로컬 실행 스크립트)
- `frontend/.gitignore` 파일 생성 (Node.js 프로젝트 제외 항목)
- `frontend/run_dev.sh` 생성 (프론트엔드 로컬 실행 스크립트)
- `README.md` 생성 (프로젝트 전체 가이드)
- `SETUP.md` 생성 (상세 설치 및 실행 가이드)
- `finish-coding.mdc`에 작업 이력 추가 규칙 추가
