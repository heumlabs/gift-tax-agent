from __future__ import annotations

import asyncio
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import uuid4

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
    metadata: Dict[str, object] = dict(asdict(response))
    metadata.pop("content", None)
    return {
        "id": str(uuid4()),
        "role": "assistant",
        "content": response.content,
        "metadata": metadata,
        "createdAt": datetime.now(timezone.utc).isoformat(),
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
