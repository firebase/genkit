/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { genkit, z } from 'genkit';
import { ollama } from 'genkitx-ollama';

const ai = genkit({
  plugins: [
    ollama({
      embedders: [{ name: 'nomic-embed-text', dimensions: 768 }],
      requestHeaders: async (params) => {
        console.log('Using server address', params.serverAddress);
        // Simulate a token-based authentication
        await new Promise((resolve) => setTimeout(resolve, 200));
        return { Authorization: 'Bearer my-token' };
      },
    }),
  ],
});

interface PokemonInfo {
  name: string;
  description: string;
  embedding: number[] | null;
}

const pokemonList: PokemonInfo[] = [
  {
    name: 'Pikachu',
    description:
      'An Electric-type Pokemon known for its strong electric attacks.',
    embedding: null,
  },
  {
    name: 'Charmander',
    description:
      'A Fire-type Pokemon that evolves into the powerful Charizard.',
    embedding: null,
  },
  {
    name: 'Bulbasaur',
    description:
      'A Grass/Poison-type Pokemon that grows into a powerful Venusaur.',
    embedding: null,
  },
  {
    name: 'Squirtle',
    description:
      'A Water-type Pokemon known for its water-based attacks and high defense.',
    embedding: null,
  },
  {
    name: 'Jigglypuff',
    description: 'A Normal/Fairy-type Pokemon with a hypnotic singing ability.',
    embedding: null,
  },
];

// Step 1: Embed each Pokemon's description
async function embedPokemon() {
  for (const pokemon of pokemonList) {
    pokemon.embedding = (
      await ai.embed({
        embedder: ollama.embedder('nomic-embed-text'),
        content: pokemon.description,
      })
    )[0].embedding;
  }
}

// Step 2: Find top 3 Pokemon closest to the input
function findNearestPokemon(inputEmbedding: number[], topN = 3) {
  if (pokemonList.some((pokemon) => pokemon.embedding === null))
    throw new Error('Some Pokemon are not yet embedded');
  const distances = pokemonList.map((pokemon) => ({
    pokemon,
    distance: cosineDistance(inputEmbedding, pokemon.embedding!),
  }));
  return distances
    .sort((a, b) => a.distance - b.distance)
    .slice(0, topN)
    .map((entry) => entry.pokemon);
}

// Helper function: cosine distance calculation
function cosineDistance(a: number[], b: number[]) {
  const dotProduct = a.reduce((sum, ai, i) => sum + ai * b[i], 0);
  const magnitudeA = Math.sqrt(a.reduce((sum, ai) => sum + ai * ai, 0));
  const magnitudeB = Math.sqrt(b.reduce((sum, bi) => sum + bi * bi, 0));
  if (magnitudeA === 0 || magnitudeB === 0)
    throw new Error('Invalid input: zero vector');
  return 1 - dotProduct / (magnitudeA * magnitudeB);
}

// Step 3: Generate response with RAG results in context
async function generateResponse(question: string) {
  const inputEmbedding = (
    await ai.embed({
      embedder: ollama.embedder('nomic-embed-text'),
      content: question,
    })
  )[0].embedding;

  const nearestPokemon = findNearestPokemon(inputEmbedding);
  const pokemonContext = nearestPokemon
    .map((pokemon) => `${pokemon.name}: ${pokemon.description}`)
    .join('\n');

  return await ai.generate({
    model: ollama.model('phi3.5:latest'),
    prompt: `Given the following context on Pokemon:\n${pokemonContext}\n\nQuestion: ${question}\n\nAnswer:`,
  });
}

export const pokemonFlow = ai.defineFlow(
  {
    name: 'Pokedex',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (input) => {
    await embedPokemon();
    const response = await generateResponse(input);

    const answer = response.text;

    return answer;
  }
);

export const joker = ai.defineFlow(
  {
    name: 'joker',
    inputSchema: z.object({
      model: z.string().default('gemma3:latest'),
      subject: z.string().describe('subject').default('AI'),
    }),
    outputSchema: z.string(),
  },
  async ({ subject, model }, { sendChunk }) => {
    const { text } = await ai.generate({
      prompt: `tell me joke about ${subject}`,
      model: ollama.model(model),
      onChunk: sendChunk,
    });

    return text;
  }
);
