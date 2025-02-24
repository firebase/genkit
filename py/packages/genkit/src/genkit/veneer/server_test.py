#!/usr/bin/env python3
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

import json
import os
import tempfile
from unittest import mock

from genkit.veneer import server


def test_server_spec() -> None:
    assert (
        server.ServerSpec(scheme='http', host='localhost', port=3100).url
        == 'http://localhost:3100'
    )

    # Test with different schemes and hosts
    assert (
        server.ServerSpec(scheme='https', host='example.com', port=8080).url
        == 'https://example.com:8080'
    )

    # Test with default values
    spec = server.ServerSpec(port=5000)
    assert spec.scheme == 'http'
    assert spec.host == 'localhost'
    assert spec.url == 'http://localhost:5000'


def test_create_runtime() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        spec = server.ServerSpec(port=3100)

        # Test runtime file creation
        runtime_path = server.create_runtime(temp_dir, spec)
        assert runtime_path.exists()

        # Verify file content
        content = json.loads(runtime_path.read_text(encoding='utf-8'))
        assert isinstance(content, dict)
        assert 'id' in content
        assert 'pid' in content
        assert content['reflectionServerUrl'] == 'http://localhost:3100'
        assert 'timestamp' in content

        # Test directory creation
        new_dir = os.path.join(temp_dir, 'new_dir')
        runtime_path = server.create_runtime(new_dir, spec)
        assert os.path.exists(new_dir)
        assert runtime_path.exists()


def test_is_dev_environment() -> None:
    # Test when GENKIT_ENV is not set
    with mock.patch.dict(os.environ, clear=True):
        assert not server.is_dev_environment()

    # Test when GENKIT_ENV is set to 'dev'
    with mock.patch.dict(os.environ, {'GENKIT_ENV': 'dev'}):
        assert server.is_dev_environment()

    # Test when GENKIT_ENV is set to something else
    with mock.patch.dict(os.environ, {'GENKIT_ENV': 'prod'}):
        assert not server.is_dev_environment()
