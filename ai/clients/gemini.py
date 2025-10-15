from __future__ import annotations

import logging
from typing import Any, Dict, List

import httpx

from ai.config import GeminiSettings
from ai.exceptions import GeminiClientError

LOGGER = logging.getLogger(__name__)


class GeminiClient:
    """Asynchronous REST client for the Gemini `generateContent` API."""

    def __init__(self, settings: GeminiSettings):
        self._settings = settings

    async def generate_content(self, *, system_prompt: str, user_message: str) -> str:
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt.strip()}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_message.strip()}],
                }
            ],
        }

        response = await self._post(payload)
        return self._extract_text(response)

    async def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        params = {"key": self._settings.api_key}
        try:
            async with httpx.AsyncClient(timeout=self._settings.request_timeout) as client:
                resp = await client.post(self._settings.endpoint, params=params, json=payload)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            response = exc.response
            try:
                body = response.json() if response else {}
            except Exception:
                body = {}
            status_code = response.status_code if response else 500
            message = self._build_error_message(status_code, body)
            LOGGER.exception("Gemini HTTPStatusError (status=%s): %s", status_code, message)
            raise GeminiClientError(status_code=status_code, message=message, payload=body) from exc
        except httpx.RequestError as exc:
            LOGGER.exception("Gemini RequestError")
            raise GeminiClientError(status_code=599, message=str(exc)) from exc

    @staticmethod
    def _extract_text(response_json: Dict[str, Any]) -> str:
        candidates: List[Dict[str, Any]] = response_json.get("candidates") or []
        if not candidates:
            raise GeminiClientError(status_code=500, message="Gemini response did not contain candidates.", payload=response_json)

        parts = (candidates[0].get("content") or {}).get("parts") or []
        for part in parts:
            if isinstance(part, dict):
                text = part.get("text")
                if text:
                    return text

        raise GeminiClientError(status_code=500, message="Gemini candidate missing text field.", payload=response_json)

    @staticmethod
    def _build_error_message(status_code: int, payload: Dict[str, Any]) -> str:
        error_obj = payload.get("error")
        if isinstance(error_obj, dict):
            status = error_obj.get("status") or status_code
            message = error_obj.get("message")
            if message:
                return f"{status}: {message}"
        return f"Gemini API error {status_code}"
