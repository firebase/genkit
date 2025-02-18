# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Contains definitions for custom headers used by the framework and other
related functionality."""

from enum import Enum


class HttpHeader(str, Enum):
    CONTENT_TYPE = 'Content-Type'
    X_GENKIT_VERSION = 'X-Genkit-Version'
