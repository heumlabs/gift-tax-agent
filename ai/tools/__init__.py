"""
LangGraph Tools

Agent에서 호출 가능한 Tool 모음입니다.
Phase 1에서 구현된 증여세 계산 Tool 등이 여기에 위치합니다.
"""

from .gift_tax.calculator import calculate_gift_tax_simple as _calculate_gift_tax_simple
from .gift_tax.models import GiftTaxSimpleInput, GiftTaxSimpleOutput
from .langchain_wrapper import calculate_gift_tax_simple

# Law search는 DB 연결이 필요하므로 lazy import
# 사용 시에만 import하도록 함
def __getattr__(name):
    """Lazy import for law_search modules"""
    if name in ("LawCitation", "LawSearchResult", "search_law", "search_law_tool"):
        from .law_search import LawCitation, LawSearchResult, search_law, search_law_tool
        globals().update({
            "LawCitation": LawCitation,
            "LawSearchResult": LawSearchResult,
            "search_law": search_law,
            "search_law_tool": search_law_tool,
        })
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    # Gift tax calculator
    "calculate_gift_tax_simple",  # LangGraph 호환 wrapper
    "_calculate_gift_tax_simple",  # 원본 함수 (직접 호출용)
    "GiftTaxSimpleInput",
    "GiftTaxSimpleOutput",
    # Law search (lazy loaded)
    "search_law",  # 원본 함수 (직접 호출용)
    "search_law_tool",  # LangGraph 호환 wrapper
    "LawCitation",
    "LawSearchResult",
]
