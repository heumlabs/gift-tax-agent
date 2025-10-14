# 인프라 철거 가이드

문서 버전: v1.0  
작성일: 2025-10-14  
목적: 프로젝트 종료 시 AWS 인프라를 완전히 제거하여 불필요한 비용 발생을 방지

## ⚠️ 주의사항

- **복구 불가**: 아래 절차를 진행하면 모든 데이터와 설정이 영구적으로 삭제됩니다.
- **비용 확인**: 철거 전 현재까지의 비용을 확인하고 기록해두는 것을 권장합니다.
- **백업**: 중요한 데이터(DB 스냅샷, S3 파일 등)가 있다면 미리 백업하세요.
- **순서 준수**: 의존성이 있는 리소스가 있으므로 아래 순서대로 진행하는 것을 권장합니다.

---

## 제거 순서

### 1. CloudFront 배포 삭제

CloudFront는 삭제 전 비활성화가 필요하며, 비활성화 후 완전 삭제까지 시간이 소요됩니다.

#### AWS Console 방식
1. [CloudFront Console](https://console.aws.amazon.com/cloudfront)에 접속
2. 배포 목록에서 `E31QVR9HFDDSUI` (또는 shuking.tax 관련 배포) 선택
3. **Disable** 클릭 → 확인
4. 상태가 `Deployed`로 변경될 때까지 대기 (약 5-15분 소요)
5. 배포 선택 후 **Delete** 클릭

---

### 2. S3 버킷 삭제

프론트엔드 호스팅에 사용된 S3 버킷을 삭제합니다.

#### AWS Console 방식
1. [S3 Console](https://console.aws.amazon.com/s3)에 접속
2. `shuking.tax` 버킷 선택
3. **Empty** 클릭 → 확인 문구 입력 → 버킷 비우기
4. 버킷 선택 후 **Delete** 클릭 → 버킷 이름 입력 → 삭제

---

### 3. Chalice 배포 삭제

백엔드 Lambda 함수 및 API Gateway를 포함한 모든 Chalice 리소스를 삭제합니다.

#### Chalice CLI 방식 (권장)
```bash
cd backend

# prod 스테이지 삭제
chalice delete --stage prod

# 삭제 확인
# - API Gateway
# - Lambda 함수
# - IAM 역할 (Chalice가 자동 생성한 것)
```

#### 수동 삭제 (Chalice CLI 사용 불가 시)
1. [Lambda Console](https://console.aws.amazon.com/lambda)에서 `gift-tax-agent-prod` 함수 삭제
2. [API Gateway Console](https://console.aws.amazon.com/apigateway)에서 관련 API 삭제
3. [CloudWatch Logs](https://console.aws.amazon.com/cloudwatch)에서 `/aws/lambda/gift-tax-agent-*` 로그 그룹 삭제

---

### 4. Lambda Layer 삭제

프로젝트에서 사용한 커스텀 Lambda Layer를 삭제합니다.

#### AWS Console 방식
1. [Lambda Console](https://console.aws.amazon.com/lambda) → **Layers** 메뉴
2. `numpy-py312` Layer 선택
3. 모든 버전 선택 후 **Delete** 클릭

---

### 5. Database 제거

`alfred-agent` stage DB 내의 `shuking` 데이터베이스를 제거합니다.

#### PostgreSQL 클라이언트 방식
```bash
# alfred-agent stage DB에 접속
psql -h <alfred-agent-stage-db-endpoint> -U <username> -d postgres

# shuking 데이터베이스 삭제
DROP DATABASE shuking;

# 확인
\l
```

**참고**: `alfred-agent` RDS 인스턴스 자체는 다른 프로젝트와 공유되므로 삭제하지 않습니다.

---

### 6. IAM 리소스 정리

프로젝트에서 생성한 IAM 사용자, 역할, 정책을 삭제합니다.

#### 삭제 대상
- IAM 사용자: `shuking-deployer` 등
- IAM 역할: `shuking-*` 또는 Chalice가 자동 생성한 역할
- IAM 정책: `shuking-*` 관련 커스텀 정책

#### AWS Console 방식
1. [IAM Console](https://console.aws.amazon.com/iam)에 접속

**정책 삭제:**
2. **Policies** 메뉴 → `shuking` 검색
3. 각 정책 선택 → 연결된 엔티티가 있다면 먼저 분리(Detach)
4. **Delete** 클릭

**역할 삭제:**
5. **Roles** 메뉴 → `shuking` 또는 `gift-tax-agent` 검색
6. 각 역할 선택 → 연결된 정책 분리
7. **Delete** 클릭

**사용자 삭제:**
8. **Users** 메뉴 → 해당 사용자 선택
9. **Security credentials** 탭 → 액세스 키 삭제
10. **Delete user** 클릭

---

### 7. CloudWatch 로그 그룹 삭제

Lambda 및 기타 서비스의 로그를 삭제합니다.

#### AWS Console 방식
1. [CloudWatch Console](https://console.aws.amazon.com/cloudwatch) → **Logs** → **Log groups**
2. `gift-tax-agent`, `shuking`, `/aws/lambda/` 등으로 검색
3. 해당 로그 그룹 선택 후 **Delete** 클릭

---

## 철거 완료 확인 체크리스트

철거 완료 후 다음 항목들을 확인하세요:

- [ ] CloudFront 배포 삭제 완료
- [ ] S3 버킷 `shuking.tax` 삭제 완료
- [ ] Lambda 함수 모두 삭제 완료
- [ ] Lambda Layer `numpy-py312` 삭제 완료
- [ ] API Gateway 삭제 완료
- [ ] `alfred-agent` stage DB 내 `shuking` 데이터베이스 삭제 완료
- [ ] IAM 사용자/역할/정책 삭제 완료
- [ ] CloudWatch 로그 그룹 삭제 완료

---

## 문제 해결

### CloudFront 삭제가 안 될 때
- 배포가 완전히 비활성화(`Deployed` 상태)되었는지 확인
- 캐시가 남아있는 경우 Invalidation 생성 후 재시도

### S3 버킷 삭제가 안 될 때
- 버킷이 완전히 비어있는지 확인 (버전 관리 활성화 시 이전 버전도 삭제 필요)
- 버킷 정책이나 CORS 설정 제거

### IAM 역할/정책 삭제가 안 될 때
- 연결된 모든 엔티티를 먼저 분리(Detach)했는지 확인
- 다른 서비스에서 해당 역할을 사용 중인지 확인

---

## 참고 자료

- [AWS CLI 공식 문서](https://docs.aws.amazon.com/cli/latest/reference/)
- [Chalice 배포 관리](https://aws.github.io/chalice/topics/stages.html)
- [AWS 리소스 정리 베스트 프랙티스](https://docs.aws.amazon.com/whitepapers/latest/how-aws-pricing-works/aws-cost-optimization.html)

