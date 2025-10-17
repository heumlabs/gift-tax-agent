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
from ai.prompts.intent import CLARIFYING_INTENT_DETECTION_PROMPT
from ai.prompts.synthesis import SYNTHESIS_PROMPT, get_synthesis_prompt_with_examples
from ai.schemas.workflow_state import WorkflowState
# exit_detection은 이제 LLM 기반으로 clarifying_node 내부에서 직접 처리
from ai.utils.parameter_extraction import (
    check_missing_parameters,
    extract_parameters,
    generate_clarifying_question,
    generate_clarifying_question_dynamic,
)

LOGGER = logging.getLogger(__name__)


# ============================================================================
# 헬퍼 함수
# ============================================================================

def _should_include_legal_basis(collected_parameters: dict, breakdown: dict) -> bool:
    """
    법령 근거 포함 여부 판단.

    특례 적용 시 법령 근거를 제공하여 신뢰도를 높입니다.

    Args:
        collected_parameters: 수집된 파라미터
        breakdown: 계산 상세 정보

    Returns:
        bool: 법령 근거 포함 여부
    """
    # 세대생략 증여 할증
    if breakdown.get("is_generation_skipping", False):
        return True

    # 혼인공제
    if breakdown.get("marriage_deduction", 0) > 0:
        return True

    # 출산공제
    if breakdown.get("childbirth_deduction", 0) > 0:
        return True

    # 미성년자 공제
    if breakdown.get("is_minor_recipient", False):
        return True

    # 비거주자
    if breakdown.get("is_non_resident", False):
        return True

    return False


def _generate_law_search_queries(collected_parameters: dict, breakdown: dict) -> list[str]:
    """
    파라미터 기반 법령 검색 쿼리 생성.

    Args:
        collected_parameters: 수집된 파라미터
        breakdown: 계산 상세 정보

    Returns:
        list[str]: 검색 쿼리 목록 (최대 3개)
    """
    queries = []

    # 기본 공제 (관계별)
    donor_relationship = collected_parameters.get("donor_relationship", "")
    if donor_relationship:
        queries.append(f"{donor_relationship} 증여재산 공제")

    # 특례 관련 쿼리
    if breakdown.get("is_generation_skipping", False):
        queries.append("세대생략 증여 할증")

    if breakdown.get("marriage_deduction", 0) > 0:
        queries.append("혼인공제")

    if breakdown.get("childbirth_deduction", 0) > 0:
        queries.append("출산공제")

    if breakdown.get("is_minor_recipient", False):
        queries.append("미성년자 증여 공제")

    # 최대 3개로 제한
    return queries[:3]


def _format_legal_references(citations: list[dict]) -> str:
    """
    법령 인용 포맷팅.

    Args:
        citations: 법령 검색 결과 (LawSearchResult.citations)

    Returns:
        str: 포맷된 법령 근거 (마크다운)
    """
    if not citations:
        return ""

    formatted = ["**법적 근거**:"]
    for cite in citations[:20]:  # 최대 20개로 증가
        ref = cite.get("full_reference", "")
        content = cite.get("content", "")

        # 내용이 너무 길면 200자로 제한 (더 많은 컨텍스트 제공)
        if len(content) > 200:
            content = content[:200] + "..."

        formatted.append(f"- {ref}: {content}")

    return "\n".join(formatted)


