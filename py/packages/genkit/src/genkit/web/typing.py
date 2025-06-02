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

    HAVE_LITESTAR = True
except ImportError:
    HAVE_LITESTAR = False


try:
    import starlette

    # Import the actual application class
    from starlette.applications import Starlette as StarletteApp

    HAVE_STARLETTE = True
except ImportError:
    HAVE_STARLETTE = False


# NOTE: Please ask these frameworks to standardize on asgiref.
if HAVE_LITESTAR and HAVE_STARLETTE:
    Application = atyping.ASGIApplication | litestar.Litestar | StarletteApp
    HTTPScope = atyping.HTTPScope | litestar.HTTPScope | starlette.types.Scope
    LifespanScope = atyping.LifespanScope | litestar.LifespanScope | starlette.types.Scope
    Receive = atyping.ASGIReceiveCallable | litestar.Receive | starlette.types.Scope
    Scope = atyping.Scope | litestar.Scope | starlette.types.Scope
    Send = atyping.ASGISendCallable | litestar.Send | starlette.types.Send
elif HAVE_LITESTAR:
    Application = atyping.ASGIApplication | litestar.Litestar
    HTTPScope = atyping.HTTPScope | litestar.HTTPScope
    LifespanScope = atyping.LifespanScope | litestar.LifespanScope
    Receive = atyping.ASGIReceiveCallable | litestar.Receive
    Scope = atyping.Scope | litestar.Scope
    Send = atyping.ASGISendCallable | litestar.Send
elif HAVE_STARLETTE:
    Application = StarletteApp | atyping.ASGIApplication
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
# type LifespanHandler = Callable[[LifespanScope, Receive, Send], Awaitable[None]]
LifespanHandler = Callable[[LifespanScope, Receive, Send], Awaitable[None]]
