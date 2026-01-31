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

"""Building blocks for the Genkit framework.

This package provides the core building blocks for AI applications, including
models, prompts, embeddings, retrievers, and tools. These blocks are composed
to create intelligent applications.

Overview:
    The blocks package contains the fundamental components used to build
    Genkit applications. Each block type represents a specific AI capability
    that can be composed together.

Key Modules:
    ┌─────────────────────────────────────────────────────────────────────────┐
    │ Module            │ Description                                         │
    ├───────────────────┼─────────────────────────────────────────────────────┤
    │ model             │ Model registration and invocation (ai.generate)     │
    │ prompt            │ Prompt templates and ExecutablePrompt               │
    │ embedding         │ Text embeddings (ai.embed)                          │
    │ retriever         │ Document retrieval for RAG (ai.retrieve)            │
    │ document          │ Document model for content + metadata               │
    │ tools             │ Tool context and interrupt handling                 │
    │ evaluator         │ Evaluation functions for quality assessment         │
    │ reranker          │ Document reranking for improved retrieval           │
    └───────────────────┴─────────────────────────────────────────────────────┘

Usage:
    Most users interact with blocks via the ``Genkit`` class methods:

    ```python
    from genkit import Genkit

    ai = Genkit(...)

    # Model block (via ai.generate)
    response = await ai.generate(prompt='Hello!')

    # Prompt block (via ai.prompt)
    prompt = ai.prompt('greet', source='...', model='...')

    # Embedding block (via ai.embed)
    embeddings = await ai.embed(content='text')

    # Retriever block (via ai.retrieve)
    docs = await ai.retrieve(retriever='my_retriever', query='...')
    ```

See Also:
    - genkit.ai: Main Genkit class
    - genkit.types: Type definitions
"""


def package_name() -> str:
    """Get the fully qualified package name.

    Returns:
        The string 'genkit.blocks', which is the fully qualified package name.
    """
    return 'genkit.blocks'


__all__ = ['package_name']
