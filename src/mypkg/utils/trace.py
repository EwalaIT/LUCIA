#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=W0102,E0712,C0103,R0903,C0301

""" MYPKG """

__updated__ = "2024-10-31 13:19:09"


import uuid
from flask import g


def generate_trace_id():
    """
    Generate and store a UUID for request tracing.
    Store trace ID in Flask's global context.
    """
    trace_id = str(uuid.uuid4())
    g.trace_id = trace_id
    return trace_id


def get_trace_id():
    """
    Retrieve the current trace ID.
    Return trace ID or None if not set.
    """
    return getattr(g, "trace_id", None)
