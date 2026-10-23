-- ============================================================================
-- Customer Acquisition & Campaign ROI Analytics SQL Engine
-- Features: Joins, CTEs, Window Functions, and Multi-Level Aggregations
-- ============================================================================

-- ============================================================================
-- QUERY 1: Channel-Level Acquisition Unit Economics & Campaign ROI
-- Joins campaign spend, leads, and orders via CTEs to compute CAC, ROAS & ROI.
-- ============================================================================
-- @name: channel_performance_kpis
WITH channel_spend AS (
    SELECT
        channel,
        COUNT(DISTINCT campaign_id) AS active_campaigns,
        SUM(ad_spend) AS total_spend,
        SUM(impressions) AS total_impressions,
        SUM(clicks) AS total_clicks,
        ROUND(CASE WHEN SUM(impressions) > 0 THEN (SUM(clicks) * 100.0) / SUM(impressions) ELSE 0 END, 2) AS ctr_pct,
        ROUND(CASE WHEN SUM(clicks) > 0 THEN SUM(ad_spend) / SUM(clicks) ELSE 0 END, 2) AS cpc
    FROM campaign_spend
    GROUP BY channel
),
channel_leads_agg AS (
    SELECT
        channel,
        COUNT(lead_id) AS total_leads,
        COUNT(DISTINCT customer_id) AS acquired_customers,
        ROUND(AVG(lead_score), 1) AS avg_lead_score,
        ROUND(CASE WHEN COUNT(lead_id) > 0 THEN (COUNT(DISTINCT customer_id) * 100.0) / COUNT(lead_id) ELSE 0 END, 2) AS conversion_rate_pct
    FROM customer_leads
    GROUP BY channel
),
channel_revenue AS (
    SELECT
        cl.channel,
        COUNT(co.order_id) AS total_transactions,
        ROUND(SUM(co.net_revenue), 2) AS total_net_revenue,
        ROUND(SUM(co.gross_profit), 2) AS total_gross_profit,
        ROUND(AVG(co.net_revenue), 2) AS avg_order_value
    FROM customer_orders co
    INNER JOIN customer_leads cl ON co.customer_id = cl.customer_id
    GROUP BY cl.channel
)
SELECT
    cs.channel,
    cs.total_spend,
    cs.total_impressions,
    cs.total_clicks,
    cs.ctr_pct,
    cs.cpc,
    COALESCE(cla.total_leads, 0) AS total_leads,
    COALESCE(cla.acquired_customers, 0) AS acquired_customers,
    COALESCE(cla.conversion_rate_pct, 0.0) AS conversion_rate_pct,
    -- Customer Acquisition Cost (CAC)
    ROUND(CASE WHEN COALESCE(cla.acquired_customers, 0) > 0 
               THEN cs.total_spend / cla.acquired_customers 
               ELSE 0 END, 2) AS cac,
    COALESCE(cr.total_transactions, 0) AS total_orders,
    COALESCE(cr.total_net_revenue, 0.0) AS total_net_revenue,
    COALESCE(cr.total_gross_profit, 0.0) AS total_gross_profit,
    -- Average Revenue Per Acquired User (ARPU)
    ROUND(CASE WHEN COALESCE(cla.acquired_customers, 0) > 0 
               THEN COALESCE(cr.total_net_revenue, 0.0) / cla.acquired_customers 
               ELSE 0 END, 2) AS arpu,
    -- Return On Ad Spend (ROAS multiple)
    ROUND(CASE WHEN cs.total_spend > 0 
               THEN COALESCE(cr.total_net_revenue, 0.0) / cs.total_spend 
               ELSE 0 END, 2) AS roas_multiple,
    -- Campaign Net ROI (%) = ((Gross Profit - Ad Spend) / Ad Spend) * 100
    ROUND(CASE WHEN cs.total_spend > 0 
               THEN ((COALESCE(cr.total_gross_profit, 0.0) - cs.total_spend) * 100.0) / cs.total_spend 
               ELSE 0 END, 2) AS net_roi_pct
FROM channel_spend cs
LEFT JOIN channel_leads_agg cla ON cs.channel = cla.channel
LEFT JOIN channel_revenue cr ON cs.channel = cr.channel
ORDER BY cs.total_spend DESC;


