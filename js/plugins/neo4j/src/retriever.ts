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

import * as z from 'zod';
import { Neo4jGraphConfig } from './types';
import { Neo4jVectorStore } from './vector';
import { EmbedderArgument } from '@genkit-ai/ai/embedder';
import { Document, defineRetriever } from '@genkit-ai/ai/retriever';

/**
 * Configures a Neo4j retriever.
 */
export function configureNeo4jRetriever<
EmbedderCustomOptions extends z.ZodTypeAny,
>(params: {
  clientParams: Neo4jGraphConfig;
  indexName: string;
  embedder: EmbedderArgument<EmbedderCustomOptions>;
  embedderOptions?: z.infer<EmbedderCustomOptions>;
}) {
  const { indexName, embedder, embedderOptions } = {
    ...params,
  };
  const neo4jConfig = params.clientParams;

  return defineRetriever(
    {
      name: `neo4j/${params.indexName}`
    },
    async (query: Document, options) => {
      const docs = await Neo4jVectorStore.fromExistingIndex(
        embedder, embedderOptions, neo4jConfig
      ).then(store => store.similaritySearch(query.text(), options.k));

      return {
        documents: docs.map(doc => doc.toJSON())
      };
    }
  );
}