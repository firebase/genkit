import pytest

from genkit.plugins.dev_local_vectorstore import DevLocalVectorStore
from genkit.plugins.google_genai import VertexEmbeddingModels
from unittest import mock
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.fixture
@patch('ollama.AsyncClient')
def vectorstore_plugin_instance(ollama_async_client):
    """Common instance of ollama plugin."""
    return DevLocalVectorStore(
            name='menu-items',
            embedder=VertexEmbeddingModels.TEXT_EMBEDDING_004_ENG,
            embedder_options={'taskType': 'RETRIEVAL_DOCUMENT'},
        )
