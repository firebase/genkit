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

"""Pokemon glossary - Local RAG with Ollama embeddings.

This sample demonstrates how to create a simple RAG application using
Ollama for local embeddings and generation, creating a Pokemon glossary
without any external API dependencies.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Local RAG           │ RAG that runs on YOUR computer. No cloud needed,   │
    │                     │ your Pokemon data stays private!                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Ollama Embeddings   │ Convert text to numbers using local models.        │
    │                     │ "Pikachu" → [0.2, -0.5, 0.8, ...]                  │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Vector Similarity   │ Find similar items by comparing numbers.           │
    │                     │ "electric mouse" finds Pikachu!                    │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Cosine Similarity   │ Math to compare how similar two things are.        │
    │                     │ 1.0 = identical, 0 = completely different.         │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Pokemon Glossary    │ A searchable database of Pokemon info.             │
    │                     │ Ask questions, get answers from your data.         │
    └─────────────────────┴────────────────────────────────────────────────────┘

Key Features
============
| Feature Description                     | Example Function / Code Snippet     |
|-----------------------------------------|-------------------------------------|
| Local Embedding with Ollama             | `ai.embed_many()`                   |
| Vector Similarity Search                | `find_nearest_pokemons`             |
| RAG (Retrieval Augmented Generation)    | `generate_response`                 |
| Custom Data Structures                  | `PokemonInfo` Pydantic model        |

See README.md for testing instructions.
"""

from math import sqrt
from typing import cast

from pydantic import BaseModel, Field
from rich.traceback import install as install_rich_traceback

from genkit.ai import Genkit
from genkit.core.logging import get_logger
from genkit.plugins.ollama import Ollama, ollama_name
from genkit.plugins.ollama.constants import OllamaAPITypes
from genkit.plugins.ollama.embedders import EmbeddingDefinition
from genkit.plugins.ollama.models import ModelDefinition
from genkit.types import GenerateResponse

install_rich_traceback(show_locals=True, width=120, extra_lines=3)

logger = get_logger(__name__)

EMBEDDER_MODEL = 'nomic-embed-text'
EMBEDDER_DIMENSIONS = 768
GENERATE_MODEL = 'phi4:latest'

ai = Genkit(
    plugins=[
        Ollama(
            models=[
                ModelDefinition(
                    name=GENERATE_MODEL,
                    api_type=cast(OllamaAPITypes, OllamaAPITypes.GENERATE),
                )
            ],
            embedders=[
                EmbeddingDefinition(
                    name=EMBEDDER_MODEL,
                    dimensions=512,
                )
            ],
        )
    ],
)


class PokemonInfo(BaseModel):
    """Information about a Pokemon."""

    name: str
    description: str
    embedding: list[float] | None = None


pokemon_list = [
    PokemonInfo(
        name='Pikachu',
        description='An Electric-type Pokemon known for its strong electric attacks.',
        embedding=None,
    ),
    PokemonInfo(
        name='Charmander',
        description='A Fire-type Pokemon that evolves into the powerful Charizard.',
        embedding=None,
    ),
    PokemonInfo(
        name='Bulbasaur',
        description='A Grass/Poison-type Pokemon that grows into a powerful Venusaur.',
        embedding=None,
    ),
    PokemonInfo(
        name='Squirtle',
        description='A Water-type Pokemon known for its water-based attacks and high defense.',
        embedding=None,
    ),
    PokemonInfo(
        name='Jigglypuff',
        description='A Normal/Fairy-type Pokemon with a hypnotic singing ability.',
        embedding=None,
    ),
]


async def embed_pokemons() -> None:
    """Embed the Pokemons."""
    embeddings = await ai.embed_many(
        embedder=ollama_name(EMBEDDER_MODEL),
        content=[pokemon.description for pokemon in pokemon_list],
    )
    for pokemon, embedding in zip(pokemon_list, embeddings, strict=True):
        pokemon.embedding = embedding.embedding


def find_nearest_pokemons(input_embedding: list[float], top_n: int = 3) -> list[PokemonInfo]:
    """Find the nearest Pokemons.

    Args:
        input_embedding: The embedding of the input.
        top_n: The number of nearest Pokemons to return.

    Returns:
        A list of the nearest Pokemons.
    """
    if any(pokemon.embedding is None for pokemon in pokemon_list):
        raise AttributeError('Some Pokemon are not yet embedded')

    # Calculate distances and keep track of the original Pokemon object.
    pokemon_distances = []
    for pokemon in pokemon_list:
        if pokemon.embedding is not None:
            distance = cosine_distance(input_embedding, pokemon.embedding)
            pokemon_distances.append((distance, pokemon))

    # Sort by distance (the first element of the tuple).
    pokemon_distances.sort(key=lambda item: item[0])

    # Return the top_n PokemonInfo objects from the sorted list.
    return [pokemon for distance, pokemon in pokemon_distances[:top_n]]


def cosine_distance(a: list[float], b: list[float]) -> float:
    """Calculate the cosine distance between two vectors.

    Args:
        a: The first vector.
        b: The second vector.

    Returns:
        The cosine distance between the two vectors.
    """
    if len(a) != len(b):
        raise ValueError('Input vectors must have the same length')
    dot_product = sum(ai * bi for ai, bi in zip(a, b, strict=True))
    magnitude_a = sqrt(sum(ai * ai for ai in a))
    magnitude_b = sqrt(sum(bi * bi for bi in b))

    if magnitude_a == 0 or magnitude_b == 0:
        raise ValueError('Invalid input: zero vector')

    return 1 - (dot_product / (magnitude_a * magnitude_b))


async def generate_response(question: str) -> GenerateResponse:
    """Generate a response to a question.

    Args:
        question: The question to answer.

    Returns:
        A GenerateResponse object with the answer.
    """
    input_embedding = await ai.embed(
        embedder=ollama_name(EMBEDDER_MODEL),
        content=question,
    )
    nearest_pokemon = find_nearest_pokemons(input_embedding[0].embedding)
    pokemons_context = '\n'.join(f'{pokemon.name}: {pokemon.description}' for pokemon in nearest_pokemon)

    return await ai.generate(
        model=ollama_name(GENERATE_MODEL),
        prompt=f'Given the following context on Pokemon:\n${pokemons_context}\n\nQuestion: ${question}\n\nAnswer:',
    )


class PokemonFlowInput(BaseModel):
    """Input for Pokemon flow."""

    question: str = Field(default='Who is the best water pokemon?', description='Question about Pokemon')


@ai.flow(
    name='Pokedex',
)
async def pokemon_flow(input: PokemonFlowInput) -> str:
    """Generate a request to greet a user.

    Args:
        input: Input with question about Pokemon.

    Returns:
        A GenerateRequest object with the greeting message.
    """
    await embed_pokemons()
    response = await generate_response(question=input.question)
    if not response.message or not response.message.content:
        raise ValueError('No message content returned from model')
    text = response.message.content[0].root.text
    return str(text) if text is not None else ''


async def main() -> None:
    """Main function."""
    response = await pokemon_flow(PokemonFlowInput(question='Who is the best water pokemon?'))
    await logger.ainfo(response)


if __name__ == '__main__':
    ai.run_main(main())
