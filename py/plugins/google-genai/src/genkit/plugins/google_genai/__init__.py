# Copyright 2025 Google LLC
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


"""Google GenAI plugin for Genkit.

This plugin provides integration with Google's AI services, including
Google AI (Gemini API) and Vertex AI. It registers Gemini models and
embedders for use with the Genkit framework.

Overview:
    The Google GenAI plugin supports two backends:
    - **GoogleAI**: Direct Gemini API access (requires GEMINI_API_KEY)
    - **VertexAI**: Google Cloud Vertex AI platform access

    Both plugins register Gemini models and text embedding models as
    Genkit actions, enabling generation and embedding operations.

Supported Models:
    ┌─────────────────────────────────────────────────────────────────────────┐
    │ Plugin     │ Models                                                     │
    ├────────────┼─────────────────────────────────────────────────────────────┤
    │ GoogleAI   │ gemini-2.0-flash, gemini-2.5-flash, gemini-2.5-pro, etc.  │
    │ VertexAI   │ Same Gemini models + imagen-4.0-generate-001               │
    └────────────┴─────────────────────────────────────────────────────────────┘

Key Components:
    ┌─────────────────────────────────────────────────────────────────────────┐
    │ Component             │ Purpose                                         │
    ├───────────────────────┼─────────────────────────────────────────────────┤
    │ GoogleAI              │ Plugin for Gemini API (api_key auth)            │
    │ VertexAI              │ Plugin for Vertex AI (GCP project auth)         │
    │ GeminiConfigSchema    │ Configuration schema for Gemini models          │
    │ GeminiEmbeddingModels │ Enum of available GoogleAI embedding models     │
    │ VertexEmbeddingModels │ Enum of available VertexAI embedding models     │
    │ EmbeddingTaskType     │ Task types for embeddings (CLUSTERING, etc.)    │
    └───────────────────────┴─────────────────────────────────────────────────┘

Example:
    Using GoogleAI (Gemini API):

    ```python
    from genkit import Genkit
    from genkit.plugins.google_genai import GoogleAI

    # Uses GEMINI_API_KEY env var or pass api_key explicitly
    ai = Genkit(plugins=[GoogleAI()], model='googleai/gemini-2.0-flash')

    response = await ai.generate(prompt='Hello, world!')
    print(response.text)

    # Embeddings
    embeddings = await ai.embed(
        embedder='googleai/gemini-embedding-001',
        content='Hello, world!',
    )
    ```

    Using VertexAI (Google Cloud):

    ```python
    from genkit import Genkit
    from genkit.plugins.google_genai import VertexAI

    # Uses default GCP credentials; optionally pass project/location
    ai = Genkit(
        plugins=[VertexAI(project='my-project', location='us-central1')],
        model='vertexai/gemini-2.0-flash',
    )

    response = await ai.generate(prompt='Hello, world!')
    print(response.text)

    # Image generation with Imagen
    response = await ai.generate(
        model='vertexai/imagen-4.0-generate-001',
        prompt='A beautiful sunset over mountains',
    )
    ```

Caveats:
    - GoogleAI requires GEMINI_API_KEY environment variable
    - VertexAI uses Google Cloud credentials (ADC or explicit)
    - Model names are prefixed with 'googleai/' or 'vertexai/'

See Also:
    - Gemini API: https://ai.google.dev/
    - Vertex AI: https://cloud.google.com/vertex-ai
    - Model catalog: https://genkit.dev/docs/models
"""

from genkit.plugins.google_genai.google import (
    GoogleAI,
    VertexAI,
)
from genkit.plugins.google_genai.models.embedder import (
    EmbeddingTaskType,
    GeminiEmbeddingModels,
    VertexEmbeddingModels,
)
from genkit.plugins.google_genai.models.gemini import (
    GeminiConfigSchema,
    GeminiImageConfigSchema,
    GeminiTtsConfigSchema,
    GoogleAIGeminiVersion,
    VertexAIGeminiVersion,
)
from genkit.plugins.google_genai.models.imagen import ImagenVersion
from genkit.plugins.google_genai.models.lyria import LyriaConfig, LyriaVersion
from genkit.plugins.google_genai.models.veo import VeoConfig, VeoVersion


def package_name() -> str:
    """Get the package name for the Vertex AI plugin.

    Returns:
        The fully qualified package name as a string.
    """
    return 'genkit.plugins.google_genai'


__all__ = [
    package_name.__name__,
    GoogleAI.__name__,
    VertexAI.__name__,
    GeminiEmbeddingModels.__name__,
    VertexEmbeddingModels.__name__,
    GoogleAIGeminiVersion.__name__,
    VertexAIGeminiVersion.__name__,
    EmbeddingTaskType.__name__,
    GeminiConfigSchema.__name__,
    GeminiImageConfigSchema.__name__,
    GeminiTtsConfigSchema.__name__,
    ImagenVersion.__name__,
    VeoVersion.__name__,
    VeoConfig.__name__,
    LyriaVersion.__name__,
    LyriaConfig.__name__,
]
