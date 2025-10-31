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

"""Embedding actions."""

from collections.abc import Callable
from typing import Any, TypedDict, Union, TYPE_CHECKING

from genkit.core.action.types import ActionKind
from genkit.core.action import ActionMetadata,Action
from genkit.core.schema import to_json_schema
from genkit.core.typing import EmbedRequest, EmbedResponse,Embedding, DocumentData
from genkit.core.registry import Registry

# type EmbedderFn = Callable[[EmbedRequest], EmbedResponse]
EmbedderFn = Callable[[EmbedRequest], EmbedResponse]

class EmbedderOptions(TypedDict):
    """Options for defining an embedder."""
    name:str
    config_schema: Any  | None
    info: dict[str, Any] | None

class EmbedderParams(TypedDict):
    """Parameters for embedding a single piece of content."""
    embedder: 'EmbedderArgument' # Must be one of : str, EmbedderAction,or EmbedderReference
    content: Union[str, DocumentData] # Must be string or DocumentData
    metadata: dict[str, Any] | None # Optional metadata dict
    options: Any | None # Optional options

class EmbedManyParams(TypedDict):
    """Parameters for embedding multiple pieces of content."""
    embedder: 'EmbedderArgument'
    content: list[Union[str, DocumentData]]
    metadata: dict[str, Any] | None
    options: Any | None

class EmbedderReference(TypedDict):
    """Reference to an embedder with configuration."""
    name: str
    config_schema: Any | None
    info: dict[str, Any] | None
    config: dict[str, Any] | None
    version: str | None

class EmbedderReferenceOptions(TypedDict):
    """Options for creating an embedder reference."""
    name: str
    config_schema: Any | None
    info: dict[str, Any] | None
    config: dict[str, Any] | None
    version: str | None
    namespace: str | None

# Union type for embedder arguments
EmbedderArgument = Union[str, 'EmbedderAction', EmbedderReference]

# Type alias for embedder action
if TYPE_CHECKING:
    EmbedderAction = Action
else:
    EmbedderAction = Any

class ResolvedEmbedder(TypedDict):
    """Resolved embedder with action, config, and version."""
    embedder_action: EmbedderAction
    config: dict[str, Any] | None
    version: str | None

def embedder_action_metadata(
    name: str,
    info: dict[str, Any] | None = None,
    config_schema: Any | None = None,
) -> ActionMetadata:
    """Generates an ActionMetadata for embedders."""
    info = info if info is not None else {}
    return ActionMetadata(
        kind=ActionKind.EMBEDDER,
        name=name,
        input_json_schema=to_json_schema(EmbedRequest),
        output_json_schema=to_json_schema(EmbedResponse),
        metadata={'embedder': {**info, 'customOptions': to_json_schema(config_schema) if config_schema else None}},
    )


def embedder(
    options: EmbedderOptions,
    runner: EmbedderFn,
) -> EmbedderAction:
    """Creates embedder model for the provided EmbedderFn model implementation.
    Unlike define_embedder this function does not register the embedder in the registry."""
     # Create metadata
    embedder_meta: dict[str, Any] = {}
    if 'embedder' not in embedder_meta:
        embedder_meta['embedder'] = {}

    if options.get('config_schema'):
        embedder_meta['embedder']['customOptions'] = to_json_schema(options['config_schema'])

    if options.get('info'):
        embedder_meta['embedder'].update(options['info'])

    return Action(
        kind=ActionKind.EMBEDDER,
        name=options['name'],
        fn=runner,
        metadata=embedder_meta,
    )


def define_embedder(
    registry: 'Registry',
    options: EmbedderOptions,
    runner: EmbedderFn,
) -> EmbedderAction:
    """Creates embedder model for the provided EmbedderFn model implementation.

    This function registers the embedder in the registry."""

    # Create metadata
    embedder_meta: dict[str, Any] = {}
    if 'embedder' not in embedder_meta:
        embedder_meta['embedder'] = {}

    if options.get('config_schema'):
        embedder_meta['embedder']['customOptions'] = to_json_schema(options['config_schema'])

    if options.get('info'):
        embedder_meta['embedder'].update(options['info'])

    # Register the action in the registry
    return registry.register_action(
        kind=ActionKind.EMBEDDER,
        name=options['name'],
        fn=runner,
        metadata=embedder_meta,
    )


