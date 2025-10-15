#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=W0102,E0712,C0103,R0903

""" MYPKG """

__updated__ = "2024-10-31 21:12:58"

import json
from flask import request, jsonify, g
from functools import wraps
from time import time
from database.redis_conn_pool import get_redis

# from utils.logger import logger
# from utils.trace import get_trace_id


def exectime(func):
    """
    Measure the time taken to execute a function.
    """

    # -- Initialization of function trace id
    # trace_id = get_trace_id()

    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        reportedtime = end_time - start_time
        print(reportedtime)
        # logger.info("%s | %s | Exec timee: %s:.2f seconds", request.method, trace_id, reportedtime)
        return result

    return wrapper


from functools import wraps
from flask import request, jsonify
from database.redis_conn_pool import get_redis
from utils.trace import get_trace_id
from utils.logger import logger


def headerapikey(func):
    """
    Check the header for the API key.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        trace_id = get_trace_id()
        try:
            apikey = request.headers.get("X-API-KEY")

            # -- Check if there is the X-API-KEY header
            if not apikey:
                logger.warning("%s | %s | API key is missing", request.method, trace_id)
                return jsonify({"error": "API key is missing"}), 400  # Bad Request

            # -- Check if the API key exists in the hash and retrieve the associated metadata
            redis_conn = get_redis()
            user_info = redis_conn.hget("sec_apikeys", apikey)

            # -- Check if the API key exists in the Redis set
            if user_info:
                logger.info("%s | %s | API key is valid", request.method, trace_id)
                return func(*args, **kwargs)
            else:
                logger.warning(
                    "%s | %s | Unauthorized access attempt with API key: %s", request.method, trace_id, apikey
                )
                return jsonify({"error": "Unauthorized"}), 401  # Unauthorized

        except Exception as error:
            logger.error("%s | %s | Exception found; %s", request.method, trace_id, error)
            return jsonify({"wrapper_error": str(error)}), 500  # Internal Server Error

    return wrapper


def format_error_message(error_dict):
    """
    Parse the internal error messages and format them for using them in a JSON response.
    """

    # -- Initialization of function trace id
    # trace_id = get_trace_id()

    error_messages = []
    for field, errors in error_dict.items():
        if isinstance(errors, dict):
            for index, field_errors in errors.items():
                for error, error_value in field_errors.items():
                    error_value_string = ", ".join(error_value) if isinstance(error_value, list) else error_value
                    error_messages.append(f"{field}[{index}].{error}: {error_value_string}")
        else:
            for error in errors:
                error_value_string = ", ".join(error) if isinstance(error, list) else error
                error_messages.append(f"{field}: {error_value_string}")

    # logger.info("%s | %s | Errors reported; %s", request.method, trace_id, json.dumps(error_messages))

    return "\n".join(error_messages)
