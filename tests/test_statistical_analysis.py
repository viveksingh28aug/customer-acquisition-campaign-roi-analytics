"""Unit tests for the StatisticalEngine and SciPy hypothesis testing."""

import numpy as np
import pandas as pd
import pytest
from src.statistical_analysis import StatisticalEngine


def test_proportion_confidence_interval():
    ci_low, ci_high = StatisticalEngine.proportion_confidence_interval(count=50, nobs=1000, confidence=0.95)
    assert 0.035 < ci_low < 0.045
    assert 0.055 < ci_high < 0.070
    assert ci_low < 0.05 < ci_high


def test_chi_square_conversion_test():
    engine = StatisticalEngine(alpha=0.05)
    # Synthetic dataset with large difference between channels A and B
    df = pd.DataFrame({
        "channel": ["Channel_A"] * 500 + ["Channel_B"] * 500,
        "converted_flag": [1] * 50 + [0] * 450 + [1] * 10 + [0] * 490, # 10% vs 2%
    })

    result = engine.chi_square_conversion_test(df, group_col="channel", target_col="converted_flag")

    assert "chi2_statistic" in result
    assert result["is_significant"] is True
    assert result["p_value"] < 0.05
    assert result["cramers_v"] > 0.10
    assert len(result["group_breakdown"]) == 2


def test_two_sample_revenue_test():
    engine = StatisticalEngine(alpha=0.05)
    np.random.seed(42)
    # Group A mean ~100, Group B mean ~100 with noise (non-significant)
    rev_a = np.random.normal(loc=100, scale=15, size=100)
    rev_b = np.random.normal(loc=100, scale=15, size=100)

    result = engine.two_sample_revenue_test(rev_a, rev_b, "Group A", "Group B")

    assert "welch_t_stat" in result
    assert "welch_p_value" in result
    assert "mann_whitney_u" in result
    assert "cohens_d" in result
    assert result["is_significant"] is False  # identical population means
