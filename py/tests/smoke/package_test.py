"""Smoke tests for package structure."""

# TODO: Replace this with proper imports once we have a proper implementation.
from genkit.ai import package_name as ai_package_name
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
    return n * n


def test_package_names() -> None:
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


def test_square() -> None:
    assert square(2) == 4
    assert square(3) == 9
    assert square(4) == 16
