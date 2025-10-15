# IAM 권한 설정 가이드

## Secrets Manager 접근 권한 추가

GitHub Actions 또는 로컬에서 AWS Secrets Manager에 접근하려면 IAM 사용자/역할에 권한이 필요합니다.

## 필요한 권한

Secrets Manager에서 환경변수를 가져오기 위해 다음 권한이 필요합니다:

- `secretsmanager:GetSecretValue` - Secret 값 읽기
- `secretsmanager:DescribeSecret` - Secret 메타데이터 확인

## 방법 1: AWS CLI로 인라인 정책 추가 (권장)

### 1. IAM 사용자 이름 확인

```bash
# 현재 사용자 확인
aws sts get-caller-identity

# IAM 사용자 목록 확인
aws iam list-users --query 'Users[*].[UserName,UserId]' --output table
```

### 2. 인라인 정책 추가

```bash
# IAM 사용자에 정책 추가
IAM_USER_NAME="your-github-actions-user"  # 실제 사용자 이름으로 변경

aws iam put-user-policy \
  --user-name "$IAM_USER_NAME" \
  --policy-name "SecretsManagerAccessPolicy" \
  --policy-document file://docs/iam-policy-secretsmanager.json
```

### 3. 정책 확인

```bash
# 추가된 정책 확인
aws iam get-user-policy \
  --user-name "$IAM_USER_NAME" \
  --policy-name "SecretsManagerAccessPolicy"
```

## 방법 2: AWS Console에서 설정

### 1. IAM Console 접속

1. AWS Console → IAM 서비스
2. 좌측 메뉴에서 "Users" 클릭
3. GitHub Actions에서 사용하는 IAM 사용자 선택

### 2. 인라인 정책 추가

1. "Permissions" 탭 선택
2. "Add permissions" → "Create inline policy" 클릭
3. "JSON" 탭 선택
4. 다음 정책 붙여넣기:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowSecretsManagerAccess",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:ap-northeast-2:862108802423:secret:shuking-QbyWZz"
    }
  ]
}
```

5. "Review policy" 클릭
6. Policy name: `SecretsManagerAccessPolicy` 입력
7. "Create policy" 클릭

## 방법 3: 관리형 정책 생성 (여러 사용자에게 적용 시)

### 1. 정책 생성

```bash
# 관리형 정책 생성
aws iam create-policy \
  --policy-name "ShukingSecretsManagerAccess" \
  --policy-document file://docs/iam-policy-secretsmanager.json \
  --description "Allow access to Shuking Secrets Manager secret"
```

### 2. 정책을 사용자에게 연결

```bash
# 정책 ARN 확인
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
POLICY_ARN="arn:aws:iam::${ACCOUNT_ID}:policy/ShukingSecretsManagerAccess"

# IAM 사용자에 정책 연결
IAM_USER_NAME="your-github-actions-user"
aws iam attach-user-policy \
  --user-name "$IAM_USER_NAME" \
  --policy-arn "$POLICY_ARN"
```

## GitHub Actions Secrets 설정

IAM 권한 추가 후, GitHub Actions에서 사용할 Access Key가 설정되어 있는지 확인:

### 1. GitHub Repository 설정

1. GitHub Repository → Settings → Secrets and variables → Actions
2. 다음 secrets 확인:
   - `AWS_ACCESS_KEY_ID` - IAM 사용자의 Access Key ID
   - `AWS_SECRET_ACCESS_KEY` - IAM 사용자의 Secret Access Key

### 2. 새 Access Key 생성 (필요 시)

```bash
# IAM 사용자의 Access Key 생성
aws iam create-access-key --user-name "$IAM_USER_NAME"

# 출력된 AccessKeyId와 SecretAccessKey를 GitHub Secrets에 등록
```

## 권한 확인

권한이 올바르게 설정되었는지 확인:

```bash
# Secrets Manager 접근 테스트
aws secretsmanager get-secret-value \
  --secret-id arn:aws:secretsmanager:ap-northeast-2:862108802423:secret:shuking-QbyWZz \
  --region ap-northeast-2 \
  --query 'SecretString' \
  --output text

# 성공하면 JSON 형식의 secret 값이 출력됨
```

## 최소 권한 원칙

현재 정책은 특정 Secret (`shuking-QbyWZz`)에만 접근을 허용합니다:

✅ **좋은 점:**
- 최소 권한 원칙 준수
- 다른 Secrets에는 접근 불가
- 읽기 전용 (쓰기 권한 없음)

## 문제 해결

### 오류: "User is not authorized to perform: secretsmanager:GetSecretValue"

**원인**: IAM 권한이 없거나 잘못 설정됨

**해결**:
1. IAM 사용자의 정책 확인
2. Secret ARN이 정확한지 확인
3. Region이 `ap-northeast-2`인지 확인

### 오류: "The security token included in the request is invalid"

**원인**: Access Key가 만료되었거나 잘못됨

**해결**:
1. 새 Access Key 생성
2. GitHub Secrets 업데이트
3. 이전 Access Key 비활성화

## 보안 권장사항

1. ✅ **정기적인 Access Key 교체**
   - 90일마다 Access Key 교체 권장

2. ✅ **불필요한 권한 제거**
   - AdministratorAccess 같은 광범위한 권한 제거
   - 필요한 최소 권한만 부여

3. ✅ **CloudTrail 로깅 활성화**
   - Secrets Manager 접근 로그 모니터링

4. ✅ **MFA 활성화**
   - 중요한 IAM 사용자는 MFA 필수

## 참고

- [AWS Secrets Manager 권한](https://docs.aws.amazon.com/secretsmanager/latest/userguide/auth-and-access.html)
- [IAM 정책 예제](https://docs.aws.amazon.com/secretsmanager/latest/userguide/auth-and-access_examples.html)
- [GitHub Actions에서 AWS 사용](https://github.com/aws-actions/configure-aws-credentials)

