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

import { checks } from '@genkit-ai/checks';
import { devLocalVectorstore } from '@genkit-ai/dev-local-vectorstore';
import { genkitEval } from '@genkit-ai/evaluator';
import { enableFirebaseTelemetry } from '@genkit-ai/firebase';
import { firebaseAuth } from '@genkit-ai/firebase/auth';
import { enableGoogleCloudTelemetry } from '@genkit-ai/google-cloud';
import { googleAI } from '@genkit-ai/googleai';
import { vertexAI } from '@genkit-ai/vertexai';
import { vertexAIEvaluation } from '@genkit-ai/vertexai/evaluation';
import { vertexAIModelGarden } from '@genkit-ai/vertexai/modelgarden';
import { vertexAIRerankers } from '@genkit-ai/vertexai/rerankers';
import { genkit } from 'genkit';
import { chroma } from 'genkitx-chromadb';
import { ollama } from 'genkitx-ollama';
import { pinecone } from 'genkitx-pinecone';

enableFirebaseTelemetry;
enableGoogleCloudTelemetry;
checks;
googleAI;
vertexAI;
vertexAIModelGarden;
vertexAIEvaluation;
vertexAIRerankers;
ollama;
pinecone;
chroma;
devLocalVectorstore;
genkitEval;
firebaseAuth;

export const ai = genkit({});
