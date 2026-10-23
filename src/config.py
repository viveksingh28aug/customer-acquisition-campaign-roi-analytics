"""Configuration loader reading environment variables and YAML settings."""
import os
from pathlib import Path
from typing import Any, Dict
import yaml
from dotenv import load_dotenv

# Load .env if present
load_dotenv()


class AppConfig:
    """Singleton-style configuration provider."""

    def __init__(self, config_file: str = "config/config.yaml"):
        self.config_path = Path(config_file)
        self.data: Dict[str, Any] = self._load_yaml()

    def _load_yaml(self) -> Dict[str, Any]:
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    @property
    def database_url(self) -> str:
        """Returns PostgreSQL connection string if configured in env, else empty."""
        return os.getenv("DATABASE_URL", "").strip()

    @property
    def fallback_db_path(self) -> str:
        """Path for local DuckDB/SQLite fallback."""
        return self.data.get("database", {}).get(
            "fallback_sqlite_path", "data/marketing_analytics.duckdb"
        )

    @property
    def raw_data_dir(self) -> Path:
        return Path(self.data.get("paths", {}).get("raw_data_dir", "data/raw"))

    @property
    def processed_data_dir(self) -> Path:
        return Path(self.data.get("paths", {}).get("processed_data_dir", "data/processed"))

    @property
    def sql_dir(self) -> Path:
        return Path(self.data.get("paths", {}).get("sql_dir", "sql"))

    @property
    def assumptions(self) -> Dict[str, Any]:
        return self.data.get("assumptions", {})

    @property
    def kpi_targets(self) -> Dict[str, float]:
        return self.data.get("analytics", {}).get("kpi_targets", {})


# Default instance
config = AppConfig()
