#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=W0102,E0712,C0103,R0903

""" MYPKG """

__updated__ = "2024-10-31 14:11:48"

import json
import redis
from flask import current_app, g


def init_redis():
    """
    Initialize the Redis connection pool
    """
    g.redis_pool = redis.ConnectionPool(
        host=current_app.config["REDIS_HOST"],
        port=current_app.config["REDIS_PORT"],
        password=current_app.config["REDIS_PASS"],
        db=current_app.config["REDIS_DB"],
        max_connections=int(current_app.config.get("REDIS_MAX_CONN", 20)),
    )


def get_redis():
    """
    Get a Redis connection from the pool
    """
    if "redis_conn" not in g:
        g.redis_conn = redis.Redis(connection_pool=g.redis_pool)
    return g.redis_conn


def close_redis():
    """
    Close the Redis connection
    """
    redis_conn = g.pop("redis_conn", None)
    if redis_conn is not None:
        redis_conn.connection_pool.disconnect()


def create_record_redis(key, value):
    """
    Create a new record in Redis
    """
    conn = get_redis()
    value_json = json.dumps(value)
    result = conn.set(key, value_json)
    return result


def read_record_redis(key):
    """
    Read a record from Redis
    """
    conn = get_redis()
    value_json = conn.get(key)
    if value_json is None:
        return None
    value = json.loads(value_json)
    return value


def update_record_redis(key, value):
    """
    Update an existing record in Redis
    """
    conn = get_redis()
    value_json = json.dumps(value)
    result = conn.set(key, value_json)
    return result


def delete_record_redis(key):
    """
    Delete a record from Redis
    """
    conn = get_redis()
    result = conn.delete(key)
    return result


def record_exists_redis(key):
    """
    Check if a record exists in Redis
    """
    conn = get_redis()
    return conn.exists(key) > 0


def execute_command_redis(command, *args, **kwargs):
    """
    Execute a Redis command
    """
    conn = get_redis()
    try:
        result = conn.execute_command(command, *args, **kwargs)
    except Exception as error:
        raise error
    return result


def execute_pipeline_redis(commands):
    """
    Execute multiple Redis commands in a pipeline
    """
    conn = get_redis()
    pipeline = conn.pipeline()
    try:
        for command, args, kwargs in commands:
            pipeline.execute_command(command, *args, **kwargs)
        result = pipeline.execute()
    except Exception as error:
        pipeline.reset()
        raise error
    return result
