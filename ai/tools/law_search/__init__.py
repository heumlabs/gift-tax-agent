"""Law search tool for RAG system."""

from .models import LawCitation, LawSearchResult
from .searcher import search_law
from .wrapper import search_law_tool

__all__ = [
    "LawCitation",
    "LawSearchResult",
    "search_law",
    "search_law_tool",
]