async def embed(
    registry: 'Registry',
    params: EmbedderParams,
) -> list[Embedding]:
    """Single embedding function"""
    resolved = await _resolve_embedder(registry, params['embedder'])

    # Convert content to DocumentData if it's a string
    if isinstance(params['content'], str):
        from genkit.blocks.document import Document
        document = Document.from_text(params['content'], params.get('metadata'))
        input_docs = [document.model_dump()]
    else:
        input_docs = [params['content']]

    # Merge options: reference config/version + caller-provided options
    merged_options: dict[str, Any] | None = None
    if resolved.get('version') is not None or resolved.get('config'):
        merged_options = {}
        if resolved.get('version') is not None:
            merged_options['version'] = resolved['version']
        if resolved.get('config'):
            merged_options.update(resolved['config'])
        if params.get('options'):
            merged_options.update(params['options'])
    else:
        merged_options = params.get('options')

    # Create embed request
    request = EmbedRequest(
        input=input_docs,
        options=merged_options,
    )

    response = await resolved['embedder_action'].arun(input=request)
    return response.response.embeddings

async def embed_many(
    registry: 'Registry',
    params: EmbedManyParams,
) -> list[Embedding]:
    """Batch embedding function."""
    resolved = await _resolve_embedder(registry, params['embedder'])

    # Convert content to DocumentData if it's strings
    input_docs = []
    for content in params['content']:
        if isinstance(content, str):
            from genkit.blocks.document import Document
            document = Document.from_text(content, params.get('metadata'))
            input_docs.append(document.model_dump())
        else:
            input_docs.append(content)

    # Merge options: reference config/version + caller-provided options
    merged_options: dict[str, Any] | None = None
    if resolved.get('version') is not None or resolved.get('config'):
        merged_options = {}
        if resolved.get('version') is not None:
            merged_options['version'] = resolved['version']
        if resolved.get('config'):
            merged_options.update(resolved['config'])
        if params.get('options'):
            merged_options.update(params['options'])
    else:
        merged_options = params.get('options')

    # Create embed request
    request = EmbedRequest(
        input=input_docs,
        options=merged_options,
    )

    # Execute the embedder
    response = await resolved['embedder_action'].arun(input=request)
    return response.response.embeddings


def embedder_ref(
    options: EmbedderReferenceOptions,
) -> EmbedderReference:
    """Helper method to configure an EmbedderReference."""

    name = options['name']
    if options.get('namespace') and not name.startswith(options['namespace'] + '/'):
        name = f"{options['namespace']}/{name}"

    return EmbedderReference(
        name=name,
        config_schema=options.get('config_schema'),
        info=options.get('info'),
        config=options.get('config'),
        version=options.get('version'),
    )


async def _resolve_embedder(
    registry: 'Registry',
    embedder_arg: EmbedderArgument,
) -> ResolvedEmbedder:
    """Resolve embedder from registry based on embedder argument"""

    if isinstance(embedder_arg, str):
        # Look up by name in registry
        action = await registry.lookup_action(f"/embedder/{embedder_arg}")
        if action is None:
            raise ValueError(f"Unable to resolve embedder {embedder_arg}")
        return ResolvedEmbedder(
            embedder_action=action,
            config=None,
            version=None,
        )
    elif hasattr(embedder_arg, 'name'):
        # It's an EmbedderAction
        return ResolvedEmbedder(
            embedder_action=embedder_arg,
            config=None,
            version=None,
        )
    elif isinstance(embedder_arg, dict) and 'name' in embedder_arg:
        # It's an EmbedderReference - extract config and version
        ref = embedder_arg
        action = await registry.lookup_action(f"/embedder/{ref['name']}")
        if action is None:
            raise ValueError(f"Unable to resolve embedder {ref['name']}")
        return ResolvedEmbedder(
            embedder_action=action,
            config=ref.get('config'),
            version=ref.get('version'),
        )
    else:
        raise ValueError(f"Failed to resolve embedder {embedder_arg}")
