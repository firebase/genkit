# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
import asyncio
from math import sqrt

from pydantic import BaseModel

from genkit.ai import Genkit
from genkit.core.typing import GenerateResponse
from genkit.plugins.ollama import Ollama, ollama_name
from genkit.plugins.ollama.constants import OllamaAPITypes
from genkit.plugins.ollama.models import (
    EmbeddingModelDefinition,
    ModelDefinition,
    OllamaPluginParams,
)

EMBEDDER_MODEL = 'nomic-embed-text'
EMBEDDER_DIMENSIONS = 768
GENERATE_MODEL = 'phi3.5:latest'

plugin_params = OllamaPluginParams(
    models=[
        ModelDefinition(
            name=GENERATE_MODEL,
            api_type=OllamaAPITypes.GENERATE,
        )
    ],
    embedders=[
        EmbeddingModelDefinition(
            name=EMBEDDER_MODEL,
            dimensions=512,
        )
    ],
)

ai = Genkit(
    plugins=[
        Ollama(
            plugin_params=plugin_params,
        )
    ],
)


class PokemonInfo(BaseModel):
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


async def embed_pokemons():
    for pokemon in pokemon_list:
        embedding_response = await ai.embed(
            model=ollama_name(EMBEDDER_MODEL),
            documents=[pokemon.description],
        )
        pokemon.embedding = embedding_response.embeddings[0]


def find_nearest_pokemons(
    input_embedding: list[float], top_n: int = 3
) -> list[PokemonInfo]:
    if any(pokemon.embedding is None for pokemon in pokemon_list):
        raise AttributeError('Some Pokemon are not yet embedded')
    pokemon_distances = [
        {
            **pokemon.model_dump(),
            'distance': cosine_distance(input_embedding, pokemon.embedding),
        }
        for pokemon in pokemon_list
    ]
    return sorted(
        pokemon_distances,
        key=lambda pokemon_distance: pokemon_distance['distance'],
    )[:top_n]


def cosine_distance(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise ValueError('Input vectors must have the same length')

    dot_product = sum(ai * bi for ai, bi in zip(a, b))
    magnitude_a = sqrt(sum(ai * ai for ai in a))
    magnitude_b = sqrt(sum(bi * bi for bi in b))

    if magnitude_a == 0 or magnitude_b == 0:
        raise ValueError('Invalid input: zero vector')

    return 1 - (dot_product / (magnitude_a * magnitude_b))


async def generate_response(question: str) -> GenerateResponse:
    input_embedding = await ai.embed(
        model=ollama_name(EMBEDDER_MODEL),
        documents=[question],
    )
    nearest_pokemon = find_nearest_pokemons(input_embedding.embeddings[0])
    pokemons_context = '\n'.join(
        f'{pokemon["name"]}: {pokemon["description"]}'
        for pokemon in nearest_pokemon
    )

    return await ai.generate(
        model=ollama_name(GENERATE_MODEL),
        prompt=f'Given the following context on Pokemon:\n${pokemons_context}\n\nQuestion: ${question}\n\nAnswer:',
    )


@ai.flow(
    name='Pokedex',
)
async def pokemon_flow(question: str):
    """Generate a request to greet a user.

    Args:
        question: Question for pokemons.

    Returns:
        A GenerateRequest object with the greeting message.
    """
    await embed_pokemons()
    response = await generate_response(question=question)
    return response.message.content[0].root.text


async def main() -> None:
    response = await pokemon_flow('Who is the best water pokemon?')
    print(response)


if __name__ == '__main__':
    asyncio.run(main())
