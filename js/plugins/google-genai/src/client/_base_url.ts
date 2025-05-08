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

import { GoogleGenAIOptions } from './client';

let _defaultBaseGeminiUrl: string | undefined = undefined;
let _defaultBaseVertexUrl: string | undefined = undefined;

/**
 * Parameters for setting the base URLs for the Gemini API and Vertex AI API.
 */
export interface BaseUrlParameters {
  geminiUrl?: string;
  vertexUrl?: string;
}

/**
 * Overrides the base URLs for the Gemini API and Vertex AI API.
 *
 * @remarks This function should be called before initializing the SDK. If the
 * base URLs are set after initializing the SDK, the base URLs will not be
 * updated. Base URLs provided in the HttpOptions will also take precedence over
 * URLs set here.
 *
 * @example
 * ```ts
 * import {GoogleGenAI, setDefaultBaseUrls} from '@google/genai';
 * // Override the base URL for the Gemini API.
 * setDefaultBaseUrls({geminiUrl:'https://gemini.google.com'});
 *
 * // Override the base URL for the Vertex AI API.
 * setDefaultBaseUrls({vertexUrl: 'https://vertexai.googleapis.com'});
 *
 * const ai = new GoogleGenAI({apiKey: 'GEMINI_API_KEY'});
 * ```
 */
export function setDefaultBaseUrls(baseUrlParams: BaseUrlParameters) {
  _defaultBaseGeminiUrl = baseUrlParams.geminiUrl;
  _defaultBaseVertexUrl = baseUrlParams.vertexUrl;
}

/**
 * Returns the default base URLs for the Gemini API and Vertex AI API.
 */
export function getDefaultBaseUrls(): BaseUrlParameters {
  return {
    geminiUrl: _defaultBaseGeminiUrl,
    vertexUrl: _defaultBaseVertexUrl,
  };
}

/**
 * Returns the default base URL based on the following priority:
 *   1. Base URLs set via HttpOptions.
 *   2. Base URLs set via the latest call to setDefaultBaseUrls.
 *   3. Base URLs set via environment variables.
 */
export function getBaseUrl(
  options: GoogleGenAIOptions,
  vertexBaseUrlFromEnv: string | undefined,
  geminiBaseUrlFromEnv: string | undefined
): string | undefined {
  if (!options.httpOptions?.baseUrl) {
    const defaultBaseUrls = getDefaultBaseUrls();
    if (options.vertexai) {
      return defaultBaseUrls.vertexUrl ?? vertexBaseUrlFromEnv;
    } else {
      return defaultBaseUrls.geminiUrl ?? geminiBaseUrlFromEnv;
    }
  }

  return options.httpOptions.baseUrl;
}
