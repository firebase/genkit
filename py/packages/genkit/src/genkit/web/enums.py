# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""HTTP header definitions and functionality."""

from enum import StrEnum


class HTTPHeader(StrEnum):
    """HTTP header names used by the Genkit framework.

    Attributes:
        CONTENT_LENGTH: Standard HTTP header for specifying the content length.
        CONTENT_TYPE: Standard HTTP header for specifying the media type.
        X_GENKIT_VERSION: Custom header for tracking genkit version.
    """

    CONTENT_LENGTH = 'Content-Length'
    CONTENT_TYPE = 'Content-Type'
    X_GENKIT_VERSION = 'X-Genkit-Version'


class HTTPMethod(StrEnum):
    """HTTP method names used by the Genkit framework.

    Attributes:
        CONNECT: Establishing a tunnel.
        DELETE: Deleting data.
        GET: Retrieving data.
        HEAD: Retrieving metadata about the resource.
        OPTIONS: Retrieving metadata about the resource.
        PATCH: Updating data.
        POST: Submitting data.
        PUT: Updating data.
        TRACE: Tracing the request.
    """

    CONNECT = 'CONNECT'
    DELETE = 'DELETE'
    GET = 'GET'
    HEAD = 'HEAD'
    OPTIONS = 'OPTIONS'
    PATCH = 'PATCH'
    POST = 'POST'
    PUT = 'PUT'
    TRACE = 'TRACE'


class ContentType(StrEnum):
    """HTTP content type names used by the Genkit framework.

    Attributes:
        APPLICATION_JSON: JSON content type.
    """

    APPLICATION_JSON = 'application/json'
    TEXT_PLAIN = 'text/plain'
