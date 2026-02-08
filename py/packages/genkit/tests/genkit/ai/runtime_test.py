#!/usr/bin/env python3
#
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tests for genkit.ai._runtime module."""

import json
import tempfile
from pathlib import Path

from genkit.ai._runtime import RuntimeManager, _create_and_write_runtime_file
from genkit.ai._server import ServerSpec


def test_create_runtime_file_without_name() -> None:
    """Runtime file omits 'name' when not provided."""
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        spec = ServerSpec(port=3100)

        file_path = _create_and_write_runtime_file(runtime_dir, spec)

        with file_path.open(encoding='utf-8') as f:
            data = json.load(f)

        if 'name' in data:
            msg = f'Runtime file should not contain "name" when not provided, got {data!r}'
            raise AssertionError(msg)

        if data['reflectionApiSpecVersion'] != 1:
            msg = f'reflectionApiSpecVersion = {data["reflectionApiSpecVersion"]!r}, want 1'
            raise AssertionError(msg)


def test_create_runtime_file_with_name() -> None:
    """Runtime file includes 'name' when provided, matching JS SDK parity."""
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        spec = ServerSpec(port=3100)

        file_path = _create_and_write_runtime_file(runtime_dir, spec, name='my-app')

        with file_path.open(encoding='utf-8') as f:
            data = json.load(f)

        if data.get('name') != 'my-app':
            msg = f'Runtime file name = {data.get("name")!r}, want "my-app"'
            raise AssertionError(msg)


def test_runtime_manager_passes_name() -> None:
    """RuntimeManager correctly passes name to the runtime file writer."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec = ServerSpec(port=3100)
        manager = RuntimeManager(spec, runtime_dir=tmpdir, name='manager-test')

        file_path = manager.write_runtime_file()

        with file_path.open(encoding='utf-8') as f:
            data = json.load(f)

        if data.get('name') != 'manager-test':
            msg = f'Runtime file name = {data.get("name")!r}, want "manager-test"'
            raise AssertionError(msg)

        manager.cleanup()
