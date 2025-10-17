"""LangGraph-compatible tool wrapper for law search."""

from __future__ import annotations

import asyncio
from typing import Annotated

from pydantic import Field

from .searcher import search_law


def search_law_tool(
    query: Annotated[str, Field(description="검색 쿼리 (예: 직계존속 증여재산 공제)")],
    top_k: Annotated[int, Field(description="반환 개수 (1~10)", ge=1, le=10)] = 5,
) -> dict:
    """
    법령 검색 Tool (LangGraph 호환).

    상속세및증여세법, 국세기본법 등 법령·예규를 검색하여
    근거 조문과 내용을 반환합니다.

    Args:
        query: 검색 쿼리 (자연어 또는 키워드)
        top_k: 반환할 검색 결과 개수 (기본 5개)

    Returns:
        LawSearchResult: citations 리스트를 포함한 딕셔너리

    Example:
        >>> result = search_law_tool("직계존속 증여재산 공제", top_k=3)
        >>> result["citations"][0]["full_reference"]
        "상속세및증여세법 제53조 1항"

    LangGraph 사용 예시:
        ```python
        from langgraph.prebuilt import create_react_agent
        from langchain_google_genai import ChatGoogleGenerativeAI

        # LangGraph가 자동으로 함수를 Tool로 변환
        tools = [search_law_tool]

        agent = create_react_agent(
            model=ChatGoogleGenerativeAI(model="gemini-2.5-flash"),
            tools=tools,
        )

        # Agent가 필요 시 Tool 자동 호출
        result = agent.invoke({
            "messages": [("user", "증여세 공제 한도는 얼마인가요?")]
        })
        ```
    """
    result = asyncio.run(search_law(query, top_k))
    return result


# Tool metadata (LangGraph가 참조)
search_law_tool.__tool_name__ = "search_law"  # type: ignore
search_law_tool.__tool_description__ = (  # type: ignore
    "상속세및증여세법, 국세기본법 등 법령·예규를 검색하여 "
    "근거 조문과 내용을 반환합니다. "
    "증여세·상속세 계산 시 법적 근거가 필요할 때 사용하세요."
)
