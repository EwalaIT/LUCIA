#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=W0102,E0712,C0103,R0903

""" MYPKG """

__updated__ = "2024-10-31 20:39:43"


from database.pg_conn_pool import execute_query


###############################################################################
#
# Model: Templates
#
###############################################################################


# CRUD operations
# C - Create
def add_new_template(template_data):
    """
    Add a new template to the database.
    """

    try:
        query = f"""
            INSERT INTO templates (name, description, content)
            VALUES (%s, %s, %s)
            RETURNING templateid;
        """
        cursor = execute_query(
            query,
            params=(template_data["name"], template_data["description"], template_data["content"]),
            commit=True,
        )
        return cursor.rowcount
    except Exception as error:
        print(error)  # debug only
        return None


# CRUD operations
# R - Read
def get_all_templates(limit=10, offset=0):
<<<<<<< HEAD
    """
    Retrieve all templates from the database.
    """

    query = "SELECT * FROM templates ORDER BY tidx ASC LIMIT %s OFFSET %s;"
    cursor = execute_query(query, (limit, offset))
    session_data = cursor.fetchall()
    response = session_data
=======
    """Retrieve all templates from the database, with pagination support"""
    query = "SELECT * FROM user_sessions ORDER BY tidx ASC LIMIT %s OFFSET %s;"
    cursor = execute_query(query, (limit, offset))
    session_data = cursor.fetchall()
    #
    # Do some processing here with the session_data
    #
    response = {
        "data": session_data,
        "limit": limit,
        "offset": offset
    }
>>>>>>> a5689c47c4ebf4e39f9aa6c519b2d291a4292204
    return response


# CRUD operations
# R - Read
def get_by_templateid(template_id):
    """
    Retrieve a template from the database.
    """

    try:
        query = f"SELECT * FROM templates WHERE templateid = '{template_id}' ORDER BY tidx ASC;"
        cursor = execute_query(query)
        session_data = cursor.fetchone()
        response = session_data
        return response
    except Exception as error:
        print(error)  # debug only
        return None


# CRUD operations
# U - Update
def update_template(template_id, template_data):
    """
    Update a template in the database.
    """

    # Build the query with parameterized placeholders
    query = """
    UPDATE templates SET
        name = %s,
        description = %s,
        content = %s,
        modified = NOW()
    WHERE templateid = %s;
    """

    # Parameters for the query
    params = (
        template_data["name"],
        template_data["description"],
        template_data["content"],
        template_id,
    )

    # Execute the query
    cursor = execute_query(query, params=params, commit=True)
    return cursor.rowcount


# CRUD operations
# D - Delete
def delete_template(template_id):
    """
    Delete a template from the database.
    """

    # Build the query
    query = f"DELETE FROM templates WHERE templateid = '{template_id}';"
    # Execute the query
    cursor = execute_query(query, commit=True)
    return cursor.rowcount
