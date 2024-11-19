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

import devLocalVectorstore, {
  devLocalIndexerRef,
  devLocalRetrieverRef,
} from '@genkit-ai/dev-local-vectorstore';
import { textEmbedding004, vertexAI } from '@genkit-ai/vertexai';
import { genkit } from 'genkit';
import { readFileSync } from 'node:fs';

const ai = genkit({
  plugins: [
    vertexAI({ projectId: 'bleigh-genkit-test', location: 'us-central1' }),
    devLocalVectorstore([
      { indexName: 'school-handbook', embedder: textEmbedding004 },
    ]),
  ],
});

const indexer = devLocalIndexerRef('school-handbook');

async function makeEmbeddings() {
  const policies = readFileSync('./src/handbook.txt', {
    encoding: 'utf8',
  }).split(/\n\n/);

  await ai.index({
    indexer,
    documents: policies.map((p) => ({ content: [{ text: p }] })),
  });
}

const retriever = devLocalRetrieverRef('school-handbook');

async function testRetrieval() {
  console.log(
    (
      await ai.retrieve({
        retriever,
        query: "What's the dress code?",
        options: { n: 3 },
      })
    ).map((d) => d.text)
  );
}

testRetrieval();
