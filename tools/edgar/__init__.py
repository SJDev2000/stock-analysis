"""
EDGAR Tools — Data fetching from SEC EDGAR XBRL filings.

These tools perform network I/O to retrieve real financial data.
Each tool returns structured JSON that downstream analysis tools consume.
"""

from tools.edgar.income_statement import analyze_income_statement
from tools.edgar.balance_sheet import analyze_balance_sheet
from tools.edgar.cash_flow import analyze_cash_flow
from tools.edgar.company_profile import analyze_company_profile

__all__ = [
    "analyze_income_statement",
    "analyze_balance_sheet",
    "analyze_cash_flow",
    "analyze_company_profile",
]
