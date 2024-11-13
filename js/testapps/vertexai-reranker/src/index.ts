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

// Sample app for demonstrating the Vertex AI plugin retriever and reranker capabilities using a local file for demo purposes.

import { Document, genkit, z } from 'genkit';
// Import necessary Vertex AI plugins and configuration:
import { vertexAI } from '@genkit-ai/vertexai';
import { vertexAIRerankers } from '@genkit-ai/vertexai/rerankers';
import { LOCATION, PROJECT_ID } from './config';

// Initialize Genkit with Vertex AI and Reranker plugins
const ai = genkit({
  plugins: [
    vertexAI({
      projectId: PROJECT_ID,
      location: LOCATION,
      googleAuth: {
        scopes: ['https://www.googleapis.com/auth/cloud-platform'],
      },
    }),
    vertexAIRerankers({
      projectId: PROJECT_ID,
      location: LOCATION,
      rerankOptions: [
        {
          model: 'semantic-ranker-512@latest', // Semantic ranker model to be used
        },
      ],
    }),
  ],
});

/**
 * Mock data to simulate document retrieval.
 * Each item represents a document with simplified content.
 */
const FAKE_DOCUMENT_CONTENT = [
  'pythagorean theorem',
  'e=mc^2',
  'pi',
  'dinosaurs',
  "euler's identity",
  'prime numbers',
  'fourier transform',
  'ABC conjecture',
  'riemann hypothesis',
  'triangles',
  "schrodinger's cat",
  'quantum mechanics',
  'the avengers',
  "harry potter and the philosopher's stone",
  'movies',
];

/**
 * @flow rerankFlow
 * Defines a flow to rerank a set of documents based on a given query.
 *
 * @flowDescription
 * This flow takes a query string, retrieves predefined documents, and ranks them
 * based on their relevance to the query using Vertex AI's reranker model.
 *
 * @inputSchema
 * The flow expects an object containing:
 * - query: A string representing the user's search query.
 *
 * @outputSchema
 * Returns an array of objects containing:
 * - text: The content of the ranked document.
 * - score: The relevance score assigned by the reranker model.
 *
 * @example
 * Input:
 * {
 *   "query": "quantum mechanics"
 * }
 *
 * Output:
 * [
 *   { "text": "quantum mechanics", "score": 0.95 },
 *   { "text": "schrodinger's cat", "score": 0.85 },
 *   { "text": "e=mc^2", "score": 0.80 }
 * ]
 */
export const rerankFlow = ai.defineFlow(
  {
    name: 'rerankFlow',
    inputSchema: z.object({ query: z.string() }), // Input must be an object with a 'query' string
    outputSchema: z.array(
      z.object({
        text: z.string(), // Each result includes a document's text
        score: z.number(), // And its relevance score
      })
    ),
  },
  async ({ query }) => {
    console.log('Received query:', query);

    // Convert fake document content into Document objects
    const documents = FAKE_DOCUMENT_CONTENT.map((text) =>
      Document.fromText(text)
    );

    // Specify the reranker to be used
    const reranker = 'vertexai/semantic-ranker-512@latest';

    // Call the reranker with the query and documents
    const rerankedDocuments = await ai.rerank({
      reranker,
      query: Document.fromText(query),
      documents,
    });

    // Return the reranked documents with text and score
    return rerankedDocuments.map((doc) => ({
      text: doc.text,
      score: doc.metadata.score,
    }));
  }
);

/**
 * Starts the Flow Server for testing and UI interaction.
 * This allows the `rerankFlow` to be invoked from the Genkit UI or programmatically.
 */
ai.startFlowServer({
  flows: [rerankFlow], // Registers the defined flow for the server
});
