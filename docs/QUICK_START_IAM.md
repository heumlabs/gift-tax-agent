# IAM 권한 빠른 설정 가이드

## 🚀 빠른 시작

GitHub Actions에서 AWS Secrets Manager를 사용하려면 IAM 권한이 필요합니다.

## 1️⃣ 스크립트로 자동 설정 (가장 빠름)

```bash
# IAM 사용자 이름을 인자로 전달
./docs/add-iam-policy.sh github-actions-user
```

## 2️⃣ AWS CLI로 수동 설정

```bash
# IAM 사용자 이름 설정
IAM_USER_NAME="github-actions-user"

# 정책 추가
aws iam put-user-policy \
  --user-name "$IAM_USER_NAME" \
  --policy-name "SecretsManagerAccessPolicy" \
  --policy-document file://docs/iam-policy-secretsmanager.json
```

## 3️⃣ 권한 확인

```bash
# Secret 가져오기 테스트
aws secretsmanager get-secret-value \
  --secret-id arn:aws:secretsmanager:ap-northeast-2:862108802423:secret:shuking-QbyWZz \
  --region ap-northeast-2
```

성공하면 JSON 형식의 환경변수가 출력됩니다! ✅

## 4️⃣ GitHub Secrets 설정

GitHub Repository → Settings → Secrets and variables → Actions

다음 secrets를 추가:
- `AWS_ACCESS_KEY_ID` - IAM 사용자의 Access Key
- `AWS_SECRET_ACCESS_KEY` - IAM 사용자의 Secret Key

## ⚠️ 문제 해결

### "User is not authorized to perform: secretsmanager:GetSecretValue"

→ IAM 권한이 없습니다. 위 1번 또는 2번 방법으로 권한 추가

### "The security token included in the request is invalid"

→ GitHub Secrets의 AWS credentials가 잘못되었습니다. Access Key 재생성 필요

## 📚 상세 문서

- [setup-iam-permissions.md](./setup-iam-permissions.md) - 전체 IAM 권한 가이드
- [secrets-management.md](./secrets-management.md) - Secrets Manager 사용법
- [iam-policy-secretsmanager.json](./iam-policy-secretsmanager.json) - IAM 정책 파일

## 💡 보안 팁

- ✅ 최소 권한 원칙: 필요한 Secret에만 접근 권한 부여
- ✅ 정기적인 Access Key 교체 (90일 권장)
- ✅ 불필요한 관리자 권한 제거
- ✅ CloudTrail로 접근 로그 모니터링

