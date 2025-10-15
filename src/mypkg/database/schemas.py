#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=W0102,E0712,C0103,R0903

""" MYPKG """

__updated__ = "2024-10-31 19:57:57"


from marshmallow import Schema, fields, validate, validates, ValidationError


class Template_Schema(Schema):
    name = fields.Str(required=True)
    description = fields.Str(required=True)
    content = fields.Str(required=True)


class TemplateId_Schema(Schema):
    templateid = fields.Str(
        required=True,
        validate=validate.Regexp(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", error="Invalid UUID4 format"
        ),
    )
