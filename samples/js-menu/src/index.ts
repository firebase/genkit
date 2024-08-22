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
import { configureGenkit } from '@genkit/core';
import { devLocalVectorstore } from '@genkit/dev-local-vectorstore';
import { dotprompt } from '@genkit/dotprompt';
import { textEmbeddingGecko, vertexAI } from '@genkit/vertexai';

// Initialize Genkit

configureGenkit({
  plugins: [
    dotprompt(),
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
export { s01_staticMenuDotPrompt, s01_vanillaPrompt } from './01/prompts';
// 02
export { s02_menuQuestionFlow } from './02/flows';
export { s02_dataMenuPrompt } from './02/prompts';
// 03
export { s03_multiTurnChatFlow } from './03/flows';
export { s03_chatPreamblePrompt } from './03/prompts';
// 04
export { s04_indexMenuItemsFlow, s04_ragMenuQuestionFlow } from './04/flows';
export { s04_ragDataMenuPrompt } from './04/prompts';
// 05
export {
  s05_readMenuFlow,
  s05_textMenuQuestionFlow,
  s05_visionMenuQuestionFlow,
} from './05/flows';
export { s05_readMenuPrompt, s05_textMenuPrompt } from './05/prompts';
