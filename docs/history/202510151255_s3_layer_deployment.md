# 작업 이력: 202510151255_s3_layer_deployment

## 작업 요약
Lambda Layer를 S3를 통해 배포하는 시스템으로 전환하여 250MB 크기 제한 문제 해결 및 자동화된 배포 파이프라인 구축

## 배경

### 문제 상황
```
InvalidParameterValueException: Layers consume more than the available size of 262144000 bytes
```

- Lambda Layer의 총 크기가 250MB 제한을 초과
- `automatic_layer: true` 설정으로 Chalice가 추가 Layer 자동 생성
- 4개의 수동 Layer + 자동 Layer의 합계가 제한 초과

### 기존 방식의 한계
1. 직접 업로드: 50MB 크기 제한
2. 여러 개의 개별 Layer 관리 복잡성
3. CI/CD에서 Layer 관리 부재
4. 패키지 증가 시 확장성 문제

## 해결 방안: S3 기반 배포

### 핵심 개선사항

#### 1. S3를 통한 Layer 배포
- **직접 업로드**: 50MB 제한
- **S3 경유**: 250MB까지 가능
- **향후 확장**: Container Image (10GB)

#### 2. 통합 Layer 전략
```
[기존] 4개 개별 Layer
- shuking-numpy
- shuking-ai-layer
- shuking-db-layer
- shuking-utils-layer

[변경] 1개 통합 Layer
- shuking-deps-layer (requirements-all.txt)
```

#### 3. 자동화된 CI/CD
```
GitHub Actions → S3 업로드 → Lambda Layer 게시 → config.json 업데이트 → Chalice 배포
```

## 변경 사항

### 1. 새로운 스크립트 생성

#### `backend/.scripts/deploy-layer-s3.sh`
**기능:**
- 패키지 설치 및 최적화 (tests, __pycache__, 문서 제거)
- ZIP 압축 (최대 압축 -9 옵션)
- S3 버킷 확인/생성
- S3에 Layer ZIP 업로드
- Lambda Layer 게시 (S3에서)
- Layer ARN을 `.layer-arn.txt`에 저장

**사용법:**
```bash
./.scripts/deploy-layer-s3.sh <layer-name> <requirements-file> [s3-bucket]

# 예시
./.scripts/deploy-layer-s3.sh shuking-deps-layer requirements-all.txt
```

**최적화 기능:**
```bash
# 불필요한 파일 제거
- tests/, test/ 디렉토리
- __pycache__, *.pyc, *.pyo
- *.dist-info, *.egg-info
- *.md, docs/ (문서 파일)
```

#### `backend/.scripts/update-layer-config.sh`
**기능:**
- `.layer-arn.txt`에서 ARN 읽기
- `.chalice/config.json` 백업
- `stages.prod.layers` 자동 업데이트
- jq 또는 Python 사용

**사용법:**
```bash
# 자동 (이전 배포의 ARN 사용)
./.scripts/update-layer-config.sh

# 수동 ARN 지정
./.scripts/update-layer-config.sh arn:aws:lambda:...:layer:name:1
```

### 2. GitHub Actions 워크플로우 업데이트

#### `.github/workflows/deploy.yml`

**추가된 환경변수:**
```yaml
env:
  S3_BUCKET: shuking-lambda-layers
  LAYER_NAME: shuking-deps-layer
```

**새로운 배포 단계:**
```yaml
- name: Deploy Lambda Layer to S3
  run: |
    chmod +x ./.scripts/deploy-layer-s3.sh
    chmod +x ./.scripts/update-layer-config.sh
    
    # Layer 배포 (S3를 통해)
    ./.scripts/deploy-layer-s3.sh ${LAYER_NAME} requirements-all.txt ${S3_BUCKET}
    
    # config.json 업데이트
    ./.scripts/update-layer-config.sh
```

**배포 순서:**
1. ✅ Python 및 의존성 설치
2. ✅ AWS 자격증명 설정
3. ✅ **Layer S3 배포 및 config 업데이트 (신규)**
4. ✅ Secrets Manager에서 환경변수 로드
5. ✅ Chalice 배포

### 3. 의존성 관리

#### `backend/requirements-all.txt` (신규)
**통합 Layer 의존성:**
```txt
# AI/ML
google-generativeai==0.8.3

# Database
psycopg2-binary==2.9.9
SQLAlchemy==2.0.32
pgvector==0.3.6

# Utilities
pydantic==2.9.2
requests==2.32.4
python-dateutil==2.9.0.post0
python-dotenv==1.0.1

# Numpy
numpy==1.26.4
```

