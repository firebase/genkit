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

import { GenerationConfig } from '@genkit-ai/ai/model';

// TODO: Do a real type here.
type JSONSchema = unknown;

/**
 * Metadata for a prompt.
 */
export interface PromptMetadata {
  /** The name of the prompt. */
  name?: string;

  /**
   * The name of the model to use for this prompt, e.g. `google-vertex/gemini-pro`
   * or `openai/gpt-4-0125-preview`.
   */
  model: string;

  /** Names of tools (registered separately) to allow use of in this prompt. */
  tools?: string[];

  /** Model configuration. Not all models support all options. */
  config?: GenerationConfig<unknown>;

  context?: {
    /** When true, the RAG context prompt should include citations. */
    citations?: boolean;
  };

  /**
   * Defines the variables that can be passed into the template in JSON schema form.
   * If not supplied, any object will be accepted.
   */
  variables?: JSONSchema;

  /** Defines the default variable values to use if none are provided. */
  defaultVariables?: Record<string, any>;

  /** Defines the expected model output format. */
  output?: {
    /** Desired output format for this prompt. */
    format?: 'json' | 'text';
    /** JSON schema of desired output (must not be specified with non-json format). */
    schema?: any; // TODO: clean up type of this
  };

  /** Arbitrary metadata to be used by code, tools, and libraries. */
  metadata?: Record<string, any>;
}
