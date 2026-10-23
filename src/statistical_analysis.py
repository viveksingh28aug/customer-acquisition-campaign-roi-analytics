"""Statistical Analysis Engine using SciPy.

Performs rigorous hypothesis testing, effect size calculations,
and distribution diagnostics for marketing acquisition and campaign ROI:
- Chi-Square Test of Independence for Conversion Rates (with Cramér's V)
- Two-Sample Welch's t-test and Mann-Whitney U test for Monetization/ARPU
- Confidence Intervals for Proportions and Means
- One-Way ANOVA and Kruskal-Wallis across Multi-Channel touchpoints
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats

from src.logger import logger


class StatisticalEngine:
    """Scientific experimentation and hypothesis testing engine."""

    def __init__(self, alpha: float = 0.05):
        self.alpha = alpha

    def chi_square_conversion_test(
        self,
        df_leads: pd.DataFrame,
        group_col: str = "channel",
        target_col: str = "converted_flag",
    ) -> Dict[str, Any]:
        """Perform Chi-Square Test of Independence on conversion rates across groups.

        H0: Conversion rate is independent of group (e.g. channel or campaign).
        Ha: Conversion rate varies significantly by group.

        Returns:
            Dictionary containing test statistic, p_value, cramers_v, and business interpretation.
        """
        # Build 2xK contingency table: [converted, non_converted] per group
        ct = pd.crosstab(df_leads[group_col], df_leads[target_col])
        if ct.shape[0] < 2 or ct.shape[1] < 2:
            return {"error": "Insufficient groups or target classes for Chi-square test."}

        chi2, p_val, dof, expected = stats.chi2_contingency(ct)

        # Cramér's V effect size calculation
        n = ct.to_numpy().sum()
        min_dim = min(ct.shape) - 1
        cramers_v = np.sqrt(chi2 / (n * min_dim)) if n * min_dim > 0 else 0.0

        is_significant = p_val < self.alpha

        # Plain-English business conclusion
        if is_significant:
            conclusion = (
                f"Statistically significant difference detected across {group_col}s "
                f"(chi2={chi2:.2f}, p={p_val:.4e} < {self.alpha}). "
                f"Effect size (Cramer's V) is {cramers_v:.3f}. "
                f"Channel choice demonstrably impacts customer acquisition probability."
            )
        else:
            conclusion = (
                f"No statistically significant difference in conversion rates across {group_col}s "
                f"(chi2={chi2:.2f}, p={p_val:.4f} >= {self.alpha}). "
                f"Observed variations are likely attributable to random sampling noise."
            )

        # Compute per-group conversion rates and 95% Wilson score intervals
        group_stats = []
        for grp in ct.index:
            conv = ct.loc[grp, 1] if 1 in ct.columns else 0
            total = ct.loc[grp].sum()
            rate = (conv / total) if total > 0 else 0.0
            ci_low, ci_high = self.proportion_confidence_interval(conv, total)
            group_stats.append({
                "group": grp,
                "conversions": int(conv),
                "total": int(total),
                "conversion_rate_pct": round(rate * 100.0, 2),
                "ci_lower_pct": round(ci_low * 100.0, 2),
                "ci_upper_pct": round(ci_high * 100.0, 2),
            })

        return {
            "test_name": "Chi-Square Test of Independence",
            "group_variable": group_col,
            "target_variable": target_col,
            "chi2_statistic": round(float(chi2), 3),
            "p_value": float(p_val),
            "degrees_of_freedom": int(dof),
            "cramers_v": round(float(cramers_v), 4),
            "is_significant": bool(is_significant),
            "conclusion": conclusion,
            "contingency_table": ct.to_dict(),
            "group_breakdown": group_stats,
        }

    def two_sample_revenue_test(
        self,
        group_a_values: np.ndarray,
        group_b_values: np.ndarray,
        label_a: str = "Group A",
        label_b: str = "Group B",
    ) -> Dict[str, Any]:
        """Perform Welch's t-test and Mann-Whitney U test on revenue/order values.

        Returns:
            Dictionary with parametric and non-parametric stats, Cohen's d, and 95% CI.
        """
        a = np.asarray(group_a_values, dtype=float)
        b = np.asarray(group_b_values, dtype=float)

        a = a[~np.isnan(a)]
        b = b[~np.isnan(b)]

        if len(a) < 5 or len(b) < 5:
            return {"error": "Each group must have at least 5 observations for comparison."}

        # Normality and Variance diagnostics
        shapiro_a_p = stats.shapiro(a[:1000]).pvalue if len(a) >= 3 else 1.0
        shapiro_b_p = stats.shapiro(b[:1000]).pvalue if len(b) >= 3 else 1.0
        levene_p = stats.levene(a, b).pvalue

        # Welch's t-test (robust to unequal variances)
        t_stat, t_pval = stats.ttest_ind(a, b, equal_var=False)

        # Mann-Whitney U test (non-parametric fallback for skewed distributions)
        u_stat, u_pval = stats.mannwhitneyu(a, b, alternative="two-sided")

        # Descriptive stats
        mean_a, std_a = np.mean(a), np.std(a, ddof=1)
        mean_b, std_b = np.mean(b), np.std(b, ddof=1)
        diff_mean = mean_a - mean_b

        # Cohen's d effect size (pooled SD)
        pooled_sd = np.sqrt(((len(a) - 1) * std_a**2 + (len(b) - 1) * std_b**2) / (len(a) + len(b) - 2))
        cohens_d = (diff_mean / pooled_sd) if pooled_sd > 0 else 0.0

        # 95% Confidence Interval for difference in means (Welch-Satterthwaite df)
        se_diff = np.sqrt((std_a**2 / len(a)) + (std_b**2 / len(b)))
        df_welch = ((std_a**2 / len(a) + std_b**2 / len(b))**2) / (
            (std_a**2 / len(a))**2 / (len(a) - 1) + (std_b**2 / len(b))**2 / (len(b) - 1)
        )
        t_crit = stats.t.ppf(1 - self.alpha / 2, df=df_welch)
        ci_lower = diff_mean - t_crit * se_diff
        ci_upper = diff_mean + t_crit * se_diff

        is_significant = t_pval < self.alpha

        interpretation = (
            f"Welch's t-test: t={t_stat:.2f}, p={t_pval:.4f}. "
            f"{label_a} Mean = ${mean_a:.2f} vs {label_b} Mean = ${mean_b:.2f} "
            f"(Delta = ${diff_mean:.2f}, 95% CI: [${ci_lower:.2f}, ${ci_upper:.2f}], Cohen's d={cohens_d:.2f}). "
            + ("Difference is statistically significant." if is_significant else "Difference is NOT statistically significant.")
        )

        return {
            "label_a": label_a,
            "label_b": label_b,
            "sample_size_a": len(a),
            "sample_size_b": len(b),
            "mean_a": round(float(mean_a), 2),
            "mean_b": round(float(mean_b), 2),
            "diff_mean": round(float(diff_mean), 2),
            "welch_t_stat": round(float(t_stat), 3),
            "welch_p_value": float(t_pval),
            "mann_whitney_u": float(u_stat),
            "mann_whitney_p_value": float(u_pval),
            "cohens_d": round(float(cohens_d), 3),
            "ci_95_lower": round(float(ci_lower), 2),
            "ci_95_upper": round(float(ci_upper), 2),
            "is_significant": bool(is_significant),
            "interpretation": interpretation,
        }

    def anova_channels_test(
        self,
        df_orders: pd.DataFrame,
        df_leads: pd.DataFrame,
        metric_col: str = "net_revenue",
    ) -> Dict[str, Any]:
        """Perform One-Way ANOVA and Kruskal-Wallis across all marketing channels."""
        cust_ch = df_leads.dropna(subset=["customer_id"])[["customer_id", "channel"]].drop_duplicates("customer_id")
        merged = df_orders.merge(cust_ch, on="customer_id")

        channels = merged["channel"].unique()
        groups = [merged[merged["channel"] == ch][metric_col].dropna().values for ch in channels if len(merged[merged["channel"] == ch]) >= 5]

        if len(groups) < 2:
            return {"error": "Need at least 2 channels with sufficient observations."}

        f_stat, f_pval = stats.f_oneway(*groups)
        kw_stat, kw_pval = stats.kruskal(*groups)

        return {
            "test_name": "One-Way ANOVA & Kruskal-Wallis",
            "metric": metric_col,
            "num_channels": len(groups),
            "f_statistic": round(float(f_stat), 3),
            "f_p_value": float(f_pval),
            "kruskal_statistic": round(float(kw_stat), 3),
            "kruskal_p_value": float(kw_pval),
            "is_significant": bool(f_pval < self.alpha),
        }

    @staticmethod
    def proportion_confidence_interval(count: int, nobs: int, confidence: float = 0.95) -> Tuple[float, float]:
        """Wilson score interval for binomial proportions."""
        if nobs == 0:
            return 0.0, 0.0
        z = stats.norm.ppf(1 - (1 - confidence) / 2)
        p = count / nobs
        denominator = 1 + z**2 / nobs
        centre_adjusted_probability = p + z**2 / (2 * nobs)
        adjusted_standard_deviation = np.sqrt((p * (1 - p) + z**2 / (4 * nobs)) / nobs)

        lower_bound = (centre_adjusted_probability - z * adjusted_standard_deviation) / denominator
        upper_bound = (centre_adjusted_probability + z * adjusted_standard_deviation) / denominator
        return max(0.0, lower_bound), min(1.0, upper_bound)


stat_engine = StatisticalEngine()
