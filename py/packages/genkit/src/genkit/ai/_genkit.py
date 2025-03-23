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

"""Genkit API module for managing AI flows.

This module provides a wrapper around the different implementations of the
Genkit API, automatically selecting the appropriate implementation based on
whether the code is running synchronously or asynchronously.
"""

import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

import structlog

from genkit.aio import GenkitAsync
from genkit.core.action import ActionKind
from genkit.core.registry import Registry
from genkit.sync import GenkitSync

F = TypeVar('F', bound=Callable[..., Any])


logger = structlog.get_logger()


class GenkitExperimental:
    """Veneer class for the Genkit API.

    This class serves as a factory for both synchronous and asynchronous
    implementations of Genkit. The appropriate implementation is selected based
    on the context in which it is used when the flow is decorated.

    Should one need to access the underlying synchronous or asynchronous
    implementation, the following properties can be used:

    - `ai`: Returns the asynchronous implementation of Genkit.
    - `sync`: Returns the synchronous implementation of Genkit.
    """

    def __init__(self) -> None:
        """Initializes Genkit."""
        self._registry = Registry()
        self._async_impl = GenkitAsync()
        self._sync_impl = GenkitSync()

    @property
    def ai(self) -> GenkitAsync:
        """Returns the asynchronous implementation of Genkit."""
        return self._async_impl

    @property
    def sync(self) -> GenkitSync:
        """Returns the synchronous implementation of Genkit."""
        return self._sync_impl

    def flow(self, name: str | None = None) -> Callable[[F], F]:
        """Returns a decorator that can be used to create a Genkit flow.

        This decorator automatically detects whether the decorated function is a
        coroutine function and injects the appropriate Genkit implementation as
        the first positional argument ('ai') to the function.

        Returns:
            A decorator function that wraps the provided flow function.
        """

        def decorator(func: F) -> F:
            """Decorator to wrap a flow function with appropriate context.

            Args:
                func: The flow function to be decorated.

            Returns:
                A wrapped function that injects the appropriate Genkit
                implementation.
            """
            flow_name = name if name is not None else func.__name__
            # action = self._registry.register_action(
            #    name=flow_name,
            #    kind=ActionKind.FLOW,
            #    fn=func,
            #    span_metadata={'genkit:metadata:flow:name': flow_name},
            # )
            # logger.debug('Registered action', action=action.name)

            if inspect.iscoroutinefunction(func):
                logger.debug('Registering async flow', name=flow_name)

                @wraps(func)
                async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                    """Wrapper for async functions."""
                    result = func(self._async_impl, *args, **kwargs)
                    return await result

                return cast(F, async_wrapper)
            else:
                logger.debug('Registering sync flow', name=flow_name)

                @wraps(func)
                def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                    """Wrapper for sync functions."""
                    return func(self._sync_impl, *args, **kwargs)

                return cast(F, sync_wrapper)

        return decorator
