#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=W0102,E0712,C0103,R0903,C0301

""" MYPKG """

__updated__ = "2024-10-31 21:36:55"


from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import Config

# Initialize Limiter without specifying Redis connection pool at this point
limiter = Limiter(
    key_func=get_remote_address, storage_uri=f"redis://:{Config.REDIS_PASS}@{Config.REDIS_HOST}:{Config.REDIS_PORT}"
)


def rate_limit(requests_per_minute: int = 0):
    """
    Convert integer rate limit to the 'requests per minute' format.
    """
    if requests_per_minute == 0:
        # Use the default from config if not provided
        requests_per_minute = Config.DEFAULT_RATE_LIMIT

    return limiter.limit(f"{requests_per_minute} per minute")


def init_limiter(app):
    """
    Initialize the limiter with the Flask app.
    """
    limiter.init_app(app)
