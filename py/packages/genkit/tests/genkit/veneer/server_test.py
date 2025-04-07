#!/usr/bin/env python3
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tests for the server module."""

import json
import os
import tempfile

from genkit.ai._server import ServerSpec, create_runtime


def test_server_spec() -> None:
    """Test the ServerSpec class.

    Verifies that the ServerSpec class correctly generates URLs and
    handles different schemes, hosts, and ports.
    """
    assert ServerSpec(scheme='http', host='localhost', port=3100).url == 'http://localhost:3100'

    # Test with different schemes and hosts
    assert ServerSpec(scheme='https', host='example.com', port=8080).url == 'https://example.com:8080'

    # Test with default values
    spec = ServerSpec(port=5000)
    assert spec.scheme == 'http'
    assert spec.host == 'localhost'
    assert spec.url == 'http://localhost:5000'


def test_create_runtime() -> None:
    """Test the create_runtime function.

    Verifies that the create_runtime function correctly creates and
    manages runtime metadata files, including cleanup on exit.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        spec = ServerSpec(port=3100)

        # Test runtime file creation
        runtime_path = create_runtime(temp_dir, spec)
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
        runtime_path = create_runtime(new_dir, spec)
        assert os.path.exists(new_dir)
        assert runtime_path.exists()
