# 작업 이력: 202510141643_infra_deployment_updates

## 작업 요약
배포 워크플로우 최적화, 서비스 이름 철자 수정, 인프라 철거 가이드 추가

## 변경 사항
- `.github/workflows/deploy.yml` 생성: 백엔드와 프론트엔드 배포를 하나의 워크플로우에서 병렬 실행
  - `deploy-backend.yml` 및 `deploy-frontend.yml` 통합
  - 두 job이 병렬로 실행되어 배포 시간 단축
  - 변경된 경로에 따라 조건부 실행으로 최적화

- 서비스 이름 철자 수정: `syuking` → `shuking`
  - `docs/PRD.md`: 제목 수정
  - `backend/app.py`: app_name 및 API 메시지 수정
  - `SETUP.md`: 데이터베이스 이름 수정
  - `README.md`: 제목 및 데이터베이스 설정 수정

- 데이터베이스 이름 간소화
  - `shuking_db` → `shuking`
  - `shuking_user` → `shuking`

- `docs/teardown-guide.md` 생성: AWS 인프라 철거 가이드
  - CloudFront, S3, Lambda, Lambda Layer, IAM 등 모든 리소스 제거 절차 포함
  - AWS Console 방식 제공 (CLI 방식 제거)
  - `alfred-agent` stage DB 내 `shuking` 데이터베이스 제거 방법 명시
  - 철거 완료 확인 체크리스트 및 문제 해결 가이드 포함

- 프로젝트 설정 파일 업데이트
  - `backend/.chalice/config.json`: dev 환경 제거 (prod만 유지)
  - `backend/.python-version` 추가
  - `backend/.gitignore`, `frontend/.gitignore` 업데이트
  - `backend/requirements.txt` 의존성 추가

## 영향 범위
- GitHub Actions 워크플로우: 배포 프로세스 변경 (병렬화)
- 서비스 전체: 이름 철자 일관성 확보
- 데이터베이스: 이름 간소화로 설정 단순화
- 운영: 인프라 철거 시 참고할 가이드 문서 확보

## 테스트
- GitHub Actions 워크플로우 구문 검증 완료
- 모든 문서 파일 철자 수정 확인
- 히스토리 파일 새로운 구조에 맞게 작성 완료

## 기타
- feature/infra-deployment-updates 브랜치로 작업
- 5개의 커밋으로 논리적 단위별 분리
- main 브랜치 최신 변경사항 merge 완료
- GitHub에 push 완료

