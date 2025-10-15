#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=W0102,E0712,C0103,R0903

""" MYPKG """

__updated__ = "2024-07-05 10:43:22"


import json
import pytest
from mypkg.app import get_status, app


def test_get_index():
    client = app.test_client()
    headers = {"X-API-KEY": "e8b21d5c-6658-481b-abe2-fd990fb7c8a6"}
    response = client.get("/", headers=headers)
    assert response.status_code == 200
    assert response.content_type == "application/json"
    data = json.loads(response.data)
    assert data["message"] == "Index HETEOAS"


def test_get_status():
    """Test the get_status function"""
    expected = "OK"
    response = get_status()
    assert response == expected


if __name__ == "__main__":
    pytest.main()
