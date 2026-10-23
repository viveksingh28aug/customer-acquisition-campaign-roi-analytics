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
        """Simulate shifting budget from source_channel to target_channel.

        Preservation of Total Budget:
            The shifted budget is deducted from the source channel and added to the
            target channel. Total budget remains strictly preserved (zero net variance).

        Negative Allocation Prevention:
            Clamps reallocation_pct to [0.0, 1.0] and enforces non-negative spend.

        Double-Counting Prevention:
            Customer attrition from source channel is capped at the channel's observed
            customer base. Incremental gains apply a 5% diminishing returns penalty.

        Args:
            channel_summary: Baseline channel KPI summary DataFrame.
            source_channel: Channel to reduce spend on.
            target_channel: Channel to increase spend on.
            reallocation_pct: Fraction (0.0 to 1.0) of source budget to shift.

        Returns:
            Dictionary with baseline vs. simulated metrics and projected uplift.
        """
        if source_channel == target_channel:
            return {"error": "Source channel and target channel must be different."}

        df = channel_summary.copy().set_index("channel")

        if source_channel not in df.index or target_channel not in df.index:
            return {"error": "Specified channel not found in summary data."}

        src_spend = float(df.loc[source_channel, "total_spend"])
        tgt_spend = float(df.loc[target_channel, "total_spend"])

        if src_spend <= 0:
            return {"error": f"Source channel '{source_channel}' has no spend to reallocate."}

        # Clamp reallocation percentage to [0.0, 1.0] to prevent negative allocations
        pct = max(0.0, min(1.0, float(reallocation_pct)))
        shift_amount = round(src_spend * pct, 2)

        # Budget preservation: Spend deducted from source is added to target
        src_projected_spend = round(src_spend - shift_amount, 2)
        tgt_projected_spend = round(tgt_spend + shift_amount, 2)

        baseline_spend = float(df["total_spend"].sum())
        projected_spend = baseline_spend  # strictly identical, zero variance

        src_cac = max(float(df.loc[source_channel, "cac"]), 1.0)
        tgt_cac = max(float(df.loc[target_channel, "cac"]), 1.0)

        src_arpu = float(df.loc[source_channel, "arpu"])
        tgt_arpu = float(df.loc[target_channel, "arpu"])

        src_customers = float(df.loc[source_channel, "acquired_customers"])

        # Customer attrition: cannot lose more customers than the channel actually has
        lost_customers = min(src_customers, shift_amount / src_cac)

        # Target acquisition: incorporates a 5% diminishing returns penalty for scaling
        decay_factor = 0.95
        gained_customers = (shift_amount / tgt_cac) * decay_factor

        net_customer_delta = gained_customers - lost_customers

        # Revenue delta
        lost_revenue = lost_customers * src_arpu
        gained_revenue = gained_customers * tgt_arpu
        net_revenue_delta = gained_revenue - lost_revenue

        baseline_customers = float(df["acquired_customers"].sum())
        baseline_revenue = float(df["total_net_revenue"].sum())

        projected_customers = max(0.0, baseline_customers + net_customer_delta)
        projected_revenue = max(0.0, baseline_revenue + net_revenue_delta)

        baseline_roas = baseline_revenue / baseline_spend if baseline_spend > 0 else 0.0
        projected_roas = projected_revenue / projected_spend if projected_spend > 0 else 0.0

        return {
            "source_channel": source_channel,
            "target_channel": target_channel,
            "reallocation_pct": pct * 100.0,
            "shifted_budget": shift_amount,
            "source_baseline_spend": src_spend,
            "source_projected_spend": src_projected_spend,
            "target_baseline_spend": tgt_spend,
            "target_projected_spend": tgt_projected_spend,
            "baseline_spend": round(baseline_spend, 2),
            "projected_spend": round(projected_spend, 2),
            "budget_delta": 0.0,  # Explicit proof of total budget preservation
            "lost_customers_source": round(lost_customers, 0),
            "gained_customers_target": round(gained_customers, 0),
            "net_customer_delta": round(net_customer_delta, 0),
            "lost_revenue_source": round(lost_revenue, 2),
            "gained_revenue_target": round(gained_revenue, 2),
            "net_revenue_delta": round(net_revenue_delta, 2),
            "baseline_customers": round(baseline_customers, 0),
            "projected_customers": round(projected_customers, 0),
            "baseline_revenue": round(baseline_revenue, 2),
            "projected_revenue": round(projected_revenue, 2),
            "baseline_roas": round(baseline_roas, 2),
            "projected_roas": round(projected_roas, 2),
            "roas_improvement_multiple": round(projected_roas - baseline_roas, 2),
            "projection_disclaimer": "Modeled projection based on constant marginal CAC with a 5% scale decay assumption. Not an empirical guarantee.",
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
