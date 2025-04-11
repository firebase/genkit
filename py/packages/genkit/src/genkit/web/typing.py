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
from typing import Union

from asgiref import typing as atyping

try:
    import litestar

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
    # type Application = atyping.ASGIApplication | litestar.Litestar | starlette.Starlette
    Application = Union[atyping.ASGIApplication, litestar.Litestar, StarletteApp]
    # type HTTPScope = atyping.HTTPScope | litestar.HTTPScope | starlette.HTTPScope
    HTTPScope = Union[atyping.HTTPScope, litestar.HTTPScope, starlette.types.Scope]
    # type LifespanScope = atyping.LifespanScope | litestar.LifespanScope | starlette.LifespanScope
    LifespanScope = Union[atyping.LifespanScope, litestar.LifespanScope, starlette.types.Scope]
    # type Receive = atyping.ASGIReceiveCallable | litestar.Receive | starlette.Receive
    Receive = Union[atyping.ASGIReceiveCallable, litestar.Receive, starlette.types.Receive]
    # type Scope = atyping.Scope | litestar.Scope | starlette.Scope
    Scope = Union[atyping.Scope, litestar.Scope, starlette.types.Scope]
    # type Send = atyping.ASGISendCallable | litestar.Send | starlette.Send
    Send = Union[atyping.ASGISendCallable, litestar.Send, starlette.types.Send]
elif HAVE_LITESTAR:
    # type Application = atyping.ASGIApplication | litestar.Litestar
    Application = Union[atyping.ASGIApplication, litestar.Litestar]
    # type HTTPScope = atyping.HTTPScope | litestar.HTTPScope
    HTTPScope = Union[atyping.HTTPScope, litestar.HTTPScope]
    # type LifespanScope = atyping.LifespanScope | litestar.LifespanScope
    LifespanScope = Union[atyping.LifespanScope, litestar.LifespanScope]
    # type Receive = atyping.ASGIReceiveCallable | litestar.Receive
    Receive = Union[atyping.ASGIReceiveCallable, litestar.Receive]
    # type Scope = atyping.Scope | litestar.Scope
    Scope = Union[atyping.Scope, litestar.Scope]
    # type Send = atyping.ASGISendCallable | litestar.Send
    Send = Union[atyping.ASGISendCallable, litestar.Send]
elif HAVE_STARLETTE:
    # type Application = starlette.Starlette | atyping.ASGIApplication
    Application = Union[StarletteApp, atyping.ASGIApplication]
    # type HTTPScope = atyping.HTTPScope | starlette.HTTPScope
    HTTPScope = Union[atyping.HTTPScope, starlette.types.Scope]
    # type LifespanScope = atyping.LifespanScope | starlette.LifespanScope
    LifespanScope = Union[atyping.LifespanScope, starlette.types.Scope]
    # type Receive = atyping.ASGIReceiveCallable | starlette.Receive
    Receive = Union[atyping.ASGIReceiveCallable, starlette.types.Receive]
    # type Scope = atyping.Scope | starlette.Scope
    Scope = Union[atyping.Scope, starlette.types.Scope]
    # type Send = atyping.ASGISendCallable | starlette.Send
    Send = Union[atyping.ASGISendCallable, starlette.types.Send]
else:
    # type Application = atyping.ASGIApplication
    Application = atyping.ASGIApplication
    # type HTTPScope = atyping.HTTPScope
    HTTPScope = atyping.HTTPScope
    # type LifespanScope = atyping.LifespanScope
    LifespanScope = atyping.LifespanScope
    # type Receive = atyping.ASGIReceiveCallable
    Receive = atyping.ASGIReceiveCallable
    # type Scope = atyping.Scope
    Scope = atyping.Scope
    # type Send = atyping.ASGISendCallable
    Send = atyping.ASGISendCallable

# Type aliases for the web framework.
# type LifespanHandler = Callable[[LifespanScope, Receive, Send], Awaitable[None]]
LifespanHandler = Callable[[LifespanScope, Receive, Send], Awaitable[None]]
