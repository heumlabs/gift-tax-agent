from __future__ import annotations

import asyncio
from typing import Dict, Optional

from ai.exceptions import ChatPipelineError
from ai.pipelines import run_workflow

# 기존 ChatPipeline 제거하고 LangGraph Workflow 사용


def generate_assistant_message(content: str, metadata: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    """
    사용자 메시지를 받아 LangGraph Workflow를 실행하고 AI 응답 반환

    Args:
        content: 사용자 메시지 내용
        metadata: 추가 메타데이터 (현재 미사용)

    Returns:
        dict: {"content": str, "metadata": dict}
    """
    try:
        # LangGraph Workflow 실행
        result = asyncio.run(run_workflow(user_message=content))

        # Backend API 형식으로 변환
        return {
            "content": result.get("response", ""),
            "metadata": {
                "intent": result.get("intent", ""),
                "session_id": result.get("session_id", ""),
            },
        }
    except Exception as exc:
        raise ChatPipelineError(str(exc)) from exc
