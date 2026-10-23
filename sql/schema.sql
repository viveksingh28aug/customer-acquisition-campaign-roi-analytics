-- ============================================================================
-- Customer Acquisition & Campaign ROI Analytics Database Schema
-- Production PostgreSQL DDL with Indexes and Constraints
-- ============================================================================

-- 1. Campaign Spend & Ad Performance Table
CREATE TABLE IF NOT EXISTS campaign_spend (
    campaign_id VARCHAR(50) NOT NULL,
    campaign_name VARCHAR(150) NOT NULL,
    channel VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    ad_spend NUMERIC(12, 2) NOT NULL CHECK (ad_spend >= 0),
    impressions INTEGER NOT NULL CHECK (impressions >= 0),
    clicks INTEGER NOT NULL CHECK (clicks >= 0),
    target_audience VARCHAR(100),
    region VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (campaign_id, date)
);

-- 2. Customer Leads & Conversion Funnel Table
CREATE TABLE IF NOT EXISTS customer_leads (
    lead_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50),
    campaign_id VARCHAR(50) NOT NULL,
    channel VARCHAR(50) NOT NULL,
    lead_date TIMESTAMP NOT NULL,
    converted_flag SMALLINT NOT NULL CHECK (converted_flag IN (0, 1)),
    conversion_date TIMESTAMP,
    signup_platform VARCHAR(50) NOT NULL,
    lead_score NUMERIC(5, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Customer Orders & Monetization Table
CREATE TABLE IF NOT EXISTS customer_orders (
    order_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    order_date TIMESTAMP NOT NULL,
    order_value NUMERIC(12, 2) NOT NULL CHECK (order_value >= 0),
    discount_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.0 CHECK (discount_amount >= 0),
    net_revenue NUMERIC(12, 2) NOT NULL CHECK (net_revenue >= 0),
    cogs NUMERIC(12, 2) NOT NULL CHECK (cogs >= 0),
    gross_profit NUMERIC(12, 2) NOT NULL,
    payment_method VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Performance Optimization Indexes
CREATE INDEX IF NOT EXISTS idx_campaign_spend_channel ON campaign_spend(channel);
CREATE INDEX IF NOT EXISTS idx_campaign_spend_date ON campaign_spend(date);
CREATE INDEX IF NOT EXISTS idx_leads_campaign_id ON customer_leads(campaign_id);
CREATE INDEX IF NOT EXISTS idx_leads_customer_id ON customer_leads(customer_id);
CREATE INDEX IF NOT EXISTS idx_leads_channel ON customer_leads(channel);
CREATE INDEX IF NOT EXISTS idx_leads_lead_date ON customer_leads(lead_date);
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON customer_orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_order_date ON customer_orders(order_date);
