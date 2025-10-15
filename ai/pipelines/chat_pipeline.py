from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from ai.clients import GeminiClient
from ai.config import GeminiSettings
from ai.exceptions import ChatPipelineError, GeminiClientError
from ai.prompts import DEFAULT_SYSTEM_PROMPT
from ai.schemas import ChatRequest, ChatResponse

LOGGER = logging.getLogger(__name__)


@dataclass
class ChatPipeline:
    """Single-turn chat pipeline that delegates response generation to Gemini."""

    gemini_client: GeminiClient
    system_prompt: str = DEFAULT_SYSTEM_PROMPT

    @classmethod
    def from_env(cls, *, system_prompt: Optional[str] = None) -> "ChatPipeline":
        settings = GeminiSettings.from_env()
        client = GeminiClient(settings)
        return cls(gemini_client=client, system_prompt=system_prompt or DEFAULT_SYSTEM_PROMPT)

    async def run(self, request: ChatRequest) -> ChatResponse:
        LOGGER.debug("Executing chat pipeline with content_length=%d", len(request.content))
        try:
            content = await self.gemini_client.generate_content(
                system_prompt=self.system_prompt,
                user_message=request.content,
            )
        except GeminiClientError as exc:
            LOGGER.exception("GeminiClientError: status=%s message=%s", exc.status_code, exc, exc_info=exc)
            raise
        except Exception as exc:  # noqa: B902
            LOGGER.exception("Unexpected error from Gemini pipeline: %s", exc)
            raise ChatPipelineError(str(exc)) from exc

        return ChatResponse(content=content)
