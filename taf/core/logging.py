"""Logging configuration for the Twilio Agentic Framework."""

import logging
import sys


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Configure logging for TAF framework.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    # Get the root logger for TAF
    logger = logging.getLogger("taf")

    # Clear any existing handlers to avoid duplicates
    logger.handlers.clear()

    # Set log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    # Create formatter with default format
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Prevent propagation to root logger to avoid duplicate messages
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Logger name (typically __name__ from the calling module)

    Returns:
        Logger instance
    """
    # Create child logger under the taf namespace
    return logging.getLogger(f"taf.{name}")
