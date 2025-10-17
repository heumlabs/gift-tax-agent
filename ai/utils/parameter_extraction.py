"""
파라미터 추출 및 질문 생성 유틸리티

Issue #23 Phase 3에서 Clarifying 노드가 사용하는 핵심 함수들을 제공합니다.

참조:
- docs/prd_detail/ai-logic/04-clarifying-implementation-spec.md (섹션 2.3, 3.2, 3.3)
- docs/prd_detail/ai-logic/04-clarifying-strategy.md
"""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from typing import Dict, List, Optional

from ai.clients.gemini import GeminiClient
from ai.config import GeminiSettings
from ai.exceptions import GeminiClientError
from ai.prompts.clarifying import (
    CLARIFYING_QUESTIONS,
    PARAMETER_EXTRACTION_PROMPT,
    QUESTION_GENERATION_PROMPT,
)

LOGGER = logging.getLogger(__name__)


async def extract_parameters(user_message: str, collected_parameters: Optional[Dict] = None) -> Dict:
    """
    Gemini API를 사용하여 사용자 메시지에서 파라미터 추출

    자연어 입력 ("1억", "부모님", "오늘")을 구조화된 JSON으로 변환합니다.
    실패 시 기본값만 반환합니다.

    Args:
        user_message: 사용자 입력 메시지
        collected_parameters: 이미 수집된 파라미터 (컨텍스트)

    Returns:
        dict: 파싱된 파라미터
            - 성공 시: 9개 변수 (null 가능)
            - 실패 시: Tier 2/3 기본값만 (is_*, *_amount, secured_debt)

    Example:
        >>> await extract_parameters("부모님께 1억 받았어요")
        {
            "donor_relationship": "직계존속",
            "gift_property_value": 100000000,
            "gift_date": null,
            ...
        }
    """
    try:
        # 날짜 관련 동적 값 계산
        today = date.today()
        yesterday = today - timedelta(days=1)
        this_month_15th = today.replace(day=15)
        current_year = today.year
        last_year = today.year - 1

        # 이미 수집된 파라미터 컨텍스트
        context_info = ""
        if collected_parameters:
            context_info = f"\n\n### 이미 수집된 정보\n{json.dumps(collected_parameters, ensure_ascii=False, indent=2)}\n위 정보를 참고하여, 현재 메시지에서 추가로 추출할 수 있는 내용만 업데이트하세요."

        # 프롬프트 포맷팅
        prompt = PARAMETER_EXTRACTION_PROMPT.format(
            today=today.isoformat(),
            yesterday=yesterday.isoformat(),
            this_month_15th=this_month_15th.isoformat(),
            current_year=current_year,
            last_year=last_year,
            user_message=user_message,
            context=context_info
        )

        # Gemini API 호출
        settings = GeminiSettings.from_env()
        client = GeminiClient(settings)

        # prompt에 이미 user_message가 포함되어 있으므로 빈 문자열 전달
        response = await client.generate_content(
            system_prompt=prompt,
            user_message=""
        )

        # JSON 파싱
        # Gemini가 ```json ... ``` 형식으로 반환할 수 있으므로 정리
        response_clean = response.strip()
        if response_clean.startswith("```json"):
            response_clean = response_clean[7:]  # ```json 제거
        if response_clean.startswith("```"):
            response_clean = response_clean[3:]  # ``` 제거
        if response_clean.endswith("```"):
            response_clean = response_clean[:-3]  # ``` 제거

        parsed = json.loads(response_clean.strip())
        LOGGER.info(f"Parameter extraction successful: {parsed}")
        return parsed

    except (json.JSONDecodeError, GeminiClientError) as e:
        # 파싱 실패 시 빈 dict 반환 (기본값은 계산 Tool 호출 시점에 추가)
        LOGGER.warning(f"Parameter extraction failed: {e}. Returning empty dict.")
        return {}


def check_missing_parameters(collected_parameters: Dict) -> List[str]:
    """
    Tier 1 필수 변수 누락 체크

    Phase 3에서는 Tier 1만 체크합니다 (Tier 2는 기본값 사용).

    Args:
        collected_parameters: 현재까지 수집된 파라미터

    Returns:
        list[str]: 누락된 변수명 리스트 (Tier 1만)

    Example:
        >>> check_missing_parameters({"donor_relationship": "직계존속"})
        ["gift_date", "gift_property_value"]
    """
    required = ["gift_date", "donor_relationship", "gift_property_value"]
    missing = [
        param for param in required
        if param not in collected_parameters or collected_parameters[param] is None
    ]
    return missing


