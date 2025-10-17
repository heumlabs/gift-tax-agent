"""
LangGraph Workflow (Phase 3 - 문서 기준 재설계)

문서 기반 단순 파이프라인:
START → intent_node → clarifying_node → [누락?]
                                         ├─ YES → 질문 반환 → END
                                         └─ NO → calculation_node → synthesis_node → END

주요 개선:
- Agent 개념 제거 (문서와 일치)
- Intent는 첫 턴에만 분류 (collected_parameters 있으면 건너뜀)
- Clarifying, Calculation, Synthesis 노드 명확히 분리
- Exit Detection 키워드 기반 단순화
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date

from langgraph.graph import END, START, StateGraph

from ai.clients.gemini import GeminiClient
from ai.config import GeminiSettings
from ai.exceptions import GeminiClientError
from ai.prompts import DEFAULT_SYSTEM_PROMPT, INTENT_CLASSIFICATION_PROMPT
from ai.prompts.clarifying import SYNTHESIS_PROMPT
from ai.schemas.workflow_state import WorkflowState
# exit_detection은 이제 LLM 기반으로 clarifying_node 내부에서 직접 처리
from ai.utils.parameter_extraction import (
    check_missing_parameters,
    extract_parameters,
    generate_clarifying_question,
)

LOGGER = logging.getLogger(__name__)


# ============================================================================
# 헬퍼 함수
# ============================================================================

def _get_tax_bracket_info(taxable_base: int) -> str:
    """
    과세표준에 해당하는 세율 구간 정보 반환

    Args:
        taxable_base: 과세표준

    Returns:
        str: 세율 구간 설명
    """
    if taxable_base == 0:
        return "과세표준 0원 (세금 없음)"

    # 증여세 세율 구간
    if taxable_base <= 100_000_000:
        return "1억 이하 (세율 10%)"
    elif taxable_base <= 500_000_000:
        return "1억 초과 5억 이하 (세율 20%)"
    elif taxable_base <= 1_000_000_000:
        return "5억 초과 10억 이하 (세율 30%)"
    elif taxable_base <= 3_000_000_000:
        return "10억 초과 30억 이하 (세율 40%)"
    else:
        return "30억 초과 (세율 50%)"


async def _synthesize_response(calculation: dict, collected_parameters: dict, intent: str) -> str:
    """
    계산 결과를 자연어로 변환

    Args:
        calculation: 계산 결과
        collected_parameters: 수집된 파라미터
        intent: gift_tax | inheritance_tax

    Returns:
        str: 자연어 답변
    """
    # 1. steps 포맷팅
    steps_text = "\n".join([
        f"{s['step']}. {s['description']}: {s['value']:,}원 ({s.get('detail', '')})"
        for s in calculation.get("steps", [])
    ])

    # 2. warnings 포맷팅
    warnings_text = "\n".join([f"- {w}" for w in calculation.get("warnings", [])])

    # 3. 세율 구간 정보 생성
    taxable_base = calculation.get("taxable_base", 0)
    tax_bracket_info = _get_tax_bracket_info(taxable_base)

    # 4. Gemini API로 자연어 설명 생성
    try:
        settings = GeminiSettings.from_env()
        client = GeminiClient(settings)

        prompt = SYNTHESIS_PROMPT.format(
            final_tax=calculation["final_tax"],
            gift_value=calculation.get("gift_value", collected_parameters.get("gift_property_value", 0)),
            total_deduction=calculation.get("total_deduction", 0),
            taxable_base=taxable_base,
            tax_bracket_info=tax_bracket_info,
            steps_formatted=steps_text,
            warnings_formatted=warnings_text
        )

        response = await client.generate_content(
            system_prompt=prompt,
            user_message=f"관계: {collected_parameters.get('donor_relationship', '알 수 없음')}, 금액: {collected_parameters.get('gift_property_value', 0):,}원"
        )

        LOGGER.info("Synthesis successful")
        return response

    except Exception as e:
        LOGGER.error(f"Synthesis error: {e}")
        # Fallback: 템플릿 기반 응답
        fallback_response = f"""증여세 계산 결과입니다.

**최종 납부 세액**: {calculation['final_tax']:,}원

**계산 단계**:
{steps_text}

**주의사항**:
{warnings_text}

