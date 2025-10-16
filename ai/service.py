from __future__ import annotations

import asyncio
from typing import Dict, Optional

from ai.exceptions import ChatPipelineError
from ai.pipelines import run_workflow

# 기존 ChatPipeline 제거하고 LangGraph Workflow 사용


def generate_assistant_message(
    content: str,
    session_id: str = "default",
    previous_collected_parameters: Optional[Dict] = None,
    metadata: Optional[Dict[str, object]] = None
) -> Dict[str, object]:
    """
    사용자 메시지를 받아 LangGraph Workflow를 실행하고 AI 응답 반환

    Phase 3에서 멀티턴 대화 지원을 위해 session_id와 previous_collected_parameters 추가

    Args:
        content: 사용자 메시지 내용
        session_id: 세션 ID (멀티턴 대화 추적)
        previous_collected_parameters: 이전까지 수집된 파라미터
        metadata: 추가 메타데이터 (현재 미사용)

    Returns:
        dict: {"content": str, "metadata": dict}
    """
    try:
        # LangGraph Workflow 실행 (이전 파라미터 전달)
        result = asyncio.run(run_workflow(
            user_message=content,
            session_id=session_id,
            previous_collected_parameters=previous_collected_parameters
        ))

        # Backend API 형식으로 변환
        return {
            "content": result.get("response", ""),
            "metadata": {
                "intent": result.get("intent", ""),
                "session_id": result.get("session_id", ""),
                "collected_parameters": result.get("collected_parameters", {}),
                "missing_parameters": result.get("missing_parameters", []),
                "calculation": result.get("metadata", {}).get("calculation"),
            },
        }
    except Exception as exc:
        raise ChatPipelineError(str(exc)) from exc