async def _extract_law_keywords_from_question(user_message: str) -> list[str]:
    """
    일반 정보 질문에서 법령 검색 키워드 추출.

    Args:
        user_message: 사용자 질문

    Returns:
        list[str]: 법령 검색 키워드 (최대 3개)

    Examples:
        "증여세 공제가 뭐예요?" → ["증여재산공제"]
        "혼인공제 받으려면?" → ["혼인공제"]
        "주식 증여 세금" → ["주식 증여", "증여세율"]
    """
    # 주요 키워드 매핑
    keyword_map = {
        "공제": ["증여재산공제", "배우자 공제", "직계존속 공제"],
        "혼인공제": ["혼인공제"],
        "출산공제": ["출산공제"],
        "세율": ["증여세율"],
        "세대생략": ["세대생략 증여 할증"],
        "할증": ["세대생략 증여 할증"],
        "신고": ["증여세 신고"],
        "기한": ["증여세 신고기한"],
        "주식": ["주식 증여", "주식 평가"],
        "부동산": ["부동산 증여"],
        "평가": ["재산 평가"],
        "비거주자": ["비거주자 증여"],
        "미성년자": ["미성년자 공제"],
    }

    queries = []
    message_lower = user_message.lower()

    # 키워드 매칭
    for keyword, search_terms in keyword_map.items():
        if keyword in message_lower:
            queries.extend(search_terms)

    # 매칭 안되면 기본 쿼리
    if not queries:
        if "증여" in message_lower:
            queries.append("증여세")
        elif "상속" in message_lower:
            queries.append("상속세")
        else:
            queries.append("증여세")  # 기본값

    # 중복 제거 및 최대 3개
    return list(dict.fromkeys(queries))[:3]


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
    계산 결과를 자연어로 변환 (V2 - 개선판)

    Args:
        calculation: 계산 결과
        collected_parameters: 수집된 파라미터
        intent: gift_tax | inheritance_tax

    Returns:
        str: 자연어 답변
    """
    # 1. 포맷된 금액 추출
    formatted = calculation.get("formatted_amounts", {})

    # 2. 세율 구간 정보 (계산 결과에서 직접 가져오기)
    bracket_info = calculation.get("tax_bracket_info", {})

    # 3. 계산 상세 정보
    breakdown = calculation.get("calculation_breakdown", {})

    # 4. steps 포맷팅 (한글 금액 사용)
    steps_text = "\n".join([
        f"{s['step']}. {s['description']}: {s['value']:,}원 ({s.get('detail', '')})"
        for s in calculation.get("steps", [])
    ])

    # 5. warnings 포맷팅
    warnings_text = "\n".join([f"- {w}" for w in calculation.get("warnings", [])])

    # 6. Tier 2/3 누락 확인 (추가 확인사항)
    optional_params_notice = _check_optional_parameters(collected_parameters, breakdown)

    # 7. 법령 근거 검색 (선택적)
    legal_references = ""
    if _should_include_legal_basis(collected_parameters, breakdown):
        try:
            from ai.tools.law_search.wrapper import search_law_tool

            # 검색 쿼리 생성
            queries = _generate_law_search_queries(collected_parameters, breakdown)
            LOGGER.info(f"Searching law for queries: {queries}")

            # 각 쿼리별로 검색 (비동기 처리 가능하지만 단순화를 위해 순차 처리)
            all_citations = []
            for query in queries:
                result = search_law_tool(query, top_k=10)  # 쿼리당 10개로 증가 (3개 쿼리 × 10개 = 최대 30개)
                citations = result.get("citations", [])
                all_citations.extend(citations)

            # 법령 근거 포맷팅
            legal_references = _format_legal_references(all_citations)
            LOGGER.info(f"Found {len(all_citations)} legal references")

        except Exception as e:
            LOGGER.warning(f"Law search failed: {e}. Continuing without legal references.")
            legal_references = ""

    # 8. Gemini API로 자연어 설명 생성
    try:
        settings = GeminiSettings.from_env()
        client = GeminiClient(settings)

        # 프롬프트 데이터 준비 (RAG 통합 + 포맷된 금액)
        import json
        calculation_data = {
            "final_tax": calculation["final_tax"],
            "formatted_final_tax": formatted.get("final_tax", f"{calculation['final_tax']:,}원"),
            "gift_value": calculation.get("gift_value", 0),
            "formatted_gift_value": formatted.get("gift_value", ""),
            "total_deduction": calculation.get("total_deduction", 0),
            "formatted_total_deduction": formatted.get("total_deduction", ""),
            "taxable_base": calculation.get("taxable_base", 0),
            "formatted_taxable_base": formatted.get("taxable_base", ""),
            "calculated_tax": calculation.get("calculated_tax", 0),
            "formatted_calculated_tax": formatted.get("calculated_tax", ""),
            "surtax": calculation.get("surtax", 0),
            "formatted_surtax": formatted.get("surtax", ""),
            "tax_bracket": bracket_info.get("description", ""),
            "bracket_rate": bracket_info.get("rate", 0),
            "breakdown": breakdown,
            "warnings": calculation.get("warnings", []),
            "optional_params_notice": optional_params_notice,
            "legal_references": legal_references,  # RAG 법령 근거
        }

        # Few-shot 예제를 포함한 전체 프롬프트 사용
        full_prompt = get_synthesis_prompt_with_examples()

        response = await client.generate_content(
            system_prompt=full_prompt.format(
                final_tax=calculation_data["final_tax"],
                gift_value=calculation_data["gift_value"],
                total_deduction=calculation_data["total_deduction"],
                taxable_base=calculation_data["taxable_base"],
                tax_bracket_info=bracket_info.get("description", _get_tax_bracket_info(calculation_data["taxable_base"])),
                steps_formatted=steps_text,
                warnings_formatted=warnings_text,
                donor_relationship=collected_parameters.get("donor_relationship", "알 수 없음"),
                gift_property_value=collected_parameters.get("gift_property_value", 0),
                legal_references=legal_references  # RAG 법령 근거 추가
            ),
            user_message=f"""위 계산 결과를 자연스럽게 설명해주세요. 매번 다른 표현과 형식을 사용하세요.

