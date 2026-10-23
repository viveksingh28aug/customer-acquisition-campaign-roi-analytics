"""Reusable Plotly Visualizations and UI rendering helpers."""

from typing import Dict, List, Optional
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def render_metric_card_html(
    title: str,
    value: str,
    subtext: str = "",
    pill_text: str = "",
    pill_type: str = "neutral",
) -> str:
    """Generate HTML for an executive KPI metric card with badge."""
    pill_html = ""
    if pill_text:
        pill_html = f'<span class="pill-{pill_type}">{pill_text}</span>'

    return f"""
    <div class="metric-card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span class="metric-title">{title}</span>
            {pill_html}
        </div>
        <div class="metric-value">{value}</div>
        <div class="metric-sub">{subtext}</div>
    </div>
    """


def plot_bubble_cac_vs_roas(df_channel: pd.DataFrame) -> go.Figure:
    """Create Plotly bubble chart of CAC vs ROAS sized by Total Spend."""
    fig = px.scatter(
        df_channel,
        x="cac",
        y="roas",
        size="total_spend",
        color="channel",
        hover_name="channel",
        hover_data={"total_spend": ":$,.2f", "acquired_customers": ":,", "cac": ":$.2f", "roas": ":.2f"},
        text="channel",
        title="<b>Channel Efficiency Matrix: CAC vs. ROAS</b> (Bubble Size = Total Spend)",
        labels={"cac": "Customer Acquisition Cost ($)", "roas": "Return on Ad Spend (Multiple)", "total_spend": "Spend ($)"},
    )

    # Reference lines for Target ROAS and Benchmark CAC
    fig.add_hline(y=1.0, line_dash="dash", line_color="#ef4444", annotation_text="Breakeven ROAS (1.0x)", annotation_position="bottom right")
    fig.add_hline(y=3.0, line_dash="dot", line_color="#10b981", annotation_text="Target ROAS (3.0x)", annotation_position="top right")

    fig.update_traces(textposition="top center", marker=dict(opacity=0.85, line=dict(width=1.5, color="white")))
    fig.update_layout(
        template="plotly_dark",
        height=480,
        margin=dict(l=40, r=40, t=60, b=40),
        xaxis=dict(gridcolor="rgba(128,128,128,0.2)"),
        yaxis=dict(gridcolor="rgba(128,128,128,0.2)"),
    )
    return fig


def plot_funnel_sankey(df_campaigns: pd.DataFrame, df_leads: pd.DataFrame, df_orders: pd.DataFrame) -> go.Figure:
    """Build Sankey funnel diagram from Impressions to Purchases."""
    tot_imp = int(df_campaigns["impressions"].sum())
    tot_clicks = int(df_campaigns["clicks"].sum())
    tot_leads = len(df_leads)
    tot_cust = int(df_leads["customer_id"].dropna().nunique())
    tot_orders = len(df_orders)

    labels = ["1. Impressions", "2. Clicks", "3. Leads Generated", "4. Acquired Customers", "5. Total Transactions"]
    
    # Nodes: 0->1, 1->2, 2->3, 3->4
    sources = [0, 1, 2, 3]
    targets = [1, 2, 3, 4]
    values = [tot_clicks, tot_leads, tot_cust, tot_orders]

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=18,
            thickness=22,
            line=dict(color="black", width=0.5),
            label=[f"{lbl} ({val:,})" for lbl, val in zip(labels, [tot_imp, tot_clicks, tot_leads, tot_cust, tot_orders])],
            color=["#3b82f6", "#06b6d4", "#10b981", "#8b5cf6", "#f59e0b"],
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=["rgba(59, 130, 246, 0.4)", "rgba(6, 182, 212, 0.4)", "rgba(16, 185, 129, 0.4)", "rgba(139, 92, 246, 0.4)"]
        )
    )])

    fig.update_layout(
        title="<b>Full-Funnel Customer Acquisition Flow</b>",
        font=dict(size=12, color="white"),
        template="plotly_dark",
        height=400,
        margin=dict(l=20, r=20, t=50, b=20),
    )
    return fig


