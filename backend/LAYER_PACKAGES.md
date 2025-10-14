# Lambda Layer로 분리할 패키지 권장 사항

## 📊 requirements.txt 패키지 크기 분석 (추정치)

### 대용량 패키지 (Lambda Layer 분리 권장)

| 순위 | 패키지 | 예상 크기 | 설명 |
|------|--------|-----------|------|
| 1 | **google-generativeai** | ~35-40MB | Google Gemini AI SDK + 의존성 (protobuf, google-auth, etc.) |
| 2 | **psycopg2-binary** | ~8-10MB | PostgreSQL 바이너리 드라이버 |
| 3 | **SQLAlchemy** | ~5-7MB | ORM 프레임워크 |
| 4 | **pydantic** | ~3-5MB | 데이터 검증 라이브러리 |
| 5 | **requests** | ~2-3MB | HTTP 클라이언트 (+ urllib3, charset-normalizer) |

### 중간 크기 패키지

| 패키지 | 예상 크기 | 비고 |
|--------|-----------|------|
| pgvector | ~1MB | Vector 확장 |
| python-dateutil | ~500KB | 날짜 유틸리티 |
| python-dotenv | ~100KB | 환경변수 로더 |
| chalice | ~1-2MB | (배포시만 필요, 런타임 불필요) |

## 🎯 Layer 분리 전략

### 전략 1: AI/ML Layer (권장)
**Layer 이름**: `shuking-ai-layer`
```
google-generativeai==0.8.3
```
- 크기: ~40MB
- 변경 빈도: 낮음
- 다른 프로젝트 재사용 가능

### 전략 2: Database Layer
**Layer 이름**: `shuking-db-layer`
```
psycopg2-binary==2.9.9
SQLAlchemy==2.0.32
pgvector==0.3.6
```
- 크기: ~15MB
- 변경 빈도: 매우 낮음
- 데이터베이스 관련 패키지 통합

### 전략 3: Utility Layer
**Layer 이름**: `shuking-utils-layer`
```
pydantic==2.9.2
requests==2.32.4
python-dateutil==2.9.0.post0
python-dotenv==1.0.1
```
- 크기: ~10MB
- 변경 빈도: 낮음

## 📝 Layer 생성 방법

### 1. Layer 생성 스크립트

`backend/create-layer.sh`:
```bash
#!/bin/bash
LAYER_NAME=$1
REQ_FILE=$2

mkdir -p python
pip install -r $REQ_FILE -t python/
zip -r ${LAYER_NAME}.zip python/
aws lambda publish-layer-version \
    --layer-name ${LAYER_NAME} \
    --zip-file fileb://${LAYER_NAME}.zip \
    --compatible-runtimes python3.12 \
    --region ap-northeast-2
rm -rf python ${LAYER_NAME}.zip
```

### 2. requirements 파일 분리

**requirements-ai.txt**:
```
google-generativeai==0.8.3
```

**requirements-db.txt**:
```
psycopg2-binary==2.9.9
SQLAlchemy==2.0.32
pgvector==0.3.6
```

**requirements-utils.txt**:
```
pydantic==2.9.2
requests==2.32.4
python-dateutil==2.9.0.post0
python-dotenv==1.0.1
```

**requirements-app.txt** (앱 전용, 자주 변경됨):
```
chalice
```

### 3. Layer ARN을 config.json에 추가

```json
{
  "stages": {
    "prod": {
      "layers": [
        "arn:aws:lambda:ap-northeast-2:862108802423:layer:numpy-py312:1",
        "arn:aws:lambda:...:layer:shuking-ai-layer:1",
        "arn:aws:lambda:...:layer:shuking-db-layer:1",
        "arn:aws:lambda:...:layer:shuking-utils-layer:1"
      ]
    }
  }
}
```

## 💡 권장 사항

### 최소 분리 (빠른 적용)
```
Layer 1 (AI): google-generativeai
Layer 2 (DB): psycopg2-binary, SQLAlchemy, pgvector
App: 나머지 전부
```
**효과**: ~50MB 감소 → 앱 크기 15MB 이하

### 최적 분리 (권장)
```
Layer 1: google-generativeai
Layer 2: psycopg2-binary, SQLAlchemy, pgvector
Layer 3: pydantic, requests, python-dateutil, python-dotenv
App: chalice만
```
**효과**: ~60MB 감소 → 앱 크기 5MB 이하

## 🚀 즉시 적용 가능한 방법

현재 이미 `automatic_layer: true`가 설정되어 있으므로, S3 업로드만으로도 해결됩니다.
하지만 Layer를 수동으로 분리하면:
- ✅ 배포 속도 향상 (Layer는 변경되지 않으면 재업로드 불필요)
- ✅ 앱 코드만 빠르게 업데이트 가능
- ✅ 여러 Lambda 함수에서 Layer 재사용 가능
- ✅ Cold start 시간 개선

## 📌 참고

- Lambda Layer 최대 크기: 250MB (압축 해제 시)
- Lambda 함수당 최대 5개 Layer 사용 가능
- Layer는 `/opt` 디렉토리에 마운트됨
- `python/` 디렉토리 구조로 패키징 필요

