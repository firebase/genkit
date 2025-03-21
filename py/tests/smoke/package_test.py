# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Smoke tests for package structure."""

# TODO: Replace this with proper imports once we have a proper implementation.
from dotpromptz import package_name as dotpromptz_package_name

from genkit.blocks import package_name as ai_package_name
from genkit.core import package_name as core_package_name
from genkit.plugins.chroma import package_name as chroma_package_name
from genkit.plugins.firebase import package_name as firebase_package_name
from genkit.plugins.google_ai import package_name as google_ai_package_name
from genkit.plugins.google_ai.models import (
    package_name as google_ai_models_package_name,
)
from genkit.plugins.google_cloud import (
    package_name as google_cloud_package_name,
)
from genkit.plugins.ollama import package_name as ollama_package_name
from genkit.plugins.pinecone import package_name as pinecone_package_name
from genkit.plugins.vertex_ai import package_name as vertex_ai_package_name
from genkit.plugins.vertex_ai.models import (
    package_name as vertex_ai_models_package_name,
)


def square(n: int | float) -> int | float:
    """Calculates the square of a number.

    Args:
        n: The number to square.

    Returns:
        The square of n.
    """
    return n * n


def test_package_names() -> None:
    """A test that ensure that the package imports work correctly.

    This test verifies that the package imports work correctly from the
    end-user perspective.
    """
    assert ai_package_name() == 'genkit.ai'
    assert chroma_package_name() == 'genkit.plugins.chroma'
    assert core_package_name() == 'genkit.core'
    assert firebase_package_name() == 'genkit.plugins.firebase'
    assert google_ai_models_package_name() == 'genkit.plugins.google_ai.models'
    assert google_ai_package_name() == 'genkit.plugins.google_ai'
    assert google_cloud_package_name() == 'genkit.plugins.google_cloud'
    assert ollama_package_name() == 'genkit.plugins.ollama'
    assert pinecone_package_name() == 'genkit.plugins.pinecone'
    assert vertex_ai_models_package_name() == 'genkit.plugins.vertex_ai.models'
    assert vertex_ai_package_name() == 'genkit.plugins.vertex_ai'
    assert dotpromptz_package_name() == 'dotpromptz'


def test_square() -> None:
    """Tests whether the square function works correctly."""
    assert square(2) == 4
    assert square(3) == 9
    assert square(4) == 16
