"""증여세 계산 도구."""

from .calculator import calculate_gift_tax_simple
from .models import GiftTaxSimpleInput, GiftTaxSimpleOutput

__all__ = [
    "calculate_gift_tax_simple",
    "GiftTaxSimpleInput",
    "GiftTaxSimpleOutput",
]
