"""Internal loop-local cache for async resources."""

import asyncio
import threading
import weakref
from collections.abc import Callable
from typing import TypeVar

T = TypeVar('T')


def _loop_local_client(factory: Callable[[], T]) -> Callable[[], T]:
    """Return a getter that caches one resource instance per event loop."""
    by_loop: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, T] = weakref.WeakKeyDictionary()
    lock = threading.Lock()

    def _get() -> T:
        loop = asyncio.get_running_loop()
        with lock:
            existing = by_loop.get(loop)
            if existing is not None:
                return existing
            created = factory()
            by_loop[loop] = created
            return created

    return _get