본 안내는 정보 제공용이며, 정확한 세액은 세무 전문가와 상담하시기 바랍니다."""

        return fallback_response


# ============================================================================
# 노드들 (문서 기준)
# ============================================================================

async def intent_node(state: WorkflowState) -> dict:
    """
    Intent 분류 노드

    첫 턴에만 실행됩니다 (collected_parameters 없을 때).
    사용자의 의도를 파악하여 gift_tax, inheritance_tax, general_info, out_of_scope로 분류합니다.

    Args:
        state: 현재 workflow 상태

    Returns:
        dict: 업데이트할 상태
            - intent: "gift_tax" | "inheritance_tax" | "general_info" | "out_of_scope"
    """
    user_message = state.get("user_message", "")

    try:
        # Gemini API를 통한 Intent 분류
        settings = GeminiSettings.from_env()
        client = GeminiClient(settings)

        intent_raw = await client.generate_content(
            system_prompt=INTENT_CLASSIFICATION_PROMPT,
            user_message=user_message
        )

        # 응답에서 공백/개행 제거 후 소문자로 정규화
        intent = intent_raw.strip().lower()

        # 유효한 intent인지 검증
        valid_intents = ["gift_tax", "inheritance_tax", "general_info", "out_of_scope"]
        if intent not in valid_intents:
            LOGGER.warning(f"Invalid intent from Gemini: {intent}. Defaulting to general_info.")
            intent = "general_info"

        LOGGER.info(f"Intent classified: {intent}")

        return {
            "intent": intent
        }

    except GeminiClientError:
        # API 오류 시 안전하게 fallback
        LOGGER.exception("Intent classification error")
        return {
            "intent": "general_info"
        }


async def clarifying_node(state: WorkflowState) -> dict:
    """
    Clarifying 노드: 파라미터 수집 및 질문 생성

    역할:
    1. Intent Re-classification (LLM 기반) - 사용자 의도 변화 감지
    2. Parameter Extraction (Gemini API)
    3. Missing Parameter Check
    4. Clarifying Question Generation

    Args:
        state: WorkflowState

    Returns:
        dict: 업데이트할 상태
            - collected_parameters: 병합된 파라미터
            - missing_parameters: 누락 목록
            - response: 질문 텍스트 (있는 경우) 또는 None (계산 진행)
            - intent: 변경된 intent (이탈/전환 시)
    """
    user_message = state.get("user_message", "")
    current_intent = state.get("intent", "gift_tax")
    # collected_parameters가 None이면 빈 딕셔너리로 초기화
    collected = (state.get("collected_parameters") or {}).copy()  # 복사본 생성

    # Step 1: Intent Re-classification (LLM 기반)
    # Clarifying 중에도 매 턴마다 사용자의 의도 변화를 감지
    from ai.prompts.clarifying import CLARIFYING_INTENT_DETECTION_PROMPT
    import json

    settings = GeminiSettings.from_env()
    client = GeminiClient(settings)

    response = None  # 초기화
    try:
        # 현재 intent를 한글로 변환
        intent_kr = "증여세" if current_intent == "gift_tax" else "상속세" if current_intent == "inheritance_tax" else "세금"

        prompt = CLARIFYING_INTENT_DETECTION_PROMPT.format(
            current_intent=intent_kr,
            user_message=user_message
        )

        response = await client.generate_content(
            system_prompt="",
            user_message=prompt
        )

        LOGGER.info(f"Raw LLM response for intent re-classification: {response}")

        # JSON 파싱 (마크다운 코드 블록 제거)
        response_cleaned = response.strip()
        if response_cleaned.startswith("```json"):
            response_cleaned = response_cleaned[7:]  # ```json 제거
        if response_cleaned.startswith("```"):
            response_cleaned = response_cleaned[3:]  # ``` 제거
        if response_cleaned.endswith("```"):
            response_cleaned = response_cleaned[:-3]  # ``` 제거
        response_cleaned = response_cleaned.strip()

        result = json.loads(response_cleaned)
        detected_intent = result.get("intent", "continue")
        reasoning = result.get("reasoning", "")

        LOGGER.info(f"Intent re-classification: {detected_intent} (reasoning: {reasoning})")

    except (json.JSONDecodeError, GeminiClientError):
        LOGGER.exception("Failed to detect intent with LLM. Defaulting to 'continue'. Response was: %s", response)
        detected_intent = "continue"

    # Step 2: Intent에 따른 분기 처리
    if detected_intent == "exit":
        LOGGER.info("User requested to exit calculation.")
        # LLM을 사용하여 자연스러운 종료 응답 생성
        try:
            exit_response = await client.generate_content(
                system_prompt="당신은 세금 계산을 도와주는 AI입니다. 사용자가 계산을 중단하려고 합니다. 자연스럽고 친절하게 응답하세요.",
                user_message=user_message
            )
        except GeminiClientError:
            LOGGER.exception("Failed to generate exit response")
            exit_response = "알겠습니다. 다른 궁금한 점이 있으시면 언제든 말씀해주세요."

        return {
            "response": exit_response,
            "collected_parameters": {},  # 초기화
            "missing_parameters": [],
            "intent": "out_of_scope"
        }

    if detected_intent == "switch_to_inheritance":
        LOGGER.info("User requested to switch to inheritance tax.")
        # LLM을 사용하여 자연스러운 모드 전환 응답 생성
        try:
            switch_response = await client.generate_content(
                system_prompt="당신은 세금 계산을 도와주는 AI입니다. 사용자가 증여세에서 상속세 계산으로 전환하려고 합니다. 자연스럽게 모드 전환을 안내하세요.",
                user_message=user_message
            )
        except GeminiClientError:
            LOGGER.exception("Failed to generate switch to inheritance response")
            switch_response = "상속세 계산으로 변경하겠습니다. 필요한 정보를 여쭤볼게요."

        return {
            "collected_parameters": {},  # 초기화
            "missing_parameters": [],
            "intent": "inheritance_tax",
            "response": switch_response
        }

    if detected_intent == "switch_to_gift":
        LOGGER.info("User requested to switch to gift tax.")
        # LLM을 사용하여 자연스러운 모드 전환 응답 생성
        try:
            switch_response = await client.generate_content(
                system_prompt="당신은 세금 계산을 도와주는 AI입니다. 사용자가 상속세에서 증여세 계산으로 전환하려고 합니다. 자연스럽게 모드 전환을 안내하세요.",
                user_message=user_message
            )
        except GeminiClientError:
            LOGGER.exception("Failed to generate switch to gift response")
            switch_response = "증여세 계산으로 변경하겠습니다. 필요한 정보를 여쭤볼게요."

        return {
            "collected_parameters": {},  # 초기화
            "missing_parameters": [],
            "intent": "gift_tax",
            "response": switch_response
        }

    if detected_intent == "general_info":
        LOGGER.info("User asked a general question during clarifying.")
        # 일반 질문으로 전환 - response_node에서 처리
        return {
            "intent": "general_info",
            "response": None  # response_node에서 생성
        }

    # detected_intent == "continue": 정상 진행 (파라미터 계속 수집)

    # Step 3: Parameter Extraction (이전 컨텍스트 포함)
    try:
        new_params = await extract_parameters(user_message, collected)
        LOGGER.info(f"Extracted parameters: {new_params}")
    except Exception as e:
        LOGGER.error(f"Parameter extraction error: {e}")
        new_params = {}

    # Step 3: 파라미터 병합 (null이 아닌 모든 변수)
    # 사용자가 자발적으로 제공한 Tier 2/3 정보도 반영
    for key, value in new_params.items():
        if value is not None:
            collected[key] = value

    # Step 4: 필수 변수 체크 (Tier 1)
    missing = check_missing_parameters(collected)

    # Step 5: 질문 생성 또는 계산 진행
    if missing:
        question = generate_clarifying_question(collected, missing)
        LOGGER.info(f"Missing parameters: {missing}. Generating question.")
        return {
            "collected_parameters": collected,
            "missing_parameters": missing,
            "response": question
        }

    # 모든 Tier 1 변수 수집 완료 → 계산 진행
    LOGGER.info("All Tier 1 parameters collected. Ready for calculation.")
    return {
        "collected_parameters": collected,
        "missing_parameters": []
    }


async def calculation_node(state: WorkflowState) -> dict:
    """
    계산 노드: GiftTaxSimpleInput 생성 및 Tool 호출

    Args:
        state: WorkflowState
            - collected_parameters: 9개 변수 완성

    Returns:
        dict: 업데이트할 상태
            - metadata.calculation: 계산 결과
    """
    collected = state.get("collected_parameters") or {}

    LOGGER.info("Starting calculation...")

    # 날짜 문자열 → date 객체
    from ai.tools import calculate_gift_tax_simple
    from ai.tools.gift_tax.models import GiftTaxSimpleInput

    try:
        gift_date_str = collected.get("gift_date")
        if isinstance(gift_date_str, str):
            gift_date_obj = date.fromisoformat(gift_date_str)
        else:
            gift_date_obj = gift_date_str

        # GiftTaxSimpleInput 생성 (Tier 2/3 기본값 추가)
        tax_input = GiftTaxSimpleInput(
            gift_date=gift_date_obj,
            donor_relationship=collected["donor_relationship"],
            gift_property_value=collected["gift_property_value"],
            is_generation_skipping=collected.get("is_generation_skipping", False),
            is_minor_recipient=collected.get("is_minor_recipient", False),
            is_non_resident=collected.get("is_non_resident", False),
            marriage_deduction_amount=collected.get("marriage_deduction_amount", 0),
            childbirth_deduction_amount=collected.get("childbirth_deduction_amount", 0),
            secured_debt=collected.get("secured_debt", 0),
        )

        # 계산 Tool 호출 (현재 날짜 전달)
        tax_params = tax_input.model_dump()
        result = calculate_gift_tax_simple(**tax_params, current_date=date.today())
        LOGGER.info(f"Calculation successful: final_tax={result['final_tax']}")

        return {
            "metadata": {"calculation": result}
        }

    except Exception as e:
        LOGGER.error(f"Calculation error: {e}")
        return {
            "response": f"계산 중 오류가 발생했습니다: {str(e)}",
            "metadata": {}
        }


async def synthesis_node(state: WorkflowState) -> dict:
    """
    답변 합성 노드: 계산 결과를 자연어로 변환

    Args:
        state: WorkflowState
            - metadata.calculation: 계산 결과
            - collected_parameters: 수집된 파라미터

    Returns:
        dict: 업데이트할 상태
            - response: 자연어 답변
    """
    calculation = state.get("metadata", {}).get("calculation")
    collected = state.get("collected_parameters") or {}
    intent = state.get("intent", "gift_tax")

    if not calculation:
        LOGGER.error("No calculation result found in metadata")
        return {
            "response": "계산 결과를 찾을 수 없습니다."
        }

    # 자연어 답변 생성
    response = await _synthesize_response(calculation, collected, intent)

    return {
        "response": response
    }


async def response_node(state: WorkflowState) -> dict:
    """
    Response 생성 노드 (일반 정보 또는 out_of_scope)

    Clarifying 노드에서 이미 response를 생성한 경우 그대로 반환합니다.
    그렇지 않으면 intent에 따라 응답을 생성합니다.

    Args:
        state: 현재 workflow 상태

    Returns:
        업데이트할 상태 (response 필드)
    """
    intent = state.get("intent", "general_info")
    user_message = state.get("user_message", "")

    # Clarifying 노드에서 이미 response를 생성한 경우 그대로 반환
    if state.get("response"):
        return {}

    # Intent별 응답 생성
    if intent == "out_of_scope":
        response = "죄송합니다. 저는 증여세와 상속세 관련 상담만 도와드릴 수 있습니다. 증여세나 상속세 관련 질문이 있으시면 말씀해 주세요."
    elif intent == "inheritance_tax":
        response = "상속세 관련 안내를 드리겠습니다."
    elif intent == "general_info":
        # Gemini API 호출
        try:
            settings = GeminiSettings.from_env()
            client = GeminiClient(settings)
            response = await client.generate_content(
                system_prompt=DEFAULT_SYSTEM_PROMPT,
                user_message=user_message
            )
        except GeminiClientError:
            LOGGER.exception("Failed to generate general info response")
            response = "죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
    else:
        response = "증여세 계산을 도와드리겠습니다."

    return {"response": response}


# ============================================================================
# Workflow 라우팅 함수들
# ============================================================================

def should_skip_intent(state: WorkflowState) -> str:
    """
    Intent 분류를 건너뛸지 판단

    collected_parameters가 있으면 Clarifying 모드 → Intent 건너뜀
    없으면 첫 턴 → Intent 분류

    Args:
        state: 현재 workflow 상태

    Returns:
        str: "intent" | "clarifying"
    """
    collected = state.get("collected_parameters")

    # collected_parameters가 존재하면 (빈 딕셔너리라도) Clarifying 모드
    if collected is not None:
        # Clarifying 모드: Intent 건너뛰기
        LOGGER.info("Clarifying mode detected. Skipping intent classification.")
        return "clarifying"
    else:
        # 첫 턴: Intent 분류
        LOGGER.info("First turn. Classifying intent.")
        return "intent"


def route_from_intent(state: WorkflowState) -> str:
    """
    Intent → 다음 노드 라우팅

    Args:
        state: 현재 workflow 상태

    Returns:
        str: "clarifying" | "response"
    """
    intent = state.get("intent", "general_info")

    if intent in ["gift_tax", "inheritance_tax"]:
        LOGGER.info(f"Intent {intent} routed to clarifying.")
        return "clarifying"
    else:
        LOGGER.info(f"Intent {intent} routed to response.")
        return "response"


def should_calculate(state: WorkflowState) -> str:
    """
    계산 가능 여부 판단

    Returns:
        "response": 질문 필요 (missing_parameters 있음 또는 이탈) 또는 일반 정보 응답
        "calculation": 계산 가능 (필수 변수 모두 수집)
    """
    # 의도에 따라 즉시 응답 경로로 분기
    intent = state.get("intent")
    if intent in ("general_info", "out_of_scope"):
        return "response"

    missing = state.get("missing_parameters", [])
    response = state.get("response")

    # response가 있으면 질문 또는 이탈 메시지 → END
    if response:
        return "response"

    # missing_parameters가 비어있으면 계산 진행
    if len(missing) == 0:
        return "calculation"
    else:
        return "response"


# ============================================================================
# Workflow 생성
# ============================================================================

def create_workflow() -> StateGraph:
    """
    LangGraph Workflow 생성 (Phase 3 - 문서 기준)

    흐름:
    START → [collected_parameters 있음?]
             ├─ NO → intent → [intent=?]
             │                 ├─ "gift_tax/inheritance_tax" → clarifying → [누락?]
             │                 │                                               ├─ YES → response → END
             │                 │                                               └─ NO → calculation → synthesis → END
             │                 └─ "general_info/out_of_scope" → response → END
             │
             └─ YES → clarifying (Intent 건너뛰기) → [누락?]
                                                      ├─ YES → response → END
                                                      └─ NO → calculation → synthesis → END

    Returns:
        컴파일된 StateGraph
    """
    # StateGraph 생성
    workflow = StateGraph(WorkflowState)

    # 노드 추가
    workflow.add_node("intent", intent_node)
    workflow.add_node("clarifying", clarifying_node)
    workflow.add_node("calculation", calculation_node)
    workflow.add_node("synthesis", synthesis_node)
    workflow.add_node("response", response_node)

    # START → intent or clarifying
    workflow.add_conditional_edges(
        START,
        should_skip_intent,
        {
            "intent": "intent",
            "clarifying": "clarifying"
        }
    )

    # intent → clarifying or response
    workflow.add_conditional_edges(
        "intent",
        route_from_intent,
        {
            "clarifying": "clarifying",
            "response": "response"
        }
    )

    # clarifying → calculation or response
    workflow.add_conditional_edges(
        "clarifying",
        should_calculate,
        {
            "calculation": "calculation",
            "response": "response"
        }
    )

    # calculation → synthesis
    workflow.add_edge("calculation", "synthesis")

    # synthesis → END
    workflow.add_edge("synthesis", END)

    # response → END
    workflow.add_edge("response", END)

    # 컴파일
    return workflow.compile()


async def run_workflow(
    user_message: str,
    session_id: str = "default",
    previous_collected_parameters: dict | None = None
) -> WorkflowState:
    """
    Workflow 실행 헬퍼 함수 (비동기)

    Phase 3에서 멀티턴 대화 지원을 위해 previous_collected_parameters 추가

    Args:
        user_message: 사용자 입력 메시지
        session_id: 세션 ID (기본값: "default")
        previous_collected_parameters: 이전까지 수집된 파라미터 (누적)

    Returns:
        최종 WorkflowState
    """
    graph = create_workflow()

    # 초기 상태 (이전 파라미터 포함)
    # 첫 턴(previous_collected_parameters가 None)일 때는 None 유지 → Intent 분류 실행
    # 두 번째 턴 이후(빈 dict 또는 값 있는 dict)일 때는 그대로 전달 → Clarifying 모드
    initial_state: WorkflowState = {
        "session_id": session_id,
        "user_message": user_message,
        "messages": [],
        "collected_parameters": previous_collected_parameters,  # None or dict
        "missing_parameters": [],
        "metadata": {},
    }

    # Workflow 실행 (비동기)
    final_state = await graph.ainvoke(initial_state)

    return final_state
