/**
 * Copyright 2024 The Fire Company
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
import { type Genkit } from 'genkit';
import { genkitPlugin } from 'genkit/plugin';
import { OpenAI, type ClientOptions } from 'openai';

export interface PluginOptions extends Partial<ClientOptions> {
  name: string;
  initializer?: (ai: Genkit, client: OpenAI) => Promise<void>;
}

/**
 * This module provides the `openAICompatible` plugin factory for Genkit. It
 * enables interaction with OpenAI-compatible API endpoints, allowing users to
 * leverage various AI models by configuring API keys and other client options.
 *
 * The core export is `openAICompatible`, a function that accepts
 * `PluginOptions` and returns a Genkit plugin.
 *
 * Key `PluginOptions` include:
 *  - `name`: A string to uniquely identify this plugin instance
 *    (e.g., 'deepSeek', 'customOpenAI').
 *  - `apiKey`: The API key for the service. If not provided directly, the
 *    plugin will attempt to use the `OPENAI_API_KEY` environment variable.
 *  - `initializer`: An optional asynchronous function for custom setup after
 *    the OpenAI client is initialized. It receives the Genkit instance and the
 *    OpenAI client.
 *  - Additional properties from OpenAI's `ClientOptions` (like `baseURL`,
 *    `timeout`, etc.) can be passed to customize the OpenAI client.
 *
 * The returned plugin initializes an OpenAI client tailored to the provided
 * options, making configured models available for use within Genkit flows.
 *
 * @param {PluginOptions} options - Configuration options for the plugin.
 * @returns A Genkit plugin configured for an OpenAI-compatible service.
 *
 * Usage: Import `openAICompatible` (or your chosen import name for the default
 * export) from this package (e.g., `genkitx-openai`). Then, invoke it within
 * the `plugins` array of `configureGenkit`, providing the necessary
 * `PluginOptions`.
 *
 * Example:
 * ```typescript
 * import myOpenAICompatiblePlugin from 'genkitx-openai'; // Default import
 *
 * export default configureGenkit({
 *  plugins: [
 *    myOpenAICompatiblePlugin({
 *      name: 'gpt4o', // Name for this specific plugin configuration
 *      apiKey: 'your-openai-api-key',
 *      // For a non-OpenAI compatible endpoint:
 *      // baseURL: 'https://api.custom-llm-provider.com/v1',
 *    }),
 *    myOpenAICompatiblePlugin({
 *      name: 'localLlama',
 *      apiKey: 'ollama', // Or specific key if required by local server
 *      baseURL: 'http://localhost:11434/v1', // Example for Ollama
 *    }),
 *    // ... other plugins
 *  ],
 * });
 * ```
 */

export const openAICompatible = (options: PluginOptions) =>
  genkitPlugin(options.name, async (ai: Genkit) => {
    const client = new OpenAI(options);
    if (options.initializer) {
      await options.initializer(ai, client);
    }
  });

export default openAICompatible;
