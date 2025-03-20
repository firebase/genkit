# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Type definitions for the web framework."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from asgiref.typing import (
    ASGIApplication as _ASGIApplication,
    ASGIReceiveCallable as _ASGIReceiveCallable,
    ASGISendCallable as _ASGISendCallable,
    HTTPScope as _HTTPScope,
    LifespanScope as _LifespanScope,
    Scope as _Scope,
)

from genkit.web.enums import HTTPMethod

# Aliases for the ASGI types to make them portable and readable.
type Application = _ASGIApplication
type HTTPScope = _HTTPScope
type LifespanScope = _LifespanScope
type Receive = _ASGIReceiveCallable
type Scope = _Scope
type Send = _ASGISendCallable

# Type aliases for the web framework.
type HTTPHandler = Callable[[HTTPScope, Receive, Send], Awaitable[None]]
type LifespanHandler = Callable[[LifespanScope, Receive, Send], Awaitable[None]]
type QueryParams = dict[str, list[str]]


@dataclass
class Route:
    """API route definition for the reflection server."""

    method: HTTPMethod
    """HTTP method (GET, POST, etc.)"""

    path: str
    """URL path for the route"""

    handler: HTTPHandler
    """Handler function for the route"""


type Routes = list[Route]
