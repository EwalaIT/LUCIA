#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=W0102,E0712,C0103,R0903,C0301

""" MYPKG """

__updated__ = "2024-10-31 13:13:53"

import logging
import sys
from config import Config

# --
# -- Architecture Decision Records (ADR)
# --
# -- ADR1: Avoid Dependency Injection
# -- ADR2: Avoid Lazy Loading
# -- ADR3: Avoid Multiple Loggers
# -- ADR4: Avoid Root Logger Propagation
# -- ADR5: Avoid Hardcoded Configuration
# --
# -- We decided to use this global logger to avoid passing it around in the code
# -- This way, we can easily change the logging configuration in one place and
# -- all modules will use the updated configuration. This means no lazy loading
# -- of the logger in each module, which could lead to multiple loggers being
# -- created and used in the application, and also avoids dependency injection,
# -- which would require passing the logger to every function that needs it.
# --


class CustomFormatter(logging.Formatter):
    """
    Custom Formatter to handle cases when 'trace_id' is missing in the log record.
    """

    def format(self, record):
        # Add default trace_id if it's missing
        if not hasattr(record, "trace_id"):
            record.trace_id = "N/A"  # Default trace_id if not set
        return super().format(record)


# -- Create a globally available logger
logger = logging.getLogger(__name__)


def setup_logging():
    """
    Set up application-wide logging to STDOUT.
    Ensure no duplicate handlers are added.
    """
    if not logger.hasHandlers():
        handler = logging.StreamHandler(sys.stdout)
        formatter = CustomFormatter("%(asctime)s | %(levelname)s | %(module)s:%(funcName)s:%(lineno)d | %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.setLevel(Config.LOG_LEVEL)
    logging.getLogger("werkzeug").disabled = True  # Disable Flask's built-in logger
    logger.propagate = False  # Avoid root logger propagation

    return logger
