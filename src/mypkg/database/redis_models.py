#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=W0102,E0712,C0103,R0903

""" MYPKG """

__updated__ = "2024-10-31 13:49:33"


from flask import request, jsonify
from database.redis_conn_pool import (
    record_exists_redis,
    execute_command_redis,
    read_record_redis,
    update_record_redis,
    delete_record_redis,
)


###############################################################################
#
# Model: Redis records
#
###############################################################################


# CRUD operations
# C - Create
def add_record(key):
    value = request.json
    if record_exists_redis(key):
        return jsonify({"error": "Record already exists"}), 400
    execute_command_redis("SET", key, value)  # SET or HSET or other to define
    return jsonify({"message": "Record created"}), 201


# CRUD operations
# R - Read
def get_record(key):
    if not record_exists_redis(key):
        return jsonify({"error": "Record not found"}), 404
    record = read_record_redis(key)
    return jsonify(record)


# CRUD operations
# U - Update
def modify_record(key):
    value = request.json
    if not record_exists_redis(key):
        return jsonify({"error": "Record not found"}), 404
    update_record_redis(key, value)
    return jsonify({"message": "Record updated"}), 200


# CRUD operations
# D - Delete
def remove_record(key):
    if not record_exists_redis(key):
        return jsonify({"error": "Record not found"}), 404
    delete_record_redis(key)
    return jsonify({"message": "Record deleted"}), 200
