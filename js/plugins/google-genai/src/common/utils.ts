/**
 * Copyright 2025 Google LLC
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

import { EmbedderReference, JSONSchema, ModelReference } from 'genkit';
import { GenerationCommonConfigSchema } from 'genkit/model';

/**
 * Finds the nearest model reference based on a provided version string.
 *
 * @param {string} version The version string to match against.
 * @param {Record<string, ModelReference<TSchema>>} knownModels A record of known models,
 * @param {ModelReference<TSchema>} genericModel A generic model reference to return if no
 *   specific match is found.
 * @param {TOptions=} options Optional configuration options to apply to the model.
 * @returns {ModelReference<TSchema>} The nearest matching model reference, or the generic model
 *   if no match is found.
 * @template TSchema The schema type for the model reference.
 * @template TOptions The type of the options object.
 */
export function nearestModelRef<
  TSchema extends typeof GenerationCommonConfigSchema,
  TOptions,
>(
  version: string,
  knownModels: Record<string, ModelReference<TSchema>>,
  genericModel: ModelReference<TSchema>,
  options?: TOptions
): ModelReference<TSchema> {
  const matchingKey = longestMatchingPrefix(version, Object.keys(knownModels));
  if (matchingKey) {
    return knownModels[matchingKey].withConfig({
      ...options,
      version,
    });
  }

  return genericModel.withConfig({ ...options, version });
}

/**
 * Finds the longest string in an array that is a prefix of a given version string.
 *
 * @param {string} version The version string to check against.
 * @param {string[]} potentialMatches An array of potential prefix strings.
 * @returns {string} The longest prefix string that matches the version, or an empty string if none match.
 */
function longestMatchingPrefix(version: string, potentialMatches: string[]) {
  return potentialMatches
    .filter((p) => version.startsWith(p))
    .reduce(
      (longest, current) =>
        current.length > longest.length ? current : longest,
      ''
    );
}

/**
 * Cleans a JSON schema by removing specific keys and standardizing types.
 *
 * @param {JSONSchema} schema The JSON schema to clean.
 * @returns {JSONSchema} The cleaned JSON schema.
 */
export function cleanSchema(schema: JSONSchema): JSONSchema {
  const out = structuredClone(schema);
  for (const key in out) {
    if (key === '$schema' || key === 'additionalProperties') {
      delete out[key];
      continue;
    }
    if (typeof out[key] === 'object') {
      out[key] = cleanSchema(out[key]);
    }
    // Zod nullish() and picoschema optional fields will produce type `["string", "null"]`
    // which is not supported by the model API. Convert them to just `"string"`.
    if (key === 'type' && Array.isArray(out[key])) {
      // find the first that's not `null`.
      out[key] = out[key].find((t) => t !== 'null');
    }
  }
  return out;
}

export function isMultiModalEmbedder(embedder: EmbedderReference): boolean {
  const input = embedder.info?.supports?.input || '';
  return (input.includes('text') && input.includes('image')) || false;
}
