"""Unit and integration tests for DatabaseManager and SQL execution."""

import pandas as pd
from src.database import DatabaseManager


def test_database_init_and_query(memory_db_manager, sample_campaigns_raw, sample_leads_raw, sample_orders_raw):
    from src.data_cleaner import DataCleaner
    cleaner = DataCleaner()
    df_c = cleaner.clean_campaign_spend(sample_campaigns_raw)
    df_l = cleaner.clean_customer_leads(sample_leads_raw)
    df_o = cleaner.clean_customer_orders(sample_orders_raw)

    # Ingest data
    memory_db_manager.load_clean_data(df_c, df_l, df_o)

    # Test basic select query
    res = memory_db_manager.execute_query("SELECT COUNT(*) AS cnt FROM campaign_spend;")
    assert res.iloc[0]["cnt"] == len(df_c)

    # Test named query execution with CTEs
    q1_res = memory_db_manager.run_named_query("channel_performance_kpis")
    assert not q1_res.empty
    assert "channel" in q1_res.columns
    assert "total_spend" in q1_res.columns
    assert "cac" in q1_res.columns
    assert "roas_multiple" in q1_res.columns
