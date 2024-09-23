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
import { genkit } from '@genkit-ai/core';
import { devLocalVectorstore } from '@genkit-ai/dev-local-vectorstore';
import { textEmbeddingGecko, vertexAI } from '@genkit-ai/vertexai';

// Initialize Genkit

export const ai = genkit({
  plugins: [
    // dotprompt(),
    vertexAI({ location: 'us-central1' }),
    devLocalVectorstore([
      {
        indexName: 'menu-items',
        embedder: textEmbeddingGecko,
        embedderOptions: { taskType: 'RETRIEVAL_DOCUMENT' },
      },
    ]),
  ],
  enableTracingAndMetrics: true,
  flowStateStore: 'firebase',
  logLevel: 'debug',
  traceStore: 'firebase',
});

// Export all of the example prompts and flows

// 01
export { s01_staticMenuDotPrompt, s01_vanillaPrompt } from './01/prompts.js';
// 02
export { s02_menuQuestionFlow } from './02/flows.js';
export { s02_dataMenuPrompt } from './02/prompts.js';
// 03
export { s03_multiTurnChatFlow } from './03/flows.js';
export { s03_chatPreamblePrompt } from './03/prompts.js';
// 04
export { s04_indexMenuItemsFlow, s04_ragMenuQuestionFlow } from './04/flows.js';
export { s04_ragDataMenuPrompt } from './04/prompts.js';
// 05
export {
  s05_readMenuFlow,
  s05_textMenuQuestionFlow,
  s05_visionMenuQuestionFlow,
} from './05/flows.js';
export { s05_readMenuPrompt, s05_textMenuPrompt } from './05/prompts.js';
