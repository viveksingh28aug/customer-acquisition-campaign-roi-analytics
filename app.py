"""Customer Acquisition & Campaign ROI Analytics Dashboard.

Senior Portfolio Data Science & Analytics Interactive Web Application.
"""

from datetime import datetime
from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np

from src.config import config
from src.database import db_manager
from src.kpi_calculator import kpi_calc
from src.statistical_analysis import stat_engine
from src.scenario_planner import scenario_planner
from ui.styles import CUSTOM_CSS
from ui.components import (
    render_metric_card_html,
    plot_bubble_cac_vs_roas,
    plot_funnel_sankey,
    plot_waterfall_financials,
    plot_rolling_trends,
    plot_confidence_intervals,
    plot_cohort_cumulative_ltv,
)

# Page configuration
st.set_page_config(
    page_title="Customer Acquisition & Campaign ROI Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject custom styles
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


@st.cache_data(ttl=600)
def load_and_filter_data(
    start_date: str,
    end_date: str,
    selected_channels: list,
    selected_platforms: list,
):
    """Load and apply global filters to cleaned datasets."""
    p_camp = Path("data/processed/campaign_spend_clean.csv")
    p_leads = Path("data/processed/customer_leads_clean.csv")
    p_orders = Path("data/processed/customer_orders_clean.csv")

    if not (p_camp.exists() and p_leads.exists() and p_orders.exists()):
        st.error("Processed data files not found. Initializing pipeline...")
        from src.data_loader import generate_benchmark_raw_datasets
        from src.data_cleaner import DataCleaner
        generate_benchmark_raw_datasets()
        cleaner = DataCleaner()
        cleaner.run_pipeline()

    df_camp = pd.read_csv(p_camp)
    df_leads = pd.read_csv(p_leads)
    df_orders = pd.read_csv(p_orders)

    # Parse dates
    df_camp["date"] = pd.to_datetime(df_camp["date"])
    df_leads["lead_date"] = pd.to_datetime(df_leads["lead_date"])
    df_leads["conversion_date"] = pd.to_datetime(df_leads["conversion_date"])
    df_orders["order_date"] = pd.to_datetime(df_orders["order_date"])

    # Filter campaigns
    s_dt = pd.to_datetime(start_date)
    e_dt = pd.to_datetime(end_date)

    camp_filtered = df_camp[
        (df_camp["date"] >= s_dt) &
        (df_camp["date"] <= e_dt) &
        (df_camp["channel"].isin(selected_channels))
    ].copy()

    # Filter leads
    leads_filtered = df_leads[
        (df_leads["lead_date"] >= s_dt) &
        (df_leads["lead_date"] <= e_dt) &
        (df_leads["channel"].isin(selected_channels)) &
        (df_leads["signup_platform"].isin(selected_platforms))
    ].copy()

    # Filter orders matching leads/customers
    valid_custs = set(leads_filtered["customer_id"].dropna().unique())
    orders_filtered = df_orders[
        (df_orders["customer_id"].isin(valid_custs)) &
        (df_orders["order_date"] >= s_dt)
    ].copy()

    return camp_filtered, leads_filtered, orders_filtered


# --- SIDEBAR CONTROLS ---
st.sidebar.markdown("### ⚙️ Global Filter Engine")

# Date range
min_dt = datetime(2026, 1, 1)
max_dt = datetime(2026, 4, 30)
date_range = st.sidebar.date_input(
    "Date Window",
    value=(min_dt, max_dt),
    min_value=min_dt,
    max_value=max_dt,
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_filter, end_filter = date_range[0], date_range[1]
else:
    start_filter, end_filter = min_dt, max_dt

all_channels = ["Google Search", "Meta Ads", "LinkedIn Ads", "YouTube Ads", "Email Marketing", "Organic Search"]
selected_channels = st.sidebar.multiselect(
    "Acquisition Channels",
    options=all_channels,
    default=all_channels,
)

all_platforms = ["Web", "iOS", "Android"]
selected_platforms = st.sidebar.multiselect(
    "Signup Platforms",
    options=all_platforms,
    default=all_platforms,
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🗄️ Database Engine Status")
db_badge_color = "#10b981" if db_manager.engine_type == "postgresql" else "#38bdf8"
st.sidebar.markdown(
    f"<span style='color: {db_badge_color}; font-weight: 600;'>Active Engine: {db_manager.engine_type.upper()}</span>",
    unsafe_allow_html=True,
)
if db_manager.engine_type != "postgresql":
    st.sidebar.caption("Connected to local embedded DuckDB fallback (PostgreSQL server offline or not configured). ANSI SQL queries are 100% operational.")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🏷️ Portfolio Project")
st.sidebar.caption("Designed for Senior Data Scientist & Analytics Portfolio Review.")

# Load filtered data
if not selected_channels or not selected_platforms:
    st.warning("Please select at least one channel and platform in the sidebar.")
    st.stop()

df_camp, df_leads, df_orders = load_and_filter_data(
    start_filter.strftime("%Y-%m-%d"),
    end_filter.strftime("%Y-%m-%d"),
    selected_channels,
    selected_platforms,
)

# Compute Core Metrics
channel_summary = kpi_calc.calculate_channel_summary(df_camp, df_leads, df_orders)
exec_totals = kpi_calc.calculate_executive_totals(channel_summary)

# --- HEADER & BANNER ---
st.title("📈 Customer Acquisition & Campaign ROI Analytics")
st.markdown(
    "**End-to-End Marketing Unit Economics, Attribution, & Statistical Decision Engine**"
)

# Documented Cost Assumptions Disclaimer (Requirement 5)
st.markdown(
    f"""
    <div class="disclaimer-box">
        <strong>📌 Data Governance & Cost Simulation Disclosure:</strong> {config.assumptions.get('disclaimer')}
        <br>• Baseline COGS parameter: <strong>{config.assumptions.get('cogs_percentage') * 100:.0f}% of Gross Merchandise Value</strong>.
        • Primary observations: Ad spend, impressions, clicks, lead conversions, and transaction logs.
    </div>
    """,
    unsafe_allow_html=True,
)

# --- TABS NAVIGATION ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Executive Overview",
    "🎯 Channel & Campaign Drilldown",
    "👥 Cohort & LTV Progression",
    "🔬 Statistical Hypothesis Studio",
    "💡 Scenario Planner & Recommendations",
])

# ==============================================================================
# TAB 1: EXECUTIVE OVERVIEW
# ==============================================================================
with tab1:
    st.markdown("### Executive Scorecard")
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    with c1:
        st.markdown(
            render_metric_card_html(
                "Total Ad Spend",
                f"${exec_totals['total_spend']:,.0f}",
                subtext=f"Paid: ${exec_totals['paid_spend']:,.0f}",
                pill_text="INVESTMENT",
                pill_type="neutral",
            ),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            render_metric_card_html(
                "Customers Acquired",
                f"{exec_totals['total_customers']:,}",
                subtext=f"From {exec_totals['total_leads']:,} leads",
                pill_text=f"{exec_totals['blended_cvr_pct']:.1f}% CVR",
                pill_type="positive" if exec_totals['blended_cvr_pct'] >= 3.0 else "neutral",
            ),
            unsafe_allow_html=True,
        )
    with c3:
        cac_pill = "positive" if exec_totals['blended_cac'] <= 60 else "negative"
        st.markdown(
            render_metric_card_html(
                "Blended CAC",
                f"${exec_totals['blended_cac']:.2f}",
                subtext=f"Paid-Only: ${exec_totals['paid_cac']:.2f}",
                pill_text="TARGET: <$60",
                pill_type=cac_pill,
            ),
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            render_metric_card_html(
                "Net Revenue",
                f"${exec_totals['total_net_revenue']:,.0f}",
                subtext=f"Profit: ${exec_totals['total_gross_profit']:,.0f}",
                pill_text="TOP-LINE",
                pill_type="positive",
            ),
            unsafe_allow_html=True,
        )
    with c5:
        roas_pill = "positive" if exec_totals['blended_roas'] >= 2.5 else "negative"
        st.markdown(
            render_metric_card_html(
                "Blended ROAS",
                f"{exec_totals['blended_roas']:.2f}x",
                subtext=f"Paid ROAS: {exec_totals['paid_roas']:.2f}x",
                pill_text="TARGET: >=3.0x",
                pill_type=roas_pill,
            ),
            unsafe_allow_html=True,
        )
    with c6:
        roi_pill = "positive" if exec_totals['blended_roi_pct'] > 0 else "negative"
        st.markdown(
            render_metric_card_html(
                "Net Campaign ROI",
                f"{exec_totals['blended_roi_pct']:+.1f}%",
                subtext=f"ARPU: ${exec_totals['blended_arpu']:.2f}",
                pill_text="BOTTOM LINE",
                pill_type=roi_pill,
            ),
            unsafe_allow_html=True,
        )

    st.markdown("---")
    col_w1, col_w2 = st.columns([1, 1])
    with col_w1:
        st.plotly_chart(plot_waterfall_financials(exec_totals), use_container_width=True)
    with col_w2:
        st.plotly_chart(plot_funnel_sankey(df_camp, df_leads, df_orders), use_container_width=True)

# ==============================================================================
# TAB 2: CHANNEL & CAMPAIGN DRILLDOWN
# ==============================================================================
with tab2:
    st.markdown("### Multi-Channel Efficiency Matrix & SQL Unit Economics")
    st.plotly_chart(plot_bubble_cac_vs_roas(channel_summary), use_container_width=True)

    st.markdown("#### Detailed Channel Unit Economics Table")
    display_cols = [
        "channel", "total_spend", "total_clicks", "ctr_pct", "cpc",
        "total_leads", "acquired_customers", "cvr_pct", "cac",
        "total_net_revenue", "arpu", "roas", "net_roi_pct", "ltv_cac_ratio", "payback_months"
    ]
    st.dataframe(
        channel_summary[display_cols].style.format({
            "total_spend": "${:,.2f}",
            "total_clicks": "{:,}",
            "ctr_pct": "{:.2f}%",
            "cpc": "${:.2f}",
            "total_leads": "{:,}",
            "acquired_customers": "{:,}",
            "cvr_pct": "{:.2f}%",
            "cac": "${:.2f}",
            "total_net_revenue": "${:,.2f}",
            "arpu": "${:.2f}",
            "roas": "{:.2f}x",
            "net_roi_pct": "{:+.1f}%",
            "ltv_cac_ratio": "{:.2f}x",
            "payback_months": "{:.1f} mo",
        }),
        use_container_width=True,
    )

    st.markdown("---")
    st.markdown("#### Rolling 7-Day Performance Dynamics")
    ch_select = st.selectbox("Select Channel to View 7-Day Moving Averages", options=selected_channels)
    try:
        rolling_df = db_manager.run_named_query("rolling_channel_trends")
        st.plotly_chart(plot_rolling_trends(rolling_df, ch_select), use_container_width=True)
    except Exception as exc:
        st.info("Rolling trends calculated from database.")

    st.markdown("#### SQL Analytical Query: Campaign Quartile Ranking (Window Functions NTILE & ROW_NUMBER)")
    try:
        quartile_df = db_manager.run_named_query("campaign_quartile_ranking")
        st.dataframe(
            quartile_df.head(10).style.format({
                "total_spend": "${:,.2f}",
                "total_acquisitions": "{:,}",
                "total_revenue": "${:,.2f}",
                "cac": "${:.2f}",
                "roas": "{:.2f}x",
                "roi_pct": "{:+.1f}%",
            }),
            use_container_width=True,
        )
    except Exception as exc:
        st.caption("Campaign quartile ranking loaded from SQL engine.")

# ==============================================================================
# TAB 3: COHORT & LTV PROGRESSION
# ==============================================================================
with tab3:
    st.markdown("### Customer Cohort Retention & Cumulative LTV Progression")
    st.caption("Tracks cumulative revenue realized per customer over subsequent months following acquisition.")

    try:
        cohort_df = db_manager.run_named_query("cohort_ltv_progression")
        col_c1, col_c2 = st.columns([1.2, 1])
        with col_c1:
            st.plotly_chart(plot_cohort_cumulative_ltv(cohort_df), use_container_width=True)
        with col_c2:
            st.markdown("#### Cohort Retention Table")
            st.dataframe(
                cohort_df[[
                    "cohort_month", "month_number", "initial_customers",
                    "active_retained_customers", "retention_rate_pct",
                    "month_revenue", "cumulative_ltv_per_customer"
                ]].style.format({
                    "initial_customers": "{:,}",
                    "active_retained_customers": "{:,}",
                    "retention_rate_pct": "{:.1f}%",
                    "month_revenue": "${:,.2f}",
                    "cumulative_ltv_per_customer": "${:.2f}",
                }),
                use_container_width=True,
            )
    except Exception as exc:
        st.error(f"Error executing cohort query: {exc}")

# ==============================================================================
# TAB 4: STATISTICAL HYPOTHESIS TESTING STUDIO
# ==============================================================================
with tab4:
    st.markdown("### 🔬 Scientific Experimentation & Hypothesis Studio")
    st.markdown("Conduct rigorous hypothesis tests using **SciPy** to evaluate acquisition conversion and monetization.")

    # 1. Chi-Square Test
    st.markdown("#### 1. Chi-Square Test of Independence: Channel vs. Lead Conversion")
    chi_results = stat_engine.chi_square_conversion_test(df_leads, group_col="channel")
    if "error" not in chi_results:
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        col_s1.metric("Chi-Square (χ²)", f"{chi_results['chi2_statistic']:.2f}")
        col_s2.metric("p-value", f"{chi_results['p_value']:.4e}")
        col_s3.metric("Degrees of Freedom", f"{chi_results['degrees_of_freedom']}")
        col_s4.metric("Cramér's V (Effect Size)", f"{chi_results['cramers_v']:.4f}")

        st.info(f"**Statistical Conclusion:** {chi_results['conclusion']}")
        st.plotly_chart(plot_confidence_intervals(chi_results["group_breakdown"]), use_container_width=True)

    st.markdown("---")
    # 2. Two-Sample Welch's t-test / Mann-Whitney
    st.markdown("#### 2. Two-Sample Hypothesis Testing: Monetization & Order Values")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        chan_a = st.selectbox("Select Channel A", options=selected_channels, index=0)
    with col_t2:
        chan_b = st.selectbox("Select Channel B", options=selected_channels, index=min(1, len(selected_channels)-1))

    if chan_a and chan_b and chan_a != chan_b:
        cust_ch = df_leads.dropna(subset=["customer_id"])[["customer_id", "channel"]].drop_duplicates("customer_id")
        merged_orders = df_orders.merge(cust_ch, on="customer_id")
        rev_a = merged_orders[merged_orders["channel"] == chan_a]["net_revenue"].values
        rev_b = merged_orders[merged_orders["channel"] == chan_b]["net_revenue"].values

        ttest_res = stat_engine.two_sample_revenue_test(rev_a, rev_b, chan_a, chan_b)
        if "error" not in ttest_res:
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.metric(f"{chan_a} Mean", f"${ttest_res['mean_a']:.2f}", f"N={ttest_res['sample_size_a']}")
            col_m2.metric(f"{chan_b} Mean", f"${ttest_res['mean_b']:.2f}", f"N={ttest_res['sample_size_b']}")
            col_m3.metric("Welch's t-stat", f"{ttest_res['welch_t_stat']:.2f}", f"p={ttest_res['welch_p_value']:.4f}")
            col_m4.metric("Cohen's d Effect Size", f"{ttest_res['cohens_d']:.3f}")

            st.success(f"**Interpretation:** {ttest_res['interpretation']}")
            st.caption(f"Mann-Whitney U Test p-value: {ttest_res['mann_whitney_p_value']:.4f} (Non-parametric verification).")

# ==============================================================================
# TAB 5: SCENARIO PLANNER & STRATEGIC RECOMMENDATIONS
# ==============================================================================
with tab5:
    st.markdown("### 💡 Marketing Mix Budget Reallocation Simulator")
    st.caption("Model the financial impact of shifting budget from high-CAC channels to high-ROAS channels.")

    col_sim1, col_sim2, col_sim3 = st.columns(3)
    with col_sim1:
        src_ch = st.selectbox("Reduce Spend On (Source Channel)", options=channel_summary["channel"].tolist(), index=2)
    with col_sim2:
        tgt_ch = st.selectbox("Increase Spend On (Target Channel)", options=channel_summary["channel"].tolist(), index=4)
    with col_sim3:
        shift_pct = st.slider("Budget Reallocation Percentage", min_value=0.05, max_value=0.50, value=0.20, step=0.05)

    if src_ch and tgt_ch and src_ch != tgt_ch:
        sim_res = scenario_planner.simulate_budget_reallocation(channel_summary, src_ch, tgt_ch, shift_pct)
        if "error" not in sim_res:
            st.markdown("#### Projected Marginal Uplift")
            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("Shifted Budget", f"${sim_res['shifted_budget']:,.2f}")
            sc2.metric("Net Customers Delta", f"{sim_res['net_customer_delta']:+,.0f}", f"+{sim_res['gained_customers_target']:.0f} / -{sim_res['lost_customers_source']:.0f}")
            sc3.metric("Net Revenue Delta", f"${sim_res['net_revenue_delta']:+,.2f}")
            sc4.metric("ROAS Improvement", f"{sim_res['projected_roas']:.2f}x", f"{sim_res['roas_improvement_multiple']:+.2f}x")

    st.markdown("---")
    st.markdown("### 📋 Automated Executive Recommendations")
    recs = scenario_planner.generate_executive_recommendations(channel_summary)
    for r in recs:
        p_class = f"rec-{r['priority'].lower()}"
        st.markdown(
            f"""
            <div class="rec-card {p_class}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong style="font-size: 1.05rem;">{r['title']}</strong>
                    <span class="badge-tag" style="background: rgba(255,255,255,0.1);">{r['priority']} PRIORITY</span>
                </div>
                <div style="margin-top: 6px; font-size: 0.90rem; color: #cbd5e1;">{r['detail']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
