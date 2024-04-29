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

import { configureGenkit } from '@genkit-ai/core';
import { firebase } from '@genkit-ai/firebase';
import { geminiPro, googleAI } from '@genkit-ai/googleai';
import { vertexAI } from '@genkit-ai/vertexai';
import { DELICIOUSNESS } from './deliciousness/deliciousness_evaluator.js';
import { FUNNINESS } from './funniness/funniness_evaluator.js';
import byoEval from './index.js';
import { PII_DETECTION } from './pii/pii_evaluator.js';
import { regexMatcher } from './regex/regex_evaluator.js';

const URL_REGEX =
  /https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)/i;
const US_PHONE_REGEX =
  /^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4}$/i;

export default configureGenkit({
  plugins: [
    firebase(),
    googleAI(),
    vertexAI(),
    byoEval({
      judge: geminiPro,
      judgeConfig: {
        safetySettings: [
          {
            category: 'HARM_CATEGORY_HATE_SPEECH',
            threshold: 'BLOCK_NONE',
          },
          {
            category: 'HARM_CATEGORY_DANGEROUS_CONTENT',
            threshold: 'BLOCK_NONE',
          },
          {
            category: 'HARM_CATEGORY_HARASSMENT',
            threshold: 'BLOCK_NONE',
          },
          {
            category: 'HARM_CATEGORY_SEXUALLY_EXPLICIT',
            threshold: 'BLOCK_NONE',
          },
        ],
      },
      metrics: [
        // regexMatcher is a factory method that generates an evaluator of the name regex_match_{name} for each call.
        // byo/regex_match_url
        regexMatcher('url', URL_REGEX),
        // byo/regex_match_us_phone
        regexMatcher('us_phone', US_PHONE_REGEX),
        PII_DETECTION,
        DELICIOUSNESS,
        FUNNINESS,
      ],
    }),
  ],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'debug',
});