#### 기존 파일 유지 (참고용)
- `requirements-ai.txt`
- `requirements-db.txt`
- `requirements-utils.txt`
- `requirements-numpy.txt`

### 4. Config 파일 업데이트

#### `backend/.chalice/config.json`
```diff
- "automatic_layer": true,
+ "automatic_layer": false,

- "layers": [
-   "arn:aws:lambda:...:layer:shuking-numpy:1",
-   "arn:aws:lambda:...:layer:shuking-ai-layer:1",
-   "arn:aws:lambda:...:layer:shuking-db-layer:1",
-   "arn:aws:lambda:...:layer:shuking-utils-layer:1"
- ]
+ "layers": []  # 배포 시 자동 업데이트됨
```

### 5. 기존 스크립트 정리

#### `backend/.scripts/create-layer.sh`
- 헤더에 "로컬 테스트용" 주석 추가
- "프로덕션은 deploy-layer-s3.sh 사용" 안내

#### `backend/.scripts/create-all-layers.sh`
- `[DEPRECATED]` 표시 추가
- 통합 Layer 사용 권장

### 6. 문서화

#### `docs/s3-layer-deployment-guide.md` (신규)
**포함 내용:**
- S3 기반 배포 아키텍처 다이어그램
- 배포 프로세스 상세 설명
- 로컬 배포 가이드
- 트러블슈팅
- S3 버킷 구조
- 모니터링 및 비용 최적화
- FAQ

#### `docs/lambda-layer-optimization.md` (기존)
- 참고용으로 유지

#### `README.md` 업데이트
- "배포" 섹션 추가
- S3 Layer 배포 가이드 링크

## 배포 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Actions                           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ 1. Checkout & Setup Python                            │ │
│  └────────────────────┬───────────────────────────────────┘ │
│                       │                                       │
│  ┌────────────────────▼───────────────────────────────────┐ │
│  │ 2. Deploy Lambda Layer to S3                          │ │
│  │    - Build & Optimize                                 │ │
│  │    - Upload to S3                                     │ │
│  │    - Publish Layer (from S3)                         │ │
│  │    - Save ARN to .layer-arn.txt                      │ │
│  └────────────────────┬───────────────────────────────────┘ │
│                       │                                       │
│  ┌────────────────────▼───────────────────────────────────┐ │
│  │ 3. Update config.json                                 │ │
│  │    - Read ARN from .layer-arn.txt                    │ │
│  │    - Update stages.prod.layers                       │ │
│  └────────────────────┬───────────────────────────────────┘ │
│                       │                                       │
│  ┌────────────────────▼───────────────────────────────────┐ │
│  │ 4. Fetch Secrets & Deploy Chalice                    │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                       │
         ┌─────────────┴──────────────┐
         ▼                            ▼
┌─────────────────┐        ┌──────────────────┐
│   S3 Bucket     │        │  Lambda Function │
│ shuking-lambda- │        │    shuking-prod  │
│    layers       │        │                  │
│                 │        │  [deps-layer]    │
└─────────────────┘        └──────────────────┘
```

## S3 버킷 구조

```
s3://shuking-lambda-layers/
└── layers/
    └── shuking-deps-layer/
        ├── 20251015-120000/
        │   └── shuking-deps-layer.zip  (v1)
        ├── 20251015-150000/
        │   └── shuking-deps-layer.zip  (v2)
        └── 20251015-180000/
            └── shuking-deps-layer.zip  (v3)
```

**자동 정리:**
- S3 Lifecycle Policy로 90일 이상 된 버전 자동 삭제 (선택적)

## 영향 범위

### Backend
- ✅ `.scripts/deploy-layer-s3.sh` - S3 배포 스크립트 (신규)
- ✅ `.scripts/update-layer-config.sh` - config 업데이트 스크립트 (신규)
- ✅ `.scripts/create-layer.sh` - 로컬 테스트용으로 변경
- ✅ `.scripts/create-all-layers.sh` - DEPRECATED 표시
- ✅ `.chalice/config.json` - automatic_layer: false, layers: []
- ✅ `requirements-all.txt` - 통합 Layer 의존성 (신규)

### CI/CD
- ✅ `.github/workflows/deploy.yml` - Layer S3 배포 단계 추가

### Documentation
- ✅ `docs/s3-layer-deployment-guide.md` - 상세 가이드 (신규)
- ✅ `docs/lambda-layer-optimization.md` - 기존 문서 유지
- ✅ `README.md` - 배포 섹션 추가

### Infrastructure
- ✅ S3 버킷: `shuking-lambda-layers` (자동 생성)
- ✅ Lambda Layer: `shuking-deps-layer` (S3에서 배포)

## 테스트 계획

### 로컬 테스트
```bash
# 1. Layer 배포 테스트
cd backend
./.scripts/deploy-layer-s3.sh shuking-deps-layer requirements-all.txt

