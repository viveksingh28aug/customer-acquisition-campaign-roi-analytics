"""Regression and audit tests addressing production-readiness requirements."""

import numpy as np
import pandas as pd
import pytest

from src.database import DatabaseManager
from src.kpi_calculator import KPICalculator
from src.scenario_planner import ScenarioPlanner
from src.statistical_analysis import StatisticalEngine


def test_format_p_value_small():
    """Verify p-value formatting avoids literal p = 0 or 0.0000e+00 display."""
    assert StatisticalEngine.format_p_value(0.0) == "< 0.0001"
    assert StatisticalEngine.format_p_value(1e-9) == "< 0.0001"
    assert StatisticalEngine.format_p_value(0.00009) == "< 0.0001"
    assert StatisticalEngine.format_p_value(0.04123) == "0.0412"
    assert StatisticalEngine.format_p_value(0.8500) == "0.8500"


def test_payback_months_edge_cases():
    """Verify payback period properly returns None for negative/zero margins and 0 for free CAC."""
    # Negative margin: customer is unprofitable, payback is unrecoverable
    assert KPICalculator.calculate_payback_months(cac=100.0, monthly_margin_per_customer=-10.0) is None
    # Zero margin: customer never pays back
    assert KPICalculator.calculate_payback_months(cac=100.0, monthly_margin_per_customer=0.0) is None
    # Zero CAC: immediate payback
    assert KPICalculator.calculate_payback_months(cac=0.0, monthly_margin_per_customer=25.0) == 0.0
    # Normal case: $100 CAC with $20/mo margin = 5.0 months
    assert KPICalculator.calculate_payback_months(cac=100.0, monthly_margin_per_customer=20.0) == 5.0


def test_budget_reallocation_preserves_total_budget():
    """Verify budget reallocation strictly preserves total spend and prevents negative allocations."""
    df_summary = pd.DataFrame([
        {"channel": "Meta Ads", "total_spend": 10000.0, "cac": 50.0, "arpu": 120.0, "acquired_customers": 200, "total_net_revenue": 24000.0},
        {"channel": "Email Marketing", "total_spend": 2000.0, "cac": 10.0, "arpu": 90.0, "acquired_customers": 200, "total_net_revenue": 18000.0},
    ])

    res = ScenarioPlanner.simulate_budget_reallocation(
        channel_summary=df_summary,
        source_channel="Meta Ads",
        target_channel="Email Marketing",
        reallocation_pct=0.25,
    )

    assert "error" not in res
    assert res["budget_delta"] == 0.0
    assert res["projected_spend"] == res["baseline_spend"] == 12000.0
    assert res["source_projected_spend"] == 7500.0
    assert res["target_projected_spend"] == 4500.0
    assert res["shifted_budget"] == 2500.0
    assert res["net_customer_delta"] > 0
    assert res["net_revenue_delta"] > 0
    assert "projection_disclaimer" in res


def test_budget_reallocation_guards():
    """Verify error handling on invalid allocations."""
    df_summary = pd.DataFrame([
        {"channel": "Meta Ads", "total_spend": 5000.0, "cac": 50.0, "arpu": 120.0, "acquired_customers": 100, "total_net_revenue": 12000.0},
    ])

    # Same channel
    err_same = ScenarioPlanner.simulate_budget_reallocation(df_summary, "Meta Ads", "Meta Ads", 0.10)
    assert "error" in err_same

    # Channel missing
    err_missing = ScenarioPlanner.simulate_budget_reallocation(df_summary, "Meta Ads", "Google Search", 0.10)
    assert "error" in err_missing


def test_empty_dataframe_handling():
    """Verify that KPI calculations handle empty dataframes gracefully without raising exceptions."""
    calc = KPICalculator()
    empty_c = pd.DataFrame()
    empty_l = pd.DataFrame()
    empty_o = pd.DataFrame()

    summary = calc.calculate_channel_summary(empty_c, empty_l, empty_o)
    assert summary.empty
    assert "channel" in summary.columns

    totals = calc.calculate_executive_totals(summary)
    assert totals["total_spend"] == 0.0
    assert totals["blended_cac"] == 0.0
    assert totals["blended_roas"] == 0.0


