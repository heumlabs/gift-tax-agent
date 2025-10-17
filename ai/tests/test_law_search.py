"""Tests for law search functionality."""

from __future__ import annotations

import pytest

from ai.tools.law_search.models import LawCitation, LawSearchResult


class TestLawSearchModels:
    """법령 검색 모델 테스트"""

    def test_law_citation_structure(self):
        """LawCitation 구조 검증"""
        citation: LawCitation = {
            "law": "상속세및증여세법",
            "article": "제53조 1항",
            "full_reference": "상속세및증여세법 제53조 1항",
            "content": "증여재산공제는 다음과 같다...",
            "url": "https://law.go.kr/...",
            "score": 0.92,
        }

        assert citation["law"] == "상속세및증여세법"
        assert citation["article"] == "제53조 1항"
        assert citation["score"] == 0.92

    def test_law_search_result_structure(self):
        """LawSearchResult 구조 검증"""
        result: LawSearchResult = {
            "citations": [
                {
                    "law": "국세기본법",
                    "article": "제1조",
                    "full_reference": "국세기본법 제1조",
                    "content": "이 법은...",
                    "url": None,
                    "score": 0.85,
                }
            ]
        }

        assert len(result["citations"]) == 1
        assert result["citations"][0]["law"] == "국세기본법"


class TestLawSearchIntegration:
    """법령 검색 통합 테스트 (Mock)"""

    @pytest.mark.asyncio
    async def test_search_law_mock(self, mocker):
        """search_law 함수 Mock 테스트"""
        # Mock DB 및 Gemini client
        from ai.tools.law_search import searcher

        # Mock 임베딩 생성
        mock_embedding = [0.1] * 768
        mocker.patch.object(
            searcher.GeminiClient,
            "generate_embedding",
            return_value=mock_embedding,
        )

        # Mock DB 쿼리 결과
        mock_rows = [
            (
                "상속세및증여세법",
                "상속세및증여세법 제53조 1항",
                "증여재산공제는 다음과 같다.",
                "https://law.go.kr/...",
                0.92,
            ),
            (
                "상속세및증여세법시행령",
                "상속세및증여세법시행령 제31조",
                "공제액의 계산방법은 다음과 같다.",
                None,
                0.88,
            ),
        ]

        class MockResult:
            def fetchall(self):
                return mock_rows

        class MockDB:
            def execute(self, *args, **kwargs):
                return MockResult()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        mocker.patch("ai.tools.law_search.searcher.get_db_session", return_value=MockDB())

        # 검색 실행
        result = await searcher.search_law("증여재산 공제", top_k=2)

        # 검증
        assert len(result["citations"]) == 2
        assert result["citations"][0]["law"] == "상속세및증여세법"
        assert result["citations"][0]["score"] == 0.92
        assert result["citations"][1]["law"] == "상속세및증여세법시행령"

    def test_search_law_tool_wrapper(self, mocker):
        """search_law_tool wrapper 테스트"""
        from ai.tools.law_search import wrapper

        # Mock search_law 함수
        mock_result: LawSearchResult = {
            "citations": [
                {
                    "law": "테스트법",
                    "article": "제1조",
                    "full_reference": "테스트법 제1조",
                    "content": "테스트입니다.",
                    "url": None,
                    "score": 0.95,
                }
            ]
        }

        async def mock_search_law(*args, **kwargs):
            return mock_result

        mocker.patch("ai.tools.law_search.wrapper.search_law", mock_search_law)

        # Tool 호출
        result = wrapper.search_law_tool("테스트 쿼리", top_k=1)

        # 검증
        assert result == mock_result
        assert len(result["citations"]) == 1

    def test_search_law_tool_metadata(self):
        """Tool 메타데이터 검증"""
        from ai.tools.law_search import search_law_tool

        assert hasattr(search_law_tool, "__tool_name__")
        assert hasattr(search_law_tool, "__tool_description__")
        assert search_law_tool.__tool_name__ == "search_law"
        assert "법령" in search_law_tool.__tool_description__
