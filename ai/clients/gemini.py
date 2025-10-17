from __future__ import annotations

import logging
from typing import Any, Dict, List

import httpx

from ai.config import GeminiSettings
from ai.exceptions import GeminiClientError

LOGGER = logging.getLogger(__name__)


class GeminiClient:
    """Asynchronous REST client for the Gemini `generateContent` and embedding APIs."""

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

    async def generate_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for a single text using Gemini embedding model.

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector (normalized if dimension < 3072)

        Raises:
            GeminiClientError: If the API call fails or response is invalid
        """
        payload = {
            "content": {"parts": [{"text": text.strip()}]},
            "output_dimensionality": self._settings.embedding_dimension,
        }

        response = await self._post_embedding(payload, batch=False)
        embedding = self._extract_embedding(response)

        # 768, 1536 차원은 정규화 필요 (3072는 자동 정규화됨)
        if self._settings.embedding_dimension < 3072:
            import numpy as np
            embedding_np = np.array(embedding)
            normalized = embedding_np / np.linalg.norm(embedding_np)
            return normalized.tolist()

        return embedding

    async def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts in a single batch request.

        Args:
            texts: List of input texts to embed (max 100 per batch)

        Returns:
            List of embedding vectors, one per input text (normalized if dimension < 3072)

        Raises:
            GeminiClientError: If the API call fails or response is invalid
            ValueError: If texts list exceeds maximum batch size
        """
        if len(texts) > self._settings.embedding_batch_size:
            raise ValueError(
                f"Batch size {len(texts)} exceeds maximum {self._settings.embedding_batch_size}"
            )

        payload = {
            "requests": [
                {
                    "model": f"models/{self._settings.embedding_model}",
                    "content": {"parts": [{"text": text.strip()}]},
                    "output_dimensionality": self._settings.embedding_dimension,
                }
                for text in texts
            ]
        }

        response = await self._post_embedding(payload, batch=True)
        embeddings = self._extract_embeddings_batch(response)

        # 768, 1536 차원은 정규화 필요 (3072는 자동 정규화됨)
        if self._settings.embedding_dimension < 3072:
            import numpy as np
            normalized_embeddings = []
            for embedding in embeddings:
                embedding_np = np.array(embedding)
                normalized = embedding_np / np.linalg.norm(embedding_np)
                normalized_embeddings.append(normalized.tolist())
            return normalized_embeddings

        return embeddings

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

    async def _post_embedding(self, payload: Dict[str, Any], batch: bool = False) -> Dict[str, Any]:
        """Post request to embedding API endpoint."""
        params = {"key": self._settings.api_key}
        endpoint = self._settings.embedding_batch_endpoint if batch else self._settings.embedding_endpoint

        try:
            async with httpx.AsyncClient(timeout=self._settings.request_timeout) as client:
                resp = await client.post(endpoint, params=params, json=payload)
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
            LOGGER.exception("Gemini Embedding HTTPStatusError (status=%s): %s", status_code, message)
            raise GeminiClientError(status_code=status_code, message=message, payload=body) from exc
        except httpx.RequestError as exc:
            LOGGER.exception("Gemini Embedding RequestError")
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
    def _extract_embedding(response_json: Dict[str, Any]) -> list[float]:
        """Extract embedding vector from single embedding response."""
        embedding = response_json.get("embedding")
        if not embedding or not isinstance(embedding, dict):
            raise GeminiClientError(
                status_code=500,
                message="Gemini embedding response missing 'embedding' field.",
                payload=response_json,
            )

        values = embedding.get("values")
        if not values or not isinstance(values, list):
            raise GeminiClientError(
                status_code=500,
                message="Gemini embedding missing 'values' field.",
                payload=response_json,
            )

        return values

    @staticmethod
    def _extract_embeddings_batch(response_json: Dict[str, Any]) -> list[list[float]]:
        """Extract embedding vectors from batch embedding response."""
        embeddings = response_json.get("embeddings")
        if not embeddings or not isinstance(embeddings, list):
            raise GeminiClientError(
                status_code=500,
                message="Gemini batch embedding response missing 'embeddings' field.",
                payload=response_json,
            )

        result = []
        for emb in embeddings:
            if not isinstance(emb, dict):
                raise GeminiClientError(
                    status_code=500,
                    message="Invalid embedding object in batch response.",
                    payload=response_json,
                )

            values = emb.get("values")
            if not values or not isinstance(values, list):
                raise GeminiClientError(
                    status_code=500,
                    message="Embedding missing 'values' field in batch response.",
                    payload=response_json,
                )

            result.append(values)

        return result

    @staticmethod
    def _build_error_message(status_code: int, payload: Dict[str, Any]) -> str:
        error_obj = payload.get("error")
        if isinstance(error_obj, dict):
            status = error_obj.get("status") or status_code
            message = error_obj.get("message")
            if message:
                return f"{status}: {message}"
        return f"Gemini API error {status_code}"
