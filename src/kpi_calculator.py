"""Business KPI Calculation Engine.

Calculates enterprise marketing acquisition unit economics:
- CTR, CPC, Conversion Rate (CVR)
- Customer Acquisition Cost (CAC)
- Average Revenue Per User (ARPU)
- Customer Lifetime Value (LTV) and LTV:CAC Ratio
- Return on Ad Spend (ROAS) and Net Campaign ROI
- Payback Period (Months)
- Blended vs Paid-Only Channel Performance
"""

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from src.config import config
from src.logger import logger


class KPICalculator:
    """Core marketing unit economics and performance KPI calculator."""

    def __init__(self, cogs_rate: Optional[float] = None):
        # Explicitly document assumptions (Requirement 5)
        self.cogs_rate = cogs_rate or config.assumptions.get("cogs_percentage", 0.35)
        self.assumptions_doc = config.assumptions

    @staticmethod
    def calculate_ctr(clicks: float, impressions: float) -> float:
        """Click-Through Rate (%) = (Clicks / Impressions) * 100."""
        if impressions <= 0:
            return 0.0
        return round(float((clicks / impressions) * 100.0), 2)

    @staticmethod
    def calculate_cpc(spend: float, clicks: float) -> float:
        """Cost Per Click ($) = Total Spend / Total Clicks."""
        if clicks <= 0:
            return 0.0
        return round(float(spend / clicks), 2)

    @staticmethod
    def calculate_conversion_rate(conversions: float, total_opportunities: float) -> float:
        """Conversion Rate (%) = (Conversions / Opportunities) * 100."""
        if total_opportunities <= 0:
            return 0.0
        return round(float((conversions / total_opportunities) * 100.0), 2)

    @staticmethod
    def calculate_cac(spend: float, customers: float) -> float:
        """Customer Acquisition Cost ($) = Total Marketing Spend / Acquired Customers."""
        if customers <= 0:
            return 0.0
        return round(float(spend / customers), 2)

    @staticmethod
    def calculate_arpu(net_revenue: float, customers: float) -> float:
        """Average Revenue Per User/Customer ($) = Net Revenue / Total Acquired Customers."""
        if customers <= 0:
            return 0.0
        return round(float(net_revenue / customers), 2)

    @staticmethod
    def calculate_roas(net_revenue: float, spend: float) -> float:
        """Return on Ad Spend (Multiple) = Attributed Net Revenue / Marketing Spend."""
        if spend <= 0:
            return 0.0
        return round(float(net_revenue / spend), 2)

    @staticmethod
    def calculate_net_roi(gross_profit: float, spend: float) -> float:
        """Campaign Net ROI (%) = ((Gross Profit - Marketing Spend) / Marketing Spend) * 100."""
        if spend <= 0:
            return 0.0
        return round(float(((gross_profit - spend) / spend) * 100.0), 2)

    @staticmethod
    def calculate_ltv_cac_ratio(ltv: float, cac: float) -> float:
        """LTV to CAC Ratio = LTV / CAC. Benchmark healthy target is >= 3.0.
        
        Numerator: Cumulative LTV or ARPU ($).
        Denominator: Customer Acquisition Cost ($).
        """
        if cac <= 0:
            return 0.0
        return round(float(ltv / cac), 2)

    @staticmethod
    def calculate_payback_months(cac: float, monthly_margin_per_customer: float) -> Optional[float]:
        """Payback Period (Months) = CAC / Monthly Gross Margin per Customer.
        
        Numerator: CAC ($).
        Denominator: Monthly gross margin realized per customer ($).
        Attribution & Assumption:
            Assumes steady-state margin realization across the observation horizon.
        Returns:
            Float representing recovery duration in months, or None if margin <= 0 (unrecoverable).
        """
        if monthly_margin_per_customer <= 0:
            return None  # Unrecoverable when margin is zero or negative
        if cac <= 0:
            return 0.0
        return round(float(cac / monthly_margin_per_customer), 1)

    def calculate_channel_summary(
        self,
        df_campaigns: pd.DataFrame,
        df_leads: pd.DataFrame,
        df_orders: pd.DataFrame,
    ) -> pd.DataFrame:
        """Compute comprehensive KPI performance table by marketing channel.

        Attribution Rule:
            First-touch lead attribution: Customer transactions are joined via customer_id
            to the initial channel that captured the qualified lead.

        Financial Formulas & Attribution:
            - CTR: (total_clicks / total_impressions) * 100
            - CPC: total_spend / total_clicks
            - Lead-to-Customer CVR: (acquired_customers / total_leads) * 100
            - CAC: total_spend / acquired_customers
            - ARPU: total_net_revenue / acquired_customers
            - ROAS: total_net_revenue / total_spend
            - Net Campaign ROI: ((total_gross_profit - total_spend) / total_spend) * 100
            - LTV:CAC Ratio: ARPU / CAC
            - Payback Months: CAC / (total_gross_profit / customers / 4.0)

        Cost Assumptions:
            - COGS is standardized at 35% of GMV.
            - Organic Search includes $50/day baseline inbound maintenance spend.
            - Paid channels strictly isolate direct media ad spend.
        """
        if df_campaigns.empty or df_leads.empty:
            empty_cols = [
                "channel", "total_spend", "total_impressions", "total_clicks", "ctr_pct", "cpc",
                "total_leads", "acquired_customers", "avg_lead_score", "cvr_pct", "total_orders",
                "total_net_revenue", "total_gross_profit", "cac", "arpu", "roas", "net_roi_pct",
                "ltv_cac_ratio", "est_monthly_margin", "payback_months"
            ]
            return pd.DataFrame(columns=empty_cols)

        # 1. Channel Spend Aggregates
        c_agg = df_campaigns.groupby("channel", as_index=False).agg(
            total_spend=("ad_spend", "sum"),
            total_impressions=("impressions", "sum"),
            total_clicks=("clicks", "sum"),
        )
        c_agg["ctr_pct"] = c_agg.apply(lambda r: self.calculate_ctr(r["total_clicks"], r["total_impressions"]), axis=1)
        c_agg["cpc"] = c_agg.apply(lambda r: self.calculate_cpc(r["total_spend"], r["total_clicks"]), axis=1)

        # 2. Leads & Conversion Aggregates
        l_agg = df_leads.groupby("channel", as_index=False).agg(
            total_leads=("lead_id", "count"),
            acquired_customers=("customer_id", lambda s: s.dropna().nunique()),
            avg_lead_score=("lead_score", "mean"),
        )
        l_agg["cvr_pct"] = l_agg.apply(lambda r: self.calculate_conversion_rate(r["acquired_customers"], r["total_leads"]), axis=1)

        # 3. Revenue & Gross Profit Aggregates
        cust_channel_map = df_leads.dropna(subset=["customer_id"])[["customer_id", "channel"]].drop_duplicates("customer_id")
        orders_with_channel = df_orders.merge(cust_channel_map, on="customer_id", how="inner") if not df_orders.empty else pd.DataFrame(columns=["channel", "order_id", "net_revenue", "gross_profit"])

        if not orders_with_channel.empty:
            r_agg = orders_with_channel.groupby("channel", as_index=False).agg(
                total_orders=("order_id", "count"),
                total_net_revenue=("net_revenue", "sum"),
                total_gross_profit=("gross_profit", "sum"),
            )
        else:
            r_agg = pd.DataFrame(columns=["channel", "total_orders", "total_net_revenue", "total_gross_profit"])

        # Merge all aggregates
        summary = c_agg.merge(l_agg, on="channel", how="left").merge(r_agg, on="channel", how="left").fillna(0)

        # Compute derived unit economics
        summary["cac"] = summary.apply(lambda r: self.calculate_cac(r["total_spend"], r["acquired_customers"]), axis=1)
        summary["arpu"] = summary.apply(lambda r: self.calculate_arpu(r["total_net_revenue"], r["acquired_customers"]), axis=1)
        summary["roas"] = summary.apply(lambda r: self.calculate_roas(r["total_net_revenue"], r["total_spend"]), axis=1)
        summary["net_roi_pct"] = summary.apply(lambda r: self.calculate_net_roi(r["total_gross_profit"], r["total_spend"]), axis=1)
        summary["ltv_cac_ratio"] = summary.apply(lambda r: self.calculate_ltv_cac_ratio(r["arpu"], r["cac"]), axis=1)

        # Estimated monthly margin per customer over observation horizon (approx 4 months)
        def calc_margin(row):
            custs = row["acquired_customers"]
            if custs <= 0:
                return 0.0
            return round(float(row["total_gross_profit"] / custs / 4.0), 2)

        summary["est_monthly_margin"] = summary.apply(calc_margin, axis=1)
        summary["payback_months"] = summary.apply(lambda r: self.calculate_payback_months(r["cac"], r["est_monthly_margin"]), axis=1)

        return summary.sort_values(by="total_spend", ascending=False).reset_index(drop=True)

    def calculate_executive_totals(self, channel_summary: pd.DataFrame) -> Dict[str, Any]:
        """Compute high-level executive scorecard totals (Blended and Paid-Only)."""
        if channel_summary.empty:
            return {
                "total_spend": 0.0,
                "total_customers": 0,
                "total_leads": 0,
                "total_net_revenue": 0.0,
                "total_gross_profit": 0.0,
                "blended_cac": 0.0,
                "blended_cvr_pct": 0.0,
                "blended_roas": 0.0,
                "blended_roi_pct": 0.0,
                "blended_arpu": 0.0,
                "paid_spend": 0.0,
                "paid_customers": 0,
                "paid_cac": 0.0,
                "paid_roas": 0.0,
                "paid_roi_pct": 0.0,
            }

        tot_spend = float(channel_summary["total_spend"].sum())
        tot_customers = int(channel_summary["acquired_customers"].sum())
        tot_leads = int(channel_summary["total_leads"].sum())
        tot_revenue = float(channel_summary["total_net_revenue"].sum())
        tot_profit = float(channel_summary["total_gross_profit"].sum())

        blended_cac = self.calculate_cac(tot_spend, tot_customers)
        blended_cvr = self.calculate_conversion_rate(tot_customers, tot_leads)
        blended_roas = self.calculate_roas(tot_revenue, tot_spend)
        blended_roi = self.calculate_net_roi(tot_profit, tot_spend)
        blended_arpu = self.calculate_arpu(tot_revenue, tot_customers)

        # Paid channels only (excluding Organic Search)
        paid_summary = channel_summary[channel_summary["channel"] != "Organic Search"]
        paid_spend = float(paid_summary["total_spend"].sum())
        paid_customers = int(paid_summary["acquired_customers"].sum())
        paid_revenue = float(paid_summary["total_net_revenue"].sum())
        paid_profit = float(paid_summary["total_gross_profit"].sum())

        paid_cac = self.calculate_cac(paid_spend, paid_customers)
        paid_roas = self.calculate_roas(paid_revenue, paid_spend)
        paid_roi = self.calculate_net_roi(paid_profit, paid_spend)

        return {
            "total_spend": tot_spend,
            "total_customers": tot_customers,
            "total_leads": tot_leads,
            "total_net_revenue": tot_revenue,
            "total_gross_profit": tot_profit,
            "blended_cac": blended_cac,
            "blended_cvr_pct": blended_cvr,
            "blended_roas": blended_roas,
            "blended_roi_pct": blended_roi,
            "blended_arpu": blended_arpu,
            "paid_spend": paid_spend,
            "paid_customers": paid_customers,
            "paid_cac": paid_cac,
            "paid_roas": paid_roas,
            "paid_roi_pct": paid_roi,
        }


kpi_calc = KPICalculator()
