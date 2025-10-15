# AI Chat Prototype

LLM 팀이 독립적으로 챗봇 로직을 실험·구현하기 위한 모듈 모음입니다.  
Gemini REST API를 직접 호출하는 최소 파이프라인을 제공하며, 백엔드와의 통합 시 해당 모듈을 가져다 쓸 수 있습니다.

## 디렉터리 구조

```
ai/
├── config.py          # Gemini 설정 로더 (환경 변수 기반)
├── exceptions.py      # 공통 예외 정의
├── clients/           # 외부 API 클라이언트 (Gemini 등)
├── prompts/           # 시스템 프롬프트 템플릿
├── schemas/           # 요청/응답 데이터 구조
├── pipelines/         # 대화 플로우 orchestrator
└── scripts/           # 수동 테스트용 CLI 스크립트
```

## 환경 변수

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `GOOGLE_API_KEY` | Gemini API 키 | (필수) |
| `GEMINI_MODEL` | 사용할 모델 이름 | `gemini-2.5-flash` |
| `GEMINI_TIMEOUT_SECONDS` | 요청 타임아웃(초) | `30.0` |

## 테스트 실행

```bash
# 테스트 의존성 설치
pip3 install -r requirements-test.txt

# 전체 테스트 실행
pytest

# 커버리지 포함
pytest --cov=ai --cov-report=term-missing

# 특정 테스트만 실행
pytest tests/test_schemas.py -v
```

## 빠른 테스트

### 1. CLI 스크립트로 테스트

```bash
pip3 install httpx python-dotenv
python -m ai.scripts.send_message "배우자에게 1억원 증여하면 세금이 어떻게 되나요?"
```

성공 시 모델 응답을 표준 출력으로 확인할 수 있습니다. JSON 형태를 원하면 `--json` 플래그를 추가하세요.

### 2. Chalice 통합 테스트

백엔드 API를 통해 전체 파이프라인을 테스트:

```bash
# 1. 백엔드 서버 실행 (터미널 1)
cd backend
chalice local

# 2. API 호출 테스트 (터미널 2)
curl -X POST http://127.0.0.1:8000/api/sessions/test-session-123/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "배우자에게 1억원 증여하면 세금이 얼마인가요?"}'
```

**예상 응답:**
```json
{
  "assistantMessage": {
    "id": "...",
    "role": "assistant",
    "content": "안녕하세요! 세무 상담사 슈킹입니다...",
    "metadata": {
      "citations": [],
      "calculation": null,
      "clarifying_context": [],
      "assumptions": [],
      "missing_parameters": [],
      "exceptions": [],
      "recommendations": [],
      "tool_calls": []
    },
    "createdAt": "2025-10-15T12:08:20..."
  }
}
```

> 내부 구현은 비동기(`async`)로 동작하므로, 여러 메시지를 `asyncio.gather`로 동시에 처리하도록 손쉽게 확장할 수 있습니다.

※ 루트 `.env` 또는 `backend/.env`에 위 환경 변수를 정의해 두면 스크립트 실행 시 자동으로 로드됩니다.
