"""
Analysis Tools — Pure computation, zero I/O.

These tools take pre-fetched data as input and compute derived metrics.
They never touch the network or filesystem.
"""

from tools.analysis.financial_ratios import analyze_financial_ratios

__all__ = ["analyze_financial_ratios"]
