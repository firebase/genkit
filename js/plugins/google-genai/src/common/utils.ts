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
import {
  EnhancedGenerateContentResponse,
  FunctionCall,
  GenerateContentResponse,
} from './types';

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

/**
 * Extracts and concatenates the text and code output from a
 * `GenerateContentResponse` into a single string.
 *
 * @param response The `GenerateContentResponse` object from which to extract text.
 * @returns A string containing all the text and code output from the response.
 *          Returns an empty string if no candidates are present or if no text or code is found.
 */
function getText(response: GenerateContentResponse): string {
  return (
    response.candidates?.[0].content?.parts
      .map((part) => {
        let string = '';
        if (part.text) {
          string += part.text;
        }
        if (part.executableCode) {
          string +=
            '\n```' +
            part.executableCode.language +
            '\n' +
            part.executableCode.code +
            '\n```\n';
        }
        if (part.codeExecutionResult) {
          string += '\n```\n' + part.codeExecutionResult.output + '\n```\n';
        }
        return string;
      })
      .join('') || ''
  );
}

/**
 * Extracts and returns an array of `FunctionCall` objects from the first candidate
 * in a `GenerateContentResponse`, if available.
 *
 * @param response The `GenerateContentResponse` object from which to extract function calls.
 * @returns An array of `FunctionCall` objects, or `undefined` if no candidates
 *          are present or if no function calls are found within the candidates.
 */
function getFunctionCalls(
  response: GenerateContentResponse
): FunctionCall[] | undefined {
  return response.candidates?.[0].content?.parts
    .map((part) => {
      if (part.functionCall) {
        return part.functionCall;
      }
      return undefined;
    })
    .filter((part) => part !== undefined) as FunctionCall[] | undefined;
}

/**
 * Enhances a `GenerateContentResponse` object by adding helper functions for
 * accessing text and function calls.
 *
 * @param response The `GenerateContentResponse` object to enhance.
 * @returns The enhanced `GenerateContentResponse` object with the added helper functions.
 * @sideEffects This function modifies the input object by adding properties.
 */
export function enhanceContentResponse(
  response: GenerateContentResponse
): EnhancedGenerateContentResponse {
  (response as EnhancedGenerateContentResponse).text = () => {
    if (response.candidates && response.candidates.length > 0) {
      return getText(response);
    }
    return '';
  };

  (response as EnhancedGenerateContentResponse).functionCalls = () => {
    if (response.candidates && response.candidates.length > 0) {
      return getFunctionCalls(response);
    }
    return undefined;
  };
  return response as EnhancedGenerateContentResponse;
}

export function isMultiModalEmbedder(embedder: EmbedderReference): boolean {
  const input = embedder.info?.supports?.input || '';
  return (input.includes('text') && input.includes('image')) || false;
}
