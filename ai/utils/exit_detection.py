"""
이탈 및 의도 변경 감지 유틸리티 (LLM 기반)

Clarifying 중 사용자가 다음과 같은 행동을 하는지 LLM이 판단합니다:
- 종료 요청: "그만", "취소", "아니야", "됐어"
- 의도 변경: "상속세로 바꿀래", "증여세 알려줘"
- 정상 진행: 파라미터 답변 (날짜, 금액, 관계 등)
"""

from __future__ import annotations

import json
import logging
from typing import Literal

from ai.clients.gemini import GeminiClient, GeminiSettings

LOGGER = logging.getLogger(__name__)


CLARIFYING_INTENT_DETECTION_PROMPT = """당신은 사용자가 증여세/상속세 계산 중에 어떤 의도를 가지고 있는지 판단하는 AI입니다.

**사용자 메시지를 분석하여 다음 중 하나로 분류하세요:**

1. **continue**: 정상적으로 계산을 진행 (날짜, 금액, 관계 등 정보 제공)
   - 예: "2025년 5월", "100억원", "부모님", "직계존속"

2. **exit**: 계산을 중단하거나 종료하려는 의도
   - 예: "그만", "취소", "안할래", "됐어", "중단할게"

3. **switch_to_inheritance**: 상속세 계산으로 전환하려는 의도
   - 예: "상속세 알려줘", "상속세로 바꿔줘", "부모님 돌아가셔서"

4. **switch_to_gift**: 증여세 계산으로 전환하려는 의도
   - 예: "증여세 알려줘", "증여세로 바꿔줘", "다시 증여세"

**출력 형식:**
JSON 형식으로만 응답하세요. 다른 설명 없이 아래 형식만 출력하세요.

{
  "intent": "continue | exit | switch_to_inheritance | switch_to_gift",
  "reasoning": "판단 근거를 1-2문장으로 설명"
}

**사용자 메시지:**
{user_message}
"""


async def detect_exit_intent(user_message: str) -> Literal["continue", "exit", "switch_to_inheritance", "switch_to_gift"]:
    """
    Clarifying 중 이탈 또는 의도 변경 감지 (LLM 기반)

    LLM을 사용하여 사용자의 의도를 정확하게 파악합니다.

    Args:
        user_message: 사용자 입력 메시지

    Returns:
        str:
            - "continue": 정상 진행 (파라미터 답변)
            - "exit": 종료 요청
            - "switch_to_inheritance": 상속세로 변경
            - "switch_to_gift": 증여세로 변경

    Examples:
        >>> await detect_exit_intent("그만할래")
        "exit"

        >>> await detect_exit_intent("상속세 알려줘")
        "switch_to_inheritance"

        >>> await detect_exit_intent("2025년 10월 15일")
        "continue"
    """
    try:
        settings = GeminiSettings.from_env()
        client = GeminiClient(settings)

        prompt = CLARIFYING_INTENT_DETECTION_PROMPT.format(user_message=user_message)

        response = await client.generate_content(
            system_prompt="",
            user_message=prompt
        )

        # JSON 파싱
        result = json.loads(response)
        intent = result.get("intent", "continue")
        reasoning = result.get("reasoning", "")

        LOGGER.info(f"LLM intent detection: {intent} (reasoning: {reasoning})")

        # 유효한 값인지 확인
        valid_intents = ["continue", "exit", "switch_to_inheritance", "switch_to_gift"]
        if intent not in valid_intents:
            LOGGER.warning(f"Invalid intent from LLM: {intent}. Defaulting to 'continue'")
            return "continue"

        return intent

    except Exception as e:
        LOGGER.error(f"Failed to detect intent with LLM: {e}. Defaulting to 'continue'")
        return "continue"


# 하위 호환성을 위해 동기 버전도 제공
def detect_exit_intent_keyword(user_message: str) -> Literal["continue", "exit", "switch_to_inheritance", "switch_to_gift"]:
    """
    하위 호환성을 위한 동기 wrapper

    실제로는 비동기 LLM 호출을 동기적으로 실행합니다.
    """
    import asyncio
    return asyncio.run(detect_exit_intent(user_message))
