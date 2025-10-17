"""Data models for law search results."""

from typing import TypedDict


class LawCitation(TypedDict):
    """단일 법령 인용 정보"""

    law: str  # 법령명 (예: "상속세및증여세법")
    article: str  # 조문 (예: "제53조 1항")
    full_reference: str  # 전체 참조 (예: "상속세및증여세법 제53조 1항")
    content: str  # 원문 텍스트
    url: str | None  # 법제처 링크
    score: float  # 유사도 점수 (0~1)


class LawSearchResult(TypedDict):
    """법령 검색 결과"""

    citations: list[LawCitation]  # 검색된 법령 인용 목록
