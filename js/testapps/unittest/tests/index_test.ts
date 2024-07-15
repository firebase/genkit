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

import { defineEmbedder } from '@genkit-ai/ai/embedder';
import { defineModel } from '@genkit-ai/ai/model';
import { defineRetriever, Document } from '@genkit-ai/ai/retriever';
import { runFlow } from '@genkit-ai/flow';
import assert from 'node:assert';
import { beforeEach, describe, it } from 'node:test';
import { pdfQA } from '../src/index.js';

describe('registry', () => {
  beforeEach(() => {
    // Override the retriever.
    defineRetriever({ name: 'devLocalVectorstore/pdfQA' }, async () => {
      return {
        documents: [Document.fromText('FlumeJava is great!')],
      };
    });

    // Override the embedder.
    defineEmbedder({ name: 'vertexai/textembedding-gecko@003' }, async () => {
      return {
        embeddings: [
          {
            embedding: Array(768).fill(0),
          },
        ],
      };
    });

    // Override the model, just echo the input.
    defineModel({ name: 'vertexai/gemini-1.5-flash' }, async (input) => {
      return {
        candidates: [
          {
            index: 0,
            finishReason: 'stop',
            message: {
              role: 'model',
              content: [
                {
                  text: input.messages
                    .map((m) => m.content.map((c) => c.text).join())
                    .join(),
                },
              ],
            },
          },
        ],
      };
    });
  });

  describe('pdfQA', () => {
    it('returns answers the question', async () => {
      const resp = await runFlow(pdfQA, 'what is flumeJava?');
      assert.ok(resp.includes('FlumeJava is great!'));
    });
  });
});
