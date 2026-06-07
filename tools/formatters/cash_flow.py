"""Cash flow report formatter — produces the exact section template."""
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .utils import fmt_money, fmt_pct, fmt_num


def _dedup(flows: List[Dict]) -> List[Dict]:
    seen = {}
    for f in flows:
        key = f.get("period", "") + str(f.get("fiscal_year", ""))
        if key not in seen:
            seen[key] = f
    return sorted(seen.values(), key=lambda x: x.get("fiscal_year", 0))


def _table(headers: List[str], rows: List[tuple]) -> str:
    col0_w = max(len(r[0]) for r in rows)
    col_ws = [max(len(h), max(len(str(r[i+1])) for r in rows)) for i, h in enumerate(headers[1:])]
    widths = [col0_w] + col_ws
    header_cells = [headers[0].ljust(widths[0])] + [h.rjust(widths[i+1]) for i, h in enumerate(headers[1:])]
    lines = [
        "| " + " | ".join(header_cells) + " |",
        "|" + "|".join("-" * (w + 2) for w in widths) + "|",
    ]
    for r in rows:
        cells = [r[0].ljust(widths[0])] + [str(r[i+1]).rjust(widths[i+1]) for i in range(len(headers) - 1)]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def format_report(artifact: Dict[str, Any]) -> str:
    ticker = artifact.get("ticker", "")
    company = artifact.get("company_name", ticker)
    flows_raw: List[Dict] = artifact.get("cash_flows", [])

    flows = _dedup(flows_raw)[-5:]
    hdrs = [f.get("period", f"FY{f.get('fiscal_year','')}") for f in flows]

    def _v(f: Dict, key: str) -> Optional[float]:
        return f.get(key)

    # -----------------------------------------------------------------------
    # Section 1: Cash Flow Statement Table
    # -----------------------------------------------------------------------
    def _acq(f: Dict) -> str:
        v = f.get("acquisitions")
        return fmt_money(v) if v else "N/R"

    cf_rows = [
        ("**Operating Cash Flow**",  [fmt_money(_v(f,"operating_cash_flow")) for f in flows]),
        ("Depreciation & Amort.",    [fmt_money(_v(f,"depreciation_amortization")) for f in flows]),
        ("Stock-Based Compensation", [fmt_money(_v(f,"stock_based_compensation")) for f in flows]),
        ("**Investing Cash Flow**",  [fmt_money(_v(f,"investing_cash_flow")) for f in flows]),
        ("Capital Expenditures",     [fmt_money(_v(f,"capital_expenditures")) for f in flows]),
        ("Acquisitions",             [_acq(f) for f in flows]),
        ("**Financing Cash Flow**",  [fmt_money(_v(f,"financing_cash_flow")) for f in flows]),
        ("Dividends Paid",           [fmt_money(_v(f,"dividends_paid")) for f in flows]),
        ("Share Buybacks",           [fmt_money(_v(f,"share_buybacks")) for f in flows]),
        ("Debt Issued",              [fmt_money(_v(f,"debt_issued")) for f in flows]),
        ("Debt Repaid",              [fmt_money(_v(f,"debt_repaid")) for f in flows]),
    ]
    cf_table = _table(["Metric"] + hdrs, [(r[0],) + tuple(r[1]) for r in cf_rows])

    # -----------------------------------------------------------------------
    # Section 2: Free Cash Flow & Efficiency
    # -----------------------------------------------------------------------
    fcf_rows = [
        ("**Free Cash Flow**",     [fmt_money(_v(f,"free_cash_flow")) for f in flows]),
        ("**FCF Margin %**",       [fmt_pct(_v(f,"fcf_margin_pct")) for f in flows]),
        ("CapEx / Revenue %",      [fmt_pct(_v(f,"capex_to_revenue_pct")) for f in flows]),
        ("**Shareholder Return**", [fmt_money(_v(f,"shareholder_return")) for f in flows]),
    ]
    fcf_table = _table(["Metric"] + hdrs, [(r[0],) + tuple(r[1]) for r in fcf_rows])

    # -----------------------------------------------------------------------
    # Section 3: Cash Generation Quality
    # -----------------------------------------------------------------------
    latest = flows[-1] if flows else {}
    earliest = flows[0] if flows else {}
    fy0 = hdrs[0] if hdrs else "N/R"
    fyn = hdrs[-1] if hdrs else "N/R"

    ocf = _v(latest, "operating_cash_flow")
    fcf = _v(latest, "free_cash_flow")
    capex = _v(latest, "capital_expenditures")
    capex_pct = _v(latest, "capex_to_revenue_pct")
    fcf_margin = _v(latest, "fcf_margin_pct")

    fcf_first = _v(earliest, "free_cash_flow")
    fcf_dir = "grew" if (fcf or 0) > (fcf_first or 0) else "declined"

    conv_rate = (fcf / ocf * 100) if ocf and fcf else None
    cq_1 = f"OCF of {fmt_money(ocf)} converted to FCF of {fmt_money(fcf)} in {fyn} ({fmt_pct(conv_rate)} conversion rate after CapEx of {fmt_money(capex)})."
    cq_2 = f"FCF {fcf_dir} from {fmt_money(fcf_first)} in {fy0} to {fmt_money(fcf)} in {fyn}; FCF margin of {fmt_pct(fcf_margin)} in {fyn}."
    cq_3 = f"CapEx intensity of {fmt_pct(capex_pct)} of revenue in {fyn} — {'light' if (capex_pct or 0) < 5 else 'moderate' if (capex_pct or 0) < 10 else 'heavy'} capital requirements."

    # -----------------------------------------------------------------------
    # Section 4: Capital Allocation (Latest Year)
    # -----------------------------------------------------------------------
    divs = _v(latest, "dividends_paid")
    buybacks = _v(latest, "share_buybacks")
    debt_repaid = _v(latest, "debt_repaid")
    total_returned = _v(latest, "shareholder_return")

    def _pct_of_fcf(v: Optional[float]) -> str:
        if v is None or not fcf or fcf == 0:
            return "N/R"
        return fmt_pct(v / fcf * 100)

    alloc_table = _table(
        ["Allocation", fyn, "% of FCF"],
        [
            ("Share Buybacks",   fmt_money(buybacks),     _pct_of_fcf(buybacks)),
            ("Dividends",        fmt_money(divs),          _pct_of_fcf(divs)),
            ("Debt Repayment",   fmt_money(debt_repaid),   _pct_of_fcf(debt_repaid)),
            ("Total Returned",   fmt_money(total_returned),_pct_of_fcf(total_returned)),
        ],
    )

    # -----------------------------------------------------------------------
    # Section 5: Debt Activity
    # -----------------------------------------------------------------------
    total_issued  = sum(_v(f,"debt_issued") or 0 for f in flows)
    total_repaid  = sum(_v(f,"debt_repaid") or 0 for f in flows)
    net_debt_act  = total_issued - total_repaid

    da_1 = f"Over {len(flows)} years, cumulative debt issued totalled {fmt_money(total_issued)} and debt repaid totalled {fmt_money(total_repaid)}."
    da_2 = f"In {fyn}, {fmt_money(_v(latest,'debt_issued'))} was issued vs. {fmt_money(_v(latest,'debt_repaid'))} repaid."
    da_3 = (
        f"Net debt activity over the full period: {fmt_money(abs(net_debt_act))} net "
        + ("reduction" if net_debt_act < 0 else "increase")
        + " in gross debt."
    )

    # -----------------------------------------------------------------------
    # Section 6: Verdict
    # -----------------------------------------------------------------------
    v1 = f"Generated {fmt_money(fcf)} FCF ({fmt_pct(fcf_margin)} FCF margin) in {fyn} from {fmt_money(ocf)} OCF."
    v2 = f"CapEx intensity of {fmt_pct(capex_pct)} of revenue — {'asset-light' if (capex_pct or 0) < 5 else 'capital-moderate'} model."
    v3 = f"Returned {fmt_money(total_returned)} to shareholders in {fyn} via {fmt_money(buybacks)} buybacks + {fmt_money(divs)} dividends."

    # -----------------------------------------------------------------------
    # Assemble
    # -----------------------------------------------------------------------
    lines = [
        f"# {company} ({ticker}) — Cash Flow Analysis",
        "**Source:** SEC EDGAR 10-K XBRL filings",
        f"**Coverage:** {len(flows)} fiscal years",
        "",
        "---",
        "",
        "## Section 1: Cash Flow Statement Table",
        "",
        cf_table,
        "",
        "---",
        "",
        "## Section 2: Free Cash Flow & Efficiency",
        "",
        fcf_table,
        "",
        "---",
        "",
        "## Section 3: Cash Generation Quality",
        "",
        cq_1,
        cq_2,
        cq_3,
        "",
        "---",
        "",
        f"## Section 4: Capital Allocation ({fyn})",
        "",
        f"FCF available: {fmt_money(fcf)}",
        "",
        alloc_table,
        "",
        "---",
        "",
        "## Section 5: Debt Activity",
        "",
        da_1,
        da_2,
        da_3,
        "",
        "---",
        "",
        "## Section 6: Verdict",
        "",
        f"- {v1}",
        f"- {v2}",
        f"- {v3}",
    ]
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m tools.formatters.cash_flow <artifact_path>", file=sys.stderr)
        sys.exit(1)
    artifact = json.loads(Path(sys.argv[1]).read_text())
    print(format_report(artifact))


if __name__ == "__main__":
    main()
