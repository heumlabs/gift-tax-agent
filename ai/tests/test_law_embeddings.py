"""Tests for Gemini embedding API."""

from __future__ import annotations

import pytest

from ai.clients.gemini import GeminiClient
from ai.config import GeminiSettings
from ai.exceptions import GeminiClientError


class TestGeminiEmbeddings:
    """Gemini embedding API 테스트"""

    @pytest.fixture
    def settings(self):
        """Mock settings"""
        return GeminiSettings(
            api_key="test-api-key",
            embedding_model="text-embedding-004",
            embedding_dimension=768,
            embedding_batch_size=100,
        )

    @pytest.fixture
    def client(self, settings):
        """GeminiClient 인스턴스"""
        return GeminiClient(settings)

    def test_embedding_endpoint(self, settings):
        """임베딩 엔드포인트 URL 검증"""
        expected = "https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent"
        assert settings.embedding_endpoint == expected

    def test_embedding_batch_endpoint(self, settings):
        """배치 임베딩 엔드포인트 URL 검증"""
        expected = "https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:batchEmbedContents"
        assert settings.embedding_batch_endpoint == expected

    @pytest.mark.asyncio
    async def test_generate_embedding_mock(self, client, mocker):
        """단일 임베딩 생성 테스트 (Mock)"""
        # Mock response
        mock_response = {"embedding": {"values": [0.1] * 768}}
        mocker.patch.object(client, "_post_embedding", return_value=mock_response)

        result = await client.generate_embedding("테스트 텍스트")

        assert isinstance(result, list)
        assert len(result) == 768
        assert all(isinstance(v, float) for v in result)

    @pytest.mark.asyncio
    async def test_generate_embeddings_batch_mock(self, client, mocker):
        """배치 임베딩 생성 테스트 (Mock)"""
        # Mock response
        mock_response = {
            "embeddings": [
                {"values": [0.1] * 768},
                {"values": [0.2] * 768},
                {"values": [0.3] * 768},
            ]
        }
        mocker.patch.object(client, "_post_embedding", return_value=mock_response)

        texts = ["텍스트1", "텍스트2", "텍스트3"]
        result = await client.generate_embeddings_batch(texts)

        assert isinstance(result, list)
        assert len(result) == 3
        assert all(len(emb) == 768 for emb in result)

    @pytest.mark.asyncio
    async def test_batch_size_limit(self, client):
        """배치 크기 제한 테스트"""
        texts = ["text"] * 101  # 최대 100개 초과

        with pytest.raises(ValueError, match="exceeds maximum"):
            await client.generate_embeddings_batch(texts)

    @pytest.mark.asyncio
    async def test_extract_embedding_missing_field(self, client):
        """임베딩 응답 필드 누락 테스트"""
        invalid_response = {"error": "missing embedding"}

        with pytest.raises(GeminiClientError, match="missing 'embedding' field"):
            client._extract_embedding(invalid_response)

    @pytest.mark.asyncio
    async def test_extract_embeddings_batch_invalid(self, client):
        """배치 임베딩 응답 오류 테스트"""
        invalid_response = {"embeddings": [{"no_values": []}]}

        with pytest.raises(GeminiClientError, match="missing 'values' field"):
            client._extract_embeddings_batch(invalid_response)
