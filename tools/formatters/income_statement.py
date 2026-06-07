"""Income statement report formatter — produces the exact section template."""
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .utils import fmt_money, fmt_pct, fmt_pct_change, fmt_num, bps, trend_label


def _cagr(first: Optional[float], last: Optional[float], years: int) -> str:
    if not first or not last or years <= 0 or first <= 0:
        return "N/R"
    rate = (last / first) ** (1 / years) - 1
    sign = "+" if rate >= 0 else ""
    return f"{sign}{rate*100:.1f}%"


def _col_header(stmts: List[Dict]) -> List[str]:
    return [s["period"] for s in stmts]


def _row(label: str, values: List[str], widths: List[int]) -> str:
    cells = [label.ljust(widths[0])] + [v.rjust(widths[i+1]) for i, v in enumerate(values)]
    return "| " + " | ".join(cells) + " |"


def _sep(widths: List[int]) -> str:
    return "|" + "|".join("-" * (w + 2) for w in widths) + "|"


def _table(headers: List[str], rows: List[tuple]) -> str:
    col0_w = max(len(r[0]) for r in rows)
    col_ws = [max(len(h), max(len(r[i+1]) for r in rows)) for i, h in enumerate(headers[1:])]
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
    report = artifact.get("report", {})

    annual: List[Dict] = report.get("annual_statements", [])
    quarterly: List[Dict] = report.get("quarterly_statements", [])
    yoy: List[Dict] = report.get("yoy_growth", [])
    qoq: List[Dict] = report.get("qoq_growth", [])
    segments: List[Dict] = report.get("revenue_segments", [])

    # Sort annual ascending
    annual = sorted(annual, key=lambda x: x.get("fiscal_year", 0))
    quarterly = sorted(quarterly, key=lambda x: (x.get("fiscal_year", 0), x.get("fiscal_period", "")))

    ann = annual[-5:] if len(annual) >= 5 else annual
    qtr = quarterly[-4:] if len(quarterly) >= 4 else quarterly

    ann_hdrs = [s["period"] for s in ann]
    qtr_hdrs = [s["period"] for s in qtr]

    def _v(stmt: Dict, key: str) -> Optional[float]:
        return stmt.get(key)

    # -----------------------------------------------------------------------
    # Section 1: Financial Summary Tables
    # -----------------------------------------------------------------------

    # Annual table rows
    ann_rows = [
        ("Revenue",            [fmt_money(_v(s,"revenue")) for s in ann]),
        ("Cost of Revenue",    [fmt_money(_v(s,"cost_of_revenue")) for s in ann]),
        ("Gross Profit",       [fmt_money(_v(s,"gross_profit")) for s in ann]),
        ("Gross Margin %",     [fmt_pct(_v(s,"gross_margin_pct")) for s in ann]),
        ("Operating Income",   [fmt_money(_v(s,"operating_income")) for s in ann]),
        ("Operating Margin %", [fmt_pct(_v(s,"operating_margin_pct")) for s in ann]),
        ("Net Income",         [fmt_money(_v(s,"net_income")) for s in ann]),
        ("Net Margin %",       [fmt_pct(_v(s,"net_margin_pct")) for s in ann]),
        ("EPS (Diluted)",      [fmt_num(_v(s,"eps_diluted")) for s in ann]),
        ("EBITDA",             [fmt_money(_v(s,"ebitda")) for s in ann]),
    ]
    ann_table = _table(["Metric"] + ann_hdrs, [(r[0],) + tuple(r[1]) for r in ann_rows])

    # Quarterly table rows
    qtr_rows = [
        ("Revenue",          [fmt_money(_v(s,"revenue")) for s in qtr]),
        ("Gross Profit",     [fmt_money(_v(s,"gross_profit")) for s in qtr]),
        ("Gross Margin %",   [fmt_pct(_v(s,"gross_margin_pct")) for s in qtr]),
        ("Operating Income", [fmt_money(_v(s,"operating_income")) for s in qtr]),
        ("Net Income",       [fmt_money(_v(s,"net_income")) for s in qtr]),
        ("EPS (Diluted)",    [fmt_num(_v(s,"eps_diluted")) for s in qtr]),
    ]
    qtr_table = _table(["Metric"] + qtr_hdrs, [(r[0],) + tuple(r[1]) for r in qtr_rows])

    # -----------------------------------------------------------------------
    # Section 2: Growth Trajectory
    # -----------------------------------------------------------------------

    # YoY growth — sort matching annual periods
    yoy_sorted = sorted(yoy, key=lambda x: x.get("period", ""))[-4:]

    def _yoy_col(item: Dict, key: str) -> str:
        v = item.get(key)
        return fmt_pct_change(v) if v is not None else "N/R"

    yoy_hdrs = [f'{y["period"]}/{y["comparison_period"]}' for y in yoy_sorted]
    yoy_rows = [
        ("Revenue YoY %",   [_yoy_col(y, "revenue_growth_pct") for y in yoy_sorted]),
        ("Net Income %",    [_yoy_col(y, "net_income_growth_pct") for y in yoy_sorted]),
        ("EPS %",           [_yoy_col(y, "eps_growth_pct") for y in yoy_sorted]),
    ]
    yoy_table = _table(["Metric"] + yoy_hdrs, [(r[0],) + tuple(r[1]) for r in yoy_rows])

    # QoQ growth
    qoq_sorted = sorted(qoq, key=lambda x: (x.get("period", "")))[-3:]
    qoq_hdrs = [f'{q["period"]}/{q["comparison_period"]}' for q in qoq_sorted] if qoq_sorted else ["N/R"]
    qoq_rows = [
        ("Revenue QoQ %",  [fmt_pct_change(q.get("revenue_growth_pct")) for q in qoq_sorted] if qoq_sorted else ["N/R"]),
        ("Net Income %",   [fmt_pct_change(q.get("net_income_growth_pct")) for q in qoq_sorted] if qoq_sorted else ["N/R"]),
    ]
    qoq_table = _table(["Metric"] + qoq_hdrs, [(r[0],) + tuple(r[1]) for r in qoq_rows])

    # CAGR
    years = len(ann) - 1
    rev_first = _v(ann[0], "revenue") if ann else None
    rev_last  = _v(ann[-1], "revenue") if ann else None
    ni_first  = _v(ann[0], "net_income") if ann else None
    ni_last   = _v(ann[-1], "net_income") if ann else None
    rev_cagr  = _cagr(rev_first, rev_last, years)
    ni_cagr   = _cagr(ni_first, ni_last, years)
    fy_range  = f"{ann[0]['period']}–{ann[-1]['period']}" if len(ann) >= 2 else "N/R"

    # -----------------------------------------------------------------------
    # Section 3: Margin Analysis
    # -----------------------------------------------------------------------

    gm_a  = _v(ann[0], "gross_margin_pct") if ann else None
    gm_z  = _v(ann[-1], "gross_margin_pct") if ann else None
    om_a  = _v(ann[0], "operating_margin_pct") if ann else None
    om_z  = _v(ann[-1], "operating_margin_pct") if ann else None
    nm_a  = _v(ann[0], "net_margin_pct") if ann else None
    nm_z  = _v(ann[-1], "net_margin_pct") if ann else None
    fy0   = ann[0]["period"] if ann else "N/R"
    fyn   = ann[-1]["period"] if ann else "N/R"

    def _margin_sentence(label: str, a: Optional[float], z: Optional[float]) -> str:
        return (
            f"**{label}:** moved from {fmt_pct(a)} in {fy0} to {fmt_pct(z)} in {fyn} "
            f"({bps(a, z)}) — {trend_label(a, z)}."
        )

    gm_sentence = _margin_sentence("Gross Margin", gm_a, gm_z)
    om_sentence = _margin_sentence("Operating Margin", om_a, om_z)
    nm_sentence = _margin_sentence("Net Margin", nm_a, nm_z)

    # Combined trend
    trends = [trend_label(gm_a, gm_z), trend_label(om_a, om_z), trend_label(nm_a, nm_z)]
    if trends.count("expanding") >= 2:
        combined = "Dual efficiency"
    elif trends.count("contracting") >= 2:
        combined = "Margin pressure"
    else:
        combined = "Reinvestment phase"

    # -----------------------------------------------------------------------
    # Section 4: Revenue Segments
    # -----------------------------------------------------------------------

    if segments:
        seg_period = segments[0].get("period", "")
        seg_rows_data = [(s["segment_name"], fmt_money(s.get("revenue")), fmt_pct(s.get("percentage_of_total")))
                         for s in sorted(segments, key=lambda x: -(x.get("revenue") or 0))]
        seg_table = _table(
            [f"Segment", f"Revenue ({seg_period})", "% of Total"],
            seg_rows_data,
        )
        top_seg = seg_rows_data[0]
        top_sentence = f"Top segment ({top_seg[0]}) accounts for {segments[0].get('percentage_of_total',0):.1f}% of total revenue."
    else:
        seg_table = "N/R"
        top_sentence = "Segment data not available."

    # -----------------------------------------------------------------------
    # Section 5: Verdict
    # -----------------------------------------------------------------------

    latest_rev_growth = yoy_sorted[-1].get("revenue_growth_pct") if yoy_sorted else None
    latest_ni_growth  = yoy_sorted[-1].get("net_income_growth_pct") if yoy_sorted else None

    verdict_1 = (
        f"Revenue grew {fmt_pct_change(latest_rev_growth)} YoY to {fmt_money(rev_last)} in {fyn}, "
        f"with a {rev_cagr} CAGR over {years} years — "
        + ("accelerating" if latest_rev_growth and latest_rev_growth > 5 else "modest") + " top-line growth."
    )
    verdict_2 = (
        f"Net income {fmt_pct_change(latest_ni_growth)} YoY to {fmt_money(ni_last)} in {fyn}; "
        f"net margin of {fmt_pct(nm_z)} represents a {bps(nm_a, nm_z)} shift from {fy0}."
    )
    latest_eps = _v(ann[-1], "eps_diluted") if ann else None
    verdict_3 = (
        f"EPS (diluted) of {fmt_num(latest_eps)} in {fyn}; "
        f"{'margin expansion and share buybacks' if combined == 'Dual efficiency' else 'cost pressures'} "
        f"are the primary earnings drivers."
    )

    # -----------------------------------------------------------------------
    # Assemble report
    # -----------------------------------------------------------------------

    lines = [
        f"# {company} ({ticker}) — Income Statement Analysis",
        "**Source:** SEC EDGAR 10-K / 10-Q XBRL filings",
        f"**Coverage:** {len(ann)} fiscal years + {len(qtr)} recent quarters",
        "",
        "---",
        "",
        "## Section 1: Financial Summary Table",
        "",
        "### Annual",
        "",
        ann_table,
        "",
        "### Quarterly",
        "",
        qtr_table,
        "",
        "---",
        "",
        "## Section 2: Growth Trajectory",
        "",
        "### Year-over-Year Growth",
        "",
        yoy_table,
        "",
        "### Quarter-over-Quarter Growth",
        "",
        qoq_table,
        "",
        f"**Revenue CAGR ({fy_range}):** {rev_cagr}",
        f"**Net Income CAGR ({fy_range}):** {ni_cagr}",
        "",
        "---",
        "",
        "## Section 3: Margin Analysis",
        "",
        gm_sentence,
        om_sentence,
        nm_sentence,
        "",
        f"**Combined trend:** {combined}",
        "",
        "---",
        "",
        "## Section 4: Revenue Segments",
        "",
        seg_table,
        "",
        top_sentence,
        "",
        "---",
        "",
        "## Section 5: Verdict",
        "",
        f"- {verdict_1}",
        f"- {verdict_2}",
        f"- {verdict_3}",
    ]

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m tools.formatters.income_statement <artifact_path>", file=sys.stderr)
        sys.exit(1)
    path = Path(sys.argv[1])
    artifact = json.loads(path.read_text())
    print(format_report(artifact))


if __name__ == "__main__":
    main()
