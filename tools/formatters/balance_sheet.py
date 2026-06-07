"""Balance sheet report formatter — produces the exact section template."""
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .utils import fmt_money, fmt_pct, fmt_ratio, fmt_num, trend_label


def _dedup(sheets: List[Dict]) -> List[Dict]:
    """One entry per period_instant, sorted ascending."""
    seen = {}
    for s in sheets:
        key = s.get("period_instant") or s.get("period", "")
        if key not in seen:
            seen[key] = s
    return sorted(seen.values(), key=lambda x: x.get("period_instant") or x.get("period", ""))


def _label(sheets: List[Dict]) -> List[str]:
    labels = []
    for s in sheets:
        inst = s.get("period_instant", "")
        fy = s.get("fiscal_year", "")
        labels.append(f"FY{fy}" if fy else inst[:4])
    return labels


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
    sheets_raw: List[Dict] = artifact.get("balance_sheets", [])

    sheets = _dedup(sheets_raw)[-5:]
    hdrs = _label(sheets)

    def _v(s: Dict, key: str) -> Optional[float]:
        return s.get(key)

    # -----------------------------------------------------------------------
    # Section 1: Financial Position Table
    # -----------------------------------------------------------------------
    def _goodwill(s: Dict) -> str:
        v = s.get("goodwill")
        return fmt_money(v) if v else "N/R"

    pos_rows = [
        ("**Total Assets**",         [fmt_money(_v(s,"total_assets")) for s in sheets]),
        ("Current Assets",           [fmt_money(_v(s,"current_assets")) for s in sheets]),
        ("Cash & Equivalents",       [fmt_money(_v(s,"cash_and_equivalents")) for s in sheets]),
        ("Marketable Securities",    [fmt_money(_v(s,"marketable_securities")) for s in sheets]),
        ("Accounts Receivable",      [fmt_money(_v(s,"accounts_receivable")) for s in sheets]),
        ("Inventory",                [fmt_money(_v(s,"inventory")) for s in sheets]),
        ("PP&E (Net)",               [fmt_money(_v(s,"property_plant_equipment")) for s in sheets]),
        ("Goodwill",                 [_goodwill(s) for s in sheets]),
        ("**Total Liabilities**",    [fmt_money(_v(s,"total_liabilities")) for s in sheets]),
        ("Current Liabilities",      [fmt_money(_v(s,"current_liabilities")) for s in sheets]),
        ("Long-Term Debt",           [fmt_money(_v(s,"long_term_debt")) for s in sheets]),
        ("Total Debt",               [fmt_money(_v(s,"total_debt")) for s in sheets]),
        ("**Stockholders' Equity**", [fmt_money(_v(s,"total_stockholders_equity")) for s in sheets]),
        ("Retained Earnings",        [fmt_money(_v(s,"retained_earnings")) for s in sheets]),
    ]
    pos_table = _table(["Metric"] + hdrs, [(r[0],) + tuple(r[1]) for r in pos_rows])

    # -----------------------------------------------------------------------
    # Section 2: Capital Structure & Key Ratios
    # -----------------------------------------------------------------------
    cap_rows = [
        ("Working Capital",   [fmt_money(_v(s,"working_capital")) for s in sheets]),
        ("Net Cash Position", [fmt_money(_v(s,"net_cash")) for s in sheets]),
        ("Debt / Equity",     [fmt_ratio(_v(s,"debt_to_equity")) for s in sheets]),
        ("Debt / Assets",     [fmt_ratio(_v(s,"debt_to_assets")) for s in sheets]),
        ("Current Ratio",     [fmt_num(_v(s,"current_ratio")) for s in sheets]),
        ("Book Value / Share",[fmt_num(_v(s,"book_value_per_share")) for s in sheets]),
    ]
    cap_table = _table(["Metric"] + hdrs, [(r[0],) + tuple(r[1]) for r in cap_rows])

    # -----------------------------------------------------------------------
    # Section 3: Liquidity Analysis
    # -----------------------------------------------------------------------
    cr_first = _v(sheets[0], "current_ratio") if sheets else None
    cr_last  = _v(sheets[-1], "current_ratio") if sheets else None
    wc_first = _v(sheets[0], "working_capital") if sheets else None
    wc_last  = _v(sheets[-1], "working_capital") if sheets else None
    nc_first = _v(sheets[0], "net_cash") if sheets else None
    nc_last  = _v(sheets[-1], "net_cash") if sheets else None
    fy0 = hdrs[0] if hdrs else "N/R"
    fyn = hdrs[-1] if hdrs else "N/R"

    liq_1 = (
        f"Current ratio moved from {fmt_num(cr_first)} in {fy0} to {fmt_num(cr_last)} in {fyn} — "
        f"{trend_label(cr_first, cr_last)}; "
        + ("above 1.0x indicates adequate short-term coverage." if (cr_last or 0) >= 1.0
           else "below 1.0x reflects reliance on operating cash flows to meet short-term obligations.")
    )
    wc_dir = "improved" if (wc_last or 0) > (wc_first or 0) else "deteriorated"
    liq_2 = (
        f"Working capital {wc_dir} from {fmt_money(wc_first)} in {fy0} to {fmt_money(wc_last)} in {fyn}, "
        f"{'driven by current liability reduction' if wc_dir == 'improved' else 'reflecting current liability growth'}."
    )
    nc_dir = "strengthened" if (nc_last or 0) > (nc_first or 0) else "weakened"
    liq_3 = (
        f"Net cash position {nc_dir} from {fmt_money(nc_first)} in {fy0} to {fmt_money(nc_last)} in {fyn}; "
        f"{'positive net cash signals low balance sheet risk' if (nc_last or 0) > 0 else 'net debt position warrants monitoring'}."
    )

    # -----------------------------------------------------------------------
    # Section 4: Debt Profile
    # -----------------------------------------------------------------------
    td_first = _v(sheets[0], "total_debt") if sheets else None
    td_last  = _v(sheets[-1], "total_debt") if sheets else None
    ltd_last = _v(sheets[-1], "long_term_debt") if sheets else None
    de_last  = _v(sheets[-1], "debt_to_equity") if sheets else None
    da_last  = _v(sheets[-1], "debt_to_assets") if sheets else None

    debt_dir = "decreased" if (td_last or 0) < (td_first or 0) else "increased"
    debt_1 = f"Total debt stood at {fmt_money(td_last)} in {fyn}, with long-term debt of {fmt_money(ltd_last)}."
    debt_2 = f"Debt {debt_dir} from {fmt_money(td_first)} in {fy0} to {fmt_money(td_last)} in {fyn}."
    debt_3 = (
        f"Leverage ratios of {fmt_ratio(de_last)} debt/equity and {fmt_ratio(da_last)} debt/assets in {fyn} indicate "
        f"{'moderate' if (de_last or 0) < 2 else 'elevated'} financial leverage."
    )

    # -----------------------------------------------------------------------
    # Section 5: Equity & Book Value
    # -----------------------------------------------------------------------
    eq_first = _v(sheets[0], "total_stockholders_equity") if sheets else None
    eq_last  = _v(sheets[-1], "total_stockholders_equity") if sheets else None
    re_last  = _v(sheets[-1], "retained_earnings") if sheets else None
    bv_first = _v(sheets[0], "book_value_per_share") if sheets else None
    bv_last  = _v(sheets[-1], "book_value_per_share") if sheets else None

    eq_dir = "grew" if (eq_last or 0) > (eq_first or 0) else "contracted"
    eq_1 = f"Stockholders' equity {eq_dir} from {fmt_money(eq_first)} in {fy0} to {fmt_money(eq_last)} in {fyn}."
    eq_2 = (
        f"Retained earnings of {fmt_money(re_last)} in {fyn} reflect cumulative profitability net of distributions; "
        + ("negative retained earnings indicate buybacks have exceeded cumulative net income." if (re_last or 0) < 0 else "positive balance supports financial flexibility.")
    )
    bv_dir = "increased" if (bv_last or 0) > (bv_first or 0) else "declined"
    eq_3 = f"Book value per share {bv_dir} from {fmt_num(bv_first)} in {fy0} to {fmt_num(bv_last)} in {fyn}."

    # -----------------------------------------------------------------------
    # Section 6: Verdict
    # -----------------------------------------------------------------------
    v1 = f"Asset base of {fmt_money(_v(sheets[-1],'total_assets'))} in {fyn}, with {fmt_pct(_v(sheets[-1],'current_assets') / _v(sheets[-1],'total_assets') * 100 if _v(sheets[-1],'total_assets') else None)} current."
    v2 = f"Leverage at {fmt_ratio(de_last)} D/E and {fmt_ratio(da_last)} D/A — {'conservative' if (de_last or 0) < 1 else 'moderate' if (de_last or 0) < 2 else 'elevated'} relative to assets."
    v3 = f"Liquidity ratio of {fmt_num(cr_last)} with working capital of {fmt_money(wc_last)} in {fyn}."

    # -----------------------------------------------------------------------
    # Assemble
    # -----------------------------------------------------------------------
    lines = [
        f"# {company} ({ticker}) — Balance Sheet Analysis",
        "**Source:** SEC EDGAR 10-K XBRL filings",
        f"**Coverage:** {len(sheets)} fiscal years",
        "",
        "---",
        "",
        "## Section 1: Financial Position Table",
        "",
        pos_table,
        "",
        "---",
        "",
        "## Section 2: Capital Structure & Key Ratios",
        "",
        cap_table,
        "",
        "---",
        "",
        "## Section 3: Liquidity Analysis",
        "",
        liq_1,
        liq_2,
        liq_3,
        "",
        "---",
        "",
        "## Section 4: Debt Profile",
        "",
        debt_1,
        debt_2,
        debt_3,
        "",
        "---",
        "",
        "## Section 5: Equity & Book Value",
        "",
        eq_1,
        eq_2,
        eq_3,
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
        print("Usage: python -m tools.formatters.balance_sheet <artifact_path>", file=sys.stderr)
        sys.exit(1)
    artifact = json.loads(Path(sys.argv[1]).read_text())
    print(format_report(artifact))


if __name__ == "__main__":
    main()
