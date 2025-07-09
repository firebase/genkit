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

import { GenerateRequest } from 'genkit/model';
import { GoogleAuth } from 'google-auth-library';
import type { ClientOptions, ImagenInstance, PluginOptions } from './types';

export { extractImagenImage, extractText } from '../common/utils.js';

const CLOUD_PLATFORM_OAUTH_SCOPE =
  'https://www.googleapis.com/auth/cloud-platform';

function parseFirebaseProjectId(): string | undefined {
  if (!process.env.FIREBASE_CONFIG) return undefined;
  try {
    return JSON.parse(process.env.FIREBASE_CONFIG).projectId as string;
  } catch {
    return undefined;
  }
}

let __mockDerivedOptions: ClientOptions | undefined = undefined;
function setMockDerivedOptions(options: ClientOptions | undefined): void {
  __mockDerivedOptions = options;
}
export const TEST_ONLY = { setMockDerivedOptions };

export async function getDerivedOptions(
  options?: PluginOptions,
  AuthClass: typeof GoogleAuth = GoogleAuth // Injectable testing
): Promise<ClientOptions> {
  if (__mockDerivedOptions) {
    return Promise.resolve(__mockDerivedOptions);
  }
  let authOptions = options?.googleAuth;
  let authClient: GoogleAuth;
  const providedProjectId =
    options?.projectId ||
    process.env.GCLOUD_PROJECT ||
    parseFirebaseProjectId();
  if (process.env.GCLOUD_SERVICE_ACCOUNT_CREDS) {
    const serviceAccountCreds = JSON.parse(
      process.env.GCLOUD_SERVICE_ACCOUNT_CREDS
    );
    authOptions = {
      credentials: serviceAccountCreds,
      scopes: [CLOUD_PLATFORM_OAUTH_SCOPE],
      projectId: providedProjectId,
    };
    authClient = new AuthClass(authOptions);
  } else {
    authClient = new AuthClass(
      authOptions ?? {
        scopes: [CLOUD_PLATFORM_OAUTH_SCOPE],
        projectId: providedProjectId,
      }
    );
  }

  const projectId =
    options?.projectId ||
    process.env.GCLOUD_PROJECT ||
    (await authClient.getProjectId());
  const location =
    options?.location || process.env.GCLOUD_LOCATION || 'us-central1';

  if (!location) {
    throw new Error(
      `VertexAI Plugin is missing the 'location' configuration. Please set the 'GCLOUD_LOCATION' environment variable or explicitly pass 'location' into genkit config.`
    );
  }
  if (!projectId) {
    throw new Error(
      `VertexAI Plugin is missing the 'project' configuration. Please set the 'GCLOUD_PROJECT' environment variable or explicitly pass 'project' into genkit config.`
    );
  }

  return {
    location,
    projectId,
    authClient,
  };
}

export function extractImagenMask(
  request: GenerateRequest
): ImagenInstance['mask'] | undefined {
  const mask = request.messages
    .at(-1)
    ?.content.find((p) => !!p.media && p.metadata?.type === 'mask')
    ?.media?.url.split(',')[1];

  if (mask) {
    return { image: { bytesBase64Encoded: mask } };
  }
  return undefined;
}
