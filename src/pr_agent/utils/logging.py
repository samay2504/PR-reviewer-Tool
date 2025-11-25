"""Structured logging configuration."""

import logging
import sys
from pathlib import Path
from typing import Optional

import structlog


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    json_logs: bool = False
) -> None:
    """
    Configure structured logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional path to log file
        json_logs: Whether to output JSON formatted logs
    """
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )
    
    # Configure structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if json_logs:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Add file handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        logging.getLogger().addHandler(file_handler)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return structlog.get_logger(name)


# Utility functions for pretty printing (referenced in llm_provider.py)
def print_status(message: str, status: str = "info", icon: Optional[str] = None) -> None:
    """
    Print a status message with color coding.
    
    Args:
        message: Message to print
        status: Status type (info, success, warning, error, progress)
        icon: Optional icon to display
    """
    logger = get_logger("pr_agent.status")
    
    # Map status to log level
    status_map = {
        "info": "info",
        "success": "info",
        "warning": "warning",
        "error": "error",
        "progress": "info"
    }
    
    log_level = status_map.get(status, "info")
    log_func = getattr(logger, log_level)
    
    # Add icon if provided
    display_message = f"{icon} {message}" if icon else message
    log_func(display_message, status=status)


def print_llm_provider_info(provider_name: str, model: str = "") -> None:
    """
    Print LLM provider information.
    
    Args:
        provider_name: Name of the LLM provider
        model: Model name
    """
    logger = get_logger("pr_agent.llm")
    logger.info("LLM provider initialized", provider=provider_name, model=model)


def print_llm_fallback_info(failed_providers: list, active_provider: str) -> None:
    """
    Print LLM fallback information.
    
    Args:
        failed_providers: List of providers that failed
        active_provider: Currently active provider
    """
    logger = get_logger("pr_agent.llm")
    if failed_providers:
        logger.warning(
            "LLM providers failed, using fallback",
            failed_providers=", ".join(failed_providers),
            active_provider=active_provider
        )
