# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

import asyncio
import threading


class ThreadWithReturnValue(threading.Thread):
    def __init__(
        self,
        group=None,
        target=None,
        name=None,
        args=(),
        kwargs={},
        Verbose=None,
    ):
        threading.Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None

    def run(self):
        if self._target is not None:
            self._return = self._target(*self._args, **self._kwargs)

    def join(self, *args):
        threading.Thread.join(self, *args)
        return self._return


async def sub_task():
    return 'banana'


def task1():
    return asyncio.run(sub_task())


async def main():
    t1 = ThreadWithReturnValue(target=task1)
    t1.start()
    print(t1.join())


asyncio.run(main())


def gen1():
    yield 1
    yield 2
    yield 3


def consume(iter):
    for chunk in iter:
        print(chunk)


consume(x + 1 for x in gen1())
