"""
Structured logging configuration.

Provides JSON-formatted logging suitable for production monitoring and audit trails.
Does not handle log aggregation, retention policies, or external log shipping.
"""

import logging
import sys
from typing import Any

from app.core.config import settings


def setup_logging() -> None:
    """Configures application-wide logging."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    if settings.log_format == "json":
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logging.basicConfig(
            level=log_level,
            handlers=[handler],
            force=True
        )
    else:
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            force=True
        )


class JsonFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    
    Produces JSON logs suitable for production monitoring and log aggregation systems.
    Includes request context, tenant information, and error details.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Formats log record as JSON with structured fields."""
        import json
        import traceback
        
        log_data: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add exception information if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add extra fields from record (structured logging)
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        
        # Extract common context fields
        context_fields = [
            "tenant_id", "invoice_uuid", "invoice_number", "environment",
            "attempt", "max_retries", "status_code", "error", "retry_delay"
        ]
        for field in context_fields:
            if hasattr(record, field):
                log_data[field] = getattr(record, field)
        
        # Add function name and line number for debugging
        log_data["function"] = record.funcName
        log_data["line"] = record.lineno
        
        # Add module path
        log_data["module"] = record.module
        
        return json.dumps(log_data, ensure_ascii=False)