추가 컨텍스트:
{json.dumps(calculation_data, ensure_ascii=False, indent=2)}"""
        )

        LOGGER.info("Synthesis successful")
        return response

    except Exception as e:
        LOGGER.error(f"Synthesis error: {e}")
        # Fallback: 개선된 템플릿 기반 응답 (한글 포맷 + RAG)
        fallback_response = _generate_fallback_response(
            calculation, collected_parameters, formatted, breakdown, bracket_info, legal_references
        )
        return fallback_response


def _check_optional_parameters(collected_parameters: dict, breakdown: dict) -> str:
    """
    Tier 2/3 파라미터 누락 확인 및 안내 메시지 생성.

    Args:
        collected_parameters: 수집된 파라미터
        breakdown: 계산 상세 정보

    Returns:
        str: 추가 확인사항 메시지 (없으면 빈 문자열)
    """
    missing_items = []

    # Tier 2/3 기본값 사용 여부 확인
    if not breakdown.get("is_generation_skipping", False) and collected_parameters.get("donor_relationship") in ["직계존속", "직계비속"]:
        # 세대생략 여부를 확인하지 않은 경우
        missing_items.append("세대생략 증여 여부")

    if breakdown.get("marriage_deduction", 0) == 0:
        missing_items.append("혼인공제")

    if breakdown.get("childbirth_deduction", 0) == 0:
        missing_items.append("출산공제")

    if collected_parameters.get("secured_debt", 0) == 0:
        missing_items.append("담보채무")

    if missing_items:
        return f"참고로, {', '.join(missing_items)} 등을 고려하면 세액이 달라질 수 있습니다."

    return ""


def _generate_fallback_response(
    calculation: dict,
    collected_parameters: dict,
    formatted: dict,
    breakdown: dict,
    bracket_info: dict,
    legal_references: str = ""
) -> str:
    """
    Gemini API 실패 시 사용할 개선된 Fallback 응답 생성.

    Args:
        calculation: 계산 결과
        collected_parameters: 수집된 파라미터
        formatted: 한글 포맷 금액들
        breakdown: 계산 상세 정보
        bracket_info: 세율 구간 정보
        legal_references: 법령 근거 (있는 경우)

    Returns:
        str: Fallback 응답
    """
    relationship = collected_parameters.get("donor_relationship", "알 수 없음")
    gift_value = formatted.get("gift_value", f"{calculation.get('gift_value', 0):,}원")
    total_deduction = formatted.get("total_deduction", f"{calculation.get('total_deduction', 0):,}원")
    taxable_base = formatted.get("taxable_base", f"{calculation.get('taxable_base', 0):,}원")
    final_tax = formatted.get("final_tax", f"{calculation.get('final_tax', 0):,}원")

    # 관계별 설명
    relationship_desc = {
        "배우자": "배우자로부터",
        "직계존속": "부모님(직계존속)으로부터",
        "직계비속": "자녀(직계비속)에게",
        "기타친족": "친족으로부터",
    }.get(relationship, f"{relationship}로부터")

    # 응답 구조
    response_parts = [
        f"## 증여세 계산 결과\n",
        f"{relationship_desc} {gift_value} 증여받으신 경우입니다.\n",
        f"**최종 납부 세액: {final_tax}**\n",
        f"\n### 상세 계산\n",
        f"- 증여재산가액: {gift_value}",
        f"- 공제액: {total_deduction}",
        f"- 과세표준: {taxable_base}",
    ]

    # 세율 구간 정보
    if bracket_info.get("description"):
        response_parts.append(f"- {bracket_info['description']}")

    # 산출세액
    calculated_tax = formatted.get("calculated_tax", "")
    if calculated_tax:
        response_parts.append(f"- 산출세액: {calculated_tax}")

    # 할증 세액
    if calculation.get("surtax", 0) > 0:
        surtax = formatted.get("surtax", "")
        response_parts.append(f"- 세대생략 할증 30%: {surtax}")

    response_parts.append(f"- **최종 납부 세액: {final_tax}**")

    # 추가 확인사항
    optional_notice = _check_optional_parameters(collected_parameters, breakdown)
    if optional_notice:
        response_parts.append(f"\n### 추가 확인사항\n{optional_notice}")

    # 신고 기한
    warnings = calculation.get("warnings", [])
    if warnings:
        response_parts.append(f"\n### 신고 기한")
        for warning in warnings:
            response_parts.append(f"- {warning}")

    # 법령 근거 (있는 경우)
    if legal_references:
        response_parts.append(f"\n{legal_references}")

    # 참고사항
    response_parts.append("\n### 참고사항")
    response_parts.append("본 안내는 간편 계산 결과이며, 정확한 세액은 세무 전문가와 상담하시기 바랍니다.")

    return "\n".join(response_parts)


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
        # 동적 질문 생성 (LLM 기반)
        question = await generate_clarifying_question_dynamic(
            collected_parameters=collected,
            missing_parameters=missing,
            user_message=user_message,
            conversation_history=state.get("messages", [])
        )
        LOGGER.info(f"Missing parameters: {missing}. Generating dynamic question.")
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
        # RAG를 활용한 일반 정보 응답 생성
        try:
            settings = GeminiSettings.from_env()
            client = GeminiClient(settings)

            # 1. 법령 검색 키워드 추출
            law_keywords = await _extract_law_keywords_from_question(user_message)
            LOGGER.info(f"Extracted law keywords for general_info: {law_keywords}")

            # 2. 법령 검색 수행
            legal_references = ""
            if law_keywords:
                try:
                    from ai.tools.law_search.wrapper import search_law_tool

                    all_citations = []
                    for query in law_keywords:
                        result = search_law_tool(query, top_k=5)  # 일반 QA는 쿼리당 5개
                        citations = result.get("citations", [])
                        all_citations.extend(citations)

                    # 법령 근거 포맷팅 (최대 10개 표시)
                    if all_citations:
                        formatted = ["**관련 법령 근거**:"]
                        for cite in all_citations[:10]:
                            ref = cite.get("full_reference", "")
                            content = cite.get("content", "")
                            if len(content) > 150:
                                content = content[:150] + "..."
                            formatted.append(f"- {ref}: {content}")
                        legal_references = "\n".join(formatted)
                        LOGGER.info(f"Found {len(all_citations)} legal references for general_info")

                except Exception as e:
                    LOGGER.warning(f"Law search failed in general_info: {e}")
                    legal_references = ""

            # 3. Gemini에게 법령 근거와 함께 전달
            if legal_references:
                enhanced_prompt = f"""{DEFAULT_SYSTEM_PROMPT}

아래 법령 근거를 참고하여 정확하고 상세하게 답변해주세요:

{legal_references}"""
                response = await client.generate_content(
                    system_prompt=enhanced_prompt,
                    user_message=user_message
                )
            else:
                # 법령 근거 없이 기본 응답
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
