"""Pytest fixtures for unit and integration testing."""

from datetime import datetime
import pytest
import pandas as pd
import numpy as np

from src.database import DatabaseManager


@pytest.fixture
def sample_campaigns_raw() -> pd.DataFrame:
    """Fixture providing raw campaign records with intentional anomalies."""
    return pd.DataFrame([
        {"campaign_id": "CMP-1", "campaign_name": "Search_Q1", "channel": " Google Search ", "date": "2026-01-01", "ad_spend": 500.0, "impressions": 10000, "clicks": 250, "target_audience": "Tech", "region": "NA"},
        {"campaign_id": "CMP-1", "campaign_name": "Search_Q1", "channel": "Google Search", "date": "2026-01-01", "ad_spend": 500.0, "impressions": 10000, "clicks": 250, "target_audience": "Tech", "region": "NA"}, # Duplicate
        {"campaign_id": "CMP-1", "campaign_name": "Search_Q1", "channel": "Google Search", "date": "2026-01-02", "ad_spend": -50.0, "impressions": 8000, "clicks": 200, "target_audience": None, "region": "NA"}, # Negative spend + missing audience
        {"campaign_id": "CMP-2", "campaign_name": "Meta_Q1", "channel": "Meta Ads", "date": "2026-01-01", "ad_spend": 300.0, "impressions": 15000, "clicks": 400, "target_audience": "Broad", "region": "EMEA"},
    ])


@pytest.fixture
def sample_leads_raw() -> pd.DataFrame:
    """Fixture providing raw customer leads with intentional anomalies."""
    return pd.DataFrame([
        {"lead_id": "L-1", "customer_id": "C-1", "campaign_id": "CMP-1", "channel": "Google Search", "lead_date": "2026-01-01 10:00:00", "converted_flag": 1, "conversion_date": "2026-01-02 12:00:00", "signup_platform": "Web", "lead_score": 85.0},
        {"lead_id": "L-1", "customer_id": "C-1", "campaign_id": "CMP-1", "channel": "Google Search", "lead_date": "2026-01-01 10:00:00", "converted_flag": 1, "conversion_date": "2026-01-02 12:00:00", "signup_platform": "Web", "lead_score": 85.0}, # Duplicate
        {"lead_id": "L-2", "customer_id": None, "campaign_id": "CMP-1", "channel": "Google Search", "lead_date": "2026-01-01 11:00:00", "converted_flag": 0, "conversion_date": None, "signup_platform": "iOS", "lead_score": np.nan}, # Missing score
        {"lead_id": "L-3", "customer_id": "C-2", "campaign_id": "CMP-2", "channel": "Meta Ads", "lead_date": "2026-01-01 14:00:00", "converted_flag": 1, "conversion_date": "2026-01-01 16:00:00", "signup_platform": "Android", "lead_score": 70.0},
        {"lead_id": "L-4", "customer_id": None, "campaign_id": "CMP-2", "channel": "Meta Ads", "lead_date": "2026-01-02 09:00:00", "converted_flag": 0, "conversion_date": None, "signup_platform": "Web", "lead_score": 45.0},
    ])


@pytest.fixture
def sample_orders_raw() -> pd.DataFrame:
    """Fixture providing raw order transactions with intentional anomalies."""
    return pd.DataFrame([
        {"order_id": "ORD-1", "customer_id": "C-1", "order_date": "2026-01-02 14:00:00", "order_value": 100.0, "discount_amount": 10.0, "net_revenue": 90.0, "cogs": 35.0, "gross_profit": 55.0, "payment_method": "Credit Card"},
        {"order_id": "ORD-1", "customer_id": "C-1", "order_date": "2026-01-02 14:00:00", "order_value": 100.0, "discount_amount": 10.0, "net_revenue": 90.0, "cogs": 35.0, "gross_profit": 55.0, "payment_method": "Credit Card"}, # Duplicate
        {"order_id": "ORD-2", "customer_id": "C-1", "order_date": "2026-01-20 10:00:00", "order_value": 150.0, "discount_amount": -15.0, "net_revenue": 150.0, "cogs": 50.0, "gross_profit": 100.0, "payment_method": "PayPal"}, # Negative discount
        {"order_id": "ORD-3", "customer_id": "C-2", "order_date": "2026-01-01 17:00:00", "order_value": 80.0, "discount_amount": 0.0, "net_revenue": 80.0, "cogs": 28.0, "gross_profit": 52.0, "payment_method": "Apple Pay"},
    ])


@pytest.fixture
def memory_db_manager(tmp_path):
    """Fixture providing an isolated embedded DuckDB test database."""
    test_db_file = str(tmp_path / "test_marketing.duckdb")
    mgr = DatabaseManager(db_url="", fallback_path=test_db_file)
    mgr.init_schema()
    yield mgr
    mgr.close()
