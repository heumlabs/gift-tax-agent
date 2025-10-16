"""
이탈 및 의도 변경 감지 유틸리티 (키워드 기반)

Clarifying 중 사용자가 다음과 같은 행동을 하는지 키워드로 판단합니다:
- 종료 요청: "그만", "취소", "아니야", "됐어"
- 의도 변경: "상속세로 바꿀래", "증여세 알려줘"
- 정상 진행: 파라미터 답변 (날짜, 금액, 관계 등)

LLM 호출 제거하고 키워드 우선 처리로 변경 (비용 절감, 성능 향상)
"""

from __future__ import annotations

import logging
from typing import Literal

LOGGER = logging.getLogger(__name__)


# 종료 키워드
EXIT_KEYWORDS = [
    "그만", "취소", "안할래", "안 할래", "됐어", "됐습니다",
    "종료", "그만할게", "그만할래", "그만둘게", "중단",
    "안해", "안 해", "하지마", "하지 마"
]

# 상속세 전환 키워드
INHERITANCE_KEYWORDS = [
    "상속세", "상속", "부모님 돌아가", "사망", "유산"
]

# 증여세 전환 키워드
GIFT_KEYWORDS = [
    "증여세", "증여"
]


def detect_exit_intent_keyword(user_message: str) -> Literal["continue", "exit", "switch_to_inheritance", "switch_to_gift"]:
    """
    Clarifying 중 이탈 또는 의도 변경 감지 (키워드 기반)

    키워드 우선 처리로 빠르고 정확하게 감지합니다.

    Args:
        user_message: 사용자 입력 메시지

    Returns:
        str:
            - "continue": 정상 진행 (파라미터 답변)
            - "exit": 종료 요청
            - "switch_to_inheritance": 상속세로 변경
            - "switch_to_gift": 증여세로 변경

    Examples:
        >>> detect_exit_intent_keyword("그만할래")
        "exit"

        >>> detect_exit_intent_keyword("상속세 알려줘")
        "switch_to_inheritance"

        >>> detect_exit_intent_keyword("6월이라고 했잖아")
        "continue"

        >>> detect_exit_intent_keyword("2025년 10월 15일")
        "continue"
    """
    message_lower = user_message.lower().strip()

    # 1. 종료 키워드 우선 체크
    for keyword in EXIT_KEYWORDS:
        if keyword in message_lower:
            LOGGER.info(f"Exit keyword detected: {keyword}")
            return "exit"

    # 2. 상속세 전환 키워드 체크
    # "증여세" 키워드가 없고 "상속세" 키워드가 있으면 상속세로 전환
    has_inheritance = any(kw in message_lower for kw in INHERITANCE_KEYWORDS)
    has_gift = any(kw in message_lower for kw in GIFT_KEYWORDS)

    if has_inheritance and not has_gift:
        LOGGER.info("Switch to inheritance tax detected")
        return "switch_to_inheritance"

    # 3. 증여세 전환 키워드 체크
    # "상속세" 키워드가 없고 "증여세" 키워드가 있으면 증여세로 전환
    if has_gift and not has_inheritance:
        LOGGER.info("Switch to gift tax detected")
        return "switch_to_gift"

    # 4. 그 외 모두 정상 진행
    LOGGER.info("Continue detected (no exit/switch keywords)")
    return "continue"


# 하위 호환성을 위해 기존 함수명 유지 (async 버전 제거)
async def detect_exit_intent(user_message: str) -> Literal["continue", "exit", "switch_to_inheritance", "switch_to_gift"]:
    """
    하위 호환성을 위한 async wrapper

    실제로는 키워드 기반 동기 함수를 호출합니다.
    """
    return detect_exit_intent_keyword(user_message)
