# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tests for the codec module."""

import pytest
from genkit.core.codec import dump_json
from pydantic import BaseModel


def test_dump_json_basic():
    """Test basic JSON serialization."""
    # Test dictionary
    assert dump_json({'a': 1, 'b': 'test'}) == '{"a": 1, "b": "test"}'

    # Test list
    assert dump_json([1, 2, 3]) == '[1, 2, 3]'

    # Test nested structures
    assert (
        dump_json({'a': [1, 2], 'b': {'c': 3}})
        == '{"a": [1, 2], "b": {"c": 3}}'
    )


def test_dump_json_special_types():
    """Test JSON serialization of special Python types."""
    # Test None
    assert dump_json(None) == 'null'

    # Test boolean
    assert dump_json(True) == 'true'
    assert dump_json(False) == 'false'


def test_dump_json_numbers():
    """Test JSON serialization of different number types."""
    # Test integers
    assert dump_json(42) == '42'

    # Test floats
    assert dump_json(3.14) == '3.14'

    # Test scientific notation
    assert dump_json(1e-10) == '1e-10'


def test_dump_json_pydantic():
    """Test JSON serialization of Pydantic models."""

    class MyModel(BaseModel):
        a: int
        b: str

    assert dump_json(MyModel(a=1, b='test')) == '{"a":1,"b":"test"}'
