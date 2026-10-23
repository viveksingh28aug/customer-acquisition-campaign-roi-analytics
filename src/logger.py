"""Structured logging configuration for Marketing Analytics Suite."""
import logging
import os
import sys
from pathlib import Path


def setup_logger(
    name: str = "marketing_analytics",
    log_file: str = "logs/app.log",
    level: str = "INFO",
) -> logging.Logger:
    """Configure and return a structured logger with console and file output.

    Args:
        name: Name of the logger.
        log_file: Path to destination log file.
        level: Minimum log level string ('DEBUG', 'INFO', 'WARNING', 'ERROR').

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers if already configured
    if logger.handlers:
        return logger

    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s:%(funcName)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler
    try:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as exc:
        logger.warning("Could not set up file handler for %s: %s", log_file, exc)

    return logger


logger = setup_logger()
