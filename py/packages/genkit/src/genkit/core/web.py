# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""HTTP header definitions and functionality for the Genkit framework."""

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
