"""Structured logging configuration for the chatbot application."""
import logging
import sys
from pathlib import Path
from datetime import datetime
import json
from typing import Any, Dict


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra_data"):
            log_data["data"] = record.extra_data

        return json.dumps(log_data)


class ColoredConsoleFormatter(logging.Formatter):
    """Custom formatter for colored console output."""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    BOLD = '\033[1m'

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors for console."""
        color = self.COLORS.get(record.levelname, self.RESET)

        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')

        # Build log message
        log_parts = [
            f"{color}{self.BOLD}[{record.levelname}]{self.RESET}",
            f"{timestamp}",
            f"{color}{record.name}{self.RESET}",
            f"- {record.getMessage()}"
        ]

        # Add location info for errors
        if record.levelno >= logging.ERROR:
            log_parts.append(f"({record.filename}:{record.lineno})")

        # Add extra data if present
        if hasattr(record, "extra_data"):
            log_parts.append(f"\n  └─ Data: {json.dumps(record.extra_data, indent=2)}")

        # Add exception info
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            log_parts.append(f"\n  └─ Exception:\n{exc_text}")

        return " ".join(log_parts)


def setup_logging(
    log_level: str = "INFO",
    log_to_file: bool = True,
    log_to_console: bool = True
) -> logging.Logger:
    """
    Setup structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file
        log_to_console: Whether to log to console

    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    logs_dir = Path(__file__).parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Create logger
    logger = logging.getLogger("chatbot")
    logger.setLevel(getattr(logging, log_level.upper()))
    logger.handlers.clear()  # Clear existing handlers

    # Console handler with colored output
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(ColoredConsoleFormatter())
        logger.addHandler(console_handler)

    # File handler with JSON structured logging
    if log_to_file:
        # Create log file with timestamp
        log_filename = f"chatbot_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(logs_dir / log_filename)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(StructuredFormatter())
        logger.addHandler(file_handler)

        # Also create a latest.log symlink/copy
        latest_log = logs_dir / "latest.log"
        latest_handler = logging.FileHandler(latest_log, mode='w')
        latest_handler.setLevel(logging.DEBUG)
        latest_handler.setFormatter(StructuredFormatter())
        logger.addHandler(latest_handler)

    return logger


def get_logger(name: str = "chatbot") -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter):
    """Custom logger adapter for adding extra context."""

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Process log message with extra context."""
        extra = kwargs.get("extra", {})
        if "extra_data" in extra:
            # Already has extra_data, merge it
            if hasattr(self, "extra") and "extra_data" in self.extra:
                extra["extra_data"] = {**self.extra["extra_data"], **extra["extra_data"]}
        elif hasattr(self, "extra") and "extra_data" in self.extra:
            # Use adapter's extra_data
            extra["extra_data"] = self.extra["extra_data"]

        kwargs["extra"] = extra
        return msg, kwargs


# Initialize default logger
default_logger = setup_logging()
