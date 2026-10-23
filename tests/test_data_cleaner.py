"""Unit tests for the DataCleaner pipeline."""

import pandas as pd
import numpy as np
from src.data_cleaner import DataCleaner


def test_clean_campaign_spend(sample_campaigns_raw):
    cleaner = DataCleaner()
    df_clean = cleaner.clean_campaign_spend(sample_campaigns_raw)

    # Check deduplication
    assert len(df_clean) == 3

    # Check string whitespace trimming
    assert "Google Search" in df_clean["channel"].values
    assert not any(df_clean["channel"].str.startswith(" "))

    # Check negative spend correction
    assert (df_clean["ad_spend"] >= 0).all()

    # Check categorical missing value fill
    assert "Unspecified" in df_clean["target_audience"].values

    # Check audit report
    assert cleaner.audit_report["campaign_spend"]["duplicates_removed"] == 1


def test_clean_customer_leads(sample_leads_raw):
    cleaner = DataCleaner()
    df_clean = cleaner.clean_customer_leads(sample_leads_raw)

    # Check deduplication
    assert len(df_clean) == 4

    # Check lead score imputation (no NaNs remaining)
    assert not df_clean["lead_score"].isna().any()

    # Check converted flag range
    assert set(df_clean["converted_flag"].unique()).issubset({0, 1})

    # Check non-converted customer_id is null/None/NaN
    assert df_clean[df_clean["converted_flag"] == 0]["customer_id"].isna().all()


def test_clean_customer_orders(sample_orders_raw):
    cleaner = DataCleaner()
    df_clean = cleaner.clean_customer_orders(sample_orders_raw)

    # Check deduplication
    assert len(df_clean) == 3

    # Check negative discount handling
    assert (df_clean["discount_amount"] >= 0).all()

    # Check net revenue consistency: net_revenue == order_value - discount_amount
    expected_net = (df_clean["order_value"] - df_clean["discount_amount"]).round(2)
    pd.testing.assert_series_equal(df_clean["net_revenue"], expected_net, check_names=False)

    # Check gross profit consistency: gross_profit == net_revenue - cogs
    expected_profit = (df_clean["net_revenue"] - df_clean["cogs"]).round(2)
    pd.testing.assert_series_equal(df_clean["gross_profit"], expected_profit, check_names=False)
