# 작업 이력

## 2025-10-14 - 서비스 이름 철자 수정

- 프로젝트 전체에서 `syuking` → `shuking`으로 철자 수정
  - `docs/PRD.md`: 제목 수정
  - `backend/app.py`: app_name 및 API 메시지 수정
  - `SETUP.md`: 데이터베이스 이름 및 사용자 이름 수정
  - `README.md`: 제목 및 데이터베이스 설정 수정

## 2025-10-14 - 인프라 제거 가이드 추가

- `docs/teardown-guide.md` 생성: 프로젝트 종료 시 AWS 인프라를 완전히 제거하는 상세 가이드
  - CloudFront, S3, Lambda, Lambda Layer, RDS, IAM 등 모든 리소스 삭제 절차 포함
  - AWS Console 방식과 AWS CLI 방식 모두 제공
  - 의존성 순서를 고려한 단계별 삭제 가이드
  - 철거 완료 확인 체크리스트 및 문제 해결 가이드 포함

## 2025-10-14 - 배포 워크플로우 병렬화

- `.github/workflows/deploy.yml` 생성: 백엔드와 프론트엔드 배포를 하나의 워크플로우에서 병렬 실행하도록 통합
  - `deploy-backend.yml` 및 `deploy-frontend.yml` 삭제 및 통합
  - 두 job이 병렬로 실행되어 배포 시간 단축
  - 각 job은 변경된 경로에 따라 조건부 실행

## 2025-10-14 - 백엔드 아키텍처 문서 업데이트

- `.github/workflows/on-push-feature-branch.yml` 수정: PR 생성 방식을 GitHub CLI에서 peter-evans/create-pull-request 액션으로 변경
- `backend/.chalice/config.json` 수정: dev 환경 설정 제거 (prod 환경만 유지)
- `docs/prd_detail/backend-architecture.md` 업데이트:
  - ORM 라이브러리를 SQLAlchemy + SQLModel 조합으로 명시
  - 브랜치 전략을 `main` 브랜치만 사용하는 것으로 단순화
  - 배포 전략을 feature 브랜치 push → PR 자동 생성 → main 머지 시 자동 배포로 변경

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
