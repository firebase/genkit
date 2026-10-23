# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# SPDX-License-Identifier: Apache-2.0

"""Tests for serving over this process's stdin and stdout, with no MCP client in the way."""

import asyncio
import io
import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest
import structlog
from genkit_mcp import create_mcp_server

from genkit import Genkit

SERVER = Path(__file__).with_name('genkit_server.py')

# Every await on the child process is bounded by this, so a lifecycle regression
# fails the suite rather than hanging it. There is no global pytest timeout.
LIMIT = 60

CALL_ID = 2


def requests(tool: str) -> list[dict[str, Any]]:
    """Open a session and call one tool, as a client would write them to stdin."""
    return [
        {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'initialize',
            'params': {
                'protocolVersion': '2025-06-18',
                'capabilities': {},
                'clientInfo': {'name': 'stdio-test', 'version': '1.0.0'},
            },
        },
        {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
        {'jsonrpc': '2.0', 'id': CALL_ID, 'method': 'tools/call', 'params': {'name': tool, 'arguments': {}}},
    ]


async def call_over_stdio(tool: str, **env: str) -> tuple[list[str], str]:
    """Run the fixture app as a child, call one tool, and return its stdout lines and stderr."""
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(SERVER),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, 'GENKIT_LOG': 'debug', **env},
    )
    assert process.stdin is not None
    assert process.stdout is not None

    for request in requests(tool):
        process.stdin.write((json.dumps(request) + '\n').encode())
    await asyncio.wait_for(process.stdin.drain(), timeout=LIMIT)

    lines = await asyncio.wait_for(_read_until_call_answered(process.stdout), timeout=LIMIT)
    process.stdin.close()
    rest, stderr = await asyncio.wait_for(process.communicate(), timeout=LIMIT)
    return lines + rest.decode().splitlines(), stderr.decode()


@pytest.mark.asyncio
async def test_stdout_carries_only_json_rpc_once_the_server_is_serving() -> None:
    """Logging while serving goes to stderr, so a debug-level app does not corrupt a frame.

    What the app logs before ``start()`` runs is another matter: stdout is not
    the wire yet and nothing has been redirected, so those lines are on stdout.
    """
    lines, stderr = await call_over_stdio('plain_text')

    wire = lines[_first_json_line(lines) :]
    assert [line for line in wire if _decode(line) is None] == []
    assert 'genkit_server imported' in '\n'.join(lines[: _first_json_line(lines)])
    assert 'serving plain text' not in '\n'.join(lines)
    assert 'serving plain text' in stderr


@pytest.mark.asyncio
async def test_text_outside_ascii_survives_a_server_whose_locale_cannot_encode_it() -> None:
    lines, _ = await call_over_stdio(
        'accented', LC_ALL='C', LANG='C', PYTHONUTF8='0', PYTHONCOERCECLOCALE='0', PYTHONIOENCODING='ascii'
    )

    answer = next(message for line in lines if (message := _decode(line)) and message.get('id') == CALL_ID)
    assert answer['result']['content'] == [{'type': 'text', 'text': 'café 東京'}]


@pytest.mark.asyncio
async def test_redirect_stdout_false_leaves_this_process_stdout_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    """Opting out means an app that already keeps stdout clear keeps its own arrangement."""
    server = create_mcp_server(Genkit(), 'quiet', redirect_stdout=False)
    wire = _stream()
    monkeypatch.setattr(sys, 'stdin', _stream())
    monkeypatch.setattr(sys, 'stdout', wire)

    await asyncio.wait_for(server.start(), timeout=LIMIT)

    assert sys.stdout is wire


@pytest.mark.asyncio
async def test_a_logger_built_before_the_swap_still_follows_it(monkeypatch: pytest.MonkeyPatch) -> None:
    """The whole stdout arrangement rests on this: structlog's default logger defers to sys.stdout.

    Its PrintLogger passes file=None to print rather than capturing a stream,
    so a logger cached before start() runs still lands on the redirected
    stream instead of writing JSON-RPC's channel.
    """
    cached = structlog.get_logger('cached-before-the-swap')
    server = create_mcp_server(Genkit(), 'noisy')
    wire_bytes = _KeptOpen()
    wire = io.TextIOWrapper(wire_bytes, encoding='utf-8')
    stderr = io.StringIO()
    monkeypatch.setattr(sys, 'stdin', _stream())
    monkeypatch.setattr(sys, 'stdout', wire)
    monkeypatch.setattr(sys, 'stderr', stderr)

    await asyncio.wait_for(server.start(), timeout=LIMIT)
    cached.info('after the swap')

    assert 'after the swap' in stderr.getvalue()
    assert b'after the swap' not in wire_bytes.getvalue()


@pytest.mark.asyncio
async def test_text_buffered_before_start_reaches_stdout_ahead_of_the_wire(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unflushed text left in the old stdout would otherwise land between frames whenever it flushed."""
    server = create_mcp_server(Genkit(), 'buffered')
    wire_bytes = _KeptOpen()
    old_stdout = io.TextIOWrapper(wire_bytes, encoding='utf-8')
    old_stdout.write('pending')
    monkeypatch.setattr(sys, 'stdin', _stream())
    monkeypatch.setattr(sys, 'stdout', old_stdout)
    monkeypatch.setattr(sys, 'stderr', io.StringIO())

    await asyncio.wait_for(server.start(), timeout=LIMIT)

    assert wire_bytes.getvalue() == b'pending'


class _KeptOpen(io.BytesIO):
    """Bytes that stay readable after the server's own wrapper closes them."""

    def close(self) -> None:
        pass


def _stream() -> io.TextIOWrapper:
    """A text stream backed by bytes, as a real stdin or stdout is."""
    return io.TextIOWrapper(_KeptOpen(), encoding='utf-8')


async def _read_until_call_answered(stdout: asyncio.StreamReader) -> list[str]:
    """Collect stdout lines up to and including the answer to the tool call."""
    lines: list[str] = []
    while True:
        raw = await stdout.readline()
        if not raw:
            raise AssertionError(f'the server closed stdout without answering: {lines}')
        line = raw.decode().rstrip('\n')
        lines.append(line)
        message = _decode(line)
        if message is not None and message.get('id') == CALL_ID:
            return lines


def _decode(line: str) -> dict[str, Any] | None:
    """Read one stdout line as a JSON-RPC message, or nothing when it is not one."""
    try:
        message = json.loads(line)
    except json.JSONDecodeError:
        return None
    return message if isinstance(message, dict) and message.get('jsonrpc') == '2.0' else None


def _first_json_line(lines: list[str]) -> int:
    """Find where the wire opens, which is the first line the transport wrote."""
    for index, line in enumerate(lines):
        if _decode(line) is not None:
            return index
    raise AssertionError(f'the server wrote no JSON-RPC at all: {lines}')