# 2. config.json 업데이트 확인
./.scripts/update-layer-config.sh
cat .chalice/config.json | jq '.stages.prod.layers'

# 3. 로컬 배포 테스트
chalice deploy --stage prod
```

### CI/CD 테스트
1. ✅ feature 브랜치에서 커밋
2. ✅ main 브랜치로 머지
3. ✅ GitHub Actions 워크플로우 실행 확인
4. ✅ S3 버킷에 Layer ZIP 업로드 확인
5. ✅ Lambda Layer 버전 생성 확인
6. ✅ Lambda 함수 업데이트 확인
7. ✅ API 엔드포인트 동작 확인

## 이점

### 1. 용량 제한 해결
- ❌ 직접 업로드: 50MB 제한
- ✅ S3 경유: 250MB까지
- 🚀 향후 Container Image: 10GB

### 2. 자동화
- ✅ GitHub Actions에서 Layer 자동 배포
- ✅ config.json 자동 업데이트
- ✅ 버전 관리 자동화

### 3. 관리 간소화
- ✅ 4개 Layer → 1개 통합 Layer
- ✅ S3에서 버전별 보관
- ✅ 쉬운 롤백

### 4. 확장성
- ✅ 패키지 추가 시 requirements-all.txt만 수정
- ✅ S3 Lifecycle Policy로 오래된 버전 자동 정리
- ✅ 향후 Container Image로 전환 가능

## 비용 분석

### S3 비용
- **스토리지**: ~$0.023/GB/월
- **예상 Layer 크기**: ~100MB
- **월 비용**: ~$0.002 (무료 수준)

### Lambda Layer 비용
- **무료**: Layer 저장 및 버전 관리 무료

### 총 예상 비용
- **월 $1 미만** (기존과 동일)

## 롤백 계획

### Layer 롤백
```bash
# 1. 이전 버전 확인
aws lambda list-layer-versions \
  --layer-name shuking-deps-layer \
  --region ap-northeast-2

# 2. 이전 버전 ARN 사용
./.scripts/update-layer-config.sh arn:aws:lambda:...:layer:shuking-deps-layer:2

# 3. 재배포
chalice deploy --stage prod
```

### 긴급 롤백 (개별 Layer로)
```bash
# config.json에 이전 Layer들 수동 추가
jq '.stages.prod.layers = [
  "arn:aws:lambda:...:layer:shuking-numpy:1",
  "arn:aws:lambda:...:layer:shuking-ai-layer:1",
  "arn:aws:lambda:...:layer:shuking-db-layer:1",
  "arn:aws:lambda:...:layer:shuking-utils-layer:1"
]' .chalice/config.json
```

## 모니터링

### Layer 크기 확인
```bash
# AWS에서 Layer 크기
aws lambda get-layer-version \
  --layer-name shuking-deps-layer \
  --version-number 1 \
  --region ap-northeast-2 \
  --query 'Content.CodeSize'
```

### S3 사용량
```bash
# 버킷 크기
aws s3 ls s3://shuking-lambda-layers/layers/ --recursive --human-readable --summarize
```

### Lambda 함수 확인
```bash
# 함수의 Layer 확인
aws lambda get-function-configuration \
  --function-name shuking-prod \
  --region ap-northeast-2 \
  --query 'Layers'
