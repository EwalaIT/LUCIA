#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=W0102,E0712,C0103,R0903

""" MYPKG """

__updated__ = "2024-10-31 21:37:15"


import json
import psycopg2
import redis.exceptions
from datetime import datetime
from flask import Flask, request, g
from config import Config
from api.templates import get_templates, add_templates, get_template_id, update_template_id, delete_template_id
from api.security import authenticate, authorize
from database.pg_conn_pool import init_db, close_db
from database.redis_conn_pool import init_redis, close_redis
from utils.helpers import headerapikey
from utils.logger import logger, setup_logging
from utils.rate_limiter import init_limiter, rate_limit
from utils.trace import generate_trace_id, get_trace_id


# -- Custom encoder for JSON serialization
class CustomJSONEncoder(json.JSONEncoder):
    """
    This class is used to serialize datetime objects to ISO format
    """

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


# -- Create the Flask application
app = Flask(__name__)
app.config.from_object(Config)
app.json.sort_keys = False

# -- Set up the application context
with app.app_context():
    # Initialize Redis connection pool and attach limiter
    init_redis()
    init_limiter(app)

# -- This custom encoder is used for JSON formatting of dates in ISO format
app.json_encoder = CustomJSONEncoder

# -- Call setup_logging early so that all logs are captured now onwards
setup_logging()


###############################################################################
#
# ROUTES FOR API ENDPOINTS
#
###############################################################################

# Template routes
app.add_url_rule("/templates", "get_templates", get_templates, methods=["GET"])
app.add_url_rule("/templates", "add_templates", add_templates, methods=["POST"])
app.add_url_rule("/templates/<template_id>", "get_template_id", get_template_id, methods=["GET"])
app.add_url_rule("/templates/<template_id>", "update_template_id", update_template_id, methods=["PUT"])
app.add_url_rule("/templates/<template_id>", "delete_template_id", delete_template_id, methods=["DELETE"])

# Security routes
app.add_url_rule("/sec/authn", "authn", authenticate, methods=["POST"])
app.add_url_rule("/sec/authz", "authz", authorize, methods=["POST"])


###############################################################################
#
# REQUEST HANDLERS
#
###############################################################################


@app.before_request
def before_request():
    """
    This function handles HTTP request as it arrives to the API
    """
    # -- Step 1: Initialization of Trace ID
    generate_trace_id()
    trace_id = get_trace_id()
    logger.info("%s | %s | New request on %s", request.method, trace_id, request.path)

    # -- Step 1: Redis initialization, if not initialized already
    if not hasattr(g, "redis_pool"):
        init_redis()
    logger.info("%s | %s | Redis Conn Pool obtained", request.method, trace_id)

    # -- Step 2: Connect to the Postgres database pool, if not connected
    if not hasattr(g, "db_pool"):
        try:
            init_db()
        except psycopg2.OperationalError:
            logger.error("%s | %s | Connection to PGSQL failed", request.method, trace_id)
            exit(1)
    logger.info("%s | %s | PGSQL Conn Pool obtained", request.method, trace_id)


@app.after_request
def after_request(response):
    """
    This function handles HTTP response before send it back to client
    """
    # -- Log the request completion
    logger.info(
        "%s | %s | Completed request on %s",
        request.method,
        get_trace_id(),
        request.path,
    )
    logger.info(
        "%s | %s | Operation status was %s",
        request.method,
        get_trace_id(),
        response.status,
    )
    return response


@app.teardown_appcontext
def shutdown_session(exception=None):
    """
    Close the database connection at the end of each request
    """

    # -- Initialization of function trace id
    trace_id = get_trace_id()

    request_method = "TDAC"

    # -- Step 1: Postgres
    try:
        close_db()
        logger.info("%s | %s | PGSQL Conn Pool closed", request_method, trace_id)
    except psycopg2.OperationalError as error:
        logger.warning("%s | %s | Closing connection to Postgres failed: %s", request_method, trace_id, str(error))
        # exit(1)

    # -- Step 2: Redis
    try:
        close_redis()
        logger.info("%s | %s | Redis Conn Pool closed", request_method, trace_id)
    except redis.exceptions.ConnectionError as error:
        logger.warning("%s | %s | Closing connection to Redis failed: %s", request_method, trace_id, str(error))


###############################################################################
#
# ENDPOINT FOR HEALTH CHECK
#
###############################################################################


@app.route("/")
@headerapikey
def get_index():
    """
    Main index
    """

    # -- Initialization of function trace id
    trace_id = get_trace_id()

    response = {"message": "Index HETEOAS", "links": []}
    logger.info("%s | %s | Index edpoint called", request.method, trace_id)

    return response


@app.route("/status")
@rate_limit(5)
def get_status():
    """
    Status endpoint
    """
    # -- Initialization of function trace id
    trace_id = get_trace_id()
    logger.info("%s | %s | Status edpoint called", request.method, trace_id)

    return "OK"


###############################################################################
#
# APPLICATION ENTRY POINT
#
###############################################################################


if __name__ == "__main__":
    app.run(host=app.config["FLASK_HOST"], port=app.config["FLASK_PORT"], debug=app.config["FLASK_DEBUG"])
