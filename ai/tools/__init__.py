"""
LangGraph Tools

Agent에서 호출 가능한 Tool 모음입니다.
Phase 1에서 구현된 증여세 계산 Tool 등이 여기에 위치합니다.
"""

from .gift_tax.calculator import calculate_gift_tax_simple as _calculate_gift_tax_simple
from .gift_tax.models import GiftTaxSimpleInput, GiftTaxSimpleOutput
from .langchain_wrapper import calculate_gift_tax_simple
from .law_search import LawCitation, LawSearchResult, search_law, search_law_tool

__all__ = [
    # Gift tax calculator
    "calculate_gift_tax_simple",  # LangGraph 호환 wrapper
    "_calculate_gift_tax_simple",  # 원본 함수 (직접 호출용)
    "GiftTaxSimpleInput",
    "GiftTaxSimpleOutput",
    # Law search
    "search_law",  # 원본 함수 (직접 호출용)
    "search_law_tool",  # LangGraph 호환 wrapper
    "LawCitation",
    "LawSearchResult",
]
