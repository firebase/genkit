# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Type annotations to smooth over some rough edges.

Not all ASGI frameworks agree on the type definitions
and we plan to support as many as we can. Currently,
we support:

- asgiref (Django)
- fastapi
- litestar
- starlette
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from asgiref import typing as atyping

from genkit.web.enums import HTTPMethod

try:
    import litestar

    HAVE_LITESTAR = True
except ImportError:
    HAVE_LITESTAR = False


try:
    import starlette

    HAVE_STARLETTE = True
except ImportError:
    HAVE_STARLETTE = False


# NOTE: Please ask these frameworks to standardize on asgiref.
if HAVE_LITESTAR and HAVE_STARLETTE:
    type Application = (
        atyping.ASGIApplication | litestar.Litestar | starlette.Starlette
    )
    type HTTPScope = (
        atyping.HTTPScope | litestar.HTTPScope | starlette.HTTPScope
    )
    type LifespanScope = (
        atyping.LifespanScope | litestar.LifespanScope | starlette.LifespanScope
    )
    type Receive = (
        atyping.ASGIReceiveCallable | litestar.Receive | starlette.Receive
    )
    type Scope = atyping.Scope | litestar.Scope | starlette.Scope
    type Send = atyping.ASGISendCallable | litestar.Send | starlette.Send
elif HAVE_LITESTAR:
    type Application = atyping.ASGIApplication | litestar.Litestar
    type HTTPScope = atyping.HTTPScope | litestar.HTTPScope
    type LifespanScope = atyping.LifespanScope | litestar.LifespanScope
    type Receive = atyping.ASGIReceiveCallable | litestar.Receive
    type Scope = atyping.Scope | litestar.Scope
    type Send = atyping.ASGISendCallable | litestar.Send
elif HAVE_STARLETTE:
    type Application = starlette.Starlette | atyping.ASGIApplication
    type HTTPScope = atyping.HTTPScope | starlette.HTTPScope
    type LifespanScope = atyping.LifespanScope | starlette.LifespanScope
    type Receive = atyping.ASGIReceiveCallable | starlette.Receive
    type Scope = atyping.Scope | starlette.Scope
    type Send = atyping.ASGISendCallable | starlette.Send
else:
    type Application = atyping.ASGIApplication
    type HTTPScope = atyping.HTTPScope
    type LifespanScope = atyping.LifespanScope
    type Receive = atyping.ASGIReceiveCallable
    type Scope = atyping.Scope
    type Send = atyping.ASGISendCallable

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
