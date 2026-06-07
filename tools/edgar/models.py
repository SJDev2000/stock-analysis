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


@dataclass
class BalanceSheetMetrics:
    period: str
    period_instant: Optional[str] = None
    fiscal_year: Optional[int] = None
    filing_date: Optional[str] = None
    total_assets: Optional[float] = None
    current_assets: Optional[float] = None
    noncurrent_assets: Optional[float] = None
    cash_and_equivalents: Optional[float] = None
    marketable_securities: Optional[float] = None
    accounts_receivable: Optional[float] = None
    inventory: Optional[float] = None
    property_plant_equipment: Optional[float] = None
    goodwill: Optional[float] = None
    intangible_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    current_liabilities: Optional[float] = None
    noncurrent_liabilities: Optional[float] = None
    long_term_debt: Optional[float] = None
    current_debt: Optional[float] = None
    accounts_payable: Optional[float] = None
    total_stockholders_equity: Optional[float] = None
    retained_earnings: Optional[float] = None
    shares_outstanding: Optional[float] = None
    working_capital: Optional[float] = None
    total_debt: Optional[float] = None
    net_cash: Optional[float] = None
    book_value_per_share: Optional[float] = None
    current_ratio: Optional[float] = None
    debt_to_equity: Optional[float] = None
    debt_to_assets: Optional[float] = None


@dataclass
class CashFlowMetrics:
    period: str
    period_type: str
    fiscal_year: Optional[int] = None
    filing_date: Optional[str] = None
    operating_cash_flow: Optional[float] = None
    depreciation_amortization: Optional[float] = None
    stock_based_compensation: Optional[float] = None
    investing_cash_flow: Optional[float] = None
    capital_expenditures: Optional[float] = None
    acquisitions: Optional[float] = None
    financing_cash_flow: Optional[float] = None
    dividends_paid: Optional[float] = None
    share_buybacks: Optional[float] = None
    debt_issued: Optional[float] = None
    debt_repaid: Optional[float] = None
    free_cash_flow: Optional[float] = None
    fcf_margin_pct: Optional[float] = None
    capex_to_revenue_pct: Optional[float] = None
    shareholder_return: Optional[float] = None


@dataclass
class ProfitabilityRatios:
    period: str
    fiscal_year: Optional[int] = None
    gross_margin_pct: Optional[float] = None
    operating_margin_pct: Optional[float] = None
    net_margin_pct: Optional[float] = None
    return_on_assets_pct: Optional[float] = None
    return_on_equity_pct: Optional[float] = None
    return_on_invested_capital_pct: Optional[float] = None
    free_cash_flow_margin_pct: Optional[float] = None


@dataclass
class LeverageRatios:
    period: str
    fiscal_year: Optional[int] = None
    debt_to_equity: Optional[float] = None
    debt_to_assets: Optional[float] = None
    interest_coverage: Optional[float] = None
    net_debt_to_ebitda: Optional[float] = None
    equity_multiplier: Optional[float] = None
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None


@dataclass
class ValuationRatios:
    period: str
    fiscal_year: Optional[int] = None
    book_value_per_share: Optional[float] = None
    earnings_per_share: Optional[float] = None
    revenue_per_share: Optional[float] = None
    free_cash_flow_per_share: Optional[float] = None


@dataclass
class OperatingRatios:
    period: str
    fiscal_year: Optional[int] = None
    asset_turnover: Optional[float] = None
    inventory_turnover: Optional[float] = None
    receivables_turnover: Optional[float] = None
    payables_turnover: Optional[float] = None
    days_sales_outstanding: Optional[float] = None
    days_inventory_outstanding: Optional[float] = None
    days_payable_outstanding: Optional[float] = None
    cash_conversion_cycle: Optional[float] = None
    capex_to_revenue_pct: Optional[float] = None
    sbc_to_revenue_pct: Optional[float] = None
