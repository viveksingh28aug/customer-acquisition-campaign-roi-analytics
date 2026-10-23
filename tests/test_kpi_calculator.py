"""Unit tests for the KPICalculator engine."""

import pytest
import pandas as pd
from src.kpi_calculator import KPICalculator


def test_ctr_calculation():
    assert KPICalculator.calculate_ctr(clicks=50, impressions=1000) == 5.0
    assert KPICalculator.calculate_ctr(clicks=0, impressions=0) == 0.0
    assert KPICalculator.calculate_ctr(clicks=10, impressions=0) == 0.0


def test_cpc_calculation():
    assert KPICalculator.calculate_cpc(spend=250.0, clicks=100) == 2.50
    assert KPICalculator.calculate_cpc(spend=100.0, clicks=0) == 0.0


def test_conversion_rate():
    assert KPICalculator.calculate_conversion_rate(conversions=25, total_opportunities=500) == 5.0
    assert KPICalculator.calculate_conversion_rate(conversions=0, total_opportunities=0) == 0.0


def test_cac_calculation():
    assert KPICalculator.calculate_cac(spend=1000.0, customers=20) == 50.0
    assert KPICalculator.calculate_cac(spend=500.0, customers=0) == 0.0


def test_roas_calculation():
    assert KPICalculator.calculate_roas(net_revenue=3500.0, spend=1000.0) == 3.50
    assert KPICalculator.calculate_roas(net_revenue=0.0, spend=0.0) == 0.0


def test_net_roi():
    # Spend = 1000, Gross Profit = 1500 -> ROI = ((1500 - 1000) / 1000) * 100 = 50.0%
    assert KPICalculator.calculate_net_roi(gross_profit=1500.0, spend=1000.0) == 50.0
    # Spend = 1000, Gross Profit = 800 -> ROI = -20.0%
    assert KPICalculator.calculate_net_roi(gross_profit=800.0, spend=1000.0) == -20.0
    assert KPICalculator.calculate_net_roi(gross_profit=100.0, spend=0.0) == 0.0


def test_ltv_cac_ratio():
    assert KPICalculator.calculate_ltv_cac_ratio(ltv=180.0, cac=60.0) == 3.0
    assert KPICalculator.calculate_ltv_cac_ratio(ltv=100.0, cac=0.0) == 0.0


def test_channel_summary_aggregation(sample_campaigns_raw, sample_leads_raw, sample_orders_raw):
    from src.data_cleaner import DataCleaner
    cleaner = DataCleaner()
    df_camp = cleaner.clean_campaign_spend(sample_campaigns_raw)
    df_leads = cleaner.clean_customer_leads(sample_leads_raw)
    df_orders = cleaner.clean_customer_orders(sample_orders_raw)

    calc = KPICalculator()
    summary = calc.calculate_channel_summary(df_camp, df_leads, df_orders)

    assert not summary.empty
    assert "channel" in summary.columns
    assert "cac" in summary.columns
    assert "roas" in summary.columns
    assert "net_roi_pct" in summary.columns
    assert len(summary) >= 2

    # Verify calculate_executive_totals on populated channel summary
    totals = calc.calculate_executive_totals(summary)
    assert totals["total_spend"] > 0
    assert totals["total_customers"] > 0
    assert totals["total_leads"] > 0
    assert totals["blended_cac"] > 0
    assert totals["blended_roas"] >= 0
    assert "paid_cac" in totals
