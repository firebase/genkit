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

//import { GoogleAuthOptions } from 'google-auth-library';

import { ApiClient } from '../_api_client';
import { getBaseUrl } from '../_base_url';
import { Caches } from '../caches';
import { Chats } from '../chats';
import { GoogleGenAIOptions } from '../client';
import { Files } from '../files';
import { Live } from '../live';
import { Models } from '../models';
import { NodeAuth } from '../node/_node_auth';
import { NodeWebSocketFactory } from '../node/_node_websocket';
import { Operations } from '../operations';
import { Tunings } from '../tunings';

import { NodeUploader } from './_node_uploader';

const LANGUAGE_LABEL_PREFIX = 'gl-node/';

/**
 * The Google GenAI SDK.
 *
 * @remarks
 * Provides access to the GenAI features through either the {@link
 * https://cloud.google.com/vertex-ai/docs/reference/rest | Gemini API} or
 * the {@link https://cloud.google.com/vertex-ai/docs/reference/rest | Vertex AI
 * API}.
 *
 * The {@link GoogleGenAIOptions.vertexai} value determines which of the API
 * services to use.
 *
 * When using the Gemini API, a {@link GoogleGenAIOptions.apiKey} must also be
 * set. When using Vertex AI, both {@link GoogleGenAIOptions.project} and {@link
 * GoogleGenAIOptions.location} must be set, or a {@link
 * GoogleGenAIOptions.apiKey} must be set when using Express Mode.
 *
 * Explicitly passed in values in {@link GoogleGenAIOptions} will always take
 * precedence over environment variables. If both project/location and api_key
 * exist in the environment variables, the project/location will be used.
 *
 * @example
 * Initializing the SDK for using the Gemini API:
 * ```ts
 * import {GoogleGenAI} from '@google/genai';
 * const ai = new GoogleGenAI({apiKey: 'GEMINI_API_KEY'});
 * ```
 *
 * @example
 * Initializing the SDK for using the Vertex AI API:
 * ```ts
 * import {GoogleGenAI} from '@google/genai';
 * const ai = new GoogleGenAI({
 *   vertexai: true,
 *   project: 'PROJECT_ID',
 *   location: 'PROJECT_LOCATION'
 * });
 * ```
 *
 */
export class GoogleGenAI {
  protected readonly apiClient: ApiClient;
  private readonly apiKey?: string;
  public readonly vertexai: boolean;
  //private readonly googleAuthOptions?: GoogleAuthOptions;
  private readonly project?: string;
  private readonly location?: string;
  private readonly apiVersion?: string;
  readonly models: Models;
  readonly live: Live;
  readonly chats: Chats;
  readonly caches: Caches;
  readonly files: Files;
  readonly operations: Operations;
  readonly tunings: Tunings;

  constructor(options: GoogleGenAIOptions) {
    // Validate explicitly set initializer values.
    if ((options.project || options.location) && options.apiKey) {
      throw new Error(
        'Project/location and API key are mutually exclusive in the client initializer.'
      );
    }

    this.vertexai =
      options.vertexai ?? getBooleanEnv('GOOGLE_GENAI_USE_VERTEXAI') ?? false;
    const envApiKey = getEnv('GOOGLE_API_KEY');
    const envProject = getEnv('GOOGLE_CLOUD_PROJECT');
    const envLocation = getEnv('GOOGLE_CLOUD_LOCATION');

    this.apiKey = options.apiKey ?? envApiKey;
    this.project = options.project ?? envProject;
    this.location = options.location ?? envLocation;

    // Handle when to use Vertex AI in express mode (api key)
    if (options.vertexai) {
      // Explicit api_key and explicit project/location already handled above.
      if ((envProject || envLocation) && options.apiKey) {
        // Explicit api_key takes precedence over implicit project/location.
        console.debug(
          'The user provided Vertex AI API key will take precedence over' +
            ' the project/location from the environment variables.'
        );
        this.project = undefined;
        this.location = undefined;
      } else if ((options.project || options.location) && envApiKey) {
        // Explicit project/location takes precedence over implicit api_key.
        console.debug(
          'The user provided project/location will take precedence over' +
            ' the API key from the environment variables.'
        );
        this.apiKey = undefined;
      } else if ((envProject || envLocation) && envApiKey) {
        // Implicit project/location takes precedence over implicit api_key.
        console.debug(
          'The project/location from the environment variables will take' +
            ' precedence over the API key from the environment variables.'
        );
        this.apiKey = undefined;
      }
    }

    const baseUrl = getBaseUrl(
      options,
      getEnv('GOOGLE_VERTEX_BASE_URL'),
      getEnv('GOOGLE_GEMINI_BASE_URL')
    );
    if (baseUrl) {
      if (options.httpOptions) {
        options.httpOptions.baseUrl = baseUrl;
      } else {
        options.httpOptions = { baseUrl: baseUrl };
      }
    }

    this.apiVersion = options.apiVersion;
    const auth = new NodeAuth({
      apiKey: this.apiKey,
      googleAuthOptions: options.googleAuthOptions,
    });
    this.apiClient = new ApiClient({
      auth: auth,
      project: this.project,
      location: this.location,
      apiVersion: this.apiVersion,
      apiKey: this.apiKey,
      vertexai: this.vertexai,
      httpOptions: options.httpOptions,
      userAgentExtra: LANGUAGE_LABEL_PREFIX + process.version,
      uploader: new NodeUploader(),
    });
    this.models = new Models(this.apiClient);
    this.live = new Live(this.apiClient, auth, new NodeWebSocketFactory());
    this.chats = new Chats(this.models, this.apiClient);
    this.caches = new Caches(this.apiClient);
    this.files = new Files(this.apiClient);
    this.operations = new Operations(this.apiClient);
    this.tunings = new Tunings(this.apiClient);
  }
}

function getEnv(env: string): string | undefined {
  return process?.env?.[env]?.trim() ?? undefined;
}

function getBooleanEnv(env: string): boolean {
  return stringToBoolean(getEnv(env));
}

function stringToBoolean(str?: string): boolean {
  if (str === undefined) {
    return false;
  }
  return str.toLowerCase() === 'true';
}
