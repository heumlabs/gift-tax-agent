# 작업 이력: 202510171038_remove_alembic_from_cicd

## 작업 요약
GitHub Actions deploy workflow에서 자동 Alembic 마이그레이션 단계를 제거하여 데이터베이스 스키마 변경을 수동으로 관리하도록 변경

## 변경 사항

### 1. GitHub Actions Workflow 수정
**파일**: `.github/workflows/deploy.yml`

**제거된 단계들 (총 27줄)**:
1. **Python 환경 설정**
   ```yaml
   - name: Set up Python for Alembic
     uses: actions/setup-python@v5
     with:
       python-version: '3.12'
   ```

2. **의존성 설치**
   ```yaml
   - name: Install dependencies from requirements.txt
     run: |
       pip install --upgrade pip
       pip install -r requirements.txt
   ```

3. **Alembic 마이그레이션 실행**
   ```yaml
   - name: Run Alembic migrations
     run: |
       if [ ! -f .env ]; then
         echo "❌ .env 파일이 없습니다."
         exit 1
       fi
       echo "🔄 데이터베이스 마이그레이션 시작..."
       alembic upgrade head
       echo "✅ 데이터베이스 마이그레이션 완료"
   ```

## 영향 범위

### CI/CD 파이프라인
- ✅ **배포 시간 단축**: Python 설치 및 마이그레이션 실행 시간 절약 (~2-3분)
- ✅ **단순화**: Lambda 컨테이너 이미지 배포만 수행
- ✅ **안정성 향상**: 마이그레이션 실패로 인한 배포 중단 위험 제거

### 데이터베이스 관리
- ⚠️ **수동 작업 필요**: 스키마 변경 시 로컬에서 수동으로 마이그레이션 실행 필요
- ✅ **더 안전한 관리**: 마이그레이션 타이밍과 순서를 명시적으로 제어
- ✅ **롤백 용이**: 문제 발생 시 즉시 alembic downgrade 가능

### 개발 프로세스
- 📋 **새로운 절차 필요**: 배포 전 마이그레이션 수동 실행
- 📋 **문서화 필요**: 마이그레이션 실행 가이드 공유

## 이유 및 배경

### 1. 초기 요구사항
- Alembic 마이그레이션을 "지금 당장은 CI/CD에 넣을 수 없어서 로컬에서 실행하는 형태"로 구현
- 프로덕션 데이터베이스에 대한 자동 스키마 변경의 위험성

### 2. 권한 문제
- RDS에서 pgvector extension 생성 시 `rds_superuser` 권한 필요
- CI/CD 파이프라인의 일반 사용자 권한으로는 특정 작업 불가

### 3. 운영 안정성
- 데이터베이스 마이그레이션은 민감한 작업
- 배포와 분리하여 독립적으로 관리하는 것이 더 안전
- 문제 발생 시 빠른 대응 가능

## 마이그레이션 실행 방법

### 로컬 환경에서 스테이징 DB에 마이그레이션 적용

```bash
# 1. backend 디렉토리로 이동
cd backend

# 2. .env 파일에 DB 정보 설정 확인
# DB_HOST=your-db-host.rds.amazonaws.com
# DB_NAME=your_database
# DB_USER=your_username
# DB_PASS=your_password

# 3. OpenVPN 연결 (필요시)
# AWS VPC 내부의 RDS에 접근하기 위해

# 4. 현재 마이그레이션 상태 확인
alembic current

# 5. 마이그레이션 히스토리 확인
alembic history

# 6. 마이그레이션 SQL 미리보기 (실행하지 않음)
alembic upgrade head --sql

# 7. 실제 마이그레이션 적용
alembic upgrade head

# 8. 적용 결과 확인
alembic current
```

### 주의사항

1. **pgvector Extension**
   - 마이그레이션 실행 전 pgvector extension이 필요
   - `rds_superuser` 권한으로 수동 설치 필요:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

2. **백업**
   - 프로덕션 환경에 마이그레이션 적용 전 반드시 백업
   - RDS 스냅샷 생성 권장

3. **순서**
   - 마이그레이션 먼저 실행 → 애플리케이션 배포
   - 롤백이 필요한 경우 역순으로 진행

## 테스트

### 1. Workflow 동작 확인
```bash
# feature 브랜치 push 시
# - backend 변경사항이 있으면 Lambda 배포만 수행
# - Alembic 마이그레이션 단계 생략 확인
```

### 2. 로컬 마이그레이션 테스트 완료
```bash
# config.py URL 인코딩 수정으로 특수문자 비밀번호 지원
# alembic/env.py에서 직접 DATABASE_URL 사용하여 ConfigParser 문제 회피
alembic current  # ✅ 연결 성공
alembic history  # ✅ 마이그레이션 목록 확인
```

## 관련 파일

### 변경됨
- `.github/workflows/deploy.yml` - Alembic 단계 제거

### 참고 문서
- `backend/README_ALEMBIC.md` - Alembic 사용 가이드 (삭제됨, 필요시 재작성)
- `backend/alembic/` - Alembic 설정 및 마이그레이션 파일
- `backend/alembic.ini` - Alembic 설정 파일
- `backend/config.py` - DATABASE_URL 생성 (URL 인코딩 포함)

## 향후 계획

### 1. 문서화 작업
- [ ] Alembic 마이그레이션 실행 가이드 작성
- [ ] 팀원 간 운영 절차 공유
- [ ] 프로덕션 마이그레이션 체크리스트 작성

### 2. 자동화 개선 (선택적)
- [ ] 마이그레이션 실행 스크립트 작성
- [ ] Slack 알림 연동 (마이그레이션 실행 시)
- [ ] 안전한 자동화 방법 검토 (승인 프로세스 등)

### 3. 모니터링
- [ ] 마이그레이션 실행 이력 기록
- [ ] 스키마 버전 추적 대시보드

## 커밋 정보

```
커밋: b766225
브랜치: feature/remove-alembic-migrate-step-in-workflow
메시지: chore: remove alembic migration step from deploy workflow

- Remove automatic database migration from CI/CD pipeline
- Alembic migrations will be run manually in local environment
- This provides better control over database schema changes
- Removed: Python setup, requirements install, alembic upgrade steps
```

## 기타

### Alembic 설정 상태
- ✅ `backend/requirements.txt`에 `alembic==1.13.2` 포함
- ✅ `backend/alembic/` 디렉토리 및 설정 파일 존재
- ✅ `backend/config.py`에 URL 인코딩 추가 (특수문자 비밀번호 지원)
- ✅ `backend/alembic/env.py`에 SQLModel 연동 완료
- ⏳ 초기 마이그레이션 파일 생성 예정

### 참고 링크
- PR: https://github.com/heumlabs/gift-tax-agent/pull/new/feature/remove-alembic-migrate-step-in-workflow
- Alembic 공식 문서: https://alembic.sqlalchemy.org/
- pgvector 문서: https://github.com/pgvector/pgvector

