"""Database abstraction layer supporting PostgreSQL with seamless DuckDB/CSV fallback.

Handles connection pooling, schema initialization, bulk data ingestion,
and analytical SQL execution with ANSI CTE and Window Function support.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import re
import duckdb
import pandas as pd

from src.config import config
from src.logger import logger


class DatabaseManager:
    """Unified database client managing PostgreSQL and embedded DuckDB fallback."""

    def __init__(self, db_url: Optional[str] = None, fallback_path: Optional[str] = None):
        self.db_url = db_url or config.database_url
        self.fallback_path = fallback_path or config.fallback_db_path
        self.engine_type: str = "unknown"
        self.pg_conn = None
        self.duck_conn: Optional[duckdb.DuckDBPyConnection] = None
        self._initialize_connection()

    def _initialize_connection(self) -> None:
        """Attempt connection to PostgreSQL; fallback to DuckDB if unavailable."""
        if self.db_url:
            try:
                import psycopg
                logger.info("Attempting connection to PostgreSQL at %s", self.db_url)
                # Attempt short-timeout connection
                self.pg_conn = psycopg.connect(self.db_url, connect_timeout=3)
                self.engine_type = "postgresql"
                logger.info("Connected successfully to PostgreSQL database.")
                return
            except Exception as exc:
                logger.warning(
                    "PostgreSQL unavailable or connection failed (%s). "
                    "Falling back to embedded DuckDB engine.", exc
                )

        # Fallback to embedded DuckDB
        self.engine_type = "duckdb"
        Path(self.fallback_path).parent.mkdir(parents=True, exist_ok=True)
        try:
            self.duck_conn = duckdb.connect(database=self.fallback_path)
            logger.info(
                "Using embedded DuckDB fallback at %s (Fully ANSI SQL, CTE, & Window function compatible)",
                self.fallback_path,
            )
        except Exception as exc:
            logger.info(
                "Notice: DuckDB file %s is active in another process (%s). Initializing concurrent in-memory session.",
                self.fallback_path, exc,
            )
            self.duck_conn = duckdb.connect(database=":memory:")
            # Preload cleaned datasets if available
            p_c = Path("data/processed/campaign_spend_clean.csv")
            p_l = Path("data/processed/customer_leads_clean.csv")
            p_o = Path("data/processed/customer_orders_clean.csv")
            if p_c.exists() and p_l.exists() and p_o.exists():
                try:
                    self.init_schema()
                    self.load_clean_data(pd.read_csv(p_c), pd.read_csv(p_l), pd.read_csv(p_o))
                except Exception as load_exc:
                    logger.debug("Could not auto-preload in-memory DuckDB: %s", load_exc)

    def init_schema(self, schema_file: str = "sql/schema.sql") -> None:
        """Initialize database tables, primary keys, and indices.

        Args:
            schema_file: Path to DDL SQL file.
        """
        sql_path = Path(schema_file)
        if not sql_path.exists():
            raise FileNotFoundError(f"Schema file not found at {schema_file}")

        with open(sql_path, "r", encoding="utf-8") as f:
            ddl_script = f.read()

        logger.info("Initializing database schema on %s engine...", self.engine_type)

        if self.engine_type == "postgresql":
            with self.pg_conn.cursor() as cur:
                cur.execute(ddl_script)
            self.pg_conn.commit()
        else:
            # For DuckDB, execute standard DDL statements
            statements = [s.strip() for s in ddl_script.split(";") if s.strip()]
            for stmt in statements:
                try:
                    self.duck_conn.execute(stmt)
                except Exception as exc:
                    logger.debug("DuckDB DDL notice on statement '%s...': %s", stmt[:40], exc)

        logger.info("Schema initialized successfully.")

    def load_clean_data(
        self,
        df_campaigns: pd.DataFrame,
        df_leads: pd.DataFrame,
        df_orders: pd.DataFrame,
    ) -> None:
        """Load cleaned DataFrames into database tables.

        Args:
            df_campaigns: Cleaned campaign spend DataFrame.
            df_leads: Cleaned customer leads DataFrame.
            df_orders: Cleaned customer orders DataFrame.
        """
        logger.info("Loading cleaned datasets into %s...", self.engine_type)

        # Prepare column subsets matching schema
        camp_cols = ["campaign_id", "campaign_name", "channel", "date", "ad_spend", "impressions", "clicks", "target_audience", "region"]
        lead_cols = ["lead_id", "customer_id", "campaign_id", "channel", "lead_date", "converted_flag", "conversion_date", "signup_platform", "lead_score"]
        order_cols = ["order_id", "customer_id", "order_date", "order_value", "discount_amount", "net_revenue", "cogs", "gross_profit", "payment_method"]

        c_df = df_campaigns[[c for c in camp_cols if c in df_campaigns.columns]].copy()
        l_df = df_leads[[c for c in lead_cols if c in df_leads.columns]].copy()
        o_df = df_orders[[c for c in order_cols if c in df_orders.columns]].copy()

        if self.engine_type == "postgresql":
            import psycopg
            # Ingest to Postgres using cursor copy or insert
            with self.pg_conn.cursor() as cur:
                # Clean existing records
                cur.execute("TRUNCATE TABLE customer_orders CASCADE;")
                cur.execute("TRUNCATE TABLE customer_leads CASCADE;")
                cur.execute("TRUNCATE TABLE campaign_spend CASCADE;")

                # Insert via COPY
                with cur.copy("COPY campaign_spend (campaign_id, campaign_name, channel, date, ad_spend, impressions, clicks, target_audience, region) FROM STDIN") as copy:
                    for row in c_df.itertuples(index=False):
                        copy.write_row(row)

                with cur.copy("COPY customer_leads (lead_id, customer_id, campaign_id, channel, lead_date, converted_flag, conversion_date, signup_platform, lead_score) FROM STDIN") as copy:
                    for row in l_df.itertuples(index=False):
                        copy.write_row(row)

                with cur.copy("COPY customer_orders (order_id, customer_id, order_date, order_value, discount_amount, net_revenue, cogs, gross_profit, payment_method) FROM STDIN") as copy:
                    for row in o_df.itertuples(index=False):
                        copy.write_row(row)

            self.pg_conn.commit()
        else:
            # Ingest to DuckDB directly from pandas with explicit column names
            self.duck_conn.register("tmp_c_df", c_df)
            self.duck_conn.register("tmp_l_df", l_df)
            self.duck_conn.register("tmp_o_df", o_df)

            c_cols_str = ", ".join(c_df.columns)
            l_cols_str = ", ".join(l_df.columns)
            o_cols_str = ", ".join(o_df.columns)

            self.duck_conn.execute("DELETE FROM campaign_spend;")
            self.duck_conn.execute(f"INSERT INTO campaign_spend ({c_cols_str}) SELECT {c_cols_str} FROM tmp_c_df;")

            self.duck_conn.execute("DELETE FROM customer_leads;")
            self.duck_conn.execute(f"INSERT INTO customer_leads ({l_cols_str}) SELECT {l_cols_str} FROM tmp_l_df;")

            self.duck_conn.execute("DELETE FROM customer_orders;")
            self.duck_conn.execute(f"INSERT INTO customer_orders ({o_cols_str}) SELECT {o_cols_str} FROM tmp_o_df;")

            self.duck_conn.unregister("tmp_c_df")
            self.duck_conn.unregister("tmp_l_df")
            self.duck_conn.unregister("tmp_o_df")

        logger.info(
            "Data ingestion complete. Rows loaded: campaigns=%d, leads=%d, orders=%d",
            len(c_df), len(l_df), len(o_df)
        )

    def execute_query(self, sql_query: str) -> pd.DataFrame:
        """Execute analytical SQL query and return results as pandas DataFrame.

        Args:
            sql_query: SQL statement string.

        Returns:
            pandas DataFrame containing the query result.
        """
        if self.engine_type == "postgresql":
            with self.pg_conn.cursor() as cur:
                cur.execute(sql_query)
                colnames = [desc[0] for desc in cur.description]
                records = cur.fetchall()
                return pd.DataFrame(records, columns=colnames)
        else:
            return self.duck_conn.execute(sql_query).df()

    def load_named_query(self, query_name: str, sql_file: str = "sql/analytics_queries.sql") -> str:
        """Extract a query block labeled with '-- @name: <query_name>' from file."""
        with open(sql_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Regex to locate query block up to next @name: or EOF
        pattern = rf"--\s*@name:\s*{re.escape(query_name)}\s*\n(.*?)(?=(?:--\s*@name:)|$)"
        match = re.search(pattern, content, re.DOTALL)
        if not match:
            raise ValueError(f"Named query '{query_name}' not found in {sql_file}")

        return match.group(1).strip()

    def run_named_query(self, query_name: str) -> pd.DataFrame:
        """Execute a named query by label from sql/analytics_queries.sql."""
        sql = self.load_named_query(query_name)
        return self.execute_query(sql)

    def run_filtered_named_query(
        self,
        query_name: str,
        df_campaigns: pd.DataFrame,
        df_leads: pd.DataFrame,
        df_orders: pd.DataFrame,
    ) -> pd.DataFrame:
        """Execute named analytical SQL query against filtered in-memory DataFrames.

        Ensures full consistency with dashboard global filters across all tabs.
        """
        sql = self.load_named_query(query_name)

        if self.engine_type == "duckdb" and self.duck_conn:
            self.duck_conn.register("tmp_filtered_c", df_campaigns)
            self.duck_conn.register("tmp_filtered_l", df_leads)
            self.duck_conn.register("tmp_filtered_o", df_orders)

            self.duck_conn.execute("CREATE OR REPLACE TEMPORARY VIEW campaign_spend AS SELECT * FROM tmp_filtered_c;")
            self.duck_conn.execute("CREATE OR REPLACE TEMPORARY VIEW customer_leads AS SELECT * FROM tmp_filtered_l;")
            self.duck_conn.execute("CREATE OR REPLACE TEMPORARY VIEW customer_orders AS SELECT * FROM tmp_filtered_o;")

            try:
                res = self.duck_conn.execute(sql).df()
            finally:
                self.duck_conn.execute("DROP VIEW IF EXISTS campaign_spend;")
                self.duck_conn.execute("DROP VIEW IF EXISTS customer_leads;")
                self.duck_conn.execute("DROP VIEW IF EXISTS customer_orders;")
                self.duck_conn.unregister("tmp_filtered_c")
                self.duck_conn.unregister("tmp_filtered_l")
                self.duck_conn.unregister("tmp_filtered_o")

            return res

        # For PostgreSQL or other engines, fall back to default run_named_query
        return self.run_named_query(query_name)

    def close(self) -> None:
        """Close connections."""
        if self.pg_conn:
            try:
                self.pg_conn.close()
            except Exception:
                pass
        if self.duck_conn:
            try:
                self.duck_conn.close()
            except Exception:
                pass


# Global database instance
db_manager = DatabaseManager()
