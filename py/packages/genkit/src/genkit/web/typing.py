# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
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

from asgiref import typing as atyping

try:
    import litestar  # type: ignore[misc]
    import litestar.types  # type: ignore[misc]
except ImportError:
    litestar = None

try:
    import starlette.types  # Explicit import for ty type checker

    # Import the actual application class
    from starlette.applications import Starlette as StarletteApp
except ImportError:
    starlette = None  # type: ignore[assignment]
    StarletteApp = None  # type: ignore[assignment,misc]


# NOTE: Please ask these frameworks to standardize on asgiref.
if litestar is not None and starlette is not None:
    Application = atyping.ASGIApplication | litestar.Litestar | StarletteApp  # pyright: ignore[reportOperatorIssue]
    HTTPScope = atyping.HTTPScope | litestar.types.HTTPScope | starlette.types.Scope
    LifespanScope = atyping.LifespanScope | litestar.types.LifeSpanScope | starlette.types.Scope
    Receive = atyping.ASGIReceiveCallable | litestar.types.Receive | starlette.types.Scope
    Scope = atyping.Scope | litestar.types.Scope | starlette.types.Scope
    Send = atyping.ASGISendCallable | litestar.types.Send | starlette.types.Send
elif litestar is not None:
    Application = atyping.ASGIApplication | litestar.Litestar
    HTTPScope = atyping.HTTPScope | litestar.types.HTTPScope
    LifespanScope = atyping.LifespanScope | litestar.types.LifeSpanScope
    Receive = atyping.ASGIReceiveCallable | litestar.types.Receive
    Scope = atyping.Scope | litestar.types.Scope
    Send = atyping.ASGISendCallable | litestar.types.Send
elif starlette is not None:
    Application = StarletteApp | atyping.ASGIApplication  # pyright: ignore[reportOptionalOperand]
    HTTPScope = atyping.HTTPScope | starlette.types.Scope
    LifespanScope = atyping.LifespanScope | starlette.types.Scope
    Receive = atyping.ASGIReceiveCallable | starlette.types.Receive
    Scope = atyping.Scope | starlette.types.Scope
    Send = atyping.ASGISendCallable | starlette.types.Send
else:
    Application = atyping.ASGIApplication
    HTTPScope = atyping.HTTPScope
    LifespanScope = atyping.LifespanScope
    Receive = atyping.ASGIReceiveCallable
    Scope = atyping.Scope
    Send = atyping.ASGISendCallable

# Type aliases for the web framework.
LifespanHandler = Callable[[LifespanScope, Receive, Send], Awaitable[None]]

# Type alias for Starlette/Litestar on_startup/on_shutdown handlers (0-argument async functions)
# This is distinct from LifespanHandler which is the full ASGI lifespan protocol handler.
StartupHandler = Callable[[], Awaitable[None]]
