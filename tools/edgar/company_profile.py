import json
from typing import Annotated, Any, Dict, Optional

from edgar import Company, set_identity

from claude_agent_sdk import tool

set_identity("Stock Analysis Tool contact@example.com")


def _safe_attr(obj, attr, default=None):
    return getattr(obj, attr, default) if hasattr(obj, attr) else default


def _extract_business_overview(tenk) -> Optional[str]:
    try:
        text = tenk.business
        if text:
            return str(text).strip()
    except Exception:
        pass
    return None


def _extract_risk_factors(tenk) -> Optional[str]:
    try:
        text = tenk.risk_factors
        if text:
            return str(text).strip()
    except Exception:
        pass
    return None


def _get_shares_data(company: Company) -> Dict[str, Any]:
    shares = {}

    shares_outstanding = _safe_attr(company, "shares_outstanding")
    if shares_outstanding:
        shares["shares_outstanding"] = shares_outstanding

    public_float = _safe_attr(company, "public_float")
    if public_float:
        shares["public_float"] = public_float

    if shares_outstanding and public_float and shares_outstanding > 0:
        shares["implied_price_per_share"] = round(public_float / shares_outstanding, 2)

    return shares


@tool(
    "analyze_company_profile",
    "Fetch comprehensive company profile from SEC EDGAR. "
    "Returns company identity (CIK, SIC, industry, exchange), "
    "shares outstanding, public float, business overview from 10-K, "
    "and risk factors.",
    {
        "ticker": Annotated[str, "Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'GOOGL')"],
    },
)
async def analyze_company_profile(args: Dict[str, Any]) -> Dict[str, Any]:
    ticker = args["ticker"]

    try:
        company = Company(ticker)
        if company.not_found:
            return {
                "content": [{"type": "text", "text": json.dumps({"success": False, "ticker": ticker.upper(), "error": "Company not found"})}],
                "is_error": True,
            }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": json.dumps({"success": False, "ticker": ticker.upper(), "error": str(e)})}],
            "is_error": True,
        }

    profile: Dict[str, Any] = {
        "company_name": company.name,
        "ticker": ticker.upper(),
        "cik": company.cik,
        "sic": company.sic,
        "industry": _safe_attr(company, "industry"),
        "exchanges": company.get_exchanges() if hasattr(company, "get_exchanges") else [],
        "fiscal_year_end": _safe_attr(company, "fiscal_year_end"),
        "filer_category": _safe_attr(company, "filer_category"),
        "is_large_accelerated_filer": _safe_attr(company, "is_large_accelerated_filer", False),
        "is_smaller_reporting_company": _safe_attr(company, "is_smaller_reporting_company", False),
        "is_emerging_growth_company": _safe_attr(company, "is_emerging_growth_company", False),
    }

    shares_data = _get_shares_data(company)
    profile["shares"] = shares_data

    business_overview = None
    risk_factors = None
    filing_date = None

    try:
        tenk = company.latest_tenk
        if tenk:
            filing_date = str(tenk.filing_date) if hasattr(tenk, "filing_date") else None
            business_overview = _extract_business_overview(tenk)
            risk_factors = _extract_risk_factors(tenk)
    except Exception:
        pass

    profile["latest_10k_filing_date"] = filing_date
    profile["business_overview"] = business_overview
    profile["risk_factors"] = risk_factors

    result = {"success": True, "ticker": ticker.upper(), "profile": profile}
    from tools.edgar._serialize import tool_response
    return tool_response(result)
