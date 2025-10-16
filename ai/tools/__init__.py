"""AI Tools module."""

from .gift_tax.calculator import calculate_gift_tax_simple as _calculate_gift_tax_simple
from .gift_tax.models import GiftTaxSimpleInput, GiftTaxSimpleOutput
from .langchain_wrapper import calculate_gift_tax_simple

__all__ = [
    "calculate_gift_tax_simple",  # LangGraph 호환 wrapper
    "_calculate_gift_tax_simple",  # 원본 함수 (직접 호출용)
    "GiftTaxSimpleInput",
    "GiftTaxSimpleOutput",
]
