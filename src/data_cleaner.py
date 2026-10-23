"""Data Cleaning and Validation Pipeline.

Handles missing values, duplicate removal, invalid data types,
anomalous values, and cross-field integrity checks for marketing campaign,
lead conversion, and order transaction records.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import numpy as np
import pandas as pd

from src.logger import logger


class DataCleaner:
    """Robust data cleaning and validation engine for marketing acquisition data."""

    def __init__(self, raw_dir: str = "data/raw", processed_dir: str = "data/processed"):
        self.raw_dir = Path(raw_dir)
        self.processed_dir = Path(processed_dir)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.audit_report: Dict[str, Any] = {}

    def clean_campaign_spend(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """Clean campaign spend dataset.

        Args:
            df_raw: Raw campaigns DataFrame.

        Returns:
            Cleaned and validated DataFrame.
        """
        logger.info("Starting cleaning of campaign_spend (initial rows: %d)", len(df_raw))
        df = df_raw.copy()

        # 1. Whitespace stripping for string columns
        str_cols = ["campaign_id", "campaign_name", "channel", "region", "target_audience"]
        for col in str_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().replace("nan", np.nan).replace("None", np.nan)

        # 2. Deduplication on composite natural key: campaign_id + date
        init_len = len(df)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date", "campaign_id"])
        df = df.drop_duplicates(subset=["campaign_id", "date"], keep="first")
        dups_removed = init_len - len(df)

        # 3. Handle missing & invalid numeric values
        # Drop or fix negative spend
        invalid_spend_mask = (df["ad_spend"] < 0) | df["ad_spend"].isna()
        num_invalid_spend = int(invalid_spend_mask.sum())
        # Impute or drop invalid spend: if clicks exist, estimate using median CPC for that channel
        df.loc[df["ad_spend"] < 0, "ad_spend"] = np.nan

        # Impute missing ad_spend using channel median CPC * clicks where possible
        median_cpc_by_channel = (df["ad_spend"] / df["clicks"].replace(0, np.nan)).groupby(df["channel"]).median()
        for ch, med_cpc in median_cpc_by_channel.items():
            fill_val = med_cpc if pd.notna(med_cpc) else 1.0
            mask = df["channel"].eq(ch) & df["ad_spend"].isna()
            df.loc[mask, "ad_spend"] = (df.loc[mask, "clicks"] * fill_val).round(2)

        # Fallback if any spend is still NaN
        df["ad_spend"] = df["ad_spend"].fillna(0.0).round(2)

        # 4. Impressions and Clicks validation
        df["impressions"] = pd.to_numeric(df["impressions"], errors="coerce").fillna(0).astype(int).clip(lower=0)
        df["clicks"] = pd.to_numeric(df["clicks"], errors="coerce").fillna(0).astype(int).clip(lower=0)
        # Clicks cannot exceed impressions
        df["clicks"] = np.minimum(df["clicks"], df["impressions"])

        # 5. Missing Categorical values
        df["target_audience"] = df["target_audience"].fillna("Unspecified")
        df["region"] = df["region"].fillna("Global")

        # 6. Type conversions and formatting
        df["date_str"] = df["date"].dt.strftime("%Y-%m-%d")

        self.audit_report["campaign_spend"] = {
            "initial_rows": init_len,
            "final_rows": len(df),
            "duplicates_removed": dups_removed,
            "invalid_spend_imputed": num_invalid_spend,
        }
        logger.info("Finished cleaning campaign_spend (clean rows: %d)", len(df))
        return df

    def clean_customer_leads(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """Clean customer leads and conversions dataset.

        Args:
            df_raw: Raw customer leads DataFrame.

        Returns:
            Cleaned and validated DataFrame.
        """
        logger.info("Starting cleaning of customer_leads (initial rows: %d)", len(df_raw))
        df = df_raw.copy()

        init_len = len(df)
        # 1. Trim strings
        for col in ["lead_id", "customer_id", "campaign_id", "channel", "signup_platform"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().replace("nan", np.nan).replace("None", np.nan)

        # 2. Deduplication on lead_id
        df = df.drop_duplicates(subset=["lead_id"], keep="first")
        dups_removed = init_len - len(df)

        # 3. Parse timestamps
        df["lead_date"] = pd.to_datetime(df["lead_date"], errors="coerce")
        df["conversion_date"] = pd.to_datetime(df["conversion_date"], errors="coerce")
        df = df.dropna(subset=["lead_date"])

        # 4. Conversion integrity check
        # If conversion_date exists and >= lead_date, converted_flag should be 1
        valid_conv = (df["conversion_date"].notna()) & (df["conversion_date"] >= df["lead_date"])
        df.loc[valid_conv, "converted_flag"] = 1

        # Inconsistent conversion dates before lead_date fixed
        invalid_conv_dt = (df["conversion_date"].notna()) & (df["conversion_date"] < df["lead_date"])
        df.loc[invalid_conv_dt, "conversion_date"] = df.loc[invalid_conv_dt, "lead_date"]

        df["converted_flag"] = pd.to_numeric(df["converted_flag"], errors="coerce").fillna(0).astype(int).clip(0, 1)

        # Ensure customer_id consistency: null if not converted
        df.loc[df["converted_flag"] == 0, "customer_id"] = np.nan

        # 5. Missing lead score imputation: median score by conversion flag
        median_score_conv = df.groupby("converted_flag")["lead_score"].transform("median")
        missing_lead_scores = int(df["lead_score"].isna().sum())
        df["lead_score"] = df["lead_score"].fillna(median_score_conv).fillna(50.0).round(1)

        # 6. Categoricals
        df["signup_platform"] = df["signup_platform"].fillna("Web").replace("Unknown", "Web")

        self.audit_report["customer_leads"] = {
            "initial_rows": init_len,
            "final_rows": len(df),
            "duplicates_removed": dups_removed,
            "missing_lead_scores_imputed": missing_lead_scores,
        }
        logger.info("Finished cleaning customer_leads (clean rows: %d)", len(df))
        return df

    def clean_customer_orders(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """Clean customer order and transaction dataset.

        Args:
            df_raw: Raw customer orders DataFrame.

        Returns:
            Cleaned and validated DataFrame.
        """
        logger.info("Starting cleaning of customer_orders (initial rows: %d)", len(df_raw))
        df = df_raw.copy()

        init_len = len(df)
        # 1. Trim strings
        for col in ["order_id", "customer_id", "payment_method"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().replace("nan", np.nan).replace("None", np.nan)

        # 2. Deduplicate on order_id
        df = df.dropna(subset=["order_id", "customer_id"])
        df = df.drop_duplicates(subset=["order_id"], keep="first")
        dups_removed = init_len - len(df)

        # 3. Parse order date
        df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
        df = df.dropna(subset=["order_date"])

        # 4. Financial sanity validation
        df["order_value"] = pd.to_numeric(df["order_value"], errors="coerce").fillna(0.0).clip(lower=0.01)
        # Fix negative discounts
        df["discount_amount"] = pd.to_numeric(df["discount_amount"], errors="coerce").fillna(0.0).abs()
        # Discount cannot exceed order value
        df["discount_amount"] = np.minimum(df["discount_amount"], df["order_value"]).round(2)

        # Recalculate net revenue to guarantee mathematical consistency
        df["net_revenue"] = (df["order_value"] - df["discount_amount"]).round(2)

        # COGS validation: must be >= 0, default to 35% of order value if invalid or missing
        df["cogs"] = pd.to_numeric(df["cogs"], errors="coerce")
        invalid_cogs = (df["cogs"].isna()) | (df["cogs"] < 0) | (df["cogs"] > df["order_value"])
        df.loc[invalid_cogs, "cogs"] = (df.loc[invalid_cogs, "order_value"] * 0.35).round(2)

        # Recalculate gross profit
        df["gross_profit"] = (df["net_revenue"] - df["cogs"]).round(2)

        # Categoricals
        df["payment_method"] = df["payment_method"].fillna("Credit Card")

        self.audit_report["customer_orders"] = {
            "initial_rows": init_len,
            "final_rows": len(df),
            "duplicates_removed": dups_removed,
            "negative_discount_fixed": int((df_raw.get("discount_amount", 0) < 0).sum()) if "discount_amount" in df_raw else 0,
        }
        logger.info("Finished cleaning customer_orders (clean rows: %d)", len(df))
        return df

    def run_pipeline(
        self,
        camp_raw_path: Optional[str] = None,
        leads_raw_path: Optional[str] = None,
        orders_raw_path: Optional[str] = None,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Execute end-to-end data cleaning pipeline and save processed artifacts."""
        p_camp = Path(camp_raw_path or self.raw_dir / "campaign_spend_raw.csv")
        p_leads = Path(leads_raw_path or self.raw_dir / "customer_leads_raw.csv")
        p_orders = Path(orders_raw_path or self.raw_dir / "customer_orders_raw.csv")

        if not (p_camp.exists() and p_leads.exists() and p_orders.exists()):
            raise FileNotFoundError(f"Raw CSV files missing in {self.raw_dir}. Run data_loader first.")

        df_camp_raw = pd.read_csv(p_camp)
        df_leads_raw = pd.read_csv(p_leads)
        df_orders_raw = pd.read_csv(p_orders)

        df_camp_clean = self.clean_campaign_spend(df_camp_raw)
        df_leads_clean = self.clean_customer_leads(df_leads_raw)
        df_orders_clean = self.clean_customer_orders(df_orders_raw)

        # Save processed CSVs
        df_camp_clean.to_csv(self.processed_dir / "campaign_spend_clean.csv", index=False)
        df_leads_clean.to_csv(self.processed_dir / "customer_leads_clean.csv", index=False)
        df_orders_clean.to_csv(self.processed_dir / "customer_orders_clean.csv", index=False)

        logger.info("All cleaned datasets saved to %s", self.processed_dir)
        return df_camp_clean, df_leads_clean, df_orders_clean


if __name__ == "__main__":
    cleaner = DataCleaner()
    cleaner.run_pipeline()
    print("Data Cleaning Audit Report:")
    for table, metrics in cleaner.audit_report.items():
        print(f"  {table}: {metrics}")
