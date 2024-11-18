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

export const CONTEXT_CACHE_SUPPORTED_MODELS = [
  'gemini-1.5-flash-001',
  'gemini-1.5-pro-001',
];

export const INVALID_ARGUMENT_MESSAGES = {
  modelVersion: `Model version is required for context caching, supported only in ${CONTEXT_CACHE_SUPPORTED_MODELS.join(',')} models.`,
  tools: 'Context caching cannot be used simultaneously with tools.',
  codeExecution:
    'Context caching cannot be used simultaneously with code execution.',
};

export const DEFAULT_TTL = 300;