def plot_waterfall_financials(totals: Dict[str, float]) -> go.Figure:
    """Plotly financial waterfall showing Spend, Net Revenue, COGS, and Net Profit."""
    spend = totals["total_spend"]
    rev = totals["total_net_revenue"]
    profit = totals["total_gross_profit"]
    cogs = rev - profit
    net_marketing_profit = profit - spend

    fig = go.Figure(go.Waterfall(
        name="Unit Economics",
        orientation="v",
        measure=["relative", "relative", "relative", "total"],
        x=["Marketing Spend", "Attributed Revenue", "COGS Offset", "Net Campaign Profit"],
        textposition="outside",
        text=[f"-${spend:,.0f}", f"+${rev:,.0f}", f"-${cogs:,.0f}", f"${net_marketing_profit:,.0f}"],
        y=[-spend, rev, -cogs, net_marketing_profit],
        connector={"line": {"color": "rgba(255,255,255,0.4)"}},
        decreasing={"marker": {"color": "#ef4444"}},
        increasing={"marker": {"color": "#10b981"}},
        totals={"marker": {"color": "#3b82f6"}},
    ))

    fig.update_layout(
        title="<b>Campaign Financial Flow & Profit Realization ($)</b>",
        template="plotly_dark",
        height=380,
        margin=dict(l=40, r=40, t=60, b=40),
        yaxis=dict(gridcolor="rgba(128,128,128,0.2)"),
    )
    return fig


def plot_rolling_trends(df_rolling: pd.DataFrame, channel: str) -> go.Figure:
    """Time-series chart showing 7-day rolling spend, acquisitions, and revenue."""
    sub = df_rolling[df_rolling["channel"] == channel].copy()
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=sub["date"],
        y=sub["rolling_7d_spend"],
        name="7d Avg Spend ($)",
        line=dict(color="#f59e0b", width=2.5),
    ))

    fig.add_trace(go.Scatter(
        x=sub["date"],
        y=sub["rolling_7d_revenue"],
        name="7d Avg Revenue ($)",
        line=dict(color="#10b981", width=2.5),
    ))

    fig.add_trace(go.Scatter(
        x=sub["date"],
        y=sub["rolling_7d_acquisitions"],
        name="7d Avg Customers",
        yaxis="y2",
        line=dict(color="#3b82f6", width=2, dash="dot"),
    ))

    fig.update_layout(
        title=f"<b>Rolling 7-Day Performance Trends: {channel}</b>",
        template="plotly_dark",
        height=400,
        margin=dict(l=40, r=40, t=60, b=40),
        xaxis=dict(gridcolor="rgba(128,128,128,0.2)"),
        yaxis=dict(title="Spend & Revenue ($)", gridcolor="rgba(128,128,128,0.2)"),
        yaxis2=dict(title="New Customers", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def plot_confidence_intervals(breakdown: List[Dict[str, Any]]) -> go.Figure:
    """Forest plot displaying conversion rate point estimates with 95% Wilson Score CIs."""
    df = pd.DataFrame(breakdown)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["conversion_rate_pct"],
        y=df["group"],
        mode="markers",
        error_x=dict(
            type="data",
            symmetric=False,
            array=df["ci_upper_pct"] - df["conversion_rate_pct"],
            arrayminus=df["conversion_rate_pct"] - df["ci_lower_pct"],
            color="#38bdf8",
            thickness=2,
            width=6,
        ),
        marker=dict(color="#0284c7", size=10),
        name="Conversion Rate (95% CI)",
    ))

    fig.update_layout(
        title="<b>Channel Conversion Rates with 95% Confidence Intervals</b>",
        xaxis_title="Conversion Rate (%)",
        yaxis_title="Acquisition Channel",
        template="plotly_dark",
        height=360,
        margin=dict(l=40, r=40, t=60, b=40),
        xaxis=dict(gridcolor="rgba(128,128,128,0.2)"),
        yaxis=dict(gridcolor="rgba(128,128,128,0.2)"),
    )
    return fig


def plot_cohort_cumulative_ltv(df_cohort: pd.DataFrame) -> go.Figure:
    """Plot cumulative LTV curves by cohort month."""
    fig = px.line(
        df_cohort,
        x="month_number",
        y="cumulative_ltv_per_customer",
        color="cohort_month",
        markers=True,
        title="<b>Cohort Cumulative LTV Progression by Acquisition Cohort</b>",
        labels={"month_number": "Months Since Acquisition", "cumulative_ltv_per_customer": "Cumulative LTV ($)"},
    )

    fig.update_layout(
        template="plotly_dark",
        height=400,
        margin=dict(l=40, r=40, t=60, b=40),
        xaxis=dict(gridcolor="rgba(128,128,128,0.2)", dtick=1),
        yaxis=dict(gridcolor="rgba(128,128,128,0.2)"),
    )
    return fig