-- ============================================================================
-- QUERY 2: Rolling 7-Day and 30-Day Moving Averages of Unit Economics
-- Window functions: AVG() OVER (PARTITION BY ... ORDER BY ... ROWS BETWEEN ...)
-- ============================================================================
-- @name: rolling_channel_trends
WITH daily_metrics AS (
    SELECT
        cs.date,
        cs.channel,
        SUM(cs.ad_spend) AS daily_spend,
        SUM(cs.clicks) AS daily_clicks,
        COUNT(DISTINCT cl.customer_id) AS daily_acquisitions,
        COALESCE(SUM(co.net_revenue), 0.0) AS daily_revenue
    FROM campaign_spend cs
    LEFT JOIN customer_leads cl 
        ON cs.campaign_id = cl.campaign_id 
        AND CAST(cl.conversion_date AS DATE) = cs.date
    LEFT JOIN customer_orders co 
        ON cl.customer_id = co.customer_id 
        AND CAST(co.order_date AS DATE) = cs.date
    GROUP BY cs.date, cs.channel
)
SELECT
    date,
    channel,
    daily_spend,
    daily_acquisitions,
    daily_revenue,
    -- 7-Day Moving Averages
    ROUND(AVG(daily_spend) OVER (
        PARTITION BY channel 
        ORDER BY date 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2) AS rolling_7d_spend,
    ROUND(AVG(daily_acquisitions) OVER (
        PARTITION BY channel 
        ORDER BY date 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2) AS rolling_7d_acquisitions,
    ROUND(AVG(daily_revenue) OVER (
        PARTITION BY channel 
        ORDER BY date 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2) AS rolling_7d_revenue
FROM daily_metrics
ORDER BY channel, date;


-- ============================================================================
-- QUERY 3: Customer Cohort Retention & Cumulative LTV Progression
-- CTEs, DATE_TRUNC, Window Functions: SUM() OVER (PARTITION BY cohort ORDER BY ...)
-- ============================================================================
-- @name: cohort_ltv_progression
WITH customer_cohorts AS (
    SELECT
        customer_id,
        channel,
        DATE_TRUNC('month', conversion_date) AS cohort_month
    FROM customer_leads
    WHERE customer_id IS NOT NULL
),
cohort_orders AS (
    SELECT
        cc.customer_id,
        cc.channel,
        cc.cohort_month,
        DATE_TRUNC('month', co.order_date) AS order_month,
        SUM(co.net_revenue) AS month_revenue
    FROM customer_cohorts cc
    INNER JOIN customer_orders co ON cc.customer_id = co.customer_id
    GROUP BY cc.customer_id, cc.channel, cc.cohort_month, DATE_TRUNC('month', co.order_date)
),
cohort_size AS (
    SELECT
        cohort_month,
        COUNT(DISTINCT customer_id) AS initial_customers
    FROM customer_cohorts
    GROUP BY cohort_month
),
monthly_cohort_agg AS (
    SELECT
        co.cohort_month,
        co.order_month,
        cs.initial_customers,
        COUNT(DISTINCT co.customer_id) AS active_retained_customers,
        SUM(co.month_revenue) AS total_month_revenue,
        -- Month index calculation (0 = acquisition month)
        ROUND(
            (EXTRACT(YEAR FROM co.order_month) - EXTRACT(YEAR FROM co.cohort_month)) * 12 +
            (EXTRACT(MONTH FROM co.order_month) - EXTRACT(MONTH FROM co.cohort_month))
        ) AS month_number
    FROM cohort_orders co
    INNER JOIN cohort_size cs ON co.cohort_month = cs.cohort_month
    GROUP BY co.cohort_month, co.order_month, cs.initial_customers
)
SELECT
    cohort_month,
    order_month,
    CAST(month_number AS INTEGER) AS month_number,
    initial_customers,
    active_retained_customers,
    ROUND((active_retained_customers * 100.0) / initial_customers, 2) AS retention_rate_pct,
    ROUND(total_month_revenue, 2) AS month_revenue,
    -- Window Function: Cumulative Cohort LTV over time
    ROUND(
        SUM(total_month_revenue) OVER (
            PARTITION BY cohort_month 
            ORDER BY month_number 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) / initial_customers, 2
    ) AS cumulative_ltv_per_customer
FROM monthly_cohort_agg
ORDER BY cohort_month, month_number;


-- ============================================================================
-- QUERY 4: Campaign Performance Ranking & Quartile Segmentation
-- Window Functions: NTILE(4), ROW_NUMBER(), DENSE_RANK()
-- ============================================================================
-- @name: campaign_quartile_ranking
WITH campaign_aggregates AS (
    SELECT
        cs.campaign_id,
        MAX(cs.campaign_name) AS campaign_name,
        MAX(cs.channel) AS channel,
        SUM(cs.ad_spend) AS total_spend,
        SUM(cs.clicks) AS total_clicks,
        COUNT(DISTINCT cl.customer_id) AS total_acquisitions,
        COALESCE(SUM(co.net_revenue), 0.0) AS total_revenue,
        COALESCE(SUM(co.gross_profit), 0.0) AS total_gross_profit
    FROM campaign_spend cs
    LEFT JOIN customer_leads cl ON cs.campaign_id = cl.campaign_id
    LEFT JOIN customer_orders co ON cl.customer_id = co.customer_id
    GROUP BY cs.campaign_id
),
campaign_metrics AS (
    SELECT
        campaign_id,
        campaign_name,
        channel,
        total_spend,
        total_acquisitions,
        total_revenue,
        ROUND(CASE WHEN total_acquisitions > 0 THEN total_spend / total_acquisitions ELSE 0 END, 2) AS cac,
        ROUND(CASE WHEN total_spend > 0 THEN total_revenue / total_spend ELSE 0 END, 2) AS roas,
        ROUND(CASE WHEN total_spend > 0 THEN ((total_gross_profit - total_spend) * 100.0) / total_spend ELSE 0 END, 2) AS roi_pct
    FROM campaign_aggregates
)
SELECT
    campaign_id,
    campaign_name,
    channel,
    total_spend,
    total_acquisitions,
    total_revenue,
    cac,
    roas,
    roi_pct,
    -- Window Functions: Rank within channel and overall quartile segmentation
    ROW_NUMBER() OVER (ORDER BY roas DESC) AS overall_rank_by_roas,
    DENSE_RANK() OVER (PARTITION BY channel ORDER BY roas DESC) AS rank_within_channel,
    NTILE(4) OVER (ORDER BY roas DESC) AS performance_quartile -- 1 = Top Quartile, 4 = Bottom Quartile
FROM campaign_metrics
ORDER BY roas DESC;
