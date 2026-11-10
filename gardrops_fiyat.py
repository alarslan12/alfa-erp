"""Gardrops siparişlerinde sabit %10 kesinti sonrası net ciro hesabı."""
from decimal import Decimal, ROUND_CEILING

def net_revenue(amount, platform):
    value=Decimal(str(amount).replace(",","."))
    if not value.is_finite() or value < 0:
        raise ValueError("Geçersiz sipariş tutarı.")
    if str(platform).casefold().strip() == "gardrops":
        return int((value * Decimal("0.90")).to_integral_value(rounding=ROUND_CEILING))
    return float(value)
