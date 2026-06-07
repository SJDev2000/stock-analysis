"""Shared formatting utilities for report templates."""
from typing import Optional


def fmt_money(value: Optional[float]) -> str:
    """Format a dollar amount: $XB (1dp) if >=1B, else $XM."""
    if value is None:
        return "N/R"
    b = 1_000_000_000
    m = 1_000_000
    if abs(value) >= b:
        return f"${value/b:.1f}B"
    if abs(value) >= m:
        return f"${value/m:.1f}M"
    return f"${value:,.0f}"


def fmt_pct(value: Optional[float], decimals: int = 1) -> str:
    if value is None:
        return "N/R"
    return f"{value:.{decimals}f}%"


def fmt_pct_change(value: Optional[float]) -> str:
    if value is None:
        return "N/R"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.1f}%"


def fmt_ratio(value: Optional[float]) -> str:
    if value is None:
        return "N/R"
    return f"{value:.2f}x"


def fmt_num(value: Optional[float], decimals: int = 2) -> str:
    if value is None:
        return "N/R"
    return f"{value:.{decimals}f}"


def bps(a: Optional[float], b: Optional[float]) -> str:
    if a is None or b is None:
        return "N/R"
    diff = (b - a) * 100
    sign = "+" if diff >= 0 else ""
    return f"{sign}{diff:.0f} bps"


def trend_label(a: Optional[float], b: Optional[float]) -> str:
    if a is None or b is None:
        return "flat"
    if b > a + 0.5:
        return "expanding"
    if b < a - 0.5:
        return "contracting"
    return "stable"
