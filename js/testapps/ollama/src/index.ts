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
import { logger } from 'genkit/logging';
import { ollama } from 'genkitx-ollama';
// Define our schemas upfront for better type safety and documentation
const PokemonSchema = z.object({
  name: z.string(),
  description: z.string(),
  type: z.array(
    z.enum(['Electric', 'Fire', 'Grass', 'Poison', 'Water', 'Normal', 'Fairy'])
  ),
  stats: z.object({
    attack: z.number(),
    defense: z.number(),
    speed: z.number(),
  }),
});

const QueryResponseSchema = z.object({
  matchedPokemon: z.array(z.string()),
  analysis: z.object({
    answer: z.string(),
    confidence: z.number().min(0).max(1),
    relevantTypes: z.array(z.string()),
  }),
});

type Pokemon = z.infer<typeof PokemonSchema>;

const ai = genkit({
  plugins: [
    ollama({
      serverAddress: 'http://localhost:11434',
      embedders: [{ name: 'nomic-embed-text', dimensions: 768 }],
      models: [{ name: 'phi3.5:latest' }],
      requestHeaders: async (params) => {
        console.log('Using server address', params.serverAddress);
        await new Promise((resolve) => setTimeout(resolve, 200));
        return { Authorization: 'Bearer my-token' };
      },
    }),
  ],
});

// Enhanced Pokemon database with more structured data
const pokemonDatabase: Pokemon[] = [
  {
    name: 'Pikachu',
    description:
      'An Electric-type Pokemon known for its strong electric attacks.',
    type: ['Electric'],
    stats: { attack: 55, defense: 40, speed: 90 },
  },
  {
    name: 'Charmander',
    description:
      'A Fire-type Pokemon that evolves into the powerful Charizard.',
    type: ['Fire'],
    stats: { attack: 52, defense: 43, speed: 65 },
  },
  {
    name: 'Bulbasaur',
    description:
      'A Grass/Poison-type Pokemon that grows into a powerful Venusaur.',
    type: ['Grass', 'Poison'],
    stats: { attack: 49, defense: 49, speed: 45 },
  },
  {
    name: 'Squirtle',
    description:
      'A Water-type Pokemon known for its water-based attacks and high defense.',
    type: ['Water'],
    stats: { attack: 48, defense: 65, speed: 43 },
  },
  {
    name: 'Jigglypuff',
    description: 'A Normal/Fairy-type Pokemon with a hypnotic singing ability.',
    type: ['Normal', 'Fairy'],
    stats: { attack: 45, defense: 20, speed: 20 },
  },
];

export const pokemonFlow = ai.defineFlow(
  {
    name: 'Pokedex',
    inputSchema: z.object({
      question: z.string(),
      maxResults: z.number().default(3).optional(),
    }),
    outputSchema: QueryResponseSchema,
  },
  async ({ question, maxResults = 3 }) => {
    // Embed the question and all Pokemon descriptions in parallel
    const [questionEmbedding, pokemonEmbeddings] = await Promise.all([
      ai.embed({
        embedder: 'ollama/nomic-embed-text',
        content: question,
      }),
      Promise.all(
        pokemonDatabase.map((pokemon) =>
          ai.embed({
            embedder: 'ollama/nomic-embed-text',
            content: pokemon.description,
          })
        )
      ),
    ]);

    // Calculate similarity and sort Pokemon by relevance
    const similarityScores = pokemonEmbeddings.map((embedding, index) => ({
      pokemon: pokemonDatabase[index],
      similarity: 1 - cosineSimilarity(questionEmbedding, embedding),
    }));

    const topPokemon = similarityScores
      .sort((a, b) => b.similarity - a.similarity)
      .slice(0, maxResults);

    logger.info('Top Pokemon:', topPokemon);

    // Build context for the LLM
    const context = topPokemon.map(({ pokemon }) => ({
      name: pokemon.name,
      description: pokemon.description,
      type: pokemon.type,
      stats: pokemon.stats,
    }));

    // Generate structured response using the LLM
    const response = await ai.generate({
      model: 'ollama/phi3.5:latest',
      prompt: `Given these Pokemon details:
${JSON.stringify(context, null, 2)}

Answer this question: ${question}

Format your response as JSON with:
- matchedPokemon: names of relevant Pokemon
- analysis.answer: detailed explanation
- analysis.confidence: score from 0-1 indicating certainty
- analysis.relevantTypes: Pokemon types mentioned in answer`,
      output: {
        format: 'json',
        schema: QueryResponseSchema,
      },
    });

    return (
      response.output || {
        matchedPokemon: [],
        analysis: {
          answer: '',
          confidence: 0,
          relevantTypes: [],
        },
      }
    );
  }
);

// Helper function for vector similarity
function cosineSimilarity(a: number[], b: number[]): number {
  const dotProduct = a.reduce((sum, ai, i) => sum + ai * b[i], 0);
  const magnitudeA = Math.sqrt(a.reduce((sum, ai) => sum + ai * ai, 0));
  const magnitudeB = Math.sqrt(b.reduce((sum, bi) => sum + bi * bi, 0));
  return dotProduct / (magnitudeA * magnitudeB);
}
