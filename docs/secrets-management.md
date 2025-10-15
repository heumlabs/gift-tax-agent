# AWS Secrets Manager를 통한 환경변수 관리

## 개요

민감한 환경변수(DB 연결 정보, API 키 등)는 AWS Secrets Manager에 저장하여 관리합니다.

## Secret 정보

- **Secret ARN**: `arn:aws:secretsmanager:ap-northeast-2:862108802423:secret:shuking-QbyWZz`
- **Region**: `ap-northeast-2`

## 저장된 환경변수

`backend/config.py`에 정의된 환경변수들:

```python
- APP_STAGE      # 애플리케이션 스테이지 (local/dev/prod)
- DB_HOST        # 데이터베이스 호스트
- DB_NAME        # 데이터베이스 이름
- DB_USER        # 데이터베이스 사용자
- DB_PASS        # 데이터베이스 비밀번호
- GOOGLE_API_KEY # Google Gemini API 키
```

## Secrets 가져오기

### 자동 스크립트 사용 (권장)

```bash
cd backend
./.scripts/fetch-secrets.sh
```

이 스크립트는:
1. AWS 자격증명 확인
2. Secrets Manager에서 secret 가져오기
3. `.env` 파일 생성 (기존 파일이 있으면 백업)
4. 환경변수 목록 표시

### 수동으로 가져오기

AWS CLI를 사용하여 직접 가져올 수도 있습니다:

```bash
# Secret 가져오기
aws secretsmanager get-secret-value \
    --secret-id arn:aws:secretsmanager:ap-northeast-2:862108802423:secret:shuking-QbyWZz \
    --region ap-northeast-2 \
    --query 'SecretString' \
    --output text | jq -r 'to_entries | .[] | "\(.key)=\(.value)"' > .env
```

## CI/CD 통합

GitHub Actions 워크플로우에서 자동으로 secrets를 가져옵니다:

```yaml
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v5.1.0
  with:
    aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
    aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    aws-region: ap-northeast-2

- name: Fetch secrets from AWS Secrets Manager
  run: |
    sudo apt-get update && sudo apt-get install -y jq
    ./.scripts/fetch-secrets.sh
```

## Secret 업데이트

### AWS Console 사용

1. AWS Console → Secrets Manager
2. Secret `shuking-QbyWZz` 선택
3. "Retrieve secret value" → "Edit"
4. JSON 형식으로 키-값 쌍 수정
5. "Save" 클릭

### AWS CLI 사용

```bash
# Secret 업데이트 (JSON 형식)
aws secretsmanager update-secret \
    --secret-id arn:aws:secretsmanager:ap-northeast-2:862108802423:secret:shuking-QbyWZz \
    --secret-string '{
        "APP_STAGE": "prod",
        "DB_HOST": "your-db-host",
        "DB_NAME": "your-db-name",
        "DB_USER": "your-db-user",
        "DB_PASS": "your-db-password",
        "GOOGLE_API_KEY": "your-google-api-key"
    }' \
    --region ap-northeast-2
```

## 로컬 개발

로컬 개발 시에는 `.env` 파일을 수동으로 생성하거나 스크립트를 사용할 수 있습니다:

```bash
# 방법 1: 스크립트 사용 (AWS 자격증명 필요)
cd backend
./.scripts/fetch-secrets.sh

# 방법 2: .env.example 복사 후 수정
cp .env.example .env
# .env 파일을 편집하여 실제 값 입력
```

## 보안 주의사항

⚠️ **중요**: `.env` 파일은 절대 Git에 커밋하지 마세요!

- `.gitignore`에 `.env` 파일이 포함되어 있는지 확인
- 민감한 정보가 포함된 파일은 로컬에만 보관
- AWS Secrets Manager를 통해 안전하게 관리

## 권한 요구사항

Secrets를 가져오려면 다음 IAM 권한이 필요합니다:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
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

GitHub Actions의 경우, `AWS_ACCESS_KEY_ID`와 `AWS_SECRET_ACCESS_KEY` secrets에 위 권한을 가진 IAM 사용자의 자격증명을 설정해야 합니다.

## 문제 해결

### jq 명령을 찾을 수 없음

```bash
# macOS
brew install jq

# Ubuntu/Debian
sudo apt-get install jq

# Amazon Linux
sudo yum install jq
```

### AWS 자격증명 오류

```bash
# 자격증명 확인
aws sts get-caller-identity

# 자격증명 설정
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_DEFAULT_REGION=ap-northeast-2
```

### Secret을 찾을 수 없음

Secret ARN과 Region이 올바른지 확인하세요:
- Secret ARN: `arn:aws:secretsmanager:ap-northeast-2:862108802423:secret:shuking-QbyWZz`
- Region: `ap-northeast-2`

## 참고

- [AWS Secrets Manager 문서](https://docs.aws.amazon.com/secretsmanager/)
- [GitHub Actions secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)

