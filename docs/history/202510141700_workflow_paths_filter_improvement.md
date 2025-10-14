# 작업 이력: 202510141700_workflow_paths_filter_improvement

## 작업 요약
GitHub Actions 배포 워크플로우의 변경사항 감지 로직을 `dorny/paths-filter` 액션을 사용하여 안정적으로 개선하고, CloudFront invalidation을 AWS CLI로 간소화

## 변경 사항
- 기존의 불안정한 `github.event.head_commit.modified/added` 조건문 제거
- 새로운 `changes` job 추가: `dorny/paths-filter@v3` 액션을 사용하여 변경된 경로 감지
- `deploy-backend` job이 `changes` job의 `backend` 출력을 확인하도록 수정
- `deploy-frontend` job이 `changes` job의 `frontend` 출력을 확인하도록 수정
- job 간 의존성 설정: `deploy-backend`와 `deploy-frontend`가 `changes` job을 필요로 함
- CloudFront invalidation을 `chetan/invalidate-cloudfront-action@v2` 대신 AWS CLI로 직접 실행하도록 변경
- 워크플로우 파일(`.github/workflows/deploy.yml`) 변경 시 backend와 frontend 모두 재배포하도록 설정

## 변경 전 문제점
- `github.event.head_commit.modified/added`는 마지막 커밋만 확인
- 여러 커밋이 동시에 푸시되거나 머지될 경우 중간 커밋의 변경사항을 놓칠 수 있음
- 이로 인해 필요한 배포가 실행되지 않을 위험 존재

## 변경 후 개선사항
- `dorny/paths-filter` 액션이 푸시된 모든 커밋의 변경사항을 정확하게 감지
- 변경사항 감지 로직이 명확하고 신뢰성 있게 개선
- job 간 의존성이 명시적으로 정의되어 워크플로우 실행 순서가 보장됨
- CloudFront invalidation을 AWS CLI로 직접 실행하여 외부 액션 의존성 제거 및 코드 간소화

## 영향 범위
- `.github/workflows/deploy.yml` 파일 수정
- 배포 워크플로우의 변경 감지 로직 개선
- backend와 frontend 배포 job의 실행 조건 변경

## 테스트
- 워크플로우 파일 구문 검증 필요
- main 브랜치에 머지 후 실제 배포 시나리오 테스트 권장:
  - backend만 변경된 커밋 푸시
  - frontend만 변경된 커밋 푸시
  - 여러 커밋을 동시에 푸시 (backend + frontend 변경 포함)

## 기타
- `dorny/paths-filter@v3` 액션 사용
- workflow-level의 `on.push.paths` 필터는 유지하여 이중 보호

