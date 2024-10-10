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

import { EmbedderAction, EmbedderReference } from 'genkit';
import { GoogleAuth } from 'google-auth-library';
import { PluginOptions } from '..';

let SUPPORTED_EMBEDDER_MODELS: Record<string, { name: string }> = {};
let textEmbeddingGeckoEmbedder;

let textEmbedding004: EmbedderReference;
let textEmbeddingGecko: EmbedderReference;
let textEmbeddingGecko001: EmbedderReference;
let textEmbeddingGecko002: EmbedderReference;
let textEmbeddingGecko003: EmbedderReference;
let textEmbeddingGeckoMultilingual001: EmbedderReference;
let textMultilingualEmbedding002: EmbedderReference;

export default async function vertexAiEmbedders(
  projectId: string,
  location: string,
  options: PluginOptions | undefined,
  authClient: GoogleAuth
): Promise<EmbedderAction<any>[]> {
  await initalizeDependencies();

  let embedders: any[] = [];

  embedders.push(
    Object.keys(SUPPORTED_EMBEDDER_MODELS).map((name) =>
      textEmbeddingGeckoEmbedder(name, authClient, { projectId, location })
    )
  );

  return embedders;
}

async function initalizeDependencies() {
  const {
    SUPPORTED_EMBEDDER_MODELS: SUPPORTED_EMBEDDER_MODELS_IMPORT,
    textEmbedding004: textEmbedding004Import,
    textEmbeddingGecko: textEmbeddingGeckoImport,
    textEmbeddingGecko001: textEmbeddingGecko001Import,
    textEmbeddingGecko002: textEmbeddingGecko002Import,
    textEmbeddingGecko003: textEmbeddingGecko003Import,
    textEmbeddingGeckoEmbedder: textEmbeddingGeckoEmbedderImport,
    textEmbeddingGeckoMultilingual001: textEmbeddingGeckoMultilingual001Import,
    textMultilingualEmbedding002: textMultilingualEmbedding002Import,
  } = await import('./embedder.js');

  SUPPORTED_EMBEDDER_MODELS = SUPPORTED_EMBEDDER_MODELS_IMPORT;
  textEmbedding004 = textEmbedding004Import;
  textEmbeddingGecko = textEmbeddingGeckoImport;
  textEmbeddingGecko001 = textEmbeddingGecko001Import;
  textEmbeddingGecko002 = textEmbeddingGecko002Import;
  textEmbeddingGecko003 = textEmbeddingGecko003Import;
  textEmbeddingGeckoEmbedder = textEmbeddingGeckoEmbedderImport;
  textEmbeddingGeckoMultilingual001 = textEmbeddingGeckoMultilingual001Import;
  textMultilingualEmbedding002 = textMultilingualEmbedding002Import;
}

export {
  textEmbedding004,
  textEmbeddingGecko,
  textEmbeddingGecko001,
  textEmbeddingGecko002,
  textEmbeddingGecko003,
  textEmbeddingGeckoEmbedder,
  textEmbeddingGeckoMultilingual001,
  textMultilingualEmbedding002,
};
