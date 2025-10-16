from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import Dict, Optional

from ai.exceptions import ChatPipelineError, GeminiClientError
from ai.pipelines import ChatPipeline
from ai.schemas import ChatRequest, ChatResponse

_pipeline: Optional[ChatPipeline] = None


def _get_pipeline() -> ChatPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = ChatPipeline.from_env()
    return _pipeline


def _serialize_response(response: ChatResponse) -> Dict[str, object]:
    """
    ChatResponse를 backend가 사용할 수 있는 dict로 변환.

    Note: id, role, createdAt 등 인프라 필드는 backend에서 생성하므로
    LLM 모듈에서는 content와 metadata만 반환한다.
    """
    metadata: Dict[str, object] = dict(asdict(response))
    metadata.pop("content", None)
    return {
        "content": response.content,
        "metadata": metadata,
    }


def generate_assistant_message(content: str, metadata: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    request = ChatRequest(content=content, metadata=metadata)
    pipeline = _get_pipeline()
    try:
        response = asyncio.run(pipeline.run(request))
    except (GeminiClientError, ChatPipelineError):
        raise
    except Exception as exc:  # noqa: B902
        raise ChatPipelineError(str(exc)) from exc

    return _serialize_response(response)
