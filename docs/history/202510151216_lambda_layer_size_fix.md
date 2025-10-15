# 작업 이력: 202510151216_lambda_layer_size_fix

## 작업 요약
Lambda Layer 크기 250MB 초과 오류 해결 - automatic_layer 비활성화 및 레이어 통합 옵션 제공

## 문제 상황

GitHub Actions 배포 중 다음 오류 발생:
```
InvalidParameterValueException: Layers consume more than the available size of 262144000 bytes
```

**원인 분석:**
1. `automatic_layer: true` 설정으로 Chalice가 자동으로 추가 레이어 생성
2. 수동 생성한 4개의 레이어 + 자동 생성 레이어의 합계가 250MB 초과
3. Lambda의 레이어 크기 제한: 250MB (압축 해제 기준)

## 변경 사항

### 1. `.chalice/config.json` 수정
**변경 내용:**
```diff
- "automatic_layer": true,
+ "automatic_layer": false,
```

**효과:**
- Chalice가 자동으로 추가 레이어를 생성하지 않음
- 명시적으로 지정한 4개의 레이어만 사용
- 레이어 크기를 수동으로 제어 가능

### 2. `requirements-all.txt` 생성
**목적:** 4개의 개별 레이어를 1개의 통합 레이어로 합칠 수 있는 옵션 제공

**포함 패키지:**
- AI/ML: google-generativeai
- Database: psycopg2-binary, SQLAlchemy, pgvector
- Utilities: pydantic, requests, python-dateutil, python-dotenv
- Numpy: numpy

**사용 방법:**
```bash
cd backend
./.scripts/create-layer.sh shuking-deps-layer requirements-all.txt
```

### 3. `docs/lambda-layer-optimization.md` 생성
**내용:**
- Lambda Layer 크기 제한 설명
- 3가지 해결 방법 제시:
  1. automatic_layer 비활성화 (✅ 즉시 적용)
  2. 레이어 통합 (선택적 적용)
  3. 의존성 최적화
- 크기 확인 방법 및 트러블슈팅 가이드
- 장기적 최적화 방안 (함수 분리, EFS, Docker Container)

## 영향 범위

### 즉시 영향
- ✅ `.chalice/config.json` - 배포 설정 변경
- ✅ GitHub Actions 배포 프로세스 - 크기 오류 해결 예상

### 선택적 적용
- `requirements-all.txt` - 레이어 통합 시 사용
- Lambda Layer ARN - 통합 레이어 생성 시 config.json 업데이트 필요

## 배포 전략

### 1단계: automatic_layer 비활성화 (현재)
```bash
# 변경사항 커밋 및 푸시
git add .chalice/config.json
git commit -m "fix: disable automatic_layer to prevent size limit"
git push origin feature/workflow-improvements
```

### 2단계: 테스트 배포
- main 브랜치로 머지 후 GitHub Actions 배포 확인
- 여전히 크기 초과 시 → 3단계 진행

### 3단계: 레이어 통합 (필요시)
```bash
# 로컬에서 통합 레이어 생성
cd backend
./.scripts/create-layer.sh shuking-deps-layer requirements-all.txt

# 생성된 ARN을 config.json에 업데이트
# 예: arn:aws:lambda:ap-northeast-2:862108802423:layer:shuking-deps-layer:1

# 재배포
chalice deploy --stage prod
```

## Lambda 크기 제한 정리

| 항목 | 제한 |
|------|------|
| 배포 패키지 (압축) | 50MB |
| 배포 패키지 (압축 해제) | 250MB |
| 레이어 포함 전체 (압축 해제) | **250MB** ⚠️ |
| 최대 레이어 개수 | 5개 |
| Container Image | 10GB |

## 현재 레이어 구성

### 개별 레이어 (4개)
```json
"layers": [
    "arn:aws:lambda:ap-northeast-2:862108802423:layer:shuking-numpy:1",
    "arn:aws:lambda:ap-northeast-2:862108802423:layer:shuking-ai-layer:1",
    "arn:aws:lambda:ap-northeast-2:862108802423:layer:shuking-db-layer:1",
    "arn:aws:lambda:ap-northeast-2:862108802423:layer:shuking-utils-layer:1"
]
```

**예상 크기:**
- numpy: ~20MB
- ai-layer: ~40MB
- db-layer: ~15MB
- utils-layer: ~10MB
- **합계: ~85MB** (의존성 포함 시 더 클 수 있음)

### 통합 레이어 (1개) - 선택사항
```json
"layers": [
    "arn:aws:lambda:ap-northeast-2:862108802423:layer:shuking-deps-layer:1"
]
```

**장점:**
- 단일 레이어로 관리 단순화
- 버전 관리 용이
- 배포 시간 단축

## 테스트

### 로컬 테스트
- [x] `automatic_layer: false` 설정 변경
- [x] `requirements-all.txt` 생성 및 검증
- [x] 최적화 가이드 문서 작성

### 배포 테스트 (예정)
- [ ] feature 브랜치에서 커밋 및 푸시
- [ ] main 브랜치 머지
- [ ] GitHub Actions 배포 성공 확인
- [ ] API 엔드포인트 동작 확인

## 추가 최적화 옵션 (장기)

### Option 1: 함수 분리
```
Lambda 1: API Gateway Handler (가볍게)
Lambda 2: AI Processing (무거운 작업)
```

### Option 2: EFS 마운트
```python
# 대용량 라이브러리를 EFS에 저장
import sys
sys.path.insert(0, '/mnt/efs/python-packages')
```

### Option 3: Container Image
```dockerfile
FROM public.ecr.aws/lambda/python:3.12
COPY requirements-all.txt .
RUN pip install -r requirements-all.txt
COPY . .
CMD ["app.handler"]
```

**Container Image 장점:**
- 크기 제한: 10GB (250MB → 10GB)
- 완전한 파일 시스템 제어
- 복잡한 의존성 관리 용이

## 기타

### 관련 명령어

```bash
# 레이어 크기 확인
aws lambda get-layer-version \
  --layer-name shuking-ai-layer \
  --version-number 1 \
  --region ap-northeast-2 \
  --query 'Content.CodeSize'

# 모든 레이어 목록 확인
aws lambda list-layers --region ap-northeast-2

# 특정 레이어 버전 삭제 (필요시)
aws lambda delete-layer-version \
  --layer-name shuking-ai-layer \
  --version-number 1 \
  --region ap-northeast-2
```

### 참고 문서
- [AWS Lambda Limits](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html)
- [Lambda Layers Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html)
- [Chalice Layers](https://aws.github.io/chalice/topics/layers)

## 결론

**즉시 해결책:** `automatic_layer: false` 설정으로 불필요한 자동 레이어 생성 방지

**향후 계획:**
1. 배포 테스트 및 모니터링
2. 여전히 크기 문제 발생 시 레이어 통합 적용
3. 장기적으로 Container Image 전환 검토

