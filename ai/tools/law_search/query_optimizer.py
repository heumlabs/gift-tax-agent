"""
LLM을 활용한 법령 검색 쿼리 최적화

사용자의 자연어 질의를 법령 검색에 최적화된 키워드로 변환합니다.
"""

from __future__ import annotations

import sys
from pathlib import Path

# AI 임포트
_PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from ai.clients.gemini import GeminiClient
from ai.config import GeminiSettings


QUERY_OPTIMIZATION_PROMPT = """당신은 한국 세법 전문가입니다.
사용자의 질문을 법령 원문에 나올 법한 표현으로 변환하세요.

# 핵심 원칙
법령 원문에는 구체적인 금액, 관계, 조건이 명시되어 있습니다.
검색어도 이런 법령 원문 스타일로 작성해야 잘 찾습니다.

# 변환 규칙
1. 법률 용어 사용 (부모님 → 직계존속, 돈 → 재산)
2. **구체적 금액 포함** (5천만원, 6억원 등)
3. **법령 원문 표현 방식** 사용
4. 띄어쓰기 정확히 (증여재산공제 → 증여재산 공제)
5. 간결하게 (5-8개 단어)

# 좋은 예시 (법령 원문 스타일)
입력: "부모님이 돈 주시면 얼마까지 공제되나요?"
출력: 직계존속 5천만원 공제

입력: "배우자한테 증여하면?"
출력: 배우자 6억원 공제

입력: "미성년자가 부모에게 받으면?"
출력: 미성년자 직계존속 2천만원 공제

입력: "증여재산공제가 뭐예요?"
출력: 거주자가 증여를 받은 경우 공제

입력: "10년 이내 증여 합산되나요?"
출력: 증여받기 전 10년 이내 공제

입력: "친척한테 증여받으면?"
출력: 4촌 이내 혈족 1천만원 공제

# 나쁜 예시 (키워드 나열)
❌ "직계존속 증여 공제" (너무 추상적)
❌ "증여재산공제" (띄어쓰기 없음)
❌ "증여 공제 한도" (법령에 없는 표현)

# 사용자 질문
{query}

# 법령 원문 스타일 검색어
"""


async def optimize_search_query(
    user_query: str,
    client: GeminiClient | None = None,
) -> str:
    """
    LLM을 사용하여 사용자 질의를 법령 검색 최적화

    Args:
        user_query: 사용자의 자연어 질의
        client: GeminiClient 인스턴스 (없으면 새로 생성)

    Returns:
        최적화된 검색 쿼리 문자열

    Example:
        >>> query = await optimize_search_query("부모님이 돈 주시면 얼마까지 세금 안내나요?")
        >>> print(query)
        "직계존속 증여 공제한도 증여재산공제"
    """
    if client is None:
        settings = GeminiSettings.from_env()
        client = GeminiClient(settings)

    prompt = QUERY_OPTIMIZATION_PROMPT.format(query=user_query)

    # LLM 호출 (generate_content 사용)
    response = await client.generate_content(
        system_prompt="당신은 한국 세법 전문가입니다. 사용자의 질문을 법령 데이터베이스 검색에 최적화된 키워드로 변환하세요.",
        user_message=prompt,
    )

    # 결과 정제
    optimized = response.strip()

    # 불필요한 따옴표, 마침표 제거
    optimized = optimized.strip('"\'.,\n')

    return optimized


async def optimize_and_log(user_query: str) -> str:
    """
    쿼리 최적화 + 로깅 (디버깅용)

    Args:
        user_query: 사용자 질의

    Returns:
        최적화된 쿼리
    """
    optimized = await optimize_search_query(user_query)
    print(f"[Query Optimization]")
    print(f"  Input:  {user_query}")
    print(f"  Output: {optimized}")
    return optimized