def test_filtered_query_duckdb(memory_db_manager, sample_campaigns_raw, sample_leads_raw, sample_orders_raw):
    """Verify that run_filtered_named_query intercepts query execution and restores physical tables."""
    from src.data_cleaner import DataCleaner
    cleaner = DataCleaner()
    df_c = cleaner.clean_campaign_spend(sample_campaigns_raw)
    df_l = cleaner.clean_customer_leads(sample_leads_raw)
    df_o = cleaner.clean_customer_orders(sample_orders_raw)

    memory_db_manager.load_clean_data(df_c, df_l, df_o)

    # Filter to only Google Search
    df_c_filt = df_c[df_c["channel"] == "Google Search"].copy()
    df_l_filt = df_l[df_l["channel"] == "Google Search"].copy()
    df_o_filt = df_o.copy()

    filt_res = memory_db_manager.run_filtered_named_query("channel_performance_kpis", df_c_filt, df_l_filt, df_o_filt)

    assert len(filt_res) == 1
    assert filt_res.iloc[0]["channel"] == "Google Search"

    # Verify physical base tables remain intact
    full_res = memory_db_manager.run_named_query("channel_performance_kpis")
    assert len(full_res) >= 2


def test_executive_totals_edge_cases():
    """Verify calculate_executive_totals handles zero customers, NaNs, missing columns, and None."""
    calc = KPICalculator()

    # 1. Zero customers scenario
    zero_cust_df = pd.DataFrame([
        {"channel": "Meta Ads", "total_spend": 5000.0, "acquired_customers": 0, "total_leads": 100, "total_net_revenue": 0.0, "total_gross_profit": 0.0},
        {"channel": "Google Search", "total_spend": 3000.0, "acquired_customers": 0, "total_leads": 50, "total_net_revenue": 0.0, "total_gross_profit": 0.0},
    ])
    totals = calc.calculate_executive_totals(zero_cust_df)
    assert totals["total_spend"] == 8000.0
    assert totals["total_customers"] == 0
    assert totals["blended_cac"] == 0.0  # Safe zero division
    assert totals["blended_cvr_pct"] == 0.0
    assert totals["blended_arpu"] == 0.0

    # 2. DataFrame with NaNs
    nan_df = pd.DataFrame([
        {"channel": "Meta Ads", "total_spend": 5000.0, "acquired_customers": np.nan, "total_leads": 100, "total_net_revenue": np.nan, "total_gross_profit": 1000.0},
        {"channel": "Organic Search", "total_spend": np.nan, "acquired_customers": 50, "total_leads": np.nan, "total_net_revenue": 5000.0, "total_gross_profit": np.nan},
    ])
    totals_nan = calc.calculate_executive_totals(nan_df)
    assert totals_nan["total_spend"] == 5000.0
    assert totals_nan["total_customers"] == 50
    assert totals_nan["blended_cac"] == 100.0  # 5000 / 50
    assert totals_nan["paid_spend"] == 5000.0
    assert totals_nan["paid_customers"] == 0

    # 3. None input
    totals_none = calc.calculate_executive_totals(None)
    assert totals_none["total_spend"] == 0.0
    assert totals_none["blended_cac"] == 0.0

    # 4. DataFrame missing expected columns entirely
    incomplete_df = pd.DataFrame({"random_col": [1, 2, 3]})
    totals_incomplete = calc.calculate_executive_totals(incomplete_df)
    assert totals_incomplete["total_spend"] == 0.0
    assert totals_incomplete["total_customers"] == 0
    assert totals_incomplete["blended_cac"] == 0.0


def test_calculate_cac_robustness():
    """Verify calculate_cac handles inf, nan, string, negative, and None safely."""
    calc = KPICalculator()
    assert calc.calculate_cac(spend=1000.0, customers=20) == 50.0
    assert calc.calculate_cac(spend=1000.0, customers=0) == 0.0
    assert calc.calculate_cac(spend=1000.0, customers=-5) == 0.0
    assert calc.calculate_cac(spend=-1000.0, customers=20) == 0.0
    assert calc.calculate_cac(spend=0.0, customers=20) == 0.0
    assert calc.calculate_cac(spend=None, customers=20) == 0.0
    assert calc.calculate_cac(spend=1000.0, customers=None) == 0.0
    assert calc.calculate_cac(spend=float("nan"), customers=20) == 0.0
    assert calc.calculate_cac(spend=1000.0, customers=float("nan")) == 0.0
    assert calc.calculate_cac(spend=float("inf"), customers=20) == 0.0
    assert calc.calculate_cac(spend=1000.0, customers=float("inf")) == 0.0