def get_next_question(collected_parameters: Dict, missing_parameters: List[str]) -> Optional[str]:
    """
    다음 질문할 변수 선택 (Tier 순서대로)

    우선순위:
    1. Tier 1 필수 변수 (gift_date, donor_relationship, gift_property_value)
    2. Tier 3 조건부 변수 (marriage/childbirth_deduction_amount - 직계존속/비속만)
    3. Tier 2는 Phase 3에서 건너뜀 (기본값 사용)

    Args:
        collected_parameters: 현재까지 수집된 파라미터
        missing_parameters: 누락된 Tier 1 변수 목록

    Returns:
        str | None: 다음 질문할 변수명 또는 None (모두 수집 완료)

    Example:
        >>> get_next_question(
        ...     {"donor_relationship": "직계존속", "gift_property_value": 100000000},
        ...     ["gift_date"]
        ... )
        "gift_date"
    """
    # Tier 1 우선 체크
    tier1_required = ["gift_date", "donor_relationship", "gift_property_value"]
    for param in tier1_required:
        if param in missing_parameters:
            return param

    # Tier 1 모두 수집됨 → Tier 3 조건부 체크
    donor_relationship = collected_parameters.get("donor_relationship")

    # 혼인공제 (직계존속/비속만)
    if donor_relationship in ["직계존속", "직계비속"]:
        if "marriage_deduction_amount" not in collected_parameters:
            return "marriage_deduction_amount"
        if "childbirth_deduction_amount" not in collected_parameters:
            return "childbirth_deduction_amount"

    # 담보채무는 Phase 3에서 생략 (기본값 0 사용)

    # 모든 필수 변수 수집 완료
    return None


def generate_clarifying_question(
    collected_parameters: Dict,
    missing_parameters: List[str]
) -> Optional[str]:
    """
    Clarifying 질문 생성 (템플릿 기반)

    Tier 순서에 따라 다음 질문할 변수를 선택하고 템플릿을 반환합니다.

    **Note**: 이 함수는 폴백용입니다. 실제로는 `generate_clarifying_question_dynamic()`을 사용하세요.

    Args:
        collected_parameters: 현재까지 수집된 파라미터
        missing_parameters: 누락된 Tier 1 변수 목록

    Returns:
        str | None: 질문 텍스트 또는 None (계산 가능)

    Example:
        >>> generate_clarifying_question(
        ...     {"donor_relationship": "직계존속"},
        ...     ["gift_date", "gift_property_value"]
        ... )
        "증여일이 언제인가요?\\n\\n💡 증여세는 증여일을 기준으로..."
    """
    next_param = get_next_question(collected_parameters, missing_parameters)

    if next_param is None:
        return None  # 계산 가능

    # 질문 템플릿 반환
    return CLARIFYING_QUESTIONS.get(
        next_param,
        f"{next_param}을(를) 알려주세요."
    )


async def generate_clarifying_question_dynamic(
    collected_parameters: Dict,
    missing_parameters: List[str],
    user_message: str,
    conversation_history: Optional[List] = None
) -> Optional[str]:
    """
    LLM을 사용한 동적 Clarifying 질문 생성

    매번 다른 표현으로 질문을 생성하여 대화가 자연스럽게 흐르도록 합니다.
    LLM 호출 실패 시 템플릿 기반 폴백을 사용합니다.

    Args:
        collected_parameters: 현재까지 수집된 파라미터
        missing_parameters: 누락된 Tier 1 변수 목록
        user_message: 사용자의 최근 메시지
        conversation_history: 대화 히스토리 (향후 활용, 현재는 미사용)

    Returns:
        str | None: 질문 텍스트 또는 None (계산 가능)

    Example:
        >>> await generate_clarifying_question_dynamic(
        ...     {"donor_relationship": "직계존속", "gift_property_value": 1000000000},
        ...     ["gift_date"],
        ...     "부모님께 10억 받았어요"
        ... )
        "10억원이시군요! 그럼 언제 증여받으셨는지도 알려주시겠어요?"
    """
    next_param = get_next_question(collected_parameters, missing_parameters)

    if next_param is None:
        return None  # 계산 가능

    try:
        # 가이드라인 가져오기 (템플릿에서)
        param_guideline = CLARIFYING_QUESTIONS.get(next_param, "해당 정보를 수집하세요.")

        # 수집 완료 정보 요약
        collected_summary = ", ".join([
            f"{k}: {v}" for k, v in collected_parameters.items() if v is not None
        ]) or "없음"

        # 프롬프트 포맷팅
        prompt = QUESTION_GENERATION_PROMPT.format(
            collected_params_summary=collected_summary,
            next_param=next_param,
            user_message=user_message,
            param_guideline=param_guideline
        )

        # Gemini API 호출
        settings = GeminiSettings.from_env()
        client = GeminiClient(settings)

        question = await client.generate_content(
            system_prompt=prompt,
            user_message="위 상황에 맞는 자연스러운 질문을 생성해주세요. 매번 다른 표현을 사용하세요."
        )

        LOGGER.info(f"Dynamic question generated for {next_param}: {question[:50]}...")
        return question.strip()

    except GeminiClientError as e:
        # LLM 호출 실패 시 템플릿 폴백
        LOGGER.warning(f"Dynamic question generation failed: {e}. Using template fallback.")
        return generate_clarifying_question(collected_parameters, missing_parameters)
