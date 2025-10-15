#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=W0102,E0712,C0103,R0903

""" MYPKG """

__updated__ = "2024-10-31 20:39:44"


from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from flask import current_app, g


minconn = 1  # Minimum number of connections to keep in the pool
maxconn = 20  # Maximum number of connections to keep in the pool


def init_db():
    """
    Initialize the database connection pool
    """
    g.db_pool = pool.SimpleConnectionPool(
        minconn,
        maxconn,
        user=current_app.config["DB_USER"],
        password=current_app.config["DB_PASS"],
        host=current_app.config["DB_HOST"],
        port=current_app.config["DB_PORT"],
        database=current_app.config["DB_NAME"],
    )


def get_db():
    """
    Get a database connection from the pool
    """
    if "db_conn" not in g:
        g.db_conn = g.db_pool.getconn()
    return g.db_conn


def close_db():
    """
    Close the database connection and return it to the pool
    """
    db_conn = g.pop("db_conn", None)
    if db_conn is not None:
        g.db_pool.putconn(db_conn)


def execute_query(query, params=None, commit=False):
    """
    Execute a SQL query and return a RealDictCursor (a Python dictionary)
    """
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(query, params or ())
        if commit:
            conn.commit()
    except Exception as error:
        conn.rollback()
        raise error
    return cursor


def rollback():
    """
    Rollback the current transaction
    """
    conn = get_db()
    conn.rollback()
    close_db()
