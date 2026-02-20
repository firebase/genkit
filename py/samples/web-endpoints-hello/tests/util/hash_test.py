# Copyright 2026 Google LLC
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

"""Tests for src.util.hash — cache key generation.

Run with::

    cd py/samples/web-endpoints-hello
    uv run pytest tests/util/hash_test.py -v
"""

from pydantic import BaseModel

from src.util.hash import make_cache_key


class FakeInput(BaseModel):
    """Pydantic model used as test input for cache key generation."""

    text: str = "hello"
    lang: str = "en"


class TestMakeCacheKey:
    """Tests for `make_cache_key`."""

    def test_pydantic_model_key(self) -> None:
        """Verify a Pydantic model produces a namespaced key."""
        key = make_cache_key("flow_a", FakeInput(text="hi", lang="fr"))
        assert key.startswith("flow_a:")
        assert len(key) > len("flow_a:")

    def test_same_input_same_key(self) -> None:
        """Verify identical inputs produce the same key."""
        inp = FakeInput(text="hi", lang="fr")
        assert make_cache_key("f", inp) == make_cache_key("f", inp)

    def test_different_input_different_key(self) -> None:
        """Verify different inputs produce different keys."""
        k1 = make_cache_key("f", FakeInput(text="a"))
        k2 = make_cache_key("f", FakeInput(text="b"))
        assert k1 != k2

    def test_different_namespace_different_key(self) -> None:
        """Verify different namespaces produce different keys."""
        inp = FakeInput()
        assert make_cache_key("a", inp) != make_cache_key("b", inp)

    def test_dict_input(self) -> None:
        """Verify dict input produces a namespaced key."""
        key = make_cache_key("f", {"text": "hi"})
        assert key.startswith("f:")

    def test_string_input(self) -> None:
        """Verify string input produces a namespaced key."""
        key = make_cache_key("f", "hello")
        assert key.startswith("f:")

    def test_deterministic_dict(self) -> None:
        """Verify dict key order does not affect the cache key."""
        k1 = make_cache_key("f", {"b": 2, "a": 1})
        k2 = make_cache_key("f", {"a": 1, "b": 2})
        assert k1 == k2

    def test_deterministic_string(self) -> None:
        """Verify identical strings produce identical keys."""
        k1 = make_cache_key("f", "hello world")
        k2 = make_cache_key("f", "hello world")
        assert k1 == k2

    def test_key_format(self) -> None:
        """Verify key format is ``namespace:hex``."""
        key = make_cache_key("translate", FakeInput())
        namespace, hex_part = key.split(":", 1)
        assert namespace == "translate"
        assert len(hex_part) == 16
        int(hex_part, 16)  # should not raise — valid hex

    def test_pydantic_excludes_none(self) -> None:
        """Verify None fields do not affect the cache key."""

        class OptInput(BaseModel):
            text: str = "hello"
            extra: str | None = None

        k_none = make_cache_key("f", OptInput())
        k_set = make_cache_key("f", OptInput(extra="value"))
        assert k_none != k_set

    def test_empty_namespace(self) -> None:
        """Verify empty namespace still produces a colon-prefixed key."""
        key = make_cache_key("", FakeInput())
        assert key.startswith(":")

    def test_empty_string_input(self) -> None:
        """Verify empty string input still produces a namespaced key."""
        key = make_cache_key("f", "")
        assert key.startswith("f:")
        assert len(key) > len("f:")
