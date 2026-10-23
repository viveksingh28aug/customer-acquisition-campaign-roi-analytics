"""Data Loader and Benchmark Dataset Generator.

Generates realistic, statistically calibrated multi-channel marketing acquisition
and e-commerce transaction datasets with documented baseline parameters.
Injects controlled real-world data quality anomalies (duplicates, missing values,
type inconsistencies) to rigorously test the data cleaning pipeline.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Tuple
import numpy as np
import pandas as pd

from src.logger import logger


def generate_benchmark_raw_datasets(
    output_dir: str = "data/raw",
    start_date: str = "2026-01-01",
    num_days: int = 120,
    random_seed: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Generate raw marketing campaign, lead conversion, and customer transaction datasets.

    Args:
        output_dir: Directory where raw CSV files are saved.
        start_date: Starting date string (YYYY-MM-DD).
        num_days: Number of days to generate time-series across.
        random_seed: Reproducibility seed.

    Returns:
        Tuple of (df_campaigns_raw, df_leads_raw, df_orders_raw).
    """
    np.random.seed(random_seed)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    base_date = datetime.strptime(start_date, "%Y-%m-%d")
    date_list = [base_date + timedelta(days=i) for i in range(num_days)]

    channels_meta = [
        {"channel": "Google Search", "cpc_range": (1.80, 4.50), "ctr_range": (0.035, 0.065), "daily_spend": (400, 900)},
        {"channel": "Meta Ads", "cpc_range": (0.85, 2.20), "ctr_range": (0.018, 0.038), "daily_spend": (500, 1100)},
        {"channel": "LinkedIn Ads", "cpc_range": (4.50, 9.50), "ctr_range": (0.008, 0.022), "daily_spend": (300, 750)},
        {"channel": "YouTube Ads", "cpc_range": (0.40, 1.20), "ctr_range": (0.012, 0.025), "daily_spend": (250, 600)},
        {"channel": "Email Marketing", "cpc_range": (0.05, 0.25), "ctr_range": (0.060, 0.120), "daily_spend": (50, 150)},
        {"channel": "Organic Search", "cpc_range": (0.00, 0.05), "ctr_range": (0.040, 0.080), "daily_spend": (20, 60)},
    ]

    campaign_records = []
    campaign_id_map = {}
    c_idx = 101

    # 1. Generate Campaign Spend Data
    for ch_info in channels_meta:
        ch = ch_info["channel"]
        for camp_num in [1, 2]:
            camp_id = f"CMP-{c_idx}"
            camp_name = f"{ch.replace(' ', '_')}_Q1_Camp{camp_num}"
            campaign_id_map[(ch, camp_num)] = camp_id
            c_idx += 1

            for day in date_list:
                spend = round(float(np.random.uniform(*ch_info["daily_spend"]) * (1.0 + 0.25 * (day.weekday() in [1, 2, 3]))), 2)
                cpc = float(np.random.uniform(*ch_info["cpc_range"]))
                clicks = int(spend / cpc) if cpc > 0 else int(np.random.uniform(50, 200))
                ctr = float(np.random.uniform(*ch_info["ctr_range"]))
                impressions = int(clicks / ctr) if ctr > 0 else clicks * 20

                campaign_records.append({
                    "campaign_id": camp_id,
                    "campaign_name": camp_name,
                    "channel": ch,
                    "date": day.strftime("%Y-%m-%d"),
                    "ad_spend": spend,
                    "impressions": impressions,
                    "clicks": clicks,
                    "target_audience": np.random.choice(["B2B Professionals", "Young Adults (18-34)", "Tech Enthusiasts", "Broad Audience", None], p=[0.25, 0.25, 0.25, 0.20, 0.05]),
                    "region": np.random.choice(["North America", "EMEA", "APAC", "LATAM"], p=[0.50, 0.25, 0.15, 0.10]),
                })

    df_campaigns = pd.DataFrame(campaign_records)

    # Inject data quality anomalies into campaigns:
    # A. 4 duplicate rows
    df_campaigns = pd.concat([df_campaigns, df_campaigns.iloc[10:14]], ignore_index=True)
    # B. 2 negative/corrupt spend records
    df_campaigns.loc[15, "ad_spend"] = -150.00
    df_campaigns.loc[25, "ad_spend"] = np.nan
    # C. Whitespace issue in channel name
    df_campaigns.loc[30, "channel"] = "  Google Search  "

    # 2. Generate Customer Leads & Conversions Data
    lead_records = []
    lead_id_counter = 10001
    customer_id_counter = 50001
    customer_pool = []

    # Probability of conversion given lead by channel
    channel_cvr = {
        "Google Search": 0.052,
        "Meta Ads": 0.034,
        "LinkedIn Ads": 0.068,
        "YouTube Ads": 0.021,
        "Email Marketing": 0.085,
        "Organic Search": 0.048,
    }

    for _, row in df_campaigns.dropna(subset=["clicks"]).iterrows():
        # sample leads proportional to clicks
        if row["clicks"] <= 0:
            continue
        num_leads = int(np.random.poisson(lam=max(1, row["clicks"] * 0.15)))
        ch_clean = str(row["channel"]).strip()
        cvr = channel_cvr.get(ch_clean, 0.04)

        for _ in range(num_leads):
            lead_dt = datetime.strptime(str(row["date"]), "%Y-%m-%d") + timedelta(hours=int(np.random.randint(0, 24)))
            is_converted = bool(np.random.binomial(n=1, p=cvr))
            cust_id = None
            conv_dt = None

            if is_converted:
                cust_id = f"CUST-{customer_id_counter}"
                customer_id_counter += 1
                # Conversion lag: 0 to 7 days
                conv_dt = lead_dt + timedelta(days=int(np.random.exponential(scale=1.5)), hours=int(np.random.randint(1, 12)))
                customer_pool.append({
                    "customer_id": cust_id,
                    "acquisition_date": conv_dt,
                    "channel": ch_clean,
                    "campaign_id": row["campaign_id"],
                })

            lead_records.append({
                "lead_id": f"LEAD-{lead_id_counter}",
                "customer_id": cust_id,
                "campaign_id": row["campaign_id"],
                "channel": row["channel"],
                "lead_date": lead_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "converted_flag": 1 if is_converted else 0,
                "conversion_date": conv_dt.strftime("%Y-%m-%d %H:%M:%S") if conv_dt else None,
                "signup_platform": np.random.choice(["Web", "iOS", "Android", "Unknown"], p=[0.55, 0.25, 0.18, 0.02]),
                "lead_score": round(float(np.random.normal(loc=65 if is_converted else 42, scale=12)), 1),
            })
            lead_id_counter += 1

    df_leads = pd.DataFrame(lead_records)

    # Inject anomalies into leads:
    # A. Duplicates
    df_leads = pd.concat([df_leads, df_leads.iloc[50:55]], ignore_index=True)
    # B. Missing lead_score
    df_leads.loc[np.random.choice(df_leads.index, size=40, replace=False), "lead_score"] = np.nan

    # 3. Generate Customer Orders & Net Revenue
    order_records = []
    order_id_counter = 80001

    for cust in customer_pool:
        # Customers have 1 to 4 transactions over time
        num_orders = np.random.choice([1, 2, 3, 4], p=[0.65, 0.22, 0.09, 0.04])
        current_dt = cust["acquisition_date"]

        for o_idx in range(num_orders):
            if o_idx > 0:
                current_dt += timedelta(days=int(np.random.exponential(scale=18)) + 1)

            # Order value: log-normal distribution with mean around $95
            order_val = round(float(np.random.lognormal(mean=4.4, sigma=0.55)), 2)
            discount = round(float(np.random.choice([0.0, order_val * 0.10, order_val * 0.15], p=[0.60, 0.25, 0.15])), 2)
            net_rev = round(order_val - discount, 2)
            # COGS assumption: ~35% of gross order value
            cogs = round(order_val * float(np.random.uniform(0.30, 0.40)), 2)
            gross_profit = round(net_rev - cogs, 2)

            order_records.append({
                "order_id": f"ORD-{order_id_counter}",
                "customer_id": cust["customer_id"],
                "order_date": current_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "order_value": order_val,
                "discount_amount": discount,
                "net_revenue": net_rev,
                "cogs": cogs,
                "gross_profit": gross_profit,
                "payment_method": np.random.choice(["Credit Card", "PayPal", "Apple Pay", "Debit Card"], p=[0.50, 0.25, 0.15, 0.10]),
            })
            order_id_counter += 1

    df_orders = pd.DataFrame(order_records)

    # Inject anomalies into orders:
    # A. 3 duplicate orders
    df_orders = pd.concat([df_orders, df_orders.iloc[15:18]], ignore_index=True)
    # B. Corrupt negative discount
    df_orders.loc[22, "discount_amount"] = -25.0

    # Save raw CSVs
    camp_file = out_path / "campaign_spend_raw.csv"
    lead_file = out_path / "customer_leads_raw.csv"
    order_file = out_path / "customer_orders_raw.csv"

    df_campaigns.to_csv(camp_file, index=False)
    df_leads.to_csv(lead_file, index=False)
    df_orders.to_csv(order_file, index=False)

    logger.info("Successfully generated raw benchmark datasets at %s", output_dir)
    logger.info("Raw counts: Campaigns=%d, Leads=%d, Orders=%d", len(df_campaigns), len(df_leads), len(df_orders))

    return df_campaigns, df_leads, df_orders


if __name__ == "__main__":
    generate_benchmark_raw_datasets()
