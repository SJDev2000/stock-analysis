from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class IncomeMetrics:
    period: str
    period_type: str
    fiscal_year: Optional[int] = None
    fiscal_period: Optional[str] = None
    filing_date: Optional[str] = None
    revenue: Optional[float] = None
    cost_of_revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    gross_margin_pct: Optional[float] = None
    operating_expenses: Optional[float] = None
    research_and_development: Optional[float] = None
    selling_general_admin: Optional[float] = None
    operating_income: Optional[float] = None
    operating_margin_pct: Optional[float] = None
    interest_expense: Optional[float] = None
    other_income_expense: Optional[float] = None
    income_before_tax: Optional[float] = None
    income_tax_expense: Optional[float] = None
    net_income: Optional[float] = None
    net_margin_pct: Optional[float] = None
    ebitda: Optional[float] = None
    ebitda_margin_pct: Optional[float] = None
    eps_basic: Optional[float] = None
    eps_diluted: Optional[float] = None
    shares_outstanding_basic: Optional[float] = None
    shares_outstanding_diluted: Optional[float] = None


@dataclass
class GrowthMetrics:
    period: str
    comparison_period: str
    growth_type: str
    revenue_growth_abs: Optional[float] = None
    revenue_growth_pct: Optional[float] = None
    gross_profit_growth_abs: Optional[float] = None
    gross_profit_growth_pct: Optional[float] = None
    operating_income_growth_abs: Optional[float] = None
    operating_income_growth_pct: Optional[float] = None
    net_income_growth_abs: Optional[float] = None
    net_income_growth_pct: Optional[float] = None
    ebitda_growth_abs: Optional[float] = None
    ebitda_growth_pct: Optional[float] = None
    eps_diluted_growth_abs: Optional[float] = None
    eps_diluted_growth_pct: Optional[float] = None
    margin_expansion_gross_bps: Optional[float] = None
    margin_expansion_operating_bps: Optional[float] = None
    margin_expansion_net_bps: Optional[float] = None


@dataclass
class SegmentRevenue:
    segment_name: str
    revenue: Optional[float] = None
    percentage_of_total: Optional[float] = None
    period: str = ""


@dataclass
class CoreIncomeMetrics:
    period: str
    period_type: str
    fiscal_year: Optional[int] = None
    revenue: Optional[float] = None
    cost_of_revenue: Optional[float] = None
    gross_income: Optional[float] = None
    gross_margin_pct: Optional[float] = None
    operating_income: Optional[float] = None
    operating_margin_pct: Optional[float] = None
    net_income: Optional[float] = None
    net_profit_margin_pct: Optional[float] = None
    eps_diluted: Optional[float] = None


@dataclass
class GrowthMomentum:
    period: str
    comparison_period: str
    growth_type: str
    revenue_growth_dollar: Optional[float] = None
    revenue_growth_pct: Optional[float] = None
    net_income_growth_dollar: Optional[float] = None
    net_income_growth_pct: Optional[float] = None
    eps_growth_dollar: Optional[float] = None
    eps_growth_pct: Optional[float] = None


@dataclass
class IncomeStatementReport:
    ticker: str
    company_name: str
    annual_statements: List[Dict] = field(default_factory=list)
    quarterly_statements: List[Dict] = field(default_factory=list)
    annual_core: List[Dict] = field(default_factory=list)
    quarterly_core: List[Dict] = field(default_factory=list)
    yoy_growth: List[Dict] = field(default_factory=list)
    qoq_growth: List[Dict] = field(default_factory=list)
    annual_growth: List[Dict] = field(default_factory=list)
    quarterly_growth: List[Dict] = field(default_factory=list)
    revenue_segments: List[Dict] = field(default_factory=list)
    top_segment: Optional[Dict] = None
    summary: Dict = field(default_factory=dict)
