"""Marketing Budget Reallocation and ROI Scenario Planner.

Simulates reallocation of budget from inefficient channels to high-performing
growth channels, forecasting incremental conversions, revenue, and gross profit.
"""

from typing import Any, Dict, List, Tuple
import pandas as pd
import numpy as np


class ScenarioPlanner:
    """Simulates marketing mix reallocations and projects marginal returns."""

    @staticmethod
    def simulate_budget_reallocation(
        channel_summary: pd.DataFrame,
        source_channel: str,
        target_channel: str,
        reallocation_pct: float = 0.20,
    ) -> Dict[str, Any]:
        """Simulate shifting a percentage of budget from source_channel to target_channel.

        Args:
            channel_summary: Baseline channel KPI summary DataFrame.
            source_channel: Channel to reduce spend on.
            target_channel: Channel to increase spend on.
            reallocation_pct: Fraction (0.0 to 1.0) of source budget to shift.

        Returns:
            Dictionary with baseline vs. simulated metrics and projected uplift.
        """
        df = channel_summary.copy().set_index("channel")

        if source_channel not in df.index or target_channel not in df.index:
            return {"error": "Specified channel not found in summary data."}

        src_spend = df.loc[source_channel, "total_spend"]
        shift_amount = src_spend * reallocation_pct

        src_cac = max(df.loc[source_channel, "cac"], 1.0)
        tgt_cac = max(df.loc[target_channel, "cac"], 1.0)

        src_arpu = df.loc[source_channel, "arpu"]
        tgt_arpu = df.loc[target_channel, "arpu"]

        # Diminishing returns factor for target channel scale (e.g. 5% efficiency decay on marginal spend)
        decay_factor = 0.95

        lost_customers = shift_amount / src_cac
        gained_customers = (shift_amount / tgt_cac) * decay_factor

        net_customer_delta = gained_customers - lost_customers

        lost_revenue = lost_customers * src_arpu
        gained_revenue = gained_customers * tgt_arpu
        net_revenue_delta = gained_revenue - lost_revenue

        baseline_customers = df["acquired_customers"].sum()
        baseline_revenue = df["total_net_revenue"].sum()
        baseline_spend = df["total_spend"].sum()

        projected_customers = baseline_customers + net_customer_delta
        projected_revenue = baseline_revenue + net_revenue_delta

        baseline_roas = baseline_revenue / baseline_spend if baseline_spend > 0 else 0.0
        projected_roas = projected_revenue / baseline_spend if baseline_spend > 0 else 0.0

        return {
            "source_channel": source_channel,
            "target_channel": target_channel,
            "reallocation_pct": reallocation_pct * 100.0,
            "shifted_budget": round(float(shift_amount), 2),
            "lost_customers_source": round(float(lost_customers), 0),
            "gained_customers_target": round(float(gained_customers), 0),
            "net_customer_delta": round(float(net_customer_delta), 0),
            "net_revenue_delta": round(float(net_revenue_delta), 2),
            "baseline_revenue": round(float(baseline_revenue), 2),
            "projected_revenue": round(float(projected_revenue), 2),
            "baseline_roas": round(float(baseline_roas), 2),
            "projected_roas": round(float(projected_roas), 2),
            "roas_improvement_multiple": round(float(projected_roas - baseline_roas), 2),
        }

    @staticmethod
    def generate_executive_recommendations(channel_summary: pd.DataFrame) -> List[Dict[str, str]]:
        """Generate automated strategic business recommendations based on unit economics."""
        recommendations = []

        # Find best ROAS / CAC channel
        paid_df = channel_summary[channel_summary["channel"] != "Organic Search"]
        if not paid_df.empty:
            best_roas_ch = paid_df.sort_values(by="roas", ascending=False).iloc[0]
            worst_roas_ch = paid_df.sort_values(by="roas", ascending=True).iloc[0]

            recommendations.append({
                "category": "Budget Optimization",
                "title": f"Scale {best_roas_ch['channel']} & Prune {worst_roas_ch['channel']}",
                "detail": (
                    f"{best_roas_ch['channel']} demonstrates a superior ROAS of {best_roas_ch['roas']:.2f}x "
                    f"with a CAC of ${best_roas_ch['cac']:.2f}. Conversely, {worst_roas_ch['channel']} "
                    f"has an unsustainable CAC of ${worst_roas_ch['cac']:.2f} yielding only {worst_roas_ch['roas']:.2f}x ROAS. "
                    f"Reallocating 15-25% of spend from {worst_roas_ch['channel']} will expand top-line margin immediately."
                ),
                "priority": "HIGH",
            })

            # Check LTV:CAC health
            for _, row in paid_df.iterrows():
                if row["ltv_cac_ratio"] < 1.0:
                    recommendations.append({
                        "category": "Unit Economics Warning",
                        "title": f"Critical LTV:CAC Deficit in {row['channel']}",
                        "detail": (
                            f"{row['channel']} has an LTV:CAC ratio of {row['ltv_cac_ratio']:.2f} (< 1.0x threshold). "
                            f"Each acquired customer loses money on a gross margin basis. Audit targeting, creative fatigue, and landing page drop-off."
                        ),
                        "priority": "CRITICAL",
                    })

        # Organic search efficiency
        if "Organic Search" in channel_summary["channel"].values:
            org_row = channel_summary[channel_summary["channel"] == "Organic Search"].iloc[0]
            recommendations.append({
                "category": "Organic Growth & SEO",
                "title": "Invest in High-Intent SEO Content Loops",
                "detail": (
                    f"Organic Search delivered {int(org_row['acquired_customers']):,} customers at virtually zero marginal paid cost, "
                    f"generating ${org_row['total_net_revenue']:,.2f} in net revenue. Expanding inbound content infrastructure is the most capital-efficient long-term growth lever."
                ),
                "priority": "MEDIUM",
            })

        return recommendations


scenario_planner = ScenarioPlanner()
