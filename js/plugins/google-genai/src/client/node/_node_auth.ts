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

import { GoogleAuth, GoogleAuthOptions } from 'google-auth-library';

import { Auth } from '../_auth';

export const GOOGLE_API_KEY_HEADER = 'x-goog-api-key';
const REQUIRED_VERTEX_AI_SCOPE =
  'https://www.googleapis.com/auth/cloud-platform';

export interface NodeAuthOptions {
  /**
   * The API Key. This is required for Gemini API users.
   */
  apiKey?: string;
  /**
   * Optional. These are the authentication options provided by google-auth-library for Vertex AI users.
   * Complete list of authentication options are documented in the
   * GoogleAuthOptions interface:
   * https://github.com/googleapis/google-auth-library-nodejs/blob/main/src/auth/googleauth.ts.
   */
  googleAuthOptions?: GoogleAuthOptions;
}

export class NodeAuth implements Auth {
  private readonly googleAuth?: GoogleAuth;
  private readonly apiKey?: string;

  constructor(opts: NodeAuthOptions) {
    if (opts.apiKey !== undefined) {
      this.apiKey = opts.apiKey;
      return;
    }
    const vertexAuthOptions = buildGoogleAuthOptions(opts.googleAuthOptions);
    this.googleAuth = new GoogleAuth(vertexAuthOptions);
  }

  async addAuthHeaders(headers: Headers): Promise<void> {
    if (this.apiKey !== undefined) {
      this.addKeyHeader(headers);
      return;
    }

    return this.addGoogleAuthHeaders(headers);
  }

  private addKeyHeader(headers: Headers) {
    if (headers.get(GOOGLE_API_KEY_HEADER) !== null) {
      return;
    }
    if (this.apiKey === undefined) {
      // This should never happen, this method is only called
      // when apiKey is set.
      throw new Error('Trying to set API key header but apiKey is not set');
    }
    headers.append(GOOGLE_API_KEY_HEADER, this.apiKey);
  }

  private async addGoogleAuthHeaders(headers: Headers): Promise<void> {
    if (this.googleAuth === undefined) {
      // This should never happen, addGoogleAuthHeaders should only be
      // called when there is no apiKey set and in these cases googleAuth
      // is set.
      throw new Error(
        'Trying to set google-auth headers but googleAuth is unset'
      );
    }
    const authHeaders = await this.googleAuth.getRequestHeaders();
    for (const key in authHeaders) {
      if (headers.get(key) !== null) {
        continue;
      }
      headers.append(key, authHeaders[key]);
    }
  }
}

function buildGoogleAuthOptions(
  googleAuthOptions?: GoogleAuthOptions
): GoogleAuthOptions {
  let authOptions: GoogleAuthOptions;
  if (!googleAuthOptions) {
    authOptions = {
      scopes: [REQUIRED_VERTEX_AI_SCOPE],
    };
    return authOptions;
  } else {
    authOptions = googleAuthOptions;
    if (!authOptions.scopes) {
      authOptions.scopes = [REQUIRED_VERTEX_AI_SCOPE];
      return authOptions;
    } else if (
      (typeof authOptions.scopes === 'string' &&
        authOptions.scopes !== REQUIRED_VERTEX_AI_SCOPE) ||
      (Array.isArray(authOptions.scopes) &&
        authOptions.scopes.indexOf(REQUIRED_VERTEX_AI_SCOPE) < 0)
    ) {
      throw new Error(
        `Invalid auth scopes. Scopes must include: ${REQUIRED_VERTEX_AI_SCOPE}`
      );
    }
    return authOptions;
  }
}
