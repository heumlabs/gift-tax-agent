"""Google Search Grounding 응답 모델"""

from __future__ import annotations

from typing import Any


class GroundingChunk:
    """웹 소스 정보"""

    def __init__(self, uri: str, title: str):
        self.uri = uri
        self.title = title

    def __repr__(self) -> str:
        return f"GroundingChunk(uri={self.uri}, title={self.title})"


class GroundingSegment:
    """텍스트 세그먼트 (인용 위치)"""

    def __init__(self, start_index: int, end_index: int, text: str):
        self.start_index = start_index
        self.end_index = end_index
        self.text = text

    def __repr__(self) -> str:
        return f"GroundingSegment({self.start_index}-{self.end_index})"


class GroundingSupport:
    """인용 정보 (텍스트 세그먼트 + 소스 인덱스)"""

    def __init__(self, segment: GroundingSegment, grounding_chunk_indices: list[int]):
        self.segment = segment
        self.grounding_chunk_indices = grounding_chunk_indices

    def __repr__(self) -> str:
        return f"GroundingSupport(segment={self.segment}, indices={self.grounding_chunk_indices})"


class GroundingMetadata:
    """Google Search Grounding 메타데이터"""

    def __init__(
        self,
        web_search_queries: list[str] | None = None,
        grounding_chunks: list[GroundingChunk] | None = None,
        grounding_supports: list[GroundingSupport] | None = None,
        search_entry_point: dict[str, Any] | None = None,
    ):
        self.web_search_queries = web_search_queries or []
        self.grounding_chunks = grounding_chunks or []
        self.grounding_supports = grounding_supports or []
        self.search_entry_point = search_entry_point or {}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GroundingMetadata:
        """API 응답에서 GroundingMetadata 객체 생성"""
        # webSearchQueries
        web_queries = data.get("webSearchQueries", [])

        # groundingChunks
        chunks_data = data.get("groundingChunks", [])
        chunks = [
            GroundingChunk(uri=c.get("web", {}).get("uri", ""), title=c.get("web", {}).get("title", ""))
            for c in chunks_data
        ]

        # groundingSupports
        supports_data = data.get("groundingSupports", [])
        supports = []
        for s in supports_data:
            seg_data = s.get("segment", {})
            segment = GroundingSegment(
                start_index=seg_data.get("startIndex", 0),
                end_index=seg_data.get("endIndex", 0),
                text=seg_data.get("text", ""),
            )
            indices = s.get("groundingChunkIndices", [])
            supports.append(GroundingSupport(segment=segment, grounding_chunk_indices=indices))

        # searchEntryPoint
        entry_point = data.get("searchEntryPoint", {})

        return cls(
            web_search_queries=web_queries,
            grounding_chunks=chunks,
            grounding_supports=supports,
            search_entry_point=entry_point,
        )

    def __repr__(self) -> str:
        return f"GroundingMetadata(queries={len(self.web_search_queries)}, chunks={len(self.grounding_chunks)}, supports={len(self.grounding_supports)})"


class GroundingResponse:
    """Google Search Grounding 응답 (텍스트 + 메타데이터)"""

    def __init__(self, text: str, grounding_metadata: GroundingMetadata | None = None):
        self.text = text
        self.grounding_metadata = grounding_metadata

    def __repr__(self) -> str:
        return f"GroundingResponse(text_length={len(self.text)}, metadata={self.grounding_metadata})"