```

## 향후 계획

### Phase 1: S3 기반 배포 (✅ 완료)
- S3를 통한 Layer 배포
- CI/CD 자동화
- 통합 Layer 전략

### Phase 2: 최적화 (선택)
- Layer 크기 모니터링
- 불필요한 패키지 제거
- 압축 최적화

### Phase 3: Container Image (장기)
```dockerfile
FROM public.ecr.aws/lambda/python:3.12
COPY requirements-all.txt .
RUN pip install -r requirements-all.txt
COPY . .
CMD ["app.handler"]
```

**Container 전환 시 이점:**
- 10GB 크기 제한
- Docker 기반 개발 환경
- 더 쉬운 의존성 관리

## 명령어 레퍼런스

### Layer 배포
```bash
# S3를 통한 배포
./.scripts/deploy-layer-s3.sh shuking-deps-layer requirements-all.txt

# 커스텀 S3 버킷
./.scripts/deploy-layer-s3.sh shuking-deps-layer requirements-all.txt my-bucket

# config 업데이트
./.scripts/update-layer-config.sh
```

### Layer 정보 확인
```bash
# 최신 버전
aws lambda list-layer-versions \
  --layer-name shuking-deps-layer \
  --region ap-northeast-2 \
  --query 'LayerVersions[0]'

# 특정 버전 상세
aws lambda get-layer-version \
  --layer-name shuking-deps-layer \
  --version-number 1 \
  --region ap-northeast-2
```

### S3 관리
```bash
# S3 버킷 생성
aws s3 mb s3://shuking-lambda-layers --region ap-northeast-2

# 버킷 내용 확인
aws s3 ls s3://shuking-lambda-layers/layers/ --recursive

# 특정 파일 다운로드
aws s3 cp s3://shuking-lambda-layers/layers/shuking-deps-layer/20251015-120000/shuking-deps-layer.zip ./
```

## 트러블슈팅

### 1. S3 업로드 실패
```bash
# IAM 권한 확인
aws iam get-user-policy --user-name your-user --policy-name your-policy

# 필요한 권한:
# - s3:CreateBucket
# - s3:PutObject
# - s3:GetObject
```

### 2. Layer 크기 여전히 큼
```bash
# 로컬에서 크기 확인
pip install -r requirements-all.txt -t /tmp/test-layer
du -sh /tmp/test-layer

# 패키지별 크기
du -sh /tmp/test-layer/* | sort -h
```

### 3. config.json 업데이트 실패
```bash
# jq 설치 (Mac)
brew install jq

# jq 설치 (Ubuntu)
sudo apt-get install jq

# Python으로 수동 업데이트
python3 -c "
import json
with open('.chalice/config.json', 'r') as f:
    config = json.load(f)
config['stages']['prod']['layers'] = ['YOUR_ARN']
with open('.chalice/config.json', 'w') as f:
    json.dump(config, f, indent=4)
"
```

## 체크리스트

### 배포 전
- [x] S3 기반 배포 스크립트 작성
- [x] config 업데이트 스크립트 작성
- [x] GitHub Actions 워크플로우 업데이트
- [x] requirements-all.txt 작성
- [x] 문서화 완료

### 배포 후
- [ ] 로컬에서 배포 테스트
- [ ] main 브랜치 머지
- [ ] GitHub Actions 실행 확인
- [ ] S3 버킷에 Layer 업로드 확인
- [ ] Lambda Layer 생성 확인
- [ ] Lambda 함수 동작 확인
- [ ] API 엔드포인트 테스트

## 관련 이슈

- InvalidParameterValueException: Layers consume more than 250MB
- 패키지 의존성 증가로 인한 확장성 문제
- 수동 Layer 관리의 복잡성

## 기타

### IAM 권한 요구사항

**S3:**
- `s3:CreateBucket`
- `s3:PutObject`
- `s3:GetObject`
- `s3:ListBucket`

**Lambda:**
- `lambda:PublishLayerVersion`
- `lambda:ListLayerVersions`
- `lambda:GetLayerVersion`
- `lambda:DeleteLayerVersion` (선택)

### 참고 문서
- [AWS Lambda Layers](https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html)
- [S3 Bucket Operations](https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingBucket.html)
- [Chalice Deployment](https://aws.github.io/chalice/topics/configfile.html)

## 결론

S3 기반 Lambda Layer 배포 시스템으로 전환하여:

1. ✅ **250MB 크기 제한 문제 해결**
2. ✅ **자동화된 CI/CD 파이프라인 구축**
3. ✅ **간소화된 Layer 관리 (4개 → 1개)**
4. ✅ **확장 가능한 배포 아키텍처**

향후 패키지가 계속 증가하더라도 S3를 통해 유연하게 대응 가능하며, 필요시 Container Image로 전환할 수 있는 기반을 마련했습니다.

