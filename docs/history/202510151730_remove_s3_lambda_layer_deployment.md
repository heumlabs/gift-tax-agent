# 작업 이력: 202510151730_remove_s3_lambda_layer_deployment

## 작업 요약
Lambda Layer를 수동으로 생성하여 config.json에 직접 설정하므로, 배포 워크플로우에서 S3 기반 Layer 자동 업로드 로직 제거

## 변경 사항
- `.github/workflows/deploy.yml` - S3 Lambda Layer 배포 관련 코드 제거
  - `AWS_LAMBDA_LAYER_S3_BUCKET` 환경변수 제거
  - S3 버킷 생성 명령어 제거 (`aws s3 mb`)
  - Chalice 배포 명령어 단순화

- `docs/add-iam-policy.sh` 삭제
  - IAM 정책 자동 추가 스크립트 제거
  
- `docs/iam-policy-secretsmanager.json` 삭제
  - IAM 정책 JSON 파일 제거

## 변경 전
```yaml
- name: Deploy to production
  env:
    AWS_LAMBDA_LAYER_S3_BUCKET: shuking-lambda-deployment
  run: |
    # S3 버킷 생성 (없는 경우)
    aws s3 mb s3://shuking-lambda-deployment --region ap-northeast-2 2>/dev/null || true
    # Chalice 배포 (S3를 통해)
    chalice deploy --stage prod --connection-timeout 300
```

## 변경 후
```yaml
- name: Deploy to production
  run: |
    chalice deploy --stage prod --connection-timeout 300
```

## 배경

Lambda Layer는 다음과 같이 수동으로 관리:
1. `.scripts/create-layer.sh` 스크립트로 Layer 생성
2. 생성된 Layer ARN을 `.chalice/config.json`에 직접 설정
3. Chalice가 기존 Layer를 참조하여 배포

### Lambda Layer 구성
- `shuking-ai-layer` - google-generativeai (~40MB)
- `shuking-db-layer` - psycopg2, SQLAlchemy, pgvector (~15MB)
- `shuking-utils-layer` - pydantic, requests 등 (~10MB)
- `numpy-py312` - numpy (외부 Layer)

## 영향 범위
- `.github/workflows/deploy.yml` - 배포 워크플로우 간소화
- 배포 시간 단축 (S3 버킷 생성 과정 제거)
- Lambda Layer는 `.chalice/config.json`의 설정을 따름

## 배포 프로세스

### 현재 배포 프로세스
1. AWS credentials 설정
2. Secrets Manager에서 환경변수 가져오기
3. Chalice 배포 (기존 Layer 참조)

### Lambda Layer 업데이트 시
```bash
# Layer 재생성 (필요 시)
cd backend
./.scripts/create-layer.sh shuking-ai-layer requirements-ai.txt

# 생성된 ARN을 .chalice/config.json에 업데이트
# 배포
chalice deploy --stage prod
```

## 이점
- ✅ 배포 워크플로우 간소화
- ✅ S3 버킷 관리 불필요
- ✅ Layer 재사용으로 배포 속도 향상
- ✅ 명시적 Layer 버전 관리
- ✅ Layer 변경 시 수동 제어 가능

## 관련 문서
- `backend/.scripts/create-layer.sh` - Layer 생성 스크립트
- `backend/.scripts/create-all-layers.sh` - 전체 Layer 생성
- `backend/.chalice/config.json` - Layer ARN 설정 파일

## 테스트
- [x] 로컬에서 Layer ARN 확인
- [x] config.json에 Layer 설정 완료
- [x] 배포 워크플로우 단순화
- [ ] main 브랜치 머지 후 실제 배포 확인

## 기타
- Lambda Layer는 변경 빈도가 낮으므로 수동 관리가 효율적
- Chalice의 `automatic_layer: true` 설정은 유지하되, 수동 Layer를 우선 사용

