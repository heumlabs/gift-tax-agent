# Lambda Layer 크기 최적화 가이드

## 문제 상황

Lambda Layer 크기가 250MB 제한을 초과하여 배포 실패:
```
InvalidParameterValueException: Layers consume more than the available size of 262144000 bytes
```

## 해결 방법

### 방법 1: automatic_layer 비활성화 (✅ 적용됨)

**변경 사항:**
- `.chalice/config.json`에서 `automatic_layer: false`로 설정
- Chalice가 자동으로 추가 레이어를 생성하지 않도록 함

**효과:**
- 지정된 4개의 수동 레이어만 사용
- 불필요한 자동 레이어 생성 방지

### 방법 2: 레이어 통합 (필요시 적용)

4개의 개별 레이어 대신 1개의 통합 레이어 사용

#### 현재 레이어 구성 (4개)
```json
"layers": [
    "arn:aws:lambda:ap-northeast-2:862108802423:layer:shuking-numpy:1",
    "arn:aws:lambda:ap-northeast-2:862108802423:layer:shuking-ai-layer:1",
    "arn:aws:lambda:ap-northeast-2:862108802423:layer:shuking-db-layer:1",
    "arn:aws:lambda:ap-northeast-2:862108802423:layer:shuking-utils-layer:1"
]
```

#### 통합 레이어 생성 방법

1. **통합 레이어 빌드:**
```bash
cd backend
./.scripts/create-layer.sh shuking-deps-layer requirements-all.txt
```

2. **생성된 ARN 확인:**
```bash
# 출력 예시:
# Created layer: shuking-deps-layer
# ARN: arn:aws:lambda:ap-northeast-2:862108802423:layer:shuking-deps-layer:1
```

3. **config.json 업데이트:**
```json
{
    "version": "2.0",
    "app_name": "shuking",
    "automatic_layer": false,
    "stages": {
        "prod": {
            "layers": [
                "arn:aws:lambda:ap-northeast-2:862108802423:layer:shuking-deps-layer:1"
            ],
            ...
        }
    }
}
```

4. **재배포:**
```bash
chalice deploy --stage prod
```

### 방법 3: 의존성 최적화

불필요한 패키지나 파일 제거:

1. **제외 패턴 추가** (`.chalice/config.json`):
```json
{
    "stages": {
        "prod": {
            "environment_variables": {...},
            "reserved_concurrency": 10,
            "lambda_memory_size": 512,
            "lambda_timeout": 60
        }
    }
}
```

2. **불필요한 파일 제거:**
- `*.pyc`, `__pycache__`
- 테스트 파일
- 문서 파일

## Lambda 크기 제한

- **배포 패키지 (압축):** 50MB
- **배포 패키지 (압축 해제):** 250MB
- **레이어 포함 전체 (압축 해제):** 250MB ⚠️
- **최대 레이어 개수:** 5개

## 크기 확인 방법

```bash
# 레이어 크기 확인 (로컬)
cd backend
du -sh .chalice/layer-*.zip

# AWS에서 레이어 정보 확인
aws lambda get-layer-version \
  --layer-name shuking-ai-layer \
  --version-number 1 \
  --region ap-northeast-2
```

## 권장 사항

### 현재 배포 (automatic_layer: false)
1. ✅ 먼저 `automatic_layer: false` 설정으로 배포 시도
2. ✅ 4개의 수동 레이어만 사용
3. ⚠️ 여전히 크기 초과 시 → 레이어 통합 (방법 2)

### 레이어 통합 후
1. 1개의 통합 레이어로 모든 의존성 관리
2. 버전 관리 단순화
3. 배포 시간 단축

### 장기적 최적화
1. **함수 분리:** 무거운 AI 로직을 별도 Lambda로 분리
2. **EFS 사용:** 대용량 라이브러리를 EFS에 마운트
3. **Docker 컨테이너:** Lambda Container Image 사용 (10GB까지 지원)

## 배포 프로세스

### 현재 프로세스
```bash
# 1. 로컬에서 레이어 생성 (한 번만)
cd backend
./.scripts/create-all-layers.sh  # 또는 통합 레이어 생성

# 2. GitHub에 푸시
git add .chalice/config.json
git commit -m "Update Lambda layer configuration"
git push origin main

# 3. GitHub Actions가 자동 배포
```

## 트러블슈팅

### 여전히 크기 초과 시

1. **레이어 크기 개별 확인:**
```bash
aws lambda list-layer-versions \
  --layer-name shuking-ai-layer \
  --region ap-northeast-2 \
  --query 'LayerVersions[0].[Version,Description]'
```

2. **통합 레이어로 전환** (위의 방법 2 참조)

3. **Docker Container Image 고려:**
```dockerfile
FROM public.ecr.aws/lambda/python:3.12
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app.py .
CMD ["app.handler"]
```

## 관련 문서

- [Lambda Limits](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html)
- [Lambda Layers](https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html)
- [Chalice Documentation](https://aws.github.io/chalice/topics/layers)

## 변경 이력

- **2025-10-15:** `automatic_layer: false` 설정 적용
- **2025-10-15:** 통합 레이어 옵션 추가 (`requirements-all.txt`)

